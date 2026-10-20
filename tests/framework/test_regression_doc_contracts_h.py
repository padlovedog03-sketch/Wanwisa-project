"""QA regression pins for the increment H document gates (R29, R31).

Written by QA for doc/qa/QA-verify-tiers-H-rework.md. Each test plants a
document in a temp root and calls the gate's own helper, so the real repo's
documents are never touched.

Run: `python3 -m pytest tests/framework/test_regression_doc_contracts_h.py -q`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_doc_contracts as dc  # noqa: E402  (path must be set up first)


def test_regression_a_fail_report_copying_the_template_placeholder_cause_is_named(tmp_path: Path) -> None:
    """A QA agent that copies the template row unedited has not chosen a cause."""
    text = dc._FAIL_REPORT.format(date="2026-10-20", cause="<one cause from the line below>")
    dc._plant(tmp_path, "doc/qa/QA-copied.md", text)
    problems = dc.qa_reports_with_bad_causes(tmp_path, dc.template_rework_causes())
    assert problems == [
        "QA-copied.md: defect row 2 has rework cause '<one cause from the line below>' — must be exactly one of "
        + ", ".join(dc.template_rework_causes())
    ]


def test_regression_a_fail_report_dated_exactly_on_the_cut_off_is_judged(tmp_path: Path) -> None:
    dc._plant(tmp_path, "doc/qa/QA-edge.md", dc._FAIL_REPORT.format(date=dc.REWORK_CAUSE_REQUIRED_FROM.isoformat(), cause="regression, test-gap"))
    problems = dc.qa_reports_with_bad_causes(tmp_path, dc.template_rework_causes())
    assert [p.split(":")[0] for p in problems] == ["QA-edge.md"]


def test_regression_a_reviewed_spec_with_the_heading_one_level_too_deep_is_named(tmp_path: Path) -> None:
    dc._plant(tmp_path, "doc/specs/SPEC-h3.md", "# S\n\nStatus: In Review\n\n### Affected tests / affected files\n")
    assert dc.reviewed_specs_missing_affected_section(tmp_path) == ["SPEC-h3.md"]
