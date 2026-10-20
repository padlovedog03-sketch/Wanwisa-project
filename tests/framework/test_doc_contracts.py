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
    """H-AC4 names the five literally; this pins the template while the meter is absent.

    Temporary: once `scripts/agent_time.py` is on the branch the test above is
    the one source, and this literal copy stands down so the two cannot drift.
    """
    if (_REPO_ROOT / "scripts" / "agent_time.py").is_file():
        pytest.skip("agent_time.REWORK_CAUSES is the source now — see the test above")
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


_ADAPTERS = _REPO_ROOT / "doc" / "framework" / "ADAPTERS.md"


def _adapter_section(letter: str) -> str:
    """The text of one adapter's section: from its `## <letter> —` heading to the next `---`."""
    text = _ADAPTERS.read_text(encoding="utf-8")
    match = re.search(rf"^## {letter} — .*?(?=^---$)", text, re.M | re.S)
    assert match, f"ADAPTERS.md has no section for adapter {letter}"
    return match.group(0)


def _capability_rows(section: str) -> list[str]:
    """Rows of the section's capability table (the one whose header starts `| ความสามารถ |`)."""
    lines = section.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| ความสามารถ |"))
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


def _meter_row(letter: str) -> str:
    rows = [r for r in _capability_rows(_adapter_section(letter)) if r.startswith("| R37 ")]
    assert len(rows) == 1, f"adapter {letter}: expected one R37 meter row, found {len(rows)}"
    return rows[0]


def test_adapter_a_declares_the_meter_supported_and_names_its_reader() -> None:
    """J-AC10 (R38): adapter ก's capability table has the R37 meter, naming its reader."""
    row = _meter_row("ก")
    assert "`.claude/meter/transcript_reader.py`" in row
    assert "unsupported" not in row
    assert (_REPO_ROOT / ".claude" / "meter" / "transcript_reader.py").is_file()


def test_adapter_a_lists_the_meter_folder_among_its_files() -> None:
    paragraph = re.search(r"^\*\*ไฟล์ของตัวเชื่อมนี้:\*\*.*?(?=\n\n)", _adapter_section("ก"), re.M | re.S)
    assert paragraph, "adapter ก has no file list"
    assert "`.claude/meter/`" in paragraph.group(0)


def test_adapter_b_declares_the_meter_unsupported() -> None:
    """J-AC10 (R38, R27): adapter ข has the same row, saying `unsupported`."""
    assert "unsupported" in _meter_row("ข")

_ENGINEERING_LOOP = _REPO_ROOT / ".agents" / "skills" / "engineering-loop" / "SKILL.md"


# ---------------------------------------------------------------------------
# Increment I (I-AC3, R34, R35, R36) — fewer model turns.
# ---------------------------------------------------------------------------


def _loop() -> str:
    return _ENGINEERING_LOOP.read_text(encoding="utf-8")


def test_engineering_loop_tells_agents_to_batch_independent_calls_into_one_turn() -> None:
    """R34."""
    assert "**Batch independent calls into one turn.**" in _loop()


def test_engineering_loop_tells_agents_not_to_re_read_an_unchanged_large_file() -> None:
    """R35: both halves — no re-read of an unchanged file, and read only the range needed."""
    text = _loop()
    assert "**Do not re-read an unchanged large file.**" in text
    assert "read only the range you need" in text


def test_engineering_loop_labels_the_turn_saving_as_unproven() -> None:
    """R36: the saving is stated as unproven and measured, never promised."""
    text = _loop()
    assert "The saving is unproven" in text
    assert "M14" in text


# ---------------------------------------------------------------------------
# Increment G (G-AC5, G-AC6; R26, R27, R28) — no hand-written polling.
# ---------------------------------------------------------------------------


def _cells(letter: str, prefix: str) -> list[str]:
    rows = [r for r in _capability_rows(_adapter_section(letter)) if r.startswith(prefix)]
    assert len(rows) == 1, f"adapter {letter}: expected one {prefix!r} row, found {len(rows)}"
    return [cell.strip() for cell in rows[0].strip().strip("|").split(" | ")]


def test_adapter_a_enforces_r26_and_has_a_completion_notification() -> None:
    """G-AC5 (R27): adapter ก."""
    assert "R26 polling guard: enforced" in _cells("ก", "| R26 ")[1]
    assert "completion notification: yes" in _cells("ก", "| R27 ")[1]


def test_adapter_b_declares_no_r26_enforcement_its_fallback_and_what_is_weaker() -> None:
    """G-AC5 (R27, R28): adapter ข names the fallback and what it loses."""
    _, has, fallback, weaker = _cells("ข", "| R26 ")
    assert "R26: no enforcement" in has
    assert "engineering-loop/SKILL.md" in fallback and "R37" in fallback
    assert weaker not in ("", "—")


