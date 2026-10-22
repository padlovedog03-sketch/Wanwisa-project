# QA Report: delegated-autonomy increment E part 1 — learning loop, reviewer gate before QA, impact rule

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy.md
Date: 2026-10-20

## Verdict: PASS (re-test 3, 2026-10-22)

Re-test 3 on the uncommitted fix in worktree `agent-a4f98650319afa539` (on c041dbb; see the section at the end): all 4 criteria pass. Defect 2 is closed: a non-bugfix QA prompt must name the spec under test on a `Spec:` or `Slice:` line, and the gate no longer guesses it from prose. The PASS covers that working tree only. It holds for the branch once those 5 files are committed unchanged.

Re-test 2 at HEAD 0fd71b6 (see the section at the end): E-AC1, E-AC3 and E-AC4 still pass. Defect 1 as first reported is closed by ed5c7e8. E-AC2 still fails on the same root with the word order swapped (Defect 2): when the prompt names the dependency's spec first and has no `Spec:` line, the dependency's review on the `Review:` line opens QA for a spec that has no review.

First run (2026-10-20): E-AC1, E-AC3 and E-AC4 pass. E-AC2 fails on one case. A QA prompt can name the spec under test, a dependency's spec and that dependency's PASS review. The gate then opens even though `doc/qa/REVIEW-<slug>.md` for the spec under test does not exist.

Scope: branch `worktree-agent-a1a8c8b68041cce03` at f672e3f (commits f205c0a and f672e3f), plus one uncommitted QA test file. E-AC5 and E-AC6 are deferred and were not checked.

Provenance:
- The invocation gives the owner's lean-gates ruling (`doc/memory/lean-gates-risk-based-qa.md`) as the basis. It does not say that a human approved this implementation, and QA did not see such an approval.
- Neither the worktree nor the main checkout has a `doc/qa/REVIEW-delegated-autonomy*.md`. This QA therefore ran without the independent review that this feature now requires. The gate did not stop it because the main checkout's hook predates this branch.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| E-AC1 | `learning_loop.py --window 28` groups rework causes and feedback memories into recurring causes (≥ 2), each with a stub marked `owner approval required (AH5)`, and exits 0. Without H it prints `unavailable: rework causes not shipped` | PASS | See the E-AC1 notes below. |
| E-AC2 | The gate refuses `qa` and `frontend-qa` when the REVIEW file is missing or not PASS, or when `Reviewer-run` equals `Author-run`. Bugfix work uses `REVIEW-bugfix-<id>.md`. Each case is planted and shown red | FAIL | See the E-AC2 notes below and Defect 1. |
| E-AC3 | `reviewer.md` exists, and its mission says it starts from the files and never from the author's conversation. `review-report.md` exists. AGENTS.md §5 shows `engineer → reviewer → qa` in every tier | PASS | See the E-AC3 notes below. |
| E-AC4 | Rule 7: a `Slice:` brief carries `Impact:` and `Selected:`, or `unavailable (<reason>)` | PASS | See the E-AC4 notes below. |

Counts: 3 PASS, 1 FAIL, out of 4 criteria.

### E-AC1 evidence

- `python3 scripts/learning_loop.py --window 28` exits 0 (`EXIT=0`) on this repo.
- On this repo it prints `missed-ac: 9 (QA rework)` and `lesson-without-mechanism: 2 (feedback memories: hostile-inputs-in-every-ac.md, rework-goes-in-a-fresh-brief.md)`. Each line is followed by its proposal stub, which ends in `owner approval required (AH5)`.
- Planted data: 2 FAIL reports with `missed-ac` give `missed-ac: 2`. A memory body containing a marker value is never printed.
- `tests/framework/test_learning_loop.py` passes inside the `framework` step (16 test functions). Those tests include `test_without_rework_causes_it_says_unavailable_and_exits_0`.

### E-AC2 evidence

