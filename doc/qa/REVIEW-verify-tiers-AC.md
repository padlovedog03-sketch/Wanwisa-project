# Review: verify tiers, increment A+C (close-out under amendment am2)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md
Author-run: d259245, a0bb7774512557e28, a3dcb95750ccd5b91
Reviewer-run: ac88c1891477261ac
Date: 2026-10-22

## Verdict: PASS

Round 3 (delta review of the round-2 parked item): `scripts/verify-handoff.sh` now marks a conf `broken` when bash's `-n` exits non-zero **or prints anything**, the same rule round 2 accepted in the full and fast tiers. An array open at EOF is no longer read as opted in; a false last line and the example conf still load; banners and exit codes are unchanged; the new pin is red against the old line.

## Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md` (Approved), AC-AC20.
- Change: uncommitted diff in worktree `.claude/worktrees/agent-a0bb7774512557e28` on top of `0fd71b6`. `git diff --stat` there → 4 files: `verify-fast.sh`, `verify-full.sh` (both reviewed in round 2), `verify-handoff.sh` (+3/-2, new in this round) and `tests/hooks/test_verify_tiers.py` (+75, of which the three `test_d2_the_handoff_tier_*` tests are new in this round). The handoff diff changes only the `if` at line 44 (was `if "$BASH" -n scripts/verify.conf 2>/dev/null; then`, now `if conf_err="$("$BASH" -n scripts/verify.conf 2>&1)" && [ -z "$conf_err" ]; then`) and its comment.
- Not read: the author's conversation.

## Criteria Review

