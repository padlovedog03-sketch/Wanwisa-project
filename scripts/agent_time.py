#!/usr/bin/env python3
"""Agent-time meter: where an agent's working time goes (R37–R40, R32).

WHY THIS EXISTS. Agent time was first measured by hand, with throwaway
scripts, and the first measurement was wrong without any error: it counted
the assistant's internal bookkeeping events as activity and moved 7 minutes
of idle time into "work" (SPEC/DESIGN-verify-tiers-merge-gate.md, ADR-2). A
number that is quietly wrong reaches the owner as fact, so the meter is a
tested script with a known-answer timeline and planted mutations
(`tests/framework/test_agent_time.py`).

The core is neutral. It never reads an assistant's transcript format itself:
a *reader* turns transcripts into the neutral events below. Pass the reader
for your assistant with `--reader <path>`, as declared in
`doc/framework/ADAPTERS.md`. With no reader the meter prints `unsupported`,
never zero (R38).

Reader contract (every adapter's reader implements exactly this)::

    def runs(source: Path, since: datetime) -> Iterator[Run]

It yields one `Run` per agent run whose last event is on or after `since`.
A run holds clock events only (the equivalents of an inbound message and a
model response, plus the tool calls, tool results and background-job
notifications they carry), sorted by time. Every other event type is dropped
and counted in `Run.excluded` by type name; a line that cannot be parsed is
counted in `Run.unreadable_lines`.

Output is categories, counts and durations only. Commands and inbound text
are used for classification and are never printed (R39, AGENTS.md §8).

Usage:
    python3 scripts/agent_time.py --reader <path> --dir <transcripts> [--since YYYY-MM-DD]
                                  [--rework [--qa-dir doc/qa]] [--test-pattern REGEX]

Always exits 0 (R39, design §J.2): it reports, it never gates. A malformed
argument prints one `agent-time: error: …` line. Any unexpected failure prints
`agent-time: internal error: <exception type>` and nothing else from it: an
exception's message or traceback can carry a transcript path or content.

Plain stdlib, no AI required (RUNTIME-CONTRACT layer ๑).
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Iterable, Optional, Pattern

#: R31's fixed rework-cause vocabulary. The QA template and the doc-contract
#: test read it from here, so the list has one source (design §H).
REWORK_CAUSES = ("missed-ac", "regression", "spec-defect", "test-gap", "env-flaky")

#: The categories whose sum is active time (design §J.2). Idle is not one of them.
CATEGORIES = ("model", "tests", "waits", "other tools", "read/git/edit")

#: Agent types whose runs count for the rework share (design §J.7).
ENGINEER_TYPES = ("ai-engineer", "frontend-engineer")

#: A shell command that runs tests (design §J.5). Neutral tool names, not providers.
#: A project extends it with --test-pattern.
TEST_RE = re.compile(r"verify-|pytest|playwright|vitest|jest|npm (run )?test|go test|cargo test")

#: A hand-written polling loop (design §J.5, R26): a loop keyword at the start
#: (after optional leading `VAR=value;` assignments), with `sleep` in the body.
#: Deliberately independent of any interception guard, so that an assistant
#: without one still gets a reading.
POLL_RE = re.compile(r"^\s*(?:\w+=\S*\s*;?\s*)*(until|while|for)\b[\s\S]*\bsleep\b")

#: Words that make a polling loop a wait on a test result rather than on
#: something else (design §J.5 names this matcher without defining it; taken
#: from the coordinator's prior-art script).
RESULT_WORDS_RE = re.compile(r"pass|fail|exit|EXIT|tier|GATE")

#: A shell command that only reads, searches or asks git (design §J.5).
READ_SHELL_RE = re.compile(r"^\s*(grep|rg|cat|sed -n|head|tail|ls|find|wc|git)\b")

DEFAULT_SINCE = "1970-01-01"

#: What a role or excluded type that is not a printable single-line label is
#: reported as (R39). A reader's labels come from transcript data; a line break in
#: one would write its own report lines, so the core checks them too.
UNPRINTABLE = "(unprintable label)"

METHOD = (
    "method: gaps between consecutive clock events, attributed to the event that ends the gap "
    "(a model response → model; a tool result → that tool's category; a background-job "
    "notification → its wait; an inbound message → idle); active = every category except idle; "
    "category rows are means per run, active time, turns and idle are medians; a turn is one "
    "distinct model-response id"
)
LIMITS = (
    "limits: commands are classified by pattern, not meaning; a loop hidden inside a script is "
    "not seen; agent reuse inflates idle time, not active time; a run belongs to the window of "
    "its last event; a background job whose completion is never notified inside the run is not "
    "timed as a wait; with no reader the meter says unsupported instead of printing zero"
)


@dataclass(frozen=True)
class Event:
    """One neutral clock event. `command` and `text` are never printed."""

    t: dt.datetime
    kind: str  # "model" | "tool_call" | "tool_result" | "notification" | "inbound"
    message_id: Optional[str] = None
    tool_id: Optional[str] = None
    tool_kind: Optional[str] = None  # "shell" | "read" | "search" | "edit" | "wait" | "other"
    command: Optional[str] = None
    background: bool = False
    job_ids: tuple = ()
    text: Optional[str] = None


@dataclass(frozen=True)
class Run:
    """One agent run: clock events sorted by time, plus what the reader dropped."""

    agent_type: str
    events: list
    excluded: Counter = field(default_factory=Counter)
    unreadable_lines: int = 0


def count_turns(events: Iterable[Event]) -> int:
    """Turns are distinct model-response ids, not model events (ADR-3).

    One response spans several transcript lines; counting lines inflated
    turns about threefold on this repo's own transcripts.
    """
    return len({e.message_id for e in events if e.kind == "model"})


def _category_of(call: Optional[Event], test_re: Pattern) -> str:
    """The category a tool's result gap belongs to (design §J.5)."""
    if call is None:
        return "other tools"
    command = call.command if isinstance(call.command, str) else ""
    if call.tool_kind == "shell":
        if POLL_RE.search(command):
            return "tests:polling" if test_re.search(command) or RESULT_WORDS_RE.search(command) else "waits:polling"
        if test_re.search(command):
            return "tests:bg-launch" if call.background else "tests:running"
        if READ_SHELL_RE.search(command):
            return "read/git/edit"
    if call.tool_kind in ("read", "search", "edit"):
        return "read/git/edit"
    if call.tool_kind == "wait":
        return "waits:other"
    return "other tools"


