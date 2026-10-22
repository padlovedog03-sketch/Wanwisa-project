# Review: Bugfix D4 + D7 (coordinator_lint --help, bootstrap skips agent worktrees)

Status: In Review
Owner: reviewer
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D4 + D7
Author-run: a998e45d25322f524
Reviewer-run: a76cb2e7097a74eed
Date: 2026-10-22

## Verdict: PASS

Both fixes do what the criteria ask, the new tests are red on the pre-change scripts and green after, and the exit gate is green on a copy carrying the 0fd71b6 doc fix; two Low observations are Parked, not rework.

## Read from

- Upstream: doc/tasks/backlog.md rows D4 and D7 (Improvement checklist), and the bug statements in the review brief.
- Change: uncommitted diff in `.claude/worktrees/agent-a998e45d25322f524` on base 41b2499 (scripts/coordinator_lint.py, scripts/bootstrap.sh, tests/coordinator/test_coordinator_lint.py, tests/ci/test_ci_examples.py).
- Not read: the author's conversation. Claims in the handback were re-run, not relayed.
- Scratch copy used for red-before, mutation and exit-gate runs: the worktree's tracked + untracked files, with `doc/qa/QA-bugfix-gate3-worktree.md` and `doc/qa/REVIEW-bugfix-gate3-worktree.md` taken from 0fd71b6 (the known 9 gate-3 reds on 41b2499 are not this change).

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| D4-a | `--help` / `-h` exit 0 with usage | PASS | `python3 scripts/coordinator_lint.py --help` and `-h` → rc=0, 37 lines on stdout (module docstring incl. the `Usage:` block), nothing on stderr |
| D4-b | missing / unreadable path → one plain line, exit 2 | PASS | missing file → rc=2, `coordinator-lint: cannot read …/nope.md: No such file or directory`; `chmod 000` file → rc=2, `… Permission denied`; directory → rc=2, `… Is a directory`; no traceback in any |
| D4-c | all other modes unchanged | PASS | stdin `-` → rc=1 with the usual violation report; no args → rc=2 `usage: coordinator_lint.py <file>\|-`; `--approve-ready` without slug → rc=2 its own usage line; full `tests/coordinator` 159 passed (exit gate, below) |
| D7-a | bootstrap skips top-level `.claude/worktrees/` in substitution | PASS | scratch bootstrap run (HOME isolated): `.claude/worktrees/a/x.md` kept `&lt;PROJECT&gt;`; `doc/.claude/worktrees/x.md` and `.claude/worktrees-old/x.md` were substituted (`Acme Portal`) — only the top-level path is skipped |
| D7-b | bootstrap skips top-level `.claude/worktrees/` in the leftover report; real files still reported | PASS | same run: leftover report listed `.claude/worktrees-old/x.md:1` and `doc/.claude/worktrees/x.md:1`, nothing under `.claude/worktrees/` |
| D7-c | the test pins all four exclusions in both places | PASS | `_GATE_3_EXCLUSIONS` holds 4 entries checked as `grep -v '…'` in the CI step and in bootstrap.sh, plus a count check that CI has no unlisted exclusion; on pre-change bootstrap.sh the test fails with `"grep -v '^\\.claude/worktrees/'" missing from bootstrap.sh` |
| Red before | new tests fail on the old scripts | PASS | scratch copy with `git show HEAD:` versions of both scripts + new tests → FAILED `test_help_prints_the_usage_and_exits_0[--help]`, `[-h]` (Traceback in stderr), missing-file and directory tests (`assert 1 == 2`), exclusions test (missing from bootstrap.sh) |
| Brief verify | `pytest tests/coordinator tests/ci/test_ci_examples.py::test_gate_3_exclusions_match_bootstraps_own_leftover_check -q -p no:cacheprovider` | PASS | in the author worktree: `160 passed in 4.12s` |
| Exit gate | `scripts/verify-full.sh` | PASS (configured steps) | scratch copy: rc=0; hooks 1303 passed, ci-examples 30 passed, coordinator 159 passed, scar-forge OK, framework OK (memory 0 problems); lint/format/tests are template TODO steps ("EXIT GATE INCOMPLETE — 3 step(s) not configured"), pre-existing |

## Defects (if FAIL)

None.

## Hostile inputs tried

- `--HELP`, `-help`, `" --help"` (leading space) → treated as file paths: rc=2, one plain `cannot read` line. Acceptable: only the exact flags are help.
- `--help extra` → rc=0 help (help wins when first). `""` (empty path) → rc=2, `cannot read : Is a directory` (Path("") is `.`); plain, no traceback.
- Non-UTF-8 file (`\xff\xfe\x00bad`) → **traceback, `UnicodeDecodeError`, rc=1** (see Parked).
- Bootstrap mutation A (drop the Python `.claude/worktrees` skip) → test fails `assert 'name Acme Portal\n' == 'name &lt;PROJECT&gt;\n'`: the substitution half is pinned.
- Bootstrap mutation B (skip any path containing `worktrees`, too broad) → test still **passes** (see Parked).
- Bootstrap mutation C (drop the `grep -v` on the FILES list) → test still passes; that list only drives the "already bootstrapped" early exit, so this is cosmetic.

## Parked

- Low (outside D4 criteria): a file that exists but is not UTF-8 still crashes with a traceback and exits 1, the same code as "violations found". `except OSError` does not cover `UnicodeDecodeError`. Proposed backlog line, not rework.
- Low (test strength, round 1 but criteria met): substitution of a look-alike real file (e.g. `doc/worktrees-notes.md` or `.claude/worktrees-old/…`) is not asserted; the `worktrees-notes` fixture holds a non-substitutable placeholder and is only checked in the report. Mutation B survives. The shipped code is correct (verified by hand above).
- Low, pre-existing pattern: the new test runs bootstrap.sh without isolating HOME, so it touches the real `~/.jarvis/approvals/registry.jsonl` (mkdir + touch, no content change); the existing bootstrap tests in tests/ci/test_ci_examples.py do the same, while tests/framework/test_bootstrapped_project.py isolates HOME.

## Approval history

- **2026-10-22 — drafted.** Independent reviewer run; based on the uncommitted diff in agent worktree a998e45d25322f524 (base 41b2499) and commands re-run in this review.