All commands ran in `.claude/worktrees/agent-a0bb7774512557e28` on 2026-10-22 with `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin24)`. Scratch copies live under this run's scratchpad (`.../scratchpad/r3`, `.../scratchpad/h`).

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| Brief | Verify-with suite | PASS | `python3 -m pytest tests/hooks/test_verify_tiers.py tests/hooks/test_verify_handoff.py -q -p no:cacheprovider` → `340 passed in 80.95s`. |
| AC-AC20 (handoff) | Array open at EOF → not opted in, existing broken path | PASS | `test_d2_the_handoff_tier_refuses_a_conf_with_an_array_open_at_eof` (in the 340) asserts `--status` → rc 0, stdout `not opted in`, stderr `scripts/verify.conf failed to load (syntax error)`; a normal run → rc 3, last line `HANDOFF TIER NOT CONFIGURED — scripts/verify.conf failed to load (syntax error); scripts/verify-full.sh before every handoff stays in force`, and nothing ran. The conf carries every opt-in setting before the open array, so a partial load would have opted in. |
| AC-AC20 (handoff) | False last line still loads | PASS | `test_d2_the_handoff_tier_still_loads_a_conf_whose_last_line_is_false` → `--status` rc 0, `opted in`, empty stderr; run rc 0, no `failed to load`. |
| AC-AC20 (handoff) | Example conf not treated as broken | PASS | `test_d2_the_handoff_tier_reads_the_example_conf_as_loaded` → `not opted in`, empty stderr, rc 3 with the plain not-opted-in banner. Independent probe: `scripts/verify.conf.example` copied as the conf in a bare scratch dir, `bash scripts/verify-handoff.sh --status` → `not opted in`, no syntax-error line. |
| AC-AC20 (handoff) | New pin red against the old line | PASS | Scratch copy `.../scratchpad/r3` with line 44 put back to `if "$BASH" -n scripts/verify.conf 2>/dev/null; then` (grep confirmed), tests kept: `python3 -m pytest tests/hooks/test_verify_tiers.py -q -p no:cacheprovider -k "d2_the_handoff_tier"` → `1 failed, 2 passed, 240 deselected`; the failure is `assert (0, 'opted in\n') == (0, 'not opted in\n')`. The other two pass on the old line as well, as they should (they pin non-regression, not the fix). `-k` was used only for this red check, never for the verdict suite. |
| No other change | Banners and exit codes | PASS | `git diff scripts/verify-handoff.sh` touches only the `if` line and two comment lines; the `--status` block, both `not_configured` messages and every `exit` are untouched. |
| Exit gate | `scripts/verify-full.sh` | INCOMPLETE (as configured) | `scripts/verify-handoff.sh --status` → `not opted in`. `bash scripts/verify-full.sh` → rc=0: `OK hooks (180s) 1308 passed`, `OK ci-examples (4s) 30 passed`, scar-forge, coordinator (`155 passed`) and framework OK; `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. |

## Defects

None in scope.

## Hostile inputs tried

Bare scratch dir with only `verify-handoff.sh`, `bash scripts/verify-handoff.sh --status`:

- Empty conf → `not opted in`, no syntax-error line (not falsely broken).
- CRLF conf `VERIFY_HANDOFF_TIER=on\r` → `not opted in` (the value is `on\r`, so it fails closed; no syntax-error line, because bash does not flag CR).
- Unterminated here-document after `VERIFY_HANDOFF_TIER=on` → `opted in`. bash 3.2's `-n` prints nothing for it, so this check cannot see it. Same behaviour as the full and fast tiers, already parked in round 2 with a proposed LIMIT line; not a regression of this delta.

## Parked (outside the criteria in scope, rule 4)

- **Unterminated here-document** — unchanged from round 2's Parked list; the handoff tier now shares it with the other two tiers. LIMIT line, if the coordinator wants one: "The conf syntax check is bash's own `-n`; a here-document left open is not a syntax error to bash 3.2, and the rest of the conf becomes its body."
- Round 2's other parked items (CRLF in the fast tier, unbound variable in the conf) are not touched by this delta.

## Review history

### Round 2 — 2026-10-22, reviewer run `ae7617bb8378a9a55`, result PASS

Round 2 (re-review after REWORK of AC-AC20): both tiers now refuse a conf that bash 3.2's `bash -n` reports on while exiting 0 (an array open at EOF), with the spec's exact banners and exit codes; a conf whose last line is false still loads; the two new pins are red without the fix.

#### Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md` (Approved), AC-AC20 (line 136) and AM2-R7 (line 212).
- Change: uncommitted diff in worktree `.claude/worktrees/agent-a0bb7774512557e28` on top of `0fd71b6`: `scripts/verify-full.sh` (+4/-2), `scripts/verify-fast.sh` (+3/-2), `tests/hooks/test_verify_tiers.py` (+29). `git diff --stat` in that worktree shows exactly these 3 files. Both scripts change only the `if` condition and its comment: `if ! conf_err="$("$BASH" -n scripts/verify.conf 2>&1)" || [ -n "$conf_err" ]; then`. The banners, the `printf` of the error and the `exit 1` / `exit 2` lines are unchanged.
- Round 1 of this review (below, under Review history): FAIL on AC-AC20 only. All other criteria were PASS there and the code behind them is not touched by this diff.
- Round 1's routing note is resolved: the check is still `bash -n` (its exit status or its output), so the fix stays inside AC-AC20's "The check is `bash -n`" and needs no spec ruling.
- Not read: the author's conversation. The brief's claims (the fix, and the reason for not refusing on a non-zero load status) were re-run here, not relayed.

#### Criteria Review

