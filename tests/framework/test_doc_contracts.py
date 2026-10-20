"""Document contracts: rules that live in prose, checked by machine.

WHY THIS FILE EXISTS. A rule a document states in prose and nobody checks
drifts the day someone edits around it, and the reader trusts the prose over
the practice. Each test here pins one thing the spec requires a document to
carry (SPEC-verify-tiers-merge-gate.md, ADR-11: document contracts are tests
inside an existing gate step).

Upgrade safety: `tests/framework/` runs inside every downstream project's
gate, so no check here judges a document written before its rule existed.

Run: `python3 -m pytest tests/framework/test_doc_contracts.py -q`
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS = _REPO_ROOT / ".claude" / "agents"

# ---- H (R29): every spec in review lists its affected tests and files -------------

AFFECTED_HEADING = "## Affected tests / affected files"


def reviewed_specs_missing_affected_section(root: Path) -> list[str]:
    """`doc/specs/SPEC-*.md` files at `Status: In Review` with no affected-files heading.

    In Review only: R29 says a spec without the section "cannot move to In
    Review". Approved and Done specs are history and are never retro-failed.
    """
    missing = []
    for path in sorted((root / "doc" / "specs").glob("SPEC-*.md")):
        text = path.read_text(encoding="utf-8")
        status = re.search(r"^Status:[ \t]*(.*?)[ \t]*$", text, re.M)
        if status and status.group(1) == "In Review" and not re.search(rf"^{re.escape(AFFECTED_HEADING)}[ \t]*$", text, re.M):
            missing.append(path.name)
    return missing


def _plant(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_spec_template_has_the_affected_tests_heading() -> None:
    """H-AC1 (R29): ba-sa starts every spec from the template, so the heading starts there."""
    text = (_REPO_ROOT / "doc" / "templates" / "spec.md").read_text(encoding="utf-8")
    assert re.search(rf"^{re.escape(AFFECTED_HEADING)}[ \t]*$", text, re.M), "doc/templates/spec.md lacks the heading"


@pytest.mark.parametrize("root", [_REPO_ROOT], ids=["repo"])
def test_every_reviewed_spec_lists_affected_tests(root: Path) -> None:
    """H-AC1 (R29): a spec at `In Review` without the section fails the gate, by name."""
    missing = reviewed_specs_missing_affected_section(root)
    assert not missing, f"spec(s) at In Review without `{AFFECTED_HEADING}`: {', '.join(missing)}"


def test_a_planted_reviewed_spec_without_the_section_is_named(tmp_path: Path) -> None:
    _plant(tmp_path, "doc/specs/SPEC-planted.md", "# SPEC: x\n\nStatus: In Review\n\n## Overview\n")
    _plant(tmp_path, "doc/specs/SPEC-good.md", f"# SPEC: y\n\nStatus: In Review\n\n{AFFECTED_HEADING}\n\n- a.py\n")
    assert reviewed_specs_missing_affected_section(tmp_path) == ["SPEC-planted.md"]
    with pytest.raises(AssertionError, match="SPEC-planted.md"):
        test_every_reviewed_spec_lists_affected_tests(tmp_path)


def test_an_approved_or_draft_spec_without_the_section_is_never_retro_failed(tmp_path: Path) -> None:
    _plant(tmp_path, "doc/specs/SPEC-old.md", "# SPEC: x\n\nStatus: Approved\n\n## Overview\n")
    _plant(tmp_path, "doc/specs/SPEC-draft.md", "# SPEC: y\n\nStatus: Draft\n\n## Overview\n")
    assert reviewed_specs_missing_affected_section(tmp_path) == []


def test_the_heading_must_be_a_heading_not_a_mention(tmp_path: Path) -> None:
    _plant(tmp_path, "doc/specs/SPEC-m.md", f"# SPEC\n\nStatus: In Review\n\nSee `{AFFECTED_HEADING}` later.\n")
    assert reviewed_specs_missing_affected_section(tmp_path) == ["SPEC-m.md"]


def test_ba_sa_is_required_to_fill_the_section() -> None:
    """R29: the owner of specs is told the section is mandatory."""
    text = (_AGENTS / "ba-sa.md").read_text(encoding="utf-8")
    assert "**Every spec carries `## Affected tests / affected files`.**" in text


# ---- H (R30): engineers self-check every AC before the handoff --------------------

SELF_CHECK_ANCHOR = "**Self-check every AC before the handoff.**"


@pytest.mark.parametrize("agent", ["ai-engineer", "frontend-engineer"])
def test_engineers_must_self_check_on_the_right_tier(agent: str) -> None:
    """H-AC3 (R30): the anchor, the opt-in handoff tier, the full-suite fallback, the lint."""
    text = (_AGENTS / f"{agent}.md").read_text(encoding="utf-8")
    assert SELF_CHECK_ANCHOR in text, f"{agent}.md lacks the self-check anchor"
    paragraph = text[text.index(SELF_CHECK_ANCHOR) :].split("\n\n", 1)[0]
    for needle in ("scripts/verify-handoff.sh --status", "scripts/verify-full.sh", "handback_lint.py --spec"):
        assert needle in paragraph, f"{agent}.md self-check paragraph does not name {needle}"


def test_handoff_protocol_carries_the_self_check_and_the_rework_marker() -> None:
    """R30 and ADR-13: the shared handoff rules name the block and the `REWORK:` line."""
    text = (_REPO_ROOT / ".agents" / "skills" / "handoff-protocol" / "SKILL.md").read_text(encoding="utf-8")
    assert "Self-check:" in text and "handback_lint.py --spec" in text
    assert "REWORK: doc/qa/QA-" in text
    assert "first message" in text


# ---- H (R31): every defect in a FAIL report has exactly one rework cause ----------

#: Reports dated before this day were written before R31 existed and are never
#: judged (the model is `MECHANISM_REQUIRED_FROM` in `scripts/correction_rate.py`).
REWORK_CAUSE_REQUIRED_FROM = dt.date(2026, 10, 20)

_QA_TEMPLATE = _REPO_ROOT / "doc" / "templates" / "qa-report.md"


def template_rework_causes() -> tuple[str, ...]:
    """The vocabulary line under the template's Defects table, in order."""
    text = _QA_TEMPLATE.read_text(encoding="utf-8")
    line = re.search(r"^Rework causes \(exactly one per defect\):(.*)$", text, re.M)
    assert line, "doc/templates/qa-report.md has no `Rework causes (exactly one per defect):` line"
    return tuple(re.findall(r"`([^`]+)`", line.group(1)))


