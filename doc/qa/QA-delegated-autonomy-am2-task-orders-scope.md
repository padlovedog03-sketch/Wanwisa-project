# QA Report: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Date: 2026-10-22

## Verdict: PASS

Increment 1 (F1), re-test 2: F-AC1 (commit half) and A-AC8 (guard half) both pass. Both defects from the first QA run are closed. A commit into a `wip/x` worktree is now allowed when the hook's cwd is on `main`, and a commit on an unborn `main` is now refused under autonomy. The reverse direction (a worktree cwd committing into `main`) is refused. With no live autonomy, behaviour is unchanged. The first run's FAIL is kept below as history.

## Increment 1 — F1

### Scope and provenance

- Tier 1. The human approved at the brief. Review PASS: doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md (Reviewer-run a0705137a137aecbc, Author-run ab74ef54c3710742d).
- Change under test: the uncommitted 3-file diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d` over HEAD b50406e. The files are `.claude/hooks/guard_bash.py`, `scripts/autonomy.py` (new `protected_commit`) and `tests/hooks/test_guard_always_human.py` (additions only). `git status --short` in the worktree shows exactly these 3 files.
- Every run below used scratch copies in the QA scratchpad `qaf1-1792671252/`. `old` is `git archive b50406e`. `new` is the same plus the 3 files, and `diff -rq old new` shows exactly those 3 files. Throwaway repos had `HOME` and `APPROVAL_LOG` pointed at temp dirs, so the real registry was never read or written.
- Criteria under test: F-AC1, commit half only (SPEC-delegated-autonomy.md line 106, narrowed by am2's increment plan row 1 to `guard_bash.py` only). A-AC8, guard half only (line 121).

### Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| F-AC1 (commit half) | Autonomy active and current branch protected (`main`, `master`, project list) → agent `git commit …` refused with `work under autonomy happens on a branch or worktree`. On `feature/x` it is allowed. `guard_bash.py` only | **FAIL** | Probe `probe.py` fed `git commit -m x` payloads to the old and new guards across 31 scenarios (state × branch). With a live mandate, order or absence on `main`, `master` and listed `release`: old=0, new=2 `rule F-AC1` (9/9). On `feature/x` under each: new=0 (3/3). The message contains the required phrase (`… — work under autonomy happens on a branch or worktree`). **Fails on two cases (Defects 1, 2):** unborn `main` → new=0; `cd <wip worktree> && git commit` from a `main` cwd → new=2. |
| A-AC8 (guard half) | No live autonomy → nothing changes | PASS | Wide probe: 12 commands × 31 scenarios, 372 rows (`probe-wide.log`). Every row where old ≠ new is an *active* state (mandate, order or absence) on a protected branch with a `git commit` command. The inactive states show old = new on every command, including `git commit`, `git merge`, `git push origin main`, `scripts/approve.sh`, `rm -rf data` and `git reset --hard`. Those states are: opted in with an empty registry, revoked order, expired order, ended absence, and never opted in with a live mandate, order or absence. The existing tests are unchanged: `diff old new` on the test file shows 0 removed lines. `python3 -m pytest tests/hooks tests/ci -q` on `new` → all pass (see Test Run). |
| Red-first | New refusal tests red on the old code | PASS | The author's test file on `old`: `12 failed, 84 passed in 16.58s`. The 12 failures are exactly `test_a_commit_on_a_protected_branch_is_refused_under_autonomy[*]`. |
| commit-msg untouched; owner commit on `main` | Rule not added to `check_commit` (am2 increment plan row 1) | PASS | `cmp` of `.githooks/commit-msg` and `.githooks/pre-commit` old vs new → identical. The `scripts/autonomy.py` diff has 0 removed lines. Script `owner.sh` used a real repo on `main`, `status` = `order order-proj-a-2026-10-22`, and `core.hooksPath` pointing to a dir holding only `.githooks/commit-msg`. Old and new gave the same results: owner commit on `main` rc=0, commit on `feature/y` rc=0, owner `git merge --no-ff feature/y` into `main` rc=0. |

### Test Run

```
python3 -m pytest tests -q -p no:cacheprovider        (on new)
2198 passed, 3 skipped in 442.97s (0:07:22)   rc=0

python3 -m pytest tests/hooks tests/ci -q -p no:cacheprovider   (on new)
1499 passed in 265.56s (0:04:25)   rc=0