All commands ran in `/Users/pongsakorn.ni/Desktop/jarvis-framework/.claude/worktrees/agent-a0bb7774512557e28` on 2026-10-22 with `/bin/bash` = `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin24)`, the only bash on PATH (`which -a bash`). "Probe" means a scratch script that calls the test module's own `_full` / `_fast` / `_run` helpers (stubbed copies of the scripts in a temp git repo).

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| Brief | Verify-with suite | PASS | `python3 -m pytest tests/hooks/test_verify_tiers.py tests/hooks/test_verify_scripts.py tests/hooks/test_regression_verify_tiers_qa.py -q -p no:cacheprovider` → `289 passed in 69.74s`. |
| AC-AC20 (a) | Broken conf refused, full tier | PASS | Probe, conf `STEPS=(` / `"tests\|echo STEP-RAN"` with no `)`: rc=1, `EXIT GATE RED — scripts/verify.conf failed to load (syntax error); no step was run`, then `scripts/verify.conf: line 1: unexpected EOF while looking for matching `)'`, and no step ran. The same probe also refused, rc=1 with no step run: an unclosed double quote, an unclosed single quote, an unclosed `if`, a stray `fi` and an unclosed `$(`. |
| AC-AC20 (a) | Broken conf refused, fast tier | PASS | The same six confs in the fast tier: rc=2, `FAST VERIFY REFUSED — scripts/verify.conf failed to load (syntax error)`, and no step ran. |
| AC-AC20 (b) | False last line still loads | PASS | Probe, full tier: a good conf (`STEPS=('tests\|python3 scripts/stub_junit.py 5 0 0')`, `VERIFY_COLLECT_CMD='echo 5'`) plus a last line `[ -n "${QA_NEVER_SET:-}" ] && VERIFY_STEP_BUDGET_S=600` → rc=0, `counts: reported 5 of 5 collected`, `EXIT GATE GREEN`, the same output as without that line, and no `failed to load`. Fast tier: rc=0, no `failed to load`. Pinned by `test_rt1_a_fast_conf_whose_last_test_is_false_still_loads` and `test_regression_a_conf_whose_last_test_is_false_still_loads` (both in the 289). |
| AC-AC20 | Author's reason for not refusing on a non-zero load status | Confirmed | `/bin/bash -c ". open.conf; echo source_rc=$?"` → `source_rc=1`; for `X=1` / `[ -n "${NOPE:-}" ] && Y=1` → also `source_rc=1`. The status of `.` cannot tell the two apart, and AC-AC20 requires the second one to load. `/bin/bash -n` gives rc=0 for both; it prints `unexpected EOF while looking for matching `)'` for the first and nothing for the second. So "rc≠0 or any output" separates them, and "load status≠0" cannot. |
| AC-AC20 | Valid conf not refused | PASS | `/bin/bash -n scripts/verify.conf.example` → rc=0, empty output. Probe with `scripts/verify.conf.example` as the conf: full tier rc=0, `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, no `failed to load`; fast tier rc=0, last line `Fill LINT and TEST in scripts/verify-fast.sh.`, no `failed to load`. Comment-only and empty confs are not refused either (probe: full tier rc=0 `EXIT GATE INCOMPLETE`, the pre-existing no-steps result; fast tier rc=0). |
| AC-AC20 | New tests red without the fix | PASS | `git show HEAD:scripts/verify-full.sh` and `HEAD:scripts/verify-fast.sh` copied over the fixed scripts, tests kept: `python3 -m pytest tests/hooks/test_verify_tiers.py -q -p no:cacheprovider -k array_open_at_eof` → `2 failed, 238 deselected`: full tier `assert 0 == 1` (output contains `Everything configured passed, and that is ALL this run proves.`), fast tier `assert 0 == 2`. The fixed scripts were then restored; `git diff --stat` matched the original 3-file stat. |
| No other change | Banners and exit codes elsewhere | PASS | `git diff` touches only the two `if` lines and their comments; no `echo`, `exit` or other line changed. |
| Exit gate | `scripts/verify-full.sh` | INCOMPLETE (as configured) | `scripts/verify-handoff.sh --status` → `not opted in`. `scripts/verify-full.sh` → rc=0: `OK hooks (295s) 1303 passed`, `OK ci-examples (9s) 30 passed`, scar-forge, coordinator and framework OK; `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. Round 1's gate-3 ci-examples red is gone on this tree. |

#### Defects

None in scope.

#### Hostile inputs tried

- The six broken confs above, in both tiers → all refused with the spec's banner and exit code.
- Here-document with no terminator (`cat <<EOT` / `hello` at EOF) → not refused in either tier: bash 3.2's `bash -n` gives rc=0 and prints nothing. Bash does not call this a syntax error, and AC-AC20 says "the check is `bash -n`", so it is outside the criterion. See Parked.
- CRLF line endings on a valid conf → not refused (bash accepts the syntax). The full tier ended RED (`record: not written (scripts/verify_record.py exited 1 before writing it)`), so it fails closed; the fast tier ended `FAST VERIFY OK`. Not a syntax error. See Parked.
- A conf that sets `VERIFY_STEP_BUDGET_S` on a false last line → loads, GREEN, identical to the same conf without it.

#### Parked (outside the criteria in scope, rule 4)

- **`scripts/verify-handoff.sh:43` has the round-1 hole.** It checks `if "$BASH" -n scripts/verify.conf 2>/dev/null; then`, by exit status only, so on bash 3.2 an array open at EOF is not marked `broken` there. AC-AC20 names only `verify-full.sh` and `verify-fast.sh`, and that file is not in this brief's Files. For the coordinator.
- **Unterminated here-document in the conf.** A `<<EOT` with no `EOT` line swallows the rest of the conf as its body, a silent partial load of the same family, and bash 3.2's `bash -n` reports nothing. Proposed LIMIT line, if the coordinator wants one: "The conf syntax check is bash's own `-n`; a here-document left open is not a syntax error to bash 3.2, and the rest of the conf becomes its body."
- **CRLF conf in the fast tier** loads values with a trailing carriage return and can end `FAST VERIFY OK`. Low; no AC covers it.
- **Round-1 note still open:** a conf with `[ -n "$NOPE" ] && Y=2` and NOPE unset stops at `unbound variable`. Not re-probed in this round; this diff does not change it.


### Round 1 — 2026-10-22, reviewer run `a4095c6cb10bfbe75` (header line read `a4095c6cb10bfbe75`), result FAIL

AC-AC8 (a to d) and AC-AC15, the two criteria QA last failed, now pass. AC-AC20 fails: on macOS's bash 3.2, a conf with an unclosed array is not caught. `bash -n` accepts it, the conf loads only partly, and the full gate ends `EXIT GATE GREEN` with exit 0.

AC-AC8 (a to d) and AC-AC15, the two criteria QA last failed, now pass. AC-AC20 fails: on macOS's bash 3.2, a conf with an unclosed array is not caught. `bash -n` accepts it, the conf loads only partly, and the full gate ends `EXIT GATE GREEN` with exit 0.

#### Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md` (Approved). It amends `doc/specs/SPEC-verify-tiers-merge-gate.md`, Part A/C. For AC-AC15, the base spec's wording was read (am2 does not rewrite it).
- Change: squash `d259245` on `feat/top3-tiers-mechanisms-deny`. The code reviewed is the code on HEAD `ef1f717`. Since `d259245`, increments B and D (`7a47d5e` to `4a209d6`) have also touched `scripts/verify_record.py` and `verify-full.sh`, so the review judges what ships now.
- QA history: `doc/qa/QA-verify-tiers-AC.md`, re-test 1 (at `f441d8d`: 2 FAIL, AC-AC8 and AC-AC15).
- Not read: the author's conversation. Every claim in the commit message and the am2 `[MEASURED]` markers was re-run here and not relayed.

