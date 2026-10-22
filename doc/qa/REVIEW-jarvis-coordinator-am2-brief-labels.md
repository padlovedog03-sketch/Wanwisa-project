# Review: Amendment 2 — wider label grammar after an empty `Files:` (C1), rule 6 reads list-form `Files:` (C3)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-jarvis-coordinator-am2-brief-labels.md
Author-run: a9180f2fd39ac0027
Reviewer-run: a30dd5fd58f524c0b
Date: 2026-10-22

## Verdict: PASS

All five criteria in scope (JC-AM3, JC-AM3-RED, JC-AM4, JC-AM4-RED, JC-AM5) pass. Every check was re-run in this review on a scratch copy of HEAD `8482670` with the author's 4 files laid on top.

## Read from

- Upstream: doc/specs/SPEC-jarvis-coordinator-am2-brief-labels.md (Approved, `spec-jarvis-coordinator-am2-brief-labels-2026-10-22`)
- Change: uncommitted edits to 4 files in the author's worktree `agent-a9180f2fd39ac0027`: `.claude/hooks/guard_agent_spawn.py`, `scripts/coordinator_lint.py`, `tests/hooks/test_guard_agent_spawn.py`, `tests/coordinator/test_coordinator_lint.py`. They were copied onto `git archive HEAD` (`8482670`) as scratch tree `new`, next to an untouched `base`. `diff -ru base new` touches exactly these 4 files (302 diff lines).
- Not read: the author's conversation. Claims in the handback were re-run, not relayed.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| JC-AM3 | Guard label grammar widened, exact regex | PASS | `probe.py` §1: the guard's `_LABEL_PATTERN.pattern` is identical to the spec string `^(?:\*\*)?[A-Za-z][A-Za-z0-9_ -]*(?:\*\*)?[ \t]*:` → `True`. The diff is a one-line change at guard line 85, and the refusal message is unchanged. `pytest tests/hooks/test_guard_agent_spawn.py tests/coordinator/test_coordinator_lint.py -q -p no:cacheprovider` on `new` gave **323 passed** (on `base`: 253 passed, so +70 new tests and none removed). Every hostile item in the spec is a refused case: NO_SPEC_BUGFIX, `Verify-with`, `Verify_with`, bold NO_SPEC_BUGFIX, `Step2`, the full-width colon, a label before a path, and the bulleted header with Files forgotten. Both known false refusals (`Makefile:`, `docker-compose:`) are in the refused list, and the `ai-engineer` and `pm` rows have their own test. All five new accepted cases (`./Makefile:`, `` `Makefile`: ``, `Makefile —`, `my-file.txt:`, a path before a label) are in the accepted list. The existing am1 and JC-AC6 ids are unchanged: the diff only appends to both parametrize lists. |
| JC-AM3-RED | New guard cases red on the old guard | PASS | `mutants.py base-code` (the old label in the guard and the old rule-6 `Files:` path in the lint, with the new tests) gave **26 failed, 297 passed**. The failures include `test_an_unfilled_files_line_is_refused_naming_files_only[am3-hyphen-label]`, `test_a_label_only_files_list_is_refused_for_engineer_and_pm[ai-engineer-no-spec-bugfix-label]` and `[pm-hyphen-label]`. `[am3-makefile-false-refusal]` stays green on the old code, which matches the spec ("refused today too"). |
| JC-AM4 | Rule 6 reads list and bold `Files:` | PASS | `probe.py` §1: the lint's `_LABEL_RE`, `_LIST_ITEM_RE` and `_FILES_FIELD_RE` match the guard's patterns → `True` ×3. The lint imports no hook code (stdlib `unicodedata` only), so AM2-ADR-2 holds. All 7 clean cases and all 7 hostile cases from the spec are parametrized, and the hostile test asserts that the violation list is exactly the one `Files:` reason. The hostile set includes "list after the next `Slice:`". Mutant `lint-ignores-block` (the lint reads `lines[start:]` instead of the block) turns that case red: **1 failed** `[list-in-next-slice]`. `Criteria:` and `Verify with:` still go through `_brief_field_value`. |
| JC-AM4-RED | New clean cases red on the old lint | PASS | `mutants.py base-code`: all 6 non-placeholder clean cases fail on the old rule 6. Examples: `test_a_files_field_the_guard_accepts_is_clean_in_rule_6[list]`, `[blank-then-list]`, `[bold-inline]`, `[bold-then-list]`, `[bulleted-indented-list]` and `[full-width-colon]`. `[inline-placeholder]` stays green on the old code too, as the spec intends. |
| JC-AM5 | Parity test fails on a one-copy revert | PASS | The table has 39 cases: 18 filled, 19 unfilled, and 2 declared disagreements (both inline `<paths>`, AM2-ADR-3). It covers every JC-AM3 case and every JC-AM4 case that does not depend on blocks. `mutants.py guard-label-reverted` gave **20 failed**, 9 of them parity cases such as `test_the_guard_and_rule_6_read_files_the_same_way[Files:\n- Verify-with: x]`. `mutants.py lint-label-reverted` gave **11 failed**, the same 9 parity cases plus 2 lint hostile cases. The parity test also catches lint drift: `lint-no-nfkc` gave 3 failed, `lint-no-blank-skip` 2 failed and `lint-accepts-placeholder-item` 2 failed. The test loads `scripts/coordinator_lint.py` from the hook test, never the other way round. |
| — | Must-stay-green set | PASS | On `new`, `pytest tests/coordinator tests/hooks/test_guard_agent_spawn.py tests/hooks/test_regression_guard_agent_spawn_review.py tests/hooks/test_regression_autonomy_rework_bypasses.py tests/framework/test_doc_contracts_jarvis.py tests/hooks/test_verify_scripts.py -q -p no:cacheprovider` gave **503 passed**. |
| — | Exit gate | PASS (with the gate's own limit) | `new/scripts/verify-full.sh` exited 0: hooks 1432 passed, ci-examples 32 passed, coordinator 174 passed, framework OK, scar-forge OK. The gate printed `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. That comes from the template, not from this change. |

## Defects (if FAIL)

None.

## Lint behaviour change: `Files: **` (checked against the spec)

`probe.py` §4, rule 6 on a `Slice:` block. `Files: **`, `Files: *` and `Files:**` were clean on `base` and are one `Files:` violation on `new`. `Files: a.py` and `Files: <exact paths>` are clean on both. This matches the spec: JC-AM4 (a) needs a *non-empty* inline value, and the spec's sketch strips `*` (`m.group(1).replace("*", "").strip()`). It also matches the guard, which refuses the same three inputs on both `base` and `new` (probe §3). So the change removes a lint/guard disagreement and does not add one. Observation (not a defect): no test pins this case. The parity table does not hold `Files: **` either.

## Real briefs from coordinator-discipline §8 (filled in)

`probe.py` §2. `_missing_brief_lines` returned `[]` on both `base` and `new` for the filled engineer T0, engineer T1, reviewer, qa T0 and qa T1 templates. It also returned `[]` for this review's own brief, whose `Files:` item carries a `(write in … the main tree)` note, and for the reviewer template's `# or REVIEW-bugfix-…` comment. Run end to end through the `new` hook, these briefs gave:

- the engineer and reviewer briefs: exit 0;
- the two QA briefs: exit 2, only at R19 ("needs an independent review — … not found"). Their `Files:` passed. This is the expected gate, because no REVIEW file exists in the scratch tree.

## Hostile inputs tried

All results are from `probe.py` §3, comparing the guard's and the lint's `_files_filled` on `new`; True means filled. **The guard and the lint agreed on every input.**

- Each of these stops the list: `- verify-with: x` (lower case), `-  Verify-with: x` (double space), `  - Verify-with: x` (indented), `1. NO_SPEC_BUGFIX: x`, `* Step-2: x`, `- Verify-with\t: x`, `- Verify-with : x`, `- **Verify-with** : x`, `- Verify with -: x`. All are False on `new` and were True on `base`, so the fix closes them too.
- `- _private: x` and `- 2fa: x` stay paths (True), because a label must start with a letter.
- Look-alike characters: the Cyrillic `е` in `Vеrify-with:` and a non-breaking hyphen `Verify‑with:` (U+2011, which NFKC does not fold to `-`) are read as paths (True). So is `- ตรวจด้วย: pytest`. All three are declared under AM2-ADR-4 (ASCII only) and fall outside the threat model.
- `- C:\x\a.py`, `- http://x/a.md` and `- README: top` are refused (False) on both `base` and `new`. These are existing false refusals under AM2-ADR-1 and are not caused by this change.
- Failing open on a crash: the new lint function has no I/O and no indexing that can go past the end (`item.group(1) or ""`). The guard's handling of crashes and exit codes is unchanged.

## Parked (outside JC-AM3…JC-AM5, or outside the threat model)

- Look-alike and non-ASCII labels read as paths: declared limit AM2-ADR-4.
- A drive letter (`C:`) or URL scheme item is refused as a label: an existing false refusal, covered by AM2-ADR-1's fail-closed stance.
- No regression test pins the `Files: **` change to rule 6 (see above). It is low value, and it is in line with the spec.

## Approval history

- **2026-10-22 — drafted.** By reviewer run `a30dd5fd58f524c0b`, from the approved spec and the author's 4 changed files, re-run on a scratch copy of HEAD `8482670`. The scripts used live in this run's scratchpad: `setup.py`, `mutants.py` and `probe.py`.
