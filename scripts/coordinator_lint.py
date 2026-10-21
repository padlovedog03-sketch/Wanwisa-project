#!/usr/bin/env python3
"""Grammar linter for `doc/framework/COORDINATOR-CONSTITUTION.md` (NORTH-STAR
mechanism ๓ — obligations that bind the ORCHESTRATOR, not the workers).

WHY THIS EXISTS. Every other guard in this repo governs an agent. Nothing
governed the coordinator, and the coordinator is the actor measured to be
wrong most often and caught least often by itself (สัจธรรม ๓). Two of the
constitution's five rules reduce to a checkable GRAMMAR: does a claim of a
count/absence carry an origin tag (`MEASURED:`/`INFERRED:`/`RELAYED:`), and
does a directive carry a provenance tag (`PROVENANCE: OWNER|APPROVED
<path>|JUDGEMENT`)? This script checks exactly that grammar — the same way
`scripts/verify_approvals.py` checks that an `Approval:` key resolves in the
registry without checking whether the human meant it.

**What this script does NOT do (stated, not glossed):**

* It does not verify a `MEASURED:` command was actually run, or that a
  `RELAYED:` source is real — only that the required tag is PRESENT next to
  the claim it governs, in the fixed grammar the constitution defines.
* It does not detect free-form claims that never used the `CLAIM:`/
  `INSTRUCTION:` markup at all — that text is invisible to this checker by
  design (see the constitution's own honesty section). This is a grammar
  check over an OPT-IN markup, not natural-language detection over arbitrary
  prose — the substring-matching failure that made the bash
  interception guard block its own test harness is exactly what this design
  avoids repeating one level up.
* Rules ๒ (never describe state from memory) and ๕'s general case (a brief
  conflicting with an approved doc's CONTENT, not just an unapproved doc)
  have no mechanical check here at all — only the required `SELF-REPORT:`
  block, whose PRESENCE and completeness is checked, never whose truth is.

Usage:
    python3 scripts/coordinator_lint.py <file>
    python3 scripts/coordinator_lint.py -            # read stdin
    python3 scripts/coordinator_lint.py --approve-ready <slug> [<slug>…]
        # before handing the owner an approve.sh command: every document the
        # slugs name is committed, clean against HEAD and `In Review`
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_CLAIM_RE = re.compile(r"^CLAIM:\s*(.+?)\s*$", re.MULTILINE)
_INSTRUCTION_RE = re.compile(r"^INSTRUCTION:\s*(.+?)\s*$", re.MULTILINE)
_ORIGIN_TAG_RE = re.compile(r"^(MEASURED|INFERRED|RELAYED):\s*(.+?)\s*$", re.MULTILINE)
_PROVENANCE_RE = re.compile(r"^PROVENANCE:\s*(.+?)\s*$", re.MULTILINE)

_SELF_REPORT_RE = re.compile(r"^SELF-REPORT:\s*$", re.MULTILINE)
_RE_MEASURED_RE = re.compile(r"^RE-MEASURED:\s*(.+?)\s*$", re.MULTILINE)
_CHECKED_DOCS_RE = re.compile(r"^CHECKED-AGAINST-APPROVED-DOCS:\s*(.+?)\s*$", re.MULTILINE)

#: How many lines after a `CLAIM:`/`INSTRUCTION:` line to look for its tag —
#: mirrors `doc/templates/SCAR.md`'s station blocks, where `Entered:`/`Owner:`
#: sit a blank line below the heading rather than immediately after it.
_LOOKAHEAD_LINES = 3

#: Rule 1: a `MEASURED:` command matching any of these truncates its own
#: view — the exact shapes named in `.agents/skills/coordinator-discipline/
#: SKILL.md` rule 1 (head/tail, a hard limit, a swallowed error, `-k`/`-m`
#: filtering, `--lf`).
_TRUNCATING_PATTERNS = (
    re.compile(r"\bhead\b"),
    re.compile(r"\btail\b"),
    re.compile(r"2>/dev/null"),
    re.compile(r"--max-count"),
    re.compile(r"-m\s*\d"),
    re.compile(r"-k\s"),
    re.compile(r"\[:\s*-?\d+\]"),
    re.compile(r"--lf\b|--last-failed"),
)

_VALID_PROVENANCE_VALUES = ("OWNER", "JUDGEMENT")
_APPROVED_PROVENANCE_RE = re.compile(r"^APPROVED\s+(\S+)$")


@dataclass(frozen=True)
class Violation:
    """One rule violation, with the line it was found on."""

    rule: str
    line_no: int
    reason: str


def _lookahead_tag(lines: list[str], start_index: int, tag_pattern: re.Pattern) -> re.Match | None:
    """Search up to `_LOOKAHEAD_LINES` non-blank lines after `start_index`
    for a line matching `tag_pattern`."""
    seen = 0
    for line in lines[start_index + 1 :]:
        if not line.strip():
            continue
        match = tag_pattern.match(line)
        if match:
            return match
        seen += 1
        if seen >= _LOOKAHEAD_LINES:
            break
    return None


def check_claims(text: str) -> list[Violation]:
    """Rule 1 (truncated view) and Rule 3 (unlabelled relay) — both reduce to
    the same grammar: every `CLAIM:` needs an origin tag, and if that tag is
    `MEASURED:`, the command it names must not itself truncate."""
    violations: list[Violation] = []
    lines = text.splitlines()
    tag_line_pattern = re.compile(r"^(MEASURED|INFERRED|RELAYED):\s*(.*)$")

    for match in _CLAIM_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        tag_match = _lookahead_tag(lines, line_no - 1, tag_line_pattern)
        if tag_match is None:
            violations.append(
                Violation(
                    rule="1/3",
                    line_no=line_no,
                    reason=(
                        f"CLAIM {match.group(1)!r} has no MEASURED:/INFERRED:/RELAYED: tag "
                        f"within {_LOOKAHEAD_LINES} lines — an untagged claim of a count or "
                        f"absence is exactly what rule 1 (unseen truncation) and rule 3 "
                        f"(unlabelled relay) both forbid"
                    ),
                )
            )
            continue
        tag_kind, tag_value = tag_match.group(1), tag_match.group(2)
        if tag_kind == "MEASURED":
            for pattern in _TRUNCATING_PATTERNS:
                if pattern.search(tag_value):
                    violations.append(
                        Violation(
                            rule="1",
                            line_no=line_no,
                            reason=(
                                f"CLAIM {match.group(1)!r} is MEASURED by a command that "
                                f"truncates its own view ({pattern.pattern!r} matched in "
                                f"{tag_value!r}) — rule 1 forbids claiming a count or absence "
                                f"from a view that could not have seen all of it"
                            ),
                        )
                    )
    return violations


def check_instructions(text: str, base_dir: Path = _REPO_ROOT) -> list[Violation]:
    """Rule 4: every `INSTRUCTION:` needs a `PROVENANCE:` tag naming OWNER,
    an APPROVED document, or the coordinator's own JUDGEMENT. If APPROVED is
    named, the path must exist and its document must say `Status: Approved`
    — reusing the same check the spawn interception guard already
    performs for one narrow case (spawning an implementer).

    `base_dir` resolves `APPROVED <path>` — overridable so tests can point it
    at a scratch directory instead of this repo's real `doc/`.
    """
    violations: list[Violation] = []
    lines = text.splitlines()

    for match in _INSTRUCTION_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        prov_match = _lookahead_tag(lines, line_no - 1, _PROVENANCE_RE)
        if prov_match is None:
            violations.append(
                Violation(
                    rule="4",
                    line_no=line_no,
                    reason=(
                        f"INSTRUCTION {match.group(1)!r} has no PROVENANCE: tag within "
                        f"{_LOOKAHEAD_LINES} lines — rule 4 requires every instruction to name "
                        f"its origin: OWNER, an APPROVED document, or the coordinator's own "
                        f"JUDGEMENT"
                    ),
                )
            )
            continue
        value = prov_match.group(1).strip()
        approved_match = _APPROVED_PROVENANCE_RE.match(value)
        if value in _VALID_PROVENANCE_VALUES:
            continue
        if approved_match is None:
            violations.append(
                Violation(
                    rule="4",
                    line_no=line_no,
                    reason=(
                        f"PROVENANCE: {value!r} is not OWNER, JUDGEMENT, or "
                        f"'APPROVED <path>' — an unrecognised provenance value is as "
                        f"uncheckable as no value at all"
                    ),
                )
            )
            continue
        doc_path = base_dir / approved_match.group(1)
        if not doc_path.is_file():
            violations.append(
                Violation(
                    rule="5",
                    line_no=line_no,
                    reason=(
                        f"PROVENANCE: APPROVED {approved_match.group(1)!r} names a file that "
                        f"does not exist at {doc_path} — an instruction cannot outrank a "
                        f"document that is not there"
                    ),
                )
            )
            continue
        doc_text = doc_path.read_text(encoding="utf-8")
        status_match = re.search(r"^Status:\s*(.+?)\s*$", doc_text, re.MULTILINE)
        status = status_match.group(1).split("(")[0].strip() if status_match else None
        if status != "Approved":
            violations.append(
                Violation(
                    rule="5",
                    line_no=line_no,
                    reason=(
                        f"PROVENANCE: APPROVED {approved_match.group(1)!r} but that document's "
                        f"own Status is {status!r}, not 'Approved' — rule 5 says the "
                        f"coordinator's instruction never outranks an approved document, and an "
                        f"unapproved one has nothing to outrank with"
                    ),
                )
            )
    return violations


def check_self_report(text: str) -> list[Violation]:
    """Rules ๒ and ๕ (general case) have no mechanical truth-check — this
    checks only that the required self-report FIELDS exist and are filled,
    per the constitution's honesty section."""
    violations: list[Violation] = []
    if not _SELF_REPORT_RE.search(text):
        violations.append(
            Violation(
                rule="2/5",
                line_no=0,
                reason=(
                    "no `SELF-REPORT:` block found — rules 2 and 5 have no mechanical "
                    "truth-check, so the constitution requires this block as the declared "
                    "substitute; its absence is itself the checkable failure"
                ),
            )
        )
        return violations

    if not _RE_MEASURED_RE.search(text):
        violations.append(
            Violation(
                rule="2",
                line_no=0,
                reason="SELF-REPORT: block has no `RE-MEASURED:` line",
            )
        )
    if not _CHECKED_DOCS_RE.search(text):
        violations.append(
            Violation(
                rule="5",
                line_no=0,
                reason="SELF-REPORT: block has no `CHECKED-AGAINST-APPROVED-DOCS:` line",
            )
        )
    return violations


