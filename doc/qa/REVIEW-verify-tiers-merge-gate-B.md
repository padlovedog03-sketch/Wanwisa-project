# Review: verify tiers — increment B (the handoff tier), delta re-review after QA REWORK (D1)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Author-run: a40a64389abbb86b6
Reviewer-run: a051f3fae766a2582
Date: 2026-10-20

Verdict: PASS

## Verdict: PASS (delta `daf5649..184b3f4`)

QA's D1 (`doc/qa/QA-verify-tiers-merge-gate-B.md`) is closed for every input QA named: empty, truncated and not-XML reports. It is also closed for the other variants probed in this run (a directory named `*.xml`, chmod 000, a broken symlink, NUL bytes, entity amplification). Each of these now gives one `HANDOFF TIER RED` banner, a `failed: unreadable JUnit report …` line, and a `record.json` with `verdict: RED`. The shared-path change turned nothing GREEN on any tier.

One exotic input still crashes the recorder: a JUnit report whose XML declaration names an encoding that expat cannot use. `encoding="bogus-enc"` raises `LookupError`, and `shift_jis`/`euc-jp` raise `ValueError: multi-byte encodings are not supported`. The run prints a traceback and writes no `record.json`, but it fails closed: rc 1 and a single `HANDOFF TIER RED — recorder failed (finalize exit 1)`.

This review first raised it as D2 (rework). It is re-judged here under `.agents/skills/scope-discipline/SKILL.md` rule 5 (owner ruling, commit `be0fa18`) and `doc/memory/stay-on-the-definition.md`:
- pytest never writes such a declaration.
- A runner killed mid-write leaves a truncated or empty file, and those are now RED with a record.
- No agent produces such a declaration by accident or as a shortcut.
- The run never reaches GREEN or OK on it.

It is therefore outside the gate's threat model. It is now P12 under Parked as a proposed LIMIT line, not rework.

This reviewer's earlier PASS at `daf5649` (the section below, kept as history) did not probe malformed JUnit input. QA caught that miss, not this review.

## Delta review — `daf5649..184b3f4` (this run)

### Read from

- `git diff daf5649 184b3f4` in the worktree `.claude/worktrees/agent-a40a64389abbb86b6` (HEAD `184b3f4`, clean). Four files changed: `scripts/verify_record.py` (`junit_counts`: `ET.ParseError`/`OSError` count as one failure and are named in `failing_ids`, never added to `reported`), `scripts/verify-handoff.sh` (finalize is trusted only when exit code, last-line banner and `record.json` agree, else `HANDOFF TIER RED — recorder failed (finalize exit N)`), `tests/hooks/test_verify_handoff.py` (+4 regression cases), `tests/hooks/test_verify_tiers.py` (`test_d10` now plants its crash in the copied recorder).
- Consumers of `junit_counts`: the fast/full `cmd_finalize` (lines 555-715) and `finalize_handoff` (lines 845-950).
- The QA report's D1 row. Not read: the author's conversation.

### Commands run in this review

- `python3 -m pytest tests/hooks/test_verify_handoff.py tests/hooks/test_verify_tiers.py -q -p no:cacheprovider` at `184b3f4` → `335 passed in 79.30s`.
- Red-first: a `git archive daf5649` copy with the two new test files → `4 failed, 331 passed`. The failures are exactly the three `test_regression_a_broken_junit_report_…[empty|not-xml|truncated]` cases and `test_regression_a_recorder_that_exits_1_without_a_verdict_is_red`.
- Hostile JUnit probes on all three tiers. Scripts: `scratchpad/review-B-184b3f4/probes/probe.py`, `probe2.py` and `probe3.py`, built on the test files' own `_repo`/`_full`/`_fast` fixtures. Results are in the table below.
- Mutation checks on a `git archive 184b3f4` copy, listed under "test_d10" and P10.
- `scripts/verify-full.sh` in the worktree → see "Exit gate (184b3f4)".

### Can the shared path turn anything GREEN? (handoff / full / fast)

