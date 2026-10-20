#!/usr/bin/env python3
"""PreToolUse gate on the `Agent` (subagent-spawn) tool — the framework spec §3.A5, ADR-2.

WHY THIS EXISTS: AGENTS.md §6 rule 2 says an implementer agent must refuse to
start when its upstream spec is not `Approved`. That was prose, and prose does
not fail. This blocks the spawn instead.

**Scope is deliberately narrow.** Only `ai-engineer` and `frontend-engineer` are
gated on a spec, and only `qa` and `frontend-qa` on a review (below). The seven
role agents (`pm`, `ba-sa`, both engineers, `reviewer`, both QA types) are checked
for brief *presence* only: a filled `Tier:` and `Files:` line (SPEC-jarvis-coordinator
JC-AC6), never whether either is true. `Explore`, `Plan`, `general-purpose` and
every other type stay ungated: gating them would block ordinary investigation,
and a guard with false positives gets switched off — that is the documented
reason Set 1's `guard_bash.py` had to be rewritten from substring matching to
command-position matching. `jarvis` is refused outright (JC-AC3): it is the main
thread, and its definition is still listed as a subagent.

**The review gate (SPEC-delegated-autonomy E-AC2, R19, D5 — all work, not opt-in).**
One explicit rule: a `qa` or `frontend-qa` prompt carries a line
`Review: doc/qa/REVIEW-<name>.md` (plain, bulleted or bold, like a brief field),
and the gate checks THAT file only — the first such line; no name is derived
and REVIEW files mentioned elsewhere in the prompt are ignored. The file must
exist in `doc/qa/` of the tree this hook lives in (the main tree, for the
registered hook), have a PASS `Verdict:`, a `Reviewer-run:` different from its
`Author-run:`, and an `Upstream:` naming the spec under test: the SPEC on a
`Slice:` or `Spec:` line, else the first SPEC the prompt names. `NO_SPEC_BUGFIX:`
work names a `REVIEW-bugfix-<id>.md` and has no spec to match. The engineer's
override token never opens this gate. STATED LIMITS: different run IDs prove two
runs, not that the reviewer ignored the author's conversation — that part is the
`reviewer` agent definition's instruction; and only the file name on the
`Review:` line is used, so any directory written before it is ignored.

**Fail-closed, with an explicit override.** When the prompt names no spec the
spawn is blocked, because a warning on a spawn is useless: by the time anyone
reads it the subagent is already running. AGENTS.md §5 does permit "small
bugfixes may start at the engineer", so a no-spec spawn is sometimes legitimate
— hence an override token rather than a prohibition, modelled on Set 1's
`ALLOW_DESTRUCTIVE=1`: the choice becomes visible in the transcript instead
of silent.

**STATED LIMIT, not glossed (stated limit):** this reads the `Status:` line
out of a repo file that an agent can edit. It is only as strong as the approval
registry (item B3) and the CI check on a protected branch (B4). On its own it is
theatre, and the spec forbids shipping it alone.

Exit codes: 0 allow, 2 block with stderr shown to the model. Malformed input
exits 0 — a hook bug must not wedge every spawn.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

# Only the two implementer types are gated on a spec.
_GATED_SUBAGENT_TYPES = frozenset({"ai-engineer", "frontend-engineer"})

# Only the two QA types are gated on a review (E-AC2). Everything else passes.
_REVIEW_GATED_SUBAGENT_TYPES = frozenset({"qa", "frontend-qa"})
_REVIEW_DIR = "doc/qa"
_REVIEW_TEMPLATE = "doc/templates/review-report.md"
_BUGFIX_REVIEW_PREFIX = "REVIEW-bugfix-"
_REVIEW_REFERENCE_PATTERN = re.compile(r"(?<![A-Za-z0-9._-])(REVIEW-[A-Za-z0-9._-]+\.md)")
# A whole `SPEC-*.md` token: `XSPEC-a.md`, `SPEC-a.md.bak` and `SPEC-a` are not `SPEC-a.md`.
_SPEC_NAME_PATTERN = re.compile(r"(?<![A-Za-z0-9._-])(SPEC-[A-Za-z0-9._-]+\.md)(?!\.?[A-Za-z0-9_-])")
# A prompt field line, plain, bulleted (`-`, `*`, `1.`) or bold — as coordinator_lint rule 6.
_FIELD_LINE = r"^[ \t]*(?:(?:[-*]|\d+\.)[ \t]+)?(?:\*\*)?(?:{field})(?:\*\*)?[ \t]*:(?:\*\*)?(.*)$"
_REVIEW_LINE_PATTERN = re.compile(_FIELD_LINE.format(field="Review"), re.MULTILINE)

# SPEC-jarvis-coordinator: the coordinator is never a spawn (JC-AC3), and a brief
# to a role agent carries a filled `Tier:` and `Files:` line (JC-AC6).
_COORDINATOR = "jarvis"
_ROLE_AGENTS = frozenset(
    {"pm", "ba-sa", "ai-engineer", "frontend-engineer", "reviewer", "qa", "frontend-qa"}
)
_TIER_LINE_PATTERN = re.compile(_FIELD_LINE.format(field="Tier"), re.MULTILINE)
_FILES_LINE_PATTERN = re.compile(_FIELD_LINE.format(field="Files"), re.MULTILINE)
_SUBJECT_LINE_PATTERN = re.compile(_FIELD_LINE.format(field="Slice|Spec"), re.MULTILINE)
# `Verdict:` as a plain line, a heading or bold — never inside another line,
# so a decorated `Status: Done (Verdict: PASS)` is not read as one.
_VERDICT_LINE_PATTERN = re.compile(r"^[ \t]*(?:#+[ \t]*)?(?:\*\*)?Verdict(?:\*\*)?[ \t]*:(?:\*\*)?(.*)$", re.MULTILINE)
_PASS_VALUE_PATTERN = re.compile(r"PASS(?:[ \t]*\([^()|]*\))?")
_RUN_LINE = r"^[ \t]*(?:\*\*)?{field}(?:\*\*)?[ \t]*:(?:\*\*)?(.*)$"

# The override, and what it must carry. A bare token would be a rubber stamp;
# requiring a reproduction line makes the claim checkable by a human reader.
_OVERRIDE_TOKEN = "NO_SPEC_BUGFIX:"
_MIN_OVERRIDE_REASON_CHARS = 10

# Upstream references we accept in a prompt: a bare filename or a repo path.
#
# The prefixes must match what `.agents/skills/handoff-protocol/SKILL.md` mandates,
# and each one lives in its own directory — a DESIGN document is not in `doc/specs/`.
# Keeping the two in sync matters: a prefix this pattern does not accept cannot be
# named as an upstream at all, so the gate silently demands the override token for
# work that legitimately has an approved document behind it.
_UPSTREAM_DIRS = {
    "SPEC": "doc/specs",
    "DESIGN": "doc/architecture",
    "ADR": "doc/architecture",
}
_SPEC_REFERENCE_PATTERN = re.compile(
    r"(?:doc/(?:specs|architecture)/)?((?:" + "|".join(_UPSTREAM_DIRS) + r")-[A-Za-z0-9._-]+\.md)"
)

_ALLOWED_STATUS = "Approved"
_STATUS_LINE_PATTERN = re.compile(r"^\s*(?:\*\*)?Status(?:\*\*)?\s*:\s*(.+?)\s*$", re.MULTILINE)


def _repo_root() -> Path:
    """The repo this hook lives in. `$CLAUDE_PROJECT_DIR` is not relied upon
    because the hook must also work when invoked directly by a test."""
    return Path(__file__).resolve().parents[2]


def _read_status(spec_path: Path) -> str | None:
    """The first `Status:` value in the file, or None if there is none."""
    try:
        text = spec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _STATUS_LINE_PATTERN.search(text)
    if not match:
        return None
    # Take the leading word only: the pre-B2 corpus decorates the value with
    # parentheticals and, in a few files, whole paragraphs.
    return match.group(1).split("(")[0].strip().rstrip(".").strip()


def _block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def _normalise_run_id(value: str) -> str:
    """A run ID as compared: NFKC, no whitespace or invisible format characters,
    case-folded — so `A111`, ` a111 ` and `a<zero-width>111` all equal `a111`."""
    value = unicodedata.normalize("NFKC", value)
    value = "".join(ch for ch in value if not ch.isspace() and unicodedata.category(ch) != "Cf")
    return value.casefold()


def _normalise_type(value: str) -> str:
    """A subagent type as compared with `_COORDINATOR`: the run-ID normalisation."""
    return _normalise_run_id(value)


def _missing_brief_lines(prompt: str) -> list[str]:
    """The brief lines a role-agent prompt lacks or leaves unfilled, in order.
    Read after NFKC, so a full-width colon counts; a zero-width character
    inside the field name does not."""
    text = unicodedata.normalize("NFKC", prompt)
    tiers = [v.replace("*", "").strip() for v in _TIER_LINE_PATTERN.findall(text)]
    files = [v.replace("*", "").strip() for v in _FILES_LINE_PATTERN.findall(text)]
    missing = []
    if not any(t[:1] in ("0", "1", "2") and t for t in tiers):
        missing.append("Tier:")
    if not any(f and not f.startswith("<") for f in files):
        missing.append("Files:")
    return missing


def _review_problem(path: Path, spec: str | None) -> str | None:
    """Why the review at `path` does not open the QA gate, or None if it does.
    When `spec` is given the review's `Upstream:` must name exactly it.
    Never raises: a crash exits 1, and only exit 2 blocks."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "not found"
    except (OSError, UnicodeDecodeError) as exc:
        return f"unreadable ({type(exc).__name__})"
    if not text.strip():
        return "empty"
    verdicts = [v.replace("*", "").strip() for v in _VERDICT_LINE_PATTERN.findall(text)]
    if not verdicts:
        return "no `Verdict:` line"
    for verdict in verdicts:
        if "FAIL" in verdict.upper() or not _PASS_VALUE_PATTERN.fullmatch(verdict):
            return f"Verdict is {verdict!r}, not PASS"
    run_ids = {}
    for field in ("Author-run", "Reviewer-run"):
        match = re.search(_RUN_LINE.format(field=field), text, re.MULTILINE)
        value = _normalise_run_id(match.group(1).replace("*", "")) if match else ""
        if not value or value.startswith("<"):
            return f"no filled `{field}:` line"
        run_ids[field] = value
    if run_ids["Author-run"] == run_ids["Reviewer-run"]:
        return "`Reviewer-run:` equals `Author-run:` — the author cannot grade its own work"
    if spec:
        upstream = re.search(_RUN_LINE.format(field="Upstream"), text, re.MULTILINE)
        if not upstream or spec not in _SPEC_NAME_PATTERN.findall(upstream.group(1)):
            return f"its `Upstream:` does not name {spec}, the spec under test — it reviews other work"
    return None