- **Red-first, re-run by QA.** The new tests in `tests/hooks/test_guard_agent_spawn.py` were run against the pre-change hook (5e7c96f) in a scratch copy: `36 failed, 38 passed`. Every planted case is among the failures: missing review, the FAIL, template, `PASSED` and `pending` verdicts, equal run IDs (case, spaces, NBSP, zero-width and full-width variants), the bugfix review, and the override not bypassing the gate. Against f672e3f all of them pass.
- **QA probes.**
  - The gate stays shut for:
    - a copied but unfilled template;
    - a review whose verdict is `Pass`, `PASS.`, or `PASS — sentence`;
    - a fenced `Verdict: FAIL`.
  - The gate opens for:
    - a CRLF file;
    - a file starting with a BOM;
    - a bold or backticked `Upstream:`.
- **Defect reproduction.** `test_regression_a_dependency_review_quoted_for_context_does_not_open_qa_for_another_spec` is red: `assert 0 == 2`.

### E-AC3 evidence

- In `tests/framework/test_doc_contracts.py`, these pass:
  - the reviewer front matter;
  - the mission sentence;
  - the run-ID lines and `LIMIT`;
  - the 5 template lines;
  - `test_agents_md_shows_engineer_then_reviewer_then_qa_in_every_tier`.
- The ordering check has teeth: `test_the_tier_row_check_rejects_a_row_with_reviewer_after_qa`.

### E-AC4 evidence

- **Red-first, re-run by QA.** The rule 7 tests were run against the pre-change `coordinator_lint.py`: `18 failed, 47 passed`. Against f672e3f all pass.
- Rule 7 is opt-in: it applies only to a brief with `Under:`. Spec impact row 19 says this: "Rule active only when the brief has `Under:`".
- QA probe results:
  - A brief with no `Under:` is clean.
  - `unavailable (reason)` is accepted.
  - A bare `unavailable` is flagged.

## Test Run

```
$ python3 -m pytest tests/hooks/test_regression_guard_agent_spawn_review.py -q -p no:cacheprovider
FAILED tests/hooks/test_regression_guard_agent_spawn_review.py::test_regression_a_dependency_review_quoted_for_context_does_not_open_qa_for_another_spec
1 failed, 13 passed in 0.37s
```

The final `scripts/verify-full.sh` output is pasted in the hand-back message.
- It is red on the `hooks` step because of the one defect reproduction above.
- It still reads EXIT GATE INCOMPLETE, because the lint, format and tests steps are not configured in this repo.

The baseline run before QA added its test was:
- hooks: 290 passed;
- ci-examples: 19 passed;
- coordinator: 134 passed;
- framework: OK;
- exit 0.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Medium | Closed in re-test 2. **A dependency's review opens QA for a spec that has no review.** In the named-review path, a REVIEW is accepted when its `Upstream:` names *any* SPEC in the prompt. Repro: the prompt `Verify doc/specs/SPEC-a.md. It builds on SPEC-b.md, already reviewed in REVIEW-b.md.` with only `REVIEW-b.md` (PASS, Upstream SPEC-b.md) gives exit 0. Commit f672e3f says it closed exactly this case, so this is a gate reporting green falsely. Same root, two other faces. First, when the prompt names no SPEC, any named PASS review opens the gate. Second, the derived path blocks a legitimate QA: `QA SPEC-a.md (builds on SPEC-b.md)` with a PASS `REVIEW-a.md` is blocked on `REVIEW-b.md: not found`. Both paths need one consistent rule for which spec is under QA. | .claude/hooks/guard_agent_spawn.py:161-178 (`_check_review`), :154-157 (Upstream check) | ai-engineer | missed-ac |
| Medium | Closed in re-test 3. **Re-test 2: a dependency's review still opens QA when the dependency's spec is named first.** Closed for Defect 1's word order, open for the reverse. `_spec_under_test` falls back to the first SPEC in the prompt when there is no `Slice:` or `Spec:` line, so the Upstream check compares the dependency's review with the dependency's own spec. Repro at HEAD 0fd71b6, with `REVIEW-zqb.md` (PASS, Upstream `doc/specs/SPEC-zqb.md`, distinct run IDs) and no review at all for SPEC-zqa: the prompt `QA the change. It builds on SPEC-zqb.md; the work under test is SPEC-zqa.md.` plus `Review: doc/qa/REVIEW-zqb.md` gives exit 0. The same prompt with SPEC-zqa named first gives exit 2. Nothing makes a QA brief carry a `Spec:` line: AGENTS.md §5 requires only the `Review:` line, and `coordinator_lint.py` has no `Spec:` rule. | .claude/hooks/guard_agent_spawn.py, `_spec_under_test` (the "else the first SPEC the prompt names" fallback) | ai-engineer | missed-ac |

