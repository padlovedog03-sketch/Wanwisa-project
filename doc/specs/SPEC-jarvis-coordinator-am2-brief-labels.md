# SPEC: Amendment 2 — a wider label grammar after an empty `Files:` (C1), and rule 6 reads list-form `Files:` (C3)

Status: Approved
Approval: spec-jarvis-coordinator-am2-brief-labels-2026-10-22
Owner: ba-sa
Upstream: doc/specs/SPEC-jarvis-coordinator-am1-files-list.md (Approved, registry key `spec-jarvis-coordinator-am1-files-list-2026-10-21`; this file amends its AM1-ADR-2) · doc/requirements/PRD-jarvis-coordinator.md (Approved, R4, R6) · doc/qa/QA-jarvis-coordinator.md (the finding behind C1) · doc/tasks/backlog.md Active row 7 and improvement checklist C1, C3 · owner rulings 2026-10-22: doc/memory/jarvis-decides-self-improvement.md, doc/memory/easy-and-end-to-end.md
Date: 2026-10-22

## Overview

Two small changes. Both make the two `Files:` checkers give the same answer.

- **JC-AM3 (C1) amends AM1-ADR-2.** The spawn guard (`.claude/hooks/guard_agent_spawn.py`, the hook that checks a brief before a role agent starts) stops a list after an empty `Files:` when it meets a *label*. Today a label may contain letters and spaces only. So `- NO_SPEC_BUGFIX: …`, `- Verify-with: x` and `- Verify_with: x` are read as paths, and a brief with no file list passes. The label grammar widens to `[A-Za-z][A-Za-z0-9_ -]*`.
- **JC-AM4 (C3).** `scripts/coordinator_lint.py` rule 6 (the linter's check that a `Slice:` brief names its files) reads only the text on the `Files:` line itself. After am1, the guard accepts a list under an empty `Files:`, but the linter reports the same brief as missing `Files:`, which is a false red. Rule 6 learns the am1 list form and the bold field form, using the same rule as the guard.

**What this amendment overrides.** Only AM1-ADR-2's label definition ("letters and spaces"). Every other JC-AM1 case, JC-AC6 and JC-AC7 stay as approved. Rule 6's `Criteria:` and `Verify with:` checks are unchanged.

**Size:** Small. Four files, about 20 minutes of engineer time.

**Markers:**
- `[MEASURED: <cmd>]`: I ran the command on 2026-10-22 at HEAD `96bebdb`.
- `[MEASURED: proto]`: I ran it against a scratch copy of HEAD (`git archive HEAD`) with the two proposed changes applied. This measures the rule as written here. It does not measure the engineer's code.
- `[INFERRED]`: I read it but did not run it.

## Current behaviour (the defects)

### C1: the guard at HEAD `96bebdb`

Each prompt below starts `Tier: 0 — x` and then `Files:` with nothing after it. The command was `python3 <scratch>/probe_guard.py`, which pipes the JSON payload to `python3 .claude/hooks/guard_agent_spawn.py` once per case `[MEASURED]`.

| Type | Next line | Exit | Note |
|---|---|---|---|
| reviewer | `- NO_SPEC_BUGFIX: repro steps here` | **0** | defect |
| reviewer | `- Verify-with: x` | **0** | defect |
| reviewer | `- Verify_with: x` | **0** | defect |
| reviewer | `- **NO_SPEC_BUGFIX:** x` | **0** | defect |
| reviewer | `- Step2: x` | **0** | defect (a label with a digit) |
| reviewer (bulleted header) | `- Files:` then `- Verify-with: pytest` | **0** | defect: am1's "bulleted header, Files forgotten" case with a hyphen |
| pm | `- Verify-with: x` | **0** | defect |
| ai-engineer | `- NO_SPEC_BUGFIX: repro steps here` | **0** | defect. **Correction to the backlog**, which says "ai-engineer is already blocked by rule A5". The override line carries ≥ 10 characters, so A5 lets it through, and `Files:` is read as filled. |
| reviewer | `- Verify with: x` | 2 | correct: already a label |
| reviewer | `- Makefile: build rules` | **2** | **already refused today**, see AM2-ADR-1 |
| reviewer | `- Dockerfile: base image` | 2 | already refused today |
| reviewer | `- Makefile`, `- Makefile — build rules`, `- scripts/x.py: add y`, `` - `Makefile`: build rules `` | 0 | correct |
| qa | `- Verify-with: x` | 2 | refused, but by the QA review gate (R19), not by `Files:` |

Cause: `_LABEL_PATTERN = ^(?:\*\*)?[A-Za-z][A-Za-z ]*(?:\*\*)?[ \t]*:` (line 85) has no digit, `_` or `-` `[MEASURED: grep -n "_LABEL_PATTERN = " .claude/hooks/guard_agent_spawn.py]`.

### C3: `coordinator_lint.py` rule 6 at HEAD `96bebdb`

Each block is `Slice: s`, then the `Files:` form below, then `Criteria: AC1` and `Verify with: pytest`. The command was `python3 <scratch>/probe_lint.py`, which calls `coordinator_lint.lint()` and keeps the rule-6 violations `[MEASURED]`.

| `Files:` form | Rule-6 result | Guard result | Agree? |
|---|---|---|---|
| `Files: a.py` | clean | accept | yes |
| `Files:` + `- a.py` + `- b.py` | **"brief has no 'Files:' line"** | accept | **no: false red** |
| `Files:` + blank + `- a.py` | **violation** | accept | **no: false red** |
| `**Files:** a.py` | **violation** | accept | **no: false red** |
| `**Files:**` + `- a.py` | **violation** | accept | **no: false red** |
| `Files:` + `- <paths>` | violation | refuse | yes |
| `Files:` (empty) | violation | refuse | yes |
| `Files: <paths>` | clean | refuse | **no**: kept on purpose, AM2-ADR-3 |

Cause: `check_briefs` asks `_brief_field_value(line, "Files:")` for a non-empty value on the same line, and that pattern has no bold form `[INFERRED: read scripts/coordinator_lint.py lines 270–312; consistent with the table]`.

## Acceptance Criteria

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| JC-AM3 | R4, R6; AM1-ADR-2 | **Given** a role-agent brief with an empty `Files:` line followed by list items, **When** the guard reads the list, **Then** an item whose text starts with a **label** ends the list and does not count as a path. **New label grammar:** optional `**`, then one ASCII letter, then any of ASCII letters, digits, `_`, space or `-`, then optional `**`, optional spaces or tabs, then `:`. As a regex: `^(?:\*\*)?[A-Za-z][A-Za-z0-9_ -]*(?:\*\*)?[ \t]*:`. Text is read after NFKC, as today, so a full-width colon is a colon. The refusal message is unchanged.<br><br>**Hostile, each exit 2 naming `Files:` (sent to `reviewer`, plus the `ai-engineer` and `pm` rows):**<ul><li>`Files:` + `- NO_SPEC_BUGFIX: repro steps here` (also to `ai-engineer`, with `Tier: 0 — x`)</li><li>`Files:` + `- Verify-with: x` (also to `pm`)</li><li>`Files:` + `- Verify_with: x`</li><li>`Files:` + `- **NO_SPEC_BUGFIX:** x`</li><li>`Files:` + `- Step2: x`</li><li>`Files:` + `- Verify-with：x` (full-width colon)</li><li>`Files:` + `- Verify-with: x` + `- a.md` (the label ends the list before the path)</li><li>Bulleted header with Files forgotten: `- Tier: 2 — x` / `- Files:` / `- Verify-with: pytest`</li></ul>**Known false refusal, by design (exit 2). These are honest briefs.** See AM2-ADR-1.<ul><li>`Files:` + `- Makefile: build rules`, refused today too</li><li>`Files:` + `- docker-compose: x`, newly refused</li></ul>**Accepted (exit 0). Every am1 accepted case, plus:**<ul><li>`Files:` + `- ./Makefile: build rules`</li><li>`Files:` + `` - `Makefile`: build rules ``</li><li>`Files:` + `- Makefile — build rules`</li><li>`Files:` + `- my-file.txt: x` (a `.` before the colon)</li><li>`Files:` + `- a.md` + `- NO_SPEC_BUGFIX: repro` (the path comes first)</li></ul>**Unchanged:** every JC-AM1 and JC-AC6 case in `test_guard_agent_spawn.py`. `[MEASURED: proto — 16 accepted and 11 refused cases, 0 mismatches against these lists, scratch proto.py; the three guard test files: 345 passed at HEAD and 345 passed in the patched copy]` | tests/hooks/test_guard_agent_spawn.py: add to the parametrized `test_an_unfilled_files_line_is_refused_naming_files_only` and `test_a_filled_brief_header_in_any_field_form_is_accepted`; add one small test for the `ai-engineer` and `pm` rows |
| JC-AM3-RED | JC-AM3 **RED-FIRST** | **Given** the HEAD `96bebdb` guard, **When** the new hostile cases run, **Then** each is red: exit 0 where 2 is expected `[MEASURED: current-behaviour table, first eight rows]`. The engineer pastes the red line for at least `- Verify-with: x` and the `ai-engineer` `NO_SPEC_BUGFIX` row, then applies the change and shows green. | tests/hooks/test_guard_agent_spawn.py |
| JC-AM4 | R4, R6 (lint and guard agree) | **Given** a `Slice:` brief block, **When** rule 6 judges `Files:`, **Then** `Files:` counts as filled if **either**:<ul><li>(a) a `Files:` field line, plain, bulleted, numbered, indented **or bold** (`**Files:**`, `**Files**:`), has a non-empty inline value. A value starting `<` still counts, as today (AM2-ADR-3).</li><li>(b) the field line's inline value is empty, and a filled list follows, under exactly the JC-AM1 list rule with the JC-AM3 label grammar.</li></ul>Only lines inside the block count, as today. The text is NFKC-normalised for this check. The violation text is unchanged: `brief has no 'Files:' line — name the exact files to touch or read`.<br><br>**Clean (no rule-6 `Files:` violation):** `Files:` + `- a.py` + `- b.py` · `Files:` + blank line + `- a.py` · `**Files:** a.py` · `**Files:**` + `- a.py` · `- Files:` + `  - a.py` · `Files：a.py` · `Files: <exact paths>` (the template).<br>**Hostile, each one rule-6 `Files:` violation:** `Files:` + `- <paths>` · `Files:` + `- NO_SPEC_BUGFIX: repro` · `Files:` + `- Verify-with: x` · `Files:` + `Criteria: AC1` (the next field is not an item, so nothing is borrowed) · the bulleted brief with `- Files:` empty and `- Criteria: …` next, as `test_an_empty_indented_field_does_not_borrow_the_next_line` asserts today · `Files:` + `Some paragraph.` + `- a.py` · a list that starts only after the next `Slice:` line (that list belongs to the next block). Each of these must name only `Files:`.<br>**Unchanged:** every existing rule-6 test, including `test_the_brief_template_carries_every_field_rule_6_requires` `[MEASURED: proto — every clean and hostile case above, plus the next-`Slice:` case, gave the stated result in the patched copy; tests/coordinator/ plus the guard tests: 345 passed, 0 failed]`. | tests/coordinator/test_coordinator_lint.py: new parametrized cases next to the existing rule-6 tests |
| JC-AM4-RED | JC-AM4 **RED-FIRST** | **Given** the HEAD `96bebdb` linter, **When** the new clean cases run, **Then** the list forms and the bold forms give one rule-6 `Files:` violation each (red) `[MEASURED: C3 table rows 2–5]`. The engineer pastes one red line, then shows green. | tests/coordinator/test_coordinator_lint.py |
| JC-AM5 | R6 (one rule, two copies) | **Given** one shared case table, **When** each case goes through the guard's `_files_filled` (after NFKC) and through the linter's new `Files:` function, **Then** both return the same answer for every case. The only exceptions are cases with an inline `<…>` value, which are listed in the table as expected disagreements (AM2-ADR-3). The table holds at least the JC-AM3 and JC-AM4 cases above. A drift in either copy makes this test red: the engineer shows it red by reverting the label change in one copy only. `[MEASURED: proto parity.py — 32 cases, 30 SAME, 2 DIFF, both inline-placeholder cases]` | tests/hooks/test_guard_agent_spawn.py (loads `scripts/coordinator_lint.py`; the adapter test depends on the core script, never the reverse) |

## Functional Behavior

**Guard (JC-AM3):** a one-line change to `_LABEL_PATTERN`:

```python
_LABEL_PATTERN = re.compile(r"^(?:\*\*)?[A-Za-z][A-Za-z0-9_ -]*(?:\*\*)?[ \t]*:")
```

**Linter (JC-AM4):** a pseudocode sketch. The engineer may shape it differently; the tables are the contract.

```python
_FILES_FIELD = r"^[ \t]*(?:(?:[-*]|\d+\.)[ \t]+)?(?:\*\*)?Files(?:\*\*)?[ \t]*:(?:\*\*)?(.*)$"   # the guard's _FIELD_LINE for Files
_LIST_ITEM   = r"^[ \t]*(?:[-*]|\d+\.)(?:[ \t]+(.*))?$"                                          # same as the guard
_LABEL       = r"^(?:\*\*)?[A-Za-z][A-Za-z0-9_ -]*(?:\*\*)?[ \t]*:"                              # same as JC-AM3

def files_filled(lines) -> bool:            # lines of one Slice: block
    lines = [NFKC(l) for l in lines]
    for i, line in enumerate(lines):
        m = match(_FILES_FIELD, line)
        if not m: continue
        if m.group(1).replace("*", "").strip(): return True          # (a): any inline value, "<…>" included
        j = first non-blank line after i
        while lines[j] is a _LIST_ITEM and its text is not a _LABEL:
            if item text, with "*" stripped, is non-empty and not "<…>": return True   # (b)
            j += 1
    return False

# check_briefs: for "Files:" use files_filled(block); "Criteria:" and "Verify with:" are unchanged
```

The linter gets its own copy of the patterns and does not import the hook. The reason is in AM2-ADR-2.

**Threat model (scope-discipline rule 5).** Both checks defend against a brief written by mistake: a forgotten file list, or a list with only a label line. They do not defend against a brief built to pass, such as `Files:` + `- anything`. That is JC-L3: presence is checked, never truth.

## Decisions (ADR-style)

- **AM2-ADR-1: keep fail-closed for path items that look like a label.**
  - **Context:** The brief asked how to handle `- Makefile: build rules` once the label grammar widens. Measured: it is **already** refused at HEAD (exit 2), together with `- Dockerfile: base image`, because am1's letters-only label already matches them. Widening adds false refusals only for extensionless file names that contain a digit, `_` or `-` before a colon, such as `- docker-compose: x` `[MEASURED: proto]`. (`- Step2: x` also stops the list, but it is a label, not a path, so refusing it is correct.)
  - **Options weighed:**
    - (a) keep fail-closed;
    - (b) a fixed allow-list of label words;
    - (c) guess paths by shape, for example "a word that names an existing file".
  - **Decision:** (a), because it is the simplest of the three. (b) misses labels nobody listed, and the coordinator invents labels. (c) reads the disk from a hook and still guesses.
  - **Consequences:**
    - A false refusal costs one retry. The forms that pass are measured: `./Makefile: …`, `` `Makefile`: … ``, `Makefile — …`.
    - The refusal message is not changed. It already shows `Files: <paths>`, the inline form, which always works.
- **AM2-ADR-2: two copies and a parity test, not a shared import.**
  - **Context:** The rule now lives in the hook (adapter layer, `.claude/`) and in the linter (core, `scripts/`). Today nothing is shared `[MEASURED: grep -n "^import\|^from" in both files: stdlib only]`.
  - **Decision:**
    - The linter keeps its own three patterns.
    - JC-AM5 runs one case table through both and fails on any drift.
    - The test lives with the hook tests, because the adapter may depend on the core and the core must not depend on an adapter (AGENTS.md §10).
  - **Consequences:** About 20 duplicated lines. A future change must touch both copies, and the parity test says so the moment one is missed.
- **AM2-ADR-3: rule 6 keeps accepting an inline `<…>` value.**
  - **Context:** The guard refuses `Files: <paths>`, and rule 6 accepts it. Aligning that too would turn `test_the_brief_template_carries_every_field_rule_6_requires` red. That test lints the coordinator-discipline brief template, whose `Files:` value is `<exact paths to touch · to read>` `[MEASURED: sed -n 138,146p .agents/skills/coordinator-discipline/SKILL.md]`. A template is placeholders by design.
  - **Decision:** Fix the two false reds (list form and bold). Keep the placeholder divergence and declare it in JC-AM5's table.
  - **Consequences:**
    - A brief with `Files: <paths>` is clean in the linter but refused at spawn. That is a false green in the linter only, and the guard catches it before any agent runs.
    - The template and its test stay untouched.
- **AM2-ADR-4: ASCII labels only.**
  - **Context:** I tried a Unicode-aware label (`[^\W\d_][\w -]*`). It still missed Thai labels, because Thai vowel and tone marks are not `\w` in Python: `ตรวจด้วย:` did not match `[MEASURED: python3 -c probe]`.
  - **Decision:** Keep ASCII.
  - **Consequences:** Declared limit: an item such as `- ตรวจด้วย: pytest` under an empty `Files:` still counts as a path. Brief labels are English by the brief template (`Verify with:`, `Criteria:`), so this is outside the mistake the check targets.

## Affected tests / affected files

**How this list was built** (all `[MEASURED]` at `96bebdb`):
- `grep -rln "guard_agent_spawn" tests` returned 3 files:
  - `tests/coordinator/test_coordinator_lint.py`;
  - `tests/hooks/test_guard_agent_spawn.py`;
  - `tests/hooks/test_regression_guard_agent_spawn_review.py`.
- `grep -rln "coordinator_lint" tests` returned 3 files:
  - `test_coordinator_lint.py`;
  - `tests/framework/test_doc_contracts_jarvis.py`, which only asserts the `--approve-ready` text (line 48);
  - `tests/hooks/test_verify_scripts.py`, which only lists the paths, at lines 455–456.
- `grep -n -- "- [A-Za-z][A-Za-z0-9_ -]*[0-9_-][A-Za-z0-9_ -]*:"` over the three guard and lint test files found no existing case that the wider label would flip.
- The patched scratch copy ran `tests/coordinator` plus the three guard test files: 345 passed, the same count as HEAD.

**One owner per file.** Every file below belongs to this amendment only. SPEC-jarvis-coordinator-inc2-scorecard touches none of them, so there is no merge order to set.

| File | Change | Whose behaviour changes |
|---|---|---|
| `.claude/hooks/guard_agent_spawn.py` | `_LABEL_PATTERN` widened (JC-AM3) | Coordinator: a brief with only a label under `Files:` is refused |
| `scripts/coordinator_lint.py` | rule 6 reads `Files:` through the new function (JC-AM4) | Coordinator: list-form and bold `Files:` no longer read red |
| `tests/hooks/test_guard_agent_spawn.py` | new cases (JC-AM3, JC-AM3-RED); parity test (JC-AM5) | — |
| `tests/coordinator/test_coordinator_lint.py` | new rule-6 cases (JC-AM4, JC-AM4-RED) | — |

**Must stay green, unchanged:**
- `tests/hooks/test_regression_guard_agent_spawn_review.py`;
- `tests/hooks/test_regression_autonomy_rework_bypasses.py`;
- `tests/framework/test_doc_contracts_jarvis.py`;
- `tests/hooks/test_verify_scripts.py`.

**Not touched:**
- the approved am1 and parent specs;
- AGENTS.md;
- `.agents/skills/coordinator-discipline/SKILL.md`: its rule-6 sentence (line 152) says "no filled `Files:`", which stays true;
- `doc/framework/COORDINATOR-CONSTITUTION.md` line 90, for the same reason `[INFERRED: read both lines]`;
- `doc/framework/ADAPTERS.md`: JC-L3 already covers presence-only.

## Traceability

R4 (brief carries `Files:`) → JC-AM3, JC-AM3-RED, JC-AM4, JC-AM4-RED · R6 (machine check, and lint and guard agree) → JC-AM3, JC-AM4, JC-AM5 · AM1-ADR-2 (amended) → JC-AM3.

That is 2 requirements and 1 amended decision, mapping to 5 criteria.

## Approval history

- **2026-10-22 — approved (human).** Registry key `spec-jarvis-coordinator-am2-brief-labels-2026-10-22`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it. -->

- **2026-10-22 — drafted.** ba-sa, from backlog Active row 7 (improvement checklist C1 + C3), the QA finding in doc/qa/QA-jarvis-coordinator.md, and probes at `96bebdb`.
