# SPEC: Amendment 1 — `Files:` may be a list (JC-AC6), and one stale refusal sentence

Status: In Review
Owner: ba-sa
Upstream: doc/specs/SPEC-jarvis-coordinator.md (Approved, registry key `spec-jarvis-coordinator-2026-10-20`) · doc/qa/REVIEW-jarvis-coordinator.md (reviewer PASS, "Spec-level finding" and the first Parked item; the file is untracked in the main tree at the time of writing) · owner ruling 2026-10-21: "ตามคำแนะนำ เน้นใช้งานง่าย"
Date: 2026-10-21

## Overview

The approved spec stays as it is. This file changes two things in increment 1, both in the spawn guard (`.claude/hooks/guard_agent_spawn.py`, the hook that checks a role-agent brief before the agent starts):

- **JC-AM1 amends JC-AC6.** A `Files:` line with an empty value is accepted when the paths are written as a list directly under it. Today that honest brief is refused, and the coordinator writes briefs this way, so its own briefs get refused after merge. That works against the owner's definition "easy to use" (doc/memory/stay-on-the-definition.md, doc/memory/ease-of-use-over-strictness.md).
- **JC-AM2** fixes one sentence in the spec-gate refusal, which still says `ba-sa` and `pm` are "never blocked".

**What this amendment overrides.** In JC-AC6, the hostile case "`Files:` empty" now means "`Files:` empty with no filled list under it" (JC-AM1). Every other accepted, refused and never-checked case in JC-AC6 is unchanged, and so is JC-AC7. Nothing else in the approved spec changes.

**Size:** Small (2 files, ≤ 15 min engineer).

**Markers:**
- `[MEASURED: <command>]`: I ran it on 2026-10-21.
- `[MEASURED: proto]`: I ran it against a scratch prototype of the JC-AM1 rule (`scratchpad/am1/proto.py`, 26 cases, all as the tables below say). This measures the rule as written here, not the hook. The hook's behaviour is `[INFERRED]` until the engineer's tests run.
- `[INFERRED]`: I read it, but did not run it.

## Current behaviour (the defect)

The worktree guard at `91d6ef2` (`.claude/worktrees/agent-a2b6d5b03efba43ea`) returns these results for a `pm` brief that starts `Tier: 2 — x`. I measured each one with `printf … | python3 .claude/hooks/guard_agent_spawn.py`:

| Rest of the prompt | Exit | Message |
|---|---|---|
| `Files:` then `- a.md`, `- b.md` | 2 | `missing or unfilled: Files:` |
| `Files:` (last line) | 2 | same |
| `Files:` then `Some paragraph.` | 2 | same |
| `Files:` then `- <paths>` | 2 | same |
| `Files:` then `- ` | 2 | same |
| `Files: a.md` | 0 | — |

The cause: `_missing_brief_lines` reads only the text after `Files:` on that same line (`_FILES_LINE_PATTERN.findall`), so a list underneath is never seen `[INFERRED: read lines 152–164; consistent with the table above]`.

