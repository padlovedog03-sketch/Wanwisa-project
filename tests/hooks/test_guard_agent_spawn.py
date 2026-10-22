"""`guard_agent_spawn.py` — the gate on spawning implementer agents.

Two properties matter roughly equally here, and the second is the one that
gets guards deleted:

* the gate blocks an implementer spawn whose upstream document is not
  `Approved`;
* the gate does **not** block anything else — not `qa`, not `ba-sa`, not
  `Explore`, and not a legitimate no-spec bugfix that states its basis.

Every scenario is built from temporary probe documents written into
`doc/specs/` / `doc/architecture/` and removed afterwards, so these tests
neither depend on nor are invalidated by the actual approval state of the
repo. On the originating project, the first hook suite skipped eight
assertions whenever the tree happened to be clean — the state CI always checks
out — so ambient state is never trusted here.

Run: `python3 -m pytest tests/hooks/ -q`   (no project dependencies required)
"""

from __future__ import annotations

import importlib.util
import json
import os
import unicodedata
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPAWN_GATE = _REPO_ROOT / ".claude" / "hooks" / "guard_agent_spawn.py"

_EXIT_ALLOW = 0
_EXIT_BLOCK = 2

_GATED = ("ai-engineer", "frontend-engineer")
# `qa` and `frontend-qa` left this list with delegated-autonomy E-AC2: they are
# gated on an independent review instead of a spec (see the review-gate section).
_UNGATED = ("ba-sa", "pm", "Explore", "Plan", "general-purpose", "reviewer")

# Probe names that cannot collide with real documents.
_PROBE_SPEC = "SPEC-zz99-agent-gate-probe.md"
_PROBE_DESIGN = "DESIGN-zz99-agent-gate-probe.md"