#### Criteria Review

All commands were run from `/Users/pongsakorn.ni/Desktop/jarvis-framework` on 2026-10-22, unless a scratch repo is named. "check-banned" means `python3 scripts/verify_record.py check-banned …`.

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| Brief | Verify-with suite | PASS | `python3 -m pytest tests/hooks/test_verify_tiers.py tests/hooks/test_verify_scripts.py -q -p no:cacheprovider` → `271 passed in 42.97s`. Subset `-k "ac15 or d6_a_project or ac24 or ac8 or rt1 or ac19 or d3_ or d9_ or collect_command_that_fails or d2_ or d8_ or runner_id_comes or d11_ or d7_"` → `194 passed, 44 deselected`. Every test named in am2 exists on HEAD (checked against `--co` output). The only exception is the retired pin `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to`, which am2 says to delete. |
| AC-AC8a | Bans in pytest-family argv | PASS | check-banned `--test-steps=tests "--step=tests\|CMD"` gives rc=2 and the right `BANNED: <token> — <reason>` line for `./pytest -x`, `\pytest -x`, `'pytest' -x`, `python3 -m pytest -x`, `uv run pytest -x`, `coverage run -m pytest -x`, `python3 -mpytest -x`, `py.test -x`, `.venv/bin/pytest --lf`, `pytest >log -x`, `pytest 'unbalanced -x`, `pytest -xq`, `pytest -qk smoke`, `pytest -mslow`, `pytest -m"not slow"`, `time -p pytest -x`, `env FOO=1 pytest --maxfail=2`, `pytest --bail`, `pytest --exitfirst` and `pytest --cache-test-results`. `python3 -mpytest --reruns 2` (QA D13) gives rc=2 with `BANNED: --reruns — retries turn a failure into a pass`; at `f441d8d` the same call printed nothing. Clusters that must pass give rc=0: `pytest -rxXs`, `pytest -p no:x`, `pytest -W error::x` and `pytest --cache-clear`. |
| AC-AC8b | Other programs not scanned | PASS | check-banned `"--step=lint\|CMD"` gives rc=0 with no `BANNED` for `git commit -m x`, `tar -x`, `sort -k 2`, `go test -timeout 5m ./...`, `go test -mod=vendor ./...`, `go test -exec sudo ./...`, `make -C tools/pytest -k`, `make -C tools/jest -k`, `echo pytest -x` and `python3 -m pytest`. QA D12 and D15 are closed: at `f441d8d`, `--cmd=go test -timeout 5m ./...` printed `BANNED: -timeout — undeclared filter…` and `--cmd=make -C tools/jest -k` printed `BANNED: -k — …`. On HEAD, neither prints anything. |
| AC-AC8c | Honest `limit:` line | PASS | `go test -timeout 5m ./...` in a test step → rc=0, `limit: step tests runs no known runner; its flags are not scanned — declare bans in VERIFY_EXTRA_BANNED`. With `--runner="go test"` → `limit: step tests runs go test; …`. With `--runner=jest`, `jest --bail` in the lint step → `limit: step lint runs jest; …`. `pytest -q` → no line. In the scratch repo (below), the full gate printed the same line once for the test step. The record-warnings and verdict-unchanged clauses: `test_rt1_the_full_gate_records_the_limit_and_keeps_its_verdict` passes in the 194 subset. |
| AC-AC8d | Project bans | PASS | `--extra=--bail` with `npm test -- --bail` → rc=2, `BANNED: --bail — project-declared`. With `--bail=1` → `BANNED: --bail=1 — project-declared`. `--extra=--retries` with `echo hi && cargo nextest run --retries 2` → rc=2. A runtime `--bail` → rc=2. |
| AC-AC15 | No conf, real commands stay GREEN | PASS | Scratch repo `scratchpad/ac15`: a copy of HEAD's `verify-full.sh` and `verify_record.py`, with no conf. Its STEPS are `make -C tools/jest -k …; sort -k 2 /dev/null`, `git commit -m x --dry-run …` and `tests\|go test -timeout 5m -mod=vendor ./... && echo out > artifact.log` (a stub `go` on PATH). The framework's own five steps are stubbed, as the tests do. `bash scripts/verify-full.sh` → `EXIT GATE GREEN`, exit=0, and `artifact.log` was left untracked. The gate added only time, `counts: not configured…`, `tree changed during the run (not enforced: no scripts/verify.conf)` and `record:`. This is the exact QA D12 shape that failed re-test 1. `test_ac15_a_project_as_filled_in_today_stays_green` and `test_d6_a_project_as_filled_in_today_with_realistic_commands_stays_green` pass. |
| AC-AC19 | Allow-list scope | PASS | check-banned `--allow=…`: `--ignore=tests/slow\|nightly` → rc=0, `declared filter: --ignore=tests/slow — nightly`. `--ignore=tests/slow` (no reason) → rc=2, `BANNED: allow-list entry without a reason: --ignore=tests/slow`. `--ff\|x`, `--reruns 2\|x`, `-x\|x`, `--sw\|x` and `--lf\|x` → rc=2, `BANNED: <token> can never be allow-listed`. `--durations\|x` and `-p no:randomly\|x` → rc=2, `… — only -m, -k, --deselect, --ignore and --ignore-glob can be declared`. A declared `-k smoke` passed at runtime → `BANNED: -k — filter used to reach green`. |
| AC-AC5 (added clause) | Duplicate test label | PASS | Scratch repo with conf `STEPS=("tests\|pytest -q" "tests\|pytest -q")`, `VERIFY_TEST_STEPS="tests"` → exit=1, `EXIT GATE RED — duplicate test step label: tests; give each test step its own label`, and no step lines were printed. |
| AC-AC6 (clauses) | Fast-tier counts wording | PASS | `test_d9_a_failing_collect_in_the_fast_tier_says_so`, `test_d9_without_a_collect_command_the_fast_tier_says_ran_n_of_unknown` and `test_a_collect_command_that_fails_is_red` pass (194 subset). No independent probe. |
| AC-AC20 | Conf syntax error refused | **FAIL** | The shape the tests pin (a stray `fi`) is caught: `/bin/bash -n` gives rc=2 for an unterminated `if` or an unterminated quote. **An unclosed array is not caught.** `/bin/bash -n` (GNU bash 3.2.57, the only bash on this Mac) gives rc=0 for `X=(` and for `STEPS=( "tests\|echo a"` at EOF, while sourcing the same file fails with `unexpected EOF while looking for matching ')'`. Full-tier repro in `scratchpad/ac15`: conf `STEPS=(` / `  "tests\|go test ./..."` / `VERIFY_TEST_STEPS="tests"` / `VERIFY_COLLECT_CMD="echo 5"` (the `)` is missing), committed. `bash scripts/verify-full.sh` → **exit=0, `EXIT GATE GREEN`**, with `counts: not configured — executed == collected NOT checked` and no `failed to load` line. The conf's test-step and count settings were silently dropped. That is the partial load the `bash -n` check exists to stop (comment at `scripts/verify-full.sh:59-61`). Fast tier, `scratchpad/fast2`: conf `LINT=(true)` / `TEST=(echo 3 passed` / `VERIFY_COLLECT_CMD="echo 5"` → exit=0, `FAST VERIFY INCOMPLETE …`. The spec requires `FAST VERIFY REFUSED — scripts/verify.conf failed to load (syntax error)` with exit 2. The false-last-line clause passes: conf `X=1` / `[ -n "${NOPE:-}" ] && Y=2` printed no `failed to load`. |
| AC-AC21 | Hashed runner id | PASS | The record from this run's exit gate (`.verify/runs/20261022T074303Z-82131/record.json`) has `runner.id` = `local:4017c78e26d1`, equal to `local:` + sha256(hostname)[:12] computed in Python. Neither the full hostname nor its first label appears in the record file. |
| AC-AC22 | Separate prune slots | PASS | `test_d11_fast_runs_never_evict_a_full_record` passes (194 subset). The reverse direction is still unpinned, as am2 itself states. |
| AC-AC23 | Tree hash by content | PASS | `test_rt1_a_same_size_edit_with_an_unchanged_mtime_is_hashed_by_content` passes (194 subset). Not run repeatedly. |
| AC-AC24 | Retry-plugin flags banned | PASS | check-banned on HEAD: `pytest --force-flaky`, `pytest --max-runs 3`, `pytest --max-runs=3`, `python3 -m pytest -q --force-flaky` and `PYTEST_ADDOPTS=--max-runs=2 pytest` → rc=2, `BANNED: <token> — retries turn a failure into a pass`. `--runtime=--force-flaky` → rc=2. `--allow=--force-flaky\|flaky suite` and `--allow=--max-runs\|x` → `BANNED: <token> can never be allow-listed`. `pytest --flake-runs 3` → rc=0 (L7). Red-first confirmed: `git show e436d1f:scripts/verify_record.py` run as check-banned gives rc=0 for `pytest --force-flaky` and for `pytest --max-runs 3`. |
| am2 docs | Limits L1 to L8, ADAPTERS section | PASS | `scripts/verify.conf.example:140-150` names wrappers, variables, eval/-c, `pypy3`/`py`, `pytest3`, verify-fast runtime arguments and `--flake-runs`. `doc/framework/ADAPTERS.md:142` has the heading. `python3 -m pytest tests/framework/test_doc_contracts_ac.py tests/framework/test_neutrality.py -q -p no:cacheprovider` → `15 passed`. QA pins `tests/hooks/test_regression_verify_tiers_qa.py` → `16 passed` (18 minus the 2 retired). |
| Exit gate | `scripts/verify-full.sh` | RED (outside A+C) | `verify-handoff.sh --status` → `not opted in`. `bash scripts/verify-full.sh` → exit=1, `EXIT GATE RED (exit 1).` `OK hooks (250s) 1303 passed`. `FAIL ci-examples (6s) (exit 1)`. Scar-forge, coordinator and framework OK. Lint, format and tests are `TODO … verified NOTHING`. Every ci-examples failure is a `test_gate_3_*` test that hits placeholder-shaped text in `doc/qa/` reports (`REVIEW-bugfix-gate3-worktree.md`, `QA-bugfix-gate3-worktree.md`, and the untracked `REVIEW-verify-tiers-G-polling.md`). `python3 -m pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider -k "not gate_3"` → `18 passed`. This is not an A+C defect; see Parked. |

#### Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| Medium | **AC-AC20: an unclosed array in `scripts/verify.conf` passes the syntax check, and the conf loads only partly.** Bash 3.2's `-n` returns 0 for an array left open at EOF, while `.` stops with `unexpected EOF while looking for matching ')'`. The source runs as `. scripts/verify.conf \|\| true`, so the failure is swallowed. In the full tier, a conf whose `STEPS=(` lacks its `)` drops everything after it (`VERIFY_TEST_STEPS`, `VERIFY_COLLECT_CMD`), and the gate ends `EXIT GATE GREEN`, exit 0. In the fast tier, the same shape gives exit 0 with `FAST VERIFY INCOMPLETE` instead of `FAST VERIFY REFUSED …` and exit 2. A missing `)` is an ordinary typo, so it is inside the mistakes threat model. Repro: the AC-AC20 row above. The existing pins use only a stray `fi`, which bash 3.2's `-n` does catch, so they stayed green. One possible direction (the author decides): treat sourcing stderr that contains a parse error (`syntax error`, `unexpected EOF`) as a load failure, or source in a subshell first and check for it. Add a pin for `X=(` at EOF in both tiers, and show it red first. | `scripts/verify-full.sh:62-67`, `scripts/verify-fast.sh:33-39` | ai-engineer. **Routing note:** am2's AC-AC20 says "The check is `bash -n`", and the code does exactly that. On bash 3.2 that mechanism cannot meet the AC's Then clause, so any fix adds a check the approved wording does not name. If the coordinator reads "the check is `bash -n`" as exclusive, this needs a spec ruling (ba-sa, then the owner) before the engineer acts. |