## Engineer's choices, judged

1. **Rule 7 only with `Under:`.** Accepted. The spec states it in impact row 19, and R20 is opt-in (Increments table, row 9).
2. **The learning loop's grouping.** Accepted. Memories carry no cause field, so `lesson-without-mechanism` is the only grouping the data supports. It counts `mechanism: none — <reason>` as unmechanised, which matches "lessons kept only as memory". QA rework reuses the meter's parser, so the two reports cannot disagree.
3. **How the gate picks the REVIEW file.** Rejected in part; see Defect 1. These parts work:
   - the bugfix path;
   - increment-scoped names such as `REVIEW-<slug>-E1.md`;
   - the requirement that a named review's Upstream must match a named spec.
4. **Verdict and run-ID parsing.** Accepted.
   - It fails closed on decorated or partial verdicts, and the block message names the bad value.
   - Run IDs are compared after NFKC, whitespace, format-character and case folding.
   - A non-placeholder filler such as `Reviewer-run: TBD` is accepted (Parked).
5. **AGENTS.md §5.** Accepted. E-AC3 requires reviewer and qa in every tier. Tier 1 can no longer run engineer and QA in parallel, because QA now waits for the review. The tier-2 👤 between reviewer and qa follows §6 until increment G reconciles it.

## Usability (owner focus)

- **The block message.** It is one actionable line, and it names the file, the problem, the `reviewer` agent and the template. Pinned by `test_regression_every_review_block_is_one_line_naming_the_file_and_the_bad_value`.
- **Normal spawns stay allowed.** All of these exit 0: `pm`, `ba-sa`, `Explore`, `Plan`, `general-purpose`, `reviewer`, `caveman:cavecrew-reviewer` and `claude`. Pinned.
- **Legitimate QA blocked by a gate quirk.**
  - A prompt that names the spec only by slug (`QA the alpha feature`) is blocked. The message tells you what to add.
  - A prompt that mentions a dependency's SPEC is blocked (Defect 1).
  - **Worktrees.** The hook runs from `$CLAUDE_PROJECT_DIR`, and `_repo_root()` reads `doc/qa/` next to it. A reviewer that writes its REVIEW inside an isolated worktree is therefore invisible to the gate until the file is merged or copied into the coordinator's checkout. Expect a `not found` block on the first QA spawn after a worktree review (Parked).
  - **Case mismatch.** `SPEC-Alpha.md` in the prompt against a `REVIEW-alpha.md` file opens the gate on macOS, which is case-insensitive. On Linux the same prompt is blocked.

## Known gaps the engineer listed, judged against the E-ACs

- **FIFO review file hangs.** This is a declared limit, following `doc/memory/ease-of-use-over-strictness.md`: a FIFO in `doc/qa/` is deliberate, not accidental.
- **`Verdict:` read inside code fences.**
  - A fenced FAIL keeps the gate shut. That is safe, but it will confuse a review of this very gate that quotes hostile inputs.
  - A fenced PASS opens the gate only when the file has no real verdict line.
  - Both are declared limits.
- **Case-insensitive name resolution on macOS.** The result depends on the platform, as described above. It is a declared limit, not an E-AC failure.

## Edge Cases Probed

