# QA Report: delegated-autonomy increment E part 1 — learning loop, reviewer gate before QA, impact rule

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy.md
Date: 2026-10-20

## Verdict: FAIL

E-AC1, E-AC3 and E-AC4 pass. E-AC2 fails on one case. A QA prompt can name the spec under test, a dependency's spec and that dependency's PASS review. The gate then opens even though `doc/qa/REVIEW-<slug>.md` for the spec under test does not exist.

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
| Medium | **A dependency's review opens QA for a spec that has no review.** In the named-review path, a REVIEW is accepted when its `Upstream:` names *any* SPEC in the prompt. Repro: the prompt `Verify doc/specs/SPEC-a.md. It builds on SPEC-b.md, already reviewed in REVIEW-b.md.` with only `REVIEW-b.md` (PASS, Upstream SPEC-b.md) gives exit 0. Commit f672e3f says it closed exactly this case, so this is a gate reporting green falsely. Same root, two other faces. First, when the prompt names no SPEC, any named PASS review opens the gate. Second, the derived path blocks a legitimate QA: `QA SPEC-a.md (builds on SPEC-b.md)` with a PASS `REVIEW-a.md` is blocked on `REVIEW-b.md: not found`. Both paths need one consistent rule for which spec is under QA. | .claude/hooks/guard_agent_spawn.py:161-178 (`_check_review`), :154-157 (Upstream check) | ai-engineer | missed-ac |

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
