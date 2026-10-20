#!/usr/bin/env python3
"""Grammar check for an agent's handoff message (`.agents/skills/handoff-protocol/`
§ Handoff Message, fields 5-6).

WHY THIS EXISTS. The costliest failure class in this framework is the one that
sends no signal (`doc/framework/WHY.md` §2). An agent that could not reach a
file, a service or an access right, and quietly worked around it with a mock,
a stub or a guess, hands back a report that reads exactly like a clean one.
Two fields make that visible: `Could not reach:` and `Substituted:`. Each must
be present and filled — `none` is a valid answer, an empty field is not, and a
missing field is the failure.

**What this script does NOT do (stated, not glossed):**

* It checks that the two fields are present and non-empty, never that they
  are true. An agent can write `none` over a mock. Reading the diff is still
  required.
* It runs only when the coordinator pipes a handback into it. Nothing calls it
  automatically — it is an opt-in grammar check, like `coordinator_lint.py`.

Usage:
    python3 scripts/handback_lint.py <file>
    python3 scripts/handback_lint.py -            # read stdin
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: The fields every handback must carry, in the handoff-protocol's wording.
REQUIRED_FIELDS = ("Could not reach", "Substituted")

#: A field line may sit in a list ("- ", "5. ") and may be bolded.
_FIELD_RE = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*\**(" + "|".join(REQUIRED_FIELDS) + r")\**\s*:\s*\**\s*(.*?)\s*$",
    re.MULTILINE,
)


def lint(text: str) -> list[str]:
    """Return one problem per required field that is missing or empty."""
    found: dict[str, str] = {}
    for match in _FIELD_RE.finditer(text):
        found.setdefault(match.group(1), match.group(2).strip("* "))
    problems = []
    for field in REQUIRED_FIELDS:
        if field not in found:
            problems.append(f"`{field}:` is missing — write `none` if there was nothing")
        elif not found[field]:
            problems.append(f"`{field}:` is empty — write `none` if there was nothing")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: handback_lint.py <file>|-", file=sys.stderr)
        return 2
    text = sys.stdin.read() if argv[0] == "-" else Path(argv[0]).read_text(encoding="utf-8")

    problems = lint(text)
    if not problems:
        print("handback-lint: clean — `Could not reach:` and `Substituted:` both filled.")
        print("LIMIT: presence only, never truth. Read the diff.")
        return 0
    print(f"handback-lint: {len(problems)} problem(s):")
    for problem in problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
