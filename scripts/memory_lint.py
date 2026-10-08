#!/usr/bin/env python3
"""Lifecycle check for the project memory in `doc/memory/` (NORTH-STAR "รู้จักคุณ").

WHY THIS EXISTS. A memory that only grows stops working long before anyone
notices: the assistant loads the first N lines of its index and the newest
rulings — the ones that matter most — are the ones cut off. On the project
this framework came from, the index reached 253 lines against a 200-line load
limit, so 53 entries, including a ruling from four days earlier, were silently
invisible at every session start. Nothing reported it; the owner noticed by
having to repeat themselves. And because that memory lived in one tool's private
folder on one laptop, no other tool and no teammate could read it at all.

So memory lives in the repo, in plain markdown any tool can read, and this
script enforces the lifecycle the 2026 research on agent memory converges on:
admit with provenance, supersede instead of silently contradicting, prune
from the index, keep the index inside its load budget.

Rules (each is exit 1):

1. Every entry `doc/memory/<slug>.md` has frontmatter with `name`,
   `description`, `type` (user | feedback | project | reference), `status`
   (active | superseded), `date` (YYYY-MM-DD) and `source` (where it came
   from — a quote, a commit, an incident). An entry with no source cannot be
   re-checked, so it cannot be trusted.
2. `status: superseded` requires `superseded_by: <slug>` naming an existing
   entry that is itself `active` — a ruling that was replaced must say by what.
3. `INDEX.md` lists exactly the active entries — no superseded entry (it
   would be followed), no active entry missing (it would never be read).
4. `INDEX.md` stays within `INDEX_BUDGET` lines.
5. A `feedback` entry dated on or after `MECHANISM_REQUIRED_FROM` names the
   `mechanism` that now enforces the lesson — a repo path (hook, test, script,
   skill) that exists — or `none — <reason>`. A lesson kept only as memory works
   only when it is remembered; on the originating project corrections per day
   doubled from one month to the next while memory files grew to 260.

Plain stdlib, no AI required (RUNTIME-CONTRACT layer ๑).

**What this does NOT do:** it cannot tell whether an entry is still TRUE, only
whether it is well-formed and reachable. Deciding that a ruling is stale is
the human's call; this makes the decision visible and the result consistent.

Usage:
    python3 scripts/memory_lint.py
    MEMORY_DIR=/tmp/probe python3 scripts/memory_lint.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

#: Lines. Below the smallest load limit seen in practice (200), so the index is
#: never truncated by the tool that reads it, with room for a header.
INDEX_BUDGET = 150
INDEX_NAME = "INDEX.md"
#: Files in the memory folder that are about the memory, not entries in it.
NOT_ENTRIES = {INDEX_NAME, "README.md"}
REQUIRED = ("name", "description", "type", "status", "date", "source")
TYPES = {"user", "feedback", "project", "reference"}
STATUSES = {"active", "superseded"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LINK = re.compile(r"\]\(([^)]+\.md)\)")
#: Rule 5 starts here; older lessons are grandfathered rather than backfilled.
MECHANISM_REQUIRED_FROM = "2026-10-08"
_MECHANISM_NONE = re.compile(r"^none\s*[—-]\s*(.{10,})$", re.IGNORECASE)


def _dir() -> Path:
    default = Path(__file__).resolve().parents[1] / "doc" / "memory"
    return Path(os.environ.get("MEMORY_DIR", default))


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Flat `key: value` frontmatter between two `---` lines, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return None


def mechanism_problem(value: str, memory_dir: Path) -> str | None:
    """Why a feedback entry's `mechanism` is unacceptable, or None (rule 5)."""
    if not value:
        return "feedback entry has no `mechanism` — name the hook/test/skill path, or `none — <reason>`"
    if value.lower().startswith("none"):
        if _MECHANISM_NONE.match(value):
            return None
        return "`mechanism: none` needs `— <reason>` of at least 10 characters"
    repo_root = memory_dir.resolve().parents[1]
    target = value.split()[0].split("::")[0].split("#")[0]
    if (repo_root / target).exists():
        return None
    return f"mechanism `{target}` does not exist in the repo"


def check(memory_dir: Path) -> list[str]:
    """Every violation, as a human-readable line. Empty list = clean."""
    if not memory_dir.is_dir():
        return [f"{memory_dir}: memory directory missing"]
    errors: list[str] = []
    entries: dict[str, dict[str, str]] = {}
    for path in sorted(memory_dir.glob("*.md")):
        if path.name in NOT_ENTRIES:
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{path.name}: no frontmatter")
            continue
        entries[path.stem] = fm
        for key in REQUIRED:
            if not fm.get(key):
                errors.append(f"{path.name}: missing `{key}`")
        if fm.get("type") and fm["type"] not in TYPES:
            errors.append(f"{path.name}: type `{fm['type']}` not in {sorted(TYPES)}")
        if fm.get("status") and fm["status"] not in STATUSES:
            errors.append(f"{path.name}: status `{fm['status']}` not in {sorted(STATUSES)}")
        if fm.get("date") and not _DATE.match(fm["date"]):
            errors.append(f"{path.name}: date `{fm['date']}` is not YYYY-MM-DD")
        if fm.get("type") == "feedback" and fm.get("date", "") >= MECHANISM_REQUIRED_FROM:
            why = mechanism_problem(fm.get("mechanism", ""), memory_dir)
            if why:
                errors.append(f"{path.name}: {why}")

    for slug, fm in entries.items():
        if fm.get("status") != "superseded":
            continue
        successor = fm.get("superseded_by", "")
        if not successor:
            errors.append(f"{slug}.md: superseded but no `superseded_by`")
        elif successor not in entries:
            errors.append(f"{slug}.md: superseded_by `{successor}` does not exist")
        elif entries[successor].get("status") != "active":
            errors.append(f"{slug}.md: superseded_by `{successor}` is not active")

    index = memory_dir / INDEX_NAME
    if not index.is_file():
        errors.append(f"{INDEX_NAME}: missing")
        return errors
    index_lines = index.read_text(encoding="utf-8").splitlines()
    if len(index_lines) > INDEX_BUDGET:
        errors.append(
            f"{INDEX_NAME}: {len(index_lines)} lines, budget {INDEX_BUDGET} — "
            "supersede or archive entries; a cut-off index hides the newest rulings"
        )
    listed = {Path(m).stem for m in _LINK.findall("\n".join(index_lines))}
    active = {s for s, fm in entries.items() if fm.get("status") == "active"}
    for slug in sorted(listed - set(entries)):
        errors.append(f"{INDEX_NAME}: links `{slug}.md`, which does not exist")
    for slug in sorted((listed & set(entries)) - active):
        errors.append(f"{INDEX_NAME}: lists `{slug}.md`, which is not active")
    for slug in sorted(active - listed):
        errors.append(f"{INDEX_NAME}: active entry `{slug}.md` is not listed — it will never be read")
    return errors


def main() -> int:
    memory_dir = _dir()
    errors = check(memory_dir)
    for line in errors:
        print(f"MEMORY  {line}")
    print(f"memory: {len(errors)} problem(s) in {memory_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
