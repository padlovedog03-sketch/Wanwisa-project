# QA Report: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Date: 2026-10-22

## Verdict: FAIL

Increment 1 (F1): A-AC8 (guard half) passes, but F-AC1 (commit half) fails. On an unborn `main` (a repo with no commits yet), the guard lets an agent's `git commit` through while autonomy is active. Separately, a commit into a working-branch worktree is refused when the hook's cwd sits on `main`.

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

## Defects

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Medium | Inc. 1, F-AC1 allowed half. The guard refuses a commit that lands on a working branch when the hook's cwd is on `main`. This hits both `cd <worktree on wip/x> && git commit -m x` and `git -C <worktree on wip/x> commit -m x`: rc 2 `rule F-AC1`. Following the refusal's own advice ("or a worktree, and commit there") from a session whose cwd is the `main` checkout is therefore refused again. Repro: repo `a` on `main` with a live order, `git worktree add -b wip/x ../a-wt`, then feed `cd ../a-wt && git commit -m x` with cwd `a`. Fixing it means resolving the commit's target directory (`cd`/`-C`) before reading the branch, which also closes Parked Q1's `cd`/`-C` forms. | scripts/autonomy.py `protected_commit`; .claude/hooks/guard_bash.py `_apply_core` (`branch = autonomy.current_branch(cwd)`) | ai-engineer | `missed-ac` |
| Low | Inc. 1, F-AC1 refused half. Under live autonomy, an agent's `git commit` on an unborn `main` (no commits yet) is allowed and creates `main`. `autonomy.current_branch` uses `git rev-parse --abbrev-ref HEAD`, which exits 128 on an unborn branch, so it returns None and `protected_commit` returns None. Repro: `git init -b main`, write `scripts/autonomy.json` `{"project":"proj"}`, live `order-proj-…` in `APPROVAL_LOG`, feed `git commit -m x` → rc 0 (status prints the order as active). `git symbolic-ref --short HEAD` prints `main` and would serve as a fallback. | scripts/autonomy.py `current_branch` (line ~925) | ai-engineer | `missed-ac` |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

## Approval history

- **2026-10-22 — drafted (increment 1, F1).** QA run, from the spec, the review, and the author's uncommitted 3-file diff in worktree agent-ab74ef54c3710742d, with every command run on scratch copies. FAIL: 2 defects (`missed-ac`), 3 of 4 rows PASS.
