# QA Report: verify tiers, increment A+C (no fake green, a measurable `verify-full`)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md (AC-AC1 to AC-AC19, increment A+C); doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md (am2: AC-AC8 replaced, AC-AC20 to AC-AC24 new); doc/architecture/DESIGN-verify-tiers-merge-gate.md §AC; branch worktree-agent-ad1e27705199bd4e4 at commits 46c5930 and cb76109; re-test 2 on worktree agent-a0bb7774512557e28 at 0fd71b6 plus the uncommitted AC-AC20 fix
Date: 2026-10-22

## Verdict: PASS

**Re-test 2 (am2, 2026-10-22): PASS.** 24 PASS, 0 FAIL (AC-AC8 counted once, with its four clauses 8a to 8d each passing). AC-AC8 and AC-AC15 pass on the re-test 1 repros. AC-AC20 passes in the full, fast and handoff tiers, and was shown red against `HEAD` first. See `## Re-test 2 (am2)` below. The earlier text is kept as it was.

**Re-test 1 (after `1785567`): still FAIL.** 17 PASS, 2 FAIL (AC-AC8, AC-AC15). See `## Re-test 1` below. The round-1 text that follows is kept as it was.

Four of nineteen criteria fail (AC-AC5, AC-AC8, AC-AC17, AC-AC19). On top of those, three verified routes still print `EXIT GATE GREEN` over work that was not done:
- a test failure masked by the step's exit code;
- a conf that stops parsing partway through;
- two steps that share a test label.

**Provenance note.** The brief cites the owner's lean-gates ruling for full QA. It does not confirm that a human approved this implementation. The spec is `Approved`, so the slice qualifies as tier 1 (AGENTS.md §5), and QA may run before that approval. This is flagged, not blocking.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AC-AC1 | Timed rows, record fields, `record:` line | PASS | `test_ac1_every_step_row_is_timed_and_a_record_is_written`. The real gate run below prints `(33s)`-style rows and `record: .verify/runs/…/record.json`. That record holds `runner`, `tree.before/after/head` and per-step `seconds`. |
| AC-AC2 | JUnit counts and failing ids in the record | PASS | `test_ac2_junit_counts_and_failing_ids_reach_the_record` |
| AC-AC3 | Dropped test → RED `reported 4 of 5 collected`; revert → GREEN | PASS | `test_ac3_a_dropped_test_turns_the_gate_red_and_the_revert_turns_it_green` |
| AC-AC4 | Shards are summed | PASS | `test_ac4_shards_in_one_step_directory_are_summed` |
| AC-AC5 | A listed step with 0 cases or no JUnit → RED | **FAIL** | D2: `test_regression_a_conf_that_stops_parsing_cannot_drop_the_test_step_check`. The conf lists `tests`, the step writes no JUnit, and the run prints `EXIT GATE GREEN` with exit 0. D3: `test_regression_two_steps_sharing_a_test_label_are_not_double_counted`. The second `tests` step writes nothing, and the run prints `counts: reported 6 of 6 collected` and `EXIT GATE GREEN`, although only 3 cases ran. |
| AC-AC6 | Fast tier `ran N of M` / `ran ? of ? (counts not configured)` | PASS | `test_ac6_*` (2). Deviation 3 is accepted; see the notes. |
| AC-AC7 | Fast tier with 0 cases → `FAST VERIFY EMPTY`, exit 1 | PASS | `test_ac7_a_fast_run_of_zero_tests_is_empty_and_exits_1` |
| AC-AC8 | Every banned form exits 2 before any step runs; only the interpreter's `-m` is exempt | **FAIL** | D4: `test_regression_m_after_a_path_named_python_is_still_a_filter`. `pytest tests/python_api -m "not slow"` is not refused, and the next step prints `STEP-RAN`. `test_regression_m_after_a_path_named_python_is_refused_at_runtime` shows the same at runtime: fast ends `FAST VERIFY OK`, exit 0. |
| AC-AC9 | A stale JUnit from an earlier run is not counted | PASS | `test_ac9_a_report_left_by_an_earlier_run_is_not_counted`. JUnit written outside the run dir is RED too: `test_regression_junit_written_outside_the_run_dir_is_not_counted` (passes). |
| AC-AC10 | Tree hashed as-is; an edit mid-run is RED with a conf and informational without one | PASS | `test_ac10_*` (3), `test_the_tree_is_hashed_when_verify_is_git_ignored_too` |
| AC-AC11 | Budgets warn and list the slowest; the verdict is unchanged | PASS | `test_ac11_*`, `test_a_size_rule_raises_the_budget_for_matching_tests` |
| AC-AC12 | Example conf states 1/10/60 and documents size rules | PASS | `test_ac12_the_example_conf_states_the_size_class_budgets`. Deviation 2 is accepted: `tests/framework/test_doc_contracts.py` does not exist on this branch. |
| AC-AC13 | Existing verify and CI tests pass; only copy helpers change; banners unchanged | PASS | The gate run below shows 291 pre-existing hooks tests passing, and ci-examples passing with 19. `git diff 9a97bc6 -- tests/ci tests/hooks/test_verify_scripts.py` removes 0 lines; the changes are additions only. |
| AC-AC14 | Counts not configured → GREEN kept plus the `counts: not configured` line | PASS | `test_ac14_unconfigured_counts_keep_green_and_say_so`. The merge-gate half (D-AC2) belongs to increment D and is not testable yet. |
| AC-AC15 | A project as filled in today, with no conf, stays GREEN | PASS as written | `test_ac15_a_project_as_filled_in_today_stays_green` uses `echo` stubs. A realistic step does not stay GREEN: see D6. |
| AC-AC16 | A declared filter runs and is printed and recorded | PASS | `test_ac16_*` (2) |
| AC-AC17 | Undeclared `-m "not slow"` → exit 2 | **FAIL** | D4: the same configured case as AC-AC8. `-m "not slow"` after `tests/python_api` is not refused. |
| AC-AC18 | An allow-list entry without a reason → exit 2 | PASS | `test_ac18_*` (parametrised) |
| AC-AC19 | Hard bans are never allow-listable; runtime filters are still refused | **FAIL** | Hard bans: `test_ac19_*` pass. The runtime clause fails through D4: `verify-fast.sh tests/python_api -m "not slow"` exits 0. `python3 scripts/verify_record.py check-banned --runtime=tests/python_api --runtime=-m --runtime="not slow"` gives rc=0. |

Count: 15 PASS, 4 FAIL.

## Test Run