#### Hostile inputs tried

- `python -m pytest --LF` → rc=0. Not a bypass: pytest options are case-sensitive, so pytest rejects `--LF` itself.
- `PYTEST -x` in a test step → rc=0 with `limit: step tests runs no known runner…`. On a case-insensitive macOS filesystem this can still run pytest. It falls under declared limit L4 (name tricks), is stated, and is not a FAIL.
- `pytest -q && go test ./...` in a test step → rc=0 and no limit line, because pytest was found, so the step counts as scanned. That matches AC-AC8c's wording.
- `pytest --lf ` (trailing space), `pytest >log -x` and an unbalanced single quote → all refused.
- Conf whose last line is false (`[ -n "${NOPE:-}" ] && Y=2`) → loads and prints no `failed to load` (AC-AC20's second clause holds).
- Conf `[ -n "$NOPE" ] && Y=2` with NOPE unset → `NOPE: unbound variable` on stderr, and the conf is cut short. This is the same silent-partial-load family as the defect above. AC-AC20's example names `"$X"` without saying whether X is set, so it is noted here and not filed separately.

#### Parked (outside the criteria in scope, rule 4)

- **Stale QA record.** `doc/qa/QA-verify-tiers-AC.md` still ends at its re-test 1 FAIL result (AC-AC8, AC-AC15), with no am2 re-test note. Am2 assigns that note to qa ("D14 is retired by this amendment, not fixed"). Yet `d259245`'s message says "Passed QA re-tests under approved amendment am2". The record and the commit disagree. For the coordinator.
- **Exit gate red from gate-3 report text.** Committed and in-flight `doc/qa/` reports quote placeholder-shaped text, which the gate-3 tests in `tests/ci/test_ci_examples.py` scan. The owner is the gate-3 bugfix line, not A+C. At review time those two files had uncommitted edits by another run (`git status`: ` M doc/qa/QA-bugfix-gate3-worktree.md`, ` M doc/qa/REVIEW-bugfix-gate3-worktree.md`). After those edits, a re-run of `python3 -m pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider` gave `2 failed, 28 passed`, and every remaining hit is in the untracked `doc/qa/REVIEW-verify-tiers-G-polling.md` (lines 37, 39 and 60). This file has no hit: `grep -nE '<[A-Z_]{3,}>'` finds nothing.
- **Not an off-ramp for the FAIL above.** The input is an ordinary typo (a missing `)`), which is inside the mistakes threat model. bash 3.2 is the scripts' own declared target (`scripts/verify-full.sh:77`: "bash 3.2 also dies on …"). So this is a defect, not a hostile environment. The LIMIT line below is offered **only if the coordinator rules otherwise**: "The conf syntax check uses the running bash's `-n`; bash 3.2 does not flag an array left open at EOF, and such a conf loads partly."

## Approval history

- **2026-10-22 — round 3 drafted.** reviewer (run ID not visible to this run; the coordinator fills `Reviewer-run:`), from am2 AC-AC20, the uncommitted `verify-handoff.sh` and test diff in worktree `agent-a0bb7774512557e28` on `0fd71b6`, and probes in scratch copies. The author's conversation was not read.
- **2026-10-22 — round 2 drafted.** reviewer (run ID not visible to this run; the coordinator fills `Reviewer-run:`), from am2 AC-AC20, the uncommitted diff in worktree `agent-a0bb7774512557e28` on `0fd71b6`, the tests, and probes through the test module's helpers. The author's conversation was not read.
- **2026-10-22 — round 1 drafted.** reviewer run `a4095c6cb10bfbe75`, from am2, the base spec's AC-AC15, `d259245` as merged into HEAD `ef1f717`, the tests, and probes run in scratch repos. The author's conversation was not read.
