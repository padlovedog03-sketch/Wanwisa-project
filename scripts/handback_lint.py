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

`--spec <spec>` (R30) also checks an engineer's `Self-check:` block: one line
`<AC-id>: <command> → <result>` for every AC id in the spec's first table
column. The block runs from the `Self-check:` line to the first blank line.
Again presence only: it cannot tell whether the command was really run.
A line whose result is `not done` is an open AC: listed, and never counted as met.

`--only <prefix>` (repeatable) limits the required ACs to those whose id starts
with the prefix, so a one-increment handoff on a multi-increment spec is checked
against its own ACs only. A prefix that matches no AC is a usage error (exit 2).

Usage:
    python3 scripts/handback_lint.py <file>
    python3 scripts/handback_lint.py -            # read stdin
    python3 scripts/handback_lint.py --spec doc/specs/SPEC-x.md -
    python3 scripts/handback_lint.py --spec doc/specs/SPEC-x.md --only H- -
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: The fields every handback must carry, in the handoff-protocol's wording.
REQUIRED_FIELDS = ("Could not reach", "Substituted")

#: A field line may sit in a list ("- ", "5. ") and may be bolded.
#: Separators are `[ \t]*`, not `\s*`: `\s` matches newlines, which let an empty
#: field swallow the next line as its value.
_FIELD_RE = re.compile(
    r"^[ \t]*(?:[-*]|\d+\.)?[ \t]*\**(" + "|".join(REQUIRED_FIELDS) + r")\**[ \t]*:[ \t]*\**[ \t]*(.*?)[ \t]*$",
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


#: An AC id: `AC1`, `H-AC2`, `AC-AC14`, `J2-AC1` (an increment prefix may carry a digit).
_AC_ID = r"(?:[A-Z][A-Z0-9]*-)?AC\d+"

#: An AC id in a spec's first table column.
_SPEC_AC_RE = re.compile(r"^\|\s*(" + _AC_ID + r")\s*\|", re.MULTILINE)

#: `- AC1: <command> → <result>`. `[ \t]*`, never `\s*`: an empty result must
#: not swallow the next line as its value (the fe59b02 bug).
_SELF_CHECK_LINE_RE = re.compile(r"^[ \t]*[-*]?[ \t]*(" + _AC_ID + r")[ \t]*:[ \t]*(.*?)[ \t]*(?:→|->)[ \t]*(.*?)[ \t]*$")


def spec_ac_ids(spec_text: str) -> list[str]:
    """AC ids from the spec's first table column, in order, without duplicates."""
    return list(dict.fromkeys(_SPEC_AC_RE.findall(spec_text)))


def lint_self_check(text: str, ac_ids: list[str]) -> list[str]:
    """One problem per AC id with no self-check line, and per line missing a command or result."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^[ \t]*\**Self-check:\**[ \t]*$", line)), None)
    if start is None:
        return ["no `Self-check:` block — one line `<AC-id>: <command> → <result>` per AC"]
    found: dict[str, tuple[str, str]] = {}
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        match = _SELF_CHECK_LINE_RE.match(line)
        if match:
            found.setdefault(match.group(1), (match.group(2), match.group(3)))
    problems = []
    for ac in ac_ids:
        if ac not in found:
            problems.append(f"self-check missing for {ac}")
        elif found[ac][1].lower().startswith("not done"):
            problems.append(f"self-check for {ac} is not done — open AC")
        elif not found[ac][0]:
            problems.append(f"self-check for {ac} has no command — name what you ran")
        elif not found[ac][1]:
            problems.append(f"self-check for {ac} has no result — give the command's outcome")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="handback_lint.py")
    parser.add_argument("--spec", help="check the Self-check block against this spec's AC ids")
    parser.add_argument("--only", action="append", metavar="PREFIX", help="require only AC ids starting with PREFIX")
    parser.add_argument("handback", help="handback file, or - for stdin")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.only and not args.spec:
        parser.error("--only needs --spec")
    ac_ids: list[str] | None = None
    if args.spec:
        ac_ids = spec_ac_ids(Path(args.spec).read_text(encoding="utf-8"))
        if not ac_ids:
            print(f"handback-lint: {args.spec} has no AC rows (`| AC1 |` …) — nothing to check against", file=sys.stderr)
            return 2
        for prefix in args.only or []:
            if not any(ac.startswith(prefix) for ac in ac_ids):
                print(f"handback-lint: --only {prefix} matches no AC in {args.spec}", file=sys.stderr)
                return 2
        if args.only:
            ac_ids = [ac for ac in ac_ids if ac.startswith(tuple(args.only))]
    text = sys.stdin.read() if args.handback == "-" else Path(args.handback).read_text(encoding="utf-8")

    problems = lint(text)
    if ac_ids is not None:
        problems += lint_self_check(text, ac_ids)
    if not problems:
        if ac_ids is not None:
            matching = f" matching {', '.join(args.only)}" if args.only else ""
            print(f"handback-lint: self-check lines present for all {len(ac_ids)} AC(s){matching}.")
        print("handback-lint: clean — `Could not reach:` and `Substituted:` both filled.")
        print("LIMIT: presence only, never truth. Read the diff.")
        return 0
    print(f"handback-lint: {len(problems)} problem(s):")
    for problem in problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