def _spec_under_test(prompt: str) -> str | None:
    """The SPEC on a `Slice:` or `Spec:` line, else the first SPEC the prompt names."""
    for value in _SUBJECT_LINE_PATTERN.findall(prompt):
        found = _SPEC_NAME_PATTERN.search(value)
        if found:
            return found.group(1)
    found = _SPEC_NAME_PATTERN.search(prompt)
    return found.group(1) if found else None


def _check_review(subagent_type: str, prompt: str) -> None:
    """E-AC2: block a QA spawn whose `Review:` line does not name an
    independent PASS review of the work under test. Exits."""
    prefix = f"BLOCKED (.claude/hooks/guard_agent_spawn.py, R19): `{subagent_type}` needs an independent review"
    bugfix = _OVERRIDE_TOKEN in prompt
    wanted = f"{_BUGFIX_REVIEW_PREFIX}<id>.md" if bugfix else "REVIEW-<slug>.md"
    line = _REVIEW_LINE_PATTERN.search(prompt)
    named = _REVIEW_REFERENCE_PATTERN.search(line.group(1)) if line else None
    if not named:
        _block(
            f"{prefix} — add \"Review: {_REVIEW_DIR}/{wanted}\" (a PASS review by a different run) to the "
            f"QA prompt; the `reviewer` agent writes it from {_REVIEW_TEMPLATE}."
        )
    name = named.group(1)
    spec = None
    if bugfix:
        if not name.startswith(_BUGFIX_REVIEW_PREFIX):
            _block(f"{prefix} — `{_OVERRIDE_TOKEN}` work must name {_REVIEW_DIR}/{wanted} on its `Review:` line, not {name}.")
    else:
        spec = _spec_under_test(prompt)
        if not spec:
            _block(
                f"{prefix} — name the spec under test on a `Spec: doc/specs/SPEC-<slug>.md` line, so "
                f"{_REVIEW_DIR}/{name} can be checked against it."
            )
    problem = _review_problem(_repo_root() / _REVIEW_DIR / name, spec)
    if not problem:
        sys.exit(0)
    _block(
        f"{prefix} — {_REVIEW_DIR}/{name}: {problem}. Spawn the `reviewer` agent to write it "
        f"from {_REVIEW_TEMPLATE} with `Verdict: PASS` and a `Reviewer-run:` different from "
        f"`Author-run:`, then name it on the prompt's `Review:` line."
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if payload.get("tool_name") != "Agent":
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    subagent_type = str(tool_input.get("subagent_type") or "")
    prompt = str(tool_input.get("prompt") or "")
    if _normalise_type(subagent_type) == _COORDINATOR:
        _block(
            "BLOCKED (.claude/hooks/guard_agent_spawn.py, JC-AC3): Jarvis is the main thread, not a role agent "
            "— do the coordination yourself, or spawn the role agent the work needs."
        )
    if subagent_type in _ROLE_AGENTS:
        missing = _missing_brief_lines(prompt)
        if missing:
            _block(
                f"BLOCKED (.claude/hooks/guard_agent_spawn.py, JC-AC6): the brief to `{subagent_type}` has "
                f"missing or unfilled: {', '.join(missing)}. Add each on a line of its own:\n"
                f"  Tier: <0|1|2> — <reason>\n"
                f"  Files: <paths>"
            )
    # Before the override and the engineer check: neither may open this gate.
    if subagent_type in _REVIEW_GATED_SUBAGENT_TYPES:
        _check_review(subagent_type, prompt)
    if subagent_type not in _GATED_SUBAGENT_TYPES:
        sys.exit(0)

    # Override path first, so a legitimate small bugfix is never blocked by a
    # spec-resolution detail.
    if _OVERRIDE_TOKEN in prompt:
        reason = prompt.split(_OVERRIDE_TOKEN, maxsplit=1)[1].strip().splitlines()
        first_line = reason[0].strip() if reason else ""
        if len(first_line) >= _MIN_OVERRIDE_REASON_CHARS:
            sys.exit(0)
        _block(
            f"BLOCKED (.claude/hooks/guard_agent_spawn.py, rule A5): "
            f"`{_OVERRIDE_TOKEN}` is present but carries no reproduction.\n"
            f"AGENTS.md §5 allows a small bugfix to start at {subagent_type} "
            f"without a spec, but the basis has to be stated. Write "
            f"`{_OVERRIDE_TOKEN} <one-line reproduction>` "
            f"(at least {_MIN_OVERRIDE_REASON_CHARS} characters)."
        )

    references = _SPEC_REFERENCE_PATTERN.findall(prompt)
    if not references:
        _block(
            f"BLOCKED (.claude/hooks/guard_agent_spawn.py, rule A5): spawning "
            f"`{subagent_type}` with no upstream spec named in the prompt.\n"
            f"AGENTS.md §6 rule 2: an implementer must not start without an "
            f"`Approved` upstream document.\n"
            f"Do one of these:\n"
            f"  1. name the spec in the prompt (e.g. `doc/specs/SPEC-NN-....md`);\n"
            f"  2. if this is a small bugfix that legitimately has no spec "
            f"(AGENTS.md §6), add `{_OVERRIDE_TOKEN} <one-line reproduction>` so "
            f"the basis is on the record.\n"
            f"Only `ai-engineer` and `frontend-engineer` are gated on a spec — "
            f"`ba-sa`, `pm`, `Explore`, `reviewer` and the rest are never blocked."
        )

    root = _repo_root()
    problems: list[str] = []
    approved: list[str] = []
    for name in dict.fromkeys(references):  # de-duplicate, keep order
        stem = Path(name).name
        prefix = stem.split("-", 1)[0]
        spec_path = root / _UPSTREAM_DIRS[prefix] / stem
        if not spec_path.is_file():
            problems.append(f"{name}: file not found at {spec_path.relative_to(root)}")
            continue
        status = _read_status(spec_path)
        if status is None:
            problems.append(f"{name}: no `Status:` line")
        elif status != _ALLOWED_STATUS:
            problems.append(f"{name}: Status is {status!r}, not {_ALLOWED_STATUS!r}")
        else:
            approved.append(name)

    if approved:
        # At least one named spec is Approved. Extra references (a superseded
        # spec, a design doc quoted for context) must not block the spawn.
        sys.exit(0)

    _block(
        f"BLOCKED (.claude/hooks/guard_agent_spawn.py, rule A5): none of the "
        f"specs named in this `{subagent_type}` prompt is `{_ALLOWED_STATUS}`.\n"
        + "\n".join(f"  - {problem}" for problem in problems)
        + f"\nAGENTS.md §6 rule 2: only the human's approval flips an artifact to "
        f"`{_ALLOWED_STATUS}`, and an agent must refuse to start before that.\n"
        f"If the human has authorised implementation ahead of the status flip, "
        f"say so in the prompt and use `{_OVERRIDE_TOKEN} <reason>` — do NOT edit "
        f"the spec's Status line yourself. Writing your own approval is exactly "
        f"what the human-only-approval rule exists to prevent.\n"
        f"LIMIT (stated limit): this gate reads a repo file an agent can edit. "
        f"It is only as strong as the approval registry and the CI check."
    )


if __name__ == "__main__":
    main()
