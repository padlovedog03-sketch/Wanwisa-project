"""`guard_bash.py` rule R26 — no hand-written polling loops (SPEC-verify-tiers-merge-gate, increment G).

WHY. An agent that launched work in the background and then writes
`until grep -q passed out.log; do sleep 10; done` burns its own time and a model
turn per wake-up, while the harness would have told it when the work ended. The
meter (R37) measured 2.4 min/run of exactly this. The rule refuses the common
loop-plus-sleep shapes at the moment they are typed, and `ALLOW_POLL=1;` at the
head of the command is the visible escape for a loop that is genuinely not a wait.

Declared limits (doc/framework/ADAPTERS.md): a loop inside `bash -c "…"`, a
script file, a heredoc fed to a shell, or another language's sleep loop is not
seen. That is a ruling (doc/memory/ease-of-use-over-strictness.md), not a gap
waiting to be chased.

Run: `python3 -m pytest tests/hooks -q -p no:cacheprovider`
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from test_guard_bash_matrix import MUST_ALLOW

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_bash.py"
_ALLOW = 0
_BLOCK = 2


def _run(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=payload, capture_output=True, text=True, cwd=cwd
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True
    )


@pytest.fixture(params=["clean", "dirty"])
def repo(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """R26 does not depend on tree state, so every case runs on both."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "f.txt").write_text("v1", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    if request.param == "dirty":
        (tmp_path / "f.txt").write_text("v2", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def dirty_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / "f.txt").write_text("v1", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    (tmp_path / "f.txt").write_text("v2", encoding="utf-8")
    return tmp_path


# ---- G-AC1 (RED-FIRST): the polling shapes the spec names are refused ---------------

SPEC_LOOPS = [
    "until grep -q passed out.log; do sleep 10; done",
    "while true; do tail -1 x; sleep 30; done",
    "for i in $(seq 20); do cat s; sleep 5; done",
    "while ! test -f done.flag; do sleep 2; done",
]

# The same shapes spelled the other ways a shell accepts, from the brief's hostile list.
HOSTILE_LOOPS = [
    # newlines instead of `;`
    "until grep -q passed out.log\ndo\n  sleep 10\ndone",
    "while true\ndo\n  tail -1 x\n  sleep 30\ndone",
    # `&&` inside the body
    "until grep -q passed out.log; do echo waiting && sleep 10; done",
    "while true; do test -f x && break; sleep 5; done",
    # sleep inside a command substitution
    "while true; do out=$(sleep 5; cat s); done",
    "until [ -f done ]; do x=`sleep 3`; done",
    # the loop condition itself is the wait — a common idiom
    "while sleep 5; do curl -s localhost:8000/health; done",
    # an absolute path, an env prefix, a wrapper in front of sleep
    "until test -f x; do /bin/sleep 2; done",
    "until true; do FOO=1 sleep 1; done",
    "while true; do env sleep 1; done",
    # nested in another construct, or after a pipe
    "if true; then while true; do sleep 1; done; fi",
    "{ while true; do sleep 1; done; }",
    "seq 5 | while read i; do sleep 1; done",
    "cd /tmp && until test -f x; do sleep 1; done",
    "time until test -f x; do sleep 1; done",
    # the escape hatch for the OTHER rule does not apply here (G-AC3)
    "ALLOW_DESTRUCTIVE=1; until grep -q passed out.log; do sleep 10; done",
    "ALLOW_DESTRUCTIVE=1 ; while true; do sleep 5; done",
]


@pytest.mark.parametrize("command", SPEC_LOOPS + HOSTILE_LOOPS)
def test_a_hand_written_polling_loop_is_refused(command: str, repo: Path) -> None:
    """G-AC1, G-AC3."""
    result = _run(command, repo)
    assert result.returncode == _BLOCK, f"exit {result.returncode} for {command!r}"


@pytest.mark.parametrize("command", SPEC_LOOPS)
def test_the_refusal_names_the_rule_and_tells_the_agent_what_to_do(command: str, repo: Path) -> None:
    """G-AC1: the message is the fix, not just the no."""
    err = _run(command, repo).stderr
    assert "rule R26" in err
    assert "hand-written polling loop" in err
    assert "end your turn or do independent work until the completion notification" in err
    assert "ALLOW_POLL=1;" in err


def test_allow_destructive_without_separator_is_still_refused(repo: Path) -> None:
    """G-AC3: `ALLOW_DESTRUCTIVE=1` waives A1' only, in any spelling."""
    command = "ALLOW_DESTRUCTIVE=1 sleep 1; while true; do sleep 1; done"
    assert _run(command, repo).returncode == _BLOCK


# ---- G-AC2: ordinary work is never blocked --------------------------------------------

NOT_POLLING = [
    "while read l; do echo $l; done < f",
    "for f in *.py; do wc -l $f; done",
    'grep -rn "while true; do sleep 1; done" .',
    "cat <<'EOF' > notes.md\nuntil grep -q passed out.log; do sleep 10; done\nEOF",
    "python3 - <<PY\nwhile True:\n    pass\n# while true; do sleep 1; done\nPY",
    "sleep 60 && cat out.log",
    # a quoted loop is data
    "echo 'until true; do sleep 1; done'",
    "git commit -m \"docs: never write while true; do sleep 1; done\"",
    # a loop and a sleep that are NOT the same construct
    "for f in *.py; do wc -l $f; done; sleep 2",
    "sleep 1; for f in a b; do echo $f; done",
    # words that merely contain the keywords
    "fortune; sleep 1",
    "./while.sh && sleeper 5",
    "for i in 1 2 3; do echo $i; done && sleep 2 && cat x",
]


@pytest.mark.parametrize("command", NOT_POLLING + MUST_ALLOW)
def test_ordinary_work_is_not_refused(command: str, repo: Path) -> None:
    """G-AC2, including every MUST_ALLOW entry from the matrix (imported, so it tracks additions)."""
    result = _run(command, repo)
    assert result.returncode == _ALLOW, f"exit {result.returncode} for {command!r}: {result.stderr}"


# ---- G-AC7: the head-position override ------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "ALLOW_POLL=1; until grep -q passed out.log; do sleep 10; done",
        "FOO=bar ALLOW_POLL=1; while true; do sleep 5; done",
        "ALLOW_POLL=1\nwhile true; do sleep 5; done",
    ],
)
def test_allow_poll_at_the_head_waives_r26(command: str, repo: Path) -> None:
    """G-AC7."""
    assert _run(command, repo).returncode == _ALLOW


