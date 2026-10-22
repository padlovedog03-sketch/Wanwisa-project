# Review: delegated-autonomy increment E part 1 (E-AC2), round 2 after the QA re-test 2 fallback defect

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy.md
Author-run: ed5c7e8, a4f98650319afa539
Reviewer-run: aadde799c467dd7f2
Date: 2026-10-22

## Verdict: PASS

The QA re-test 2 defect is closed: a non-bugfix QA spawn must now name the spec under test on a `Spec:`/`Slice:` line, the prose fallback is gone, QA's reproduction is refused, and the new tests are red against the pre-fix hook.

## Read from

- Upstream: doc/specs/SPEC-delegated-autonomy.md, row E-AC2 (line 198). Defect: QA re-test 2 in commit c041dbb.
- Change: the uncommitted diff in worktree `.claude/worktrees/agent-a4f98650319afa539` over HEAD c041dbb, 5 files: `.claude/hooks/guard_agent_spawn.py` (`_spec_under_test` returns None instead of the first SPEC in prose; docstring), `tests/hooks/test_guard_agent_spawn.py`, `tests/hooks/test_regression_guard_agent_spawn_review.py`, `.claude/agents/reviewer.md` line 22, AGENTS.md §5 tier 1 row.
- Not read: the author's conversation. The brief's claims were re-run, not relayed.
- Red-first and mutation runs used a scratch copy of the worktree's tracked files, never the worktree itself.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| E-AC2 | `guard_agent_spawn.py` refuses `qa`/`frontend-qa` when the review is missing or not PASS, or `Reviewer-run` equals `Author-run`; bugfix work uses `REVIEW-bugfix-<id>.md`; each case planted and shown red. Round 2 scope: the review must be of the spec under test, and that spec is never guessed from prose | PASS | `python3 -m pytest tests/hooks -q -p no:cacheprovider` in the worktree → `1308 passed in 190.44s`. With the hook reset to `HEAD:.claude/hooks/guard_agent_spawn.py` and the new tests: `4 failed, 177 passed` (below). Hostile probes below, all fail closed. |

### Brief checks, one by one

- **QA's repro refused.** Prompt "QA the change. It builds on SPEC-zqb.md; the work under test is SPEC-zqa.md." with `Review: doc/qa/REVIEW-zqb.md` (a PASS review of SPEC-zqb) → exit 2, one line: "name the spec under test on a `Spec: doc/specs/SPEC-&lt;slug&gt;.md` line, so doc/qa/REVIEW-zqb.md can be checked against it."
- **No `Spec:` line refused with one actionable line.** "Verify doc/specs/SPEC-zqa.md." with a matching PASS REVIEW-zqa → exit 2, one stderr line, same message, for both `qa` and `frontend-qa`.
- **Correct `Spec:` plus matching PASS review opens.** "Builds on SPEC-zqb.md." + `Spec: doc/specs/SPEC-zqa.md` + `Review: doc/qa/REVIEW-zqa.md` → exit 0. The same `Spec:` line with `Review:` naming REVIEW-zqb → exit 2 ("its `Upstream:` does not name SPEC-zqa.md").
- **`NO_SPEC_BUGFIX:` path unchanged.** The diff does not touch the `if bugfix:` branch of `_check_review`. Probes: bugfix token + PASS REVIEW-bugfix-zq1 → 0; + a non-bugfix review → 2; + a missing bugfix review → 2.
- **The one flipped case is purely the fallback pin.** `test_a_slice_line_without_a_spec_path_falls_back_to_the_first_named_spec` (expected allow) became `test_a_slice_line_without_a_spec_path_does_not_fall_back_to_a_spec_named_in_prose` (expected block, asserts the `Spec:` message). Its prompt is unchanged: a `Slice:` line with no SPEC path and the spec named only on a `Criteria:` line. The only thing it pinned was the removed fallback.
- **Every other changed existing test keeps its own reason.** The edits only move the spec from prose onto a `Spec:` line (and move context prose to its own line). With the fixed hook, the 7 blocking cases among them block through the review-file path (stderr ends "then name it on the prompt's `Review:` line"), not through the missing-spec message; run with a temporary copy of the test file that prints each stderr. A mutation where `_spec_under_test` always returns None turns 22 of the touched tests red, among them every allow case and `test_a_review_line_pointing_at_another_specs_review_blocks` (asserts `Upstream` in stderr).
- **New tests red against the old hook.** Scratch copy, hook from HEAD, new tests: `FAILED ...test_a_slice_line_without_a_spec_path_does_not_fall_back_to_a_spec_named_in_prose`, `FAILED ...test_regression_qa_repro_a_dependency_named_first_does_not_open_qa_for_the_work_under_test`, `FAILED ...test_regression_a_qa_brief_with_no_spec_line_is_refused_and_told_to_add_one[qa]` and `[frontend-qa]` → `4 failed, 177 passed`. The fourth new test, `test_regression_a_correct_brief_with_a_spec_line_and_matching_pass_review_opens`, passes on the old hook too. That is expected: it pins the allow path.
- **Docs.** reviewer.md line 22 and AGENTS.md §5 tier 1 now say the QA prompt carries a `Spec:` line. `grep -rnE "first SPEC|else the first"` over `*.md`/`*.py` outside doc/qa finds no stale wording of the fallback.