- learning_loop `--window 0` or `-3` → exit 2 with `--window must be at least 1`; `--window abc` → argparse error, exit 2.
- learning_loop `--window 800000` → `OverflowError: date value out of range`, exit 1 (Parked).
- learning_loop with a quoted `type: "feedback"` → silently skipped. `memory_lint` also rejects that type, so the two agree (Parked).
- learning_loop with a quoted `date: '…'` → counted under `no date`.
- learning_loop with a CRLF memory → read correctly.
- Rule 7 with `Under: none` → the rule switches on.
- Rule 7 with `Impact: n/a` or `Selected: TBD` → accepted.
- Rule 7 with `unavailable(reason)` (no space) or `unavailable (r) — more` → flagged, with a message that says "no reason".
- Rule 7 with a bold `**Under:**` → rule 7 silently off. This is the same prefix grammar rule 6 uses for `Slice:` (Parked).
- Review gate with `QA` in upper case or `plugin:qa` → not gated (Parked).

## Approval history

- **2026-10-20 — drafted.** By qa, from SPEC-delegated-autonomy E-AC1–E-AC4 and commits f205c0a and f672e3f. The verdict comes from runs made in this QA session.
- **2026-10-22 — re-test 2.** By qa, at HEAD 0fd71b6 on `feat/top3-tiers-mechanisms-deny`, after fix ed5c7e8 (merged in a60d8f2) and its PASS review doc/qa/REVIEW-delegated-autonomy-E1.md. The verdict stays FAIL on E-AC2 (Defect 2). Status stays In Review.
- **2026-10-22 — re-test 3.** By qa, on the uncommitted 5-file fix in worktree `agent-a4f98650319afa539` (base c041dbb), after its PASS re-review (commit 0d92200). Verdict PASS, 4 of 4. Status stays In Review for the owner's approval.

## Re-test 2

Date: 2026-10-22. Scope: HEAD 0fd71b6, which contains fix ed5c7e8 (merged in a60d8f2). Review read: doc/qa/REVIEW-delegated-autonomy-E1.md (PASS). Probes ran on a `git archive HEAD` copy in the scratchpad with planted `doc/qa/` files. Exit 2 is block, 0 is allow.

Provenance: the brief is a Tier 1 re-test under an approved spec. It confirms Tier 1 pre-approval, not a human approval of this implementation, and QA saw none.

| # | Verdict | Evidence (run in this re-test) |
|---|---|---|
| E-AC1 | PASS | `pytest tests/framework/test_learning_loop.py` → `17 passed`. `python3 scripts/learning_loop.py --window 28` → EXIT=0. Before this edit it printed `missed-ac: 19`, `spec-defect: 10`, `test-gap: 2` and `lesson-without-mechanism: 4`, each with a stub ending `owner approval required (AH5)`. |
| E-AC2 | FAIL | `pytest tests/hooks/test_guard_agent_spawn.py` → `162 passed`. `pytest tests/hooks/test_regression_guard_agent_spawn_review.py` → `14 passed`. Red-first: with the `ed5c7e8^` hook, the regression test fails, `1 failed, 13 passed`. Probes are below. Defect 2 is open. |
| E-AC3 | PASS | `pytest tests/framework/test_doc_contracts.py -rs` → `62 passed, 1 skipped`. The skip is `test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now`, which is not an E-AC3 contract. |
| E-AC4 | PASS | `pytest tests/coordinator/test_coordinator_lint.py` → `86 passed`. |

Counts: 3 PASS, 1 FAIL, out of 4 criteria.

### E-AC2 probes at HEAD

Every planted review has a PASS verdict and distinct run IDs unless stated. Every prompt has a filled Tier and Files line.

- **The original repro is closed.**
  - The prompt `Verify doc/specs/SPEC-zqa.md. It builds on SPEC-zqb.md, already reviewed in REVIEW-zqb.md.` with no `Review:` line → 2.
  - The same prompt plus `Review: doc/qa/REVIEW-zqb.md` → 2. The message reads `its Upstream: does not name SPEC-zqa.md, the spec under test — it reviews other work`.
- **Its two other faces are closed.**
  - A `Review:` line with no spec named → 2. The message asks for a `Spec:` line.
  - `QA SPEC-zqa.md (builds on SPEC-zqb.md)` with `Review:` naming a PASS `REVIEW-zqa.md` → 0. The legitimate case is no longer blocked.
