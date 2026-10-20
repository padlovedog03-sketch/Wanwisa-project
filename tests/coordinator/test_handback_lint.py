"""Tests for `scripts/handback_lint.py` — a handback must say what it could not
reach and what it substituted.

Each rule is proven by planting the violation (NORTH-STAR truth 2): a lint that
quietly stopped checking would turn this file red.

Run: `python3 -m pytest tests/coordinator/ -q`   (stdlib only)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "handback_lint.py"

sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import handback_lint as hl  # noqa: E402  (path must be set up first)

_CLEAN = """\
1. Artifacts: src/a.py
2. Evidence: 12 passed
3. Assumptions: none
4. Next step: qa
5. **Could not reach:** none
6. **Substituted:** the payment API — mocked, the sandbox key was absent
"""


def _run(text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "-"], input=text, capture_output=True, text=True, check=False
    )


def test_a_complete_handback_is_clean() -> None:
    assert hl.lint(_CLEAN) == []
    result = _run(_CLEAN)
    assert result.returncode == 0, result.stdout


def test_a_missing_field_is_red_and_names_the_field() -> None:
    text = _CLEAN.replace("5. **Could not reach:** none\n", "")
    result = _run(text)
    assert result.returncode == 1
    assert "`Could not reach:` is missing" in result.stdout
    assert "Substituted" not in result.stdout


def test_an_empty_field_is_red_not_treated_as_none() -> None:
    text = _CLEAN.replace("**Substituted:** the payment API — mocked, the sandbox key was absent", "**Substituted:**")
    problems = hl.lint(text)
    assert problems == ["`Substituted:` is empty — write `none` if there was nothing"]


def test_a_handback_with_neither_field_reports_both() -> None:
    problems = hl.lint("1. Artifacts: src/a.py\n2. Evidence: 12 passed\n")
    assert len(problems) == 2


def test_plain_and_dash_prefixed_fields_are_accepted() -> None:
    assert hl.lint("Could not reach: the staging DB\n- Substituted: none\n") == []


def test_no_argument_is_a_usage_error_not_a_pass() -> None:
    result = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 2


def test_an_empty_field_does_not_swallow_the_next_line_as_its_value() -> None:
    """Regression: the separator after the colon matched newlines, so an empty
    `Could not reach:` took `Next step: qa` as its value and the lint said clean."""
    text = "Summary\nCould not reach:\n\nNext step: qa\nSubstituted: none\n"
    result = _run(text)
    assert result.returncode == 1, result.stdout
    assert "`Could not reach:` is empty" in result.stdout


def test_an_empty_field_does_not_swallow_the_other_required_field() -> None:
    """Regression: an empty `Could not reach:` ate the `Substituted:` line, so the
    lint reported `Substituted:` missing instead of both fields empty."""
    problems = hl.lint("Could not reach:   \nSubstituted:\n")
    assert problems == [
        "`Could not reach:` is empty — write `none` if there was nothing",
        "`Substituted:` is empty — write `none` if there was nothing",
    ]


def test_a_field_filled_on_the_same_line_still_passes() -> None:
    assert hl.lint("Could not reach: the staging DB\n\nSubstituted: none\n") == []


# ---- H-AC2 (R30): `--spec <spec>` checks the per-AC `Self-check:` block -------------

_SPEC = """\
# SPEC: planted

