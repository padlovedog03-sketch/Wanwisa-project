# QA Report: Verify tiers — increment J2 (meter reports per size class)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate-am1-size-class.md
Date: 2026-10-20

## Verdict: PASS

All 10 J2 acceptance criteria pass, with executed evidence for each. I found no defect against a J2-AC. Five observations are listed below. None of them blocks.

Provenance: the coordinator's brief says the spec is APPROVED, and the registry key on the spec agrees: `spec-verify-tiers-merge-gate-am1-size-class-2026-10-20`. The brief cites the owner's lean-gates ruling, which says a measuring instrument gets full QA. **The brief does not confirm that a human approved this implementation before QA.** Under AGENTS.md §5 this is tier-1 work: it is inside an approved spec, so engineer → qa may run without a stop in between. I am flagging it, as my role requires. The code under test is commit `3f2877a` on branch `worktree-agent-adb5bfb611d973516`. I did not change any production file: `git status --short` lists only my two files.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| J2-AC1 | `size_class(run-small) == ("small", 5)`. Boundaries 0/1/5/6/10/11 are inclusive. | PASS | `test_run_small_is_small_with_five_files`, `test_class_boundaries_are_inclusive[0..11]`: PASSED. Through the real reader, `test_ten_thousand_edits_to_one_file_through_the_reader_are_small` also passes. |
| J2-AC2 | RED-FIRST: the two planted counting mistakes are caught. | PASS | **QA's own mutation run.** I copied the worktree into the scratchpad and edited the copy's `scripts/agent_time.py`, not the worktree's. Then I ran `test_run_small_is_small_with_five_files` alone. Mistake 1, a per-call counter: `E AssertionError: size class differs: small → medium (8)` / `1 failed`. Mistake 2, `SIZE_TOOL_KINDS = frozenset({"edit", "read"})`: `E AssertionError: size class differs: small → large (11)` / `1 failed`. After the revert: `1 passed`. The engineer's in-process tests (`test_counting_each_edit_call_is_caught`, `test_counting_read_only_files_is_caught`) only show that the assertion message is right. They pass by construction. The run above shows the real test bites. |
| J2-AC3 | A pathless edit makes the run `size unknown`. The run is in no class, but it is in the overall numbers. | PASS | `test_an_edit_with_no_usable_path_makes_the_run_size_unknown[8 shapes]` and `test_size_unknown_runs_are_in_no_class_but_in_the_overall_numbers` (overall `n=4`, `small n=1`): PASSED. Through the real reader, `test_an_edit_whose_path_cannot_be_determined_has_no_path[14 shapes]`: PASSED. |
| J2-AC4 | An unreadable line makes the run `size unknown`, and the output prints `size unknown: k (path missing: a · unreadable lines: b)`. | PASS | `test_an_unreadable_line_makes_the_run_size_unknown` and `size unknown: 3 (path missing: 2 · unreadable lines: 1)`: PASSED. QA added a real-reader case, `test_regression_no_path_reaches_a_size_line_through_the_real_reader`, which prints `size unknown: 2 (path missing: 1 · unreadable lines: 1)`: PASSED. |
| J2-AC5 | Each class line shows its count and median. `large n=0 no median` never prints `0.0`. The overall line is present. | PASS | `test_the_report_gives_each_class_its_count_and_median`: PASSED. It checks the literal `small  n=3  median 15.0 min`, `large  n=0  no median`, `size unknown n=1` and `all engineer runs n=5  mean 18.0 min · median 15.0 min`. |
| J2-AC6 | Per-class verdicts, `acceptance: NOT met (met 1 of 3 classes)`, and the meter exits 0. | PASS | `test_acceptance_is_judged_per_class_and_the_meter_still_exits_0`, `test_a_median_above_its_target_is_not_met` and `test_all_three_classes_met_is_accepted`: PASSED. QA swept every active time from 880 s to 920 s (`test_regression_the_verdict_agrees_with_the_printed_median[880..920]`, 41 cases): every verdict agrees with the printed median. `test_regression_zero_runs_is_never_met_even_with_min_runs_1`: PASSED. |
| J2-AC7 | Probe runs (2 of 6) are excluded from every class, from the overall numbers and from the acceptance line, and are counted. | PASS | `test_probe_runs_are_excluded_and_counted`: PASSED. That test uses the stub reader. QA added a real-reader case with CRLF line endings, `test_regression_a_probe_brief_is_excluded_through_the_real_reader`. QA also added 7 look-alike markers that must not exclude a run: U+2028, a bare CR, a BOM, `> `, backticks, a tab, and `PROBE :`. All PASSED. |
| J2-AC8 | A canary in an edited path and in a read path never appears in the output. | PASS | `test_no_path_reaches_the_output` and `test_no_edited_or_read_path_reaches_the_output`: PASSED. QA added a real-reader case with the canary in `cwd`, in a relative edit, in a pathless edit's input and in an unreadable line. It runs with `--targets`, so the class headers, the unknown reasons and the `acceptance:` line are all printed: PASSED. QA also added `test_regression_a_bad_flag_value_is_not_echoed[4]`: PASSED. |
| J2-AC9 | Adapter ก's reader puts exactly the edited paths on edit events. A pathless Edit gets `()`. A Read gets none. Relative paths are resolved against `cwd`. | PASS | `test_edit_events_carry_exactly_the_edited_paths`, `test_paths_are_normalised_against_the_line_cwd[7]` and `test_an_edit_whose_path_cannot_be_determined_has_no_path[14]`: PASSED. QA checked the NotebookEdit tool's own schema in this session: the path key is `notebook_path`, and it is required, as the reader assumes. The MultiEdit key could not be checked, because that tool is not available in this session. ADAPTERS ก already states that this key is unproven. |
| J2-AC10 | ADAPTERS.md has a "meter size class (R41)" row for each adapter: ก supported, ข unsupported. | PASS | `test_adapter_a_declares_the_size_class_supported` and `test_adapter_b_declares_the_size_class_unsupported`: PASSED. I also read both rows. **Location deviation:** the spec names `tests/framework/test_doc_contracts.py`, but the tests live in `tests/framework/test_agent_time.py`. The engineer gives the brief's file limit as the reason. The behaviour is checked either way. |

