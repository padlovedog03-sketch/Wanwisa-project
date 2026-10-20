# QA Report: verify-tiers increment D — merge gate

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Date: 2026-10-20

## Verdict: PASS

QA ran its own tests at head 1ee6f19 (worktree `agent-a251af236e29ab259`), and all eight D criteria pass. An honest candidate with a real pytest suite gets `MERGE GATE GREEN`, bound to its tree. The same candidate with a real failing test gets `MERGE GATE RED`, exit 1. The exit gate ends INCOMPLETE with exit 0 and has no RED step.

Scope: this was a confirmation round only, not a new search for defects. The threat model is scope-discipline rule 5 and doc/memory/stay-on-the-definition.md. Review: doc/qa/REVIEW-verify-tiers-merge-gate-D.md (PASS, separate run).

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| D-AC1 | GREEN in a fresh worktree, bound to tree and runner | PASS | `test_green_runs_in_a_fresh_worktree_and_binds_tree_and_runner` passes. QA's own scratch repo has a real pytest suite of 2 tests, `VERIFY_RUNNER_ID=runner-7`. `verify-merge.sh HEAD` gives `counts: reported 2 of 2 collected` and `MERGE GATE GREEN — tree 5b235e9a… — runner runner-7`, exit 0. The merge record has `tree.before == tree.after == tree.judged == HEAD^{tree}` and `runner.kind = runner`. Afterwards `git worktree list` shows 1 entry. |
| D-AC2 | exactly one banner; RED exit 1, NOT RUN exit 3 | PASS | Test parametrisations pass. In the scratch repo: a real failing test (`assert 2*2 == 5`) gives `FAIL tests`, then `MERGE GATE RED — tree 5c6bd49f… — runner runner-7`, exit 1, 1 banner. Removing `VERIFY_COLLECT_CMD` gives `MERGE GATE NOT RUN — executed == collected is not configured`, exit 3, 1 banner. With `VERIFY_MERGE_GATE=none` the output is `MERGE GATE NOT RUN — no runner and no local fallback configured`, exit 3, 1 banner. |
| D-AC3 | `--check` refuses another tree and a record with no runner | PASS | `test_check_refuses_a_record_for_another_tree` and `test_check_refuses_a_record_that_names_no_runner[*]` pass. In the scratch repo, a CI-style `VERIFY_RUNNER_ID=ci-1 verify-full.sh` record: checked against the same tree it gives GREEN, exit 0. Checked against another tree it gives `MERGE GATE NOT RUN — record is for tree 5b235e9a…, candidate is tree 5c6bd49f…`, exit 3. A local record gives `MERGE GATE NOT RUN — record names no runner (kind local)`, exit 3. The reviewer re-proved RED-FIRST (the review, D-AC3 row). |
| D-AC4 | local fallback is labelled weaker | PASS | `test_local_fallback_without_a_runner_id_is_labelled_weaker` passes. In the scratch repo the committed conf sets `local-fallback` and the run has no `VERIFY_RUNNER_ID`. Output: `MERGE GATE GREEN — tree f2d40cd9… — runner local:4017c78e26d1 (local fallback — weaker: same machine and same user as the agent)`. |
| D-AC5 | dirty caller tree: HEAD is judged, caller is untouched | PASS | Both dirty-tree tests pass. In the scratch repo, HEAD has a failing test committed, the caller fixes it without committing, and an untracked file is added. The gate still gives `MERGE GATE RED — tree 5c6bd49f…` (the committed tree). Afterwards `git status --short` still shows ` M tests/test_bad.py` and `?? untracked.txt`, and the fix is still in the file. |
| D-AC6 | every requiring line carries the opt-in qualifier | PASS | `tests/framework/test_doc_contracts.py` passes in the run below. |
| D-AC7 | QA verdict rests on its own run | PASS | `test_qa_verdict_rests_on_its_own_run_never_an_earlier_record[*]` passes in the run below. |
| D-AC8 | conf example, SETUP, CI runner id, ci tests, neutrality 0 | PASS | `tests/ci` passes in the run below, and the exit gate gives `ci-examples 22 passed`. `test_the_example_conf_and_setup_document_runner_fallback_and_none` passes. `python3 scripts/check_neutrality.py` gives `neutrality: 0 provider name(s) in layers 0-1, 0 project leak(s)`. |

## Test Run

```
$ python3 -m pytest tests/hooks/test_verify_merge.py tests/framework/test_doc_contracts.py tests/ci -q -p no:cacheprovider
132 passed, 1 skipped in 39.16s
  (skip: test_doc_contracts.py:193 "agent_time.REWORK_CAUSES is the source now" — pre-existing, not D)

$ scripts/verify-full.sh        # worktree, head 1ee6f19
  TODO lint / format / tests   not configured — this step verified NOTHING
  OK   hooks        858 passed
  OK   ci-examples  22 passed
  OK   scar-forge
  OK   coordinator  111 passed
  OK   framework    memory: 0 problem(s)
counts: not configured — executed == collected NOT checked
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
exit=0
```

## Defects (if FAIL)

None.

## Edge Cases Probed

- A dirty caller tree with an uncommitted fix of the committed failing test → RED on the committed tree, and the caller's files are untouched.
- `--check` of a genuine runner record against the same tree → GREEN. Against a different tree → NOT RUN. A local record → NOT RUN (kind local).
- `VERIFY_MERGE_GATE=local-fallback` set only in the environment while the base conf says `runner` → `NOT RUN — VERIFY_MERGE_GATE=runner but VERIFY_RUNNER_ID is empty`. The base conf wins, as the conf example documents ("gate code and THIS file taken from the base ref"). This fails closed and is not a defect.

## Parked

- The reviewer's parked items stay parked unchanged. They include R7 (a test step rewrites the recorder: deliberate fraud, a declared LIMIT) and the moving-base `--check` case, which fails closed.

## Approval history

- **2026-10-20 — drafted.** qa, confirmation round at 1ee6f19 against SPEC-verify-tiers-merge-gate.md D-AC1..D-AC8 (Approved, `spec-verify-tiers-merge-gate-2026-10-20`) and REVIEW-verify-tiers-merge-gate-D.md (PASS).
