# Review: Jarvis coordinator, Increment 2: the scorecard (R9–R10)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-jarvis-coordinator-inc2-scorecard.md
Author-run: a477ed9734a9e26e3
Reviewer-run: ae675b38f138bc90e
Date: 2026-10-22

## Verdict: PASS

All twelve criteria, SC-AC1 to SC-AC12, hold on commands run in this review. The SC-AC9 baseline replay reproduces every number in the spec's Baseline table for W0 and W1, with no differences. The default time report is byte-identical to HEAD on real transcripts. Every planted mistake I put in the source turns a plain (not monkeypatched) test red.

## Read from

- Upstream: `doc/specs/SPEC-jarvis-coordinator-inc2-scorecard.md` (Approved, `spec-jarvis-coordinator-inc2-scorecard-2026-10-22`)
- Change: uncommitted files in the author's worktree `agent-a477ed9734a9e26e3`:
  - `scripts/agent_time.py`;
  - `.claude/meter/transcript_reader.py`;
  - `tests/framework/test_agent_time.py`;
  - `tests/hooks/test_transcript_reader.py`;
  - 3 new fixture directories: `tests/framework/fixtures/agent_time/scorecard/`, `tests/hooks/fixtures/transcripts/scorecard-owner/`, `tests/hooks/fixtures/transcripts/scorecard-turn-ends/`.

  These were overlaid on a `git archive` of this branch's HEAD `8482670` in a scratch copy (`new`). A second, untouched copy of HEAD (`base`) served as the "before".
  - The author's worktree also differs from HEAD in `scripts/coordinator_lint.py`, `tests/coordinator/test_coordinator_lint.py`, `tests/ci/test_ci_examples.py` and two D8/D9 `doc/qa` files. Those differences come from the author's older base, not from this change, so they were not overlaid.