- **These stay shut (2):**
  - a `Spec:` line for SPEC-zqa with `Review:` naming the dependency's review, whether the dependency is mentioned first in prose or both lines are bold;
  - a dependency's review that names SPEC-zqa only on a non-Upstream line;
  - an Upstream that differs only in case;
  - an Upstream of `SPEC-zqa.md.bak`;
  - a FAIL verdict;
  - run IDs `Run-1` and ` run-1 `;
  - a missing review file;
  - two `Review:` lines with the dependency's first;
  - `NO_SPEC_BUGFIX:` work naming a non-bugfix review.
- **These open, as expected (0):**
  - bulleted `Spec:` and `Review:` lines;
  - an increment review `REVIEW-zqa-E1.md`;
  - a bugfix review for bugfix work;
  - a `doc/qa/../qa/` path, since only the file name is used;
  - `reviewer`, which is ungated;
  - this re-test's own brief shape.
- **Defect 2 (open).** Before the run, `REVIEW-zqa.md` was removed so that SPEC-zqa had no review at all. The prompt `QA the change. It builds on SPEC-zqb.md; the work under test is SPEC-zqa.md.` plus `Review: doc/qa/REVIEW-zqb.md` → **0**. The spec under test has no review, and the dependency's review opened the gate.
  - **Why it is in scope.** The threat model covers mistakes. Writing the dependency first and pasting the wrong review name is the same mistake Defect 1 described. The fix only catches it when the spec under test comes first. The independent review probed only that order.
  - **Not added as a test.** This brief's `Files:` allows only this report. The repro above is the one the engineer needs.

### Exit gate

`scripts/verify-handoff.sh --status` → `not opted in`, so the verdict command is `scripts/verify-full.sh`. It was run after this edit, and its result is in the hand-back message.

### Parked (re-test 2)

- **A `Review:` line inside a code fence opens the gate.** This is outside the letter of E-AC2.
- **A review whose Upstream names two specs opens QA for either.** This is outside the letter of E-AC2.
- **Carried from the review.** These are already parked in doc/qa/REVIEW-delegated-autonomy-E1.md:
  - the named review is not tied to the slug;
  - a stale bugfix review opens QA;
  - a malformed payload crashes the hook with exit 1, which does not block.

## Re-test 3

Date: 2026-10-22. Scope: the uncommitted fix in worktree `.claude/worktrees/agent-a4f98650319afa539`, base c041dbb. It changes 5 files: `.claude/hooks/guard_agent_spawn.py`, `.claude/agents/reviewer.md`, `AGENTS.md`, `tests/hooks/test_guard_agent_spawn.py` and `tests/hooks/test_regression_guard_agent_spawn_review.py`. Review read: doc/qa/REVIEW-delegated-autonomy-E1.md (re-review PASS, commit 0d92200). Probes ran on a copy of that working tree in the scratchpad, with planted `doc/qa/` files. Exit 2 is block, 0 is allow.

The fix: `_spec_under_test` returns only the SPEC on the first `Spec:` or `Slice:` line that names one. The first-mention fallback is gone. A non-bugfix QA prompt without such a line is refused with one line asking for `Spec: doc/specs/SPEC-<slug>.md`. AGENTS.md §5 tier 1 and `reviewer.md` now say the QA brief carries that line.

Provenance: the brief is a Tier 1 re-test under an approved spec. It confirms Tier 1 pre-approval, not a human approval of this implementation, and QA saw none.

| # | Verdict | Evidence (run in this re-test, on the worktree) |
|---|---|---|
| E-AC1 | PASS | `pytest tests/framework/test_learning_loop.py` → `17 passed`. `python3 scripts/learning_loop.py --window 28` → EXIT=0, with 4 stubs ending `owner approval required (AH5)`. |
| E-AC2 | PASS | `pytest tests/hooks/test_guard_agent_spawn.py` → `162 passed`. `pytest tests/hooks/test_regression_guard_agent_spawn_review.py` → `19 passed`. Red-first: the same two files against the c041dbb hook → `4 failed, 177 passed`, and the 4 failures are the new repro test, the no-`Spec:`-line refusal for `qa` and `frontend-qa`, and the slice-without-spec test. Probes are below. |
| E-AC3 | PASS | `pytest tests/framework/test_doc_contracts.py -rs` → `62 passed, 1 skipped`. The skip is `test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now`, which is not an E-AC3 contract. The tier rows of AGENTS.md §5 still show `engineer` → `reviewer` → `qa`. |
| E-AC4 | PASS | `pytest tests/coordinator/test_coordinator_lint.py` → `86 passed`. |