#: Rule 6: every field a `Slice:` brief must fill, with what to put there.
#: `REWORK:` is optional (only on QA rework) and so is not listed.
_BRIEF_FIELDS = (
    ("Files:", "name the exact files to touch or read"),
    ("Criteria:", "name the acceptance criteria in scope"),
    ("Verify with:", "name the tests or tier to run"),
)


#: Optional indentation and list marker (`-`, `*`, `1.`) before a brief field.
#: `[ \t]` and never `\s`, so a match cannot run onto the next line.
_BRIEF_PREFIX = r"^[ \t]*(?:(?:[-*]|\d+\.)[ \t]+)?"


def _brief_field_value(line: str, field: str) -> str | None:
    """The text after `field` on `line`, or None if the line is not that field."""
    match = re.match(_BRIEF_PREFIX + re.escape(field) + r"(.*)$", line)
    return match.group(1).strip() if match else None


def check_briefs(text: str) -> list[Violation]:
    """Rule 6: a brief block — from a `Slice:` line to the next one or the
    end of the text — must carry a filled `Files:`, `Criteria:` and
    `Verify with:` line. Lines may be indented or bulleted. Checked line by
    line, so an empty field never borrows the line below it."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if _brief_field_value(line, "Slice:") is not None]
    violations: list[Violation] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]
        for field, hint in _BRIEF_FIELDS:
            if not any(_brief_field_value(line, field) for line in block):
                violations.append(
                    Violation(
                        rule="6",
                        line_no=start + 1,
                        reason=f"brief has no {field!r} line — {hint}",
                    )
                )
    return violations


#: Rule 7 (SPEC-delegated-autonomy E-AC4, R20): the impact map an engineer
#: brief written under autonomy must carry, with where each value comes from.
_IMPACT_FIELDS = (
    ("Impact:", "the spec's \"Affected tests / affected files\""),
    ("Selected:", "the output of `verify-handoff.sh --list`"),
)
#: Until verify-tiers B and H ship, a source may be unavailable — but only
#: with a stated reason, so the gap stays visible.
_UNAVAILABLE_RE = re.compile(r"unavailable\b(.*)$", re.IGNORECASE)
_UNAVAILABLE_WITH_REASON_RE = re.compile(r"unavailable \(\s*\S[^()]*\)", re.IGNORECASE)


def _impact_value_problem(value: str | None) -> str | None:
    if not value:
        return "is missing or empty"
    if _UNAVAILABLE_RE.match(value) and not _UNAVAILABLE_WITH_REASON_RE.fullmatch(value):
        return "says unavailable with no reason — write `unavailable (<reason>)`"
    return None


def check_impact(text: str) -> list[Violation]:
    """Rule 7: a `Slice:` block with a filled `Under:` line (work under a
    mandate or order) must carry a filled `Impact:` and `Selected:` line.
    Opt-in like R20 itself: a brief with no `Under:` is not judged."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if _brief_field_value(line, "Slice:") is not None]
    violations: list[Violation] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]
        if not any(_brief_field_value(line, "Under:") for line in block):
            continue
        for field, source in _IMPACT_FIELDS:
            value = next((v for v in (_brief_field_value(line, field) for line in block) if v is not None), None)
            problem = _impact_value_problem(value)
            if problem:
                violations.append(
                    Violation(
                        rule="7",
                        line_no=start + 1,
                        reason=f"brief under autonomy: {field!r} {problem} — take it from {source}",
                    )
                )
    return violations


