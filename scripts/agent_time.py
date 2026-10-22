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

For the scorecard a reader also marks an inbound event `owner=True` when it is
a message from the owner (H-AC1's rule, which is the adapter's to apply), and a
model event `turn_end=True` when that response ended the turn; a model event
may carry its response `text`, read for Tier lines only. All three default to
off, and the time report never reads them.

Output is categories, counts and durations only. Commands and inbound text
are used for classification and are never printed (R39, AGENTS.md §8).

Usage:
    python3 scripts/agent_time.py --reader <path> --dir <transcripts> [--since YYYY-MM-DD]
                                  [--rework [--qa-dir doc/qa]] [--test-pattern REGEX]
    python3 scripts/agent_time.py --reader <path> --dir <transcripts> --scorecard
                                  [--since T] [--until T] [--memory-dir doc/memory]
        T is YYYY-MM-DD (midnight UTC) or YYYY-MM-DDTHH:MM:SSZ; the window is [since, until).
        Prints M1–M7 of PRD-jarvis-coordinator instead of the time report; it runs alone.

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
import math
import os
import re
import statistics
import sys
import unicodedata
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

#: Size classes by distinct files edited in a run (R41). Bounds are inclusive; None = no upper bound.
SIZE_CLASSES = (("investigate-only", 0, 0), ("small", 1, 5), ("medium", 6, 10), ("large", 11, None))

#: The classes trial acceptance judges (R22, M10); investigate-only is reported, not judged.
JUDGED_CLASSES = ("small", "medium", "large")

#: The tool kinds whose paths count toward the size class. The J2-AC2 mutation widens it.
SIZE_TOOL_KINDS = frozenset({"edit"})

UNKNOWN_SIZE = "size unknown"

#: A trial probe's brief carries a line starting `PROBE:` (R23, AM1-ADR-3).
PROBE_RE = re.compile(r"^PROBE:", re.M)

#: A shell command that writes a file: `sed -i`, `git apply`, or an output redirection
#: that is not to /dev/null or another descriptor (`2>&1`), and not an arrow or a
#: comparison (`->`, `=>`, `>=`). By pattern, for a visible count only: such files are
#: not in the size class.
SHELL_WRITE_RE = re.compile(r"\bsed\s+(-\w*\s+)*-i|\bgit\s+apply\b|(?<![0-9&>=-])>>?(?![>=])(?!\s*(&|/dev/null\b))")

SIZE_LIMITS = (
    "size limits: a run's size is its distinct edited paths, compared as written after "
    "normalising . and .. (a symlink or a case variant of one file counts twice); files written "
    "by shell commands are not counted; an edit call that failed still counts its file; a run "
    "with any pathless edit or unreadable line is size unknown"
)

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
    paths: tuple = ()  # edit calls only: normalised paths, counted, never printed; () = unknown
    owner: bool = False  # inbound only: the reader judged this an owner message (H-AC1)
    turn_end: bool = False  # model only: this response ended the turn (a message to the owner)


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


def _counted_paths(event: Event) -> Optional[list]:
    """The event's paths as normalised strings, or None when any is missing or not a path."""
    paths = event.paths
    if not isinstance(paths, (tuple, list)) or not paths:
        return None
    if not all(isinstance(p, str) and p for p in paths):
        return None
    return [os.path.normpath(p) for p in paths]


def count_edited_files(events: Iterable[Event]) -> Optional[int]:
    """Distinct normalised paths over the counted calls; None if any counted call has no usable path.

    Distinct, not per call: re-editing one file is still one file (J2-AC2).
    """
    seen: set = set()
    for e in events:
        if e.kind == "tool_call" and e.tool_kind in SIZE_TOOL_KINDS:
            paths = _counted_paths(e)
            if paths is None:
                return None
            seen.update(paths)
    return len(seen)


def size_class(run: Run) -> tuple:
    """(class name, distinct files edited), or (`size unknown`, None) when it cannot be determined.

    An unreadable line may have hidden an edit, so it makes the run unknown (AM1-ADR-2).
    """
    if run.unreadable_lines:
        return UNKNOWN_SIZE, None
    n = count_edited_files(run.events)
    if n is None:
        return UNKNOWN_SIZE, None
    for name, low, high in SIZE_CLASSES:
        if n >= low and (high is None or n <= high):
            return name, n


