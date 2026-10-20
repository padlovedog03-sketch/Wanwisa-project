#!/usr/bin/env python3
"""The closed learning loop (SPEC-delegated-autonomy E-AC1, R18).

WHY THIS EXISTS. AGENTS.md §9 says a lesson must become a mechanism. Lessons
arrive two ways: QA sends work back with a rework cause, and the owner corrects
the assistant, which becomes a `feedback` memory. This report groups both over a
window and names each cause that recurred (two or more occurrences), with a
proposal stub. It proposes only: changing the mechanism set is always-human
item AH5, so every stub is marked for owner approval.

How causes are grouped:
- **QA rework.** The `Rework cause` column of FAIL reports in `doc/qa/QA-*.md`,
  parsed by the meter's own parser (`agent_time._qa_causes`) so the two reports
  can never disagree. Without verify-tiers H (no `agent_time.REWORK_CAUSES`) it
  prints `unavailable: rework causes not shipped`.
- **Owner corrections.** `type: feedback` memories dated in the window whose
  `mechanism:` is missing or `none`, which are lessons kept only as memory.
  They form one cause, `lesson-without-mechanism`. Memories carry no cause field,
  so this is the only grouping the data supports.

The window is inclusive: a report or memory dated exactly `--window` days ago
counts. Prints cause names, file names and counts only, never a memory's or
report's text (AGENTS.md §8). A report, not a gate: always exits 0.

Usage:
    learning_loop.py [--window 28] [--qa-dir doc/qa] [--memory-dir doc/memory]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STAMP = "owner approval required (AH5)"
_RECURRING = 2
_MEMORY_CAUSE = "lesson-without-mechanism"

_TYPE_FEEDBACK = re.compile(r"^\s*type:\s*feedback\s*$", re.MULTILINE)
_DATE = re.compile(r"^\s*date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_MECHANISM = re.compile(r"^\s*mechanism:\s*(\S.*?)\s*$", re.MULTILINE)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def qa_section(qa_dir: Path, since: dt.date) -> tuple[list[str], Counter]:
    """Report lines and the rework-cause counts in the window."""
    try:
        import agent_time

        rework_causes, qa_causes = agent_time.REWORK_CAUSES, agent_time._qa_causes
        since_utc = agent_time.parse_since(since.isoformat())
    except (ImportError, AttributeError):
        return ["unavailable: rework causes not shipped"], Counter()
    if not qa_dir.is_dir():
        return [f"QA directory not found: {qa_dir}"], Counter()
    # The meter's parser reads a whole directory and raises on one unreadable
    # file. Copy the readable reports into a scratch directory so one bad file
    # is counted instead of ending the run.
    unreadable = 0
    with tempfile.TemporaryDirectory() as scratch:
        readable = 0
        for path in sorted(qa_dir.glob("QA-*.md")):
            text = _read(path)
            if text is None:
                unreadable += 1
                continue
            (Path(scratch) / path.name).write_text(text, encoding="utf-8")
            readable += 1
        causes, unclassified, no_date, no_table = qa_causes(Path(scratch), since_utc)
    lines = [
        f"QA reports read: {readable} · unreadable: {unreadable} · no Date: {no_date}"
        f" · FAIL with no Defects table: {no_table} · unclassified defects: {unclassified}",
        "rework causes: " + " · ".join(f"{c} {causes[c]}" for c in rework_causes),
    ]
    return lines, Counter({c: causes[c] for c in rework_causes if causes[c]})


def memory_section(memory_dir: Path, since: dt.date, today: dt.date) -> tuple[list[str], list[str]]:
    """Report lines and the names of feedback memories in the window with no mechanism."""
    if not memory_dir.is_dir():
        return [f"memory directory not found: {memory_dir}"], []
    unreadable = no_date = in_window = 0
    unmechanised: list[str] = []
    for path in sorted(memory_dir.glob("*.md")):
        text = _read(path)
        if text is None:
            unreadable += 1
            continue
        parts = text.split("---", 2)
        front = parts[1] if text.startswith("---") and len(parts) == 3 else ""
        if not _TYPE_FEEDBACK.search(front):
            continue
        date = _DATE.search(front)
        if not date:
            no_date += 1
            continue
        try:
            born = dt.date.fromisoformat(date.group(1))
        except ValueError:
            no_date += 1
            continue
        if not since <= born <= today:
            continue
        in_window += 1
        mechanism = _MECHANISM.search(front)
        if mechanism is None or mechanism.group(1).lower().startswith("none"):
            unmechanised.append(path.name)
    lines = [
        f"feedback memories in window: {in_window} · with no mechanism: {len(unmechanised)}"
        f" · no date: {no_date} · memories unreadable: {unreadable}"
    ]
    return lines, unmechanised


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--window", type=int, default=28, help="days to look back (default 28)")
    parser.add_argument("--qa-dir", type=Path, default=_REPO_ROOT / "doc" / "qa")
    parser.add_argument("--memory-dir", type=Path, default=_REPO_ROOT / "doc" / "memory")
    args = parser.parse_args(argv)
    if args.window < 1:
        parser.error("--window must be at least 1")

    today = dt.date.today()
    since = today - dt.timedelta(days=args.window)
    print(f"learning-loop — window {args.window} days, since {since.isoformat()}")
    qa_lines, qa_counts = qa_section(args.qa_dir, since)
    memory_lines, unmechanised = memory_section(args.memory_dir, since, today)
    for line in qa_lines + memory_lines:
        print(line)

    recurring = [(cause, count, "QA rework") for cause, count in qa_counts.most_common() if count >= _RECURRING]
    if len(unmechanised) >= _RECURRING:
        recurring.append((_MEMORY_CAUSE, len(unmechanised), "feedback memories: " + ", ".join(unmechanised)))
    if not recurring:
        print(f"recurring causes: none in the window (a cause needs {_RECURRING} or more occurrences)")
        return 0
    print(f"recurring causes ({_RECURRING} or more occurrences):")
    for cause, count, origin in recurring:
        print(f"  {cause}: {count} ({origin})")
        print(f"    proposal for {cause}: a gate, test, script or skill change that catches it — {_STAMP}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