- Not read: the author's conversation or handback. Every result below was produced in this run.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| SC-AC1 | One block per metric, in order; runs alone; empty directory says "no …" | PASS | `python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py -q -p no:cacheprovider` on `new` → `220 passed`.<br>The tests assert the M1…M7 and owner-line order, the M5 text, `no exchanges`, the 4 `--scorecard runs alone` cases, `--until needs --scorecard`, the no-reader `unsupported` line, and an empty directory with no `0` in M1, M3, M4 or M6.<br>Mutant "empty M6 prints `0 of 0`" → 2 failed (`test_an_empty_directory_prints_no_for_every_metric_never_zero`, `test_only_exchanges_whose_owner_message_is_in_the_window_count`). |
| SC-AC2 | H-AC1 owner rule through the real reader (RED-FIRST) | PASS | The fixture `scorecard-owner/main.jsonl` holds exactly 3 owner lines, 2 `<task-notification>`, 1 `<command-name>`, 1 `isMeta: true`, 1 list-content text line and 4 tool results.<br>Planted mistake in the source, `_is_owner` → `return True`: 3 failed, including `test_only_plain_non_meta_main_thread_strings_are_owner_messages` and `test_the_scorecard_reports_3_owner_messages_and_3_exchanges`.<br>Mutant "ignore `isMeta`" → 2 failed.<br>New tests with HEAD's reader → 7 failed. |
| SC-AC3 | Turn ends are distinct ids (RED-FIRST) | PASS | Planted mistake in the source, `count_turn_ends` → per line: 2 failed (`test_one_reply_over_two_lines_is_one_turn_end`, `test_a_reply_spanning_two_lines_is_one_turn_end`).<br>Hostile cases are tested and green: no id counts 1 (×2 → 2); `tool_use`, list and `None` `stop_reason` are not turn ends; no timestamp → excluded. |
| SC-AC4 | Tier line grammar; first one wins | PASS | All 7 spec cases plus numbered and `* **Tier**:` cases are green.<br>Mutant "no NFKC" → the `Tier：0` case fails.<br>Mutant "owner text counts for tier" → the owner-only case fails.<br>Mutant "field anywhere on the line" → the mid-sentence case and the M6 case fail. |
| SC-AC5 | Window by owner message and first event; malformed times | PASS | Mutant "role runs windowed by last event" → `test_only_exchanges_whose_owner_message_is_in_the_window_count` fails.<br>Mutant "events after `--until` kept" → the same test fails.<br>The 7 bad-window cases print one error line with exit 0.<br>The existing `2026/10/01` refusal output is byte-identical to HEAD (AC11 run).<br>My own probes: `T25:00:00Z`, `.5Z`, empty, and full-width `Ｔ` each give one `agent-time: error:` line, exit 0, 0 bytes on stderr. |
| SC-AC6 | M3 per report slug | PASS | `test_m3_counts_runs_per_slug_once_each` asserts `a: review 2 · QA 1` and `1 run wrote no report`.<br>Mutants "count by run type", "engineers counted" and "slug printed raw" each go red.<br>Real-data replay matches the baseline M3 exactly (below). |
| SC-AC7 | M6 brief field lines | PASS | `M6 … 2 of 5` for the spec's 5 briefs plus `Explore`, and `1 of 2` for a role run with no inbound event: green.<br>My probe with a `None` brief text gave no crash. |
| SC-AC8 | M2, M7; missing or unreadable memory | PASS | Tests green for `1 … (previous 7: 1, flat)` / `M7 1`, for `M2, M7: memory directory not found`, and for `not measured (unreadable memory file)` with M1, M3, M4 and M6 still printed.<br>Mutant "missing dir falls through" → `test_a_missing_memory_directory_is_said_not_zero` fails.<br>My probe `--memory-dir` pointing at a file → `M2, M7: memory directory not found`, exit 0.<br>`cwd=/` with the default memory dir → full scorecard, exit 0 (the `correction_rate` import resolves). |
| SC-AC9 | Baseline replay | PASS | `python3 scripts/agent_time.py --reader .claude/meter/transcript_reader.py --dir ~/.claude/projects/-Users-pongsakorn-ni-Desktop-jarvis-framework --scorecard --since 2026-10-01T00:00:00Z --until 2026-10-21T02:03:54Z`, then the same with `--since 2026-10-21T02:03:54Z --until 2026-10-22T09:00:00Z`, run read-only on `new`.<br>**Every cell of the Baseline table is reproduced, with 0 differences.** See "Baseline replay" below. |
| SC-AC10 | No transcript text leaks | PASS | `test_the_canary_never_reaches_the_scorecard_output` is green (the canary appears ≥ 6 times in the fixtures).<br>My own fixture puts the canary in an owner `Tier:` line, a Jarvis `Tier:` line, a brief `Files:` line and an unprintable slug `REVIEW-CANARY 7f3a.md` → `grep -c CANARY` on the output = `0`.<br>The internal-error test prints only `agent-time: internal error: RuntimeError`. |
| SC-AC11 | One instrument; default output byte-identical | PASS | `diff base/tests/… new/tests/…` → 0 removed lines in both test files (additions only).<br>The four named files on HEAD gave `246 passed`; on `new`, `306 passed`.<br>HEAD's meter vs the new meter on one read-only snapshot of the real transcripts → `IDENTICAL` for each of:<ul><li>default (88 lines, 6974 bytes);</li><li>`--since 2026-10-15 --rework --qa-dir doc/qa`;</li><li>`--targets … --min-runs 2 --include-probes`;</li><li>`--min-runs 3`;</li><li>no reader;</li><li>`--since 2026/10/01`;</li><li>`--min-runs 0`;</li><li>the stub reader on the neutral fixtures.</li></ul> |
| SC-AC12 | M4 to first reply after a tool result | PASS | `test_m4_counts_the_first_turn_end_after_a_tool_result` covers (a) 1.5, (b) 1.0, (c) and (d) as `no result: 2`.<br>Mutant "first turn end regardless of result" → red.<br>A mutant letting a pre-owner result count is equivalent, so it is not a gap: the exchange span starts at the owner message, so case (d) holds by construction. |

**Red-first at HEAD:** with the new tests and fixtures on HEAD's code, the result is `52 failed, 168 passed`. The two files hold 160 tests at HEAD and 220 after the change, so 60 are new: 52 are red at HEAD and **8 are already green at HEAD**. Diffing the `-rA` PASSED lists of `base` and the red copy names them:
- **The 7 `test_a_bad_window_is_one_error_line_and_exit_0` cases.** At HEAD, `--scorecard` is an unknown flag, so argparse already prints an `agent-time: error:` line. Three window-parsing mutants on the new code show that 6 of the 7 cases catch a real bug in it:
  - removing the `until <= since` check → 2 failed (window0, window1);
  - accepting any offset after `T` → 2 failed (window3, window6);
  - accepting any ISO form → 4 failed (window2, window3, window5, window6).
  The 7th case, `--until 2026/10/22`, is the pre-existing refusal, which the existing `2026/10/01` test already covers.
