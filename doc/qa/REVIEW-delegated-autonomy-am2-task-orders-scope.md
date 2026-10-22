# Review: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Author-run: ab74ef54c3710742d
Reviewer-run: ab1fa0c0beac00430
Date: 2026-10-22

## Verdict: FAIL

Round 2 (rework after QA FAIL): both QA defects are closed, but the rework lost coverage in the refused half of F-AC1. Round 1 refused two commits that land on `main` by plain mistake, and round 2 allows them: `cd <typo>; git commit` and `(cd <worktree> && …); git commit`.

## Round 2 — increment 1 (F1) rework

### Read from

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

### What changed

- `protected_commit(command, config, cwd)` (`scripts/autonomy.py:817`) now walks the segments. A `cd`/`pushd` moves a running `here`, and `git -C <dir>` moves the target. The branch is read at the target with `current_branch(target)` (line 847).
- `current_branch` (line ~945) tries `git rev-parse --abbrev-ref HEAD` first. When that fails or prints nothing, it falls back to `git symbolic-ref --short HEAD`.
- `guard_bash.py` `_apply_core` passes `cwd` instead of the hook-cwd branch.

### Criteria Review

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

### Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| Medium | **A `cd` that fails moves the guard but not the shell.** If the `cd` destination does not exist (a typo), the shell stays in the `main` checkout. With `;`, the commit runs there. `protected_commit` moves `here` anyway, and then `current_branch(<nonexistent dir>)` hits `OSError` and returns `None`. `None` counts as "not protected", so the guard fails open. Repro: hook cwd on `main`, live order, `cd /nonexistent-rvf2; git commit -m x` → round 1 rc 2 F-AC1, round 2 **rc 0**. `rvf2-ab1fa/mech.py` confirms `current_branch(Path('/nonexistent-rvf2'))` → `None`. Fix direction: move `here` only when the destination is an existing directory (the shell's own behaviour). Also, do not let an unreadable target clear a commit that the starting cwd would refuse. | scripts/autonomy.py:836-838 (cd), :847 (`current_branch(target)`) | ai-engineer (`regression`) |
| Medium | **A subshell's `cd` leaks past its closing parenthesis.** `segments()` splits at `( )` but keeps no scope, so after `(cd <wt> && …)` the guard still thinks it is in the worktree. Repro: hook cwd on `main`, live order, `(cd WT && git commit -m x); git commit -m y`. The second commit lands on `main`: round 1 rc 2 F-AC1, round 2 **rc 0**. `mech.py`: `segments('(cd /x && git commit -m x); git commit -m y')` → `[['cd','/x'], ['git','commit',…], ['git','commit',…]]`, so the parentheses are gone. `(cd dir && cmd)` is a common agent idiom, so this is reachable by plain mistake. The docstring's declared limits name `bash -c`, `--git-dir` and `pushd` stacks, and not subshells. Fix direction: one simple safe option is to judge each `git commit` against both the starting cwd and the tracked `here`, and refuse if either is protected. Any new test must be red on the current r2. | scripts/autonomy.py:830-848 (`protected_commit` walk) | ai-engineer (`regression`) |

### Hostile inputs tried (round 2; r1 → r2 rc, hook cwd on `main`, live order, unless stated)

- Correct after the rework: every row in the Criteria table above. `echo 'cd WT && git commit -m x'` 0→0 (a mention is not a run).
- Declared limits (docstring: `bash -c`, `--git-dir`, `pushd` stacks):
  - `pushd WT; popd; git commit` 2→0 (lands on `main`). Parked R1.
  - `git --work-tree=WT commit` 2→2 (still refused, correctly: HEAD is `main`'s).
- `cd WT && cd - && git commit` 2→0 (lands on `main`). `cd -` is skipped as an option, so it resolves to `~`, not to the previous directory. Parked R2.
- Hook cwd outside any repo, `cd MAIN && git commit` → 0→0. `status` is read at the hook cwd's project root, not the target's. This is not new in round 2. Parked R3.
- `git commit --dry-run` 2→2. Unchanged (QA Q3).

### Parked (outside the threat model or declared; for the coordinator)

- **R1 — `pushd`/`popd` stacks.** `popd` is not tracked, so `pushd WT; popd; git commit` is judged at WT. The docstring declares this limit. It is a regression from round 1 (2→0), but only through a declared spelling.
- **R2 — `cd -`.** It resolves to `$HOME` instead of the previous directory. It is rare in agent commands. If the Defect 2 fix judges against the starting cwd as well, it closes this too.
- **R3 — status is read where the hook runs, not where the commit lands.** A session whose cwd is outside the opted-in project, running `cd <project on main> && git commit`, is allowed. The same was true in round 1, so this is the same family as QA Q1's evasion direction.
- Round-1 P1 (cherry-pick/revert/commit-tree/alias/`bash -c`), P3 and P4 are unchanged. P2 is closed by the new `absence-main` rows.

## Review history

### Round 1 (reviewer run a0705137a137aecbc) — result PASS, later failed by QA at 17ce083

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
