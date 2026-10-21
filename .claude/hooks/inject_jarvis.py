#!/usr/bin/env python3
"""UserPromptSubmit fallback for the Jarvis entry — SPEC-jarvis-coordinator D6, JC-AC4.

WHY THIS EXISTS: the committed `agent` setting makes every main thread run as
`jarvis`. A local or user setting, or a typed flag, can replace it. When the
replacement is "no agent", the payload's `agent_type` is empty (probe P12), and
this hook prints the Jarvis pointer so the bare main thread still reads it.
When `agent_type` names any agent — `jarvis` itself, or one the owner chose on
purpose (PRD A3, owner decision O2) — it prints nothing.

The pointer has one home: the body of `.claude/agents/jarvis.md`, below its
frontmatter. This hook holds no text of its own.

Always exits 0: a bug here must not block the owner's prompt.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

_AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n(.*)\Z", re.DOTALL)


def _normalise(value: str) -> str:
    """NFKC, no whitespace or format characters, case-folded — as the spawn guard."""
    value = unicodedata.normalize("NFKC", value)
    return "".join(ch for ch in value if not ch.isspace() and unicodedata.category(ch) != "Cf").casefold()


def pointer_text(agents_dir: Path) -> str | None:
    """The body of `jarvis.md` below its frontmatter, or None if unreadable."""
    try:
        text = (agents_dir / "jarvis.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _FRONTMATTER.match(text)
    return match.group(1).strip() if match else None


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        return
    if not isinstance(payload, dict) or _normalise(str(payload.get("agent_type") or "")):
        return
    text = pointer_text(_AGENTS_DIR)
    if text:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
