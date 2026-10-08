"""Tests for `scripts/memory_lint.py` — the project-memory lifecycle check.

WHY THIS FILE EXISTS. The failure it guards against was silent for weeks: an
append-only memory index outgrew its load limit and hid its newest rulings.
Each rule below is proven by planting the violation (NORTH-STAR truth 2), so a
lint that quietly stopped checking would turn this file red.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib only)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "memory_lint.py"

sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import memory_lint as ml  # noqa: E402  (path must be set up first)


def _entry(slug: str, status: str = "active", **extra: str) -> str:
    fields = {
        "name": slug,
        "description": "one line",
        "type": "feedback",
        "status": status,
        "date": "2026-10-08",
        "source": "owner, chat 2026-10-08",
        "mechanism": "none — fixture entry, no lesson",
        **extra,
    }
    body = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{body}\n---\n\nText.\n"


def _memory(tmp_path: Path, entries: dict[str, str], index: list[str]) -> Path:
    mem = tmp_path / "memory"
    mem.mkdir()
    for slug, text in entries.items():
        (mem / f"{slug}.md").write_text(text, encoding="utf-8")
    (mem / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    (mem / "README.md").write_text("# how to write memory\n", encoding="utf-8")
    return mem


def test_this_repo_memory_is_clean() -> None:
    env = {**os.environ}
    env.pop("MEMORY_DIR", None)
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)], capture_output=True, text=True, env=env, check=False
    )
    assert result.returncode == 0, result.stdout


def test_clean_memory_has_no_errors(tmp_path: Path) -> None:
    mem = _memory(tmp_path, {"a": _entry("a")}, ["- [A](a.md) — hook"])
    assert ml.check(mem) == []


def test_missing_source_is_caught(tmp_path: Path) -> None:
    text = _entry("a").replace("source: owner, chat 2026-10-08\n", "")
    mem = _memory(tmp_path, {"a": text}, ["- [A](a.md)"])
    assert "a.md: missing `source`" in ml.check(mem)


def test_superseded_without_successor_is_caught(tmp_path: Path) -> None:
    mem = _memory(tmp_path, {"old": _entry("old", "superseded")}, [])
    assert "old.md: superseded but no `superseded_by`" in ml.check(mem)


def test_superseded_by_a_superseded_entry_is_caught(tmp_path: Path) -> None:
    entries = {
        "old": _entry("old", "superseded", superseded_by="mid"),
        "mid": _entry("mid", "superseded", superseded_by="new"),
        "new": _entry("new"),
    }
    mem = _memory(tmp_path, entries, ["- [New](new.md)"])
    assert ml.check(mem) == ["old.md: superseded_by `mid` is not active"]


def test_index_listing_a_superseded_entry_is_caught(tmp_path: Path) -> None:
    entries = {"old": _entry("old", "superseded", superseded_by="new"), "new": _entry("new")}
    mem = _memory(tmp_path, entries, ["- [Old](old.md)", "- [New](new.md)"])
    assert ml.check(mem) == ["INDEX.md: lists `old.md`, which is not active"]


def test_active_entry_missing_from_index_is_caught(tmp_path: Path) -> None:
    mem = _memory(tmp_path, {"a": _entry("a"), "b": _entry("b")}, ["- [A](a.md)"])
    assert ml.check(mem) == [
        "INDEX.md: active entry `b.md` is not listed — it will never be read"
    ]


def test_index_over_budget_is_caught(tmp_path: Path) -> None:
    filler = [f"line {i}" for i in range(ml.INDEX_BUDGET)]
    mem = _memory(tmp_path, {"a": _entry("a")}, ["- [A](a.md)", *filler])
    errors = ml.check(mem)
    assert len(errors) == 1 and errors[0].startswith(
        f"INDEX.md: {ml.INDEX_BUDGET + 1} lines, budget {ml.INDEX_BUDGET}"
    )


def test_cli_exits_nonzero_on_violation(tmp_path: Path) -> None:
    mem = _memory(tmp_path, {"a": _entry("a")}, [])
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={**os.environ, "MEMORY_DIR": str(mem)},
        check=False,
    )
    assert result.returncode == 1
    assert "it will never be read" in result.stdout


# Rule 5 — a lesson names the mechanism that now enforces it.


def test_feedback_without_mechanism_is_refused(tmp_path: Path) -> None:
    text = _entry("a").replace("mechanism: none — fixture entry, no lesson\n", "")
    mem = _memory(tmp_path, {"a": text}, ["- [A](a.md) — hook"])
    assert any("no `mechanism`" in e for e in ml.check(mem))


def test_mechanism_none_needs_a_reason(tmp_path: Path) -> None:
    mem = _memory(tmp_path, {"a": _entry("a", mechanism="none")}, ["- [A](a.md) — hook"])
    assert any("needs `— <reason>`" in e for e in ml.check(mem))


def test_mechanism_path_must_exist(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "doc").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "real.py").write_text("", encoding="utf-8")
    mem = _memory(repo / "doc", {"a": _entry("a", mechanism="scripts/ghost.py")}, ["- [A](a.md) — hook"])
    assert any("does not exist" in e for e in ml.check(mem))
    (mem / "a.md").write_text(_entry("a", mechanism="scripts/real.py"), encoding="utf-8")
    assert ml.check(mem) == []


def test_lessons_before_the_cutoff_are_grandfathered(tmp_path: Path) -> None:
    text = _entry("a", date="2026-10-07").replace("mechanism: none — fixture entry, no lesson\n", "")
    mem = _memory(tmp_path, {"a": text}, ["- [A](a.md) — hook"])
    assert ml.check(mem) == []
