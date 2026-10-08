#!/usr/bin/env python3
"""The assistant's one honest learning metric: how often the owner corrects it.

WHY THIS EXISTS. "Learns from mistakes" was a claim nobody measured. Every
correction becomes a `feedback` memory, so counting new feedback entries per
week is the correction rate. If it does not fall, the assistant is not
learning — it is only remembering, and memory that only grows stops being read.
On the originating project the rate doubled month over month (Sep ≈1.1/day,
Oct ≈2.2/day) while nobody was looking, which is why this prints itself at
session start instead of waiting to be run.

It also counts lessons since `MECHANISM_REQUIRED_FROM` that name no
`mechanism:` — lessons kept only as memory (see memory_lint.py rule 5).

A meter, not a gate: always exits 0.

Usage:
    correction_rate.py [--dir <memory dir>] [--brief]

Entry date: frontmatter `date:` when present, else the file's creation time
(STATED LIMIT: creation time moves if the directory is copied or restored).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

MECHANISM_REQUIRED_FROM = dt.date(2026, 10, 8)
WINDOW_DAYS = 7
_TYPE = re.compile(r"^\s*type:\s*feedback\s*$", re.MULTILINE)
_DATE = re.compile(r"^\s*date:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_MECHANISM = re.compile(r"^\s*mechanism:\s*\S", re.MULTILINE)


def _frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if text.startswith("---") and len(parts) == 3 else ""


def _born(path: Path, fm: str) -> dt.date:
    found = _DATE.search(fm)
    if found:
        return dt.date.fromisoformat(found.group(1))
    st = path.stat()
    return dt.date.fromtimestamp(getattr(st, "st_birthtime", st.st_mtime))


def measure(memory_dir: Path, today: dt.date) -> dict[str, object]:
    """Counts for the last window, the window before it, and unmechanised lessons."""
    last = prev = 0
    unmechanised: list[str] = []
    for path in sorted(memory_dir.glob("*.md")):
        fm = _frontmatter(path.read_text(encoding="utf-8"))
        if not _TYPE.search(fm):
            continue
        age = (today - _born(path, fm)).days
        if 0 <= age < WINDOW_DAYS:
            last += 1
        elif WINDOW_DAYS <= age < 2 * WINDOW_DAYS:
            prev += 1
        if _born(path, fm) >= MECHANISM_REQUIRED_FROM and not _MECHANISM.search(fm):
            unmechanised.append(path.name)
    return {"last": last, "prev": prev, "unmechanised": unmechanised}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    default = Path(__file__).resolve().parents[1] / "doc" / "memory"
    parser.add_argument("--dir", type=Path, default=Path(os.environ.get("MEMORY_DIR", default)))
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args(argv)
    if not args.dir.is_dir():
        print(f"correction-rate: memory directory not found: {args.dir}")
        return 0
    m = measure(args.dir, dt.date.today())
    trend = "down" if m["last"] < m["prev"] else "NOT down" if m["last"] > m["prev"] else "flat"
    print(
        f"correction-rate: {m['last']} owner corrections in the last {WINDOW_DAYS} days "
        f"(previous {WINDOW_DAYS}: {m['prev']}, {trend}) · "
        f"{len(m['unmechanised'])} lesson(s) since {MECHANISM_REQUIRED_FROM} with no mechanism"
    )
    if not args.brief:
        for name in m["unmechanised"]:
            print(f"  no mechanism: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