## Defects (if FAIL)

None.

## Hostile inputs tried

Against the fixed hook in the scratch copy, with planted `doc/qa/` files and a filled Tier and Files line. Exit 2 is block, 0 is allow.

- `- Spec:` bulleted → 0. `**Spec:**` bold → 0. `Slice:` line carrying the SPEC path → 0. An empty `Spec:` line followed by a filled one → 0. CRLF line endings → 0.
- Lower-case `spec:` → 2. `Specs:` → 2. `The Spec: ...` mid-line → 2. Full-width colon → 2. `Spec: SPEC-zqa` with no `.md` → 2. Each gives the one-line `Spec:` message, so all fail closed with a fix the coordinator can act on.
- No `Review:` line with a `Spec:` line → 2 ("add Review: ..."). `reviewer` type → 0 (not gated).

## Exit gate

`scripts/verify-full.sh` in the worktree (`verify-handoff.sh --status` → `not opted in`) → EXIT=0: `hooks 1308 passed`, `ci-examples 30 passed`, `scar-forge OK`, `coordinator 155 passed`, `framework OK (memory: 0 problems)`, then `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests` (the project-side steps of this template, not configured here).

## Parked

- **Some blocking tests do not pin their reason.** `test_an_explicitly_named_review_must_exist_exactly`, `test_only_the_review_line_counts_not_reviews_mentioned_elsewhere`, `test_an_upstream_near_miss_of_the_spec_under_test_blocks[*]` and `test_only_the_first_review_line_counts` stay green when `_spec_under_test` always returns None, because they assert only exit 2 or a file name that the missing-spec message also carries. Today they block for their own reason (checked above). This predates the change; the old fallback hid it. A one-line assert on "not found" or `Verdict` would close it.
- **Lower-case `spec:` is refused.** Fail closed with an actionable message. It is in line with the `Review:` line, which is also case-sensitive.
- Round 1 parked items (below) still stand.

## Review history

### Round 2 (this file, above)

Reviewed the uncommitted rework of the prose-fallback defect from QA re-test 2 (c041dbb). Result above.

### Round 1 (Reviewer-run ad79f6fe8c702907e, HEAD ef1f717, Author-run ed5c7e8)

Round 1 result: PASS

