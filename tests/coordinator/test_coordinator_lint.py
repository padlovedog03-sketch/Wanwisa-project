"""Tests for `scripts/coordinator_lint.py` — the mechanically-checkable half
of `doc/framework/COORDINATOR-CONSTITUTION.md` (NORTH-STAR mechanism ๓).

WHY THIS FILE EXISTS. The constitution states, in its own table, exactly
which of its five rules a script can and cannot check. A test suite that only
proves the HAPPY path would leave that table's claims unverified — this file
proves each mechanically-enforced rule actually bites (injected, observed
red naming the rule, reverted), and separately proves the checker correctly
declines to claim more than it can: an untagged claim is invisible-by-design,
not a false negative.

Run: `python3 -m pytest tests/coordinator/ -q`   (no project dependencies required)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "coordinator_lint.py"

sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import coordinator_lint as cl  # noqa: E402  (path must be set up first)

_SELF_REPORT = (
    "SELF-REPORT:\nRE-MEASURED: yes, ran the suite just now\n"
    "CHECKED-AGAINST-APPROVED-DOCS: none applicable\n"
)


def _run_cli(text: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "report.md"
    path.write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_fully_tagged_report_is_clean(tmp_path: Path) -> None:
    text = (
        "CLAIM: 205 tests passed.\n"
        "MEASURED: python3 -m pytest tests/ -q\n\n"
        "CLAIM: the QA agent reported 42 files affected.\n"
        "RELAYED: qa-agent report, not independently re-verified\n\n"
        "CLAIM: this is probably fine because the pattern matches wave 1.\n"
        "INFERRED: assumed wave 1's fix generalises; would be wrong if this "
        "repo's directory layout differs\n\n"
        "INSTRUCTION: do not rename tests/hooks/.\n"
        "PROVENANCE: JUDGEMENT\n\n"
        "INSTRUCTION: only the human writes the registry.\n"
        "PROVENANCE: OWNER\n\n"
    ) + _SELF_REPORT

    result = _run_cli(text, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "clean" in result.stdout


def test_the_coordinator_constitution_document_itself_exists_and_names_the_grammar() -> None:
    """A cheap sanity check that the contract and the checker did not drift
    apart: every tag the checker recognises is documented, and vice versa."""
    doc = (_REPO_ROOT / "doc" / "framework" / "COORDINATOR-CONSTITUTION.md").read_text(
        encoding="utf-8"
    )
    for tag in ("CLAIM:", "MEASURED:", "INFERRED:", "RELAYED:", "INSTRUCTION:", "PROVENANCE:",
                "SELF-REPORT:", "RE-MEASURED:", "CHECKED-AGAINST-APPROVED-DOCS:",
                "Slice:", "Files:", "Criteria:", "Verify with:"):
        assert tag in doc, f"{tag!r} is checked by the linter but not documented in the constitution"


# ---------------------------------------------------------------------------
# Rule 1 / 3 — CLAIM: needs an origin tag; MEASURED: must not truncate.
# Proven by injection: break the check function, observe the specific test
# go red, revert.
# ---------------------------------------------------------------------------


def test_an_untagged_claim_is_flagged(tmp_path: Path) -> None:
    """Injection run 2026-08-12: with the violation-append removed from the
    untagged-claim branch of `check_claims` (the `continue` left in place,
    the `Violation(...)` appended before it deleted), this test alone went
    red — the CLI reported "clean" for a claim carrying no origin tag at
    all. Reverted; `diff` against the pre-injection copy was empty.
    """
    text = "CLAIM: no files were affected.\n\n" + _SELF_REPORT

    result = _run_cli(text, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "rule 1/3" in result.stdout
    assert "no files were affected" in result.stdout


def test_a_measured_claim_with_a_truncating_command_is_flagged(tmp_path: Path) -> None:
    """The exact failure mode named in `.agents/skills/coordinator-discipline/
    SKILL.md` rule 1: a count claimed from a command with a `head`/`tail`/
    `2>/dev/null`/`-m`/`-k` in it.

    Injection run 2026-08-12: with `_TRUNCATING_PATTERNS` emptied to `()`,
    this test alone went red — a claim measured by `grep -c crash log |
    tail -1` was reported clean. Reverted; `diff` against the pre-injection
    copy was empty.
    """
    text = "CLAIM: only 2 crashes occurred.\nMEASURED: grep -c crash log | tail -1\n\n" + _SELF_REPORT

    result = _run_cli(text, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "rule 1" in result.stdout
    assert "truncates its own view" in result.stdout


def test_a_measured_claim_with_a_full_command_passes(tmp_path: Path) -> None:
    """The complement: a command with no truncating pattern must not be
    flagged, or the check above would be indistinguishable from "reject every
    MEASURED claim"."""
    text = "CLAIM: 4 files match.\nMEASURED: grep -rl pattern src/ | wc -l\n\n" + _SELF_REPORT

    result = _run_cli(text, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_a_relayed_claim_with_no_further_tag_is_accepted() -> None:
    """RELAYED: satisfies rule 3 on its own — the claim is labelled as
    someone else's number, which is exactly what the rule requires."""
    violations = cl.check_claims("CLAIM: the other team found 12 defects.\nRELAYED: their report\n")
    assert violations == []


def test_an_untagged_claim_with_a_tag_two_non_blank_lines_away_is_still_found() -> None:
    """`_LOOKAHEAD_LINES` tolerates a few non-matching lines between the claim
    and its tag (mirroring `doc/templates/SCAR.md`'s station blocks, where
    `Entered:` sits below prose, not immediately under the heading) — but it
    is finite. This pins the tolerated case; the injection below proves the
    limit itself is load-bearing, not decorative."""
    text = "CLAIM: 3 things happened.\nsome context line\nanother context line\nMEASURED: a command\n"
    assert cl.check_claims(text) == []


# ---------------------------------------------------------------------------
# Rule 4 / 5 — INSTRUCTION: needs PROVENANCE:; APPROVED <path> must resolve
# to a real, Approved document.
# ---------------------------------------------------------------------------


def test_an_instruction_with_no_provenance_is_flagged(tmp_path: Path) -> None:
    text = "INSTRUCTION: never touch the config file.\n\n" + _SELF_REPORT

    result = _run_cli(text, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "rule 4" in result.stdout


def test_provenance_owner_and_judgement_are_both_accepted() -> None:
    assert cl.check_instructions("INSTRUCTION: x.\nPROVENANCE: OWNER\n") == []
    assert cl.check_instructions("INSTRUCTION: x.\nPROVENANCE: JUDGEMENT\n") == []


def test_an_unrecognised_provenance_value_is_flagged() -> None:
    violations = cl.check_instructions("INSTRUCTION: x.\nPROVENANCE: BECAUSE I SAID SO\n")
    assert len(violations) == 1
    assert violations[0].rule == "4"


def test_provenance_approved_a_missing_file_is_flagged(tmp_path: Path) -> None:
    text = "INSTRUCTION: x.\nPROVENANCE: APPROVED doc/specs/SPEC-does-not-exist.md\n"
    violations = cl.check_instructions(text, base_dir=tmp_path)
    assert len(violations) == 1
    assert violations[0].rule == "5"
    assert "does not exist" in violations[0].reason


def test_provenance_approved_an_unapproved_document_is_flagged(tmp_path: Path) -> None:
    """The one place Rule 5 and the existing `guard_agent_spawn.py` logic
    overlap: citing a real document that is not `Status: Approved`."""
    spec_dir = tmp_path / "doc" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC-draft.md").write_text("Status: Draft\n", encoding="utf-8")
    text = "INSTRUCTION: x.\nPROVENANCE: APPROVED doc/specs/SPEC-draft.md\n"

    violations = cl.check_instructions(text, base_dir=tmp_path)

    assert len(violations) == 1
    assert violations[0].rule == "5"
    assert "Draft" in violations[0].reason


def test_provenance_approved_a_genuinely_approved_document_passes(tmp_path: Path) -> None:
    spec_dir = tmp_path / "doc" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC-real.md").write_text(
        "Status: Approved\nApproval: spec-real-2026-08-12\n", encoding="utf-8"
    )
    text = "INSTRUCTION: x.\nPROVENANCE: APPROVED doc/specs/SPEC-real.md\n"

    violations = cl.check_instructions(text, base_dir=tmp_path)

    assert violations == []


def test_the_provenance_check_bites_when_the_valid_values_are_widened() -> None:
    """Injection: add 'BECAUSE I SAID SO' to the valid-provenance tuple —
    the shape of a rule 4 check that has quietly stopped meaning anything.

    Measured: with the injected value added, an instruction citing that
    exact string is wrongly accepted. Restored immediately after.
    """
    original = cl._VALID_PROVENANCE_VALUES
    try:
        cl._VALID_PROVENANCE_VALUES = original + ("BECAUSE I SAID SO",)
        violations = cl.check_instructions("INSTRUCTION: x.\nPROVENANCE: BECAUSE I SAID SO\n")
        assert violations == [], "expected the injected value to be wrongly accepted"
    finally:
        cl._VALID_PROVENANCE_VALUES = original
        assert len(cl.check_instructions("INSTRUCTION: x.\nPROVENANCE: BECAUSE I SAID SO\n")) == 1


# ---------------------------------------------------------------------------
# Rules 2 / 5 (general case) — no truth-check; only the required self-report
# fields' PRESENCE is checkable, and the constitution says so.
# ---------------------------------------------------------------------------


def test_a_missing_self_report_block_is_flagged(tmp_path: Path) -> None:
    text = "CLAIM: x.\nMEASURED: y.\n"

    result = _run_cli(text, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "SELF-REPORT" in result.stdout


def test_a_self_report_block_missing_one_field_is_flagged() -> None:
    violations = cl.check_self_report("SELF-REPORT:\nRE-MEASURED: yes\n")
    assert len(violations) == 1
    assert violations[0].rule == "5"
    assert "CHECKED-AGAINST-APPROVED-DOCS" in violations[0].reason


def test_a_complete_self_report_block_passes() -> None:
    assert cl.check_self_report(_SELF_REPORT) == []


def test_the_self_report_presence_check_does_not_verify_truth() -> None:
    """States the documented limit as an executable fact: a `SELF-REPORT:`
    block with FABRICATED content still passes, because presence, not truth,
    is all this rule can check. If this test ever fails, the constitution's
    own claim about its limit has become false and the doc needs updating,
    not the code."""
    fabricated = (
        "SELF-REPORT:\nRE-MEASURED: yes, definitely, trust me\n"
        "CHECKED-AGAINST-APPROVED-DOCS: all of them, somehow\n"
    )
    assert cl.check_self_report(fabricated) == []


# ---------------------------------------------------------------------------
# Explicitly-declared blind spot: text with no markup at all is invisible.
# ---------------------------------------------------------------------------


def test_free_prose_with_no_markup_is_invisible_to_the_linter(tmp_path: Path) -> None:
    """Not a false negative — a stated design limit. This checker is a
    grammar check over an opt-in markup, not natural-language detection over
    arbitrary prose (the constitution says why: substring/NLP-style guessing
    is exactly what broke `.claude/hooks/guard_bash.py` before it was
    rewritten to match on command position instead)."""
    text = "There are no known bugs left. I checked everything and it's fine.\n"

    result = _run_cli(text, tmp_path)

    # No CLAIM:/INSTRUCTION: markup -> rules 1/3/4 see nothing at all. Only
    # the unconditional SELF-REPORT: requirement still fires.
    assert result.returncode == 1, result.stdout + result.stderr
    assert "SELF-REPORT" in result.stdout
    assert "no known bugs" not in result.stdout


# ---------------------------------------------------------------------------
# Rule 6 (SPEC-verify-tiers-merge-gate I-AC1, R33) — a `Slice:` brief must
# name its files, its criteria and what to verify with. A brief missing any
# of these sends the agent to rediscover them, one model turn at a time.
# ---------------------------------------------------------------------------

_FULL_BRIEF = (
    "Slice:        rule 6 in the coordinator linter\n"
    "Files:        scripts/coordinator_lint.py · tests/coordinator/test_coordinator_lint.py\n"
    "Criteria:     I-AC1, I-AC2\n"
    "Verify with:  python3 -m pytest tests/coordinator/ -q\n"
    "Do not:       commit\n"
)


def _without(field: str, brief: str = _FULL_BRIEF) -> str:
    return "".join(line + "\n" for line in brief.splitlines() if not line.startswith(field))


def _rule6(text: str) -> list[cl.Violation]:
    return [v for v in cl.lint(text) if v.rule == "6"]


def test_a_brief_with_files_criteria_and_verify_with_is_clean(tmp_path: Path) -> None:
    result = _run_cli(_FULL_BRIEF + "\n" + _SELF_REPORT, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "clean" in result.stdout


def test_a_brief_missing_files_is_flagged_and_names_the_field(tmp_path: Path) -> None:
    result = _run_cli(_without("Files:") + "\n" + _SELF_REPORT, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "rule 6 (line 1): brief has no 'Files:' line" in result.stdout


def test_a_brief_missing_criteria_is_flagged_and_names_the_field() -> None:
    violations = _rule6(_without("Criteria:") + "\n" + _SELF_REPORT)

    assert len(violations) == 1, violations
    assert "'Criteria:'" in violations[0].reason


def test_a_brief_missing_verify_with_is_flagged_and_names_the_field() -> None:
    violations = _rule6(_without("Verify with:") + "\n" + _SELF_REPORT)

    assert len(violations) == 1, violations
    assert "'Verify with:'" in violations[0].reason


def test_a_brief_missing_all_three_names_each_missing_field() -> None:
    brief = _without("Files:", _without("Criteria:", _without("Verify with:")))

    reasons = " ".join(v.reason for v in _rule6(brief + "\n" + _SELF_REPORT))

    for field in ("'Files:'", "'Criteria:'", "'Verify with:'"):
        assert field in reasons, reasons


def test_an_empty_field_counts_as_missing_and_does_not_borrow_the_next_line() -> None:
    """`Files:` with nothing after it must not be satisfied by the `Criteria:`
    line below it — the empty-field-swallows-the-next-line bug that fe59b02
    fixed in handback_lint."""
    brief = _FULL_BRIEF.replace(
        "Files:        scripts/coordinator_lint.py · tests/coordinator/test_coordinator_lint.py\n",
        "Files:\n",
    )

    violations = _rule6(brief + "\n" + _SELF_REPORT)

    assert [("'Files:'" in v.reason) for v in violations] == [True], violations


def test_each_slice_block_is_judged_on_its_own_fields() -> None:
    """The first brief's fields must not satisfy the second brief."""
    second = _without("Criteria:").replace("Slice:        rule 6", "Slice:        second slice")
    text = _FULL_BRIEF + "\n" + second + "\n" + _SELF_REPORT

    violations = _rule6(text)

    assert len(violations) == 1, violations
    assert violations[0].line_no == _FULL_BRIEF.count("\n") + 2
    assert "'Criteria:'" in violations[0].reason


def _prefixed(prefix: str, brief: str = _FULL_BRIEF) -> str:
    return "".join(prefix + line + "\n" for line in brief.splitlines())


@pytest.mark.parametrize("prefix", ["  ", "\t", "- ", "* ", "1. ", "  - "])
def test_an_indented_or_bulleted_brief_missing_criteria_is_flagged(prefix: str) -> None:
    """A brief written indented or as a list must still be judged — a
    `Slice:` matched only at column 0 let these through silently."""
    brief = _prefixed(prefix, _without("Criteria:"))

    violations = _rule6(brief + "\n" + _SELF_REPORT)

    assert len(violations) == 1, violations
    assert violations[0].line_no == 1
    assert "'Criteria:'" in violations[0].reason


@pytest.mark.parametrize("prefix", ["  ", "\t", "- ", "* ", "1. ", "  - "])
def test_an_indented_or_bulleted_full_brief_is_clean(prefix: str) -> None:
    """Fields are matched the same way as `Slice:`, so an indented field is
    not falsely reported missing."""
    assert _rule6(_prefixed(prefix) + "\n" + _SELF_REPORT) == []


def test_an_empty_indented_field_does_not_borrow_the_next_line() -> None:
    brief = _prefixed("- ", _FULL_BRIEF).replace(
        "- Files:        scripts/coordinator_lint.py · tests/coordinator/test_coordinator_lint.py\n",
        "- Files:\n",
    )

    violations = _rule6(brief + "\n" + _SELF_REPORT)

    assert [("'Files:'" in v.reason) for v in violations] == [True], violations


def test_rework_is_optional_in_a_brief() -> None:
    assert _rule6(_FULL_BRIEF + "\n" + _SELF_REPORT) == []
    assert _rule6(_FULL_BRIEF + "REWORK:       doc/qa/QA-x.md\n\n" + _SELF_REPORT) == []


def test_text_with_no_slice_line_is_not_judged_by_rule_6() -> None:
    assert _rule6("Files:\nnothing here\n" + _SELF_REPORT) == []


def test_the_brief_template_carries_every_field_rule_6_requires() -> None:
    """I-AC2: the template the coordinator copies must itself pass rule 6,
    and carry the optional `REWORK:` line ADR-13 uses to mark rework runs."""
    skill = (_REPO_ROOT / ".agents" / "skills" / "coordinator-discipline" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    start = skill.index("\nSlice:") + 1
    template = skill[start : skill.index("```", start)]

    assert _rule6(template + "\n" + _SELF_REPORT) == [], template
    assert "\nREWORK:" in template, template


# ---------------------------------------------------------------------------
# Rule 7 (SPEC-delegated-autonomy E-AC4, R20): an engineer brief written under
# autonomy (a filled `Under:` line) carries the impact map — `Impact:` from the
# spec's affected-files section and `Selected:` from `verify-handoff.sh --list`.
# Opt-in: a brief with no `Under:` is not judged (spec impact table row 19).
# ---------------------------------------------------------------------------

_UNDER_BRIEF = (
    _FULL_BRIEF
    + "Under:        mandate mandate-demo-tests-2026-10-20\n"
    + "Impact:       tests/coordinator/test_coordinator_lint.py · scripts/coordinator_lint.py\n"
    + "Selected:     tests/coordinator/test_coordinator_lint.py\n"
)


def _rule7(text: str) -> list[cl.Violation]:
    return [v for v in cl.lint(text) if v.rule == "7"]


def test_a_full_brief_under_autonomy_is_clean() -> None:
    assert _rule7(_UNDER_BRIEF + "\n" + _SELF_REPORT) == []


@pytest.mark.parametrize("field", ["Impact:", "Selected:"])
def test_a_brief_under_autonomy_missing_a_field_is_flagged(field: str) -> None:
    violations = _rule7(_without(field, _UNDER_BRIEF) + "\n" + _SELF_REPORT)

    assert len(violations) == 1, violations
    assert repr(field) in violations[0].reason
    assert violations[0].line_no == 1


@pytest.mark.parametrize("field", ["Impact:", "Selected:"])
def test_an_empty_field_under_autonomy_is_flagged(field: str) -> None:
    brief = "".join(
        (field + "\n") if line.startswith(field) else line + "\n" for line in _UNDER_BRIEF.splitlines()
    )
    assert len(_rule7(brief + "\n" + _SELF_REPORT)) == 1


@pytest.mark.parametrize("field", ["Impact:", "Selected:"])
def test_unavailable_with_a_reason_is_accepted_until_the_sources_ship(field: str) -> None:
    brief = "".join(
        f"{field} unavailable (verify-handoff.sh not shipped)\n" if line.startswith(field) else line + "\n"
        for line in _UNDER_BRIEF.splitlines()
    )
    assert _rule7(brief + "\n" + _SELF_REPORT) == []


@pytest.mark.parametrize("value", ["unavailable", "unavailable ()", "unavailable (  )", "Unavailable", "unavailable because"])
@pytest.mark.parametrize("field", ["Impact:", "Selected:"])
def test_unavailable_without_a_reason_is_flagged(field: str, value: str) -> None:
    brief = "".join(
        f"{field} {value}\n" if line.startswith(field) else line + "\n" for line in _UNDER_BRIEF.splitlines()
    )
    violations = _rule7(brief + "\n" + _SELF_REPORT)
    assert len(violations) == 1, violations
    assert "unavailable (<reason>)" in violations[0].reason


def test_a_brief_with_no_under_line_is_not_judged_by_rule_7() -> None:
    """Opt-in: today's briefs carry no impact map and must stay clean."""
    assert _rule7(_FULL_BRIEF + "\n" + _SELF_REPORT) == []


def test_an_empty_under_line_does_not_switch_rule_7_on() -> None:
    assert _rule7(_FULL_BRIEF + "Under:\n\n" + _SELF_REPORT) == []


def test_an_impact_line_in_another_brief_does_not_count() -> None:
    """Each `Slice:` block is judged on its own lines."""
    second = _without("Impact:", _without("Selected:", _UNDER_BRIEF)).replace("rule 6 in", "rule 7 in")
    text = _UNDER_BRIEF + "\n" + second + "\n" + _SELF_REPORT

    violations = _rule7(text)

    assert len(violations) == 2, violations
    assert {v.line_no for v in violations} == {_UNDER_BRIEF.count("\n") + 2}


@pytest.mark.parametrize("prefix", ["  ", "- ", "1. "])
def test_an_indented_or_bulleted_brief_under_autonomy_is_judged(prefix: str) -> None:
    assert _rule7(_prefixed(prefix, _UNDER_BRIEF) + "\n" + _SELF_REPORT) == []
    assert len(_rule7(_prefixed(prefix, _without("Impact:", _UNDER_BRIEF)) + "\n" + _SELF_REPORT)) == 1


# ---------------------------------------------------------------------------
# SPEC-jarvis-coordinator JC-AC11 — `--approve-ready`: a document handed to
# approve.sh is committed, clean against HEAD, and `In Review`. Each case runs
# in its own tmp git repo; approve.py is neither imported nor changed.
# ---------------------------------------------------------------------------

_IN_REVIEW = "# PRD: probe\n\nStatus: In Review\nUpstream: test\n\n## Approval history\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True, timeout=30,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / "doc" / "requirements").mkdir(parents=True)
    (tmp_path / "doc" / "specs").mkdir()
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _doc(repo: Path, rel: str, text: str = _IN_REVIEW, *, add: bool = True, commit: bool = True) -> None:
    (repo / rel).write_text(text, encoding="utf-8")
    if add:
        _git(repo, "add", rel)
    if commit:
        _git(repo, "commit", "-qm", f"add {rel}")


def test_a_committed_clean_in_review_document_prints_the_approve_command(repo: Path) -> None:
    _doc(repo, "doc/requirements/PRD-zz-probe.md")
    code, lines = cl.approve_ready(["zz-probe"], repo)
    assert (code, lines) == (0, ["scripts/approve.sh zz-probe --by <name>"])


def test_two_ready_slugs_print_one_command_for_both(repo: Path) -> None:
    _doc(repo, "doc/requirements/PRD-zz-a.md")
    _doc(repo, "doc/specs/SPEC-zz-b.md")
    assert cl.approve_ready(["zz-a", "ZZ-B"], repo) == (0, ["scripts/approve.sh zz-a ZZ-B --by <name>"])


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("untracked", "no tracked document matches 'zz-probe' — git add and commit it"),
        ("staged-only", "doc/requirements/PRD-zz-probe.md: not committed — commit before handing over approve.sh"),
        ("edited", "doc/requirements/PRD-zz-probe.md: uncommitted changes — commit before handing over approve.sh"),
        ("edited-staged", "doc/requirements/PRD-zz-probe.md: uncommitted changes — commit before handing over approve.sh"),
    ],
)
def test_a_document_not_committed_and_clean_is_refused_naming_the_problem(
    repo: Path, state: str, expected: str
) -> None:
    rel = "doc/requirements/PRD-zz-probe.md"
    if state == "untracked":
        _doc(repo, rel, add=False, commit=False)
    elif state == "staged-only":
        _doc(repo, rel, commit=False)
    else:
        _doc(repo, rel)
        (repo / rel).write_text(_IN_REVIEW + "edit\n", encoding="utf-8")
        if state == "edited-staged":
            _git(repo, "add", rel)
    assert cl.approve_ready(["zz-probe"], repo) == (1, [expected])


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        (_IN_REVIEW.replace("In Review", "Draft"), "'Draft'"),
        (_IN_REVIEW.replace("Status: In Review\n", ""), "'(none)'"),
        (_IN_REVIEW + "Status: In Review\n", "'In Review, In Review'"),
    ],
    ids=["draft", "no-status", "two-status-lines"],
)
def test_a_document_whose_status_is_not_exactly_one_in_review_is_refused(repo: Path, text: str, shown: str) -> None:
    _doc(repo, "doc/requirements/PRD-zz-probe.md", text)
    expected = f"doc/requirements/PRD-zz-probe.md: Status is {shown}, approve.sh accepts only In Review"
    assert cl.approve_ready(["zz-probe"], repo) == (1, [expected])


def test_a_slug_matching_nothing_is_refused(repo: Path) -> None:
    _doc(repo, "doc/requirements/PRD-zz-probe.md")
    code, lines = cl.approve_ready(["zz-probe", "zz-absent"], repo)
    assert (code, lines) == (1, ["no tracked document matches 'zz-absent' — git add and commit it"])


def test_one_dirty_document_of_two_matches_refuses_the_whole_batch(repo: Path) -> None:
    _doc(repo, "doc/requirements/PRD-zz-probe.md")
    _doc(repo, "doc/specs/SPEC-zz-probe.md")
    (repo / "doc/specs/SPEC-zz-probe.md").write_text(_IN_REVIEW + "edit\n", encoding="utf-8")
    code, lines = cl.approve_ready(["zz-probe"], repo)
    assert code == 1
    assert lines == ["doc/specs/SPEC-zz-probe.md: uncommitted changes — commit before handing over approve.sh"]


def test_documents_outside_the_approvable_folders_are_not_matched(repo: Path) -> None:
    """As approve.py: only its document folders count, so a framework page
    that carries the slug never drags a `Living` status into the batch."""
    (repo / "doc" / "framework").mkdir()
    _doc(repo, "doc/framework/zz-probe-notes.md", "Status: Living\n")
    _doc(repo, "doc/requirements/PRD-zz-probe.md")
    assert cl.approve_ready(["zz-probe"], repo) == (0, ["scripts/approve.sh zz-probe --by <name>"])


def _run_ready(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--approve-ready", *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=30,
    )


def test_the_cli_finds_the_repo_from_the_working_directory(repo: Path) -> None:
    _doc(repo, "doc/requirements/PRD-zz-probe.md")
    result = _run_ready("zz-probe", cwd=repo / "doc")
    assert (result.returncode, result.stdout) == (0, "scripts/approve.sh zz-probe --by <name>\n"), result.stderr


def test_the_cli_exits_1_with_one_line_per_problem(repo: Path) -> None:
    result = _run_ready("zz-a", "zz-b", cwd=repo)
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "no tracked document matches 'zz-a' — git add and commit it",
        "no tracked document matches 'zz-b' — git add and commit it",
    ]


