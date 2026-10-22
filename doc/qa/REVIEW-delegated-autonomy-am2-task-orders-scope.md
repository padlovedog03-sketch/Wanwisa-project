# Review: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Author-run: ab74ef54c3710742d
Reviewer-run: a0705137a137aecbc
Date: 2026-10-22

## Verdict: PASS

Increment 1 (F1) refuses an agent `git commit` on a protected branch while autonomy is active, allows it on a working branch, leaves projects without live autonomy exactly as before, and the new refusal tests are red against the old code.

## Increment 1 — F1

### Read from

- Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md, row-5 increment plan row 1 (line 107: F-AC1 `git commit` half, `guard_bash.py` only, not `check_commit`); the approved F-AC1 and A-AC8 rows in doc/specs/SPEC-delegated-autonomy.md (lines 106 and 121).
- Change: the uncommitted diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d` over HEAD b50406e. `diff -rq` of that worktree against HEAD (excluding `.git`, caches) → exactly 3 files differ, plus the untracked `.verify/` run folder: `scripts/autonomy.py` (new `protected_commit`, +16 lines, nothing else changed), `.claude/hooks/guard_bash.py` (`_apply_core`, +9 lines), `tests/hooks/test_guard_always_human.py` (additions only). `.githooks/commit-msg` and `check_commit` are untouched.
- Not read: the author's conversation. Every result below was run in this review, on scratch copies (`old` = HEAD, `new` = HEAD plus the author's 3 files) under the reviewer's scratchpad `rvf1-a0705/`. The author's worktree was never written to.

### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| F-AC1 (commit half, as amended) | Under a live mandate, order or absence, an agent `git commit` on `main`, `master` or a project-listed protected branch is refused with `work under autonomy happens on a branch or worktree`; on a working branch it is allowed; enforced in `guard_bash.py` only | PASS | `python3 -m pytest tests/hooks/test_guard_always_human.py tests/framework/test_autonomy_items.py -q -p no:cacheprovider` on `new` → `173 passed in 11.36s`. Probe (`probe.py`, old vs new guard, real git repos): `main`+mandate, `main`+order, `main`+absence → `git commit -m x` old=0 new=2 `rule F-AC1`; `feature/x`+mandate and a `wip/x` worktree of a `main` repo → old=0 new=0. Only the 3 files differ (`diff -rq`, above), so `.githooks/commit-msg` and `check_commit` are untouched. |
| A-AC8 (guard half) | With no live autonomy nothing changes | PASS | Probe, 25 commands each, every row old rc = new rc: `main` with no `scripts/autonomy.json` but a live mandate in the registry (e.g. `git commit -m x` 0→0, `git merge feature/x` 0→0, `git status` 0→0, `ls` 0→0); `main` opted in with an empty registry (same); `main` with the mandate revoked (same). Full exit gate below: existing `tests/hooks/` and `tests/ci/` all pass. |
| Red-first | New refusal tests red against the old code | PASS | Same pytest command on `old` with the author's test file → `12 failed, 161 passed`; the 12 are exactly `test_a_commit_on_a_protected_branch_is_refused_under_autonomy[*]` (3 commands × mandate-main, mandate-master, order-main, order-project-listed-branch). The allow tests (working branch, no live autonomy, never opted in, mentions) are green on both, as regression pins should be. |
| Exit gate | `scripts/verify-full.sh` | PASS | Run on `new` (made a git repo for the run) → hooks `1463 passed`, ci-examples `36 passed`, coordinator `174 passed`, scar-forge OK, framework OK, `verify-full exit=0`. lint/format/tests are the template's `TODO` placeholders ("this step verified NOTHING"), as on HEAD. |

### The author's fail-open, against the guard's stated policy

The brief notes that F-AC1 fails open when the core raises. Checked with planted mutants (`failopen.sh`, a `raise RuntimeError` inserted into one core function, `main` + live mandate):

- `status` raises, old guard → `git merge feature/x` rc=0, `scripts/approve.sh x --by y` rc=2.
- `status` raises, new guard → `git commit -m x` rc=0, `git merge` rc=0, `approve.sh` rc=2.
- `protected_commit` raises, new guard → `git commit` rc=0, `git merge` rc=0, `approve.sh` rc=2.

This **matches** the stated policy. `guard_bash.py`'s `_check_always_human` docstring and its `except` say only the owner rule (AH5 owner scripts) survives a core failure, through the inline `_OWNER_FALLBACK` matcher; the module header says "Malformed input exits 0 — a guard that fails closed on its own bug would be worse". The always-human items (AH1–AH4) already fail open the same way, and F-AC1 now joins them. One side effect is noted below as P4.

### Hostile inputs tried (`main` + live mandate unless stated; new guard)

- Refused (rc 2, F-AC1): `git commit --amend --no-edit`, `git commit -m x 2>&1`, `git commit -m x >/dev/null`, `env git commit`, `sudo git commit`, `/usr/bin/git commit`, `GIT_AUTHOR_NAME=a git commit`, `git --no-pager commit`, `git -C . commit`, `(git commit -m x)`, `git status; git commit -m x`, tab between words, `git commit -m 'git commit'`.
- Allowed (rc 0, correct): `echo git commit`, `git log --grep commit`, `git help commit`, `git status`, `ls`.
- Malformed `scripts/autonomy.json` (`{not json`) on `main` → status `unknown — treated as active`, `git commit` refused (fails closed).
- Detached HEAD at `main`'s commit → allowed (no branch moves; git reports `HEAD`).
- Branch `Main` (case variant) → allowed. Git branch names are case-sensitive, and the existing AH3 rule uses the same exact-name set.
- Not caught: `git commit-tree`, alias `git ci`, `bash -c 'git commit -m x'`, `git cherry-pick HEAD`, `git revert HEAD`. See Parked P1.

### Defects

None.

### Parked (outside increment 1's criteria; for the coordinator)

- **P1 — other commands that land a commit on `main`.** `git cherry-pick`, `git revert`, `git commit-tree`, aliases and `bash -c '…'` all exit 0 under a live mandate on `main`. F-AC1 names `git commit …` only, and the brief declares other shell spellings a stated limit (doc/memory/ease-of-use-over-strictness.md). `cherry-pick` and `revert` are the ones an agent could reach by plain mistake, not by evasion. Whether F-AC1 should name them is a spec question.
- **P2 — absence is not in the author's tests.** The parametrised refusal test covers mandate and order only. The probe shows absence is refused too (`main+absence` → rc 2 F-AC1), so behaviour is right but nothing pins it. One more `ids` row would.
- **P3 — a rejected project file drops the project-listed branch.** `{"project":"proj","protected_branches":["release"],"bogus":1}` is rejected by `load_config`, so `git commit` on `release` is allowed (`main`/`master` still refused). This matches how AH3 already behaves and the guard's message "the framework items still apply".
- **P4 — one new way to lose AH1–AH4 on a crash.** `protected_commit` runs before the always-human block. If it raised, that command's AH3 match would also go unenforced (mutant above: `git merge` rc 0). This is within the stated fail-open policy, and `protected_commit` only reuses `segments`/`_split_redirects`/`_git_subcommand`, which `command_matches` has already run on the same command. Low risk; noted for completeness.

## Approval history

- **2026-10-22 — drafted (increment 1, F1).** Reviewer run a0705137a137aecbc, from the spec, the author's uncommitted 3-file diff in worktree agent-ab74ef54c3710742d, and commands run on scratch copies. PASS.
