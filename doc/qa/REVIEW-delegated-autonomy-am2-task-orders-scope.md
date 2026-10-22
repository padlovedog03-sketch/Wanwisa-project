# Review: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Author-run: a652078d3d8838f6b
Reviewer-run: a10b15a401c97dfa2
Date: 2026-10-22

## Verdict: PASS

Increment 2 (Log) meets AM2-AC2, F-AC2, AM2-AC3 (a), AM2-AC8 for `log`/`verify-log` and A-AC8. The new tests are red on HEAD (139 failed) and green with the change (312 passed). The exit gate is green on its configured steps. There is one stray whitespace edit to fix before commit (see Defects, Low, not blocking).

## Increment 2 — Log

### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md (increment plan row 2; AM2-AC2, AM2-AC3 (a), AM2-AC8, the `scripts/verify-fast.sh` and `test_*` rows of the files table, AM2-ADR-2, D-L11) and doc/specs/SPEC-delegated-autonomy.md (F-AC2, C-AC1, C-AC2, A-AC8 wording).
- Change: the author's uncommitted files in worktree `.claude/worktrees/agent-a652078d3d8838f6b`, on the same HEAD as this branch (d535bfb). I ran `diff -rq` over the two trees. Exactly 8 files differ: `scripts/autonomy.py`, `scripts/verify-fast.sh`, `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml`, `tests/framework/test_commit_msg_owner_trailer.py`, `tests/hooks/test_guard_always_human.py`, `tests/ci/test_ci_examples.py`, and the new `tests/framework/test_decision_log.py`. A `.verify/` run directory is also present, which is a run artefact.
- Scratch copy: reviewer scratchpad `scr/` = this worktree's HEAD (rsync, `git init`, committed as base). First the 4 test files, then the 4 production files. The author's worktree was only read, never written.
- Not read: the author's conversation. The brief's description of the change was checked against the diff.

### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| Red-first | New tests red before the change | PASS | Scratch copy with only the author's 4 test files on HEAD: `python3 -m pytest tests/framework/test_decision_log.py tests/framework/test_commit_msg_owner_trailer.py tests/hooks/test_guard_always_human.py tests/ci/test_ci_examples.py -q -p no:cacheprovider` → `139 failed, 173 passed in 45.08s`. The failures include every tamper case (`edited`, `deleted`, `swapped`, `inserted-before-end`, `emptied`), `test_an_unknown_base_fails_closed`, every AM2-AC3 (a) case under `order` and `mandate`, the 3 AM2-AC8 allow cases, and the gate-6 CI cases. F-AC2 check: I put HEAD's `scripts/autonomy.py` back into the scratch copy and ran `python3 -m pytest tests/framework/test_decision_log.py -q -rA -p no:cacheprovider` → `110 failed, 4 passed`. Every F-AC2 case is red, and each one asserts `reverse: missing or not one action`, not only the exit code. The 4 green cases are `test_malformed_input_exits_2_without_a_traceback[*]`, which are green for the wrong reason (Parked P8). After restoring the author's file, the brief's command again gave `312 passed in 48.55s`. |
| Brief's verify command | — | PASS | The same command with all 8 files → `312 passed in 48.67s`. |
| AM2-AC2 (writer) | `log` appends one JSON line; requires the 11 fields, no `prev`; exit 2 naming the field; 13+ digits refused | PASS | `bash probes/probe_log.sh` (a throwaway repo): a full entry → rc 0, appended. Missing `why` → rc 2 `log: missing field: why`. A `prev` field is neither required nor refused (rc 0). `why: "id 1234567890123"` → rc 2 `why: looks like an identifier — describe the shape, not the value`. 12 digits → rc 0. 13 Thai digits → rc 2. 13 digits in `options[1]` → rc 2. Not JSON, a JSON list or `null` → rc 2. `NaN` in `options` → rc 2 `options: a list of text`. |
| AM2-AC2 (verify-log) | Exit 1 naming the line on any removed or changed line; green on appends at the end | PASS | `test_decision_log.py` tamper cases (each planted red, then reverted green) pass in the 312. Probe: same commit → rc 0. Base without a log → rc 0. Empty base, a tree object or an unknown ref → rc 2 `… is not a commit` (fails closed). An edited last line → rc 1 naming a line. A file that ends without a newline and then gets an append is red on line 1, which matches `git diff` (see the probe in AM2-AC3 (a)). |
| AM2-AC2 (CI) | The same command runs as a step in both `ci-examples/*.yml`, identically | PASS | `git diff -- ci-examples`: gate 6 has the same 5-line script in both files (`set -euo pipefail`, base from `GITHUB_BASE_REF`/`SYSTEM_PULLREQUEST_TARGETBRANCH`/`main`, `git fetch`, `verify-log --append-only "$(git merge-base "origin/$base" HEAD)"`). `test_gate_6_scripts_are_byte_identical` passes. The tests run the gate-6 script itself under `github`, `azure-pr` and `azure-push` environments, against a base that moved on after the fork. They prove the PR path. The `azure-push` case runs a detached non-main candidate, which a main-only push trigger never produces (Parked P7). Both files already check out with `fetch-depth: 0`/`fetchDepth: 0`, so `merge-base` has the history it needs. The gate-count test went from 5 to 6, which is the spec adding a gate, not a changed old case. |
| F-AC2 | `approval`/`decision`/`provisional`/`merge` with a `reverse` outside the one-action grammar → exit 2 `reverse: missing or not one action` | PASS | Probe: `revert abc1234` → 0. `revert abc1234; rm -rf x` → 2. A trailing newline → 2. `none:   ` (blank reason) → 2. Missing → 2. A list → 2. Upper-case sha → 2. Each message is `log: reverse: missing or not one action`. |
| AM2-AC3 (a) | A log commit that only appends needs no trailer under a live order (a new file counts); anything else is still refused, naming AH5 and the path | PASS | In the 312, under both `order` and `mandate`: a new log commits, an append commits, and changed, removed, swapped, inserted-before-the-end and deleted are refused with `always-human item AH5: doc/decisions/decision-log.jsonl is protected`. The index is judged, not the worktree. `doc/decisions/other.jsonl` and an append carrying `scripts/autonomy.json` are still refused. My own scratch probes (`test_zz_reviewer_probe.py`, deleted after the run, `4 passed`): an append plus an unprotected `README.md` commits; emptying the log is refused; an append after a last line with no newline is refused (same as `git diff`). |
| AM2-AC8 | The guard allows `log` and `verify-log` under an order; an undefined subcommand stays AH5 | PASS | `AGENT_SUBCOMMANDS` now also holds `log` and `verify-log`, and nothing else was added (`approve-under`, `close-order` and the rest wait for their increments). In the 312: `test_the_shipped_log_subcommands_are_allowed_under_an_order` (3 spellings, including `-I` and a `$(…)` base) and `…_without_autonomy` pass. `grant` and `close-order` are refused as AH5. |
| A-AC8 | No live autonomy → nothing changes | PASS | `check_commit` still returns `[]` before the carve-out when `state == "inactive"`. Scratch probe `test_inactive_project_edits_log_freely`: with no `scripts/autonomy.json`, rewriting a log line commits. In a project with no log, gate 6 is green (`test_no_log_on_either_side_is_green`). The exit gate below shows existing hook and CI tests unchanged and green. |
| Out-of-Files edits | The CI YAML and `verify-fast.sh` are what the spec asks | PASS | The spec's files table lists `scripts/verify-fast.sh` ("routing lines for new scripts and tests … each"), and increment row 2 says "CI step in both YAML files". The routing change only adds `test_decision_log` and `test_commit_msg_owner_trailer` to the existing case that runs `tests/framework/ tests/hooks/`. |
| Exit gate | `scripts/verify-full.sh` | PASS | Run on the scratch copy → `verify-full rc=0`: hooks `1489 passed`, ci-examples `43 passed`, scar-forge OK, coordinator `174 passed`, framework OK (memory 0 problems). Lint, format and tests are the template's `TODO` placeholders ("this step verified NOTHING"), the same as on HEAD. |

### Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| Low (not blocking) | A whitespace edit on a line this increment does not need: `entries, _ = verify_approvals.load_registry(…)` became `entries, _ =verify_approvals.load_registry(…)`. It changes no behaviour, but it breaks the surgical-change rule and the file's formatting. Restore the space before committing. | `scripts/autonomy.py`, `check_commit`, the `load_registry` line just after the new carve-out | ai-engineer (author run a652078d3d8838f6b) |

### Hostile inputs tried (`log` unless stated)

- `kind: "Approval"` (a case variant) with `reverse: "whatever"` → rc 0. The grammar check matches `kind` exactly. See Parked P1.
- `why: ""` → rc 0. "Required" is checked as "not null", not "not empty". See Parked P2.
- `why: "1-2345-67890-12-3"` (a national-ID shape with dashes) → rc 0. The spec says "a run of 13 or more digits", so this is spec-literal. See Parked P3.
- `why` containing U+2028 → rc 0 and written raw (`ensure_ascii=False`). Python's `splitlines()` then counts 9 lines where `wc -l` counts 8, and after an edit of the last line `verify-log` named "line 9" instead of 8. It is still red, so only the line number is off. See Parked P4.
- `verify-log --append-only ""`, a tree object, `nosuchref` → rc 2 (fails closed).

### Parked (outside the threat model, or tests could be stronger; for the coordinator)