@pytest.mark.parametrize("args", [(), ("",), ("   ",), ("zz-a", " ")], ids=["none", "empty", "whitespace", "one-blank"])
def test_no_or_blank_slug_exits_2_with_usage(repo: Path, args: tuple[str, ...]) -> None:
    result = _run_ready(*args, cwd=repo)
    assert result.returncode == 2
    assert "usage: coordinator_lint.py --approve-ready <slug>" in result.stderr and "Traceback" not in result.stderr


def test_outside_a_git_work_tree_exits_2_with_one_line(tmp_path: Path) -> None:
    result = _run_ready("zz-probe", cwd=tmp_path)
    assert result.returncode == 2
    assert result.stderr.strip().splitlines() == ["coordinator-lint: not inside a git work tree"]


def test_git_missing_from_path_exits_2_with_one_line(repo: Path) -> None:
    result = _run_ready("zz-probe", cwd=repo, env={"PATH": str(repo / "no-such-bin")})
    assert result.returncode == 2
    assert result.stderr.strip().splitlines() == ["coordinator-lint: git not found on PATH"]


def test_the_default_mode_still_needs_exactly_one_argument(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 2 and "usage: coordinator_lint.py <file>|-" in result.stderr


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_the_usage_and_exits_0(flag: str) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), flag], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert "python3 scripts/coordinator_lint.py --approve-ready" in result.stdout


def test_a_missing_file_is_one_plain_error_naming_it_and_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-report.md"
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(missing)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert str(missing) in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1


def test_a_directory_path_is_a_plain_error_not_a_traceback(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr and str(tmp_path) in result.stderr