def is_probe(run: Run) -> bool:
    """A trial probe: the run's first inbound message has a line starting `PROBE:` (R23)."""
    text = _first_inbound_text(run)
    return isinstance(text, str) and bool(PROBE_RE.search(text))


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
    """`YYYY-MM-DD` as midnight UTC, or `YYYY-MM-DDTHH:MM:SSZ` in UTC. No other offset is accepted."""
    fmt = "%Y-%m-%dT%H:%M:%SZ" if "T" in text else "%Y-%m-%d"
    return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc)


def parse_until(text: str) -> dt.datetime:
    """`--until` takes the same two forms as `--since` (scorecard only)."""
    return parse_since(text)


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


def _verdict(name: str, medians: list, targets: dict, min_runs: int) -> tuple:
    """(suffix for the class line, met?) for one class under `--targets` (R22, J2-AC6).

    The median is compared as printed (one decimal), so the verdict never
    contradicts the number beside it.
    """
    if name not in targets:
        return " · report only", False
    if len(medians) < min_runs:
        return f" · not enough runs ({len(medians)}) — extend the trial for this class; not met", False
    median = round(statistics.median(medians) / 60, 1)
    target = targets[name]
    if median <= target:
        return f" · met (median {median:.1f} ≤ {target:g})", True
    return f" · NOT met (median {median:.1f} > {target:g})", False


def _size_block(agent_type: str, runs: list, targets: Optional[dict], min_runs: int) -> list:
    """The size-class lines for one engineer type (R41, M10, M10a)."""
    active = {id(r): categorise(r)["active"] for r in runs}
    by_class: dict = defaultdict(list)
    path_missing = unreadable = 0
    for r in runs:
        name, _ = size_class(r)
        if name == UNKNOWN_SIZE:
            # Exactly one reason per run, so the two reasons add up to the unknown count.
            if count_edited_files(r.events) is None:
                path_missing += 1
            else:
                unreadable += 1
        by_class[name].append(active[id(r)])
    lines = [f"{agent_type} — size classes (distinct files edited per run):"]
    met = 0
    for name, _, _ in SIZE_CLASSES:
        medians = by_class[name]
        line = f"  {name:<6} n={len(medians)}  " + (
            f"median {_minutes(statistics.median(medians))}" if medians else "no median"
        )
        if targets is not None:
            suffix, ok = _verdict(name, medians, targets, min_runs)
            line += suffix
            met += ok
        lines.append(line)
    unknown = len(by_class[UNKNOWN_SIZE])
    lines.append(f"  {UNKNOWN_SIZE} n={unknown}")
    lines.append(f"  {UNKNOWN_SIZE}: {unknown} (path missing: {path_missing} · unreadable lines: {unreadable})")
    values = list(active.values())
    lines.append(
        f"  all engineer runs n={len(values)}  mean {_minutes(sum(values) / len(values))}"
        f" · median {_minutes(statistics.median(values))}"
    )
    if targets is not None:
        verdict = "met" if met == len(JUDGED_CLASSES) else "NOT met"
        lines.append(f"  acceptance: {verdict} (met {met} of {len(JUDGED_CLASSES)} classes)")
    return lines


def size_report(runs: list, targets: Optional[dict] = None, min_runs: int = 3, include_probes: bool = False) -> str:
    """Per engineer type: runs per size class with medians, size unknown, overall mean and median,
    and with `targets` the per-class acceptance (R41, R22, R23). Paths are never printed (R39)."""
    engineer = [r for r in runs if r.events and r.agent_type in ENGINEER_TYPES]
    probes = [r for r in engineer if is_probe(r)]
    if include_probes:
        lines = [f"probe runs included (--include-probes, debugging only): {len(probes)}"]
    else:
        lines = [f"probe runs excluded: {len(probes)}"]
        engineer = [r for r in engineer if not is_probe(r)]
    if not engineer:
        return "\n".join(["size classes: no engineer runs in the window", *lines])
    shell_writes = sum(
        1
        for r in engineer
        if any(
            e.kind == "tool_call" and e.tool_kind == "shell" and isinstance(e.command, str)
            and SHELL_WRITE_RE.search(e.command)
            for e in r.events
        )
    )
    lines.append(f"runs with shell file writes (not counted in size): {shell_writes}")
    by_type: dict = defaultdict(list)
    for r in engineer:
        by_type[r.agent_type].append(r)
    for agent_type in sorted(by_type):
        lines.extend(_size_block(agent_type, by_type[agent_type], targets, min_runs))
    lines.append(SIZE_LIMITS)
    return "\n".join(lines)


