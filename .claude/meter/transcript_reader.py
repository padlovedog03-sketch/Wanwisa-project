"""Adapter ก's transcript reader for the agent-time meter (`scripts/agent_time.py`).

It turns this assistant's session transcripts into the meter's neutral events
and implements the reader contract documented in `scripts/agent_time.py`::

    runs(source: Path, since: datetime) -> Iterator[Run]

Layout read (DESIGN-verify-tiers-merge-gate.md §J.3, measured on local
transcripts):

* `<source>/<session>.jsonl`: a main-thread session, reported as `(main thread)`.
* `<source>/<session>/subagents/agent-<id>.jsonl`: a subagent run; its role is
  `agentType` in the sibling `agent-<id>.meta.json`.

WHY AN ALLOW-LIST. The transcripts carry many internal event types besides
the user and assistant lines: attachments, API requests, system and queue
events, and untimed `api-request-blob` copies of tool blocks. The
coordinator's first measurement timed some of them and put idle time 7
minutes wrong (ADR-2). So exactly one constant, `CLOCK_EVENT_TYPES`, admits
clock events. Everything else is dropped and counted by type, so a new
internal type stays visible on the meter's `excluded events:` line instead of
moving time silently. `tests/hooks/test_transcript_reader.py` widens this
constant on purpose and shows the golden totals break.

Nothing read here is printed: commands and inbound text are kept in memory
for classification only (R39).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Iterator

from agent_time import Event, Run  # registered by agent_time.load_reader before this module runs

#: The only event types that are clock events (ADR-2). The J-AC3 mutation targets this.
CLOCK_EVENT_TYPES = frozenset({"user", "assistant"})

#: Tool name → the meter's neutral tool kind (design §J.3). Anything else is "other".
TOOL_KINDS = {
    "Bash": "shell",
    "Read": "read",
    "Grep": "search",
    "Glob": "search",
    "Edit": "edit",
    "Write": "edit",
    "MultiEdit": "edit",
    "NotebookEdit": "edit",
    "Monitor": "wait",
}

#: Edit tool → the input key holding the file it edits (R41, the size class). Edit and
#: Write measured on 9,612 local calls (2026-10-20); NotebookEdit from the tool's own
#: schema; MultiEdit appeared in no local transcript, so its key is unverified.
EDIT_PATH_KEYS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}

#: A background launch's acknowledgement in its tool result. `\w+` stops at the
#: trailing full stop the real text carries (measured on local transcripts).
ACK_RE = re.compile(r"background with ID: (\w+)")

#: A background job's completion arrives as a user line carrying this tag.
#: The tag, not the bare word: some user lines only mention it.
NOTIFICATION_TAG = "<task-notification>"
TASK_ID_RE = re.compile(r"<task-id>(\w+)</task-id>")

MAIN_THREAD = "(main thread)"
UNKNOWN_ROLE = "(unknown)"

#: An event type or role is printed as a label, so it must be a plain single-line
#: token (R39). Anything else could write its own report lines (a newline can forge
#: the rework-share line), so it is counted under UNPRINTABLE instead. `fullmatch`,
#: not `$`: `$` also matches before a trailing newline.
LABEL_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
UNPRINTABLE = "(unprintable label)"

#: A line whose shape the reader cannot use (an id that is not a string, nesting
#: deeper than the interpreter recurses) is one unreadable line, not a report-wide
#: internal error (J-AC7). Exceptions only: their messages are never printed.
_BAD_LINE = (TypeError, ValueError, AttributeError, KeyError, RecursionError)


def _label(value: object) -> str:
    return value if isinstance(value, str) and LABEL_RE.fullmatch(value) else UNPRINTABLE


def _id(value: object) -> object:
    """A message or tool id the meter can key on: a string or absent, else the line is unreadable."""
    if value is not None and not isinstance(value, str):
        raise TypeError("id is not a string")
    return value


def _blocks(content: object) -> list:
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text(content: object) -> str:
    """All text inside a message or tool-result content, strings and text blocks alike."""
    if isinstance(content, str):
        return content
    parts = []
    for block in _blocks(content):
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif "content" in block:
            parts.append(_text(block["content"]))
    return "\n".join(parts)


def _edited_paths(name: str, tool_input: dict, cwd: object) -> tuple:
    """The edited path of an edit tool call, normalised; () when it cannot be determined (R41).

    A relative path is resolved against the line's `cwd`, and only when that is
    absolute. Lexical only (`os.path.normpath`): the disk is never read, because
    a run's files are often gone by the time the meter runs. Never raises, so an
    odd path cannot make the whole line unreadable and move the timing.
    """
    path = tool_input.get(EDIT_PATH_KEYS[name])
    if not isinstance(path, str) or not path:
        return ()
    if not os.path.isabs(path):
        if not isinstance(cwd, str) or not os.path.isabs(cwd):
            return ()
        path = os.path.join(cwd, path)
    return (os.path.normpath(path),)


def _events_of(kind: str, t: dt.datetime, message: dict, cwd: object = None) -> list:
    """Neutral events for one clock line (design §J.3, mapping table)."""
    content = message.get("content")
    if kind == "assistant":
        events = [Event(t, "model", message_id=_id(message.get("id")))]
        for block in _blocks(content):
            if block.get("type") != "tool_use":
                continue
            name = _id(block.get("name", ""))
            tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
            command = tool_input.get("command")
            events.append(
                Event(
                    t,
                    "tool_call",
                    tool_id=_id(block.get("id")),
                    tool_kind=TOOL_KINDS.get(name, "other"),
                    command=command if name == "Bash" and isinstance(command, str) else None,
                    background=tool_input.get("run_in_background") is True,
                    paths=_edited_paths(name, tool_input, cwd) if name in EDIT_PATH_KEYS else (),
                )
            )
        return events
    # Every other clock type takes the user path, so widening CLOCK_EVENT_TYPES
    # changes the totals (that is what makes the J-AC3 mutation bite).
    results = [b for b in _blocks(content) if b.get("type") == "tool_result"]
    if results:
        return [
            Event(t, "tool_result", tool_id=_id(b.get("tool_use_id")), job_ids=tuple(ACK_RE.findall(_text(b.get("content")))))
            for b in results
        ]
    text = _text(content)
    if NOTIFICATION_TAG in text:
        return [Event(t, "notification", job_ids=tuple(TASK_ID_RE.findall(text)))]
    return [Event(t, "inbound", text=text)]


def _read_run(path: Path, agent_type: str, unreadable: int = 0) -> Run:
    """One run from one transcript. A file that cannot be read at all (a directory,
    no permission) is one unreadable line, never an error: an OSError's message
    carries the path, and the path carries identifiers (R39)."""
    events: list = []
    excluded: Counter = Counter()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return Run(agent_type, events, excluded, unreadable + 1)
    # Records end at "\n" only: splitlines() also breaks on U+0085, U+2028 and U+2029,
    # which JSON allows raw inside a string, and would cut a valid line apart (QA D7).
    for line in text.split("\n"):
        line = line.removesuffix("\r")
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            kind = record.get("type")
        except (ValueError, AttributeError, RecursionError):  # ValueError covers JSONDecodeError and the int-digit limit (QA N1a)
            unreadable += 1
            continue
        if not isinstance(kind, str) or kind not in CLOCK_EVENT_TYPES:  # type first: a list is unhashable
            excluded[_label(kind)] += 1
            continue
        try:
            t = dt.datetime.fromisoformat(str(record["timestamp"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            excluded[f"{kind} (no timestamp)"] += 1
            continue
        if t.tzinfo is None:
            # A time with no offset is not a point in time: guessing UTC could move it
            # by hours, and comparing it with aware times raises. Counted, not timed.
            excluded[f"{kind} (timestamp without offset)"] += 1
            continue
        message = record.get("message") if isinstance(record.get("message"), dict) else {}
        try:
            events.extend(_events_of(kind, t, message, record.get("cwd")))
        except _BAD_LINE:
            unreadable += 1
    events.sort(key=lambda e: e.t)  # stable: a tool call keeps its place after its model event
    return Run(agent_type, events, excluded, unreadable)


def _role(meta_path: Path) -> tuple:
    """(agentType, unreadable count) from a subagent's meta file.

    Missing → unknown role. Unreadable (a directory, no permission, bad JSON or
    bad encoding) → unknown role plus one unreadable line, never an error whose
    message would carry the path (R39). Valid JSON that is not an object, or an
    `agentType` that is not a non-empty string → unknown. A string role that is not a
    single-line token → UNPRINTABLE.
    """
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return UNKNOWN_ROLE, 0
    except (OSError, ValueError, RecursionError):  # ValueError covers JSONDecodeError and UnicodeDecodeError
        return UNKNOWN_ROLE, 1
    if not isinstance(meta, dict):
        return UNKNOWN_ROLE, 0
    agent_type = meta.get("agentType")
    if not isinstance(agent_type, str) or not agent_type:  # a non-string role is never printed (R39)
        return UNKNOWN_ROLE, 0
    return _label(agent_type), 0


def runs(source: Path, since: dt.datetime) -> Iterator[Run]:
    """Yield every run under `source` whose last clock event is on or after `since`.

    A run with no clock events at all is yielded too, so the meter can count it.
    """
    source = Path(source)
    found = [(p, MAIN_THREAD, 0) for p in sorted(source.glob("*.jsonl"))]
    for path in sorted(source.glob("*/subagents/agent-*.jsonl")):
        found.append((path, *_role(path.with_name(path.name[: -len(".jsonl")] + ".meta.json"))))
    for path, agent_type, unreadable in found:
        run = _read_run(path, agent_type, unreadable)
        if not run.events or run.events[-1].t >= since:
            yield run

