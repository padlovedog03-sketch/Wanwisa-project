"""Doc-contract tests: rules that live only in prose, pinned by their anchors.

WHY THIS FILE EXISTS. A rule that exists only as a sentence in a skill file
disappears the day someone tidies the paragraph. These tests pin the anchors
of rules the approved spec (doc/specs/SPEC-verify-tiers-merge-gate.md) places
in prose, so deleting one goes red instead of going unnoticed. They check that
the rule is stated, never that agents follow it — its effect is measured by
the trial (M14), not here.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib only)
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
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
