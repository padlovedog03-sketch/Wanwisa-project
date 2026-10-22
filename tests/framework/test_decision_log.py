"""The decision log: `autonomy.py log` and `autonomy.py verify-log` (row 5, increment 2).

SPEC-delegated-autonomy-am2-task-orders-scope.md AM2-AC2 (replaces C-AC1 and
C-AC2 for row 5: a plain append-only JSONL log, no hash chain) and
SPEC-delegated-autonomy.md F-AC2 (every `approval`, `decision`, `provisional`
or `merge` entry carries a one-action `reverse`).

Every case runs the CLI as a subprocess with its cwd in a throwaway git repo,
`HOME` and `APPROVAL_LOG` pointed into `tmp_path`: the real registry is never
read or written.

Run: `python3 -m pytest tests/framework/test_decision_log.py -q`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOG = "doc/decisions/decision-log.jsonl"
_REVERSE_MESSAGE = "reverse: missing or not one action"
_IDENTIFIER_MESSAGE = "looks like an identifier — describe the shape, not the value"
_REQUIRED = ("id", "ts", "project", "kind", "class", "under", "artifact", "options", "choice", "why", "reverse")


def _entry(**changes: object) -> dict:
    entry: dict = {
        "id": "d-2026-10-22-0001",
        "ts": "2026-10-22T09:00:00+07:00",
        "project": "p",
        "kind": "decision",
        "class": "tier-1",
        "under": "order order-p-first-2026-10-22",
        "artifact": "doc/specs/SPEC-p.md",
        "options": ["split the table", "keep one table"],
        "choice": "split the table",
        "why": "smaller change",
        "reverse": "none: nothing applied yet",
    }
    entry.update(changes)
    return entry


def _env(tmp_path: Path) -> dict[str, str]:
    registry = tmp_path / "registry.jsonl"
    registry.touch()
    return {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "APPROVAL_LOG": str(registry),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    (path / "scripts").mkdir(parents=True)
    for name in ("autonomy.py", "verify_approvals.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, path / "scripts" / name)
    env = _env(tmp_path)
    subprocess.run(["git", "init", "-q", "-b", "feature/x"], cwd=path, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=path, check=True, env=env)
    return path


def _cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "scripts/autonomy.py", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=_env(repo.parent),
    )


def _log(repo: Path, entry: object) -> subprocess.CompletedProcess[str]:
    return _cli(repo, "log", "--entry", entry if isinstance(entry, str) else json.dumps(entry))


def _lines(repo: Path) -> list[str]:
    path = repo / _LOG
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


# --------------------------------------------------------------------------- AM2-AC2: the writer


def test_a_valid_entry_is_appended_as_one_json_line_with_no_prev(repo: Path) -> None:
    first = _log(repo, _entry())
    assert first.returncode == 0, first.stderr
    second = _log(repo, _entry(id="d-2026-10-22-0002", choice="keep one table"))
    assert second.returncode == 0, second.stderr
    lines = _lines(repo)
    assert len(lines) == 2
    assert json.loads(lines[0]) == _entry()
    assert json.loads(lines[1])["id"] == "d-2026-10-22-0002"
    assert "prev" not in json.loads(lines[0]), "row 5 ships no hash chain (AM2-ADR-2)"
    assert (repo / _LOG).read_bytes().endswith(b"\n")


@pytest.mark.parametrize("field", _REQUIRED)
def test_an_entry_lacking_a_required_field_is_refused_naming_it(repo: Path, field: str) -> None:
    entry = _entry()
    del entry[field]
    result = _log(repo, entry)
    assert result.returncode == 2, result.stderr
    expected = _REVERSE_MESSAGE if field == "reverse" else f"missing field: {field}"
    assert expected in result.stderr
    assert "Traceback" not in result.stderr
    assert _lines(repo) == [], "a refused entry was written"


def test_a_non_decision_kind_still_needs_a_reverse(repo: Path) -> None:
    entry = _entry(kind="ask")
    del entry["reverse"]
    result = _log(repo, entry)
    assert result.returncode == 2
    assert "missing field: reverse" in result.stderr


@pytest.mark.parametrize("field", ["why", "choice", "options"])
def test_a_free_text_field_holding_13_digits_is_refused(repo: Path, field: str) -> None:
    value = "customer 1234567890123 asked"
    result = _log(repo, _entry(**{field: [value] if field == "options" else value}))
    assert result.returncode == 2, result.stderr
    assert f"{field}: {_IDENTIFIER_MESSAGE}" in result.stderr
    assert "1234567890123" not in result.stderr, "the refusal echoed the identifier it refuses"
    assert _lines(repo) == []


def test_twelve_digits_and_digit_runs_outside_free_text_pass(repo: Path) -> None:
    """The shape is 13 or more digits in free text. `ts` (epoch millis is 13
    digits) and the sha inside `reverse` are not free text."""
    result = _log(
        repo,
        _entry(why="order 123456789012 lines", ts="1761123456789", reverse="revert 1234567890123456abc"),
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "raw",
    ["not json", "[1, 2]", json.dumps(_entry(options="one string")), json.dumps(_entry(choice=7))],
    ids=["not-json", "a-list", "options-not-a-list", "choice-not-text"],
)
def test_malformed_input_exits_2_without_a_traceback(repo: Path, raw: str) -> None:
    result = _log(repo, raw)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert _lines(repo) == []


# --------------------------------------------------------------------------- F-AC2: one-action reverse

_DECIDING_KINDS = ("approval", "decision", "provisional", "merge")
_GOOD_REVERSES = (
    "revert 0a1b2c3",
    "revert 0123456789abcdef0123456789abcdef01234567",
    "delete branch feature/x",
    "restore doc/specs/SPEC-p.md from 0a1b2c3",
    "remove stamp doc/specs/SPEC-p.md",
    "none: nothing applied yet",
)
_BAD_REVERSES = (
    "",
    "undo it",
    "revert",
    "revert not-a-sha",
    "revert 0a1b2c3; revert 4d5e6f7",
    "revert 0a1b2c3 && delete branch x",
    "revert 0a1b2c3\nrevert 4d5e6f7",
    "delete branch a b",
    "restore doc/x.md from",
    "remove stamp",
    "none:",
    "none:   ",
    "none: two\nlines",
)


@pytest.mark.parametrize("kind", _DECIDING_KINDS)
@pytest.mark.parametrize("reverse", _GOOD_REVERSES)
def test_each_one_action_reverse_is_accepted(repo: Path, kind: str, reverse: str) -> None:
    result = _log(repo, _entry(kind=kind, reverse=reverse))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("kind", _DECIDING_KINDS)
@pytest.mark.parametrize("reverse", _BAD_REVERSES)
def test_a_reverse_that_is_not_one_action_is_refused(repo: Path, kind: str, reverse: str) -> None:
    result = _log(repo, _entry(kind=kind, reverse=reverse))
    assert result.returncode == 2, f"{reverse!r} accepted for {kind}"
    assert _REVERSE_MESSAGE in result.stderr
    assert _lines(repo) == []


@pytest.mark.parametrize("kind", _DECIDING_KINDS)
def test_a_missing_reverse_on_a_deciding_kind_gets_the_f_ac2_message(repo: Path, kind: str) -> None:
    entry = _entry(kind=kind)
    del entry["reverse"]
    result = _log(repo, entry)
    assert result.returncode == 2
    assert _REVERSE_MESSAGE in result.stderr


def test_an_answer_entry_takes_none_as_its_reverse(repo: Path) -> None:
    """AM2 clarification: the coordinator writes `kind: answer` with
    `reverse: none: <reason>` when it relays the owner's reply."""
    result = _log(repo, _entry(kind="answer", target="d-2026-10-22-0001", reverse="none: an answer changes nothing"))
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------- AM2-AC2: verify-log --append-only


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=_env(repo.parent)
    ).stdout.strip()