def _defects_table(text: str) -> list[list[str]]:
    """Rows of the `## Defects` table, parsed as `scripts/agent_time.py` parses them."""
    section = re.search(r"^## Defects[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    table = [line for line in (section.group(1) if section else "").splitlines() if line.startswith("|")]
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in table]


def qa_reports_with_bad_causes(root: Path, causes: tuple[str, ...]) -> list[str]:
    """One problem per FAIL report row (dated on or after the cut-off) whose cause is not exactly one of `causes`."""
    problems = []
    for path in sorted((root / "doc" / "qa").glob("QA-*.md")):
        text = path.read_text(encoding="utf-8")
        date = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        if not date or dt.date.fromisoformat(date.group(1)) < REWORK_CAUSE_REQUIRED_FROM:
            continue
        if not re.search(r"^#*\s*Verdict:\s*FAIL\b", text, re.M):
            continue
        rows = _defects_table(text)
        if not rows:
            problems.append(f"{path.name}: FAIL with no Defects table")
            continue
        header = rows[0]
        if "Rework cause" not in header:
            problems.append(f"{path.name}: Defects table has no `Rework cause` column")
            continue
        col = header.index("Rework cause")
        body = [r for r in rows[1:] if not all(set(c) <= set("-: ") for c in r)]
        for n, row in enumerate(body, start=1):
            cause = row[col].strip("`") if col < len(row) else ""
            if cause not in causes:
                problems.append(f"{path.name}: defect row {n} has rework cause {cause!r} — must be exactly one of {', '.join(causes)}")
    return problems


def test_qa_template_defects_table_has_a_rework_cause_column() -> None:
    """H-AC4 (R31)."""
    header = _defects_table(_QA_TEMPLATE.read_text(encoding="utf-8"))[0]
    assert header[-1] == "Rework cause", header