## Test Run

The exit gate, `scripts/verify-full.sh`, was run after my tests and this report were written. Full output:

```
$ scripts/verify-full.sh; echo "exit $?"
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             325 passed in 10.92s
  OK   ci-examples       19 passed in 0.61s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       111 passed in 1.57s
  OK   framework         memory: 0 problem(s) in /Users/<user>/<repo>/.claude/worktrees/agent-adb5bfb611d973516/doc/memory
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.
Fill those steps in scripts/verify-full.sh before treating this output as a gate.
exit 0
```

The gate says INCOMPLETE, not GREEN. That is because three template steps are unconfigured: lint, format and tests. This is a pre-existing project state, not a J2 defect. Every configured step passed. The `framework` step prints only its last line, so I also ran the J2 files and the J-era pins directly:

```
$ python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py tests/framework/test_doc_contracts.py tests/hooks/test_regression_agent_time_reader.py tests/hooks/test_regression_agent_time_size_class.py -q -rs
=========================== short test summary info ============================
SKIPPED [1] tests/framework/test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now — see the test above
273 passed, 1 skipped in 5.28s
```

The one skip is `tests/framework/test_doc_contracts.py:193`: "agent_time.REWORK_CAUSES is the source now — see the test above". It predates J2 and is not a J2 test.

**The J-era QA regression pins still pass.** `tests/hooks/test_regression_agent_time_reader.py` gives `31 passed` when run alone. It is also part of the `hooks` step and of the direct run above.

**QA's new tests bite.** File: `tests/hooks/test_regression_agent_time_size_class.py` (55 cases). Each mutation below was applied to a scratchpad copy of `scripts/agent_time.py`, never to the worktree:

| Mutation | Result |
|---|---|
| Probe marker unanchored (`PROBE\s*:` anywhere) | 7 failed (every look-alike case) |
| Probe runs not excluded | 1 failed (`…excluded_through_the_real_reader`) |
| Unknown-reason block prints the run's paths | 1 failed (`…no_path_reaches_a_size_line…`; canary printed) |
| Verdict on the unrounded median | 2 failed (`[901]`, `[902]`: printed 15.0, verdict NOT met) |
| A class with 0 runs judged instead of "not enough runs" | 2 failed |
| `--targets` / `--min-runs` error echoes the value | 4 failed |
| Reverted | `55 passed` |

## Defects (if FAIL)

None against a J2-AC.

## Engineer choices judged

| Choice | Judgement |
|---|---|
| A symlink or case variant of one file counts as 2 files, and this is stated on the `size limits:` line. | **Accept.** The limit is stated in the output and in ADAPTERS ก. QA measured it independently: 0 of 436 pilot engineer runs edited two paths that differ only in case. Folding case would merge distinct files on a case-sensitive file system. |
| A run with both a pathless edit and an unreadable line is counted under `path missing` only. | **Accept.** Each run gets exactly one reason, so `a + b = k` always holds. Tested. |
| Medians are compared to targets at 1 decimal. | **Accept.** This gives at most about 3 s of leeway. The 41-point sweep shows the verdict never contradicts the printed number. |
| Probe exclusion applies to the size section only. | **Accept.** PRD R23 says "excluded from the M10 per-size measurement". The spec's "everything" sits in the size-class table. J's time report is not M10. |
| `--targets` must name all three classes. | **Accept.** F-AM1 judges all three classes. A missing class is a usage error (one line, exit 0), never a silent pass. |

## Edge Cases Probed

