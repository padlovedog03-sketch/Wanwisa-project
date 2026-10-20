"""QA regression tests for the review gate in `guard_agent_spawn.py`
(SPEC-delegated-autonomy E-AC2, R19).

Written by QA for doc/qa/QA-delegated-autonomy-E1.md. Two groups:

* Defect reproduction (red until fixed): a QA prompt that names the spec under
  test and, for context, a dependency's spec and that dependency's PASS review
  opens the gate although no review of the spec under test exists. E-AC2:
  the spawn is refused while `doc/qa/REVIEW-<slug>.md` is missing.
* Pins on behaviour that works today and that the owner's ease-of-use ruling
  depends on: ordinary agent types are never gated, a copied-but-unfilled
  template keeps QA shut, and every block is one actionable line.

Every review file is a `zz99` probe written into `doc/qa/` and removed after
the test, so the real approval state of the repo never matters.

Run: `python3 -m pytest tests/hooks/test_regression_guard_agent_spawn_review.py -q`
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPAWN_GATE = _REPO_ROOT / ".claude" / "hooks" / "guard_agent_spawn.py"
_REVIEW_DIR = _REPO_ROOT / "doc" / "qa"
_TEMPLATE = _REPO_ROOT / "doc" / "templates" / "review-report.md"

_EXIT_ALLOW = 0
_EXIT_BLOCK = 2

_UNDER_TEST = "zz99-qa-under-test"
_DEPENDENCY = "zz99-qa-dependency"


def _review(slug: str, verdict: str = "PASS") -> str:
    return (
        "# Review: probe\n\n"
        "Status: In Review\n"
        f"Upstream: doc/specs/SPEC-{slug}.md\n"
        "Author-run: a111\n"
        "Reviewer-run: b222\n\n"
        f"## Verdict: {verdict}\n"
    )


def _run_gate(subagent_type: str, prompt: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": subagent_type, "prompt": prompt}})
    return subprocess.run(
        [sys.executable, str(_SPAWN_GATE)], input=payload, capture_output=True, text=True, timeout=30, check=False
    )


@pytest.fixture
def review_file():
    created: list[Path] = []

    def _write(name: str, content: str) -> None:
        path = _REVIEW_DIR / name
        path.write_text(content, encoding="utf-8")
        created.append(path)

    yield _write

    for path in created:
        path.unlink(missing_ok=True)
    leftovers = sorted(p.name for p in _REVIEW_DIR.glob("REVIEW-*zz99*"))
    assert not leftovers, f"probe review leaked: {leftovers}"


# --- Defect reproduction (red until fixed) ----------------------------------


def test_regression_a_dependency_review_quoted_for_context_does_not_open_qa_for_another_spec(review_file) -> None:
    """Only the dependency has a PASS review; the spec under test has none."""
    review_file(f"REVIEW-{_DEPENDENCY}.md", _review(_DEPENDENCY))
    prompt = (
        f"Verify doc/specs/SPEC-{_UNDER_TEST}.md. It builds on SPEC-{_DEPENDENCY}.md, "
        f"already reviewed in REVIEW-{_DEPENDENCY}.md."
    )

    result = _run_gate("qa", prompt)

    assert result.returncode == _EXIT_BLOCK, "QA opened with no review of the spec under test"


# --- Pins on behaviour that works today -------------------------------------


@pytest.mark.parametrize(
    "subagent_type",
    ["pm", "ba-sa", "Explore", "Plan", "general-purpose", "reviewer", "caveman:cavecrew-reviewer", "claude"],
)
def test_regression_ordinary_agent_types_are_never_gated_on_a_review(subagent_type: str) -> None:
    result = _run_gate(subagent_type, f"Look at doc/specs/SPEC-{_UNDER_TEST}.md.")
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_regression_a_copied_but_unfilled_template_keeps_qa_shut(review_file) -> None:
    review_file(f"REVIEW-{_UNDER_TEST}.md", _TEMPLATE.read_text(encoding="utf-8"))

    result = _run_gate("qa", f"Verify doc/specs/SPEC-{_UNDER_TEST}.md.\nReview: doc/qa/REVIEW-{_UNDER_TEST}.md")

    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "PASS | FAIL" in result.stderr


@pytest.mark.parametrize("verdict", ["Pass", "PASS.", "PASS — all criteria met", "FAIL"])
def test_regression_every_review_block_is_one_line_naming_the_file_and_the_bad_value(review_file, verdict) -> None:
    review_file(f"REVIEW-{_UNDER_TEST}.md", _review(_UNDER_TEST, verdict))

    result = _run_gate("frontend-qa", f"Verify doc/specs/SPEC-{_UNDER_TEST}.md.\nReview: doc/qa/REVIEW-{_UNDER_TEST}.md")

    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == _EXIT_BLOCK
    assert len(lines) == 1, result.stderr
    assert f"doc/qa/REVIEW-{_UNDER_TEST}.md" in lines[0] and repr(verdict) in lines[0]