def test_allow_poll_does_not_waive_the_destructive_rule(dirty_repo: Path) -> None:
    """G-AC7: each override waives its own rule only."""
    result = _run("ALLOW_POLL=1; git reset --hard", dirty_repo)
    assert result.returncode == _BLOCK
    assert "rule A1'" in result.stderr


# ---- G-AC8 (RED-FIRST): the override anywhere else does not count ---------------------


@pytest.mark.parametrize(
    "command",
    [
        "echo ALLOW_POLL=1 && until true; do sleep 1; done",
        "until true; do ALLOW_POLL=1 sleep 1; done",
        "until true; do sleep 1; done # ALLOW_POLL=1",
        "echo 'ALLOW_POLL=1' ; while true; do sleep 1; done",
        # near-misses of the real spelling
        "ALLOW_POLL=10; while true; do sleep 1; done",
        "ALLOW_POLL=0; while true; do sleep 1; done",
        "'ALLOW_POLL=1'; while true; do sleep 1; done",
    ],
)
def test_allow_poll_outside_the_head_does_not_waive_r26(command: str, repo: Path) -> None:
    """G-AC8."""
    assert _run(command, repo).returncode == _BLOCK


# ---- hostile input never crashes the guard --------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "do",
        "done",
        "while",
        "{",
        "do\n\n\ndone",
        "$(",
        "while true; do sleep",
        "until 'unclosed; do sleep 1; done",
        'while "x; do sleep 1',
        "cat <<EOF\nEOF",
        "cat <<EOF",
        ";;;&&||",
        "ALLOW_POLL=1;",
        "\x00 while \x00 sleep",
        "while " * 2000 + "sleep 1",
    ],
)
def test_malformed_shell_never_crashes_the_guard(command: str, tmp_path: Path) -> None:
    result = _run(command, tmp_path)
    assert result.returncode in (_ALLOW, _BLOCK), result.stderr
    assert "Traceback" not in result.stderr