Counts: 4 PASS, 0 FAIL, out of 4 criteria.

### E-AC2 probes on the fix

`REVIEW-zqb.md` is a PASS review with Upstream `doc/specs/SPEC-zqb.md` and distinct run IDs. SPEC-zqa has no review unless stated. Every prompt has a filled Tier and Files line.

- **The re-test 2 repro is closed.** `QA the change. It builds on SPEC-zqb.md; the work under test is SPEC-zqa.md.` plus `Review: doc/qa/REVIEW-zqb.md` → **2**, for both `qa` and `frontend-qa`. The message asks for a `Spec:` line.
- **These stay shut (2):**
  - the spec under test named first in prose, with no `Spec:` line;
  - a `Spec:` line for SPEC-zqa with the dependency's review, whether the `Spec:` line comes before or after the `Review:` line;
  - a `Spec:` line naming SPEC-zqa then SPEC-zqb, with the dependency's review;
  - a `Slice:` line with no SPEC on it and the dependency named in prose;
  - a `Spec:` line with no SPEC on it and the dependency named in prose;
  - a lower-case `spec:` line;
  - a missing review, a FAIL review, and run IDs `r1` and ` R1 `;
  - `NO_SPEC_BUGFIX:` work naming a non-bugfix review;
  - a correct PASS review with the spec only in prose. This was allowed before the fix; it is now refused with a one-line message saying what to add.
- **These open, as expected (0):**
  - a `Spec:` line for SPEC-zqa with a PASS `REVIEW-zqa.md`, for `qa` and `frontend-qa`, with a dependency named in prose;
  - a `Slice:` line carrying the SPEC path;
  - bold, bulleted `Spec:` and `Review:` lines;
  - a `Spec:` line with no SPEC followed by a `Slice:` line with one;
  - `NO_SPEC_BUGFIX:` work with a bugfix review and no `Spec:` line;
  - `reviewer`, which is ungated;
  - this re-test's own brief shape.

### Exit gate

- `scripts/verify-handoff.sh --status` → `not opted in`, so the verdict command is `scripts/verify-full.sh`.
- `python3 -m pytest tests -q -p no:cacheprovider` on the worktree → `1884 passed, 1 skipped`, exit 0.
- `scripts/verify-full.sh` on the worktree → exit 0. Steps: hooks `1308 passed`, ci-examples `30 passed`, scar-forge OK, coordinator `155 passed`, framework OK. Banner: `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. That is the repo's standing state, not a finding of this re-test.
- Both runs were on the worktree before this report was edited. This report is outside that tree.

### Parked (re-test 3)

- **LIMIT: a `Spec:` line that names the wrong spec opens the gate for the wrong work.** `Spec: doc/specs/SPEC-zqb.md` plus `Review: doc/qa/REVIEW-zqb.md` → 0. The gate trusts the brief's explicit subject. The threat model covers mistakes, not fraud. An explicit wrong `Spec:` line is a visible statement that a reader can check, unlike the prose guess that was removed.
- **Older QA briefs without a `Spec:` line are now refused.** This includes the shape that re-test 2 listed as open. The refusal is one actionable line, and AGENTS.md §5 tier 1 now names the line. It is a usability cost, not a defect.
- **AGENTS.md §5 names the `Spec:` line only in the tier 1 row.** The tier 2 row's QA gate cell does not, yet tier 2 QA briefs are refused without it too. This sits outside E-AC1–E-AC4.
- **Carried from re-test 2:** a `Review:` line inside a code fence; a review whose Upstream names two specs; and the items parked in doc/qa/REVIEW-delegated-autonomy-E1.md.