def categorise(run: Run, test_re: Pattern = TEST_RE) -> dict:
    """Seconds per category and sub-line, plus `polling`, `idle`, `active` and `turns`.

    Each gap between consecutive events is attributed to the event that ends
    it. Sub-lines (`tests:running` …) sum to their category; `polling` repeats
    time already inside tests or waits and is never added to active again.
    """
    totals: dict = defaultdict(float)
    pending: dict = {}
    test_jobs: set = set()
    for prev, event in zip(run.events, run.events[1:]):
        gap = (event.t - prev.t).total_seconds()
        if event.kind in ("model", "tool_call"):
            cat = "model"
        elif event.kind == "tool_result":
            call = pending.pop(event.tool_id, None)
            cat = _category_of(call, test_re)
            if cat == "tests:bg-launch":
                test_jobs.update(event.job_ids)
        elif event.kind == "notification":
            cat = "tests:bg-wait" if test_jobs.intersection(event.job_ids) else "waits:bg-wait"
        else:
            cat = "idle"
        if event.kind == "tool_call":
            pending[event.tool_id] = event
        totals[cat] += gap

    result = {name: totals[name] for name in ("model", "other tools", "read/git/edit", "idle")}
    for parent, subs in (
        ("tests", ("running", "bg-launch", "bg-wait", "polling")),
        ("waits", ("bg-wait", "polling", "other")),
    ):
        for sub in subs:
            result[f"{parent}:{sub}"] = totals[f"{parent}:{sub}"]
        result[parent] = sum(totals[f"{parent}:{sub}"] for sub in subs)
    result["polling"] = result["tests:polling"] + result["waits:polling"]
    result["active"] = sum(result[c] for c in CATEGORIES)
    result["turns"] = count_turns(run.events)
    return result


def load_reader(path: Path) -> Optional[ModuleType]:
    """Import a reader module from a file path; None when the file does not exist.

    The running core is registered as `agent_time` first, so a reader that
    imports it gets these very classes even when this file runs as __main__.
    """
    if not Path(path).is_file():
        return None
    sys.modules.setdefault("agent_time", sys.modules[__name__])
    spec = importlib.util.spec_from_file_location(f"agent_time_reader_{Path(path).stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_since(text: str) -> dt.datetime:
    """`YYYY-MM-DD` as midnight UTC."""
    return dt.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)