## Acceptance Criteria

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| JC-AM1 | R4, R6; owner ruling 2026-10-21 | **Given** a role-agent brief (the JC-AC6 types), **When** the guard reads `Files:`, **Then** the brief has a filled `Files:` if **either**: <ul><li>(a) some `Files:` line, in any form JC-AC6 already accepts, has an inline value that is non-empty and does not start with `<`. This is unchanged.</li><li>(b) some `Files:` line has an **empty** inline value, and the lines after it form a filled list.</li></ul>**The list, for (b):**<ul><li>Lines that are empty or whitespace only are skipped between `Files:` and the first item.</li><li>The list starts at the first non-blank line, which must be a list item: optional indentation, then `-`, `*` or `1.` (any digits), then whitespace or end of line.</li><li>The list runs over consecutive item lines and stops at the first line that is not an item, and at the first blank line after the first item.</li><li>The list is filled if at least one item's text is non-empty and does not start with `<`. The text is read with `*` and whitespace stripped, as in JC-AC6.</li><li>An item whose text starts with a label also ends the list and does not count. A label is letters and spaces, optionally bold, then a colon, e.g. `Verify with:` or `**Criteria:**`.</li></ul>Text is read after NFKC, and CRLF line ends are handled, as in JC-AC6. The refusal message is unchanged: `missing or unfilled: Files:`, showing `Files: <paths>`.<br><br>**Accepted (exit 0):**<ul><li>`Files:` + `- a.md` + `- b.md`</li><li>`Files:` + `* a.md`</li><li>`Files:` + `1. a.md`</li><li>`**Files:**` + `- a.md`</li><li>`- Files:` + `  - a.md` (indented items)</li><li>`Files:` + blank line + `- a.md`</li><li>CRLF `Files:\r\n- a.md\r\n`</li><li>`Files:` + `- <paths>` + `- a.md` (one filled item is enough)</li><li>`Files:` + `- doc/a.md — new: x` (a `.` or `/` before the colon means it is not a label)</li></ul>**Hostile, each exit 2 naming `Files:`:**<ul><li>`Files:` as the last line, with or without a trailing newline</li><li>`Files:` followed by a normal paragraph: `Some paragraph.` + `- a.md` (the list must start on the first non-blank line)</li><li>`Files:` followed only by `- <paths>`</li><li>`Files:` followed by an empty `- ` item, or by a bare `-`</li><li>`Files:` followed by blank lines only</li><li>`Files:` followed by an indented path with no list marker (`  a.md`), which the reviewer's repro used</li><li>`Files:` followed by a bold heading `**Task**` (not an item: no whitespace after the `*`)</li><li>`Files: <paths>` + `- a.md` (an inline placeholder is not empty, so (b) does not apply)</li><li>**Bulleted header with Files forgotten:** `- Tier: 2 — x` / `- Files:` / `- Verify with: pytest`. This is refused today and must stay refused; the label rule is what keeps it so.</li></ul>**Unchanged:** every JC-AC6 case, including `Tier: 1 — x` + `Files:` (files-empty) and `## Tier: 2` used as a heading, which is still refused. `[MEASURED: proto]` for the rule, `[INFERRED]` for the hook. | tests/hooks/test_guard_agent_spawn.py (existing). Add the cases to the parametrized `test_a_filled_brief_header_in_any_field_form_is_accepted` and `test_an_unfilled_files_line_is_refused_naming_files_only`. |
| JC-AM1-RED | JC-AM1 **RED-FIRST** | **Given** the new accepted cases, **When** they run against the `91d6ef2` guard, **Then** each is red (exit 2), measured for the first accepted case above `[MEASURED: current-behaviour table]`. **And Given** the label rule is removed, **Then** the bulleted-header-forgotten case is red (exit 0 instead of 2) `[MEASURED: proto, which returned True for it before the label rule was added]`. The engineer pastes both red lines, restores, and shows green. | tests/hooks/test_guard_agent_spawn.py |
| JC-AM2 | R6 (wording) | **Given** the spec-gate refusal in `main()` (line 307 at `91d6ef2`) that ends "`ba-sa`, `pm`, `Explore`, `reviewer` and the rest are never blocked.", **When** an engineer spawn is refused by rule A5, **Then** the sentence says they are never blocked **by this spec gate**, because role agents are now checked for `Tier:` and `Files:` (JC-AC6). Only that sentence changes. The docstring at line 278 ("a legitimate small bugfix is never blocked by…") is a different sentence and is left alone. No test asserts the old wording `[MEASURED: grep -rn "never blocked" tests/ in the worktree; only test_guard_bash_matrix.py:11 and test_guard_bash_polling.py:130 match, and both are about other hooks]`. | none new; existing rule-A5 tests must stay green |

## Functional Behavior

Pseudocode for `_missing_brief_lines`. Only the `Files:` half changes; `Tier:` keeps the same-line rule.

```python
_LIST_ITEM = r"^[ \t]*(?:[-*]|\d+\.)(?:[ \t]+(.*))?$"
_LABEL     = r"^(?:\*\*)?[A-Za-z][A-Za-z ]*(?:\*\*)?[ \t]*:"

def _filled(value) -> bool:            # same rule JC-AC6 already applies
    v = value.replace("*", "").strip()
    return bool(v) and not v.startswith("<")

def _files_filled(text) -> bool:       # text is already NFKC-normalised
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _FILES_LINE_PATTERN.match(line)        # same pattern, applied per line
        if not m: continue
        if _filled(m.group(1)): return True        # (a) unchanged
        if m.group(1).replace("*", "").strip(): continue   # inline "<…>": not empty, (b) does not apply
        j = next non-blank line index after i
        while lines[j] is a _LIST_ITEM and its text is not a _LABEL:
            if _filled(item text): return True     # (b)
            j += 1
    return False
```

The engineer may shape this differently. The tables are the contract, not the code.

**Threat model (scope-discipline rule 5).** This check defends against a brief written by mistake: forgotten paths, an unfilled placeholder, or a bulleted header with the value missing. It does not defend against a brief built to pass, e.g. `Files:` + `- anything`. That is already the stated limit JC-L3: only presence is checked, never truth. No case in this amendment chases forgery.