- **Path shapes that could misclass a run:**
  - `.`, `..`, a trailing `/` and an inner `//` all fold to one file. So do relative and absolute forms of the same file under one `cwd`.
  - A relative path is `size unknown` when `cwd` is missing, relative, empty or not a string. It never guesses.
  - 10,000 edits to one file is still small.
  - A **leading `//`** (`/r/a.py` vs `//r/a.py`) counts as **2 files**. POSIX `normpath` keeps exactly two leading slashes, and the `size limits:` line names only `.` and `..`. Pilot data has 0 such runs. → Observation O2.
- **Leak surfaces:**
  - Class headers print only the two fixed engineer type names.
  - The unknown reasons are integers.
  - The `acceptance:` line and the `size limits:` line are constants.
  - A target is printed with `{:g}` from a float that was already validated.
  - A canary in `--targets` or `--min-runs` is not echoed.
  - A canary in `cwd`, in a relative path, in pathless input or in an unreadable line is not printed.
- **`--targets` / `--min-runs` edges:**
  - Rejected with one line and exit 0: `nan`, `inf`, `0`, a negative value, a duplicate, a missing class, an unknown class, a trailing comma, an empty value, and `3.0` for min-runs.
  - Accepted: `1_5` (Python float syntax), surrounding spaces, and `--min-runs 99999999999999999999`, which makes every class `not enough runs`.
  - With `--targets` and **no** engineer runs, the output is `size classes: no engineer runs in the window`, with no acceptance line. → Observation O3.
- **`PROBE:` spoofing:**
  - A marker counts only at the start of a line after `\n`. CRLF works.
  - U+2028, a bare CR, a BOM, a `> ` quote, backticks, a tab and `PROBE :` do not count.
  - A later inbound `PROBE:` does not count.
  - On 436 real pilot engineer runs, no first inbound message contains a `<system-reminder>`. So injected project context cannot carry a stray `PROBE:` into the brief that is checked. 0 runs are flagged as probes.
- **Real data** (`--dir ~/.claude/projects/<repo>` for the pilot, no `--since`, 436 engineer runs): `size unknown: 0 (path missing: 0 · unreadable lines: 0)` for both engineer types. The output carries no path or user name.

## Observations (non-blocking)

- **O1 — the shell-write count is a pattern estimate, but the line reads as an exact count.**
  - The limit itself is stated honestly in both places, as the owner's ruling requires:
    - `size limits: … files written by shell commands are not counted`;
    - ADAPTERS ก: "ไฟล์ที่เขียนด้วยคำสั่งเชลล์ไม่ถูกนับ".
  - The count line `runs with shell file writes (not counted in size): <k>` gives no sign that `k` is approximate.
  - **False positives:**
    - the `>` that closes `<email>` in every `Co-Authored-By:` commit message;
    - `<placeholder>` text;
    - `awk '$2 > 5'`;
    - `python3 -c "print(3 > 2)"`.
  - **Misses:** `sed -Ei`, `sed -e … -i`, `sed --in-place`, `tee`, `cp`, `mv`, `perl -pi`, and Python `open(…,'w')`.
  - **Measured on the pilot:** 432 of 436 runs are flagged as shipped, and 429 of 436 once commit messages and `<…>` tokens are stripped. Run-level misses are at most 2. So the error is small here, but only because almost every run really writes with `cat >`.
  - **Suggestion:** add "(by pattern)" to the line, and mention it in the ADAPTERS ก row.
- **O2 — a leading `//` counts as a second file.** It is not on the `size limits:` line. 0 occurrences on the pilot.
- **O3 — `--targets` with zero engineer runs (or all of them probes) prints no `acceptance:` line.** It is not wrongly "met", but an explicit `acceptance: NOT met (no engineer runs)` would read more safely when pasted into the trial report.
- **O4 — the spec's file plan differs from what was delivered, and this matters for increment F:**
  - There is no `tests/framework/fixtures/agent_time/size_runs.json`; the fixture is built in the test file.
  - The J2-AC10 test is in `test_agent_time.py`.
  - **`.agents/skills/coordinator-discipline/SKILL.md` did not gain the optional `PROBE:` brief line** that the spec's affected-files table lists. That line is outside this slice's file list and no J2-AC covers it, but F-AM3 depends on it. It must land before the trial.
  - Separately, `probe runs excluded:` counts engineer runs only. If a trial probe is dispatched to a non-engineer agent, F-AM3's equality check would mismatch.
- **O5 — the engineer's pilot replication is not reproduced.** The claim was small 72/21.2, medium 32/34.7, large 60/72.8. I ran with no `--since` and got ai-engineer small 112/26.4, medium 62/36.9 and large 83/76.2. That is a different window, so it does not contradict the claim. I did not have the engineer's window or flags.

## Approval history

- **2026-10-20 — drafted.** qa, from the approved amendment spec, commit `3f2877a`, the full gate run, a direct pytest run, scratch-copy mutation runs, and real pilot transcripts. All numbers are counts only.
