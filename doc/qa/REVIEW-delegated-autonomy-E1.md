# Review: delegated-autonomy increment E part 1 (E-AC1 to E-AC4), close-out after the E-AC2 fix

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy.md
Author-run: ed5c7e8
Reviewer-run: ad79f6fe8c702907e
Date: 2026-10-22

## Verdict: PASS

E-AC1 to E-AC4 hold at HEAD ef1f717. The E-AC2 defect from doc/qa/QA-delegated-autonomy-E1.md (a dependency's review opening QA for another spec) is closed by ed5c7e8, and its regression test is red before the fix and green after it.

## Read from

- Upstream: doc/specs/SPEC-delegated-autonomy.md, rows E-AC1 to E-AC4 (lines 197-200) and impact row 19 (line 271).
- Change: ed5c7e8 (fix), merged in a60d8f2; reviewed as checked out at ef1f717 on `feat/top3-tiers-mechanisms-deny`. Prior QA: doc/qa/QA-delegated-autonomy-E1.md.
- Not read: the author's conversation. The commit message's claims were re-run, not relayed.
- Main tree at review time had unrelated uncommitted edits (doc/qa/QA-bugfix-gate3-worktree.md, doc/qa/REVIEW-bugfix-gate3-worktree.md) and an untracked doc/qa/REVIEW-verify-tiers-G-polling.md. None was touched. Red-first runs used clean `git archive` copies in the scratchpad.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| E-AC1 | `learning_loop.py --window 28` groups rework causes and feedback memories into recurring causes (2 or more), each with a stub marked `owner approval required (AH5)`, exit 0; `unavailable: rework causes not shipped` without H | PASS | `python3 -m pytest tests/framework/test_learning_loop.py -q -p no:cacheprovider` → `17 passed`. `python3 scripts/learning_loop.py --window 28` → EXIT=0, prints `missed-ac: 19`, `spec-defect: 10`, `test-gap: 2`, `lesson-without-mechanism: 4`, each followed by a stub ending `owner approval required (AH5)`. |
| E-AC2 | `guard_agent_spawn.py` refuses `qa`/`frontend-qa` when the review is missing or not PASS, or `Reviewer-run` equals `Author-run`; bugfix work uses `REVIEW-bugfix-<id>.md`; each case planted and shown red | PASS | At HEAD: `pytest tests/hooks/test_guard_agent_spawn.py` → `162 passed`; `pytest tests/hooks/test_regression_guard_agent_spawn_review.py` → `14 passed`. Red-first (see below): the fix's own tests against the pre-fix hook → `20 failed, 85 passed`; the QA regression test against the pre-fix hook → `1 failed, 13 passed`; the original four cases against the pre-E hook 5e7c96f → red. Hostile probes below, all as expected. |
| E-AC3 | `.claude/agents/reviewer.md` exists, mission says it starts from the files, never the author's conversation; `doc/templates/review-report.md` exists; AGENTS.md §5 shows `engineer → reviewer → qa` in every tier | PASS | `pytest tests/framework/test_doc_contracts.py -rs` → `62 passed, 1 skipped`; the skip is `test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now`, not an E-AC3 contract. `ls` shows both files; reviewer.md line 10 carries the mission sentence; `grep -n reviewer AGENTS.md` shows tiers 0, 1 and 2 (lines 93-95) each with engineer, then reviewer, then qa. |
| E-AC4 | `coordinator_lint.py` rule 7: a `Slice:` brief carries `Impact:` and `Selected:`, or `unavailable (<reason>)` until B and H ship | PASS | `pytest tests/coordinator/test_coordinator_lint.py` → `86 passed`. Planted briefs (Slice, Under, Criteria, Verify with): no Impact/Selected → two rule 7 violations; `unavailable (reason)` on both → no rule 7 line; bare `unavailable` → `'Impact:' says unavailable with no reason`; filled paths → clean. Opt-in on `Under:` matches spec impact row 19 (line 271: "Rule active only when the brief has `Under:`"). |

### E-AC2 red-first, run in this review

- **The fix's own tests.** In a `git archive ed5c7e8` copy, `tests/hooks/test_guard_agent_spawn.py` gives `105 passed`. With the hook replaced by `ed5c7e8^`, it gives `20 failed, 85 passed`. The reds are the new rule's tests, among them `test_a_review_line_pointing_at_another_specs_review_blocks`, `test_a_spec_or_slice_line_names_the_spec_under_test_over_the_first_mention[Spec:]`, `test_a_review_line_with_no_spec_named_blocks_and_asks_for_the_spec`, `test_an_upstream_near_miss_of_the_spec_under_test_blocks[doc/specs/XSPEC-zz99-a.md]` and `test_a_bugfix_prompt_with_no_review_line_asks_for_a_bugfix_review`.
- **QA's defect reproduction.** With HEAD's tests and the `ed5c7e8^` hook: `FAILED tests/hooks/test_regression_guard_agent_spawn_review.py::test_regression_a_dependency_review_quoted_for_context_does_not_open_qa_for_another_spec` and `1 failed, 13 passed`. At HEAD it passes.
- **The four spec cases.** With the ed5c7e8 tests and the pre-E hook (5e7c96f), these are red, among others: `test_a_missing_review_blocks_the_qa_spawn[qa]` and `[frontend-qa]`; `test_a_review_without_a_pass_verdict_blocks[## Verdict: FAIL]`; `test_a_review_by_the_author_run_blocks[equal]`, `[case]`, `[zero-width]`, `[full-width]`; `test_bugfix_work_does_not_accept_a_non_bugfix_review`; `test_bugfix_work_with_a_failing_bugfix_review_blocks`; `test_the_bugfix_override_does_not_bypass_the_review_gate`.
- A count over HEAD's whole test file against `ed5c7e8^` (56 failed) is not cited: about 35 of those reds are later JC-AC3/JC-AC6 brief tests (9278b21, 0601a0b), not E-AC2.

## Defects (if FAIL)

None.

## Hostile inputs tried

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

## Exit gate

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

## Parked

- **Exit gate red from 7661338 (above).** Owner: whoever owns the gate-3 bugfix reports. The main tree already holds uncommitted edits to both files that escape the literal.
- **Proposed LIMIT line.** A malformed payload crashes the hook with exit 1, which does not block. Two cases: a JSON list (`'list' object has no attribute 'get'`) and a string `tool_input`. The module docstring says malformed input exits 0, so the behaviour differs from the text, but both outcomes allow the spawn. This is a harness-supplied payload, so it is outside the mistakes-only threat model. The code predates ed5c7e8.
- **A stale bugfix review opens QA.** With `NO_SPEC_BUGFIX:`, any PASS `REVIEW-bugfix-*.md` named on the `Review:` line opens the gate, because there is no spec or id to match it against. The spec does not bind the id, so this is not an E-AC2 failure.
- **The named review is not tied to the slug.** The file on the `Review:` line need not be named after the spec. A PASS review under any name whose Upstream names the spec under test opens the gate. The spec says `REVIEW-<slug>.md`. The Upstream check covers the mistake case this review was asked to look for.
- **Carried from QA, re-seen here.** An upper-case `QA` subagent type is not gated.