| Planted next to (or instead of) the stub's good report | handoff | full | fast |
|---|---|---|---|
| Good report + truncated `zz.xml` | rc 1 `RED — ran 3 of 5`, record RED | rc 1 `EXIT GATE RED`, record written | rc 1 `FAST VERIFY RED — 1 test(s) failed` |
| Good report + empty directory `d.xml` | rc 1 RED (`[Errno 21] Is a directory`), record RED | rc 1 RED, record | rc 1 RED |
| Good report moved inside a directory `d.xml/` | rc 1 RED (the directory counts as unreadable), record RED | rc 1 RED, record | not run |
| Only a directory `x.xml`, no readable report | rc 1 `RED — ran 0 of 5`, record RED (not EMPTY, not OK) | rc 1 RED (`0 tests reported`, `reported 0 of 3`) | rc 1 RED |
| Only an empty `x.xml` | rc 1 `RED — ran 0 of 5`, record RED | rc 1 RED | rc 1 RED |
| chmod 000 / broken symlink / NUL bytes / billion-laughs DTD | rc 1 RED, record RED, one banner | not run | not run |
| 200 000-deep nesting, or `<testsuites/>` beside the good report | rc 0 `ran 3 of 5`, record OK | not run | not run |
| `encoding="utf-16"` over ASCII bytes | rc 1 RED, record RED | not run | not run |
| `encoding="bogus-enc"` | rc 1 `HANDOFF TIER RED — recorder failed (finalize exit 1)`, `LookupError` traceback, **no record.json** (`ls` of the run dir) | rc 1 `EXIT GATE RED`, `record: not written`, traceback | rc 1, traceback, **no FAST VERIFY banner** |
| `encoding="shift_jis"` / `"euc-jp"` | same as above with `ValueError: multi-byte encodings are not supported`, no record.json | not run | not run |