def _run_gate(
    *, subagent_type: str, prompt: str, tool_name: str = "Agent"
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "tool_name": tool_name,
            "tool_input": {"subagent_type": subagent_type, "prompt": prompt + "\nTier: 1 — test\nFiles: x"},
        }
    )
    return subprocess.run(
        [sys.executable, str(_SPAWN_GATE)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.fixture
def probe_doc():
    """Writes a temporary document with a chosen Status into the repo, then
    removes it. The gate resolves documents by repo path, so the file has to
    live there — but it must never survive the test."""
    created: list[Path] = []

    def _write(status_line: str | None, *, directory: str = "doc/specs", name: str = _PROBE_SPEC):
        path = _REPO_ROOT / directory / name
        body = "# Probe document for the agent-spawn gate test\n\n"
        if status_line is not None:
            body += f"{status_line}\n"
        body += "\nUpstream: `tests/hooks/test_guard_agent_spawn.py`\n"
        path.write_text(body, encoding="utf-8")
        created.append(path)
        return name

    yield _write

    for path in created:
        if path.exists():
            path.unlink()
    for leftover in (_REPO_ROOT / "doc" / "specs" / _PROBE_SPEC,
                     _REPO_ROOT / "doc" / "architecture" / _PROBE_DESIGN):
        assert not leftover.exists(), f"probe document leaked: {leftover}"


# ---------------------------------------------------------------------------
# The gate reads the Status line.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subagent_type", _GATED)
def test_an_approved_spec_allows_the_spawn(subagent_type: str, probe_doc) -> None:
    name = probe_doc("Status: Approved")
    result = _run_gate(
        subagent_type=subagent_type,
        prompt=f"Implement doc/specs/{name} exactly as written.",
    )
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize("status", ["Draft", "In Review", "Done", "Living"])
def test_a_non_approved_spec_blocks_the_spawn_and_names_the_status(status: str, probe_doc) -> None:
    """The message must name the document *and* its actual status — a bare
    "blocked" tells the reader nothing about what to fix.

    Injection run 2026-08-12: with the status comparison loosened to accept
    any non-empty status (`status != _ALLOWED_STATUS` replaced by
    `not status`), six tests went red — all four rows of this matrix, plus the
    two other tests that rely on a Draft probe blocking — meaning every
    unapproved document then authorised an implementer. The ungated-types and
    override tests stayed green. Reverted."""
    name = probe_doc(f"Status: {status}")
    result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement doc/specs/{name}.")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert name in result.stderr
    assert status in result.stderr


def test_a_spec_with_no_status_line_blocks(probe_doc) -> None:
    name = probe_doc(None)
    result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement doc/specs/{name}.")
    assert result.returncode == _EXIT_BLOCK
    assert "no `Status:` line" in result.stderr


def test_a_named_spec_that_does_not_exist_blocks_rather_than_passing() -> None:
    """A typo in a spec name must not read as "no spec named, so fall through"."""
    result = _run_gate(
        subagent_type="ai-engineer",
        prompt="Implement doc/specs/SPEC-zz98-does-not-exist.md.",
    )
    assert result.returncode == _EXIT_BLOCK
    assert "file not found" in result.stderr


def test_a_decorated_approved_status_is_still_read_as_approved(probe_doc) -> None:
    """A repo migrating onto this framework carries decorated lines like
    `Status: Approved (human-approved 2026-07-20)`. The gate reads the leading
    word, so migration does not block every spawn — policing the grammar
    itself is the document-contract check's job, not this gate's."""
    name = probe_doc("Status: Approved (human-approved 2026-07-20)")
    result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement doc/specs/{name}.")
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_one_approved_spec_among_several_references_is_enough(probe_doc) -> None:
    """A prompt often quotes a superseded spec or a design doc for context.
    Blocking on those would be a false positive, and false positives get
    guards switched off."""
    name = probe_doc("Status: Approved")
    result = _run_gate(
        subagent_type="ai-engineer",
        prompt=(
            f"Implement doc/specs/{name}. For context see "
            f"doc/specs/SPEC-zz97-superseded.md which no longer exists."
        ),
    )
    assert result.returncode == _EXIT_ALLOW, result.stderr


# ---------------------------------------------------------------------------
# DESIGN documents are upstreams too — in their own directory.
# ---------------------------------------------------------------------------


class TestDesignDocumentsCountAsUpstream:
    """On the originating project a DESIGN document could not be named as an
    upstream at all: the reference pattern did not accept the prefix, and the
    resolver hardcoded `doc/specs/` — so every legitimately approved design
    forced the override token instead. A gate people are trained to bypass is
    worse than no gate, because it also carries the appearance of control."""

    def test_an_approved_design_document_is_accepted_by_repo_path(self, probe_doc) -> None:
        name = probe_doc(
            "Status: Approved", directory="doc/architecture", name=_PROBE_DESIGN
        )
        result = _run_gate(
            subagent_type="ai-engineer",
            prompt=f"Implement doc/architecture/{name}.",
        )
        assert result.returncode == _EXIT_ALLOW, result.stderr

    def test_an_approved_design_document_is_accepted_by_bare_filename(self, probe_doc) -> None:
        name = probe_doc(
            "Status: Approved", directory="doc/architecture", name=_PROBE_DESIGN
        )
        result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement {name}.")
        assert result.returncode == _EXIT_ALLOW, result.stderr

    def test_a_design_document_that_does_not_exist_is_still_blocked(self) -> None:
        """Accepting the prefix must not become accepting the claim: the file
        still has to be there and still has to be Approved."""
        result = _run_gate(
            subagent_type="ai-engineer", prompt="Implement DESIGN-zz98-does-not-exist.md."
        )
        assert result.returncode == _EXIT_BLOCK, result.stdout

    def test_a_design_document_is_resolved_in_its_own_directory(self, probe_doc) -> None:
        """The second half of the original defect: a DESIGN file lives in
        `doc/architecture/`, and looking it up under `doc/specs/` reports
        `file not found` for a document sitting right there."""
        name = probe_doc(
            "Status: Draft", directory="doc/architecture", name=_PROBE_DESIGN
        )
        result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement {name}.")
        # Draft blocks — but the reason must be its status, not a wrong path.
        assert result.returncode == _EXIT_BLOCK
        assert "Draft" in result.stderr
        assert "file not found" not in result.stderr


# ---------------------------------------------------------------------------
# Fail-closed, with a stated override.
# ---------------------------------------------------------------------------


def test_no_spec_named_blocks_and_explains_both_remedies() -> None:
    result = _run_gate(subagent_type="ai-engineer", prompt="Just fix the thing please.")
    assert result.returncode == _EXIT_BLOCK
    assert "NO_SPEC_BUGFIX:" in result.stderr
    assert "name the spec" in result.stderr


def test_the_override_with_a_reproduction_allows_the_spawn() -> None:
    """AGENTS.md §5 permits a small bugfix with a clear reproduction to start
    at the engineer — the section that actually carries the rule. The hook's
    own message cited §6 (the approval gates) until 2026-08-12; a guard that
    misdirects the reader to the wrong rule teaches the wrong rule."""
    result = _run_gate(
        subagent_type="ai-engineer",
        prompt=(
            "NO_SPEC_BUGFIX: submitting the form with a trailing space in the "
            "amount field crashes the parser with ValueError."
        ),
    )
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_bare_override_token_with_no_reason_is_still_blocked() -> None:
    """An override that needs no justification is a rubber stamp.

    Injection run 2026-08-12: with `_MIN_OVERRIDE_REASON_CHARS` dropped to 0,
    this test alone went red — `NO_SPEC_BUGFIX: x` then authorised a spawn on a
    one-character basis — while the with-reproduction test above stayed green.
    Reverted."""
    result = _run_gate(subagent_type="ai-engineer", prompt="NO_SPEC_BUGFIX: x")
    assert result.returncode == _EXIT_BLOCK
    assert "carries no reproduction" in result.stderr


def test_the_gate_refuses_to_suggest_editing_the_status_line(probe_doc) -> None:
    """The one remedy that must never be offered: an agent writing its own
    approval is precisely what the registry deny hook exists to prevent."""
    name = probe_doc("Status: Draft")
    result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement doc/specs/{name}.")
    assert result.returncode == _EXIT_BLOCK
    assert "do NOT edit" in result.stderr


# ---------------------------------------------------------------------------
# Everything else passes through.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subagent_type", _UNGATED)
def test_ungated_agent_types_are_never_blocked(subagent_type: str) -> None:
    """Gating investigation agents would block ordinary work, and a guard with
    false positives gets disabled."""
    result = _run_gate(
        subagent_type=subagent_type,
        prompt="Investigate why the score dropped. No spec named on purpose.",
    )
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_non_agent_tool_call_passes_through() -> None:
    result = _run_gate(subagent_type="ai-engineer", prompt="no spec", tool_name="Bash")
    assert result.returncode == _EXIT_ALLOW


def test_a_malformed_payload_fails_open_rather_than_wedging_every_spawn() -> None:
    """A hook bug must not make the pipeline unusable."""
    result = subprocess.run(
        [sys.executable, str(_SPAWN_GATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == _EXIT_ALLOW


def test_the_gate_is_registered_in_settings_json() -> None:
    """A hook file that is not wired in never runs — the quietest possible
    failure."""
    settings = json.loads((_REPO_ROOT / ".claude" / "settings.json").read_text())
    assert "guard_agent_spawn.py" in json.dumps(settings)
    matchers = [
        entry.get("matcher", "")
        for entry in settings["hooks"]["PreToolUse"]
        if "guard_agent_spawn.py" in json.dumps(entry)
    ]
    assert matchers, "no PreToolUse entry registers the spawn gate"
    assert any("Agent" in matcher for matcher in matchers), (
        f"the spawn gate is registered but not on the Agent tool: {matchers}"
    )


# ---------------------------------------------------------------------------
# The review gate on QA spawns (SPEC-delegated-autonomy E-AC2, R19, D5).
#
# A `qa` or `frontend-qa` spawn names its review on a `Review:` line; that file
# needs a PASS verdict written by a different run from the author, and an
# `Upstream:` naming the spec under test. It applies to all work, not only
# under autonomy, and is separate from the engineer spec check.
# ---------------------------------------------------------------------------

_REVIEW_GATED = ("qa", "frontend-qa")
_PROBE_SLUG = "zz99-review-gate-probe"
_PROBE_REVIEW = f"REVIEW-{_PROBE_SLUG}.md"
_PROBE_BUGFIX_REVIEW = "REVIEW-bugfix-zz99-probe.md"
_QA_PROMPT = f"Verify against its acceptance criteria.\nSpec: doc/specs/SPEC-{_PROBE_SLUG}.md\nReview: doc/qa/{_PROBE_REVIEW}"
_ADD_REVIEW_LINE = 'add "Review: doc/qa/REVIEW-<slug>.md" (a PASS review by a different run) to the QA prompt'

_GOOD_REVIEW = (
    "# Review: probe\n\n"
    "Status: In Review\n"
    f"Upstream: doc/specs/SPEC-{_PROBE_SLUG}.md\n"
    "Author-run: a111\n"
    "Reviewer-run: b222\n\n"
    "## Verdict: PASS\n"
)


@pytest.fixture
def review_doc():
    """Writes a temporary REVIEW file into `doc/qa/` and removes it afterwards.
    The gate resolves reviews by repo path, so the file has to live there."""
    created: list[Path] = []

    def _write(content: str | bytes, *, name: str = _PROBE_REVIEW) -> Path:
        path = _REPO_ROOT / "doc" / "qa" / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        created.append(path)
        return path

    yield _write

    for path in created:
        if path.exists():
            path.chmod(0o644)
            path.unlink()
    leftovers = sorted(p.name for p in (_REPO_ROOT / "doc" / "qa").glob("REVIEW-*zz99*"))
    assert not leftovers, f"probe review leaked: {leftovers}"


@pytest.mark.parametrize("subagent_type", _REVIEW_GATED)
def test_a_passing_review_by_another_run_allows_the_qa_spawn(subagent_type: str, review_doc) -> None:
    review_doc(_GOOD_REVIEW)
    result = _run_gate(subagent_type=subagent_type, prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize("subagent_type", _REVIEW_GATED)
def test_a_missing_review_blocks_the_qa_spawn(subagent_type: str) -> None:
    result = _run_gate(subagent_type=subagent_type, prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert _PROBE_REVIEW in result.stderr
    assert "not found" in result.stderr


def test_a_qa_prompt_naming_no_spec_and_no_review_blocks() -> None:
    result = _run_gate(subagent_type="qa", prompt="Check the new feature please.")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "REVIEW-" in result.stderr


@pytest.mark.parametrize(
    "verdict_line",
    [
        "## Verdict: FAIL",
        "Verdict: PASS | FAIL",  # the unfilled template line
        "Verdict:",
        "Verdict: PASSED",
        "Verdict: PASS but FAIL on AC2",
        "Verdict: PASS (FAIL on AC2 waived)",
        "Verdict: pending",
    ],
)
def test_a_review_without_a_pass_verdict_blocks(verdict_line: str, review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", verdict_line))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "PASS" in result.stderr


@pytest.mark.parametrize(
    "verdict_line",
    ["Verdict: PASS", "**Verdict:** PASS", "Verdict: **PASS**", "## Verdict: PASS (two nits, non-blocking)"],
)
def test_the_pass_verdict_is_read_in_its_heading_bold_and_plain_forms(verdict_line: str, review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", verdict_line))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_decorated_status_line_is_not_read_as_the_verdict(review_doc) -> None:
    """Hostile: a PASS smuggled onto a decorated Status line, with no Verdict line."""
    text = _GOOD_REVIEW.replace("Status: In Review", "Status: Done (Verdict: PASS)")
    review_doc(text.replace("## Verdict: PASS\n", ""))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_a_decorated_status_line_does_not_disturb_a_real_verdict(review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace("Status: In Review", "Status: Approved (by nobody, FAIL)"))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_second_verdict_line_that_fails_blocks(review_doc) -> None:
    review_doc(_GOOD_REVIEW + "\n## Re-review\n\nVerdict: FAIL\n")
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout


@pytest.mark.parametrize(
    "author, reviewer",
    [
        ("a111", "a111"),
        ("a111", "A111"),
        ("a111", " a111 "),
        ("a111", "a 111"),
        ("a111", "a​111"),
        ("a111", "ａ111"),
    ],
    ids=["equal", "case", "spaces", "nbsp", "zero-width", "full-width"],
)
def test_a_review_by_the_author_run_blocks(author: str, reviewer: str, review_doc) -> None:
    text = _GOOD_REVIEW.replace("Author-run: a111", f"Author-run: {author}")
    review_doc(text.replace("Reviewer-run: b222", f"Reviewer-run: {reviewer}"))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "Author-run" in result.stderr


@pytest.mark.parametrize(
    "old, new",
    [
        ("Author-run: a111\n", ""),
        ("Reviewer-run: b222\n", ""),
        ("Reviewer-run: b222", "Reviewer-run:"),
        ("Reviewer-run: b222", "Reviewer-run: <id>"),
        ("Author-run: a111", "Author-run: <id>"),
    ],
    ids=["no-author", "no-reviewer", "empty-reviewer", "placeholder-reviewer", "placeholder-author"],
)
def test_a_missing_or_placeholder_run_id_blocks(old: str, new: str, review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace(old, new))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout


@pytest.mark.parametrize("content", ["", "   \n\n", b"\xff\xfe not utf-8 \xff"], ids=["empty", "blank", "invalid-utf8"])
def test_an_empty_or_undecodable_review_blocks_with_exit_2_not_a_crash(content, review_doc) -> None:
    """A traceback exits 1, and only exit 2 blocks — a crash would let QA through."""
    review_doc(content)
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="permission bits do not bind here")
def test_an_unreadable_review_blocks_with_exit_2(review_doc) -> None:
    review_doc(_GOOD_REVIEW).chmod(0)
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_a_directory_named_like_the_review_blocks() -> None:
    path = _REPO_ROOT / "doc" / "qa" / _PROBE_REVIEW
    path.mkdir()
    try:
        result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    finally:
        path.rmdir()
    assert result.returncode == _EXIT_BLOCK, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_a_passing_review_for_another_slug_does_not_count(review_doc) -> None:
    """Exact stem only: no glob, no prefix match."""
    review_doc(_GOOD_REVIEW, name=f"REVIEW-{_PROBE_SLUG}-other.md")
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_an_explicitly_named_review_must_exist_exactly(review_doc) -> None:
    review_doc(_GOOD_REVIEW, name="REVIEW-zz99-a-b.md")
    result = _run_gate(subagent_type="qa", prompt=f"Spec: SPEC-{_PROBE_SLUG}.md\nReview: doc/qa/REVIEW-zz99-a.md")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "REVIEW-zz99-a.md" in result.stderr


def test_an_explicitly_named_passing_review_allows(review_doc) -> None:
    review_doc(_GOOD_REVIEW, name="REVIEW-zz99-a.md")
    result = _run_gate(subagent_type="qa", prompt=f"Spec: SPEC-{_PROBE_SLUG}.md\nReview: doc/qa/REVIEW-zz99-a.md")
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_only_the_review_line_counts_not_reviews_mentioned_elsewhere(review_doc) -> None:
    """A passing review quoted elsewhere in the prompt cannot rescue the named one."""
    review_doc(_GOOD_REVIEW, name="REVIEW-zz99-a.md")
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", "## Verdict: FAIL"), name="REVIEW-zz99-b.md")
    prompt = f"Compare REVIEW-zz99-a.md.\nSpec: SPEC-{_PROBE_SLUG}.md\nReview: REVIEW-zz99-b.md"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "REVIEW-zz99-b.md" in result.stderr


def test_a_named_review_of_another_spec_does_not_cover_the_named_spec(review_doc) -> None:
    """Accident shape: a PASS review of other work quoted in a QA prompt for SPEC-zz99-a."""
    review_doc(_GOOD_REVIEW.replace(f"SPEC-{_PROBE_SLUG}.md", "SPEC-zz99-b.md"), name="REVIEW-zz99-b.md")
    result = _run_gate(subagent_type="qa", prompt="Spec: doc/specs/SPEC-zz99-a.md\nReview: REVIEW-zz99-b.md")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "Upstream" in result.stderr and "SPEC-zz99-a.md" in result.stderr


def test_an_increment_scoped_review_of_the_named_spec_allows(review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace(f"SPEC-{_PROBE_SLUG}.md", "SPEC-zz99-a.md"), name="REVIEW-zz99-a-E.md")
    result = _run_gate(subagent_type="qa", prompt="Spec: doc/specs/SPEC-zz99-a.md increment E\nReview: REVIEW-zz99-a-E.md")
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_the_bugfix_override_does_not_bypass_the_review_gate() -> None:
    """The engineer's override token must not open the QA gate."""
    result = _run_gate(
        subagent_type="qa",
        prompt="NO_SPEC_BUGFIX: the amount parser crashes on a trailing space in the field.",
    )
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "REVIEW-bugfix-" in result.stderr


def test_bugfix_work_uses_a_bugfix_review(review_doc) -> None:
    review_doc(_GOOD_REVIEW, name=_PROBE_BUGFIX_REVIEW)
    result = _run_gate(
        subagent_type="qa",
        prompt=f"NO_SPEC_BUGFIX: amount parser crash on trailing space.\nReview: doc/qa/{_PROBE_BUGFIX_REVIEW}",
    )
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_bugfix_work_does_not_accept_a_non_bugfix_review(review_doc) -> None:
    review_doc(_GOOD_REVIEW, name="REVIEW-zz99-a.md")
    result = _run_gate(
        subagent_type="qa",
        prompt="NO_SPEC_BUGFIX: amount parser crash on trailing space.\nReview: REVIEW-zz99-a.md",
    )
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_bugfix_work_with_a_failing_bugfix_review_blocks(review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", "## Verdict: FAIL"), name=_PROBE_BUGFIX_REVIEW)
    result = _run_gate(
        subagent_type="qa",
        prompt=f"NO_SPEC_BUGFIX: amount parser crash on trailing space.\nReview: {_PROBE_BUGFIX_REVIEW}",
    )
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_the_review_block_message_is_one_actionable_line() -> None:
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, result.stderr
    assert "`reviewer`" in lines[0] and "doc/templates/review-report.md" in lines[0]


# --- One rule: the `Review:` line names the review (QA-delegated-autonomy-E1 defect 1) ---


def _review_of(spec: str) -> str:
    return _GOOD_REVIEW.replace(f"SPEC-{_PROBE_SLUG}.md", spec)


@pytest.mark.parametrize("subagent_type", _REVIEW_GATED)
def test_a_prompt_with_no_review_line_blocks_with_one_line_saying_add_it(subagent_type: str, review_doc) -> None:
    """Even a passing review at the SPEC-derived name does not open QA: no name is guessed."""
    review_doc(_GOOD_REVIEW)
    result = _run_gate(subagent_type=subagent_type, prompt=f"Verify doc/specs/SPEC-{_PROBE_SLUG}.md.")
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert len(lines) == 1, result.stderr
    assert _ADD_REVIEW_LINE in lines[0]


@pytest.mark.parametrize(
    "review_line",
    [
        f"Review: doc/qa/{_PROBE_REVIEW}",
        f"Review: {_PROBE_REVIEW}",
        f"  - Review: doc/qa/{_PROBE_REVIEW}",
        f"* Review: doc/qa/{_PROBE_REVIEW}",
        f"1. Review: doc/qa/{_PROBE_REVIEW}",
        f"**Review:** doc/qa/{_PROBE_REVIEW}",
        f"**Review**: doc/qa/{_PROBE_REVIEW}",
        f"- **Review:** `doc/qa/{_PROBE_REVIEW}`",
    ],
    ids=["plain", "bare-name", "bulleted", "star-bullet", "numbered", "bold", "bold-label", "bulleted-bold-code"],
)
def test_the_review_line_is_read_plain_bulleted_or_bold(review_line: str, review_doc) -> None:
    """A REVIEW quoted for context (missing here) does not count against the named one."""
    review_doc(_GOOD_REVIEW)
    prompt = f"Earlier round: REVIEW-zz99-c.md.\nSpec: doc/specs/SPEC-{_PROBE_SLUG}.md\n{review_line}"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_review_line_mid_sentence_is_not_a_review_line(review_doc) -> None:
    review_doc(_GOOD_REVIEW)
    result = _run_gate(subagent_type="qa", prompt=f"Verify SPEC-{_PROBE_SLUG}.md. Review: {_PROBE_REVIEW}")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert _ADD_REVIEW_LINE in result.stderr


def test_a_review_line_naming_no_review_file_blocks_with_the_add_line_message() -> None:
    result = _run_gate(subagent_type="qa", prompt=f"Verify SPEC-{_PROBE_SLUG}.md.\nReview: pending")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert _ADD_REVIEW_LINE in result.stderr


def test_a_review_line_pointing_at_another_specs_review_blocks(review_doc) -> None:
    """Defect 1: the dependency is named too, but QA is about SPEC-zz99-a only."""
    review_doc(_review_of("SPEC-zz99-b.md"), name="REVIEW-zz99-b.md")
    prompt = "Builds on SPEC-zz99-b.md.\nSpec: doc/specs/SPEC-zz99-a.md\nReview: doc/qa/REVIEW-zz99-b.md"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "Upstream" in result.stderr and "SPEC-zz99-a.md" in result.stderr


def test_a_review_of_the_spec_line_spec_allows_although_a_dependency_is_named(review_doc) -> None:
    """The old derived-name path blocked this correct QA on a missing REVIEW-zz99-b.md."""
    review_doc(_review_of("SPEC-zz99-a.md"), name="REVIEW-zz99-a.md")
    prompt = "QA the change (builds on SPEC-zz99-b.md)\nSpec: SPEC-zz99-a.md\nReview: doc/qa/REVIEW-zz99-a.md"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize("field", ["Spec:", "Slice:", "- **Spec:**"])
def test_a_spec_or_slice_line_names_the_spec_under_test_over_the_first_mention(field: str, review_doc) -> None:
    review_doc(_review_of("SPEC-zz99-b.md"), name="REVIEW-zz99-b.md")
    review_doc(_review_of("SPEC-zz99-a.md"), name="REVIEW-zz99-a.md")
    head = f"Builds on doc/specs/SPEC-zz99-b.md.\n{field} doc/specs/SPEC-zz99-a.md increment E\n"
    allowed = _run_gate(subagent_type="qa", prompt=head + "Review: REVIEW-zz99-a.md")
    blocked = _run_gate(subagent_type="qa", prompt=head + "Review: REVIEW-zz99-b.md")
    assert allowed.returncode == _EXIT_ALLOW, allowed.stderr
    assert blocked.returncode == _EXIT_BLOCK, blocked.stdout


def test_a_slice_line_without_a_spec_path_does_not_fall_back_to_a_spec_named_in_prose(review_doc) -> None:
    """QA re-test 2: the first-mention fallback let a dependency's review open QA."""
    review_doc(_review_of("SPEC-zz99-a.md"), name="REVIEW-zz99-a.md")
    prompt = "Slice: increment E part 1\nCriteria: E-AC2 of doc/specs/SPEC-zz99-a.md\nReview: REVIEW-zz99-a.md"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "Spec: doc/specs/SPEC-<slug>.md" in result.stderr


@pytest.mark.parametrize(
    "upstream",
    ["doc/specs/SPEC-zz99-ab.md", "doc/specs/SPEC-zz99-a.md.bak", "doc/specs/XSPEC-zz99-a.md", "see SPEC-zz99-a"],
)
def test_an_upstream_near_miss_of_the_spec_under_test_blocks(upstream: str, review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace(f"doc/specs/SPEC-{_PROBE_SLUG}.md", upstream), name="REVIEW-zz99-a.md")
    result = _run_gate(subagent_type="qa", prompt="Spec: doc/specs/SPEC-zz99-a.md\nReview: REVIEW-zz99-a.md")
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_a_review_line_with_no_spec_named_blocks_and_asks_for_the_spec(review_doc) -> None:
    """Interpretation: with no spec there is nothing to match `Upstream:` against."""
    review_doc(_GOOD_REVIEW)
    result = _run_gate(subagent_type="qa", prompt=f"Check the new feature please.\nReview: {_PROBE_REVIEW}")
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert len(lines) == 1 and "Spec: doc/specs/SPEC-" in lines[0], result.stderr


def test_only_the_first_review_line_counts(review_doc) -> None:
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", "## Verdict: FAIL"), name="REVIEW-zz99-b.md")
    review_doc(_GOOD_REVIEW)
    prompt = f"Spec: SPEC-{_PROBE_SLUG}.md\nReview: REVIEW-zz99-b.md\nReview: {_PROBE_REVIEW}"
    result = _run_gate(subagent_type="qa", prompt=prompt)
    assert result.returncode == _EXIT_BLOCK, result.stdout


def test_a_review_path_outside_doc_qa_is_read_from_doc_qa_only(review_doc) -> None:
    """Only the file name is used, so `../` cannot point the gate outside doc/qa/."""
    result = _run_gate(subagent_type="qa", prompt=f"Spec: SPEC-{_PROBE_SLUG}.md\nReview: ../../../tmp/{_PROBE_REVIEW}")
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert f"doc/qa/{_PROBE_REVIEW}: not found" in result.stderr


def test_a_bugfix_prompt_with_no_review_line_asks_for_a_bugfix_review() -> None:
    result = _run_gate(subagent_type="qa", prompt="NO_SPEC_BUGFIX: amount parser crash on trailing space.")
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert len(lines) == 1 and 'add "Review: doc/qa/REVIEW-bugfix-<id>.md"' in lines[0], result.stderr


def test_an_unfilled_template_named_on_the_review_line_keeps_qa_shut(review_doc) -> None:
    """Mirror of QA's pin, through the `Review:` line."""
    review_doc((_REPO_ROOT / "doc" / "templates" / "review-report.md").read_text(encoding="utf-8"))
    result = _run_gate(subagent_type="qa", prompt=_QA_PROMPT)
    assert result.returncode == _EXIT_BLOCK, result.stdout
    assert "PASS | FAIL" in result.stderr


@pytest.mark.parametrize("verdict", ["Pass", "PASS.", "PASS — all criteria met", "FAIL"])
def test_a_bad_verdict_block_is_one_line_naming_the_file_and_the_value(verdict: str, review_doc) -> None:
    """Mirror of QA's pin, through the `Review:` line."""
    review_doc(_GOOD_REVIEW.replace("## Verdict: PASS", f"## Verdict: {verdict}"))
    result = _run_gate(subagent_type="frontend-qa", prompt=_QA_PROMPT)
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.returncode == _EXIT_BLOCK
    assert len(lines) == 1, result.stderr
    assert f"doc/qa/{_PROBE_REVIEW}" in lines[0] and repr(verdict) in lines[0]


def test_the_review_gate_does_not_touch_engineer_spawns(probe_doc) -> None:
    """Existing engineer behaviour is unchanged: no review is needed to start building."""
    name = probe_doc("Status: Approved")
    result = _run_gate(subagent_type="ai-engineer", prompt=f"Implement doc/specs/{name}.")
    assert result.returncode == _EXIT_ALLOW, result.stderr


# ---------------------------------------------------------------------------
# SPEC-jarvis-coordinator JC-AC3 — Jarvis is the main thread, never a spawn.
# JC-AC6 — a role-agent brief carries a filled `Tier:` and `Files:` line.
# These cases send the prompt exactly as given: `_run_gate` appends a filled
# header (JC-AC7), which would hide the very lines under test.
# ---------------------------------------------------------------------------

_ROLE_AGENTS = ("pm", "ba-sa", "ai-engineer", "frontend-engineer", "reviewer", "qa", "frontend-qa")
_BRIEF_MESSAGE = "missing or unfilled:"


def _run_brief(subagent_type: str, prompt: str, tool_name: str = "Agent") -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"subagent_type": subagent_type, "prompt": prompt}})
    return subprocess.run(
        [sys.executable, str(_SPAWN_GATE)], input=payload, capture_output=True, text=True, timeout=30, check=False
    )


@pytest.mark.parametrize("subagent_type", ["jarvis", "Jarvis", " jarvis ", "jar​vis", "ｊａｒｖｉｓ"])
def test_jarvis_is_refused_as_a_subagent_before_any_other_check(subagent_type: str) -> None:
    result = _run_brief(subagent_type, "Tier: 1 — x\nFiles: a.py\nNO_SPEC_BUGFIX: a long enough repro line")
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert "Jarvis is the main thread, not a role agent" in result.stderr


@pytest.mark.parametrize("subagent_type", ["jarvis-helper", "general-purpose", "Explore"])
def test_types_that_are_not_jarvis_are_not_refused_as_jarvis(subagent_type: str) -> None:
    result = _run_brief(subagent_type, "")
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize("subagent_type", _ROLE_AGENTS)
def test_a_role_agent_brief_with_neither_line_is_refused_naming_both(subagent_type: str) -> None:
    result = _run_brief(subagent_type, "Please do the work.")
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert f"{_BRIEF_MESSAGE} Tier:, Files:" in result.stderr
    assert "Tier: <0|1|2> — <reason>" in result.stderr and "Files: <paths>" in result.stderr


@pytest.mark.parametrize(
    "prompt",
    [
        "Files: a.py",
        "Tier:\nFiles: a.py",
        "Tier: <0|1|2>\nFiles: a.py",
        "Tier: high\nFiles: a.py",
        "Please set the Tier: 1 line.\nFiles: a.py",
        "Ti​er: 1\nFiles: a.py",
        "tier: 1\nFiles: a.py",
        "NO_SPEC_BUGFIX: the parser crashes on a trailing space\nFiles: a.py",
    ],
    ids=["no-tier", "tier-empty", "tier-placeholder", "tier-high", "tier-mid-sentence", "tier-zero-width",
         "tier-lowercase", "override-does-not-open"],
)
def test_an_unfilled_tier_line_is_refused_naming_tier_only(prompt: str) -> None:
    result = _run_brief("ai-engineer", prompt)
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert f"{_BRIEF_MESSAGE} Tier:" in result.stderr and "Tier:, Files:" not in result.stderr


@pytest.mark.parametrize(
    "prompt",
    [
        "Tier: 1 — x",
        "Tier: 1 — x\nFiles:",
        "Tier: 1 — x\nFiles: <paths>",
        # JC-AM1: an empty `Files:` with no filled list directly under it.
        "Tier: 1 — x\nFiles:\n",
        "Tier: 1 — x\nFiles:\nSome paragraph.\n- a.md",
        "Tier: 1 — x\nFiles:\n- <paths>",
        "Tier: 1 — x\nFiles:\n- ",
        "Tier: 1 — x\nFiles:\n-",
        "Tier: 1 — x\nFiles:\n\n\n",
        "Tier: 1 — x\nFiles:\n  a.md",
        "Tier: 1 — x\nFiles:\n**Task**",
        "Tier: 1 — x\nFiles: <paths>\n- a.md",
        "- Tier: 2 — x\n- Files:\n- Verify with: pytest",
        "Tier: 1 — x\nFiles:\n- Verify with: x\n- a.md",
        # JC-AM3: a label may hold digits, `_` and `-`; it still ends the list.
        "Tier: 0 — x\nFiles:\n- NO_SPEC_BUGFIX: repro steps here",
        "Tier: 1 — x\nFiles:\n- Verify-with: x",
        "Tier: 1 — x\nFiles:\n- Verify_with: x",
        "Tier: 1 — x\nFiles:\n- **NO_SPEC_BUGFIX:** x",
        "Tier: 1 — x\nFiles:\n- Step2: x",
        "Tier: 1 — x\nFiles:\n- Verify-with：x",
        "Tier: 1 — x\nFiles:\n- Verify-with: x\n- a.md",
        "- Tier: 2 — x\n- Files:\n- Verify-with: pytest",
        # JC-AM3 / AM2-ADR-1: known false refusals, by design.
        "Tier: 1 — x\nFiles:\n- Makefile: build rules",
        "Tier: 1 — x\nFiles:\n- docker-compose: x",
    ],
    ids=["no-files", "files-empty", "files-placeholder", "files-last-line-newline", "paragraph-before-list",
         "list-placeholder-only", "list-empty-item", "list-bare-dash", "blank-lines-only", "indented-path-no-marker",
         "bold-heading-not-an-item", "inline-placeholder-then-list", "bulleted-header-files-forgotten",
         "label-item-ends-the-list", "am3-no-spec-bugfix-label", "am3-hyphen-label", "am3-underscore-label",
         "am3-bold-underscore-label", "am3-digit-label", "am3-full-width-colon-label", "am3-label-before-path",
         "am3-bulleted-header-hyphen-label", "am3-makefile-false-refusal", "am3-docker-compose-false-refusal"],
)
def test_an_unfilled_files_line_is_refused_naming_files_only(prompt: str) -> None:
    result = _run_brief("reviewer", prompt)
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert f"{_BRIEF_MESSAGE} Files:" in result.stderr


@pytest.mark.parametrize(
    "prompt",
    [
        "Tier：1 — x\nFiles: a.py",
        "**Tier:** 2 — x\n- Files: a.py",
        "  1. Tier: 0 — x\n* **Files:** a.py, b.py",
        # JC-AM1: an empty `Files:` with a filled list directly under it.
        "Tier: 2 — x\nFiles:\n- a.md\n- b.md",
        "Tier: 2 — x\nFiles:\n* a.md",
        "Tier: 2 — x\nFiles:\n1. a.md",
        "Tier: 2 — x\n**Files:**\n- a.md",
        "Tier: 2 — x\n- Files:\n  - a.md",
        "Tier: 2 — x\nFiles:\n\n- a.md",
        "Tier: 2 — x\r\nFiles:\r\n- a.md\r\n",
        "Tier: 2 — x\nFiles:\n- <paths>\n- a.md",
        "Tier: 2 — x\nFiles:\n- doc/a.md — new: x",
        # JC-AM3: path items the wider label grammar must not swallow.
        "Tier: 2 — x\nFiles:\n- ./Makefile: build rules",
        "Tier: 2 — x\nFiles:\n- `Makefile`: build rules",
        "Tier: 2 — x\nFiles:\n- Makefile — build rules",
        "Tier: 2 — x\nFiles:\n- my-file.txt: x",
        "Tier: 2 — x\nFiles:\n- a.md\n- NO_SPEC_BUGFIX: repro",
    ],
    ids=["full-width-colon", "bold-and-bulleted", "numbered-and-bold", "list-dash", "list-star", "list-numbered",
         "bold-files-list", "bulleted-files-indented-list", "blank-line-then-list", "list-crlf",
         "placeholder-then-filled-item", "path-item-with-colon", "am3-dot-slash-makefile", "am3-backticked-makefile",
         "am3-makefile-dash-note", "am3-dotted-name-before-colon", "am3-path-before-label"],
)
def test_a_filled_brief_header_in_any_field_form_is_accepted(prompt: str) -> None:
    result = _run_brief("pm", prompt)
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize(
    ("subagent_type", "prompt"),
    [
        ("ai-engineer", "Tier: 0 — x\nFiles:\n- NO_SPEC_BUGFIX: repro steps here"),
        ("pm", "Tier: 1 — x\nFiles:\n- Verify-with: x"),
    ],
    ids=["ai-engineer-no-spec-bugfix-label", "pm-hyphen-label"],
)
def test_a_label_only_files_list_is_refused_for_engineer_and_pm(subagent_type: str, prompt: str) -> None:
    """JC-AM3: the override line under an empty `Files:` is a label, not a path —
    rule A5 alone does not stop this brief, so the `Files:` check must."""
    result = _run_brief(subagent_type, prompt)
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert f"{_BRIEF_MESSAGE} Files:" in result.stderr


def test_the_brief_check_runs_before_the_spec_gate_and_the_review_gate() -> None:
    for result in (_run_brief("ai-engineer", "Implement it."), _run_brief("qa", "Test it.")):
        assert result.returncode == _EXIT_BLOCK
        assert _BRIEF_MESSAGE in result.stderr and "rule A5" not in result.stderr and "R19" not in result.stderr


@pytest.mark.parametrize("subagent_type", ["Explore", "Plan", "general-purpose", "claude-code-guide", "zz-unknown", ""])
def test_investigation_and_unknown_types_are_never_checked_for_brief_lines(subagent_type: str) -> None:
    result = _run_brief(subagent_type, "")
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_non_agent_tool_is_never_checked_for_brief_lines() -> None:
    assert _run_brief("reviewer", "", tool_name="Bash").returncode == _EXIT_ALLOW


# ---------------------------------------------------------------------------
# JC-AM5 (AM2-ADR-2): the guard and coordinator_lint rule 6 hold two copies of
# one `Files:` rule. One case table runs through both; any drift is red.
# The adapter test loads the core script, never the reverse (AGENTS.md §10).
# ---------------------------------------------------------------------------


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # a @dataclass looks its module up while it is built
    spec.loader.exec_module(module)
    return module


_GUARD = _load("_guard_agent_spawn_parity", _SPAWN_GATE)
_LINT = _load("_coordinator_lint_parity", _REPO_ROOT / "scripts" / "coordinator_lint.py")

# Inline `<...>` values: the guard refuses them, rule 6 accepts them so the
# brief template stays clean (AM2-ADR-3). The only declared disagreements.
_EXPECTED_DIFF = {"Files: <paths>", "Files: <paths>\n- a.md"}

_PARITY_CASES = [
    # filled
    "Files: a.py",
    "**Files:** a.py",
    "- Files: a.py",
    "  1. **Files**: a.py",
    "Files：a.py",
    "Files:\n- a.md\n- b.md",
    "Files:\n* a.md",
    "Files:\n1. a.md",
    "**Files:**\n- a.md",
    "- Files:\n  - a.md",
    "Files:\n\n- a.md",
    "Files:\n- <paths>\n- a.md",
    "Files:\n- doc/a.md — new: x",
    "Files:\n- ./Makefile: build rules",
    "Files:\n- `Makefile`: build rules",
    "Files:\n- Makefile — build rules",
    "Files:\n- my-file.txt: x",
    "Files:\n- a.md\n- NO_SPEC_BUGFIX: repro",
    # unfilled
    "",
    "Files:",
    "Files:\nSome paragraph.\n- a.md",
    "Files:\n- <paths>",
    "Files:\n- ",
    "Files:\n  a.md",
    "Files:\n**Task**",
    "Files:\n- Verify with: x\n- a.md",
    "Files:\nCriteria: AC1",
    "- Files:\n- Verify-with: pytest",
    "Files:\n- NO_SPEC_BUGFIX: repro steps here",
    "Files:\n- Verify-with: x",
    "Files:\n- Verify_with: x",
    "Files:\n- **NO_SPEC_BUGFIX:** x",
    "Files:\n- Step2: x",
    "Files:\n- Verify-with：x",
    "Files:\n- Verify-with: x\n- a.md",
    "Files:\n- Makefile: build rules",
    "Files:\n- docker-compose: x",
    # declared disagreements
    *sorted(_EXPECTED_DIFF),
]


@pytest.mark.parametrize("case", _PARITY_CASES)
def test_the_guard_and_rule_6_read_files_the_same_way(case: str) -> None:
    guard = _GUARD._files_filled(unicodedata.normalize("NFKC", case).splitlines())
    lint = _LINT._files_filled(case.splitlines())

    if case in _EXPECTED_DIFF:
        assert (guard, lint) == (False, True), case
    else:
        assert guard == lint, case
