# QA Report: Bugfix D8 + D9 (bootstrap tests touched the real HOME; coordinator_lint traceback on non-UTF-8)

Status: In Review
Owner: qa
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D8 + D9
Review: doc/qa/REVIEW-bugfix-d8-d9.md
Date: 2026-10-22

## Verdict: PASS

Both bugs are fixed. With the fix, no bootstrap run in the suite writes `.jarvis` under the HOME it was given; the old test file did. A non-UTF-8 input to `coordinator_lint.py` now gives one plain line and exit 2 instead of a traceback and exit 1. Every other mode behaves as before, and the full suite and the exit gate are green.

## Criteria Results

Change under test: the uncommitted 3-file diff in worktree `.claude/worktrees/agent-a95923fef5248e08a` (HEAD 7caa80d): `scripts/coordinator_lint.py`, `tests/ci/test_ci_examples.py`, `tests/coordinator/test_coordinator_lint.py`. QA ran every command below itself and did not relay results from the engineer or the reviewer.

Setup: two scratch copies of the worktree, made with `rsync` and each given its own `git init`. `new` holds the worktree as is. `old` holds the same files, but the 3 changed files come from `git show HEAD:`. `diff -rq old new` lists only those 3 files. A third copy, `new2`, ran the exit gate. Every run had `HOME` set to a fresh, empty sentinel directory. The real HOME was never used.

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| D8-a | Repro: the old test file writes under HOME | PASS (bug reproduced) | `old`: `HOME=home-old python3 -m pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider` → `30 passed`. Afterwards `home-old` contains `.jarvis/approvals/registry.jsonl`. |
| D8-b | Fixed: the full suite leaves nothing under the sentinel's `.jarvis` | PASS | `new`: `HOME=home-sentinel python3 -m pytest tests -q -p no:cacheprovider` → `1959 passed, 1 skipped in 264.68s`, rc=0. `find home-sentinel -path '*.jarvis*'` → no output. The same holds for the exit-gate sentinel `home-sentinel2`. The sentinels are not completely empty: they hold `go/pkg/mod`, `Library/Caches/go-build` and `Library/Application Support/go`, written by the hooks suite. That suite is byte-identical between `old` and `new`, so the change did not cause these files (see Parked). |
| D8-c | Every bootstrap call goes through the isolating helper | PASS | The literal `["bash", "scripts/bootstrap.sh"]` appears 3 times in the old file and once in the new file (in `_run_bootstrap`, which sets `HOME` to `tmp_path/"home"`). `test_bootstrap_runs_only_through_the_isolating_helper` pins the count at 1, so the old file would fail it. |
| D9-a | Non-UTF-8 input: exactly one line, exit 2 | PASS | `new`: latin-1 `\xe9`, UTF-16 BOM `\xff\xfe`, valid text followed by `\x80`, a truncated `\xc3`, and a path containing a space and `é` all give rc=2, empty stdout and exactly 1 stderr line, `coordinator-lint: cannot read …/latin1.md: not UTF-8`. Non-UTF-8 on stdin (`-`) → rc=2, `coordinator-lint: cannot read -: not UTF-8`. `old`: all 6 of these inputs give rc=1 and a 12-line `UnicodeDecodeError` traceback. |
| D9-b | The new D9 test is red on the old code | PASS | `old` code with the new `test_coordinator_lint.py`: `FAILED …::test_a_non_utf8_file_is_one_plain_error_and_exits_2_not_1`, `1 failed, 90 passed`. |
| D9-c | Other modes unchanged | PASS | Old and new give the same rc and the same output on: empty file (rc 1), UTF-8 BOM file (rc 1), valid UTF-8 file (rc 1). `cmp` shows byte-identical output for all three, and for `--help` (rc 0). They also match on missing file (rc 2, one line), directory (rc 2), no args (rc 2, usage), two args (rc 2, usage), `--approve-ready` with no slug (rc 2, usage), and `--approve-ready zzz-none` (rc 1). |
| Suite | Full pytest, sentinel HOME | PASS | `1959 passed, 1 skipped`, rc=0 |
| Exit gate | `scripts/verify-full.sh` (`scripts/verify-handoff.sh --status` → `not opted in`), sentinel HOME, output to log | PASS (configured steps) | rc=0. `OK hooks 1376 passed` · `OK ci-examples 32 passed` · `OK scar-forge` · `OK coordinator 160 passed` · `OK framework` (memory: 0 problems). The banner also says `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. Those steps are template TODOs that were not configured before this change either. |

## Test Run

```
old: HOME=home-old pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider -> 30 passed; home-old/.jarvis/approvals/registry.jsonl created
new: HOME=home-sentinel  python3 -m pytest tests -q -p no:cacheprovider   -> 1959 passed, 1 skipped in 264.68s (rc=0); no .jarvis under sentinel
new2: HOME=home-sentinel2 scripts/verify-full.sh > vfull.log 2>&1        -> rc=0; no .jarvis under sentinel
  OK hooks 1376 passed · OK ci-examples 32 passed · OK scar-forge · OK coordinator 160 passed · OK framework
  EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests   (template TODOs, not configured before this change either)
old code + new coordinator test -> 1 failed, 90 passed (the D9 test)
```

QA added no tests. The suite runs above include the engineer's 3 new tests.

## Defects (if FAIL)

None.

## Edge Cases Probed

- Six non-UTF-8 inputs (latin-1, UTF-16 BOM, trailing `\x80`, truncated multibyte `\xc3`, a path with a space and `é`, stdin) → new rc=2 with one line each; old rc=1 with a traceback each.
- Empty file and UTF-8 BOM file → unchanged, with byte-identical output.
- Missing path and directory path → unchanged; both still go through the `OSError` branch with rc=2.
- `--approve-ready` on a tracked `In Review` doc that contains a non-UTF-8 byte → still a `UnicodeDecodeError` traceback, the same as before. The engineer did not change this mode, and it is outside D9's `<file>` mode (see Parked).

## Parked (outside the D8/D9 criteria; threat model = mistakes, not fraud)

- `--approve-ready` reads each matched doc with `read_text(encoding="utf-8")` (`scripts/coordinator_lint.py:401`), and so does line 213. A non-UTF-8 approvable doc still produces a traceback in that mode. This is the same behaviour as before the change. Candidate backlog row.
- The hooks suite writes Go toolchain caches (`~/go`, `~/Library/Caches/go-build`, `~/Library/Application Support/go`) under HOME. This is not the approval registry and has nothing to do with this change. The reviewer recorded the same finding.
- LIMIT: the guard test matches one literal spelling of the bootstrap command. A direct call spelled another way would get past it. This was already recorded in the review.

## Approval history

- **2026-10-22 — drafted.** QA run for bugfix D8 + D9. Based on the uncommitted diff in agent-a95923fef5248e08a, backlog rows D8 and D9, doc/qa/REVIEW-bugfix-d8-d9.md (PASS), and the commands above, all run in scratch copies with a sentinel HOME.