def _test_pattern(text: str) -> Pattern:
    """TEST_RE extended with a project's own test-command regex (`--test-pattern`)."""
    try:
        return re.compile(f"{TEST_RE.pattern}|{text}")
    except re.error as exc:
        raise argparse.ArgumentTypeError(f"invalid regex: {exc}") from exc


def _label(value: object) -> str:
    """`value` when it is a printable single-line string of at most 100 characters, else UNPRINTABLE.

    `isprintable()` also rejects the separators `str.splitlines()` breaks on (\x85, \u2028)
    and lone surrogates, which cannot be written to an ASCII or UTF-8 stdout.
    """
    return value if isinstance(value, str) and 0 < len(value) <= 100 and value.isprintable() else UNPRINTABLE


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f} min"


def _type_block(agent_type: str, runs: list, test_re: Pattern) -> list:
    """The report lines for one agent type."""
    per_run = [categorise(r, test_re) for r in runs]
    n = len(per_run)

    def mean(key: str) -> float:
        return sum(p[key] for p in per_run) / n

    lines = [
        f"{agent_type}: {n} runs · active median {_minutes(statistics.median(p['active'] for p in per_run))}"
        f" · turns median {statistics.median(p['turns'] for p in per_run):g}"
    ]
    active = mean("active")
    labels = {
        "model": "model generating",
        "tests": "tests",
        "waits": "waits (background/poll)",
        "other tools": "other tools",
        "read/git/edit": "read/git/edit",
    }
    details = {
        "tests": (
            f"   (running {mean('tests:running') / 60:.1f} · background launch {mean('tests:bg-launch') / 60:.1f}"
            f" · background wait {mean('tests:bg-wait') / 60:.1f}"
            f" · hand-written polling {mean('tests:polling') / 60:.1f})"
        ),
        "waits": f"   (background {mean('waits:bg-wait') / 60:.1f} · hand-written polling {mean('waits:polling') / 60:.1f})",
    }
    for cat in CATEGORIES:
        share = f"{round(mean(cat) / active * 100):3d}%" if active else "   —"
        lines.append(f"  {labels[cat]:<25}{mean(cat) / 60:5.1f} min/run  {share}{details.get(cat, '')}")
    if not active:
        lines.append("  no active time in these runs, so no shares")
    lines.append(
        f"  hand-written polling loops, all categories: {_minutes(mean('polling'))}/run (already counted above)"
    )
    lines.append(f"  idle (not active): median {_minutes(statistics.median(p['idle'] for p in per_run))}/run")
    return lines


def report(runs: list, since: dt.datetime, reader_name: str, test_re: Pattern = TEST_RE) -> str:
    """The text report: header, excluded events, one block per agent type, method, limits."""
    timed = [r for r in runs if r.events]
    excluded: Counter = Counter()
    for r in runs:
        for name, count in r.excluded.items():
            excluded[_label(name)] += count
    unreadable = sum(r.unreadable_lines for r in runs)
    lines = [
        f"agent-time — {len(timed)} runs read since {since:%Y-%m-%d} · reader: {reader_name}"
        f" · unreadable lines: {unreadable}"
    ]
    if len(timed) != len(runs):
        lines.append(f"runs with no clock events: {len(runs) - len(timed)}")
    lines.append(
        "excluded events (adapter-internal, not timed): "
        + (" · ".join(f"{name} {count}" for name, count in sorted(excluded.items())) or "none")
    )
    if not timed:
        lines.append("no runs with clock events in the window; nothing to report")
        return "\n".join(lines)
    by_type: dict = defaultdict(list)
    for r in timed:
        by_type[_label(r.agent_type)].append(r)
    for agent_type in sorted(by_type):
        lines.extend(_type_block(agent_type, by_type[agent_type], test_re))
    lines.extend([METHOD, LIMITS])
    return "\n".join(lines)


def _first_inbound_text(run: Run) -> str:
    return next((e.text or "" for e in run.events if e.kind == "inbound"), "")