- **`test_an_end_turn_line_with_no_timestamp_is_excluded`.** It asserts the "as today" behaviour SC-AC3 asks to keep, so it is green by design.

**Exit gate:** `bash scripts/verify-full.sh` was run on a git-initialised scratch copy of `new`, exit 0. Every configured step is OK:
- hooks: `1388 passed` (HEAD copy: `1376 passed`, so +12 new reader tests);
- ci-examples: `32 passed`;
- scar-forge: OK;
- coordinator: `160 passed`;
- framework: OK. Run directly, `tests/framework/` gives `423 passed, 1 skipped` (HEAD: `375 passed, 1 skipped`, so +48). The must-stay-green files `test_correction_rate.py`, `test_doc_contracts.py`, `test_learning_loop.py` and `test_settings_deny.py` give `84 passed, 1 skipped` on both.

The gate's own last lines, quoted whole: `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests` and `Everything configured passed, and that is ALL this run proves.` So the gate is not "green": lint, format and the project test step are template placeholders in this repo.

**QA spawn gate check:** `guard_agent_spawn._review_problem(<this file>, _spec_under_test("Spec: doc/specs/SPEC-jarvis-coordinator-inc2-scorecard.md"))` → `None`, so the gate opens. The same call with the am2 spec is refused (`Upstream:` does not name it). The file has exactly one verdict line, `## Verdict: PASS`.

### Baseline replay (SC-AC9), counts only

| Metric | Spec W0 | Replayed W0 | Spec W1 | Replayed W1 |
|---|---|---|---|---|
| Owner messages | 76 | 2026-10-08 2 · 10-20 70 · 10-21 4 = 76 | 8 | 10-21 1 · 10-22 7 = 8 |
| M1 tier 0 | — | no exchanges | 1 · 8 · 8.00 · 0 | 1 · 8 · 8.00 · 0 |
| M1 tier 1 | — | no exchanges | no exchanges | no exchanges |
| M1 tier 2 | — | no exchanges | 2 · 0 · 0.00 · 2 | 2 · 0 · 0.00 · 2 |
| M1 untiered | 76 · 103 · 1.36 · 46 | 76 · 103 · 1.36 · 46 | 5 · 17 · 3.40 · 4 | 5 · 17 · 3.40 · 4 |
| M2 | 6 (prev 1, NOT down) | 6 (prev 1, NOT down) | 7 (prev 0, NOT down) | 7 (prev 0, NOT down) |
| M3 | 11 slugs · rev med 0 · QA med 1 · max B, D 2+1 · 5 no report | same, B and D 2+1 | 6 slugs · rev 1 · QA 1 · max gate3 3+1 · 4 no report | same, gate3 3+1 |
| M4 | untiered n 54, 0.6 · 22 no result | n 54, 0.6 · 22 | t0 n1 7.0 · t2 n1 0.4, 1 · untiered n1 2.1, 4 | identical |
| M6 | 7 of 60 | 7 of 60 | 30 of 30 | 30 of 30 |
| M7 | 0 | 0 | 0 | 0 |

M2 and M7 read this branch's `doc/memory/` at `8482670`, not `96bebdb`. They still match, so no lesson dated 2026-10-22 or earlier has been added since.

## Reading choices the brief asked about

1. **M3 is sorted into "review" and "QA" by the report file's prefix (`REVIEW-` or `QA-`), not by the run's type.** This matches the spec.
   - SC-AC6's Given lists "reviewer runs editing … `doc/qa/QA-a.md`" and expects `QA 1`. Only the prefix reading gives that result; a run-type reading gives `review 3 · QA 0`, and my mutant "count by run type" turns that test red.
   - The run-type gate is still applied: only `reviewer` / `qa` / `frontend-qa` runs are counted.
   - Side effect, not covered by any criterion: one run that edits both `REVIEW-a.md` and `QA-a.md` counts once in each column, so twice for slug `a`. That is no defect; see Parked.
