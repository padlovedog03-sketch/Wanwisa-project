# QA Report: Amendment 2 — wider label grammar after an empty `Files:` (C1), rule 6 reads list-form `Files:` (C3)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-jarvis-coordinator-am2-brief-labels.md
Date: 2026-10-22

## Verdict: PASS

All five criteria (JC-AM3, JC-AM3-RED, JC-AM4, JC-AM4-RED, JC-AM5) pass on a scratch copy of branch HEAD `955d883` with the author's 4 changed files laid on top, and the exit gate passes on that copy.

## Setup

- `git archive HEAD` (`955d883`, which differs from the author's base `8482670` only by the review document) unpacked twice: `base` (untouched) and `new` (plus `.claude/hooks/guard_agent_spawn.py`, `scripts/coordinator_lint.py`, `tests/hooks/test_guard_agent_spawn.py`, `tests/coordinator/test_coordinator_lint.py` copied from worktree `agent-a9180f2fd39ac0027`). `diff -rq base new` lists exactly those 4 files.
- `scripts/verify-handoff.sh --status` → `not opted in`, so the verdict command is `scripts/verify-full.sh`.
- Invocation: Tier 1, review `doc/qa/REVIEW-jarvis-coordinator-am2-brief-labels.md`, spec Approved (`spec-jarvis-coordinator-am2-brief-labels-2026-10-22`), review PASS by a different run (`a30dd5fd58f524c0b` vs author `a9180f2fd39ac0027`).
- Isolation: a first run of the suite and the gate was discarded. Another agent sharing this session's scratchpad overwrote the scratch tree with unrelated inc2-scorecard files mid-run (hooks 1388, coordinator 160, no am2 code). Everything above and below was rerun in a uniquely named scratch tree. The 4 changed files were compared byte for byte with the worktree (`cmp`) before and after the suite and gate run: no drift.
- Own probe: a scratch script that sends each brief end to end to the guard (JSON payload on stdin, as the hook runtime does) on `base` and on `new`, and compares the guard's and the linter's `_files_filled` on `new`. Hostile strings are copied from the spec's JC-AM3 cell, not retyped from the brief.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| JC-AM3 | Guard: a label (new grammar) ends the list after an empty `Files:` | PASS | Probe, 17 spec rows: every hostile row (NO_SPEC_BUGFIX to `reviewer` and `ai-engineer`, `Verify-with` to `reviewer` and `pm`, `Verify_with`, bold NO_SPEC_BUGFIX, `Step2`, full-width colon, label before a path, bulleted header with Files forgotten) gave **base=0 new=2**, and stderr names `Files:`. Known false refusals: `Makefile:` base=2 new=2, `docker-compose:` base=0 new=2 (both as the spec states). All 5 new accepted rows (`./Makefile:`, `` `Makefile`: ``, `Makefile —`, `my-file.txt:`, path before label) gave new=0. `guard mismatches: 0`. Existing am1/JC-AC6 cases: `pytest tests/hooks/test_guard_agent_spawn.py tests/coordinator/test_coordinator_lint.py` → **323 passed** on `new` (253 on `base`). |
| JC-AM3-RED | New guard cases red on the old guard | PASS | `m_oldcode` (base guard + base lint, new tests): **56 failed, 267 passed**. Includes `[am3-hyphen-label]`, `test_a_label_only_files_list_is_refused_for_engineer_and_pm[ai-engineer-no-spec-bugfix-label]` and `[pm-hyphen-label]`. (Of the 56, 39 are parity cases that fail because the old lint has no `_files_filled` — expected, not a red-first signal by themselves.) |
| JC-AM4 | Rule 6 counts list-form and bold `Files:` as filled | PASS | All 7 clean cases and 7 hostile cases from the spec are parametrized (`test_a_files_field_the_guard_accepts_is_clean_in_rule_6[list, blank-then-list, bold-inline, bold-then-list, bulleted-indented-list, full-width-colon, inline-placeholder]`, `test_a_files_field_with_no_filled_list_is_one_rule_6_violation[placeholder-item, no-spec-bugfix-label, hyphen-label, next-field-not-an-item, bulleted-empty-files, paragraph-before-list, list-in-next-slice]`), all green on `new`. `test_the_brief_template_carries_every_field_rule_6_requires` green. Probe, `check_briefs` end to end: `Files:` + `- Verify-with: x` → one violation, reason exactly `brief has no 'Files:' line — name the exact files to touch or read`; `Files:` + `- a.py`, the same with CRLF line endings, and `**Files**:` + `  1. a.py` → no rule-6 violation. |
| JC-AM4-RED | New clean cases red on the old lint | PASS | `m_oldcode`: `test_a_files_field_the_guard_accepts_is_clean_in_rule_6[list]`, `[blank-then-list]`, `[bold-inline]`, `[bold-then-list]`, `[bulleted-indented-list]`, `[full-width-colon]` FAILED; `[inline-placeholder]` stays green (correct per AM2-ADR-3). |
| JC-AM5 | Parity test fails when one copy drifts | PASS | Reverting only the guard's label to `[A-Za-z][A-Za-z ]*` (`m_guardrev`): **20 failed**, 9 of them `test_the_guard_and_rule_6_read_files_the_same_way[...]`. Reverting only the lint's label (`m_lintrev`): **11 failed**, the same 9 parity cases plus 2 lint hostile cases. Own probe on `new`: 31 spec + own cases, `parity diffs: 0`; `Files: <paths>` is the declared disagreement (guard False, lint True). |
| — | Must stay green | PASS | Full suite and exit gate below; includes `test_regression_guard_agent_spawn_review.py`, `test_regression_autonomy_rework_bypasses.py`, `test_doc_contracts_jarvis.py`, `test_verify_scripts.py`. |

## Test Run

```
# scratch copy `new` = 955d883 + the 4 changed files
$ python3 -m pytest tests -q -p no:cacheprovider
2029 passed, 1 skipped in 505.42s (0:08:25)          exit 0

$ scripts/verify-full.sh > verify-full.log 2>&1      exit 0
  OK   hooks             (345s) 1432 passed in 337.49s (0:05:37)
  OK   ci-examples       (9s) 32 passed in 8.69s
  OK   scar-forge        (2s)
  OK   coordinator       (8s) 174 passed in 7.82s
  OK   framework         (80s) memory: 0 problem(s)
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.

$ pytest tests/hooks/test_guard_agent_spawn.py tests/coordinator/test_coordinator_lint.py
new: 323 passed · base: 253 passed · m_oldcode: 56 failed, 267 passed
m_guardrev: 20 failed, 303 passed · m_lintrev: 11 failed, 312 passed
```

## Defects (if FAIL)

None.

## Edge Cases Probed

All end to end through the hook on `base` and `new`; "OK" means the `new` result matches the spec's intent.

- CRLF brief `Files:\r\n- Verify-with: x` → base 0, new 2 naming `Files:`. OK.
- Tab after the dash, `-\tVerify-with: x` → base 0, new 2. OK.
- Bold label with a digit, `- **Step2:** x` → base 0, new 2. OK.
- Bare `-` item then a label → base 0, new 2 (an empty item fills nothing). OK.
- Full-width hyphen `Verify－with:` (NFKC folds to `-`) → base 0, new 2. OK.
- Numbered `1. Verify_with: x` → base 0, new 2. OK.
- `ai-engineer` with `**Files:**` then only the NO_SPEC_BUGFIX label; and with a blank line, a label item, then a free-standing NO_SPEC_BUGFIX line → both base 0, new 2. The A5 override does not open the `Files:` check. OK.
- Paths that must stay paths: `- a.py:42`, `- src/x_y-z.py: edit`, `-` then `- a.py`, `- 2fa: x` (starts with a digit) → new 0. OK.
- A label-only list followed later by `Files: a.py` → new 0 (the second line fills it), and lint agrees. OK.
- `- v2-notes: x` → new 2. A newly refused honest brief of the same class as `docker-compose:` (AM2-ADR-1, fail closed). Declared, not a defect.
- Zero-width space inside a label (`Veri`U+200B`fy-with: x`) → read as a path by both guard and lint. Look-alike/non-ASCII labels are outside the threat model (AM2-ADR-4).
- `Files: **` → guard False, lint False (lint was clean on base; now agrees with the guard). Not pinned by a test (the review noted this too).
- Long input: an item of `a` + 20000 spaces + `x` takes about 0.7 s in the guard on both `base` (0.65 s) and `new` (0.72 s); the overlap is the existing space in both `[A-Za-z ]*` and `[ \t]*`, not the new characters. Not introduced by this change.

## Parked (outside JC-AM3…JC-AM5, or outside the threat model)

- LIMIT: look-alike and non-ASCII labels (zero-width space, Cyrillic letters, Thai) are read as paths — declared by AM2-ADR-4.
- LIMIT: new honest false refusals of hyphen/digit names without a dot (`docker-compose:`, `v2-notes:`) — declared by AM2-ADR-1; `./name:` or a backticked name is the workaround.
- Pre-existing: the label regex is quadratic in a run of spaces (about 0.7 s at 20000 spaces, same on base). Not caused by this change; outside the brief-mistake threat model.
- Observation: no test pins `Files: **` (lint now refuses it, like the guard).

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-22 — drafted.** qa, from the approved spec, the PASS review at `955d883`, and runs on a scratch copy of `955d883` plus the author's 4 files.
