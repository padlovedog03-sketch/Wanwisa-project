# QA Report: Bugfix D10 (read-only flag after `--` exempted an owner script)

Status: In Review
Owner: qa
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D10
Review: doc/qa/REVIEW-bugfix-d10.md
Date: 2026-10-22

## Verdict: PASS

The bypass is gone. A read-only flag after `--` no longer exempts any of the 8 owner scripts. Read-only uses before `--` are still allowed, a `--` before the script name changes nothing, and the full suite and the exit gate are green on the fixed worktree.

## Criteria Results

Change under test: the uncommitted diff in worktree `.claude/worktrees/agent-a791a8aea9df4ae78` (base 96bebdb). It touches `scripts/autonomy.py` (`_owner_script` only) and `tests/hooks/test_guard_always_human_rework.py`. This QA run ran every probe below itself and did not relay results from the engineer or the reviewer. No owner script was executed.

Probe setup: two scratch trees, `old` and `new`. Each one holds a copy of the worktree's `scripts/` and `.claude/hooks/`. In `old`, `scripts/autonomy.py` comes from `git show HEAD:` (pre-fix), and that is the only file that differs between the trees (`diff -rq`). The probe pipes `{"tool_name":"Bash","tool_input":{"command":...}}` into each tree's `.claude/hooks/guard_bash.py`. It does this in two throwaway git repos: a plain project with an empty registry, and an active project with `scripts/autonomy.json` plus an approved mandate in `APPROVAL_LOG`. A first attempt that copied only `autonomy.py` blocked every command through the guard's fail-closed path (`verify_approvals.py` missing). Copying all of `scripts/` fixed that, and the results below come from that second run.

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| D10-a | Repro: the original bypass exits 0 on the old code | PASS (bug reproduced) | `scripts/<owner> --by a -- spec-x <flag>` for all 8 owner scripts × {`-h`, `--help`, `-n`, `--list`, `--dry-run`} × {plain, active} = 80 commands. Old tree: **all 80 exit 0**. This matches the reported bug. |
| D10-b | Fixed: every one of those commands is refused | PASS | Same 80 commands on the new tree: **all 80 exit 2**, and stderr contains `owner-only command`. |
| D10-c | B-AC10 read-only uses before `--` still exit 0 | PASS | `scripts/approve.sh` with `--help`, `-h`, `-n`, `--list`, `--dry-run`, `--help -- spec-x`, `-h -- -h`, plus `env -- scripts/approve.sh --help`, `scripts/release.sh --dry-run`, `scripts/delegate.sh --list`. That is 10 commands × 2 projects. Old and new both exit 0 for all 20. |
| D10-d | A `--` before the script name changes nothing | PASS | `env -- scripts/approve.sh x --by a` → old 2, new 2 (same as `scripts/approve.sh x --by a` → 2/2). `env -- scripts/approve.sh --help` → old 0, new 0. `env -- scripts/approve.sh -- --help` → old 0, new 2. The flag is after the script's own `--`, so the new result is correct. |
| D10-e | The new tests are red on the old code | PASS | The worktree's `tests/` in the old scratch tree: `python3 -m pytest tests/hooks/test_guard_always_human_rework.py -q -p no:cacheprovider` → `48 failed, 61 passed in 14.13s`. All 48 failures are `test_a_read_only_flag_after_double_dash_does_not_exempt_an_owner_script`. |
| Suite | Full pytest on the fixed worktree | PASS | `python3 -m pytest tests -q -p no:cacheprovider` → `1956 passed, 1 skipped in 309.51s (0:05:09)`, rc=0 |
| Exit gate | `scripts/verify-full.sh` (`scripts/verify-handoff.sh --status` → `not opted in`) | PASS (configured steps) | rc=0. `OK hooks 1376 passed`, `OK ci-examples 30 passed`, `OK scar-forge`, `OK coordinator 159 passed`, `OK framework` (memory 0 problems). The banner also says `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. Those are template TODO steps that were already there before this change. |

## Test Run

```
python3 -m pytest tests -q -p no:cacheprovider        -> 1956 passed, 1 skipped in 309.51s (rc=0)
scripts/verify-full.sh > vfull.log 2>&1               -> rc=0
  OK hooks 1376 passed · OK ci-examples 30 passed · OK scar-forge · OK coordinator 159 passed · OK framework
  EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests   (pre-existing template TODOs)
guard probe (old vs new autonomy.py, plain + active):
  bypass   80/80  old=0 -> new=2 (owner-only command)
  hostile  18/20  old=0 -> new=2 ; 2/20 old=2 new=2 (`scripts/approve.sh --`, no read-only flag)
  readonly 20/20  old=0 ,  new=0
  pre-dd    6/6   unchanged
```

QA added no tests. The engineer's 63 new parametrized cases are part of the suite run above.

## Defects (if FAIL)

None.

## Edge Cases Probed

All of these went through the real `guard_bash.py` with JSON on stdin, in both projects.

- `scripts/approve.sh -- -h` → old 0, new 2.
- `scripts/approve.sh --by a -- spec -- -h` (two `--`) → old 0, new 2. The search stops at the first `--`.
- Wrapped forms: `bash scripts/approve.sh --by a -- spec -h`, `python3 scripts/approve.py --by a -- spec --help`, `nice scripts/approve.sh --by a -- spec -h` → old 0, new 2.
- `./scripts/release.sh -- --dry-run` → old 0, new 2.
- Compound commands: `scripts/approve.sh --by a -- spec-x -h && echo hi` and `echo hi; scripts/approve.sh --by a -- spec-x -h` → old 0, new 2.
- `scripts/approve.sh --` (empty operand list) → 2 on both, no crash.
- `scripts/approve.sh -h -- -h` → 0 on both. The read-only flag is before `--`, so this is correct.

## Approval history

- **2026-10-22 — drafted.** QA run for bugfix D10. Based on the uncommitted diff in agent-a791a8aea9df4ae78, the backlog row D10, doc/qa/REVIEW-bugfix-d10.md (PASS), and the commands above.