def test_adapter_b_declares_no_completion_notification_and_its_substitute() -> None:
    """G-AC5 (R28): the substitute is a foreground run with the tool's own timeout."""
    _, has, substitute, weaker = _cells("ข", "| R27 ")
    assert "completion notification: no" in has
    assert "foreground" in substitute and "timeout" in substitute
    assert weaker not in ("", "—")


def test_engineering_loop_carries_the_waiting_rule() -> None:
    """G-AC6 (R28)."""
    text = _loop()
    assert "## Waiting on background work" in text
    assert "**Never poll.**" in text
    assert "end your turn or do independent work until the completion notification arrives" in text
    assert "doc/framework/ADAPTERS.md" in text
# SPEC-delegated-autonomy E-AC3 (R19) — the independent reviewer is a role,
# has a report template, and sits between engineer and qa in every tier.
# ---------------------------------------------------------------------------

_REVIEWER = _AGENTS / "reviewer.md"
_REVIEW_TEMPLATE = _REPO_ROOT / "doc" / "templates" / "review-report.md"


def test_the_reviewer_agent_exists_with_frontmatter() -> None:
    text = _REVIEWER.read_text(encoding="utf-8")
    assert re.search(r"\A---\nname: reviewer\ndescription: \S", text), text[:200]


def test_the_reviewer_starts_from_the_files_never_the_authors_conversation() -> None:
    mission = _REVIEWER.read_text(encoding="utf-8").split("## Mission", 1)[1].split("\n## ", 1)[0]
    assert "starts from the files" in mission
    assert "never from the author's conversation" in mission


def test_the_reviewer_records_its_own_run_and_states_the_limit() -> None:
    text = _REVIEWER.read_text(encoding="utf-8")
    assert "Reviewer-run:" in text and "Author-run:" in text
    assert "doc/templates/review-report.md" in text
    assert "LIMIT" in text


@pytest.mark.parametrize(
    "line",
    [r"Status: \S", r"Upstream: \S", r"Author-run: \S", r"Reviewer-run: \S", r"(?:## )?Verdict: PASS \| FAIL"],
)
def test_the_review_template_carries_the_lines_the_spawn_gate_reads(line: str) -> None:
    text = _REVIEW_TEMPLATE.read_text(encoding="utf-8")
    assert re.search(rf"^{line}", text, re.M), f"doc/templates/review-report.md lacks {line!r}"


def _tier_rows(agents_md: str) -> list[str]:
    """The tier rows of the AGENTS.md §5 table, with backticks removed."""
    section = agents_md.split("\n## 5.", 1)[1].split("\n## 6.", 1)[0]
    return [line.replace("`", "") for line in section.splitlines() if re.match(r"^\| \*\*\d", line)]


def _ordered(row: str, steps: tuple[str, ...]) -> bool:
    position = 0
    for step in steps:
        found = re.search(rf"(?<![\w-]){re.escape(step)}(?![\w-])", row[position:])
        if not found:
            return False
        position += found.end()
    return True


def test_agents_md_shows_engineer_then_reviewer_then_qa_in_every_tier() -> None:
    rows = _tier_rows((_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))
    assert len(rows) == 3, rows
    for row in rows:
        assert _ordered(row, ("engineer", "reviewer", "qa")), row


def test_the_tier_row_check_rejects_a_row_with_reviewer_after_qa() -> None:
    """The ordering check has teeth: qa before reviewer is not the R19 flow."""
    assert not _ordered("| **1** | x | engineer → qa → reviewer |", ("engineer", "reviewer", "qa"))
    assert not _ordered("| **1** | x | engineer → frontend-qa |", ("engineer", "reviewer", "qa"))
    assert _ordered("| **2** | x | pm → engineer → reviewer → 👤 → qa → 👤 |", ("engineer", "reviewer", "qa"))


# ---------------------------------------------------------------------------
# Increment D (D-AC6, R14) — every "full run before every handoff" rule carries
# the opt-in qualifier. An opted-in project hands off on the handoff tier and
# runs the full suite once per merge (scripts/verify-merge.sh); a project that
# has not opted in keeps the full run before every handoff, exactly as before.
# ---------------------------------------------------------------------------

R14_SCOPE = ("AGENTS.md", ".agents", ".claude/agents", "doc/framework", "doc/templates",
             "scripts/verify-full.sh")