The exit gate is `scripts/verify-full.sh`, run in the worktree after adding `tests/hooks/test_regression_verify_tiers_qa.py`. Its output follows in full; the hooks step prints its own last 30 lines.

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (145s) (exit 1)
E        +  where 0 = CompletedProcess(args=['bash', '/private/var/folders/r2/73832r291lbbyj71vk7774cc0000gp/T/pytest-of-<user>/pytes...nSTEP-RAN tests/python_api -m not slow\nFAST VERIFY OK — partial run: ran ? of ? (counts not configured)\n', stderr='').returncode

tests/hooks/test_regression_verify_tiers_qa.py:88: AssertionError
________ test_regression_an_empty_step_list_is_red_not_vacuously_green _________

tmp_path = PosixPath('/private/var/folders/r2/73832r291lbbyj71vk7774cc0000gp/T/pytest-of-<user>/pytest-746/test_regression_an_empty_step_0')

    def test_regression_an_empty_step_list_is_red_not_vacuously_green(tmp_path: Path) -> None:
        """D5. `STEPS=()` runs nothing. bash 3.2 dies on an unbound variable with no
        banner; bash >= 4.4 reaches finalize, which returns VERDICT=GREEN."""
        probe = _full(tmp_path, "STEPS=()\n")
    
        result = _run(probe)
    
        assert result.returncode == 1, result.stdout + result.stderr
>       assert "EXIT GATE RED" in result.stdout, result.stdout + result.stderr
E       AssertionError: /private/var/folders/r2/73832r291lbbyj71vk7774cc0000gp/T/pytest-of-<user>/pytest-746/test_regression_an_empty_step_0/scripts/verify-full.sh: line 71: STEPS[@]: unbound variable
E         
E       assert 'EXIT GATE RED' in ''
E        +  where '' = CompletedProcess(args=['bash', '/private/var/folders/r2/73832r291lbbyj71vk7774cc0000gp/T/pytest-of-<user>/pytes...<user>/pytest-746/test_regression_an_empty_step_0/scripts/verify-full.sh: line 71: STEPS[@]: unbound variable\n').stdout

tests/hooks/test_regression_verify_tiers_qa.py:101: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_test_step_failure_masked_by_its_exit_code_is_red
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_conf_that_stops_parsing_cannot_drop_the_test_step_check
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_two_steps_sharing_a_test_label_are_not_double_counted
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_m_after_a_path_named_python_is_still_a_filter
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_m_after_a_path_named_python_is_refused_at_runtime
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_an_empty_step_list_is_red_not_vacuously_green
6 failed, 292 passed in 145.10s (0:02:25)
  OK   ci-examples       (4s) 19 passed in 3.41s
  OK   scar-forge        (10s) LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       (2s) 28 passed in 0.81s
  OK   framework         (12s) memory: 0 problem(s) in /Users/<user>/Desktop/<repo>/.claude/worktrees/agent-ad1e27705199bd4e4/doc/memory
counts: not configured — executed == collected NOT checked
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
record: .verify/runs/20261020T083422Z-46168/record.json
exit=1
```

After this run, the D2 and D3 tests each gained an `EXIT GATE RED` assertion. A re-run of that file gave the same result: `6 failed, 1 passed in 11.62s`.

**The RED is expected.** It comes from the six QA regression tests, each pinning one defect below. The other 292 tests pass: the 291 pre-existing hooks tests plus the one QA control.

**Before QA added any test**, the same gate on the engineer's tree ended `EXIT GATE INCOMPLETE` with exit 0. Its rows were hooks `(33s) 291 passed in 32.27s`, ci-examples 19 passed, and coordinator 28 passed. INCOMPLETE is correct for the framework repo, whose lint/format/tests are placeholders.

## Defects

Ordered by severity. Each defect has exactly one rework cause.

| ID | Severity | Rework cause | Description | Where | Suggested owner |
|---|---|---|---|---|---|
| D1 | High | spec-defect | **A failing test with a masked exit code is GREEN.** Take the step `stub_junit.py 3 1 0` followed by `or true`, with collected 4. It prints `counts: reported 4 of 4 collected` and `EXIT GATE GREEN`, exit 0, while `record.failures == ["…::test_fail_0"]` and `red == []`. Design §AC.2 lists "new failures → RED", and with no baseline every failure is new. The verdict looks only at step exit codes and `red`, and JUnit failures never reach `red`. This breaks the spec's invariant: "nothing prints GREEN unless …". The only ACs that turn a JUnit failure RED are in increment E (E-AC2), so A+C has no AC for it. That makes the cause `spec-defect`, even though the A+C pseudocode in design §AC.2 already lists the rule. The fake GREEN exists today, so the fix belongs in A+C and should not wait for E. Repro: `test_regression_a_test_step_failure_masked_by_its_exit_code_is_red`. | `scripts/verify_record.py:426-429` (the verdict ignores `failures`) | ai-engineer |
| D2 | High | missed-ac | **A conf that stops parsing silently drops `VERIFY_TEST_STEPS`.** Take a conf whose first line sets STEPS to one step, `tests` running `true`, then a syntax error, then `VERIFY_TEST_STEPS="tests"`. Bash prints the error on stderr, keeps the STEPS it already read, and the gate prints `EXIT GATE GREEN`, exit 0. Neither tier checks the status of `. scripts/verify.conf`. This fails AC-AC5. Repro: `test_regression_a_conf_that_stops_parsing_cannot_drop_the_test_step_check`. | `scripts/verify-full.sh:55-58`, `scripts/verify-fast.sh:29` | ai-engineer |
| D3 | High | missed-ac | **Two steps with the same test label are double-counted.** Both steps write to `junit/<label>`, and each step's count reads the whole shared directory. With 3 cases run, collected 6 and the second step writing nothing, the gate prints `counts: reported 6 of 6 collected` and `EXIT GATE GREEN`. This fails AC-AC5 (a listed step wrote no JUnit) and the honesty of AC-AC3. Fix: refuse duplicate labels, or give each step its own directory. Repro: `test_regression_two_steps_sharing_a_test_label_are_not_double_counted`. | `scripts/verify-full.sh:113-116`, `scripts/verify_record.py:346-356` | ai-engineer |
| D4 | Medium | missed-ac | **The interpreter exemption for `-m` keys on the basename of any previous token.** `pytest tests/python_api -m "not slow"` is waived, and so is `pytest tests/python -m slow`, because the basename starts with `python`. The same happens at runtime: `verify-fast.sh tests/python_api -m "not slow"` gives `FAST VERIFY OK`. A path is not a program, and the exemption must apply only when the previous token *is* the interpreter. This fails AC-AC8, AC-AC17 and AC-AC19 (runtime clause). Repro: `test_regression_m_after_a_path_named_python_is_still_a_filter`, `…_is_refused_at_runtime`. | `scripts/verify_record.py:112-114` | ai-engineer |
| D5 | Medium | test-gap | **`STEPS=()` in a conf has no honest outcome.** On bash 3.2 (this machine) the gate dies on `STEPS[@]: unbound variable`, exit 1, with no banner and no record. On bash 4.4 and later the loop runs nothing. The recorder's `finalize` over an empty `steps.tsv` returns `VERDICT=GREEN`; I measured this directly: `python3 scripts/verify_record.py finalize --tier full --run-dir <empty> --conf-present` printed `VERDICT=GREEN`, rc=0. A vacuous GREEN is therefore INFERRED for bash ≥4.4 (see Could not reach). Repro: `test_regression_an_empty_step_list_is_red_not_vacuously_green`. | `scripts/verify-full.sh:71,95`, `scripts/verify_record.py:426-429` | ai-engineer |
| D6 | Medium | spec-defect | **The ban list is too broad for realistic stacks, and R12 breaks on upgrade.** Bans match whole tokens in *every* program of a step, even with no conf. Each command below exits 2 on a project that has no `scripts/verify.conf`. *Owner ruling needed.* | design §AC.3 (implemented literally in `scripts/verify_record.py:88-121`) | ba-sa |
| D7 | Medium | spec-defect | **Ban bypasses the whole-token design cannot see.** These forms are not refused (`check-banned` rc=0): clustered or attached short options (`pytest -xq`, `-qx`, `-qk smoke`, `-m"not slow"`, `-mslow`); `PYTEST_ADDOPTS=-x pytest`; `bash -c "pytest -x"`; `eval "pytest --lf"`; `pytest $FLAGS`; `--sw`/`--stepwise`; `--ignore=…`. The count check catches the filtering forms only when both `VERIFY_COLLECT_CMD` and `VERIFY_TEST_STEPS` are set. `VERIFY_COLLECT_CMD` itself is never ban-scanned, by design. The design calls the gate "tamper-evident, not tamper-proof". Clustered short options and `--sw` are ordinary spellings, though, not tampering. | design §AC.3 | ba-sa |
| D8 | Low | spec-defect | **`runner.id = local:<hostname>` can carry a person's name.** The design mandates it (§AC.1). The spec's personal-data paragraph says records never carry user identifiers (AGENTS.md §8). Default macOS hostnames are `<First-name>s-MacBook-…`; this machine's is `<hostname>`. The spec contradicts itself, so the owner must rule. | design §AC.1 vs spec "Personal data" | ba-sa |
| D9 | Low | spec-defect | **The spec contradicts itself on fast-tier counts without a collect command.** AC-AC6 says `ran ? of ?`, and the Functional Behavior table says `ran N of ?`. The implementation follows the table (Deviation 3). Related: in fast, a *failing* `VERIFY_COLLECT_CMD` also ends `(counts not configured)`, which is misleading. | spec AC-AC6 vs Functional Behavior table | ba-sa |
| D10 | Low | test-gap | **The `record:` path dangles when the recorder crashes.** With malformed JUnit XML the gate is correctly RED, prints `recorder failed — no verdict`, and then prints `record: …/record.json`, but no `record.json` was written. | `scripts/verify-full.sh:149` | ai-engineer |
| D11 | Low | spec-defect | **Fast and full runs share one 20-slot prune.** Twenty fast runs evict the latest full record, so a `record:` path pasted into a handoff can vanish within a day. This matches design §AC.2 literally. Increment D's merge gate reads records, so the owner may want separate slots. | `scripts/verify_record.py:325-329` | ba-sa |

## Defect details

**D6 detail: commands each exit 2 with no conf.**

| Command | `BANNED:` line printed |
|---|---|
| `coverage run -m pytest` | `BANNED: -m pytest — undeclared filter` |
| `python3 -u -m pytest` and `python -W error -m pytest` | the previous token is not the interpreter |
| `mypy -m pkg` | refused |
| `make -k test` (keep-going, the opposite of `-x`) | refused |
| `sort -k 2` in a pipeline | refused; registry-count gates are the kind the STEPS comment invites |
| `git commit -m msg` | refused |
| `tar -x -f a.tar` | refused |

- **Measured.** A copy of `verify-full.sh` with no conf, real-looking steps, and `tests|coverage run -m pytest -q` exits 2.
- **Why the escape hatch fails.** `tar -x` is a hard ban, so no allow-list entry can ever release it. Declaring `-m pytest` as a "filter" would be false. Either fix needs a conf, which also switches on the tree-changed check.
- **AC-AC15 as written passes**, because its stubs are `echo`.

## Engineer's claims and choices — judgement

- **Deviation 1 (an undeclared `--deselect` is banned): ACCEPT.** ADR-14's `ALLOWLISTABLE` includes `--deselect`. The Q4 ruling says "Any undeclared filter … still exits 2."
- **Deviation 2 (the AC-AC12 test is in `test_verify_tiers.py`): ACCEPT.** `tests/framework/test_doc_contracts.py` is not on this branch. When it lands from the meter work (it is uncommitted in the main tree), check for a duplicate size-budget assertion.
- **Deviation 3 (`ran N of ?`): ACCEPT.** It matches the Functional Behavior table and never claims more than it ran. The spec inconsistency is logged as D9.
- **Index path from `git rev-parse --git-path index`: CONFIRMED.** In this worktree it resolves to `.git/worktrees/agent-ad1e27705199bd4e4/index`, and the gate's record shows `tree.before == tree.after` with `dirty: false`.
- **`.verify` is dropped from the temp index: CONFIRMED.** `test_the_tree_is_hashed_when_verify_is_git_ignored_too` and `_init_repo`, with no `.gitignore`, both pass.
- **`-x`/`-k`/`-m` banned in every program: over-broad.** It breaks R12 for realistic stacks (D6).
- **`runner.id` hostname: a spec-internal conflict, not an implementation defect.** Logged as D8.
- **Shared 20-slot prune:** logged as D11.
- **Hooks-step time: measured differently.** I did not measure 35 s. The hooks suite without `test_verify_tiers.py` took 11.66 s (176 passed). The verify-tier files alone took 40.92 s (148 passed). The full hooks step took 33 s (291 passed) on the engineer's tree. My later run took 145 s, under machine load from other worktrees, so it is not a clean figure.
- **The `verify-fast.sh` merge with main's uncommitted meter block: CONFIRMED.**
  - `git merge-file -p ours base theirs` gave 0 conflicts. The base is `9a97bc6`, identical to main HEAD for this file.
  - `bash -n merged.sh` passes.
  - Both verify-tier test files pass against the merged file in a scratch copy: 148 passed.
  - **New:** the branch as a whole conflicts with main HEAD `e857a87` on `.gitignore` (`git merge-tree` rc=1). Main added `.claude/worktrees/` and this branch added `.verify/`. The resolution is trivial: keep both lines.

## Edge Cases Probed

- A step that runs 0 tests and exits 0, with the label listed → RED `0 tests reported` / `no JUnit report written` (AC-AC5 tests). Unlisted with no conf → GREEN, by R12 design.
- An empty step command (`"tests|"`) with no conf → `OK` and GREEN. This is pre-existing behaviour kept by R12; the `TODO` detector matches only `echo TODO:`. It is an observation for the owner, not filed.
- A conf that overrides STEPS to `true` with no `VERIFY_TEST_STEPS` → GREEN plus `counts: not configured — executed == collected NOT checked`. That is honest per spec; no defect.
- A stale JUnit in an older run dir → not counted (AC-AC9). JUnit written outside the run dir → RED (QA control test, passes).
- A step that edits a tracked file → RED with a conf, informational without one (AC-AC10).
- Every test skipped → GREEN with counts matched. §AC.4 counts skipped cases as reported by design; no defect.
- Malformed JUnit XML → RED (`recorder failed`), with the dangling record path in D10.
- Bans hidden by quoting: `pytest "-x"` and `pytest '--lf'` → refused. `=` forms: `--maxfail=1`, `--exitfirst=1`, `--deselect=a::b`, `-k=a` → refused. Env vars, `eval`, `bash -c`, `$VAR` → not refused (D7).
- bash 3.2 with `set -u` and a partial conf: unset `VERIFY_*` keys are fine. `STEPS=()` crashes (D5). A conf syntax error gives a fake GREEN (D2).
- AC-AC15 backward compatibility: the stubbed shape passes, and a realistic `coverage run -m pytest` refuses (D6).
- **Regression tests added:** `tests/hooks/test_regression_verify_tiers_qa.py`.
  - 7 tests: 6 red against the current code (D1 to D5, with D4 twice) and 1 passing control.
  - Each red test was checked to fail on its own defect's assertion: the D4 tests fail on `returncode` 1/0 against 2 with `STEP-RAN` printed, and D5 fails on the missing `EXIT GATE RED`. None fails on an unrelated error.

## Re-test 1

Tree under test: branch `worktree-agent-ad1e27705199bd4e4` at `f441d8d` (fix `1785567`, QA pins `50e9777`, redaction `f441d8d`). The criteria are AC-AC1 to AC-AC19, as amended by the coordinator's rulings on D6 to D11:
- Bans apply to test-runner argv only (`VERIFY_TEST_RUNNERS`).
- Clustered, attached, env and collect-command forms are caught. `eval` and `sh -c` print a `limit:` line.
- `runner.id` is `local:<12 hex>`.
- Fast and full runs are pruned separately.
- `collect failed (exit n)` is reported.
- Accepted deviations: duplicate test labels give RED with exit 1, and `--ignore`/`--ignore-glob` can be declared.

**Provenance.** The brief cites the owner's lean-gates ruling, under which gate code gets full QA. It does not say that a human approved this rework. The spec is `Approved`, so this is tier 1 and QA may run first. This is flagged, not blocking.

### Verdict: FAIL

The six round-1 pins are green and every round-1 fake-green route is closed. The rework opened new holes, though:
- **Regressions in the scanner.** Banned forms that `cb76109` refused now pass in real test-runner spellings: `python3 -mpytest --reruns 2`, `bazel test … --cache_test_results=yes` and `cargo nextest run --retries 2`. That fails AC-AC8.
- **Over-refusal.** The new short-option cluster walk reads go's single-dash long flags as pytest clusters. A go project with no conf and the line `go test -timeout 5m ./...` now exits 2, which fails AC-AC15 (R12).

Count: 17 PASS, 2 FAIL (AC-AC8, AC-AC15).

### Criteria results (re-test 1)

| # | Verdict | Change since round 1 | Evidence |
|---|---|---|---|
| AC-AC1 | PASS | — | `test_ac1_*`. The gate run below prints `(45s)`-style rows and `record: .verify/runs/…/record.json`. A probe record holds `runner: {"id": "local:<12 hex>", "kind": "local"}`; the id equals `sha256(hostname)[:12]` and the hostname is not in the record (D8 ruling). |
| AC-AC2 | PASS | — | `test_ac2_*` |
| AC-AC3 | PASS | — | `test_ac3_*` |
| AC-AC4 | PASS | — | `test_ac4_*` |
| AC-AC5 | PASS | was FAIL | D2: `test_regression_a_conf_that_stops_parsing_…` passes. A probe gives `EXIT GATE RED — scripts/verify.conf failed to load (exit 1); no step was run`. D3: `test_regression_two_steps_sharing_a_test_label_…` passes. A probe gives `EXIT GATE RED — duplicate test step label: tests; give each test step its own label` with exit 1 (accepted deviation 1). |
| AC-AC6 | PASS | — | `test_ac6_*`. With D9 fixed, a fast probe whose collect command exits 3 ends `FAST VERIFY OK — partial run: ran 3 of ? — collect failed (exit 3)`. |
| AC-AC7 | PASS | — | `test_ac7_*` |
| AC-AC8 | **FAIL** | still FAIL, new cause | D4 is fixed: both D4 pins pass. New: D13 and D14. Banned forms in a configured test-runner command are not refused: `python3 -mpytest --reruns 2`, `python3 -mpytest --lf`, `bazel test //... --cache_test_results=yes` and `cargo nextest run --retries 2` each give `check-banned` rc=0 with no `BANNED:` line. `cb76109` refused all four. Pins: `test_regression_an_attached_interpreter_m_still_finds_the_runner[*]` and `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[*]`. Over-refusal (D15) also contradicts the amended scope: `make -C tools/jest -k` is refused. |
| AC-AC9 | PASS | — | `test_ac9_*` and the round-1 control (passes) |
| AC-AC10 | PASS | — | `test_ac10_*` (3) |
| AC-AC11 | PASS | — | `test_ac11_*` |
| AC-AC12 | PASS | — | `test_ac12_*`. Deviation 2 stands: `tests/framework/test_doc_contracts.py` is still absent on this branch. |
| AC-AC13 | PASS | — | The gate run below: ci-examples `19 passed`, and the pre-existing hooks tests are inside `344 passed` on the engineer's tree. |
| AC-AC14 | PASS | — | `test_ac14_*` |
| AC-AC15 | **FAIL** | was "PASS as written" | D12, see below. Round 1 kept this at "PASS as written" because the design itself mandated scanning every program; that was round-1 D6, a spec-defect. The D6 ruling has since narrowed the bans to runner argv, precisely so that realistic stacks stay GREEN with no conf. Under the amended criterion, a real `go test -timeout 5m ./...` line with no conf must not be refused. It is: exit 2, `BANNED: -timeout — undeclared filter`. Pin: `test_regression_a_go_project_with_no_conf_is_not_refused_for_go_test_timeout`. `cb76109` passed it. |
| AC-AC16 | PASS | — | `test_ac16_*`. Also probed: a declared `--ignore=tests/slow` prints `declared filter: --ignore=tests/slow — …` and gives GREEN (accepted deviation 2). |
| AC-AC17 | PASS | was FAIL | `test_regression_m_after_a_path_named_python_is_still_a_filter` passes. Also probed: `-m "not slow"` inside `VERIFY_COLLECT_CMD` gives `BANNED: -m "not slow" — undeclared filter; …` with exit 2. |
| AC-AC18 | PASS | — | `test_ac18_*` |
| AC-AC19 | PASS | was FAIL | `…_is_refused_at_runtime` passes. Also probed: `--lf`, `--ff`, `--sw`, `-x`, `--maxfail=3` and `--reruns 2` in `VERIFY_ALLOWED_FILTERS`, each with a reason, give `BANNED: <token> can never be allow-listed`. A declared `--ignore=tests/slow` typed at `verify-fast.sh` gives `BANNED: --ignore=tests/slow — path ignored to reach green`, exit 2. |

### Round-1 fake-green routes, re-run

| Round-1 ID | Route | Now |
|---|---|---|
| D1 | Step `stub 3 1 0 \|\| true`, collected 4 | Closed. `step tests exited 0 but its JUnit records 1 failed test(s)` and `EXIT GATE RED`, exit 1. In fast: `FAST VERIFY RED — 1 test(s) failed in the JUnit report`, exit 1. |
| D2 | Conf syntax error on line 2 | Closed. Full: `EXIT GATE RED — scripts/verify.conf failed to load …`, exit 1. Fast: `FAST VERIFY REFUSED — …`, exit 2. |
| D3 | Two steps labelled `tests` | Closed. RED with exit 1 before any step runs. |
| D4 | `pytest tests/python_api -m "not slow"`, configured and at runtime | Closed. Both pins pass. |
| D5 | `STEPS=()` | Closed on bash 3.2: `EXIT GATE RED — no steps configured`. The recorder now adds `no steps configured` too, which covers bash ≥4.4 by construction; not executed (see Could not reach). |
| D6 | `coverage run -m pytest`, `git commit -m`, `tar -x`, `sort -k 2` | Closed for these, but go flags now over-refuse (D12) and path arguments still do (D15). |
| D7 | `-xq`, `-qk smoke`, `-m"not slow"`, `PYTEST_ADDOPTS=-x pytest`, `eval`, `bash -c` | Closed per the ruling. `pytest -qxv` → `BANNED: -qxv`. `pytest -vk smoke` → `BANNED: -vk smoke`. `pytest -rxXs`, `-p no:x` and `-o x=1 -W error -n 4 -c a.ini` are not refused (correct). `eval "…--lf"` prints `limit: flags inside eval or a shell's -c string are not scanned: …`. |
| D8 | Hostname in `runner.id` | Closed: `local:<12 hex>`. |
| D9 | Fast tier with a failing collect | Closed: `— collect failed (exit 3)`. |
| D10 | `record:` path printed with no record | Closed. Malformed JUnit gives `recorder failed — no verdict …` and then `record: not written (scripts/verify_record.py exited 1 before writing it)`. |
| D11 | Shared prune | Closed both ways. The engineer's `test_d11_fast_runs_never_evict_a_full_record` covers one direction. My probe covered the other: 25 full dirs plus 1 older `-fast` dir, then one full run, leaves the fast dir kept and 20 full dirs. |

**A real `PYTEST_ADDOPTS` in the environment** (attack 3):
- `-p no:cacheprovider -rxXs --tb=short` → GREEN.
- `JEST_JUNIT_OUTPUT_DIR=./reports` and `JEST_JUNIT_CLASSNAME={classname}-{title}` → GREEN.
- `-x` → `BANNED: -x — hides the other failures (in PYTEST_ADDOPTS)`, exit 2.
- `--lf` (fast tier) → exit 2.
- A *declared* filter set in `PYTEST_ADDOPTS` (`-m "not real_sleep"`, declared with a reason) is refused as a runtime filter: `BANNED: -m — marker deselection used to reach green (in PYTEST_ADDOPTS)`. This is consistent with "the allow-list covers the project's own step commands only". It is noted for the owner, not filed.

### Scanner probe table (`check-banned --cmd=<command>`, no runner env)

| Command | `cb76109` | `1785567` | Right answer |
|---|---|---|---|
| `go test -timeout 5m ./...` | passes | `BANNED: -timeout — undeclared filter` | pass (D12) |
| `go test -mod=vendor ./...` | passes | `BANNED: -mod=vendor` | pass (D12) |
| `go test -memprofile m.out ./...` | passes | `BANNED: -memprofile` | pass (D12) |
| `go test -fuzztime 10s ./...` | passes | `BANNED: -fuzztime` | pass (D12) |
| `go test -asmflags=-S ./...` | passes | `BANNED: -asmflags=-S` | pass (D12) |
| `go test -exec sudo ./...` | passes | `BANNED: -exec — hides the other failures` | pass (D12) |
| `python3 -mpytest -x` / `--lf` / `--reruns 2` | refused | passes | refuse (D13) |
| `bazel test //... --cache_test_results=yes` | refused | passes | refuse (D14) |
| `cargo nextest run --retries 2` | refused | passes | refuse (D14) |
| `cargo test -- --retries 2` (default runners) | refused | passes; refused only with `--runner="cargo test"` | refuse (D14: the default entry `cargo-test` matches no real command) |
| `make -C tools/jest -k` | refused | refused | pass (D15) |
| `echo pytest -x` | refused | refused | pass (D15, same root cause) |
| `npm test -- --bail`, `tox -- -x` | refused | passes, with no line | at least a `limit:` line (D16) |
| `go test -x ./...` (go: print commands) | refused | refused | owner to rule (D17) |
| `go test -failfast`, `jest -b`, `jest --onlyFailures`, `mocha -b`, `rspec --fail-fast`, `rspec --only-failures`, `phpunit --stop-on-failure` | passes | passes | owner to rule (D17) |

### The stated silent gap (attack 4): judgement

A step listed in `VERIFY_TEST_STEPS` whose command contains no `VERIFY_TEST_RUNNERS` entry is not ban-scanned, and nothing says so. Examples are `npm test`, `tox`, `make test`, `hatch test`, `nox`, `cargo test` and `bazel test`.
- **Measured.** A conf with `tests|python3 scripts/stub_junit.py 3 0 0 --reruns=2`, listed with collect `echo 3`, gives `counts: reported 3 of 3 collected` and `EXIT GATE GREEN`. No `BANNED:` line and no `limit:` line are printed. The stub stands in for `tox -- --reruns 2`.
- **Does it break AC-AC8?** Not as amended. The ruling scopes the bans to recognised runner argv, and the AC-AC8 failures above come from D13 and D14, not from this gap.
- **Does it break R4?** Yes, in its honesty clause. The ruling already requires a `limit:` line when `eval` or `sh -c` hides flags from the scanner. A wrapper hides them the same way, yet produces silence, and silence reads as "scanned, clean".
- **Why the count check does not cover it.** It catches the selecting forms (`--lf`, filters) only when `VERIFY_COLLECT_CMD` is set. It never catches retries, because a rerun does not change the case count.
- **Minimal notice that closes it.** Pass the `VERIFY_TEST_STEPS` labels to `check-banned`. For each listed step whose command has no runner match, print one unindented line and add it to the record's `warnings`. The verdict does not change. Suggested wording: `limit: step <label> runs no runner in VERIFY_TEST_RUNNERS; its flags are not scanned`. This is R12-safe, because `VERIFY_TEST_STEPS` exists only in a conf. Filed as D16. Pin: `test_regression_a_test_step_with_no_recognised_runner_says_it_was_not_scanned`. It asserts only a `limit:` line that names the step, so the engineer can choose the wording.

### Test run (re-test 1)

These are the regression pins on their own, after adding the re-test pins (pytest's temporary paths redacted). Each new pin fails on its own assertion:
- D12: `BANNED: -timeout|-mod=vendor|-memprofile|-exec … == []`
- D13 and D14: `assert 0 == 2`
- D15: `BANNED: -k … == []`
- D16: no `limit:` line
- D18: `'failed to load' not in 'EXIT GATE RED — scripts/verify.conf failed to load (exit 1); no step was run'`

```
$ python3 -m pytest tests/hooks/test_regression_verify_tiers_qa.py -q -p no:cacheprovider
FAILED …::test_regression_a_go_project_with_no_conf_is_not_refused_for_go_test_timeout
FAILED …::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -mod=vendor ./...]
FAILED …::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -memprofile mem.out ./...]
FAILED …::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -exec sudo ./...]
FAILED …::test_regression_an_attached_interpreter_m_still_finds_the_runner[python3 -mpytest --reruns 2---reruns]
FAILED …::test_regression_an_attached_interpreter_m_still_finds_the_runner[python3 -mpytest --lf---lf]
FAILED …::test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[bazel test //... --cache_test_results=yes---cache_test_results=yes]
FAILED …::test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[cargo nextest run --retries 2---retries]
FAILED …::test_regression_a_path_argument_named_like_a_runner_is_not_a_runner
FAILED …::test_regression_a_test_step_with_no_recognised_runner_says_it_was_not_scanned
FAILED …::test_regression_a_conf_whose_last_test_is_false_still_loads
11 failed, 7 passed in 2.32s
```

The 7 that pass are the six round-1 pins plus the round-1 control.

**The engineer's tree before QA added the re-test pins.** The exit gate in the worktree gave the following; the home path in the framework row is redacted:

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             (45s) 344 passed in 44.65s
  OK   ci-examples       (1s) 19 passed in 0.87s
  OK   scar-forge        (1s) LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       (1s) 28 passed in 0.34s
  OK   framework         (7s) memory: 0 problem(s) in /Users/<user>/Desktop/<repo>/.claude/worktrees/agent-ad1e27705199bd4e4/doc/memory
counts: not configured — executed == collected NOT checked
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.
Fill those steps in scripts/verify-full.sh before treating this output as a gate.
record: .verify/runs/20261020T091546Z-20274/record.json
exit=0
```

This confirms the engineer's claims:
- **344 hooks tests pass.** That is 291 pre-existing, 7 round-1 QA pins and 46 new.
- **INCOMPLETE, exit 0.** This is correct for the framework repo, whose lint/format/tests are placeholders.

**Exit gate after adding the re-test pins.** This is the verdict run; the home path and the pytest user directory are redacted:

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (42s) (exit 1)
        probe = _full(tmp_path, _conf(
            ["tests|python3 scripts/stub_junit.py 3 0 0"], collect="echo 3",
            extra='[ -n "${QA_NEVER_SET_FLAG:-}" ] && VERIFY_STEP_BUDGET_S=600\n'))
        assert "QA_NEVER_SET_FLAG" not in os.environ
    
        result = _run(probe)
    
>       assert "failed to load" not in result.stdout, result.stdout
E       AssertionError: EXIT GATE RED — scripts/verify.conf failed to load (exit 1); no step was run
E         
E       assert 'failed to load' not in 'EXIT GATE R...ep was run\n'
E         
E         'failed to load' is contained here:
E           EXIT GATE RED — scripts/verify.conf failed to load (exit 1); no step was run
E         ?                                     ++++++++++++++

tests/hooks/test_regression_verify_tiers_qa.py:252: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_go_project_with_no_conf_is_not_refused_for_go_test_timeout
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -mod=vendor ./...]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -memprofile mem.out ./...]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters[go test -exec sudo ./...]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_an_attached_interpreter_m_still_finds_the_runner[python3 -mpytest --reruns 2---reruns]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_an_attached_interpreter_m_still_finds_the_runner[python3 -mpytest --lf---lf]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[bazel test //... --cache_test_results=yes---cache_test_results=yes]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[cargo nextest run --retries 2---retries]
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_path_argument_named_like_a_runner_is_not_a_runner
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_test_step_with_no_recognised_runner_says_it_was_not_scanned
FAILED tests/hooks/test_regression_verify_tiers_qa.py::test_regression_a_conf_whose_last_test_is_false_still_loads
11 failed, 344 passed in 41.56s
  OK   ci-examples       (1s) 19 passed in 0.78s
  OK   scar-forge        (1s) LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       (0s) 28 passed in 0.31s
  OK   framework         (6s) memory: 0 problem(s) in /Users/<user>/Desktop/<repo>/.claude/worktrees/agent-ad1e27705199bd4e4/doc/memory
counts: not configured — executed == collected NOT checked
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
record: .verify/runs/20261020T092147Z-33019/record.json
exit=1
```

**The RED is expected.** It comes from the 11 new QA pins, each pinning a defect below. Nothing else in the suite fails.

### Defects (re-test 1)

Ordered by severity. Each row carries exactly one rework cause. Round-1 D1 to D11 are closed as listed above.

| ID | Severity | Rework cause | Description | Where | Suggested owner |
|---|---|---|---|---|---|
| D12 | High | regression | **Go projects with no conf are refused.** `_short_cluster` applies pytest's short-option clustering to every runner, but go's flags are single-dash *long* options. `-timeout` is walked as `-t -i -m` with the value `eout`, so it is read as an undeclared marker filter. `-mod=vendor`, `-memprofile` and `-fuzztime` hit `-m` the same way, `-asmflags` hits `-m` after `-a -s`, and `-exec` hits `-x`. `go test` is in `DEFAULT_RUNNERS`, so with no conf a go project's ordinary `go test -timeout 5m ./...` exits 2 before any step runs. That breaks R12 (AC-AC15) and the purpose of the D6 ruling. Any escape needs a conf. `cb76109` passed every one of these. Fix direction: apply cluster parsing only to runners with POSIX short options (pytest/py.test), or skip it for `go test`. Pins: `test_regression_a_go_project_with_no_conf_…`, `test_regression_go_single_dash_long_flags_…[*]`. | `scripts/verify_record.py:134-147` (`_short_cluster`), `:94` (`_VALUE_SHORTS`) | ai-engineer |
| D13 | High | regression | **`python3 -mpytest` hides the runner.** `_runner_argv` matches whole words, so the attached spelling `-mpytest` finds no runner and its argv is never scanned. `python3 -mpytest --reruns 2` and `python3 -mpytest --lf` pass with no line, and retries turn a failure into a pass even with counts configured. `cb76109` refused both. Fails AC-AC8. Pin: `test_regression_an_attached_interpreter_m_still_finds_the_runner[*]`. | `scripts/verify_record.py:241-251` (`_runner_argv`) | ai-engineer |
| D14 | Medium | regression | **The design-listed bans are not refused in the tools they belong to.** `--cache_test_results*` is the build-tool result cache the design names, and no default runner uses it. `bazel test //... --cache_test_results=yes` passes. `cargo nextest run --retries 2` passes too. The default entry `cargo-test` matches no real command line (`cargo test` splits into two words), so cargo is never scanned unless the project sets `--runner="cargo test"`; that was measured with rc=2 versus rc=0. `cb76109` refused these. The engineer's AC-AC8 parametrisation places every form after `pytest`, where `--cache_test_results` never occurs, so it missed this. Fails AC-AC8. Pin: `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[*]`. | `scripts/verify_record.py:90-91` (`DEFAULT_RUNNERS`) | ai-engineer |
| D15 | Medium | missed-ac | **Runner detection matches the basename of any word.** `make -C tools/jest -k` is refused (`BANNED: -k — undeclared filter`): `tools/jest` is a directory argument to make, and make's `-k` means keep-going. `echo pytest -x` is the same root cause. This is round-1 D4's shape again, a path read as a program, now in runner matching. It contradicts the amended AC-AC8 scope, under which bans apply to test-runner argv only. Pin: `test_regression_a_path_argument_named_like_a_runner_is_not_a_runner`. | `scripts/verify_record.py:241-251` (`_runner_argv`) | ai-engineer |
| D16 | Medium | spec-defect | **A listed test step with no recognised runner is silently unscanned.** See the judgement above. The ruling requires a `limit:` notice for `eval`/`sh -c` but not for wrappers (`npm test`, `tox`, `make test`, `bazel test`), which hide flags the same way. Proposed amendment: print one `limit:` line per such `VERIFY_TEST_STEPS` step and record it in `warnings`, without changing the verdict. Pin: `test_regression_a_test_step_with_no_recognised_runner_says_it_was_not_scanned`. | ruling D6/D7 → `scripts/verify_record.py` `cmd_check_banned` | ba-sa (ruling), then ai-engineer |
| D17 | Low | spec-defect | **The ban list carries pytest meanings into every runner.** `go test -x` ("print the commands") is refused as "hides the other failures". The real stop-at-first-failure and last-failed flags of the other default runners pass: `go test -failfast`, `jest -b`, `jest --onlyFailures`, `mocha -b`, `rspec --fail-fast`, `rspec --only-failures`, `phpunit --stop-on-failure`. Listing jest/mocha/go/rspec/phpunit as runners suggests coverage the design §AC.3 list does not give. *Owner ruling needed:* per-runner ban tables, or a pytest-only default list. | design §AC.3; `scripts/verify_record.py:52-69` | ba-sa |
| D18 | Low | regression | **A conf whose last statement is a false test is reported as "failed to load".** Take a conf ending `[ -n "${X:-}" ] && VERIFY_STEP_BUDGET_S=600`, a common bash idiom, with X unset. It loads completely, but `.` returns 1, so the gate prints `EXIT GATE RED — scripts/verify.conf failed to load (exit 1); no step was run`. It fails closed, but it names the wrong reason. `cb76109` ran this conf GREEN. Fix direction: detect a parse failure with `bash -n scripts/verify.conf` before sourcing, instead of reading the exit status of `.`. Pin: `test_regression_a_conf_whose_last_test_is_false_still_loads`. | `scripts/verify-full.sh:59-64`, `scripts/verify-fast.sh:32-39` | ai-engineer |

### Edge cases probed (re-test 1), not filed

- **Conf that reads an unset variable** (`VERIFY_RUNNER_ID=$CI_RUNNER_NAME`). Under `set -u` the gate dies with `scripts/verify.conf: line 6: CI_RUNNER_NAME: unbound variable`, exit 1, with no banner and no record. It fails closed, so it is not filed. A `bash -n` pre-check (D18) would not catch it.
- **`STEPS=('')`**. The empty label matches the `case " ${VERIFY_TEST_STEPS:-} "` pattern, so the gate gives RED `no JUnit report written by step ` (with an empty name). It fails closed.
- **Repeated non-test label** (`lint` twice) → GREEN. Correct: only test labels share a JUnit directory.
- **Flags out of the scanner's sight.** `pytest $(echo -x)` is not scanned and gives no `limit:` line; command substitution is split into its own words. `PYTEST_ADDOPTS+=-x pytest` is not seen either. Both are tampering forms, in line with "tamper-evident, not tamper-proof".
- **`pytest -o -x`** → refused. pytest would read `-x` as the value of `-o`, but no one writes that.
- **Spellings that are not filters** (`-rxXs`, `-p no:x`, `-nx`, `-Wx`) → not refused. Correct.

### Engineer's claims — judgement (re-test 1)

| Claim | Judgement |
|---|---|
| "6 red pins are now green" | CONFIRMED: `7 passed` covers the 6 pins plus the control. |
| "46 new tests; 344 hooks passed" | CONFIRMED: `344 passed` = 291 + 7 + 46. |
| "Gate ends INCOMPLETE with exit 0" | CONFIRMED (run above). |
| Accepted deviation 1: duplicate labels give RED, exit 1 | Matches the pinned test; accepted. |
| Accepted deviation 2: `--ignore`/`--ignore-glob` declarable | Measured working at configure time, and refused at runtime. |
| The stated silent gap | Real, and it reaches further than stated: it also covers `bazel test` (where the cache ban lives) and `cargo test` (the `cargo-test` typo). Filed as D16, plus D14 for the part that is a regression. |

## Re-test 2 (am2)

Tree under test: worktree `agent-a0bb7774512557e28` at `0fd71b6`, which carries `d259245` (A+C merged under am2), plus the engineer's uncommitted AC-AC20 fix. That fix touches `scripts/verify-full.sh`, `scripts/verify-fast.sh`, `scripts/verify-handoff.sh` and `tests/hooks/test_verify_tiers.py` (+75 lines). The criteria are AC-AC1 to AC-AC19 as reworded by `doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md` (Approved), plus its new AC-AC20 to AC-AC24. The independent review `doc/qa/REVIEW-verify-tiers-AC.md` is round 3, PASS (`afb16f9`).

All commands ran on 2026-10-22 with `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin24)`. Scratch copies were kept outside the repo.

**Provenance.** The brief says this is tier 1 under the approved am2. It does not say a human approved this implementation. Tier 1 lets QA run first, so this is flagged and does not block.

### Verdict: PASS

All 24 criteria pass. AC-AC8 counts once here; its four am2 clauses (8a to 8d) each pass. AC-AC8 and AC-AC15 pass with the original re-test 1 repros. AC-AC20 passes in all three tiers, and it is shown red against `HEAD` first. `pytest tests` gives `1884 passed, 1 skipped`, and the exit gate gives `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests` with exit 0 (hooks `1308 passed`; this repo's lint/format/tests are placeholders, so INCOMPLETE is the right result, not GREEN).

Count: 24 PASS, 0 FAIL.

### What am2 reworded

| Item | am2 change | Effect on this re-test |
|---|---|---|
| AC-AC8 | Replaced by AC-AC8a (bans match pytest-family argv only), AC-AC8b (other programs are not scanned for built-in bans), AC-AC8c (one `limit:` line per unscanned step, kept in `record.warnings`) and AC-AC8d (`VERIFY_EXTRA_BANNED` applies to every program) | Re-test 1's D13 is now an AC-AC8a case. D15 is an AC-AC8b case. D16 became AC-AC8c. D14 and D17 are declared limits, not defects. |
| AC-AC19 | Amended: the hard-ban list grows (`--ff`, `--sw` and their families), and `--ignore`/`--ignore-glob` can be declared | Accepted deviation 2 is now the wording |
| AC-AC5 | One clause added: duplicate test labels give RED, exit 1 | Accepted deviation 1 is now the wording |
| AC-AC6 | Two exact clauses: `ran N of ?`, and `collect failed (exit n)` | Round-1 D9 is now the wording |
| AC-AC15 | Not reworded. AC-AC8b now names `go test -timeout 5m ./...` explicitly as a command that must not be refused. | D12 is checked under both |
| AC-AC20 to AC-AC24 | New: the conf syntax check (AC-AC20), the hashed `runner.id` (AC-AC21, AM2-R4), separate pruning for fast and full runs (AC-AC22, AM2-R5), the content-hashed tree (AC-AC23), and the retry-plugin bans `--force-flaky`/`--max-runs` (AC-AC24) | Each gets its own verdict below |
| Design §AC.3 and ADR-14 `ALLOWLISTABLE` | Superseded by am2's ban table | Probes below use the am2 table |
| QA pin `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to` | Retired by am2's "QA regression pins" table, because D14 is now declared limit L1 | Deleted on the branch. A comment at its old place names am2. The 16 remaining pin cases (13 functions, three of them parametrised) are collected and pass. |

### Re-test 1 defects, now

| ID | Status | Evidence |
|---|---|---|
| D12 | Closed | `go test -timeout 5m ./...`, `-mod=vendor`, `-memprofile m.out`, `-fuzztime 10s`, `-asmflags=-S` and `-exec sudo` all give rc=0 with no `BANNED:` line. In a listed test step they also print `limit: step tests runs no known runner; …`, as AC-AC8c requires. Pins `test_regression_a_go_project_with_no_conf_…` and `test_regression_go_single_dash_long_flags_…[*]` pass. |
| D13 | Closed | `python3 -mpytest -x` / `--lf` / `--reruns 2` each give rc=2 with `BANNED: -x — hides the other failures`, `BANNED: --lf — selects nothing after a green run` and `BANNED: --reruns — retries turn a failure into a pass`. Pin `test_regression_an_attached_interpreter_m_…[*]` passes. |
| D14 | Retired (declared limit L1) | `bazel test //... --cache_test_results=yes` and `cargo nextest run --retries 2` give rc=0 and, in a listed test step, the `limit:` line. That is what am2 asks for. A project can refuse them through `VERIFY_EXTRA_BANNED` (AC-AC8d, probed below). |
| D15 | Closed | `make -C tools/jest -k`, `make -C tools/pytest -k` and `echo pytest -x` give rc=0, with no `BANNED:` line. Pin passes. |
| D16 | Closed (now AC-AC8c) | `npm test -- --bail` and `tox -- -x` in a listed test step print the `no known runner` limit line. Pin `test_regression_a_test_step_with_no_recognised_runner_…` passes. |
| D17 | Resolved by am2 scope | Built-in bans are pytest-only (AC-AC8a and AC-AC8b), so `go test -x` is no longer refused. Other runners' stop/last-failed flags are limit L6, or are declared by the project. |
| D18 | Closed | A conf whose last line is false loads in all three tiers (AC-AC20 below). Pin `test_regression_a_conf_whose_last_test_is_false_still_loads` passes. |

### Criteria results (re-test 2)

| # | Verdict | Evidence |
|---|---|---|
| AC-AC1 to AC-AC4 | PASS | `test_ac1_*` to `test_ac4_*` are in the 1884-pass run. The exit gate prints timed rows and a `record:` line. |
| AC-AC5 (+ am2 clause) | PASS | `test_d3_two_test_steps_with_one_label_…`, plus pins `test_regression_a_conf_that_stops_parsing_…` and `test_regression_two_steps_sharing_a_test_label_…` (pass) |
| AC-AC6 (+ am2 clauses) | PASS | `test_ac6_*`, `test_d9_*`, `test_a_collect_command_that_fails_is_red` (pass) |
| AC-AC7 | PASS | `test_ac7_*` |
| AC-AC8a | PASS | `check-banned --test-steps=tests "--step=tests\|<cmd>"`, probe output: `pytest tests/python_api -m "not slow"` → `BANNED: -m "not slow" — undeclared filter; …`. `.venv/bin/pytest -qxv` → `BANNED: -qxv`. `pytest -vk smoke` → `BANNED: -vk smoke`. `pytest -m"not slow"` → `BANNED: -m"not slow"`. `env A=1 uv run pytest --sw` → `BANNED: --sw`. `time -p pytest --ff` → `BANNED: --ff`. `if pytest --lf; then :; fi` → `BANNED: --lf`. `PYTEST_ADDOPTS=-x pytest` → `BANNED: -x — … (in PYTEST_ADDOPTS)`. Each of these is rc=2. `pytest -rxXs -p no:x` and `pytest --cache-clear` → rc=0 (correct). Plus D13 above, and the am2-listed tests in the suite run. |
| AC-AC8b | PASS | rc=0 with no `BANNED:` line for `git commit -m x`, `tar -x`, `sort -k 2`, `go test -timeout 5m ./...`, `make -C tools/pytest -k`, `echo pytest -x`, `python3 -m pytest` and `coverage run -m pytest`. With no `--test-steps` (no conf), `go test -timeout 5m ./...`, `go test -exec sudo ./...` and `cargo test -- --retries 2` → rc=0 and silent. |
| AC-AC8c | PASS | `--runner=jest`, step `tests\|jest --ci` → `limit: step tests runs jest; its flags are not scanned — declare bans in VERIFY_EXTRA_BANNED`, rc=0. Steps `tests\|pytest -q`, `e2e\|npm run e2e` and `lint\|ruff check .`, with `tests e2e` listed → exactly one line, for `e2e`, with `no known runner`. Nothing for the scanned `tests` step or the unlisted `lint` step. The `rt1_*` record and verdict tests pass. |
| AC-AC8d | PASS | `--extra=-failfast`: `go test -failfast ./...` in a test step → `BANNED: -failfast — project-declared`, rc=2, after the limit line. The `=` form `-failfast=true` → `BANNED: -failfast=true — project-declared`. In a non-test step (`make lint -failfast`) and at runtime (`--runtime=-failfast`) it is refused too. |
| AC-AC9 to AC-AC12 | PASS | `test_ac9_*` to `test_ac12_*` |
| AC-AC13 | PASS | ci-examples and the pre-existing hooks tests pass in the gate run. The one QA pin deleted is the one am2 retires (see above). |
| AC-AC14 | PASS | `test_ac14_*`. The gate run prints `counts: not configured — executed == collected NOT checked`. |
| AC-AC15 | PASS | Original repro: the D12 pin builds a project with no conf whose test step is `go test -timeout 5m ./...`. It passes: no `BANNED:` line and no exit 2. `test_ac15_*` and `test_d6_a_project_as_filled_in_today_with_realistic_commands_stays_green` pass. |
| AC-AC16 to AC-AC18 | PASS | `test_ac16_*` to `test_ac18_*`. Probe: `--allow='-m slow\|nightly'` with step `pytest -m slow` → `declared filter: -m slow — nightly`, rc=0. `--allow='--deselect=t::a'` with no reason → `BANNED: allow-list entry without a reason: --deselect=t::a`, rc=2. |
| AC-AC19 (amended) | PASS | `--allow='--co\|why'` → `BANNED: --co — only -m, -k, --deselect, --ignore and --ignore-glob can be declared`, rc=2. A declared `-m slow` passed at runtime → `BANNED: -m — marker deselection used to reach green`, rc=2. `test_ac19_*` and `test_d7_ignore_…` pass. |
| AC-AC20 | PASS | See the AC-AC20 table below: all three tiers, red-first against `HEAD`. |
| AC-AC21 | PASS | `test_d8_the_local_runner_id_never_carries_the_hostname` and `test_the_runner_id_comes_from_the_environment_when_set` are collected and pass |
| AC-AC22 | PASS | `test_d11_fast_runs_never_evict_a_full_record` passes. The reverse direction was probed in re-test 1 (D11 row). |
| AC-AC23 | PASS | `test_rt1_a_same_size_edit_with_an_unchanged_mtime_is_hashed_by_content` passes |
| AC-AC24 | PASS | `test_ac24_*`: 17 cases, all pass. Probes: `pytest --force-flaky`, `pytest --max-runs 3`, `python3 -m pytest -q --force-flaky` and `PYTEST_ADDOPTS=--max-runs=2 pytest` → rc=2, `BANNED: … — retries turn a failure into a pass`. `--allow='--force-flaky\|flaky suite'` and `--allow='--max-runs\|x'` → `BANNED: <token> can never be allow-listed`. `--runtime=--force-flaky` → rc=2. `pytest --flake-runs 3` → rc=0 (L7). **Red-first:** `git show e436d1f:scripts/verify_record.py` run with `check-banned "--step=tests\|pytest --force-flaky"` and `…--max-runs 3` → both rc=0. |

### AC-AC20 in all three tiers

Each conf was copied as `scripts/verify.conf` into a fresh scratch git repo holding the worktree's `scripts/`. Each tier was then run: `verify-full.sh`, `verify-fast.sh x.py`, `verify-handoff.sh --status` and `verify-handoff.sh`.

| Conf | `bash -n` | full | fast | handoff `--status` / run |
|---|---|---|---|---|
| `STEPS=(` open at EOF, settings after it (the review's repro) | rc 0, prints `unexpected EOF while looking for matching ')'` | rc 1, `EXIT GATE RED — scripts/verify.conf failed to load (syntax error); no step was run`, no step ran | rc 2, `FAST VERIFY REFUSED — scripts/verify.conf failed to load (syntax error)`, no step ran | `not opted in` + stderr `scripts/verify.conf failed to load (syntax error)` / rc 3, `HANDOFF TIER NOT CONFIGURED — scripts/verify.conf failed to load (syntax error); …` |
| `X=(a b` as the last line, after valid `STEPS` | rc 0, prints | same as above | same | same |
| Open `"`, open `'`, stray `fi`, open `if`, open `$(`, open `${` | rc 2 | same as above, for each | same | same |
| UTF-8 BOM before `STEPS=` | rc 2 | refused, as above | refused | refused |
| Last line `[ -n "${QA_NEVER_SET_FLAG:-}" ] && VERIFY_STEP_BUDGET_S=600` | rc 0, silent | rc 0, `EXIT GATE GREEN`, step ran, no `failed to load` | rc 0, `FAST VERIFY OK — partial run: …`, no `failed to load` | `not opted in`, empty stderr (this conf does not opt in) |
| Last line `false` | rc 0, silent | GREEN, as above | OK, as above | as above |
| Unbalanced `(` inside a comment and inside a quoted string | rc 0, silent | GREEN | OK | as above |
| `scripts/verify.conf.example`; an empty conf | rc 0, silent | no `failed to load`; the steps ran (the RED that follows comes from the probe copy, which has no `tests/` for the default hooks step) | `FAST VERIFY INCOMPLETE …`, no `failed to load` | `not opted in`, empty stderr / rc 3, plain not-opted-in banner |

**The handoff tier with an opt-in conf.** These were driven through `tests/hooks/test_verify_handoff.py`'s own `_repo`/`_run` helpers, from a scratch script. The conf is the full opt-in conf, then one of the following:
- `VERIFY_ALLOWED_FILTERS=(` open at EOF;
- `VERIFY_UNTRACKED_INPUTS=(` open at the *top*, with the opt-in settings after it;
- `X="abc` open at EOF.

Each gives `--status` → `not opted in` + `failed to load (syntax error)`, and the run gives rc 3 with the broken-conf banner; `_nothing_ran` is true. Controls behave as they should: the same conf with a false last line gives `opted in` and rc 0 (`HANDOFF TIER — ran 3 of 5 …`), and so does the bare opt-in conf.

**Red-first against `HEAD` (`0fd71b6`, without the fix).** These are scripts from `git archive HEAD`, with the same probes:
- **Full:** conf `STEPS=("tests|touch STEP-MARK; echo STEP-RAN")` / `X=(` / `VERIFY_TEST_STEPS="tests"` / `VERIFY_COLLECT_CMD="echo 5"`. The run prints `OK tests … STEP-RAN`, `counts: not configured — executed == collected NOT checked` and `EXIT GATE GREEN`, rc 0. The two settings after the open array were dropped silently. With the fix, it gives rc 1 with the syntax-error banner, and the marker file is not created.
- **Fast:** conf `LINT=(touch STEP-MARK)` / `TEST=(touch STEP-MARK)` / `VERIFY_COLLECT_CMD="echo 5"` / `X=(`. The run gives rc 0, `FAST VERIFY OK — partial run: ran ? of 5 …`, and the steps ran. With the fix, it gives rc 2 `FAST VERIFY REFUSED …`, and the marker is not created.
- **Handoff:** opt-in conf + `VERIFY_ALLOWED_FILTERS=(` open at EOF. `--status` gives `opted in` (stderr carries bash's EOF error), and the run gives rc 0, `HANDOFF TIER — ran 3 of 5`. With the fix: not opted in, rc 3.

### Edge cases probed (re-test 2), not filed

- `pytest -- -x` → refused (`BANNED: -x`). After `--`, `-x` is a path. That is over-refusal, but no one writes it, and it fails closed.
- `pytest --lf-not-really` → refused by the `--lf*` prefix rule. That is the table's stated prefix match.
- `pytest --co` in a test step → not refused. It collects and runs nothing, so AC-AC5's zero-cases rule covers it.
- `pytest tests/-x` → not refused (correct: it is a path).

### Test run (re-test 2)

Both commands ran in worktree `agent-a0bb7774512557e28`, with output redirected to a log. `scripts/verify-handoff.sh --status` → `not opted in`, so the verdict command is `scripts/verify-full.sh`.

```
$ python3 -m pytest tests -q -p no:cacheprovider
1884 passed, 1 skipped in 254.86s (0:04:14)
pytest_exit=0
```

The skip is `tests/framework/test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now — see the test above`. It is pre-existing, and outside this slice.

```
$ bash scripts/verify-full.sh
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             (200s) 1308 passed in 199.97s (0:03:19)
  OK   ci-examples       (5s) 30 passed in 3.56s
  OK   scar-forge        (1s) LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       (4s) 155 passed in 3.66s
  OK   framework         (45s) memory: 0 problem(s) in /Users/<user>/Desktop/<repo>/.claude/worktrees/agent-a0bb7774512557e28/doc/memory
counts: not configured — executed == collected NOT checked
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.
Fill those steps in scripts/verify-full.sh before treating this output as a gate.
record: .verify/runs/20261022T083820Z-88018/record.json
full_exit=0
```

### Engineer's claims — judgement (re-test 2)

| Claim | Judgement |
|---|---|
| Full, fast and handoff refuse when `bash -n` exits non-zero or prints anything | CONFIRMED in all three tiers (table above) |
| A false last line and `verify.conf.example` still load | CONFIRMED |
| The new tests are red without the fix | CONFIRMED independently through the red-first probes above (not with `-k`) |

### Parked (outside the ACs; for the coordinator)

- A conf that writes to stdout or stderr when loaded (for example `echo hello-from-conf`) puts that text into the output of `verify-handoff.sh --status`, so the output becomes `hello-from-conf` followed by `not opted in`. Callers that compare the whole stdout would misread it.
- A conf with CRLF line endings passes `bash -n` (rc 0, silent). It then loads labels with a trailing `\r` and fails closed: RED with `eval: … syntax error near unexpected token ')'`, and no `failed to load` line names the real cause.
- A conf saved with a UTF-8 BOM is refused as a syntax error. That fails closed, but the message does not mention the BOM, so it is a usability point.
- An unterminated heredoc is not caught by `bash -n`. The reviewer parked this already; it is repeated here only for completeness.
- LIMIT (threat model): deliberate tampering, such as hiding flags in `$FLAGS` or renaming pytest, stays within am2's declared limits L1 to L8. It was not chased.

## Approval history

- **2026-10-20 — drafted.** qa wrote this from the approved spec and design, a read of `scripts/verify_record.py`, `verify-full.sh` and `verify-fast.sh`, direct probes in scratch git repos, and the full gate run above. Nothing was committed and the main tree was not modified; it was read only, for the merge check.
- **2026-10-20 — re-test 1.** qa re-tested the rework at `f441d8d` against the coordinator's D6–D11 rulings. It added 11 `test_regression_*` pins (D12–D16, D18), ran direct scanner probes against `cb76109` and `1785567`, and ran the full gate above. It also redacted a truncated username fragment that round 1 left in the D5 traceback, and the repo directory name in the round-1 framework row. Nothing was committed and the main tree was not touched.
- **2026-10-22 — re-test 2 (am2).** qa re-tested worktree `agent-a0bb7774512557e28` at `0fd71b6` (which carries `d259245`) plus the uncommitted AC-AC20 fix, against am2. It ran `python3 -m pytest tests` (1884 passed, 1 skipped) and `scripts/verify-full.sh` (INCOMPLETE, exit 0), ran scanner probes and three-tier conf probes in scratch copies, and ran red-first checks against `HEAD` and `e436d1f`. Verdict PASS, 24/24. No test was added (the brief's Files list names only this report), and no other file was edited.