def lint(text: str, base_dir: Path = _REPO_ROOT) -> list[Violation]:
    return (
        check_claims(text)
        + check_instructions(text, base_dir)
        + check_self_report(text)
        + check_briefs(text)
        + check_impact(text)
    )


#: SPEC-jarvis-coordinator JC-AC11. Resolved as `scripts/approve.py` resolves
#: (its DOC_DIRS, `.md`, slug in the filename, case-insensitive) — copied, not
#: imported, because the approval mechanism is out of this spec's scope.
_APPROVABLE_DIRS = ("doc/requirements", "doc/specs", "doc/architecture", "doc/qa", "doc/tasks")
_STATUS_LINE_RE = re.compile(r"^Status: (.+)$", re.MULTILINE)
_APPROVE_READY_USAGE = "usage: coordinator_lint.py --approve-ready <slug> [<slug>…]"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)


def approve_ready(slugs: list[str], root: Path) -> tuple[int, list[str]]:
    """Whether every document the slugs name is committed, clean against HEAD
    and `In Review` — the state approve.sh needs. Returns (exit code, lines):
    0 with the approve.sh command, or 1 with one line per problem."""
    tracked = sorted(
        rel
        for rel in _git(root, "ls-files", "--", "doc").stdout.splitlines()
        if rel.endswith(".md") and any(rel.startswith(f"{d}/") for d in _APPROVABLE_DIRS)
    )
    problems: list[str] = []
    for slug in slugs:
        matches = [rel for rel in tracked if slug.lower() in Path(rel).name.lower()]
        if not matches:
            problems.append(f"no tracked document matches '{slug}' — git add and commit it")
        for rel in matches:
            if _git(root, "cat-file", "-e", f"HEAD:{rel}").returncode != 0:
                problems.append(f"{rel}: not committed — commit before handing over approve.sh")
            elif _git(root, "diff", "--quiet", "HEAD", "--", rel).returncode != 0:
                problems.append(f"{rel}: uncommitted changes — commit before handing over approve.sh")
            else:
                found = _STATUS_LINE_RE.findall((root / rel).read_text(encoding="utf-8"))
                if found != ["In Review"]:
                    shown = ", ".join(found) or "(none)"
                    problems.append(f"{rel}: Status is '{shown}', approve.sh accepts only In Review")
    if problems:
        return 1, problems
    return 0, [f"scripts/approve.sh {' '.join(slugs)} --by <name>"]