E-AC1 to E-AC4 hold at HEAD ef1f717. The E-AC2 defect from doc/qa/QA-delegated-autonomy-E1.md (a dependency's review opening QA for another spec) is closed by ed5c7e8, and its regression test is red before the fix and green after it.

### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy.md, rows E-AC1 to E-AC4 (lines 197-200) and impact row 19 (line 271).
- Change: ed5c7e8 (fix), merged in a60d8f2; reviewed as checked out at ef1f717 on `feat/top3-tiers-mechanisms-deny`. Prior QA: doc/qa/QA-delegated-autonomy-E1.md.
- Not read: the author's conversation. The commit message's claims were re-run, not relayed.
- Main tree at review time had unrelated uncommitted edits (doc/qa/QA-bugfix-gate3-worktree.md, doc/qa/REVIEW-bugfix-gate3-worktree.md) and an untracked doc/qa/REVIEW-verify-tiers-G-polling.md. None was touched. Red-first runs used clean `git archive` copies in the scratchpad.

### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| E-AC1 | `learning_loop.py --window 28` groups rework causes and feedback memories into recurring causes (2 or more), each with a stub marked `owner approval required (AH5)`, exit 0; `unavailable: rework causes not shipped` without H | PASS | `python3 -m pytest tests/framework/test_learning_loop.py -q -p no:cacheprovider` → `17 passed`. `python3 scripts/learning_loop.py --window 28` → EXIT=0, prints `missed-ac: 19`, `spec-defect: 10`, `test-gap: 2`, `lesson-without-mechanism: 4`, each followed by a stub ending `owner approval required (AH5)`. |
| E-AC2 | `guard_agent_spawn.py` refuses `qa`/`frontend-qa` when the review is missing or not PASS, or `Reviewer-run` equals `Author-run`; bugfix work uses `REVIEW-bugfix-<id>.md`; each case planted and shown red | PASS | At HEAD: `pytest tests/hooks/test_guard_agent_spawn.py` → `162 passed`; `pytest tests/hooks/test_regression_guard_agent_spawn_review.py` → `14 passed`. Red-first (see below): the fix's own tests against the pre-fix hook → `20 failed, 85 passed`; the QA regression test against the pre-fix hook → `1 failed, 13 passed`; the original four cases against the pre-E hook 5e7c96f → red. Hostile probes below, all as expected. |
| E-AC3 | `.claude/agents/reviewer.md` exists, mission says it starts from the files, never the author's conversation; `doc/templates/review-report.md` exists; AGENTS.md §5 shows `engineer → reviewer → qa` in every tier | PASS | `pytest tests/framework/test_doc_contracts.py -rs` → `62 passed, 1 skipped`; the skip is `test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now`, not an E-AC3 contract. `ls` shows both files; reviewer.md line 10 carries the mission sentence; `grep -n reviewer AGENTS.md` shows tiers 0, 1 and 2 (lines 93-95) each with engineer, then reviewer, then qa. |
| E-AC4 | `coordinator_lint.py` rule 7: a `Slice:` brief carries `Impact:` and `Selected:`, or `unavailable (<reason>)` until B and H ship | PASS | `pytest tests/coordinator/test_coordinator_lint.py` → `86 passed`. Planted briefs (Slice, Under, Criteria, Verify with): no Impact/Selected → two rule 7 violations; `unavailable (reason)` on both → no rule 7 line; bare `unavailable` → `'Impact:' says unavailable with no reason`; filled paths → clean. Opt-in on `Under:` matches spec impact row 19 (line 271: "Rule active only when the brief has `Under:`"). |

#### E-AC2 red-first, run in this review

- **The fix's own tests.** In a `git archive ed5c7e8` copy, `tests/hooks/test_guard_agent_spawn.py` gives `105 passed`. With the hook replaced by `ed5c7e8^`, it gives `20 failed, 85 passed`. The reds are the new rule's tests, among them `test_a_review_line_pointing_at_another_specs_review_blocks`, `test_a_spec_or_slice_line_names_the_spec_under_test_over_the_first_mention[Spec:]`, `test_a_review_line_with_no_spec_named_blocks_and_asks_for_the_spec`, `test_an_upstream_near_miss_of_the_spec_under_test_blocks[doc/specs/XSPEC-zz99-a.md]` and `test_a_bugfix_prompt_with_no_review_line_asks_for_a_bugfix_review`.
- **QA's defect reproduction.** With HEAD's tests and the `ed5c7e8^` hook: `FAILED tests/hooks/test_regression_guard_agent_spawn_review.py::test_regression_a_dependency_review_quoted_for_context_does_not_open_qa_for_another_spec` and `1 failed, 13 passed`. At HEAD it passes.
- **The four spec cases.** With the ed5c7e8 tests and the pre-E hook (5e7c96f), these are red, among others: `test_a_missing_review_blocks_the_qa_spawn[qa]` and `[frontend-qa]`; `test_a_review_without_a_pass_verdict_blocks[## Verdict: FAIL]`; `test_a_review_by_the_author_run_blocks[equal]`, `[case]`, `[zero-width]`, `[full-width]`; `test_bugfix_work_does_not_accept_a_non_bugfix_review`; `test_bugfix_work_with_a_failing_bugfix_review_blocks`; `test_the_bugfix_override_does_not_bypass_the_review_gate`.
- A count over HEAD's whole test file against `ed5c7e8^` (56 failed) is not cited: about 35 of those reds are later JC-AC3/JC-AC6 brief tests (9278b21, 0601a0b), not E-AC2.

### Defects (if FAIL)

None.

### Hostile inputs tried

All against the HEAD hook in a scratch copy with planted `doc/qa/` files, each prompt carrying a filled Tier and Files line. Exit 2 is block, 0 is allow.

- The QA repro: spec under test SPEC-za, `Review:` naming a PASS review whose Upstream is SPEC-zb → 2.
- The prose form of the repro: "Verify SPEC-za. Builds on SPEC-zb, reviewed in REVIEW-zb.", `Review:` naming REVIEW-zb → 2.
- The previously blocked legitimate case: "QA SPEC-za (builds on SPEC-zb)" with `Review:` naming a PASS REVIEW-za → 0.
- A `Review:` line naming an increment file (REVIEW-za-E1) whose Upstream is SPEC-za → 0.
- A `Review:` line with no spec named anywhere → 2, with a message asking for a `Spec:` line.
- No `Review:` line → 2. A review named only in prose ("See REVIEW-za.md") → 2. A lowercase `review:` line → 2. A full-width colon after `Review` → 2.
- A `Review:` line naming two files, the wrong one first → 2 (first only).
- A review file that is missing → 2. One that is a directory → 2.
- A verdict of FAIL → 2. A lowercase `pass` → 2. A PASS line followed by a FAIL line → 2.
- Equal run IDs differing only in case and a leading space → 2.
- A CRLF review file → 0.
- The bugfix token with a non-bugfix review → 2. The bugfix token with a missing bugfix review → 2. The bugfix token with a PASS bugfix review → 0.
- A spec QA prompt that also contains the bugfix token → 2: it is treated as bugfix work and asks for a bugfix review. That is fail-closed.
- `frontend-qa` gated the same as `qa`. `reviewer` → 0.

### Exit gate

`scripts/verify-full.sh` (run in the main tree; `verify-handoff.sh --status` says `not opted in`) → `EXIT GATE RED (exit 1)`:

```
  OK   hooks             (268s) 1303 passed in 267.60s (0:04:27)
  FAIL ci-examples       (7s) (exit 1)
FAILED tests/ci/test_ci_examples.py::test_gate_3_is_green_after_bootstrap_runs
FAILED tests/ci/test_ci_examples.py::test_gate_3_ignores_an_agent_worktree_under_dot_claude
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[.claude/agents/x.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[doc/x.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[doc/worktrees-notes.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[doc/.claude/worktrees/x.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[.claude/worktreesX/x.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_scans_real_paths_next_to_a_worktree[.claude/worktrees.md]
FAILED tests/ci/test_ci_examples.py::test_gate_3_still_reports_a_real_file_whose_content_mentions_a_worktree
9 failed, 21 passed in 6.19s
  OK   coordinator       (7s) 155 passed in 4.24s
  OK   framework         (54s) memory: 0 problem(s) in /Users/pongsakorn.ni/Desktop/jarvis-framework/doc/memory
EXIT GATE RED (exit 1).
```

The red is not from the change under review:
- `tests/ci/test_ci_examples.py` on clean archives gives `19 passed` at a60d8f2 and `30 passed` at 632c808. It gives `1 failed, 21 passed` at 7661338, and the same 9 failures as above at HEAD.
- 7661338 commits doc/qa/QA-bugfix-gate3-worktree.md and doc/qa/REVIEW-bugfix-gate3-worktree.md. Both quote an upper-case angle-bracket placeholder literal, and gate 3's `grep '<[A-Z_]{3,}>'` over `doc` reports it.
- ed5c7e8 touches only the hook, its test file and reviewer.md.

This is Parked, not a FAIL. It still turns every exit gate on this branch red until those two reports are fixed.

### Parked

- **Exit gate red from 7661338 (above).** Owner: whoever owns the gate-3 bugfix reports. The main tree already holds uncommitted edits to both files that escape the literal.
- **Proposed LIMIT line.** A malformed payload crashes the hook with exit 1, which does not block. Two cases: a JSON list (`'list' object has no attribute 'get'`) and a string `tool_input`. The module docstring says malformed input exits 0, so the behaviour differs from the text, but both outcomes allow the spawn. This is a harness-supplied payload, so it is outside the mistakes-only threat model. The code predates ed5c7e8.
- **A stale bugfix review opens QA.** With `NO_SPEC_BUGFIX:`, any PASS `REVIEW-bugfix-*.md` named on the `Review:` line opens the gate, because there is no spec or id to match it against. The spec does not bind the id, so this is not an E-AC2 failure.
- **The named review is not tied to the slug.** The file on the `Review:` line need not be named after the spec. A PASS review under any name whose Upstream names the spec under test opens the gate. The spec says `REVIEW-<slug>.md`. The Upstream check covers the mistake case this review was asked to look for.
- **Carried from QA, re-seen here.** An upper-case `QA` subagent type is not gated.