scripts/verify-full.sh > verify-full.log 2>&1         (on new, made a git repo for the run)
OK hooks 1463 passed · OK ci-examples 36 passed · OK scar-forge · OK coordinator 174 passed · OK framework
lint/format/tests: template TODO placeholders ("this step verified NOTHING"), as on HEAD
"Everything configured passed, and that is ALL this run proves."   verify-full rc=0
```

The suite is green. The FAIL comes from two cases that no test covers (Defects below).

### Edge Cases Probed (new guard, live order, `main` unless stated)

- Refused (rc 2, F-AC1), correctly:
  - `git commit -m x` from a subdirectory
  - `git commit -F -` fed by a heredoc
  - newline-separated `git status⏎git commit -m x`
  - `true | git commit -m x`
  - `git commit -m x &`
  - `echo $(git commit -m x)`
  - `echo -m | xargs git commit`
  - `GIT_DIR=.git git commit -m x`
  - `git commit --amend --no-edit`
  - `git add . && git commit -m x`
- Refused, harmlessly: `git commit --dry-run` (writes nothing). See Parked Q3.
- Allowed, correctly:
  - `echo "git commit -m x"`
  - `git config alias.ci commit`
  - detached HEAD at `main`'s commit (no branch moves)
  - a `wip/x` worktree of a `main` repo when the hook's cwd is that worktree
  - outside any repo
- Malformed payloads exit 0 on both old and new:
  - empty input
  - `not json`
  - no `tool_input`
  - `command` set to null or to 123
  - `tool_name: Write`

  This matches the guard's stated policy ("Malformed input exits 0").
- Allowed, not caught (rc 0, old = new = 0), spellings outside F-AC1's wording, Parked:
  - `git cherry-pick HEAD`
  - `git revert --no-edit HEAD`
  - `git commit-tree`
  - `bash -c 'git commit -m x'`
- **Unborn `main`** (`git init -b main`, `scripts/autonomy.json` on disk, no commits): `autonomy.py status` → `order order-proj-a-2026-10-22`. `git symbolic-ref --short HEAD` → `main`. `git rev-parse --abbrev-ref HEAD` → rc 128. Guard result: `git commit -m x` → **rc 0**. → Defect 1.
- **Branch is read from the hook's cwd, not from where the commit lands.**
  - Hook cwd on `main`:
    - `cd <wip/x worktree> && git commit -m x` → **rc 2 F-AC1**. → Defect 2.
    - `git -C <wip/x worktree> commit -m x` → **rc 2 F-AC1**. → Defect 2.
  - Hook cwd on `feature/x`:
    - `cd <main repo> && git commit -m x` → rc 0.
    - `git -C <main repo> commit -m x` → rc 0.
    - `git switch main && git commit -m x` → rc 0.
    - `git checkout main; git commit -m x` → rc 0.

    These are Parked under Q1.

### Parked (outside increment 1's criteria or the declared threat model; for the coordinator)

- **Q1 — same root as Defect 2, the evasion direction.** The guard reads the hook's cwd branch. A command that changes the target, via `cd X &&`, `git -C X` or `git switch main && git commit`, commits on `main` with rc 0. `switch main && commit` and `cherry-pick`/`revert` (reviewer P1) are the forms an agent could reach by plain mistake. The brief declares other shell spellings a limit, so these are Parked, not FAIL. A fix for Defect 2 that resolves the target directory would also close the `cd`/`-C` forms.
- **Q2 — absence is not pinned by a test** (same as reviewer P2). The behaviour is right: the probe gives `main` + absence → rc 2 F-AC1. Nothing in `tests/` covers it. QA's `Files:` covers only this report, so no test was added.
- **Q3 — `git commit --dry-run` is refused** on a protected branch under autonomy. It is a false refusal of a read-only form, but harmless.
- **Q4 — the owner check ran through `commit-msg` only.** `pre-commit` fails the same way on old and new in a fresh copy of the framework, because 16 framework docs carry `Approval:` keys that the temp registry lacks. That is unrelated to F1.

### Defects

See the top-level `## Defects` table below (rows tagged "Inc. 1").

## Increment 1 — F1, re-test 2

### Scope and provenance