#: Design §D "R14 patterns". Each requiring location matches at least one
#: (asserted below through `R14_LOCATIONS`), so the list cannot pass vacuously.
R14_PATTERNS = (
    r"before every handoff",
    r"before \*\*every\*\* handoff",
    r"ก่อนส่งมอบทุกครั้ง",
    r"ก่อนถือว่าเสร็จ",
    r"exit gate, before the handoff",
    r"verify-full\.sh`? output",
    r"the verdict command is the exit gate",
    r"run the full suite",
    r"EXIT GATE \(full tier\)",
    r"Paste this output in the handoff",
)
R14_QUALIFIERS = ("verify-handoff.sh --status", "not opted in", "ยังไม่ opt-in")
#: The requiring locations, found by a fragment of their own text rather than a
#: line number (line numbers drift with every edit above them).
R14_LOCATIONS = (
    ("scripts/verify-full.sh", "# THE EXIT GATE."),
    ("scripts/verify-full.sh", 'echo "EXIT GATE GREEN.'),
    ("AGENTS.md", "scripts/verify-full.sh           #"),
    (".agents/skills/engineering-loop/SKILL.md", "EXIT GATE (full tier)"),
    (".agents/skills/engineering-loop/SKILL.md", "| **exit gate** |"),
    (".agents/skills/engineering-loop/SKILL.md", "- Which criteria passed"),
    (".claude/agents/ai-engineer.md", "**exit gate, before the handoff"),
    (".claude/agents/ai-engineer.md", "**Report** with evidence"),
    (".claude/agents/qa.md", "The verdict command is the exit gate"),
    (".claude/agents/qa.md", "3. **Execute**"),
    (".claude/agents/frontend-qa.md", "**Never trust a reported pass"),
    (".claude/agents/frontend-qa.md", "3. **Execute**"),
    ("doc/framework/SETUP.md", "คือประตูออก**"),
)
_R14_RE = re.compile("|".join(R14_PATTERNS), re.I)


def _r14_files(root: Path) -> list[Path]:
    files = []
    for rel in R14_SCOPE:
        path = root / rel
        files += [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return files


def r14_violations(root: Path) -> list[str]:
    """`file:line` of every line in the R14 scope that requires a full run and
    does not carry the opt-in qualifier. A `Do not:` line forbids a full run
    rather than requiring one, so it is exempt."""
    bad = []
    for path in _r14_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("Do not:") or not _R14_RE.search(line):
                continue
            if not any(q in line for q in R14_QUALIFIERS):
                bad.append(f"{path.relative_to(root).as_posix()}:{n}")
    return bad


@pytest.mark.parametrize("root", [_REPO_ROOT], ids=["repo"])
def test_every_full_run_rule_carries_the_opt_in_qualifier(root: Path) -> None:
    """D-AC6 (R14, M9)."""
    assert r14_violations(root) == []


@pytest.mark.parametrize(("rel", "anchor"), R14_LOCATIONS, ids=[f"{r}:{a[:24]}" for r, a in R14_LOCATIONS])
def test_each_requiring_location_matches_a_pattern_and_is_qualified(rel: str, anchor: str) -> None:
    """D-AC6: the pattern list reaches every location the PRD names."""
    lines = [ln for ln in (_REPO_ROOT / rel).read_text(encoding="utf-8").splitlines() if anchor in ln]
    assert len(lines) == 1, f"{rel}: expected one line with {anchor!r}, found {len(lines)}"
    assert _R14_RE.search(lines[0]), f"{rel}: {lines[0]!r} matches no R14 pattern"
    assert any(q in lines[0] for q in R14_QUALIFIERS), f"{rel}: {lines[0]!r} lacks the qualifier"


def test_a_planted_unqualified_rule_is_named_with_file_and_line(tmp_path: Path) -> None:
    """D-AC6 RED-FIRST: the planted line from the spec."""
    _plant(tmp_path, ".agents/skills/x/SKILL.md", "# x\n\nrun verify-full before every handoff\n")
    assert r14_violations(tmp_path) == [".agents/skills/x/SKILL.md:3"]


def test_a_do_not_line_is_exempt_and_a_qualified_line_is_clean(tmp_path: Path) -> None:
    _plant(tmp_path, "AGENTS.md",
           "Do not:       run the full suite · commit\n"
           "run the full suite (when `scripts/verify-handoff.sh --status` says *not opted in*)\n")
    assert r14_violations(tmp_path) == []


@pytest.mark.parametrize("rel", [
    ".agents/skills/coordinator-discipline/SKILL.md",
    "doc/framework/WHY.md",
    "doc/framework/SETUP.md",
])
def test_the_related_locations_name_the_merge_gate(rel: str) -> None:
    """D-AC6, second assertion: the three consistency locations mention verify-merge.sh."""
    assert "verify-merge.sh" in (_REPO_ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("agent", ["qa.md", "frontend-qa.md"])
def test_qa_verdict_rests_on_its_own_run_never_an_earlier_record(agent: str) -> None:
    """D-AC7 (R15): an opted-in QA verdict is QA's own handoff-tier run plus the
    tests it added, labelled `ran N of M`, never an earlier record."""
    text = (_AGENTS / agent).read_text(encoding="utf-8")
    line = next((ln for ln in text.splitlines() if "own handoff-tier run" in ln), "")
    assert line, f"{agent} lacks the opted-in verdict rule"
    for phrase in ("plus the tests you added", "ran N of M", "never an earlier record"):
        assert phrase in line, f"{agent}: verdict rule lacks {phrase!r}"
