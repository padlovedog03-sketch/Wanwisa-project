#!/usr/bin/env python3
"""Portability check for the framework template (RUNTIME-CONTRACT, "เกณฑ์ตัดสินว่าพกพาได้จริง" ข้อ 1).

WHY THIS EXISTS. RUNTIME-CONTRACT says layers ๐ and ๑ must not contain a single
provider name, "ตรวจด้วยเครื่อง ไม่ใช่ด้วยความตั้งใจ" — and the same document
records that the claim was false when first written (provider name in 29
files). A promise with no instrument behind it is exactly the silent failure
this framework exists to refuse, so this script is the instrument.

Two checks:

1. **Provider names** in the layer ๐/๑ files (`CORE_PATHS` minus
   `ADAPTER_EXEMPT`). Adapters (layer ๓) live elsewhere and may name their
   provider freely — that is their job.
2. **Project leaks** — terms from an optional, git-ignored local denylist
   (`scripts/neutrality-denylist.local.txt`, one term per line). The template
   must not carry any one project's vocabulary, but the list of a project's
   terms is itself that project's vocabulary, so it is never committed.

Plain stdlib, no AI required (RUNTIME-CONTRACT layer ๑).

**What this does NOT do (stated, not glossed):**

* After `scripts/bootstrap.sh` fills the `<PROJECT>` placeholder, the repo is
  a project, not the template, and a project may name its own stack. The check
  then prints SKIP with that reason and exits 0 — loudly, never silently.
* It matches words, not meaning. A provider described without its name passes.

Usage:
    python3 scripts/check_neutrality.py
    NEUTRALITY_ROOT=/tmp/probe python3 scripts/check_neutrality.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

#: Layer ๐ (methodology) and layer ๑ (core that runs with no AI present).
CORE_PATHS = ("AGENTS.md", ".agents", "doc/framework", "doc/templates", "scripts")

#: Files inside CORE_PATHS that are adapter wiring or adapter docs, and so may
#: name a provider. Each one is listed, with its reason, in
#: `doc/framework/ADAPTERS.md` — an exemption nobody can see is a hole.
ADAPTER_EXEMPT = frozenset(
    {
        "doc/framework/ADAPTERS.md",  # the capability tables, per adapter
        "doc/framework/SETUP.md",  # step-by-step setup names the tools it sets up
        "scripts/bootstrap.sh",  # scans adapter folders for placeholders
        "scripts/verify-fast.sh",  # routes adapter-hook edits to their tests
        "scripts/check_neutrality.py",  # this file holds the pattern itself
        "scripts/neutrality-denylist.local.txt",  # local, git-ignored
    }
)

#: AI tool vendors and clouds. Word-boundary matched, case-insensitive.
PROVIDER_PATTERN = re.compile(
    r"\b(claude|anthropic|openai|chatgpt|codex|gemini|copilot|cursor|windsurf"
    r"|gpt-\d|azure|aws|bedrock|vertex|github|gitlab)\b",
    re.IGNORECASE,
)

PLACEHOLDER = "<PROJECT>"
DENYLIST_NAME = "scripts/neutrality-denylist.local.txt"
_SKIP_DIRS = {"__pycache__", ".pytest_cache"}


def _root() -> Path:
    return Path(os.environ.get("NEUTRALITY_ROOT", Path(__file__).resolve().parents[1]))


def _core_files(root: Path) -> list[Path]:
    """Real files under CORE_PATHS. Symlinks are skipped: they point at core
    files already counted, and following them would double-report."""
    found: list[Path] = []
    for rel in CORE_PATHS:
        base = root / rel
        if base.is_file():
            found.append(base)
            continue
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if _SKIP_DIRS.intersection(path.relative_to(root).parts):
                continue
            found.append(path)
    return [p for p in found if p.relative_to(root).as_posix() not in ADAPTER_EXEMPT]


def _all_text_files(root: Path) -> list[Path]:
    skip = _SKIP_DIRS | {".git"}
    return [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and not p.is_symlink()
        and not skip.intersection(p.relative_to(root).parts)
        and p.relative_to(root).as_posix() != DENYLIST_NAME
    ]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def provider_hits(root: Path) -> list[str]:
    """`path:line: name` for every provider name in a layer ๐/๑ file."""
    hits: list[str] = []
    for path in _core_files(root):
        text = _read(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in PROVIDER_PATTERN.finditer(line):
                hits.append(f"{path.relative_to(root)}:{lineno}: {match.group(0)}")
    return hits


def leak_hits(root: Path) -> list[str]:
    """`path:line: term` for every local-denylist term anywhere in the repo."""
    denylist = root / DENYLIST_NAME
    if not denylist.is_file():
        return []
    terms = [t.strip() for t in denylist.read_text(encoding="utf-8").splitlines()]
    terms = [t for t in terms if t and not t.startswith("#")]
    if not terms:
        return []
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE)
    hits: list[str] = []
    for path in _all_text_files(root):
        text = _read(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                hits.append(f"{path.relative_to(root)}:{lineno}: {match.group(0)}")
    return hits


def main() -> int:
    root = _root()
    agents = _read(root / "AGENTS.md") or ""
    if PLACEHOLDER not in agents:
        print(
            "SKIP: AGENTS.md no longer carries <PROJECT> — this is a bootstrapped "
            "project, not the template, and may name its own stack."
        )
        return 0
    providers = provider_hits(root)
    leaks = leak_hits(root)
    denylist_state = "present" if (root / DENYLIST_NAME).is_file() else "absent"
    for hit in providers:
        print(f"PROVIDER  {hit}")
    for hit in leaks:
        print(f"LEAK      {hit}")
    print(
        f"neutrality: {len(providers)} provider name(s) in layers 0-1, "
        f"{len(leaks)} project leak(s) (local denylist {denylist_state})"
    )
    return 1 if providers or leaks else 0


if __name__ == "__main__":
    sys.exit(main())