def _qa_causes(qa_dir: Path, since: dt.datetime) -> tuple:
    """(valid causes, unclassified defects, reports with no Date:, FAIL reports with no Defects table).

    The last two are counted, not skipped silently: either would otherwise
    read exactly like a report with no defects.
    """
    causes: Counter = Counter()
    unclassified = no_date = no_table = 0
    for path in sorted(qa_dir.glob("QA-*.md")):
        text = path.read_text(encoding="utf-8")
        date = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        if not date:
            no_date += 1
            continue
        if parse_since(date.group(1)) < since:
            continue
        if not re.search(r"^#*\s*Verdict:\s*FAIL\b", text, re.M):
            continue
        section = re.search(r"^## Defects[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        table = [line for line in (section.group(1) if section else "").splitlines() if line.startswith("|")]
        if not table:
            no_table += 1
            continue
        rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in table]
        header, body = rows[0], [r for r in rows[1:] if not all(set(c) <= set("-: ") for c in r)]
        col = header.index("Rework cause") if "Rework cause" in header else None
        for row in body:
            cause = row[col].strip("`") if col is not None and col < len(row) else ""
            if cause in REWORK_CAUSES:
                causes[cause] += 1
            else:
                unclassified += 1
    return causes, unclassified, no_date, no_table


def rework_report(runs: list, qa_dir: Optional[Path], since: dt.datetime) -> str:
    """Rework share from the `REWORK:` brief marker (ADR-13), causes from QA reports (R31)."""
    engineer = [r for r in runs if r.events and r.agent_type in ENGINEER_TYPES]
    if not engineer:
        lines = ["rework share: no engineer runs in the window"]
    else:
        k = sum(1 for r in engineer if re.search(r"^REWORK:", _first_inbound_text(r), re.M))
        line = f"rework share: {k} of {len(engineer)} engineer runs ({round(k / len(engineer) * 100)}%)"
        if not k:
            line += " — unmarked: no brief carries a REWORK: line, so earlier rework cannot be told apart"
        lines = [line]
    if qa_dir is None:
        lines.append("rework causes: not read (pass --qa-dir)")
    elif not qa_dir.is_dir():
        lines.append("rework causes: QA directory not found (--qa-dir)")
    else:
        causes, unclassified, no_date, no_table = _qa_causes(qa_dir, since)
        lines.append(
            f"rework causes (FAIL QA reports dated since {since:%Y-%m-%d}): "
            + " · ".join(f"{c} {causes[c]}" for c in REWORK_CAUSES)
        )
        lines.append(f"unclassified defects: {unclassified}")
        lines.append(
            f"QA reports not read: {no_date + no_table}"
            f" (no Date: {no_date} · FAIL with no Defects table: {no_table})"
        )
    return "\n".join(lines)


class _UsageError(Exception):
    """A malformed argument, reported as one line instead of argparse's exit 2."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print usage and exit 2
        raise _UsageError(message)


def main(argv: list) -> int:
    """Print the report. Always returns 0: the meter reports, it never gates (R39).

    Nothing from an unexpected exception but its type is printed, because its
    message or traceback can carry a transcript path or transcript content.
    """
    try:
        return _run(argv)
    except _UsageError as exc:
        print(f"agent-time: error: {exc}")
    except Exception as exc:  # noqa: BLE001 — the R39 boundary: no traceback, path or exit 1, ever
        print(f"agent-time: internal error: {type(exc).__name__}")
    return 0


def _run(argv: list) -> int:
    parser = _Parser(description="Where agent time goes, by category.")
    parser.add_argument("--reader", type=Path, help="transcript reader, as declared in doc/framework/ADAPTERS.md")
    parser.add_argument("--dir", type=Path, help="transcript directory the reader understands")
    parser.add_argument("--since", type=parse_since, default=DEFAULT_SINCE, help="YYYY-MM-DD (default: all)")
    parser.add_argument("--rework", action="store_true", help="add the rework share and causes")
    parser.add_argument("--qa-dir", type=Path, help="QA reports for rework causes (e.g. doc/qa)")
    parser.add_argument("--test-pattern", type=_test_pattern, help="extra regex for this project's test commands")
    args = parser.parse_args(argv)

    reader = load_reader(args.reader) if args.reader else None
    if reader is None or not hasattr(reader, "runs"):
        print(
            "agent-time: unsupported — no transcript reader for this assistant "
            "(pass --reader as declared in doc/framework/ADAPTERS.md); nothing measured"
        )
        return 0
    if args.dir is None or not args.dir.is_dir():
        print("agent-time: transcript directory not found (--dir); nothing measured")
        return 0
    test_re = args.test_pattern or TEST_RE
    runs = list(reader.runs(args.dir, args.since))
    print(report(runs, args.since, args.reader.name, test_re))
    if args.rework:
        print(rework_report(runs, args.qa_dir, args.since))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