def _approve_ready_main(slugs: list[str]) -> int:
    if not slugs or any(not slug.strip() for slug in slugs):
        print(_APPROVE_READY_USAGE, file=sys.stderr)
        return 2
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        print("coordinator-lint: git not found on PATH", file=sys.stderr)
        return 2
    if top.returncode != 0:
        print("coordinator-lint: not inside a git work tree", file=sys.stderr)
        return 2
    code, lines = approve_ready(slugs, Path(top.stdout.strip()))
    print("\n".join(lines))
    return code


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--approve-ready"]:
        return _approve_ready_main(argv[1:])
    if len(argv) != 1:
        print("usage: coordinator_lint.py <file>|-", file=sys.stderr)
        return 2
    text = sys.stdin.read() if argv[0] == "-" else Path(argv[0]).read_text(encoding="utf-8")

    violations = lint(text)
    if not violations:
        print("coordinator-lint: clean — every CLAIM/INSTRUCTION tagged, SELF-REPORT complete.")
        print(
            "LIMIT (stated limit): this checks grammar (a tag is present, in the right shape), "
            "never truth (that the tagged command was really run, or the tagged source is real). "
            "An independent read of the raw evidence is still required — this does not replace it."
        )
        return 0

    print(f"coordinator-lint: {len(violations)} violation(s):")
    for v in sorted(violations, key=lambda x: x.line_no):
        where = f"line {v.line_no}" if v.line_no else "document"
        print(f"  rule {v.rule} ({where}): {v.reason}")
    print(
        "LIMIT (stated limit): this checks grammar, never truth. See doc/framework/"
        "COORDINATOR-CONSTITUTION.md for what each rule can and cannot mechanically catch."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
