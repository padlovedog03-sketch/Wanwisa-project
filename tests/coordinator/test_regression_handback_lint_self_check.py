"""QA regression tests for `scripts/handback_lint.py --spec` (increment H, R30).

Written by QA for doc/qa/QA-verify-tiers-H-rework.md. Two groups:

* Defect reproductions (red until fixed): a `not done` result written the way
  the agent docs themselves write it (in backticks) or in bold is counted as
  met; and an earlier met line for the same AC hides a later `not done`. Owner
  rule (2026-10-20): a `not done` result is always an open AC, never met.
* Pins on edges that work today: letter case and both arrows, no-arrow lines,
  empty results that must not borrow the next line, the widened AC-id pattern
  (`J2-AC1`), `--only` boundaries, and plain `-` mode staying spec-free.

Run: `python3 -m pytest tests/coordinator/test_regression_handback_lint_self_check.py -q`
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "handback_lint.py"

_SPEC = """\
| # | Given / When / Then |
|---|---|
| AC1 | a |
| AC-AC2 | b |
| H-AC1 | c |
| J2-AC1 | d |
"""

_TAIL = "\nCould not reach: none\nSubstituted: none\n"


def _run(tmp_path: Path, handback: str, *extra: str) -> subprocess.CompletedProcess[str]:
    spec = tmp_path / "SPEC-x.md"
    spec.write_text(_SPEC, encoding="utf-8")
    args = [sys.executable, str(_SCRIPT), "--spec", str(spec), *extra, "-"]
    return subprocess.run(args, input=handback, capture_output=True, text=True, check=False)


def _one_line(result: str) -> str:
    return f"Self-check:\n- H-AC1: pytest tests/x.py {result}\n{_TAIL}"


# ---- defect reproductions ----------------------------------------------------------


@pytest.mark.parametrize("result", ["→ `not done`", "→ **not done**", "-> `not done`"], ids=["backticks", "bold", "ascii-arrow-backticks"])
def test_regression_a_decorated_not_done_is_an_open_ac_never_met(tmp_path: Path, result: str) -> None:
    """The agent docs spell it `not done` in backticks; copying them must not read as met."""
    out = _run(tmp_path, _one_line(result), "--only", "H-")
    assert out.returncode == 1, out.stdout
    assert "self-check for H-AC1 is not done — open AC" in out.stdout


def test_regression_an_earlier_met_line_does_not_hide_a_later_not_done(tmp_path: Path) -> None:
    text = f"Self-check:\n- H-AC1: pytest → 1 passed\n- H-AC1: pytest → not done\n{_TAIL}"
    out = _run(tmp_path, text, "--only", "H-")
    assert out.returncode == 1, out.stdout


# ---- pins on edges that work today -------------------------------------------------


@pytest.mark.parametrize("result", ["→ not done", "-> Not Done", "→ NOT DONE yet"], ids=["arrow", "ascii-arrow-titlecase", "upper-with-tail"])
def test_regression_not_done_in_any_case_and_either_arrow_is_open(tmp_path: Path, result: str) -> None:
    out = _run(tmp_path, _one_line(result), "--only", "H-")
    assert out.returncode == 1, out.stdout
    assert "self-check for H-AC1 is not done — open AC" in out.stdout


def test_regression_a_line_with_no_arrow_is_missing_not_met(tmp_path: Path) -> None:
    out = _run(tmp_path, f"Self-check:\n- H-AC1: not done\n{_TAIL}", "--only", "H-")
    assert out.returncode == 1, out.stdout
    assert "self-check missing for H-AC1" in out.stdout


def test_regression_an_empty_result_does_not_borrow_the_next_line(tmp_path: Path) -> None:
    text = f"Self-check:\n- H-AC1: pytest → \t \n  1 passed\n{_TAIL}"
    out = _run(tmp_path, text, "--only", "H-")
    assert out.returncode == 1, out.stdout
    assert "self-check for H-AC1 has no result" in out.stdout


def test_regression_a_digit_carrying_prefix_is_read_from_the_spec(tmp_path: Path) -> None:
    """The engineer's widened pattern: `J2-AC1` is required, not silently dropped."""
    out = _run(tmp_path, f"Self-check:\n- AC1: c → ok\n{_TAIL}", "--only", "J2-")
    assert out.returncode == 1, out.stdout
    assert "self-check missing for J2-AC1" in out.stdout


def test_regression_only_ac_dash_selects_ac_ac_ids_not_bare_ac(tmp_path: Path) -> None:
    out = _run(tmp_path, f"Self-check:\n- AC1: c → ok\n{_TAIL}", "--only", "AC-")
    assert out.returncode == 1, out.stdout
    assert "self-check missing for AC-AC2" in out.stdout
    assert "AC1" not in out.stdout.replace("AC-AC2", "")


def test_regression_only_with_an_unmatched_prefix_is_a_usage_error(tmp_path: Path) -> None:
    out = _run(tmp_path, f"Self-check:\n- AC1: c → ok\n{_TAIL}", "--only", "ZZ-")
    assert out.returncode == 2
    assert "matches no AC" in out.stderr


def test_regression_plain_mode_never_asks_for_a_self_check() -> None:
    """Without `--spec`, a handback with no Self-check block is still clean (pre-H behaviour)."""
    out = subprocess.run(
        [sys.executable, str(_SCRIPT), "-"], input=_TAIL, capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stdout
    assert "self-check" not in out.stdout.lower()