def test_qa_template_lists_exactly_the_meter_vocabulary() -> None:
    """H-AC4 (R31): one source for the list, `agent_time.REWORK_CAUSES`.

    `scripts/agent_time.py` ships with increment J. Until it is on the branch
    this test cannot compare, and says so as a skip — it is not a pass.
    """
    if not (_REPO_ROOT / "scripts" / "agent_time.py").is_file():
        pytest.skip("scripts/agent_time.py (increment J) not on this branch — template vocabulary NOT compared")
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    import agent_time

    assert template_rework_causes() == tuple(agent_time.REWORK_CAUSES)


def test_qa_template_vocabulary_is_the_five_spec_causes() -> None:
    """H-AC4 names the five literally; this pins the template while the meter is absent."""
    assert set(template_rework_causes()) == {"missed-ac", "regression", "spec-defect", "test-gap", "env-flaky"}


@pytest.mark.parametrize("root", [_REPO_ROOT], ids=["repo"])
def test_every_fail_report_classifies_each_defect(root: Path) -> None:
    """H-AC4 (R31): a FAIL report's defect rows each carry exactly one known cause."""
    problems = qa_reports_with_bad_causes(root, template_rework_causes())
    assert not problems, "\n".join(problems)


_FAIL_REPORT = """\
# QA Report: planted

Status: In Review
Upstream: doc/specs/SPEC-x.md
Date: {date}

## Verdict: FAIL

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| High | a | a.py:1 | ai-engineer | `missed-ac` |
| Med | b | b.py:2 | ai-engineer | {cause} |

## Edge Cases Probed
"""


@pytest.mark.parametrize(
    ("cause", "shown"),
    [("", "''"), ("missed-ac, test-gap", "'missed-ac, test-gap'"), ("flaky-ish", "'flaky-ish'")],
    ids=["none", "two", "unknown"],
)
def test_a_planted_fail_report_with_a_bad_cause_is_named_with_its_row(tmp_path: Path, cause: str, shown: str) -> None:
    _plant(tmp_path, "doc/qa/QA-planted.md", _FAIL_REPORT.format(date="2026-10-20", cause=cause))
    with pytest.raises(AssertionError, match=rf"QA-planted\.md: defect row 2 has rework cause {re.escape(shown)}"):
        test_every_fail_report_classifies_each_defect(tmp_path)


def test_a_planted_fail_report_with_one_known_cause_per_row_is_clean(tmp_path: Path) -> None:
    _plant(tmp_path, "doc/qa/QA-planted.md", _FAIL_REPORT.format(date="2026-10-21", cause="test-gap"))
    test_every_fail_report_classifies_each_defect(tmp_path)


def test_a_fail_report_dated_before_the_cut_off_is_never_retro_failed(tmp_path: Path) -> None:
    _plant(tmp_path, "doc/qa/QA-old.md", _FAIL_REPORT.format(date="2026-10-19", cause=""))
    test_every_fail_report_classifies_each_defect(tmp_path)


def test_a_pass_report_is_not_judged(tmp_path: Path) -> None:
    text = _FAIL_REPORT.format(date="2026-10-20", cause="").replace("Verdict: FAIL", "Verdict: PASS")
    _plant(tmp_path, "doc/qa/QA-pass.md", text)
    test_every_fail_report_classifies_each_defect(tmp_path)


def test_a_fail_report_without_the_cause_column_is_named(tmp_path: Path) -> None:
    text = _FAIL_REPORT.format(date="2026-10-20", cause="x").replace(" Rework cause |", "").replace("|---|---|---|---|---|", "|---|---|---|---|")
    _plant(tmp_path, "doc/qa/QA-nocol.md", text)
    with pytest.raises(AssertionError, match=r"QA-nocol\.md: Defects table has no `Rework cause` column"):
        test_every_fail_report_classifies_each_defect(tmp_path)


@pytest.mark.parametrize("agent", ["qa", "frontend-qa"])
def test_qa_agents_require_one_cause_per_defect(agent: str) -> None:
    """H-AC5 (R31)."""
    text = (_AGENTS / f"{agent}.md").read_text(encoding="utf-8")
    assert "**One rework cause per defect.**" in text, f"{agent}.md lacks the rework-cause anchor"
    assert "doc/templates/qa-report.md" in text