- Tier 1, re-test after rework. Review PASS at round 3 (commit db71dda; doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md). The brief was dispatched under the tier-1 approval at the brief. This QA run did not see the human approval itself.
- Change under test: the uncommitted 3-file diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d`, over this branch's HEAD db71dda. The worktree is based on b50406e, and HEAD differs from it only in `doc/qa/`. The files are `.claude/hooks/guard_bash.py` (unchanged since round 1), `scripts/autonomy.py` (`protected_commit` now follows `cd`/`-C` and `( )` scope, and `current_branch` falls back to `symbolic-ref`), and `tests/hooks/test_guard_always_human.py` (additions only, 0 removed lines). `git status --short` in the worktree shows exactly these 3 files.
- Scratch copies are in the QA scratchpad `qaf1r2-1792674955/`. `old` is `git archive HEAD`. `new` is the same plus the 3 files, and `diff -rq old new` shows exactly those 3 files. Every probe pointed `HOME` and `APPROVAL_LOG` at temp dirs, so the real registry was never read or written. The author's worktree was only read.
- `scripts/verify-handoff.sh --status` → `not opted in`, so `scripts/verify-full.sh` is the exit gate.

### Criteria Results (re-test 2)

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| Defect "worktree from a `main` cwd" (first run, Medium) | A commit that lands on a working branch is allowed | PASS (closed) | `tools/hostile.sh` (the first run's repro script, re-run as is) with the hook cwd on `main` and a live order, old/new rc: `cd WT && git commit -m x` 0/**0** · `git -C WT commit -m x` 0/**0** (first run: new=2). `tools/cdcases.sh`, new rc 0: `cd WT; git commit` · `(cd WT && git commit)` · relative `cd ../a-wt` and `git -C ../a-wt` · `cd -- WT` · a quoted worktree path with a space · `cd WT && git add . && git commit` · `cd WT && git commit --amend --no-edit` · `pushd WT && git commit`. |
| Defect "unborn `main`" (first run, Low) | Unborn `main` + live autonomy → `git commit` refused | PASS (closed) | `hostile.sh`, unborn `main` with a live order: old=0, new=**2 rule F-AC1** (first run: new=0). `tools/unborn.py`, 112 rows (unborn `main` and `feature/x` × opted in or not × 7 registry states × 4 commands): `git commit -m x` is new=2 F-AC1 under mandate, order and absence on `main`, and 0 on unborn `feature/x`. |
| F-AC1 refused half (reverse direction and regression) | Every commit that lands on a protected branch under autonomy is refused | PASS | Hook cwd on `feature/x`, new rc 2 F-AC1: `cd MAIN && git commit` · `git -C MAIN commit` · `cd ../a && git commit` · `git -c core.x=1 -C MAIN commit` · `git --no-pager -C MAIN commit` · `(cd MAIN && git commit)` · `cd WT && git commit && cd MAIN && git commit -m y`. Hook cwd on `main`, new rc 2 F-AC1: `cd /missing && git commit` · `(cd WT) && git commit` · `git -C /missing commit` · `cd sub && git commit` · `git commit -m x; cd WT`. The first run's 10 refused spellings (subdir, heredoc, newline, pipe, `&`, `$( )`, xargs, `GIT_DIR=`, `--amend`, `add &&`) all still give new=2. `tools/probe.py`, 31 scenarios: `git commit` on `main`/`master`/listed `release` under mandate, order or absence → new=2 (9/9). On `feature/x` → 0. |
| A-AC8 (guard half) | No live autonomy → nothing changes | PASS | `probe.py`, 8 commands × 31 scenarios = 248 rows (`probe-wide.log`): 18 rows differ, and every one is an *active* state on a protected branch running `git commit -m x` or `cd .. && git commit -m x`. In every inactive state (empty registry, revoked order, expired order, ended absence, and never opted in with a mandate, order or absence), old = new on all 8 commands. `unborn.py`: the inactive states on unborn repos give old = new on all rows. |
| Owner commit path untouched | `commit-msg`/`pre-commit` unchanged; owner commit and merge on `main` still work | PASS | `cmp` of `.githooks/commit-msg` and `.githooks/pre-commit` old vs new → identical. `tools/owner.sh`, real repo on `main`, status `order order-proj-a-2026-10-22`, old and new: owner commit on `main` rc=0, commit on `feature/y` rc=0, owner `git merge --no-ff feature/y` into `main` rc=0. |
| Red-first | New tests red on the code without the fix | PASS | The new test file on `old`: `25 failed, 89 passed in 21.26s`. The failures include `test_a_commit_on_an_unborn_main_is_refused_under_autonomy`, both `test_a_commit_aimed_at_main_from_a_worktree_is_refused[*]`, the 6 `test_a_commit_that_does_not_land_in_the_worktree_is_judged_on_main[*]` and `test_a_failed_cd_does_not_move_a_relative_git_dash_c`. The worktree-allowed tests pass on `old`, as they should: `old` allowed everything. |

### Test Run (re-test 2)

```
python3 -m pytest tests -q -p no:cacheprovider         (on new)
2216 passed, 3 skipped in 441.86s (0:07:21)   rc=0

