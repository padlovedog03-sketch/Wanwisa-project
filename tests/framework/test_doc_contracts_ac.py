"""Doc contract for increment A+C (amendment 2): ADAPTERS.md states the ban
scanner's declared limits.

Spec: doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md, affected-files
row `tests/framework/test_doc_contracts.py`. That file does not exist on this
branch yet, so the case lives here; fold it in when the branches merge.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADAPTERS = _REPO_ROOT / "doc" / "framework" / "ADAPTERS.md"
_HEADING = "## ประตูตรวจ (verify tiers) — ข้อจำกัดที่ประกาศไว้"


def test_adapters_states_the_verify_tier_limits() -> None:
    text = _ADAPTERS.read_text(encoding="utf-8")

    assert _HEADING in text.splitlines(), "ADAPTERS.md lacks the verify-tiers limits heading"
    section = text.split(_HEADING, 1)[1]
    assert "VERIFY_EXTRA_BANNED" in section
    assert "limit:" in section
