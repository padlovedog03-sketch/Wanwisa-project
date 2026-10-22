# QA Report: Gate 3 skips agent worktrees under .claude/worktrees/

Status: In Review
Owner: qa
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md item B1
Date: 2026-10-22

## Verdict: PASS

The original bug reproduces end to end on an unfixed copy (`1 failed, 21 passed`) and is gone on the fixed copy (`30 passed`). A real placeholder in a tracked doc is still caught. The full suite (`1879 passed, 1 skipped`) and `scripts/verify-full.sh` (rc=0) are green. All 4 criteria pass.

Code under test: the uncommitted diff in `.claude/worktrees/agent-afbef35185650415b` on HEAD `018f11b`. It covers `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml` and `tests/ci/test_ci_examples.py`. `git status --short` showed these 3 files before and after QA, and QA edited none of them.
Review read: `doc/qa/REVIEW-bugfix-gate3-worktree.md` (PASS, reviewer run `ab890f306d7777f69`). Every result below was re-run by QA. None is copied from the review.
Scratch: `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/19bfa7c3-9fca-4cb5-a638-a9c8b7f4068e/scratchpad/`. It holds `fixed/`, `unfixed/`, `c2/`, `c3/`, `gate3.sh`, `pytest.log` and `vf.log`.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AC1 | The original repro is green on the fixed tree. Setup: a fresh copy of the worktree (rsync, without `.git` or the nested `.claude/worktrees`) plus `.claude/worktrees/agent-x/doc/f.md` holding `fixture <ABC_DEF>`. | PASS | Unfixed control: the same copy with the 3 files restored from `git show HEAD:` gives `FAILED tests/ci/test_ci_examples.py::test_gate_3_is_green_after_bootstrap_runs` and `1 failed, 21 passed in 2.16s`. That is the bug exactly as the brief describes it. Fixed copy: `python3 -m pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider` gives `30 passed in 3.33s`. The original `test_gate_3_is_green_after_bootstrap_runs` copies the planted worktree along with everything else, so it is the true end-to-end check. |
| AC2 | A real placeholder is still caught | PASS | In copy `c2`, QA ran bootstrap (rc=0) and extracted the gate-3 `run` text from `ci-examples/github-actions.yml` with `yaml.safe_load` into `gate3.sh`. Baseline with the worktree fixture only: `ไม่มีตัวยึดหลงเหลือ`, rc=0. QA then appended `leftover <ABC_DEF>` to the tracked `doc/memory/README.md` (`git ls-files` lists it). Result: `พบตัวยึดที่ยังไม่ได้เติม:` / `doc/memory/README.md:41:leftover <ABC_DEF>`, rc=1. The worktree fixture does not appear in the output. |
| AC3 | Full suite green | PASS | In the worktree, `python3 -m pytest tests -q -p no:cacheprovider` gives `1879 passed, 1 skipped in 223.10s (0:03:43)`, rc=0. |
| AC4 | Exit gate | PASS | In the worktree, `scripts/verify-full.sh` exits rc=0. `scripts/verify-handoff.sh --status` reports `not opted in`, so verify-full is the verdict command. Output: `OK hooks 1303 passed`, `OK ci-examples 30 passed`, `OK scar-forge`, `OK coordinator 155 passed`, `OK framework memory: 0 problem(s)`. The banner reads `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, and `counts: not configured — executed == collected NOT checked`. That is the template repo's standing state, not something this change introduced. It means the run proves only the configured steps. |

## Test Run

```
# fixed copy, worktree fixture planted
30 passed in 3.33s
# unfixed control (HEAD versions of the 3 files), same fixture
FAILED tests/ci/test_ci_examples.py::test_gate_3_is_green_after_bootstrap_runs
1 failed, 21 passed in 2.16s
# worktree: python3 -m pytest tests -q -p no:cacheprovider
1879 passed, 1 skipped in 223.10s (0:03:43)
# worktree: scripts/verify-full.sh  -> rc=0
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
```

## Defects (if FAIL)

None.

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|

## Edge Cases Probed

- A tracked real placeholder and a worktree placeholder together, plus an empty `.claude/worktrees/empty/` → rc=1, and only `doc/memory/README.md:41` is reported.
- Worktree fixture only, after bootstrap → rc=0. The skip covers exactly the untracked area.
- `.claude/worktrees/` is gitignored (`.gitignore:14`), and `git ls-files .claude/worktrees` is empty. So the skip cannot hide a committed project file under the current ignore rules.
- Filter widening and un-anchoring (`doc/worktrees-notes.md`, `doc/.claude/worktrees/x.md`, `.claude/worktreesX/x.md`, `.claude/worktrees.md`, and a content line that mentions `.claude/worktrees/`) are pinned by the new parametrized tests. All of them ran green in the fixed copy and in the full suite. The reviewer's mutants m1–m8 show these tests go red when the filter is weakened.
- No other gate changed: the diff in both YAML files is only the gate-3 pipe plus one comment line.
- Bootstrap drift (parked, see below): in copy `c3`, `scripts/bootstrap.sh` still lists the worktree fixture in its own leftover report (rc=0, report only), while gate 3 now skips it.

## Parked

- `scripts/bootstrap.sh` lines 14 and 56–58 do not exclude `.claude/worktrees/`. Two effects follow. (a) Its leftover report lists worktree placeholders that CI gate 3 now ignores. This is the exact drift that `test_gate_3_exclusions_match_bootstraps_own_leftover_check` was written to catch, but that test only compares the three original exclusions. (b) Its substitution `grep -rl` would rewrite `<PROJECT>` and similar placeholders inside agent worktrees. The first effect is an informational report and the second predates this fix, so neither is in B1's criteria. Proposed backlog item.

## Approval history

- **2026-10-22 — drafted.** qa. Based on the B1 reproduction in the brief and the reviewer PASS in `doc/qa/REVIEW-bugfix-gate3-worktree.md`. Every check was re-run independently.
