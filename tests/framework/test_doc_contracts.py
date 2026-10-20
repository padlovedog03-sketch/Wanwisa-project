"""Document contracts: rules that live in prose, checked by machine.

WHY THIS FILE EXISTS. A capability an adapter declares in prose and nobody
checks drifts the day the code changes, and the reader trusts the table over
the code. Each test here pins one sentence the spec requires a document to
carry (SPEC-verify-tiers-merge-gate.md, ADR-11: document contracts are tests
inside an existing gate step).

Run: `python3 -m pytest tests/framework/test_doc_contracts.py -q`   (stdlib only)
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
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