- **P1 — `kind` is not checked against a list.** A sloppy `Approval` or ` approval` skips F-AC2's grammar. I expect increment 4's validator (not built yet) to match `kind: approval` exactly, so it would not count this entry. That is an expectation, not something I measured. A future fix is to refuse an unknown `kind`, or to normalise it.
- **P2 — empty-string fields count as present.** C-AC1 says "lacks", which the code reads as missing or null.
- **P3 — the identifier check misses dashed or spaced 13-digit IDs**, and checks only `options`/`choice`/`why`. Both follow the spec's wording. Widening them would be a spec change.
- **P4 — line numbers drift on U+2028/U+2029/U+0085 inside a value.** `appended_only` splits with `str.splitlines()`. Splitting on `"\n"` only would match git. Detection is unaffected.
- **P5 — gate 6 runs the candidate's own `scripts/autonomy.py`.** Gate 2 runs the base branch's copy of its gate code, but gate 6 does not. A candidate that broke `verify_log` would judge itself with the broken copy. Deliberate tampering is outside the brief's threat model. An accidental break is caught by `test_decision_log.py` in the same CI run.
- **P6 — the commit carve-out reads a failed `git show HEAD:…` as "no log yet".** On any git error the old log would read as empty, and any content would count as an append. I found no input that triggers this. It is a fail-open path, noted for completeness. CI gate 6 would still catch an edit to an earlier line.
- **P7 — on a push to `main`, gate 6 compares HEAD with itself.** `GITHUB_BASE_REF` is empty on push, so `base=main`, and `merge-base origin/main HEAD` is HEAD. The step is always green there. The PR run is where it bites. The spec defines no base for push, and the PR path is tested.
- **P8 — 4 malformed-input tests are green before the change** (`test_malformed_input_exits_2_without_a_traceback[not-json|a-list|options-not-a-list|choice-not-text]`). They assert only exit 2 with no traceback, and on HEAD argparse rejects the unknown `log` subcommand with exit 2. Asserting the `log:` message would make them red-first. These are field checks, outside AM2-AC2's RED-FIRST clause (tamper). Tests could be stronger.
- D-L11 (forged appended lines) is the spec's own stated limit, unchanged.

## Review history

### Increment 1, round 3 (reviewer run a937e09bb10826b24) — result PASS

Round 3 (delta review of the round-2 rework): both round-2 regressions are closed, both QA defects stay closed, and in the round-2 probe set the only case that round 1 refused and round 3 allows is `pushd WT; popd; git commit`. That spelling is a declared limit, so it is Parked (R1), not a defect.

#### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md (increment plan row 1, F-AC1 `git commit` half). The round-2 section below has the two defects this round has to close.
- Change: the uncommitted files in worktree `.claude/worktrees/agent-ab74ef54c3710742d`. I ran `diff -q` on each file against this branch's HEAD (3d5fe2c). `scripts/autonomy.py`, `.claude/hooks/guard_bash.py` and `tests/hooks/test_guard_always_human.py` differ. `tests/framework/test_autonomy_items.py` is identical. Against the round-2 code (the round-2 reviewer's scratch copy `rvf2-ab1fa/r2`), `guard_bash.py` is identical, and only `scripts/autonomy.py` and the test file changed.
- Scratch copies under the reviewer scratchpad `rvf3-a937e/`:
  - `base` = `git archive HEAD`.
  - `r1` = the round-1 code, copied from `rvf2-ab1fa/r1`.
  - `r2` = the round-2 code with the round-3 test file, for red-first.
  - `r3` = base plus the author's 3 files.
- The author's worktree was only read, never written. I did not read the author's conversation. The brief's summary of the change was checked against the diff.

#### What changed (r2 → r3, `scripts/autonomy.py` `protected_commit` only)

- The walk now runs over the raw tokens instead of `segments()`. It applies `_strip_command_position` and `_split_redirects` to each command, the same steps `segments()` takes.
- A `cd`/`pushd` moves `here` only when `moved.is_dir()`.
- A `(` saves `here` and a `)` restores it. Each character is checked, so a combined token such as `);` also counts.
- The branch is now `current_branch(target) or current_branch(cwd)`, so a target whose branch cannot be read is judged as the starting cwd.
- The docstring now names the safe-direction rules. It also lists these declared limits: `pushd`/`popd` stacks, `cd -`, `bash -c`, `--git-dir`/`--work-tree` and backticks.

#### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| (a) Round-2 Defect 1 | A `cd` to a missing directory must not move the judged directory | PASS (closed) | `python3 rvf3-a937e/probe.py`: the round-2 probe set, re-run against r1, r2 and r3 guards in real repos, with a live order and `HOME` and `APPROVAL_LOG` in a temp dir. Hook cwd on `main`, r1/r2/r3 rc: `cd /nonexistent-rvf2; git commit -m x` 2/0/**2** F-AC1. Variants: `cd /nonexistent-rvf2 && git commit` 2/0/2 · `cd nosuchsub; git commit` 2/0/2. |
| (a) Round-2 Defect 2 | A `cd` inside `( … )` must not leak past the `)` | PASS (closed) | Same probe: `(cd WT && git commit -m x); git commit -m y` 2/0/**2** F-AC1. Variants: `(cd WT; git commit); git commit` 2/0/2 · `(cd WT && git commit) && git commit` 2/0/2 · `((cd WT); git commit)` 2/0/2. The scope does not overshoot: `(cd WT && git commit)` alone 2/0/0 (allowed, the commit lands in the worktree) · cwd = worktree, `(cd MAIN && git commit)` 0/2/2 · cwd = worktree, `(cd MAIN); git commit` 0/2/**0** (correct: that commit runs in the worktree, and r2 refused it wrongly). |
| (b) QA Defect 1 stays closed | Hook cwd on `main`, commit into a `wip/x` worktree is allowed | PASS | Same probe, r3 = 0 on every row: `cd WT && commit` · `cd WT; commit` · `git -C WT commit` · `cd ../a-wt && commit` · `pushd WT && commit` · `cd -P WT` · `cd -- WT` · `cd 'WT'` · `git -c user.name=t -C WT commit` · `sudo git -C WT commit`. |
| (b) QA Defect 2 stays closed | Unborn `main` + live autonomy → `git commit` refused | PASS | Same probe, unborn `main`, r3: `git commit` 2 F-AC1 · `git add . && git commit` 2 F-AC1 · `git merge feature/x` 2 AH3 · `git rebase feature/x` 2 AH3 · `git status` 0. |
| (c) Round-1 refusals in the round-2 probe set | No case that round 1 refused is allowed now, except through a declared limit | PASS | Same probe, 59 rows, `unexpected=0`. Every r1 = 2 row is 2 on r3 (plain commit · `cd sub` · `git -C .` · `git -C sub` · `git -C WT/../a` · `cd ../a-wt && git -C ../a` · `cd WT && commit; cd ../a && commit` · `add && commit` · `merge` AH3 · `--work-tree=WT` · `--dry-run` · both regression rows), except for two groups. The first is the rows meant to be allowed (commit into the worktree, QA Defect 1). The second is `pushd WT; popd; git commit -m x` 2/0/0, which uses a declared spelling (Parked R1). `cd WT && cd - && git commit` is now 2/0/**2**: `cd -` resolves to `$HOME`, which is not a repo in the probe, so the fallback judges the commit as cwd (`main`). The fix is incidental, and it still depends on `$HOME` (R2 stays parked). |
| Reverse direction and A-AC8 | Worktree → `main` refused; no live autonomy → nothing changes | PASS | Same probe. Cwd = worktree: `cd MAIN && commit` · `cd MAIN; commit` · `git -C MAIN commit` · `cd ../a && commit` · `pushd MAIN && commit` → r3 2 F-AC1. Plain `git commit` → 0. Empty registry or never opted in (9 rows): r1 = r2 = r3 = 0. Detached HEAD and outside a repo: 0. `echo 'cd WT && git commit'` 0. |
| Red-first | New tests red against the round-2 code | PASS | `python3 -m pytest tests/hooks/test_guard_always_human.py tests/framework/test_autonomy_items.py -q -p no:cacheprovider` on `r2` (round-2 code plus the round-3 test file) → `7 failed, 184 passed in 14.24s`. The 7 are the 6 `test_a_commit_that_does_not_land_in_the_worktree_is_judged_on_main[*]` (3 missing-dir spellings, including `git -C /nonexistent-f-ac1`, and 3 subshell spellings) and `test_a_failed_cd_does_not_move_a_relative_git_dash_c`. The other new test, `test_a_commit_inside_a_subshell_cd_to_the_worktree_is_allowed`, is green on r2. That is correct: it is an allow pin that keeps the scope fix from overshooting. |
| Brief's verify command | — | PASS | Same command on `r3` → `191 passed in 14.87s`. |
| Exit gate | `scripts/verify-full.sh` | PASS | `bash rvf3-a937e/vfull.sh` runs on `r3`, made a git repo for the run → hooks `1481 passed`, ci-examples `36 passed`, scar-forge OK, coordinator `174 passed`, framework OK (memory 0 problems), `verify-full exit=0`. Lint, format and tests are the template's `TODO` placeholders ("this step verified NOTHING"), the same as on HEAD. |

#### Defects

None.

#### Observations (no action required)

- **The fallback refuses some commits that would never land on `main`.** `current_branch(target) or current_branch(cwd)` judges a commit as `main` when its target is not a repo, for example `cd /tmp && git commit` from a `main` checkout. Git would fail there anyway, so nothing lands on `main`. This is the safe direction, and the docstring states it ("a target whose branch cannot be read is judged as the starting `cwd`").
- **The walk repeats `segments()` instead of calling it.** The new loop duplicates `segments()`'s splitting so that it can see the `( )` tokens. `segments()` is unchanged, so the two can drift apart if one is edited later. This is a code-quality note, not a defect.

#### Parked (for the coordinator)

- R1 (`pushd`/`popd` stacks) stays parked. It is declared in the docstring, and in the round-2 probe set it is the only round-1 refusal that is still allowed.
- R2 (`cd -`) is parked, and the probe now refuses it only by accident (see (c)). R3 (status read at the hook cwd) is unchanged. Round-1 P1, P3 and P4 are unchanged.


### Increment 1, round 2 (reviewer run ab1fa0c0beac00430) — result FAIL

Both QA defects were closed, but the rework lost coverage in the refused half of F-AC1. Round 1 refused two commits that land on `main` by plain mistake, and round 2 allowed them: `cd` to a missing directory followed by `; git commit`, and `( cd` into the worktree `… ); git commit`.

#### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md, increment plan row 1 (F-AC1 `git commit` half, `guard_bash.py` only). The F-AC1 and A-AC8 rows are in doc/specs/SPEC-delegated-autonomy.md. QA's two defects are in doc/qa/QA-delegated-autonomy-am2-task-orders-scope.md (commit 17ce083).
- Change: the uncommitted rework in worktree `.claude/worktrees/agent-ab74ef54c3710742d`. I ran `diff -rq` of that tree against this branch's HEAD (17ce083), excluding `.git` and caches. Exactly 3 files differ: `scripts/autonomy.py`, `.claude/hooks/guard_bash.py` and `tests/hooks/test_guard_always_human.py`. There is also the untracked `.verify/` run folder, plus the two doc/qa files that HEAD has and the older base does not. `tests/framework/test_autonomy_items.py` is identical to HEAD.
- Round-1 code: round 1's reviewer and QA left copies of it in their scratch folders (`rvf1-a0705/new`, `qaf1-1792671252/new`). I ran `cmp` on the 3 files across the two copies, and they are identical.
- Scratch copies under the reviewer scratchpad `rvf2-ab1fa/`:
  - `base` = `git archive HEAD`.
  - `r1` = base plus the round-1 files.
  - `r2` = base plus the author's 3 files.
  - `r1t` = r1 with r2's test file.
- The author's worktree was only read, never written.
- Not read: the author's conversation. The brief's summary of the rework was checked against the diff, not relayed.

#### What changed

- `protected_commit(command, config, cwd)` (`scripts/autonomy.py:817`) now walks the segments. A `cd`/`pushd` moves a running `here`, and `git -C <dir>` moves the target. The branch is read at the target with `current_branch(target)` (line 847).
- `current_branch` (line ~945) tries `git rev-parse --abbrev-ref HEAD` first. When that fails or prints nothing, it falls back to `git symbolic-ref --short HEAD`.
- `guard_bash.py` `_apply_core` passes `cwd` instead of the hook-cwd branch.

#### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| QA Defect 1 (Medium) | Hook cwd on `main`, commit into a `wip/x` worktree is allowed | PASS (closed) | `python3 rvf2-ab1fa/probe.py` (real repos, live order, `HOME` and `APPROVAL_LOG` in a temp dir). Every row is r1 → r2: `cd WT && git commit` 2→0 · `cd WT; git commit` 2→0 · `git -C WT commit` 2→0 · `cd ../a-wt && git commit` 2→0 · `pushd WT && git commit` 2→0 · `cd -P WT` 2→0 · `cd -- WT` 2→0 · quoted `cd 'WT'` 2→0 · `git -c user.name=t -C WT commit` 2→0 · `sudo git -C WT commit` 2→0. |
| QA Defect 2 (Low) | Unborn `main` + live autonomy → `git commit` refused | PASS (closed) | Same probe, unborn `main` repo (`git init -b main` and `scripts/autonomy.json`, no commits): `git commit -m x` 0→2 F-AC1 · `git add . && git commit` 0→2 F-AC1 · `git status` 0→0. |
| Reverse direction | Hook cwd in a `wip/x` worktree, commit aimed at `main` → refused | PASS | Probe, cwd = worktree: `cd MAIN && git commit` 0→2 F-AC1 · `cd MAIN; git commit` 0→2 · `git -C MAIN commit` 0→2 · `cd ../a && git commit` 0→2 · `pushd MAIN && git commit` 0→2 · plain `git commit` 0→0. This also closes the `cd`/`-C` forms of QA Parked Q1. |
| F-AC1 refused half, stays caught | Everything round 1 refused that still lands on a protected branch stays refused | **FAIL** | Probe, hook cwd on `main`, live order. These stayed refused (2→2): plain `git commit` · `cd sub && git commit` · `git -C . commit` · `git -C sub commit` · `git -C WT/../a commit` · `cd ../a-wt && git -C ../a commit` · `cd WT && git commit; cd ../a && git commit -m y` · `git --work-tree=WT commit`. **Regressed (2→0), and each commit lands on `main`:** `cd /nonexistent-rvf2; git commit -m x` · `(cd WT && git commit -m x); git commit -m y` · `cd WT && cd - && git commit -m x` · `pushd WT; popd; git commit -m x`. See Defects 1–2 and Parked R1–R2. |
| Symbolic-ref fallback, effect on the merge/rebase rule (AH3) | Change in the safe direction only, no test broken | PASS | Probe: unborn `main` + live order: `git merge feature/x` 0→2 AH3 · `git rebase feature/x` 0→2 AH3 (now refused, the safe direction). Unchanged: detached HEAD `git merge` 0→0 and `git commit` 0→0 (rev-parse succeeds with `HEAD`, so the fallback is not reached) · outside a repo `git commit` 0→0 · `wip/x` `git merge main` 0→0 · `main` `git merge feature/x` 2→2 AH3. Unborn `main` with an empty registry: `git merge` 0→0, `git commit` 0→0. `current_branch` callers (`grep -rn "current_branch("`): only `protected_commit` and `guard_bash.py:388`; `.githooks` and `check_commit` do not call it. |
| A-AC8 (guard half) | No live autonomy → nothing changes | PASS | Probe, every row r1 = r2 = 0. Empty registry: `main` `git commit` · `main` `cd WT && git commit` · worktree `cd MAIN && git commit` · unborn `git commit` · unborn `git merge` · `main` `git merge`. Never opted in (no `scripts/autonomy.json`) + live order: `git commit` · `git -C . commit` · `git merge x`. |
| Red-first | New tests red against round-1 code | PASS | `python3 -m pytest tests/hooks/test_guard_always_human.py tests/framework/test_autonomy_items.py -q -p no:cacheprovider` on `r1t` → `7 failed, 176 passed in 13.07s`. The 7 are the 4 `test_a_commit_in_a_worktree_on_a_working_branch_is_allowed_from_main[*]`, the 2 `test_a_commit_aimed_at_main_from_a_worktree_is_refused[*]` and `test_a_commit_on_an_unborn_main_is_refused_under_autonomy`. The 3 new `absence-main` rows are green on r1. That is correct: they are regression pins that close round-1 P2 / QA Q2, not red-first tests. |
| Brief's verify command | — | PASS | Same command on `r2` → `183 passed in 13.36s`. |
| Exit gate | `scripts/verify-full.sh` | PASS (green; does not cover the 2 regressions) | Run on `r2` (made a git repo for the run) → hooks `1473 passed`, ci-examples `36 passed`, scar-forge OK, coordinator `174 passed`, framework OK, `verify-full exit=0`. The lint, format and tests steps are the template's `TODO` placeholders ("this step verified NOTHING"), the same as on HEAD. A green suite is not the verdict here: no test covers either regression row. |

#### Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| Medium | **A `cd` that fails moves the guard but not the shell.** If the `cd` destination does not exist (a typo), the shell stays in the `main` checkout. With `;`, the commit runs there. `protected_commit` moves `here` anyway, and then `current_branch(<nonexistent dir>)` hits `OSError` and returns `None`. `None` counts as "not protected", so the guard fails open. Repro: hook cwd on `main`, live order, `cd /nonexistent-rvf2; git commit -m x` → round 1 rc 2 F-AC1, round 2 **rc 0**. `rvf2-ab1fa/mech.py` confirms `current_branch(Path('/nonexistent-rvf2'))` → `None`. Fix direction: move `here` only when the destination is an existing directory (the shell's own behaviour). Also, do not let an unreadable target clear a commit that the starting cwd would refuse. | scripts/autonomy.py:836-838 (cd), :847 (`current_branch(target)`) | ai-engineer (`regression`) |
| Medium | **A subshell's `cd` leaks past its closing parenthesis.** `segments()` splits at `( )` but keeps no scope, so after `(cd <wt> && …)` the guard still thinks it is in the worktree. Repro: hook cwd on `main`, live order, `(cd WT && git commit -m x); git commit -m y`. The second commit lands on `main`: round 1 rc 2 F-AC1, round 2 **rc 0**. `mech.py`: `segments('(cd /x && git commit -m x); git commit -m y')` → `[['cd','/x'], ['git','commit',…], ['git','commit',…]]`, so the parentheses are gone. `(cd dir && cmd)` is a common agent idiom, so this is reachable by plain mistake. The docstring's declared limits name `bash -c`, `--git-dir` and `pushd` stacks, and not subshells. Fix direction: one simple safe option is to judge each `git commit` against both the starting cwd and the tracked `here`, and refuse if either is protected. Any new test must be red on the current r2. | scripts/autonomy.py:830-848 (`protected_commit` walk) | ai-engineer (`regression`) |

#### Hostile inputs tried (round 2; r1 → r2 rc, hook cwd on `main`, live order, unless stated)

- Correct after the rework: every row in the Criteria table above. `echo 'cd WT && git commit -m x'` 0→0 (a mention is not a run).
- Declared limits (docstring: `bash -c`, `--git-dir`, `pushd` stacks):
  - `pushd WT; popd; git commit` 2→0 (lands on `main`). Parked R1.
  - `git --work-tree=WT commit` 2→2 (still refused, correctly: HEAD is `main`'s).
- `cd WT && cd - && git commit` 2→0 (lands on `main`). `cd -` is skipped as an option, so it resolves to `~`, not to the previous directory. Parked R2.
- Hook cwd outside any repo, `cd MAIN && git commit` → 0→0. `status` is read at the hook cwd's project root, not the target's. This is not new in round 2. Parked R3.
- `git commit --dry-run` 2→2. Unchanged (QA Q3).

#### Parked (outside the threat model or declared; for the coordinator)

- **R1 — `pushd`/`popd` stacks.** `popd` is not tracked, so `pushd WT; popd; git commit` is judged at WT. The docstring declares this limit. It is a regression from round 1 (2→0), but only through a declared spelling.
- **R2 — `cd -`.** It resolves to `$HOME` instead of the previous directory. It is rare in agent commands. If the Defect 2 fix judges against the starting cwd as well, it closes this too.
- **R3 — status is read where the hook runs, not where the commit lands.** A session whose cwd is outside the opted-in project, running `cd <project on main> && git commit`, is allowed. The same was true in round 1, so this is the same family as QA Q1's evasion direction.
- Round-1 P1 (cherry-pick/revert/commit-tree/alias/`bash -c`), P3 and P4 are unchanged. P2 is closed by the new `absence-main` rows.

### Increment 1, round 1 (reviewer run a0705137a137aecbc) — result PASS, later failed by QA at 17ce083

Increment 1 (F1) refuses an agent `git commit` on a protected branch while autonomy is active, allows it on a working branch, leaves projects without live autonomy exactly as before, and the new refusal tests are red against the old code.


#### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md, row-5 increment plan row 1 (line 107: F-AC1 `git commit` half, `guard_bash.py` only, not `check_commit`); the approved F-AC1 and A-AC8 rows in doc/specs/SPEC-delegated-autonomy.md (lines 106 and 121).
- Change: the uncommitted diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d` over HEAD b50406e. `diff -rq` of that worktree against HEAD (excluding `.git`, caches) → exactly 3 files differ, plus the untracked `.verify/` run folder: `scripts/autonomy.py` (new `protected_commit`, +16 lines, nothing else changed), `.claude/hooks/guard_bash.py` (`_apply_core`, +9 lines), `tests/hooks/test_guard_always_human.py` (additions only). `.githooks/commit-msg` and `check_commit` are untouched.
- Not read: the author's conversation. Every result below was run in this review, on scratch copies (`old` = HEAD, `new` = HEAD plus the author's 3 files) under the reviewer's scratchpad `rvf1-a0705/`. The author's worktree was never written to.

#### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| F-AC1 (commit half, as amended) | Under a live mandate, order or absence, an agent `git commit` on `main`, `master` or a project-listed protected branch is refused with `work under autonomy happens on a branch or worktree`; on a working branch it is allowed; enforced in `guard_bash.py` only | PASS | `python3 -m pytest tests/hooks/test_guard_always_human.py tests/framework/test_autonomy_items.py -q -p no:cacheprovider` on `new` → `173 passed in 11.36s`. Probe (`probe.py`, old vs new guard, real git repos): `main`+mandate, `main`+order, `main`+absence → `git commit -m x` old=0 new=2 `rule F-AC1`; `feature/x`+mandate and a `wip/x` worktree of a `main` repo → old=0 new=0. Only the 3 files differ (`diff -rq`, above), so `.githooks/commit-msg` and `check_commit` are untouched. |
| A-AC8 (guard half) | With no live autonomy nothing changes | PASS | Probe, 25 commands each, every row old rc = new rc: `main` with no `scripts/autonomy.json` but a live mandate in the registry (e.g. `git commit -m x` 0→0, `git merge feature/x` 0→0, `git status` 0→0, `ls` 0→0); `main` opted in with an empty registry (same); `main` with the mandate revoked (same). Full exit gate below: existing `tests/hooks/` and `tests/ci/` all pass. |
| Red-first | New refusal tests red against the old code | PASS | Same pytest command on `old` with the author's test file → `12 failed, 161 passed`; the 12 are exactly `test_a_commit_on_a_protected_branch_is_refused_under_autonomy[*]` (3 commands × mandate-main, mandate-master, order-main, order-project-listed-branch). The allow tests (working branch, no live autonomy, never opted in, mentions) are green on both, as regression pins should be. |
| Exit gate | `scripts/verify-full.sh` | PASS | Run on `new` (made a git repo for the run) → hooks `1463 passed`, ci-examples `36 passed`, coordinator `174 passed`, scar-forge OK, framework OK, `verify-full exit=0`. lint/format/tests are the template's `TODO` placeholders ("this step verified NOTHING"), as on HEAD. |

#### The author's fail-open, against the guard's stated policy

The brief notes that F-AC1 fails open when the core raises. Checked with planted mutants (`failopen.sh`, a `raise RuntimeError` inserted into one core function, `main` + live mandate):

- `status` raises, old guard → `git merge feature/x` rc=0, `scripts/approve.sh x --by y` rc=2.
- `status` raises, new guard → `git commit -m x` rc=0, `git merge` rc=0, `approve.sh` rc=2.
- `protected_commit` raises, new guard → `git commit` rc=0, `git merge` rc=0, `approve.sh` rc=2.

This **matches** the stated policy. `guard_bash.py`'s `_check_always_human` docstring and its `except` say only the owner rule (AH5 owner scripts) survives a core failure, through the inline `_OWNER_FALLBACK` matcher; the module header says "Malformed input exits 0 — a guard that fails closed on its own bug would be worse". The always-human items (AH1–AH4) already fail open the same way, and F-AC1 now joins them. One side effect is noted below as P4.

#### Hostile inputs tried (`main` + live mandate unless stated; new guard)

- Refused (rc 2, F-AC1): `git commit --amend --no-edit`, `git commit -m x 2>&1`, `git commit -m x >/dev/null`, `env git commit`, `sudo git commit`, `/usr/bin/git commit`, `GIT_AUTHOR_NAME=a git commit`, `git --no-pager commit`, `git -C . commit`, `(git commit -m x)`, `git status; git commit -m x`, tab between words, `git commit -m 'git commit'`.
- Allowed (rc 0, correct): `echo git commit`, `git log --grep commit`, `git help commit`, `git status`, `ls`.
- Malformed `scripts/autonomy.json` (`{not json`) on `main` → status `unknown — treated as active`, `git commit` refused (fails closed).
- Detached HEAD at `main`'s commit → allowed (no branch moves; git reports `HEAD`).
- Branch `Main` (case variant) → allowed. Git branch names are case-sensitive, and the existing AH3 rule uses the same exact-name set.
- Not caught: `git commit-tree`, alias `git ci`, `bash -c 'git commit -m x'`, `git cherry-pick HEAD`, `git revert HEAD`. See Parked P1.

#### Defects

None.

#### Parked (outside increment 1's criteria; for the coordinator)

- **P1 — other commands that land a commit on `main`.** `git cherry-pick`, `git revert`, `git commit-tree`, aliases and `bash -c '…'` all exit 0 under a live mandate on `main`. F-AC1 names `git commit …` only, and the brief declares other shell spellings a stated limit (doc/memory/ease-of-use-over-strictness.md). `cherry-pick` and `revert` are the ones an agent could reach by plain mistake, not by evasion. Whether F-AC1 should name them is a spec question.
- **P2 — absence is not in the author's tests.** The parametrised refusal test covers mandate and order only. The probe shows absence is refused too (`main+absence` → rc 2 F-AC1), so behaviour is right but nothing pins it. One more `ids` row would.
- **P3 — a rejected project file drops the project-listed branch.** `{"project":"proj","protected_branches":["release"],"bogus":1}` is rejected by `load_config`, so `git commit` on `release` is allowed (`main`/`master` still refused). This matches how AH3 already behaves and the guard's message "the framework items still apply".
- **P4 — one new way to lose AH1–AH4 on a crash.** `protected_commit` runs before the always-human block. If it raised, that command's AH3 match would also go unenforced (mutant above: `git merge` rc 0). This is within the stated fail-open policy, and `protected_commit` only reuses `segments`/`_split_redirects`/`_git_subcommand`, which `command_matches` has already run on the same command. Low risk; noted for completeness.

## Approval history

- **2026-10-22 — drafted (increment 1, F1).** Reviewer run a0705137a137aecbc, from the spec, the author's uncommitted 3-file diff in worktree agent-ab74ef54c3710742d, and commands run on scratch copies. PASS.
- **2026-10-22 — round 2 (rework after QA FAIL at 17ce083).** Reviewer run ab1fa0c0beac00430, from the spec, the QA report, the author's uncommitted 3-file rework in worktree agent-ab74ef54c3710742d, and commands run on scratch copies (`rvf2-ab1fa/`). FAIL: the QA defects are closed, but 2 regressions appeared in F-AC1's refused half.
- **2026-10-22 — round 3 (delta after round-2 FAIL).** Reviewer run a937e09bb10826b24, from the spec, the round-2 section, the author's uncommitted 3-file rework in worktree agent-ab74ef54c3710742d, and commands run on scratch copies (`rvf3-a937e/`). PASS: both regressions are closed and both QA defects stay closed. In the round-2 probe set, the only round-1 refusal still allowed is the declared `pushd`/`popd` limit.
- **2026-10-22 — increment 2 (Log).** Reviewer run a10b15a401c97dfa2, from the spec, the parent spec's F-AC2/C-AC1/C-AC2/A-AC8 rows, the author's uncommitted 8-file change in worktree agent-a652078d3d8838f6b, and commands run on a scratch copy (`scr/`). PASS: red-first 139 failed on HEAD, 312 passed with the change, exit gate rc 0. One Low, non-blocking defect (a stray whitespace edit). P1–P8 are parked.
