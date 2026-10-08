"""Tests for `scripts/correction_rate.py` — the learning metric.

WHY THIS FILE EXISTS. A meter that silently counts zero looks exactly like an
assistant that stopped being corrected. Each count is checked against entries
planted on known dates.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib only)
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import correction_rate as cr  # noqa: E402  (path must be set up first)

_TODAY = dt.date(2026, 10, 20)


def _write(mem: Path, slug: str, kind: str, date: str, mechanism: str | None = None) -> None:
    extra = f"mechanism: {mechanism}\n" if mechanism else ""
    (mem / f"{slug}.md").write_text(
        f"---\nname: {slug}\ntype: {kind}\ndate: {date}\n{extra}---\n\nText.\n", encoding="utf-8"
    )


def test_counts_feedback_per_window_and_ignores_other_types(tmp_path: Path) -> None:
    _write(tmp_path, "a", "feedback", "2026-10-19", "scripts/x.py")
    _write(tmp_path, "b", "feedback", "2026-10-14", "scripts/x.py")
    _write(tmp_path, "c", "feedback", "2026-10-12", "scripts/x.py")
    _write(tmp_path, "d", "project", "2026-10-19")
    _write(tmp_path, "e", "feedback", "2026-09-01")
    m = cr.measure(tmp_path, _TODAY)
    assert (m["last"], m["prev"]) == (2, 1)


def test_reports_lessons_without_a_mechanism_since_the_cutoff(tmp_path: Path) -> None:
    _write(tmp_path, "new", "feedback", "2026-10-19")
    _write(tmp_path, "old", "feedback", "2026-10-01")
    _write(tmp_path, "ok", "feedback", "2026-10-19", "none — a ruling, not a lesson")
    assert cr.measure(tmp_path, _TODAY)["unmechanised"] == ["new.md"]


def test_nested_frontmatter_type_is_read(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text(
        "---\nname: n\nmetadata:\n  type: feedback\n---\n", encoding="utf-8"
    )
    m = cr.measure(tmp_path, dt.date.today())
    assert m["last"] == 1
