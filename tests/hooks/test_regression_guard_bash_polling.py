"""QA regression tests for `guard_bash.py` rule R26 (SPEC-verify-tiers-merge-gate, increment G).

WHY. The engineer's suite covers the spec's literal cases. These pin what QA found
by running about 2,200 real Bash commands from this repo's own session logs, and
by probing the head-only override in positions the suite did not list:

* the real shapes the guard refuses: one wait on a background output file, and a
  repeat-with-sleep race harness that matches G-AC1's `for … seq …; sleep` shape.
  The harness is refused bare and runs with the `ALLOW_POLL=1;` escape (G-AC7);
* `ALLOW_POLL=1` placed after a command, inside a subshell, behind `export`, or
  in lower case is not the head override (G-AC8);
* a loop that has already closed (`done | …`, `done 2>&1`, nested `done; done`)
  followed by a sleep is ordinary work (G-AC2).

Paths in the fixtures are placeholders; the guard judges shape, not paths.

Run: `python3 -m pytest tests/hooks/test_regression_guard_bash_polling.py -q -p no:cacheprovider`
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_bash.py"
_ALLOW = 0
_BLOCK = 2

# Shapes taken from real session logs, with paths replaced by placeholders.
REAL_BACKGROUND_WAIT = (
    "until [ -s /tmp/<user>/tasks/job.output ]; do sleep 5; done; "
    'tail -40 /tmp/<user>/tasks/job.output | grep -E "FAILED|passed|failed"'
)
REAL_RACE_HARNESS = (
    "S=/tmp/<user>/scratch; stale=0; for i in $(seq 1 20); do d=$S/racy$i; "
    'rm -rf $d; mkdir -p $d; cd $d; git init -q; echo "count 4" > f; git add f; '
    'echo "count 5" > f; sleep 1.1; c=$(cat f); '
    '[ "$c" != "count 5" ] && stale=$((stale+1)); done; echo "stale: $stale/20"'
)


def _exit_code(command: str, cwd: Path) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=payload, capture_output=True, text=True, cwd=cwd
    ).returncode


@pytest.mark.parametrize("command", [REAL_BACKGROUND_WAIT, REAL_RACE_HARNESS])
def test_regression_real_loop_with_sleep_shapes_are_refused(command: str, tmp_path: Path) -> None:
    """G-AC1 on shapes agents actually typed in this repo."""
    assert _exit_code(command, tmp_path) == _BLOCK


def test_regression_the_race_harness_runs_with_the_head_override(tmp_path: Path) -> None:
    """G-AC7: a loop that is genuinely not a wait has a visible way through."""
    assert _exit_code("ALLOW_POLL=1; " + REAL_RACE_HARNESS, tmp_path) == _ALLOW


_LOOP = "until true; do sleep 1; done"


@pytest.mark.parametrize(
    "command",
    [
        f"cd /x; ALLOW_POLL=1; {_LOOP}",
        f"export ALLOW_POLL=1; {_LOOP}",
        f"(ALLOW_POLL=1; {_LOOP})",
        f"allow_poll=1; {_LOOP}",
        f"ALLOW_DESTRUCTIVE=1 {_LOOP}",
    ],
)
def test_regression_allow_poll_off_the_head_does_not_waive_r26(command: str, tmp_path: Path) -> None:
    """G-AC8 (and G-AC3 for the other rule's override) in positions the suite did not list."""
    assert _exit_code(command, tmp_path) == _BLOCK


@pytest.mark.parametrize(
    "command",
    [
        "for f in a b; do echo $f; done | sort; sleep 1",
        "for f in a b; do echo $f; done 2>&1; sleep 1",
        "for a in 1; do for b in 2; do echo; done; done; sleep 1",
        'for c in "a \\"b"; do echo "$c"; done; sleep 1',
    ],
)
def test_regression_a_sleep_after_a_closed_loop_is_not_refused(command: str, tmp_path: Path) -> None:
    """G-AC2: the loop has ended before the sleep runs."""
    assert _exit_code(command, tmp_path) == _ALLOW