scripts/verify-full.sh > verify-full.log 2>&1          (on new, made a git repo for the run)
  TODO lint/format/tests   not configured — this step verified NOTHING   (template placeholders, as on HEAD)
  OK   hooks             (258s) 1481 passed in 257.12s (0:04:17)
  OK   ci-examples       (10s) 36 passed in 5.87s
  OK   scar-forge
  OK   coordinator       (4s) 174 passed in 4.46s
  OK   framework         (157s) memory: 0 problem(s)
Everything configured passed, and that is ALL this run proves.
verify-full rc=0
```

### Observations (no action)

- **The unborn-branch fallback also tightens AH3.** On an unborn `main` under a live mandate, order or absence, `git merge feature/x` goes from old=0 to new=2 AH3, because `current_branch` now returns `main`. That is the safe direction, only under active autonomy, and the inactive rows are unchanged. The round-3 review noted it too.
- **An unreadable target is judged as the starting cwd.** For example, `cd` with no argument (to `$HOME`), `cd .. && git commit` out of the repo, or `git -C WT -C .. commit` from a `main` cwd → rc 2. Git would fail in a non-repo anyway. This is the docstring's stated safe-direction rule.

### Parked (re-test 2; declared limits or outside F-AC1's wording)

- First run's Q1 evasion forms that are still allowed: `git switch main && git commit` and `git checkout main; git commit` from a `feature/x` cwd → 0. `cherry-pick`, `revert`, `commit-tree` and `bash -c '…'` → 0. The `cd`/`-C` forms of Q1 are now refused.
- `cd -` and `pushd`/`popd` stacks are declared limits. `cd WT && cd - && git commit` from `main` → 2, but only by accident: `cd -` is read as `$HOME`. This matches reviewer R1/R2.
- Q2 (absence not pinned) is closed: the new `absence-main` rows are in the test file. Q3 (`--dry-run` refused) and Q4 (owner check through `commit-msg` only) are unchanged.

## Defects

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Medium | Inc. 1, F-AC1 allowed half. The guard refuses a commit that lands on a working branch when the hook's cwd is on `main`. This hits both `cd <worktree on wip/x> && git commit -m x` and `git -C <worktree on wip/x> commit -m x`: rc 2 `rule F-AC1`. Following the refusal's own advice ("or a worktree, and commit there") from a session whose cwd is the `main` checkout is therefore refused again. Repro: repo `a` on `main` with a live order, `git worktree add -b wip/x ../a-wt`, then feed `cd ../a-wt && git commit -m x` with cwd `a`. Fixing it means resolving the commit's target directory (`cd`/`-C`) before reading the branch, which also closes Parked Q1's `cd`/`-C` forms. | scripts/autonomy.py `protected_commit`; .claude/hooks/guard_bash.py `_apply_core` (`branch = autonomy.current_branch(cwd)`) | ai-engineer | `missed-ac` |
| Low | Inc. 1, F-AC1 refused half. Under live autonomy, an agent's `git commit` on an unborn `main` (no commits yet) is allowed and creates `main`. `autonomy.current_branch` uses `git rev-parse --abbrev-ref HEAD`, which exits 128 on an unborn branch, so it returns None and `protected_commit` returns None. Repro: `git init -b main`, write `scripts/autonomy.json` `{"project":"proj"}`, live `order-proj-…` in `APPROVAL_LOG`, feed `git commit -m x` → rc 0 (status prints the order as active). `git symbolic-ref --short HEAD` prints `main` and would serve as a fallback. | scripts/autonomy.py `current_branch` (line ~925) | ai-engineer | `missed-ac` |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

Both rows above are from the first increment-1 run (commit 17ce083). Both are closed in re-test 2. They stay here as the rework record.

## Approval history

- **2026-10-22 — drafted (increment 1, F1).** QA run, from the spec, the review, and the author's uncommitted 3-file diff in worktree agent-ab74ef54c3710742d, with every command run on scratch copies. FAIL: 2 defects (`missed-ac`), 3 of 4 rows PASS.
- **2026-10-22 — re-test 2 (increment 1, F1).** Re-ran the first run's repros and extra `cd`/`-C`/unborn probes on scratch copies of HEAD db71dda plus the reworked 3-file diff (review round 3 PASS). PASS: both defects closed, the reverse direction refused, A-AC8 unchanged, owner commit path unchanged. Full pytest and `scripts/verify-full.sh` rc=0.