def _commit_log(repo: Path, lines: list[str], message: str) -> None:
    path = repo / _LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


_BASE_LINES = ['{"id": "a"}', '{"id": "b"}', '{"id": "c"}']


@pytest.fixture
def logged(repo: Path) -> tuple[Path, str]:
    """A repo whose base commit holds three log lines; returns (repo, base sha)."""
    _commit_log(repo, _BASE_LINES, "base log")
    return repo, _git(repo, "rev-parse", "HEAD")


def _verify(repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    return _cli(repo, "verify-log", "--append-only", base)


def test_lines_added_at_the_end_are_green(logged: tuple[Path, str]) -> None:
    repo, base = logged
    _commit_log(repo, [*_BASE_LINES, '{"id": "d"}', '{"id": "e"}'], "append")
    result = _verify(repo, base)
    assert result.returncode == 0, result.stderr


def test_no_change_is_green(logged: tuple[Path, str]) -> None:
    repo, base = logged
    assert _verify(repo, base).returncode == 0


def test_a_log_first_added_after_the_base_is_green(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit_log(repo, ['{"id": "a"}'], "first log")
    result = _verify(repo, base)
    assert result.returncode == 0, result.stderr


def test_no_log_on_either_side_is_green(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    assert _verify(repo, base).returncode == 0


@pytest.mark.parametrize(
    ("planted", "line"),
    [
        (['{"id": "a"}', '{"id": "B"}', '{"id": "c"}', '{"id": "d"}'], 2),  # an earlier line edited
        (['{"id": "a"}', '{"id": "c"}', '{"id": "d"}'], 2),  # a line deleted
        (['{"id": "b"}', '{"id": "a"}', '{"id": "c"}'], 1),  # two lines swapped
        (['{"id": "a"}', '{"id": "x"}', '{"id": "b"}', '{"id": "c"}'], 2),  # inserted before the end
        ([], 1),  # the log emptied
    ],
    ids=["edited", "deleted", "swapped", "inserted-before-end", "emptied"],
)
def test_a_planted_tamper_is_red_naming_the_line_then_green_when_reverted(
    logged: tuple[Path, str], planted: list[str], line: int
) -> None:
    repo, base = logged
    _commit_log(repo, planted, "tamper")
    red = _verify(repo, base)
    assert red.returncode == 1, f"tamper passed: {red.stdout}{red.stderr}"
    assert f"line {line}" in red.stderr, red.stderr
    _commit_log(repo, [*_BASE_LINES, '{"id": "d"}'], "revert the tamper")
    green = _verify(repo, base)
    assert green.returncode == 0, green.stderr


def test_a_deleted_log_is_red(logged: tuple[Path, str]) -> None:
    repo, base = logged
    _git(repo, "rm", "-q", _LOG)
    _git(repo, "commit", "-q", "-m", "drop the log")
    result = _verify(repo, base)
    assert result.returncode == 1
    assert "line 1" in result.stderr


def test_an_unknown_base_fails_closed(logged: tuple[Path, str]) -> None:
    """A base git cannot resolve must not read as 'no log at the base' and go green."""
    repo, _ = logged
    result = _verify(repo, "no-such-ref")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "no-such-ref" in result.stderr


def test_the_check_reads_head_not_the_worktree(logged: tuple[Path, str]) -> None:
    repo, base = logged
    (repo / _LOG).write_text('{"id": "edited, not committed"}\n', encoding="utf-8")
    assert _verify(repo, base).returncode == 0
