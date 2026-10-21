"""Doc contracts for the Jarvis coordinator — SPEC-jarvis-coordinator JC-AC8, JC-AC9.

AGENTS.md §0 holds every coordinator duty in tool-neutral words (R2–R8), and
ADAPTERS.md says how each adapter reaches Jarvis and what is only self-report
(JC-L1 … JC-L10). Each anchor is checked by exact substring, and each hostile
case removes it from a planted copy and expects a red naming it.

A separate file from test_doc_contracts.py so this increment does not share a
file with other in-flight increments (one owner per file).

Run: `python3 -m pytest tests/framework/test_doc_contracts_jarvis.py -q`
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_MD = _REPO_ROOT / "AGENTS.md"
_ADAPTERS_MD = _REPO_ROOT / "doc" / "framework" / "ADAPTERS.md"

#: §0 anchors, each tied to the requirement it carries.
_SECTION0_ANCHORS = (
    "ผู้ประสานงาน",  # R2: the coordinator, not only a voice
    "รับทุกข้อความของเจ้าของงาน",  # R1/R2: the main thread every owner message reaches
    "ไม่ใช่แค่น้ำเสียง",  # R2
    "Tier: <0|1|2>",  # R3
    "first reply",  # R3
    "higher tier when unsure",  # R3
    "`Tier:`",  # R4
    "`Files:`",  # R4
    "`Verify with:`",  # R4
    "`REWORK:`",  # R4
    "scope-discipline ข้อ 5",  # R4: the threat-model sentence for reviewer and QA briefs
    "พร้อมข้อแนะนำและเหตุผล",  # R5: every escalation carries a recommendation and the reason
    "สิ่งที่ทำ",  # R7 report field
    "หลักฐาน",  # R7 report field
    "สิ่งที่จาร์วิสตัดสินเอง",  # R7 report field
    "สิ่งที่เจ้าของงานต้องตัดสิน",  # R7 report field
    "`Parked:`",  # R7 report field
    "`mechanism:`",  # R8
    "`doc/memory/`",  # R8
    "coordinator_lint.py --approve-ready <slug>",  # owner slip, JC-L7
)
_R5_HEADER = ("Jarvis ตัดสินเอง", "เจ้าของงานตัดสินเท่านั้น")
#: One anchor per R5 item, checked inside its own column (PRD R5, D5 as written).
_R5_JARVIS_ITEMS = ("ปรับขึ้นเท่านั้น", "ใบสั่งงาน", "ลำดับงานภายใน", "แบบจำลองภัย", "เพดานรอบ", "นอกเกณฑ์",
                    "บทเรียนเป็นกลไก")
_R5_OWNER_ITEMS = ("ประตูอนุมัติ", "กฎธุรกิจ", "§3", "มนุษย์ตัดสินเสมอ", "ลดระดับ", "ยังแดงหลังครบเพดาน")
_SECTION5_ANCHOR = "ทุกใบสั่งงานถึงบทบาทต้องมีบรรทัด `Tier:` และ `Files:`"
_SECTION5_REFUSED = "ถูกปฏิเสธ"

_LIMIT_IDS_A = tuple(f"JC-L{n}" for n in range(1, 10))
_LIMIT_ID_B = "JC-L10"
_ENTRY_ROW_A = ("| coordinator entry", "`agent`", ".claude/agents/jarvis.md", ".claude/hooks/inject_jarvis.py")
_ENTRY_ROW_B = ("| coordinator entry", "AGENTS.md", "ไม่มีอะไรถูกขัดจังหวะ")


def _section(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    return text.split(start, 1)[1].split(end, 1)[0]


def _r5_columns(section0: str) -> tuple[list[str], list[str]] | None:
    """The two columns of the R5 table, non-empty cells only, or None."""
    lines = section0.splitlines()
    header = f"| {_R5_HEADER[0]} | {_R5_HEADER[1]} |"
    if header not in lines:
        return None
    jarvis, owner = [], []
    for line in lines[lines.index(header) + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2:
            return None
        jarvis += [cells[0]] if cells[0] else []
        owner += [cells[1]] if cells[1] else []
    return jarvis, owner


def _agents_problems(text: str) -> list[str]:
    """JC-AC8: every missing §0 or §5 anchor, by name."""
    section0 = _section(text, "\n## 0.", "\n## 1.")
    section5 = _section(text, "\n## 5.", "\n## 6.")
    problems = [f"§0 lacks {a!r}" for a in _SECTION0_ANCHORS if a not in section0]
    if ".claude" in section0:
        problems.append("§0 names an adapter path")
    columns = _r5_columns(section0)
    if columns is None:
        problems.append(f"§0 has no two-column table headed {_R5_HEADER}")
    else:
        for column, items, name in ((columns[0], _R5_JARVIS_ITEMS, "Jarvis"), (columns[1], _R5_OWNER_ITEMS, "owner")):
            if len(column) != len(items):
                problems.append(f"R5 {name} column has {len(column)} items, not {len(items)}")
            problems += [f"R5 {name} column lacks {i!r}" for i in items if not any(i in cell for cell in column)]
    for anchor in (_SECTION5_ANCHOR, _SECTION5_REFUSED):
        if anchor not in section5:
            problems.append(f"§5 lacks {anchor!r}")
    return problems


def _row(section: str, label: str) -> str:
    return next((line for line in section.splitlines() if line.startswith(label)), "")


def _adapters_problems(text: str) -> list[str]:
    """JC-AC9: every missing entry row or LIMIT id, by name."""
    section_a = _section(text, "\n## ก —", "\n## ข —")
    section_b = _section(text, "\n## ข —", "\n## ")
    problems = []
    for section, anchors, name in ((section_a, _ENTRY_ROW_A, "ก"), (section_b, _ENTRY_ROW_B, "ข")):
        row = _row(section, anchors[0])
        problems += [f"section {name} coordinator-entry row lacks {a!r}" for a in anchors if a not in row]
    for ident, section, name in [(i, section_a, "ก") for i in _LIMIT_IDS_A] + [(_LIMIT_ID_B, section_b, "ข")]:
        pattern = re.compile(rf"{re.escape(ident)}(?!\d)")
        if len(pattern.findall(text)) != 1 or not pattern.search(section):
            problems.append(f"{ident} does not appear exactly once, in section {name}")
    return problems


# ---------------------------------------------------------------------------
# JC-AC8 — AGENTS.md §0 and §5
# ---------------------------------------------------------------------------


def test_agents_md_carries_every_coordinator_anchor() -> None:
    assert _agents_problems(_AGENTS_MD.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("anchor", _SECTION0_ANCHORS + (_SECTION5_ANCHOR,))
def test_removing_an_anchor_is_red_naming_it(anchor: str) -> None:
    planted = _AGENTS_MD.read_text(encoding="utf-8").replace(anchor, "")
    assert any(repr(anchor) in p for p in _agents_problems(planted))


@pytest.mark.parametrize("item", _R5_JARVIS_ITEMS + _R5_OWNER_ITEMS)
def test_removing_an_r5_item_is_red_naming_it(item: str) -> None:
    text = _AGENTS_MD.read_text(encoding="utf-8")
    section0 = _section(text, "\n## 0.", "\n## 1.")
    planted = text.replace(section0, section0.replace(item, ""))
    assert any(repr(item) in p for p in _agents_problems(planted))


def test_a_changed_r5_header_is_red() -> None:
    planted = _AGENTS_MD.read_text(encoding="utf-8").replace(_R5_HEADER[1], "เจ้าของงานตัดสิน")
    assert any("two-column table" in p for p in _agents_problems(planted))


def test_a_dropped_r5_row_is_red_naming_the_count() -> None:
    text = _AGENTS_MD.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("|") and "ลดระดับ" in line)
    assert any("items, not" in p for p in _agents_problems(text.replace(row + "\n", "")))


def test_section0_naming_an_adapter_path_is_red() -> None:
    planted = _AGENTS_MD.read_text(encoding="utf-8").replace("first reply", "first reply (.claude/agents)")
    assert "§0 names an adapter path" in _agents_problems(planted)


def test_agents_md_stays_provider_neutral() -> None:
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "check_neutrality.py")],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if "<" + "PROJECT>" not in _AGENTS_MD.read_text(encoding="utf-8"):
        # A bootstrapped project may name its own stack; the checker's documented answer there.
        assert result.returncode == 0 and result.stdout.startswith("SKIP:"), result.stdout + result.stderr
        return
    assert result.returncode == 0 and "0 provider name(s)" in result.stdout, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# JC-AC9 — ADAPTERS.md entry rows and JC-L1 … JC-L10
# ---------------------------------------------------------------------------


def test_adapters_md_carries_both_entry_rows_and_every_limit_id() -> None:
    assert _adapters_problems(_ADAPTERS_MD.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("ident", _LIMIT_IDS_A + (_LIMIT_ID_B,))
def test_a_missing_limit_id_is_red_naming_it(ident: str) -> None:
    text = _ADAPTERS_MD.read_text(encoding="utf-8")
    planted = re.sub(rf"{re.escape(ident)}(?!\d)", "JC-LX", text)
    assert any(p.startswith(f"{ident} ") for p in _adapters_problems(planted))


@pytest.mark.parametrize("ident", ["JC-L1", "JC-L10"])
def test_a_duplicated_limit_id_is_red(ident: str) -> None:
    text = _ADAPTERS_MD.read_text(encoding="utf-8") + f"\n{ident} again\n"
    assert any(p.startswith(f"{ident} ") for p in _adapters_problems(text))


@pytest.mark.parametrize(("section", "label"), [("ก", "\n## ก —"), ("ข", "\n## ข —")])
def test_a_missing_entry_row_is_red_naming_its_section(section: str, label: str) -> None:
    text = _ADAPTERS_MD.read_text(encoding="utf-8")
    body = _section(text, label, "\n## ข —" if section == "ก" else "\n## ")
    row = _row(body, "| coordinator entry")
    assert row, f"no entry row in section {section}"
    problems = _adapters_problems(text.replace(row + "\n", ""))
    assert any(p.startswith(f"section {section} coordinator-entry row") for p in problems)
