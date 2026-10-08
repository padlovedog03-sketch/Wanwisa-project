#!/usr/bin/env python3
"""commit-msg gate: a `fix` commit must stage a test change (risk tier 0).

WHY THIS EXISTS. Tier 0 (AGENTS.md, risk tiers) lets a bugfix skip the spec
and the per-stage approvals. What it trades them for is a test that reproduces
the bug. Without a check, "a bugfix carries its test" is prose, and prose held
on the days someone remembered it: on the originating project, 26 of 319 `fix`
commits in one month shipped with no test change at all.

Rule: a commit whose subject starts with `fix` (`fix:`, `fix(scope):`, `fix!:`)
must stage at least one path under a test directory, unless the message
carries a `No-Test: <reason>` trailer of at least 10 characters — a docs-only
or infra-only fix is legitimate, but the reason becomes visible in history.

STATED LIMIT: this checks that a test file changed, not that the test was red
before the fix. Red-first stays a reported claim (paste the red run in the
hand-off). `git commit --no-verify` skips this hook; CI can run the same
script over a range with `--range`.

Usage:
    check_fix_has_test.py <commit-msg-file>          # as a commit-msg hook
    check_fix_has_test.py --range origin/main..HEAD  # in CI
"""

from __future__ import annotations

import re
import subprocess
import sys

#: Directories that count as "a test changed". Adjust per project.
TEST_DIRS = ("tests/",)
#: Same 10-character floor the spawn gate uses for its override reason.
MIN_REASON_CHARS = 10
_FIX_SUBJECT = re.compile(r"^fix(\([^)]*\))?!?:", re.IGNORECASE)
_NO_TEST = re.compile(r"^No-Test:[ \t]*(.*)$", re.MULTILINE | re.IGNORECASE)


def violation(message: str, paths: list[str]) -> str | None:
    """Return why this commit is refused, or None when it may proceed."""
    lines = [ln for ln in message.splitlines() if not ln.startswith("#")]
    subject = lines[0].strip() if lines else ""
    if not _FIX_SUBJECT.match(subject):
        return None
    if any(p.startswith(TEST_DIRS) for p in paths):
        return None
    trailer = _NO_TEST.search("\n".join(lines))
    if trailer and len(trailer.group(1).strip()) >= MIN_REASON_CHARS:
        return None
    if trailer:
        return f"`No-Test:` needs a reason of at least {MIN_REASON_CHARS} characters."
    return (
        f"`{subject}` is a fix but stages no change under {', '.join(TEST_DIRS)}.\n"
        "Tier 0 trades the spec for a test that reproduces the bug — add it, or add a\n"
        "`No-Test: <reason>` trailer if this fix genuinely cannot carry one (docs, infra)."
    )


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main(argv: list[str]) -> int:
    """Check one commit message (hook mode) or every commit in a range (CI mode)."""
    if len(argv) == 3 and argv[1] == "--range":
        failures = []
        for sha in _git("rev-list", "--no-merges", argv[2]).split():
            message = _git("log", "-1", "--format=%B", sha)
            paths = _git("show", "--name-only", "--format=", sha).split()
            why = violation(message, paths)
            if why:
                failures.append(f"{sha[:10]}: {why}")
        for f in failures:
            print(f"check_fix_has_test: FAIL {f}")
        return 1 if failures else 0
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        message = fh.read()
    paths = _git("diff", "--cached", "--name-only").split()
    why = violation(message, paths)
    if why:
        print(f"check_fix_has_test: blocked — {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
