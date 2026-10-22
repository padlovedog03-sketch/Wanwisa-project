# QA Report: Bugfix D4 + D7 (coordinator_lint --help, bootstrap skips agent worktrees)

Status: In Review
Owner: qa
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D4 + D7
Review: doc/qa/REVIEW-bugfix-d4-d7.md
Date: 2026-10-22

## Verdict: PASS

Both bugs are gone: `--help`/`-h` print usage and exit 0, unreadable paths give one plain line and exit 2, and bootstrap neither rewrites nor reports files under the top-level `.claude/worktrees/` while still handling real look-alike paths; the full suite and the exit gate are green on the scratch copy.

## Criteria Results

Change under test: the uncommitted diff in worktree `.claude/worktrees/agent-a998e45d25322f524` (base 41b2499). All probes were run by this QA run, not relayed from the engineer or reviewer.

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| D4-a | `--help` and `-h` exit 0 with usage | PASS | `python3 scripts/coordinator_lint.py --help` and `-h` → rc=0, 37 lines on stdout including the `Usage` block, 0 bytes on stderr. Control: the pre-fix script (`git show HEAD:scripts/coordinator_lint.py`) with `--help` ends `FileNotFoundError: [Errno 2] No such file or directory: '--help'`, which is the reported bug. |
| D4-b | missing, unreadable and directory paths → one plain line, exit 2 | PASS | `nope.md` → rc=2 `coordinator-lint: cannot read nope.md: No such file or directory`; `chmod 000 ro.md` → rc=2 `... Permission denied`; directory `d` → rc=2 `... Is a directory`. One line each, no traceback. |
| D4-c | other modes unchanged | PASS | Old and new script run side by side, stdout+stderr compared byte for byte: stdin `-` (rc 1/1, same output), no args (rc 2/2, same), `--approve-ready` with no slug (rc 2/2, same). Two args → rc=2 `usage: coordinator_lint.py <file>\|-`. The only changed output is a path that cannot be read: a traceback with rc=1 before, one plain line with rc=2 now. That change is the fix. |
| D7-a | bootstrap substitution skips agent worktrees; real files are still substituted | PASS | Scratch copy with `HOME` pointed at a scratch folder. Planted `.claude/worktrees/a/doc/x.md` and `.claude/worktrees/a/AGENTS.md` (both with `&lt;PROJECT&gt;`), plus real files `doc/real.md`, `doc/.claude/worktrees/x.md` and `.claude/worktrees-old/x.md`. After `bash scripts/bootstrap.sh` (rc=0, "18 files substituted"): `diff -r` of the worktree folder before and after shows no change; all three real files read `name Acme Portal`. Control: the pre-fix bootstrap.sh rewrote the worktree file to `name Acme Portal`. |
| D7-b | leftover report skips agent worktrees; real files are still reported | PASS | Same run. The report lists `.claude/worktrees-old/x.md:2:left &lt;ZZZ_OLD&gt;`, `doc/.claude/worktrees/x.md:2:left &lt;ZZZ_NESTED&gt;` and `doc/real.md:2:left &lt;ZZZ_REAL&gt;`, and has no line under `.claude/worktrees/`. Control: the pre-fix report listed `.claude/worktrees/a/doc/x.md:2:left &lt;ZZZ_WT&gt;`. The real `~/.jarvis` was not touched (the registry was created under the scratch HOME). |
| Suite | full pytest on the scratch copy | PASS | `python3 -m pytest tests -q -p no:cacheprovider` → `1883 passed, 1 skipped in 373.55s`, rc=0 |
| Exit gate | `scripts/verify-full.sh` (`verify-handoff.sh --status` → `not opted in`) | PASS (configured steps) | rc=0. hooks `1303 passed`, ci-examples `30 passed`, coordinator `159 passed`, scar-forge OK, framework OK (memory 0 problems). The banner also says `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. Those are template TODO steps that were there before this change. |

Scratch copy: the worktree's tracked and untracked files (rsync, without `.git` and the nested `.claude/worktrees`), with `doc/qa/QA-bugfix-gate3-worktree.md` and `doc/qa/REVIEW-bugfix-gate3-worktree.md` taken from commit 0fd71b6. That commit fixes the 9 known gate-3 reds on base 41b2499, which come from outside this change. The copy was put in a fresh `git init` repo with one commit.

## Test Run

```
python3 -m pytest tests -q -p no:cacheprovider        -> 1883 passed, 1 skipped in 373.55s (rc=0)
scripts/verify-full.sh > vfull.log 2>&1               -> rc=0
  OK hooks 1303 passed · OK ci-examples 30 passed · OK scar-forge · OK coordinator 159 passed · OK framework
  EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests   (pre-existing template TODOs)
```

No tests were added by QA. The engineer's new tests are in the suite above (`test_help_prints_the_usage_and_exits_0[--help|-h]`, the missing-file and directory tests, and the extended `test_gate_3_exclusions_match_bootstraps_own_leftover_check`).

## Defects (if FAIL)

None.

## Edge Cases Probed

- `--help --approve-ready` → rc=0, help (help wins when it comes first).
- `--approve-ready --help` → handled by approve-ready mode as before: rc=2 `not inside a git work tree` in a non-git folder. Mode unchanged.
- A file name containing a space (`"a b"`, one argument, missing file) → old: traceback, rc=1; new: one plain line, rc=2.
- Nested `doc/.claude/worktrees/` and sibling `.claude/worktrees-old/` → still substituted and reported. Only the top-level path is skipped, the same as CI gate 3.
- A file that is not UTF-8 (`\xff\xfe bad`) → still `UnicodeDecodeError` traceback with rc=1 (see Parked).

## Parked

- Low, outside the D4 criteria: a readable file that is not UTF-8 still crashes coordinator_lint with a traceback and rc=1, which is the same code as "violations found". The reviewer saw the same thing. Proposed backlog line, not rework.
- Low, test strength (Tier 0, rule 4): the new bootstrap test does not isolate `HOME`, so it touches the real `~/.jarvis/approvals/registry.jsonl` (mkdir and touch only), and it does not check that a look-alike real file gets substituted. The reviewer also parked both points.

## Approval history

- **2026-10-22 — drafted.** Independent QA run on a scratch copy of agent worktree a998e45d25322f524 (base 41b2499 plus the 0fd71b6 gate-3 doc fix), after reviewer PASS in commit b1c588b. Every result above comes from commands re-run in this QA run.
