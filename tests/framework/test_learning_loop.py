"""`scripts/learning_loop.py` — SPEC-delegated-autonomy E-AC1 (R18).

The loop groups QA rework causes and feedback memories in a window into
recurring causes (two or more occurrences) and prints a proposal stub for each,
marked for owner approval. It is a report: it always exits 0, never crashes on
an odd file, and prints names and counts only — never a memory's text, which
could hold personal data (AGENTS.md §8).

Every scenario runs on temporary directories, never on this repo's own
`doc/qa/` or `doc/memory/`.

Run: `python3 -m pytest tests/framework/test_learning_loop.py -q`
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "learning_loop.py"
_STAMP = "owner approval required (AH5)"
_SECRET = "1101700203451"  # a 13-digit ID shape: must never reach stdout

_TODAY = dt.date.today()


def _day(days_ago: int) -> str:
    return (_TODAY - dt.timedelta(days=days_ago)).isoformat()


def _qa_report(days_ago: int, *causes: str, verdict: str = "FAIL") -> str:
    rows = "".join(f"| High | broke {i} | x.py:1 | ai-engineer | {c} |\n" for i, c in enumerate(causes))
    return (
        "# QA Report: probe\n\nStatus: Draft\nUpstream: doc/specs/SPEC-x.md\n"
        f"Date: {_day(days_ago)}\n\n## Verdict: {verdict}\n\n## Defects (if FAIL)\n\n"
        "| Severity | Description | Where | Suggested owner | Rework cause |\n|---|---|---|---|---|\n"
        + rows
        + "\n## Edge Cases Probed\n"
    )


def _memory(days_ago: int, *, kind: str = "feedback", mechanism: str | None = "none — memory only") -> str:
    lines = [
        "---",
        "name: probe",
        f"description: lesson about customer {_SECRET}",
        f"type: {kind}",
        "status: active",
        f"date: {_day(days_ago)}",
        f"source: owner said {_SECRET}",
    ]
    if mechanism is not None:
        lines.append(f"mechanism: {mechanism}")
    return "\n".join(lines) + f"\n---\n\nBody mentions {_SECRET}.\n"


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    qa, memory = tmp_path / "qa", tmp_path / "memory"
    qa.mkdir()
    memory.mkdir()
    return qa, memory


def _run(qa: Path, memory: Path, *extra: str, script: Path = _SCRIPT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--qa-dir", str(qa), "--memory-dir", str(memory), *extra],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_a_cause_seen_twice_gets_a_proposal_stub_for_the_owner(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-a.md").write_text(_qa_report(3, "test-gap"), encoding="utf-8")
    (qa / "QA-b.md").write_text(_qa_report(5, "test-gap", "regression"), encoding="utf-8")

    result = _run(qa, memory, "--window", "28")

    assert result.returncode == 0, result.stderr
    assert "test-gap: 2" in result.stdout
    stub = next(line for line in result.stdout.splitlines() if "proposal" in line and "test-gap" in line)
    assert _STAMP in stub
    assert "regression" not in result.stdout.split("recurring causes", 1)[1], result.stdout


def test_a_cause_seen_once_gets_no_stub(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-a.md").write_text(_qa_report(3, "missed-ac"), encoding="utf-8")

    result = _run(qa, memory)

    assert result.returncode == 0
    assert _STAMP not in result.stdout
    assert "recurring causes: none" in result.stdout


def test_reports_outside_the_window_are_not_counted(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-old.md").write_text(_qa_report(29, "test-gap", "test-gap"), encoding="utf-8")
    (qa / "QA-edge.md").write_text(_qa_report(28, "spec-defect"), encoding="utf-8")
    (qa / "QA-new.md").write_text(_qa_report(0, "spec-defect"), encoding="utf-8")

    result = _run(qa, memory, "--window", "28")

    assert "test-gap" not in result.stdout.split("recurring causes", 1)[1]
    # The window edge is inclusive: a report dated exactly 28 days ago counts.
    assert "spec-defect: 2" in result.stdout


def test_a_pass_report_contributes_nothing(dirs) -> None:
    qa, memory = dirs
    for name in ("QA-a.md", "QA-b.md"):
        (qa / name).write_text(_qa_report(1, verdict="PASS"), encoding="utf-8")
    assert "recurring causes: none" in _run(qa, memory).stdout


def test_feedback_memories_without_a_mechanism_recur_as_one_cause(dirs) -> None:
    qa, memory = dirs
    (memory / "lesson-a.md").write_text(_memory(2), encoding="utf-8")
    (memory / "lesson-b.md").write_text(_memory(4, mechanism=None), encoding="utf-8")
    (memory / "lesson-c.md").write_text(_memory(4, mechanism="scripts/memory_lint.py"), encoding="utf-8")
    (memory / "ruling.md").write_text(_memory(1, kind="project"), encoding="utf-8")
    (memory / "lesson-old.md").write_text(_memory(40), encoding="utf-8")

    result = _run(qa, memory)

    assert "lesson-without-mechanism: 2" in result.stdout, result.stdout
    assert "lesson-a.md" in result.stdout and "lesson-b.md" in result.stdout
    for absent in ("lesson-c.md", "ruling.md", "lesson-old.md"):
        assert absent not in result.stdout, result.stdout
    assert _STAMP in result.stdout


def test_no_memory_text_or_value_ever_reaches_the_output(dirs) -> None:
    """AGENTS.md §8: names and counts only."""
    qa, memory = dirs
    for name in ("a.md", "b.md"):
        (memory / name).write_text(_memory(1), encoding="utf-8")
    (qa / "QA-a.md").write_text(_qa_report(1, "test-gap", "test-gap").replace("broke", _SECRET), encoding="utf-8")

    result = _run(qa, memory)

    assert result.returncode == 0, result.stderr
    assert "lesson-without-mechanism: 2" in result.stdout  # the memories were read
    assert "test-gap: 2" in result.stdout  # and so was the report
    assert _SECRET not in result.stdout + result.stderr
    assert "lesson about customer" not in result.stdout


def test_empty_directories_report_nothing_and_exit_0(dirs) -> None:
    qa, memory = dirs
    result = _run(qa, memory)
    assert result.returncode == 0, result.stderr
    assert "QA reports read: 0" in result.stdout
    assert "feedback memories in window: 0" in result.stdout
    assert "recurring causes: none" in result.stdout


def test_missing_directories_are_named_and_exit_0(tmp_path: Path) -> None:
    result = _run(tmp_path / "no-qa", tmp_path / "no-memory")
    assert result.returncode == 0, result.stderr
    assert "QA directory not found" in result.stdout
    assert "memory directory not found" in result.stdout


@pytest.mark.parametrize("content", [b"\xff\xfe\x00 not utf-8", b""], ids=["invalid-utf8", "empty"])
def test_an_undecodable_or_empty_file_is_counted_not_fatal(dirs, content: bytes) -> None:
    qa, memory = dirs
    (qa / "QA-bad.md").write_bytes(content)
    (memory / "bad.md").write_bytes(content)
    (qa / "QA-a.md").write_text(_qa_report(1, "test-gap", "test-gap"), encoding="utf-8")

    result = _run(qa, memory)

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert "test-gap: 2" in result.stdout


def test_an_invalid_utf8_file_is_reported_as_unreadable(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-bad.md").write_bytes(b"\xff\xfe")
    (memory / "bad.md").write_bytes(b"\xff\xfe")
    result = _run(qa, memory)
    assert "QA reports read: 0 · unreadable: 1" in result.stdout, result.stdout
    assert "memories unreadable: 1" in result.stdout, result.stdout


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="permission bits do not bind here")
def test_an_unreadable_file_is_counted_not_fatal(dirs) -> None:
    qa, memory = dirs
    locked = qa / "QA-locked.md"
    locked.write_text(_qa_report(1, "test-gap"), encoding="utf-8")
    locked.chmod(0)
    try:
        result = _run(qa, memory)
    finally:
        locked.chmod(0o644)
    assert result.returncode == 0, result.stderr
    assert "unreadable: 1" in result.stdout


def test_an_unknown_cause_is_counted_as_unclassified_not_as_a_cause(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-a.md").write_text(_qa_report(1, "made-up", "made-up"), encoding="utf-8")
    result = _run(qa, memory)
    assert "unclassified defects: 2" in result.stdout
    assert "made-up" not in result.stdout


def test_without_rework_causes_it_says_unavailable_and_exits_0(dirs, tmp_path: Path) -> None:
    """A project without verify-tiers H: the meter module is absent."""
    qa, memory = dirs
    alone = tmp_path / "scripts"
    alone.mkdir()
    shutil.copy(_SCRIPT, alone / "learning_loop.py")
    (qa / "QA-a.md").write_text(_qa_report(1, "test-gap", "test-gap"), encoding="utf-8")

    result = _run(qa, memory, script=alone / "learning_loop.py")

    assert result.returncode == 0, result.stderr
    assert "unavailable: rework causes not shipped" in result.stdout
    assert "test-gap" not in result.stdout


def test_a_meter_without_the_cause_list_also_counts_as_unavailable(dirs, tmp_path: Path) -> None:
    """The meter exists but predates H: no `REWORK_CAUSES`."""
    qa, memory = dirs
    alone = tmp_path / "scripts"
    alone.mkdir()
    shutil.copy(_SCRIPT, alone / "learning_loop.py")
    (alone / "agent_time.py").write_text("CATEGORIES = ()\n", encoding="utf-8")

    result = _run(qa, memory, script=alone / "learning_loop.py")

    assert result.returncode == 0, result.stderr
    assert "unavailable: rework causes not shipped" in result.stdout


def test_the_default_window_is_28_days(dirs) -> None:
    qa, memory = dirs
    (qa / "QA-a.md").write_text(_qa_report(20, "test-gap", "test-gap"), encoding="utf-8")
    result = _run(qa, memory)
    assert "window 28 days" in result.stdout
    assert "test-gap: 2" in result.stdout


def test_it_runs_on_this_repo_and_exits_0() -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--window", "28"], capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "recurring causes" in result.stdout