## Decisions (ADR-style)

- **AM1-ADR-1: blank lines are allowed before the first item, not inside the list.**
  - **Context:** The brief left this open. In Markdown, `Files:`, then a blank line, then a list renders the same as without the blank line, and people write both.
  - **Decision:** Skip blank lines before the first item. After the first item, a blank line ends the list.
  - **Consequences:** Both honest shapes pass. The "paragraph first" case stays refused, because the first non-blank line must be an item.
- **AM1-ADR-2: an item that starts with a label is not a path, and ends the list.**
  - **Context:** JC-AC6 accepts `- Files: a.py`, so bulleted headers are a supported form. Without this rule, `- Files:` with the value forgotten, followed by `- Verify with: pytest`, turns from refused into accepted. That would be a new false accept of a mistake.
  - **Decision:** Letters and spaces, optionally bold, then a colon, is a label.
  - **Consequences:** A path item written as `- Makefile: add target` is refused falsely, because it has no `.` or `/` before the colon `[MEASURED: proto]`. This fails closed: the message shows the accepted form, and the retry costs one line.
- **AM1-ADR-3: AGENTS.md is not changed.**
  - **Context:** §0 ข and §5 require the `Files:` line, but never say the paths sit on the same line `[INFERRED: read AGENTS.md lines 32 and 99 in the worktree]`.
  - **Decision and consequences:** No wording is needed for the list form. Editing §0 would also touch text whose anchors JC-AC8 checks, for no gain.
- **AM1-ADR-4: `Tier:` keeps the same-line rule.**
  - **Context and decision:** A tier is one value, so there is no honest list form for it.
  - **Consequences:** `Tier:` + `- 2` stays refused.

## Affected tests / affected files

**How this list was built:**
- `grep -rln "guard_agent_spawn" tests` in the worktree `[MEASURED]`. It returned:
  - `tests/hooks/test_guard_agent_spawn.py`;
  - `tests/hooks/test_regression_guard_agent_spawn_review.py`;
  - `tests/coordinator/test_coordinator_lint.py`, whose line 189 compares rule 5 with the guard's NO_SPEC_BUGFIX logic, which is unchanged here.
- The two spawn-guard helpers append an inline `\nTier: 1 — test\nFiles: x` (`test_guard_agent_spawn.py:53`, `test_regression_guard_agent_spawn_review.py:53`) `[MEASURED: grep -n Files]`. Branch (a) is unchanged, so they are unaffected `[INFERRED]`.
- `grep -rn "never blocked" tests/` for JC-AM2 `[MEASURED]`: there are no assertions on the guard's wording.
- `test_regression_autonomy_rework_bypasses.py` (one of the JC-AC7 three) has no `Files` match `[MEASURED: grep -n]`, so it is unaffected.

| File (in worktree `.claude/worktrees/agent-a2b6d5b03efba43ea`) | Change | Whose behaviour changes |
|---|---|---|
| `.claude/hooks/guard_agent_spawn.py` | `_missing_brief_lines` gains branch (b) (JC-AM1); one sentence of the rule-A5 refusal (JC-AM2) | Coordinator: list-form briefs are accepted |
| `tests/hooks/test_guard_agent_spawn.py` | new cases in the two existing parametrized tests (JC-AM1, JC-AM1-RED) | — |

**Existing tests that must keep passing:**
- `python3 -m pytest tests/hooks/test_guard_agent_spawn.py tests/hooks/test_regression_guard_agent_spawn_review.py tests/hooks/test_regression_autonomy_rework_bypasses.py -q -p no:cacheprovider`: 161 passed at `91d6ef2`, per the review `[RELAYED: REVIEW-jarvis-coordinator.md]`. The count rises by the new cases.
- `tests/coordinator/test_coordinator_lint.py`: unchanged.

**Not touched:**
- the approved parent spec;
- AGENTS.md (AM1-ADR-3);
- `scripts/coordinator_lint.py` rule 6, which still refuses list-form `Files:` in `Slice:` briefs. See Parked in the handback.
- ADAPTERS.md: JC-L3 already covers "presence, never truth".

## Traceability

R4 (brief carries `Files:`) and the owner's ease-of-use ruling → JC-AM1, JC-AM1-RED · R6 (guard wording accurate) → JC-AM2.

That is 2 requirements and 1 ruling, mapping to 3 criteria.

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it. -->

- **2026-10-21 — drafted.** ba-sa, from the reviewer's spec-level finding and parked item in REVIEW-jarvis-coordinator.md, after the owner ruled "ตามคำแนะนำ เน้นใช้งานง่าย".
