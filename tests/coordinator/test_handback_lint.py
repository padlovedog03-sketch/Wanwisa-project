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