2. **An exchange's tier comes from the first Jarvis model event that has a Tier line, not from the first model event only.** This matches spec line 58 word for word ("the first Jarvis model event in the exchange whose text … has a line matching").
   - A consequence of the same text: a first reply with `Tier: 3` falls through to a later valid Tier line, because `3` does not match `[012]`. That is the spec's regex, applied as written.
3. **`\Z` instead of the spec's `$` in the report regex.** This is a deviation from the spec text, and it is stricter. In Python, `$` also matches before a final `\n`, so only a path ending `.md\n` is treated differently: the spec's regex would count it as slug `a`, and this code counts it under "wrote no report".
   - No criterion names that input. The `$` mutant passes all 220 tests, and the replay is unchanged.
   - It honours SC-AC6's intent that a newline in the path does not match. Accepted; recorded so that the spec owner can align the text if they wish.
4. **When M2 and M7 cannot be measured, they share one line, `M2, M7: …`.** This matches SC-AC8, which spells out the combined line text for both hostile cases. The line sits in M2's slot, and M7 has no separate line in that case. This is consistent with SC-AC1's order, because the spec itself names the combined line.

## Defects (if FAIL)

None.

## Hostile inputs tried

- `--since 2026-10-22T25:00:00Z`, `--until 2026-10-22T09:00:00.5Z`, `--until ""`, `--until 2026-10-22Ｔ09:00:00Z` → each prints one `agent-time: error: …` line, exit 0, no stderr.
- `--until 2026-10-22T09:00:00z` (lowercase z) and `--until ๒๐๒๖-10-22` (Thai digits) → **accepted**, because `strptime` is case-insensitive for literals and accepts Unicode digits. Both give the same UTC instant, so nothing is misreported. Parked (Low), outside SC-AC5's named cases.
- A model event whose `text` is a list, a brief with `text: null`, and an edit whose `paths` is a string, holds `7` and `None`, or holds two different unprintable slugs → no crash, exit 0. The non-tuple `paths` run counts under "wrote no report".
- The canary in owner, Jarvis and brief `Tier:` / `Files:` lines and in an unprintable slug → 0 occurrences in the output.
- `--memory-dir` pointing at a file → `M2, M7: memory directory not found`.
- Run from `cwd=/` → normal output, so the `correction_rate` import does not depend on the working directory.
- Mutation set run in this review: 16 planted mistakes plus 3 window-parsing mutants.
  - 12 of the 16 went red at once.
  - 2 had syntax errors as first written; rerun, both went red.
  - 1 was equivalent: a tool result before the owner message is outside the exchange span by construction.
  - 1 survived: `$` for `\Z` (see choice 3).
  - All 3 window-parsing mutants went red.

## Parked (outside SC-AC1…SC-AC12 or the threat model)

- **Two different unprintable slugs edited by one run count once.** They are merged under `(unprintable label)` in a set. Two unprintable slugs also count as one slug in "N slugs" and in the medians. No criterion names either case. Low.
- **One run that edits both `REVIEW-a` and `QA-a` counts once in each column** (choice 1). Low.
- **`--since` now accepts a time of day in the time report too,** because `parse_since` is shared. The time report's header still prints the date only (`since 2026-10-21` for `--since 2026-10-21T02:03:54Z`). This is not a byte change to any existing output. Low.
- **Lowercase `z` and Thai digits are accepted** in `--since` / `--until` (above). Low.
- **Grammar:** `1 slugs`. Cosmetic.
- **Two tests cannot fail on a regression of the real code.** `test_marking_every_inbound_line_as_owner_is_caught` and `test_counting_turn_ends_per_line_is_caught` monkeypatch the mistake in, then assert on the mistake's own output. They stay green whatever the real `_is_owner` / `count_turn_ends` do. The red-first claim of SC-AC2 and SC-AC3 rests on the plain tests instead, which my source mutants turned red (above). Low: they are demonstrations, not guards.

## Approval history

- **2026-10-22 — drafted.** Reviewer run `ae675b38f138bc90e`. Based on the spec, the author's uncommitted files overlaid on HEAD `8482670` in a scratch copy, and commands run in this review only.