Nothing turned GREEN or OK on a broken report. The two rc-0 rows are well-formed XML with no failing cases, so OK is correct there. An unreadable report always adds to both `failed` and `failing_ids`, so the handoff and fast verdicts (`if failures`) and the full verdict (`exited 0 but its JUnit records N failed`, or the step's own non-zero exit) all go RED. Zero readable reports gives RED, not EMPTY, on the handoff tier, because `failures` is tested before `empty`.

### test_d10 (edit outside the handoff files)

The old planted crash was a bad JUnit file, which is now RED with a record by design. The new plant puts `raise RuntimeError('planted crash')` at the top of `cmd_finalize` in the copied recorder. The test asserts the anchor occurs exactly once, so the plant cannot silently miss. It still tests its claim, and two mutations on a copy of `scripts/verify-full.sh` show it can fail:
- `print_record` always prints the path (`if true`) → `1 failed`.
- The no-verdict case is no longer RED (`*) ;;`) → `1 failed`.
- With the original file restored → `1 passed`.

The edit is accepted: the reason is stated in the test and is a direct consequence of the fix.

### Criteria (delta)

| # | Verdict | Evidence (this run) |
|---|---|---|
| B-AC1 to B-AC11 | PASS (unchanged) | The delta touches only the JUnit count and the finalize trust check. 97 handoff tests passed in the 335-pass run. |
| B-AC12 | PASS | Truncated, empty and not-XML reports, and every other accident-class variant probed, now write `record.json` with `verdict: RED`, so D1 is closed. A deliberately written unsupported encoding declaration writes no record but fails closed (RED, exit 1). It is parked as P12 under rule 5. |

### Defects

None open. D1 is closed for every accident-class input. The first draft of this delta review raised D2, which is re-judged as P12 (Parked) under scope-discipline rule 5.

### Exit gate (184b3f4)

`scripts/verify-full.sh` was run in the worktree at `184b3f4`. Results: `OK hooks (136s) 893 passed`, `OK ci-examples 19 passed`, `OK scar-forge`, `OK coordinator 111 passed`, `OK framework` (memory: 0 problems), then `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, exit 0. The hooks count went from 889 to 893, which matches the 4 added regression tests. `git status --short` in the worktree was empty after the run. No committed test covers P12's input. The gate does not cover it.

## Previous review (daf5649) — kept as history

## Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate.md` §Increment 4 (B-AC1 to B-AC12); `doc/architecture/DESIGN-verify-tiers-merge-gate.md` §B; `doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md` (ban scope, D7).
- Change: worktree `.claude/worktrees/agent-a40a64389abbb86b6`, branch `worktree-agent-a40a64389abbb86b6`. Rework diff `eed72b9..daf5649` touches `scripts/verify-handoff.sh` (+8 lines: comment and `unset`) and `tests/hooks/test_verify_handoff.py` (+91 lines: `_run(caller_env=…)` and 10 leak tests). The rest of increment B is unchanged since the previous review of `f532b08..eed72b9`.
- Every place `scripts/verify_record.py` reads the environment (`grep -n "environ\|getenv"`): `VERIFY_RUN_DIR`, `PYTEST_ADDOPTS`, the budgets, `VERIFY_TEST_SIZE_RULES`, `VERIFY_RUNNER_ID`, and `VERIFY_TEST_STEPS`. The last is read only under `args.tier == "full"`.
- Not read: the author's conversation. The handback's claims were re-run here, not relayed.

## Commands run in this review

- `python3 -m pytest tests/hooks/test_verify_handoff.py -q -p no:cacheprovider` (worktree at `daf5649`) → `93 passed in 39.81s`.
- Red before the fix: `git archive eed72b9` copy plus the new test file → `10 failed, 83 passed in 43.23s`. The 10 failures are exactly the `test_leak_*` cases: tier switch, untracked inputs, base ref, the three commands, allow-list, extra bans, test runners and lint.
- `scripts/verify-full.sh` (worktree) → see "Exit gate" below.
- Hostile-environment probes (script `scratchpad/probes/probe.py`). It builds the B-AC1 fixture with the test file's own `_repo`/`_conf_text`, then exports one variable per run. Results are in the table under "Hostile inputs tried".
- A real-pytest probe repo (`scratchpad/realpy`): a selector of `python3 -m pytest … --junitxml`, a collect command of `pytest --collect-only`, and `PYTEST_ADDOPTS` set to options the ban list does not name.

## Exit gate

`scripts/verify-full.sh` was run in the worktree at `daf5649`. Results: `OK hooks (130s) 889 passed`, `OK ci-examples 19 passed`, `OK scar-forge`, `OK coordinator 111 passed`, `OK framework` (memory: 0 problems), then `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, exit 0. INCOMPLETE is this framework repo's normal state, because lint, format and tests are template TODO steps; this change did not cause it. The hooks count went up from 879 to 889, which matches the 10 added leak tests. `git status --short` in the worktree was empty after the run.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| B-AC1 | Selector receives exactly `{a.py, b.py, c.py}`; ends `HANDOFF TIER — ran N of M (selected by machine from the diff against <base>)` | PASS | `test_b1_the_selector_receives_exactly_the_diff` passed (93-pass run). Probe with `VERIFY_TEST_STEPS=nope tests` exported → selector got `["a.py", "b.py", "c.py"]`, `ran 3 of 5 (selected by machine from the diff against base)`. |
| B-AC2 | Paths left out by the agent are still selected and named | PASS | `test_b2_paths_left_out_by_the_agent_are_still_selected_and_named` passed. |
| B-AC3 | A named path adds to the selection and never removes from it | PASS | `test_b3_*` passed. |
| B-AC4 | A declared input that changed forces the full set, with the reason and `ran M of M` | PASS | `test_b4_*` passed (7 cases). |
| B-AC5 | Empty or unset `VERIFY_UNTRACKED_INPUTS` → full set, reason `no untracked inputs declared` | PASS (D1 closed) | Probe: conf leaves it unset, caller exports `VERIFY_UNTRACKED_INPUTS='doc/**'` → rc 0, `HANDOFF TIER — ran 5 of 5 (full collected set — no untracked inputs declared)`. In the previous review this was `ran 3 of 5 (selected …)`. `test_leak_exported_untracked_inputs_still_run_the_full_set` passed here and fails on `eed72b9`. |
| B-AC6 | No conf, or tier not `on` → exact NOT CONFIGURED line, exit 3, nothing run; `--status` → `not opted in` | PASS (D1 closed) | Probe: conf without `VERIFY_HANDOFF_TIER`, caller exports `VERIFY_HANDOFF_TIER=on` → `--status` rc 0 `not opted in`, and a plain run gives rc 3 `HANDOFF TIER NOT CONFIGURED — this project has not opted in; scripts/verify-full.sh before every handoff stays in force`. A conf that writes `VERIFY_HANDOFF_TIER="${VERIFY_HANDOFF_TIER:-off}"` with `on` exported → `not opted in`. `test_leak_an_exported_tier_switch_does_not_opt_in` and the three `test_leak_an_exported_command_does_not_fill_the_conf[...]` cases passed here and fail on `eed72b9`. |
| B-AC7 | 0 cases → `HANDOFF TIER EMPTY — ran 0 of M; nothing was verified`, exit 1 | PASS | `test_b7_*` passed. Real pytest with `PYTEST_ADDOPTS=--co` → `HANDOFF TIER EMPTY — ran 0 of 5; nothing was verified`, rc 1. |
| B-AC8 | stdout never contains `GREEN` or `suite passes` | PASS | `_run` asserts it on all 93 runs, and all 93 passed. |
| B-AC9 | A base that does not resolve → full set, reason `base <ref> not found` | PASS | `test_b9_*` passed. `test_leak_an_exported_base_ref_is_not_the_base` (conf leaves it unset, caller exports `base`) → `ran 5 of 5 (full collected set — base origin/main not found)`. Passed here, fails on `eed72b9`. |
| B-AC10 (RED-FIRST) | A planted regression → `HANDOFF TIER RED — ran N of M`, failing id named, exit 1 | PASS | `test_b10_*` passed. The rework is red-first too: 10 failed on `eed72b9`. |
| B-AC11 | A banned form in `VERIFY_SELECT_CMD` → exit 2 `BANNED:` | PASS | `test_b11_*` passed. An exported `VERIFY_ALLOWED_FILTERS` no longer waives `-k smoke` (`test_leak_an_exported_allow_list_waives_nothing`, rc 2). A `PYTEST_ADDOPTS` of `--lf`, `-x`, `-k foo`, `--deselect …`, `--ignore=tests`, `--maxfail=1`, `--reruns 3`, `-m slow` or `--sw` → rc 2 with `BANNED: … (in PYTEST_ADDOPTS)`. A conf-declared `-k smoke` does not waive `-k smoke` in `PYTEST_ADDOPTS` (rc 2). |
| B-AC12 | Record has `tier: "handoff"` and both tree hashes | PASS | `test_b12_*` passed, including the prune bucket. |

## Hostile inputs tried (this run)

| Exported by the caller | Result | Verdict or selection changed? |
|---|---|---|
| `VERIFY_HANDOFF_TIER=on` (conf unset) | `not opted in` / rc 3 | No (D1 closed) |
| `VERIFY_UNTRACKED_INPUTS='doc/**'` (conf unset) | `ran 5 of 5 (full … no untracked inputs declared)` | No (D1 closed) |
| `VERIFY_TEST_STEPS='nope tests'`, on a selection and on the full set | `ran 3 of 5` / `ran 5 of 5`, rc 0, same as without it | No. It is read only by the full tier's finalize. |
| `PYTEST_ADDOPTS` with each banned form (9 forms) | rc 2 `BANNED: … (in PYTEST_ADDOPTS)` | No pass possible |
| `PYTEST_ADDOPTS` unbanned, real pytest: `-p no:junitxml` | `no JUnit report written by the selector`, `RED — ran ? of 5`, rc 1 | Fails closed |
| `PYTEST_ADDOPTS=--co`, real pytest | `EMPTY — ran 0 of 5`, rc 1 | Fails closed |
| `PYTEST_ADDOPTS=--continue-on-collection-errors`, real pytest | `ran 1 of 5`, rc 0, same as the baseline | No |
| `VERIFY_RUN_DIR=/tmp/evil VERIFY_JUNIT_DIR=/tmp/evil` | Overwritten by the script before sourcing; normal `ran 3 of 5` | No |
| `VERIFY_STEP_BUDGET_S=0`, `VERIFY_TEST_BUDGET_SMALL_S=0`, `VERIFY_TEST_SIZE_RULES='*=large'`, `VERIFY_RUNNER_ID=ci-1` | Normal `ran 3 of 5`, rc 0 | No. The handoff finalize does not read the budgets. |
| `LINT=false` (string) | Not run, rc 0 | No |
| `GIT_DIR=/nonexistent` | rc 3 `not a git work tree` | Fails closed |
| `GIT_CONFIG_COUNT/KEY_0/VALUE_0` setting `core.excludesFile` to a file containing `*.py` | Selector got `["a.py", "b.py"]`, `ran 2 of 5`, rc 0: untracked `c.py` dropped | Yes: see P6 (parked) |
| `BASH_FUNC_unset%%='() { :; }'` with `VERIFY_HANDOFF_TIER=on` | `--status` → `opted in` | Yes: see P7 (parked) |

## Defects

None open. D1 is closed by `daf5649` (evidence in the B-AC5, B-AC6 and B-AC9 rows above).

## Author deviations

The deviations accepted in the previous review stand: the `diff-paths`/`finalize --tier handoff`/prune bucket interface, and the full set on an empty diff or with no common ancestor. The rework's choice to keep the recorder's own environment reads overridable is accepted on the evidence above. None of them changed a verdict or a selection, and `PYTEST_ADDOPTS` is scanned for bans with no allow-list waiver.

## Parked

Outside the B-ACs.

- **P12 (Low, outside the threat model; was D2).** A JUnit report whose XML declaration names an encoding expat cannot use crashes `junit_counts`, because it catches only `ET.ParseError`/`OSError`. Repro: the selector writes `b'<?xml version="1.0" encoding="bogus-enc"?><testsuites/>'` to `$VERIFY_JUNIT_DIR/zz.xml`. Result: rc 1, `HANDOFF TIER RED — recorder failed (finalize exit 1)`, stderr `LookupError: unknown encoding: bogus-enc`, and no `record.json`. `shift_jis`/`euc-jp` give `ValueError: multi-byte encodings are not supported`. It fails closed. Proposed LIMIT line: `LIMIT: a JUnit report declaring an encoding the XML parser cannot use crashes the recorder; the tier still ends RED (exit 1) but writes no record.` An optional one-line hardening is to catch `(ET.ParseError, OSError, LookupError, ValueError)`.
- **P8 (Low, predates the delta).** The fast tier crashes with no `FAST VERIFY` banner on the same `encoding="bogus-enc"` report: rc 1 and a traceback. `verify-fast.sh` `exec`s finalize, so there is no wrapper to catch it. The P12 hardening in `junit_counts` would close this too.
- **P9 (Low, test gap).** No test in `tests/hooks/test_verify_tiers.py` pins the new behaviour of the full and fast tiers on an unreadable report (RED with a record, instead of a crash). This run checked that behaviour only with probes.
- **P10 (Low, test gap).** The wrapper's `[ -f "$RUN_DIR/record.json" ]` condition is untested. Replacing it with `true` on a copy left `tests/hooks/test_verify_handoff.py` at `97 passed`. It is hard to reach, because the recorder writes the record before it prints, but no test would notice if it were removed.
- **P11 (Low, wording).** On the full tier, an unreadable report beside a step that exited 0 is reported as `step tests exited 0 but its JUnit records 1 failed test(s)`. The verdict (RED) is right, but the message misdescribes the cause. The handoff tier names it correctly (`unreadable JUnit report …`).

Earlier items: Not rework under `.agents/skills/scope-discipline/SKILL.md`; they go to the backlog owner.

- **P2 to P5** from the previous review stand unchanged: the label on an empty diff with named paths, the selector's tail line on the `OK select` row, all-skipped cases counted as run under ADR-5, and the design's `verdict`/`full_set_reason` enum lagging the code.
- **P6 (Low).** A git configuration from the caller's environment (`GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n`, here `core.excludesFile`) can hide an untracked file from `ls-files --others --exclude-standard`. That narrows the selection: `ran 2 of 5`, rc 0, `c.py` not run. `_git_env()` strips `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` but not `GIT_CONFIG_*`. The same effect comes from a user's global gitignore, and the design treats ignored files as outside the tree (the tree hash excludes them too), so this is consistent with design §B and is not a B-AC failure. One possible hardening is to drop `GIT_CONFIG_*` and `GIT_CONFIG_PARAMETERS` in `_git_env()`.
- **P7 (Low, declared limit).** An exported bash function named `unset` (`BASH_FUNC_unset%%`) turns the new `unset` line into a no-op, and the D1 leak comes back (`--status` → `opted in`). This takes a deliberately hostile environment, the same class as putting a fake `python3` or `git` on `PATH`. Under `doc/memory/ease-of-use-over-strictness.md` the guards catch accidents, not adversaries. `builtin unset` would close it with one word if the owner wants that.

## Approval history

- **2026-10-20, first review, verdict FAIL (D1).** Reviewer run ac9043cff82e172e6, diff `f532b08..eed72b9`.
- **2026-10-20, re-review after REWORK, verdict PASS.** Diff `eed72b9..daf5649` plus a re-check of all twelve B-ACs, from the files and this run's own commands. The author's conversation was not read.
- **2026-10-20, delta re-review after QA REWORK (D1), verdict PASS.** Diff `daf5649..184b3f4`, from the files and this run's own commands. The author's conversation was not read. The first draft raised D2 as FAIL; it was re-judged as P12 (Parked) under scope-discipline rule 5 (owner ruling `be0fa18`) at the coordinator's request.