## Acceptance Criteria

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| AC1 | R1 | Given a, Then b | tests/test_a.py |
| AC2 | R1 | Given c, Then d | tests/test_a.py |
| AC3 | R2 | Given e, Then f | tests/test_b.py |
"""

_SELF_CHECK_ALL = """\
Self-check:
- AC1: pytest tests/test_a.py::test_one → 1 passed
- AC2: pytest tests/test_a.py::test_two -> 1 passed
- AC3: scripts/verify-full.sh → EXIT GATE GREEN
"""


def _run_spec(tmp_path: Path, spec: str, handback: str) -> subprocess.CompletedProcess[str]:
    spec_path = tmp_path / "SPEC-planted.md"
    spec_path.write_text(spec, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--spec", str(spec_path), "-"],
        input=handback,
        capture_output=True,
        text=True,
        check=False,
    )


def test_spec_self_check_missing_an_ac_is_red_and_names_it(tmp_path: Path) -> None:
    handback = _CLEAN + _SELF_CHECK_ALL.replace("- AC2: pytest tests/test_a.py::test_two -> 1 passed\n", "")
    result = _run_spec(tmp_path, _SPEC, handback)
    assert result.returncode == 1, result.stdout
    assert "self-check missing for AC2" in result.stdout
    assert "for AC1" not in result.stdout
    assert "for AC3" not in result.stdout


def test_spec_self_check_with_every_ac_is_clean(tmp_path: Path) -> None:
    result = _run_spec(tmp_path, _SPEC, _CLEAN + _SELF_CHECK_ALL)
    assert result.returncode == 0, result.stdout


def test_spec_self_check_line_with_no_result_is_flagged(tmp_path: Path) -> None:
    handback = _CLEAN + _SELF_CHECK_ALL.replace("-> 1 passed", "->")
    result = _run_spec(tmp_path, _SPEC, handback)
    assert result.returncode == 1, result.stdout
    assert "self-check for AC2 has no result" in result.stdout


def test_spec_self_check_empty_result_does_not_swallow_the_next_ac_line() -> None:
    """The design's grammar put `\\s*` around the arrow; `\\s` crosses newlines, so an
    empty result took the next AC line as its value (the fe59b02 bug, again)."""
    text = "Self-check:\n- AC1: pytest a →\n- AC2: pytest b → 1 passed\n- AC3: pytest c → 1 passed\n"
    problems = hl.lint_self_check(text, ["AC1", "AC2", "AC3"])
    assert problems == ["self-check for AC1 has no result — give the command's outcome"]


def test_spec_self_check_line_with_no_command_is_flagged() -> None:
    problems = hl.lint_self_check("Self-check:\n- AC1:  → 1 passed\n", ["AC1"])
    assert problems == ["self-check for AC1 has no command — name what you ran"]


def test_spec_self_check_ids_match_exactly_not_by_prefix() -> None:
    """`AC10` present must not satisfy a missing `AC1`."""
    problems = hl.lint_self_check("Self-check:\n- AC10: pytest x → 1 passed\n", ["AC1", "AC10"])
    assert problems == ["self-check missing for AC1"]


def test_spec_self_check_block_ends_at_the_first_blank_line() -> None:
    """An AC line after the block has ended is prose, not a self-check."""
    text = "Self-check:\n- AC1: pytest x → 1 passed\n\n- AC2: pytest y → 1 passed\n"
    assert hl.lint_self_check(text, ["AC1", "AC2"]) == ["self-check missing for AC2"]


def test_spec_with_no_self_check_block_is_red(tmp_path: Path) -> None:
    result = _run_spec(tmp_path, _SPEC, _CLEAN)
    assert result.returncode == 1
    assert "no `Self-check:` block" in result.stdout


def test_spec_ids_are_read_from_the_first_table_column_including_prefixed_ids() -> None:
    spec = "| AC-AC1 | R1 | x | t |\n| H-AC2 | R2 | y | t |\n| note | AC9 | z | t |\n"
    assert hl.spec_ac_ids(spec) == ["AC-AC1", "H-AC2"]


def test_spec_with_no_ac_rows_is_a_usage_error_not_a_pass(tmp_path: Path) -> None:
    result = _run_spec(tmp_path, "# SPEC with no table\n", _CLEAN + _SELF_CHECK_ALL)
    assert result.returncode == 2, result.stdout


def test_spec_mode_still_checks_the_two_required_fields(tmp_path: Path) -> None:
    handback = _CLEAN.replace("5. **Could not reach:** none\n", "") + _SELF_CHECK_ALL
    result = _run_spec(tmp_path, _SPEC, handback)
    assert result.returncode == 1
    assert "`Could not reach:` is missing" in result.stdout