def _targets(text: str) -> dict:
    """`small=15,medium=25,large=50`: a positive finite number of minutes for each judged class."""
    targets: dict = {}
    for part in text.split(","):
        name, sep, value = part.partition("=")
        name = name.strip()
        try:
            minutes = float(value)
        except ValueError:
            minutes = math.nan
        if not sep or name not in JUDGED_CLASSES or name in targets or not (math.isfinite(minutes) and minutes > 0):
            raise argparse.ArgumentTypeError(
                "expected small=<min>,medium=<min>,large=<min>, each a positive number, each once"
            )
        targets[name] = minutes
    if set(targets) != set(JUDGED_CLASSES):
        raise argparse.ArgumentTypeError("expected a target for each of small, medium and large")
    return targets


def _min_runs(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError("expected a whole number of runs, 1 or more")
    return value


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


# ---- The scorecard (SPEC-jarvis-coordinator-inc2-scorecard.md, R9–R10) ----------------
#
# M1–M7 for a window, from the same reader events as the time report. Owner messages
# and turn ends are marked by the reader (`Event.owner`, `Event.turn_end`); everything
# here counts neutral events only. Nothing from an event's text or paths is printed but
# a report slug that passes SLUG_RE.

#: The role agents whose briefs M6 reads and whose runs M3 may count.
ROLE_TYPES = ("pm", "ba-sa", "ai-engineer", "frontend-engineer", "reviewer", "qa", "frontend-qa")

#: The role agents whose report edits M3 counts.
REVIEW_TYPES = ("reviewer", "qa", "frontend-qa")

TIERS = ("tier 0", "tier 1", "tier 2", "untiered")

#: A field line: plain, bulleted, numbered or bold, read after NFKC (as the guard reads it).
_FIELD = r"^[ \t]*(?:(?:[-*]|\d+\.)[ \t]+)?(?:\*\*)?{}(?:\*\*)?[ \t]*:"

#: An exchange's tier: the first Jarvis text with a Tier field line whose value is 0, 1 or 2.
TIER_RE = re.compile(_FIELD.format("Tier") + r"(?:\*\*)?[ \t]*([012])", re.M)

#: M6: a brief carries a Tier field line and a Files field line. Presence only.
BRIEF_FIELD_RES = (re.compile(_FIELD.format("Tier"), re.M), re.compile(_FIELD.format("Files"), re.M))

#: M3: a review or QA report path, in any checkout (a worktree too). `\Z`, not `$`:
#: `$` also matches before a trailing newline.
REPORT_RE = re.compile(r"(?:^|/)doc/qa/(REVIEW|QA)-(.+)\.md\Z")

#: A slug is printed only when it is a plain label; anything else is UNPRINTABLE.
SLUG_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")

DEFAULT_MEMORY_DIR = Path(__file__).resolve().parents[1] / "doc" / "memory"

SC_METHOD = (
    "method: an exchange is one owner message and everything until the next one; it belongs to the "
    "window of its owner message, and events at or after --until are ignored; a turn end is one "
    "distinct response id that ended the turn; an exchange's tier is the first Tier line in Jarvis's "
    "text; a subagent run belongs to the window of its first event (its brief), unlike the time "
    "report, which uses the last"
)
SC_LIMITS = (
    "limits: M1 is an upper bound and treats one owner message as one task; an exchange with no "
    "Tier line in Jarvis's reply is untiered, even inside a tiered task; M2 reads the working memory "
    "folder, by date; M4's result is any tool result; M3 counts only runs that edit their report "
    "file; M6 checks presence only and is 100% by construction where the guard intercepts; M7 is "
    "not windowed; the transcripts the adapter keeps decide how far back any figure can go"
)


@dataclass(frozen=True)
class _Exchange:
    tier: str
    extra: int
    minutes: Optional[float]  # to the first turn end after a tool result; None = no result
    day: dt.date


def count_turn_ends(events: Iterable[Event]) -> int:
    """Turn ends are distinct response ids, as turns are (SC-AC3); one with no id counts once."""
    ids: set = set()
    no_id = 0
    for e in events:
        if e.kind == "model" and e.turn_end:
            if e.message_id is None:
                no_id += 1
            else:
                ids.add(e.message_id)
    return no_id + len(ids)


def _nfkc(text: object) -> str:
    return unicodedata.normalize("NFKC", text) if isinstance(text, str) else ""


def _tier(events: list) -> str:
    """The value of the first Tier line in Jarvis's text in the exchange, else `untiered`."""
    for e in events:
        if e.kind == "model":
            found = TIER_RE.search(_nfkc(e.text))
            if found:
                return f"tier {found.group(1)}"
    return "untiered"


def _minutes_to_result(events: list) -> Optional[float]:
    """Minutes from the owner message (events[0]) to the first turn end after a tool result."""
    seen_result = False
    for e in events[1:]:
        if e.kind == "tool_result":
            seen_result = True
        elif e.kind == "model" and e.turn_end and seen_result:
            return (e.t - events[0].t).total_seconds() / 60
    return None


def _exchanges(runs: list, since: dt.datetime, until: dt.datetime) -> list:
    exchanges = []
    for r in runs:
        events = [e for e in r.events if e.t < until]
        starts = [i for i, e in enumerate(events) if e.kind == "inbound" and e.owner]
        for n, start in enumerate(starts):
            if events[start].t < since:
                continue
            span = events[start : starts[n + 1] if n + 1 < len(starts) else len(events)]
            exchanges.append(
                _Exchange(
                    _tier(span),
                    max(0, count_turn_ends(span) - 1),
                    _minutes_to_result(span),
                    events[start].t.astimezone(dt.timezone.utc).date(),
                )
            )
    return exchanges


def _m1_lines(exchanges: list) -> list:
    lines = ["M1 extra Jarvis messages per owner message (upper bound: gate stops and owner decisions are not told apart)"]
    for tier in TIERS:
        mine = [x for x in exchanges if x.tier == tier]
        if not mine:
            lines.append(f"  {tier}: no exchanges")
            continue
        extra = sum(x.extra for x in mine)
        none = sum(1 for x in mine if not x.extra)
        lines.append(f"  {tier}: {len(mine)} exchanges · {extra} extra · mean {extra / len(mine):.2f} · {none} with none")
    return lines


def _m4_lines(exchanges: list) -> list:
    lines = ["M4 minutes from owner message to first reply after a tool result"]
    for tier in TIERS:
        mine = [x for x in exchanges if x.tier == tier]
        if not mine:
            lines.append(f"  {tier}: no exchanges")
            continue
        timed = [x.minutes for x in mine if x.minutes is not None]
        no_result = len(mine) - len(timed)
        if timed:
            lines.append(f"  {tier}: median {statistics.median(timed):.1f} min (n {len(timed)}) · no result: {no_result}")
        else:
            lines.append(f"  {tier}: no result: {no_result}")
    return lines


def _m3_lines(review_runs: list, until: dt.datetime) -> list:
    """Review and QA runs per report slug, each run once per slug and report kind it edited."""
    head = "M3 review and QA runs per report slug: "
    if not review_runs:
        return [head + "no review or QA runs"]
    counts: dict = defaultdict(Counter)
    no_report = 0
    for r in review_runs:
        found = set()
        for e in r.events:
            if e.t >= until or e.kind != "tool_call" or not isinstance(e.paths, (tuple, list)):
                continue
            for path in e.paths:
                match = REPORT_RE.search(path) if isinstance(path, str) else None
                if match:
                    slug = match.group(2)
                    found.add((slug if SLUG_RE.fullmatch(slug) else UNPRINTABLE, match.group(1)))
        no_report += not found
        for label, kind in found:
            counts[label][kind] += 1
    wrote_none = f"{no_report} {'run' if no_report == 1 else 'runs'} wrote no report"
    if not counts:
        return [head + "no report slugs · " + wrote_none]
    review = statistics.median(c["REVIEW"] for c in counts.values())
    qa = statistics.median(c["QA"] for c in counts.values())
    lines = [head + f"{len(counts)} slugs · review median {review:g} · QA median {qa:g} · " + wrote_none]
    lines.extend(f"  {label}: review {c['REVIEW']} · QA {c['QA']}" for label, c in sorted(counts.items()))
    return lines


def _m6_line(role_runs: list) -> str:
    head = "M6 role-agent briefs with a Tier: line and a Files: line: "
    if not role_runs:
        return head + "no role-agent briefs"
    full = sum(
        1 for r in role_runs if all(rx.search(_nfkc(_first_inbound_text(r))) for rx in BRIEF_FIELD_RES)
    )
    return head + f"{full} of {len(role_runs)}"


def _memory_lines(memory_dir: Path, until: dt.datetime) -> tuple:
    """(M2 lines, M7 lines) from correction_rate; one combined line when it cannot be measured."""
    if not Path(memory_dir).is_dir():
        return ["M2, M7: memory directory not found"], []
    import correction_rate  # noqa: PLC0415 — a sibling script, imported only when the scorecard runs

    date = (until - dt.timedelta(microseconds=1)).astimezone(dt.timezone.utc).date()
    try:
        m = correction_rate.measure(Path(memory_dir), date)
    except (OSError, ValueError):  # ValueError covers UnicodeDecodeError and a bad date: line
        return ["M2, M7: not measured (unreadable memory file)"], []
    last, prev = m["last"], m["prev"]
    trend = "down" if last < prev else "NOT down" if last > prev else "flat"
    days = correction_rate.WINDOW_DAYS
    return (
        [f"M2 owner corrections: {last} in the {days} days to {date} (previous {days}: {prev}, {trend})"],
        [f"M7 {len(m['unmechanised'])} lesson(s) since {correction_rate.MECHANISM_REQUIRED_FROM} with no mechanism"],
    )


def _utc(t: dt.datetime) -> str:
    return f"{t.astimezone(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"


def scorecard(runs: list, since: dt.datetime, until: dt.datetime, memory_dir: Path, reader_name: str) -> str:
    """The scorecard: M1–M7 and owner messages per day for [since, until). Counts only (R39)."""
    exchanges = _exchanges(runs, since, until)
    role_runs = [
        r for r in runs
        if r.agent_type in ROLE_TYPES and r.events and since <= r.events[0].t < until and not is_probe(r)
    ]
    m2, m7 = _memory_lines(memory_dir, until)
    days = Counter(x.day for x in exchanges)
    lines = [
        f"scorecard — window [{_utc(since)}, {_utc(until)}) · reader: {reader_name}"
        f" · unreadable lines: {sum(r.unreadable_lines for r in runs)}",
        *_m1_lines(exchanges),
        *m2,
        *_m3_lines([r for r in role_runs if r.agent_type in REVIEW_TYPES], until),
        *_m4_lines(exchanges),
        "M5 new-user setup time: not measured by this command (timed by hand, R12)",
        _m6_line(role_runs),
        *m7,
        "owner messages per day (UTC): "
        + (" · ".join(f"{day} {n}" for day, n in sorted(days.items())) or "none"),
        SC_METHOD,
        SC_LIMITS,
    ]
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
    parser.add_argument(
        "--since", type=parse_since, default=DEFAULT_SINCE, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ (default: all)"
    )
    parser.add_argument("--rework", action="store_true", help="add the rework share and causes")
    parser.add_argument("--qa-dir", type=Path, help="QA reports for rework causes (e.g. doc/qa)")
    parser.add_argument("--test-pattern", type=_test_pattern, help="extra regex for this project's test commands")
    parser.add_argument("--targets", type=_targets, help="judge size classes: small=15,medium=25,large=50 (minutes)")
    parser.add_argument("--min-runs", type=_min_runs, help="runs a class needs to be judged (default 3)")
    parser.add_argument("--include-probes", action="store_true", help="count PROBE: runs too (debugging only)")
    parser.add_argument("--scorecard", action="store_true", help="print M1–M7 for the window instead (runs alone)")
    parser.add_argument("--until", type=parse_until, help="scorecard window end, exclusive (default: now)")
    parser.add_argument("--memory-dir", type=Path, default=DEFAULT_MEMORY_DIR, help="memory folder for M2 and M7")
    args = parser.parse_args(argv)
    if args.scorecard and (args.rework or args.targets is not None or args.min_runs is not None or args.include_probes):
        raise _UsageError("--scorecard runs alone")
    if args.until is not None and not args.scorecard:
        raise _UsageError("--until needs --scorecard")
    until = args.until or dt.datetime.now(dt.timezone.utc)
    if args.scorecard and until <= args.since:
        raise _UsageError("--until must be later than --since")

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
    if args.scorecard:
        print(scorecard(runs, args.since, until, args.memory_dir, args.reader.name))
        return 0
    print(report(runs, args.since, args.reader.name, test_re))
    if any(r.events for r in runs):
        min_runs = 3 if args.min_runs is None else args.min_runs
        print(size_report(runs, args.targets, min_runs, args.include_probes))
    if args.rework:
        print(rework_report(runs, args.qa_dir, args.since))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
