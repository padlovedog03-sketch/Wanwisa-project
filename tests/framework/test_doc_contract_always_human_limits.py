"""Doc contract: ADAPTERS.md declares what the always-human guards do not catch.

SPEC-delegated-autonomy-am1-guards-catch-accidents §Declared limits: the guards
catch accidents, and each spelling they do not refuse is written down instead
of chased. A limit that is no longer named here is a hole nobody can see.

Run: `python3 -m pytest tests/framework/test_doc_contract_always_human_limits.py -q`
"""

from __future__ import annotations

from pathlib import Path

_ADAPTERS = Path(__file__).resolve().parents[2] / "doc" / "framework" / "ADAPTERS.md"
_HEADING = "## รายการที่มนุษย์ตัดสินเสมอ — จุดบังคับต่อตัวเชื่อม"

LIMIT_CLASSES = ("alias", "bisect", "awk", "stash", "restore", "symlink", "caffeinate", "--repo=", "cd $HOME", "perl -pi")
READ_ONLY_LINE = "งานอ่านอย่างเดียว (`find -name`, `ruff check`, `--help`, `nl`, `sort`, `bash -n`, `py_compile`)"


def _always_human_section() -> str:
    text = _ADAPTERS.read_text(encoding="utf-8")
    assert _HEADING in text, f"{_HEADING!r} is missing from ADAPTERS.md"
    section = text.split(_HEADING, 1)[1]
    return section.split("\n## ", 1)[0]


def test_the_always_human_section_names_every_declared_limit_and_the_read_only_line() -> None:
    section = _always_human_section()
    missing = [c for c in LIMIT_CLASSES if c not in section]
    assert not missing, f"ADAPTERS.md always-human section no longer declares: {missing}"
    assert READ_ONLY_LINE in section, "ADAPTERS.md always-human section lost the read-only line"
