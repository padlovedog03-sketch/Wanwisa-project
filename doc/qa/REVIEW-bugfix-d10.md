# Review: Bugfix D10 (read-only flag after `--` exempted an owner script)

Status: In Review
Owner: reviewer
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D10
Author-run: a791a8aea9df4ae78
Reviewer-run: a40318906bfead348
Date: 2026-10-22

## Verdict: PASS

The fix stops the read-only-flag search at the first `--` after the owner script. All 48 new refusal cases are red on the old code and green after, the B-AC10 read-only uses still pass, the only production change is inside `_owner_script`, and the exit gate is green on the author's tree.

## Read from

- Upstream: doc/tasks/backlog.md row D10, and the bug statement in the review brief.
- Change: uncommitted diff in `.claude/worktrees/agent-a791a8aea9df4ae78` (scripts/autonomy.py, tests/hooks/test_guard_always_human_rework.py). I compared it with `diff -u` against my own worktree at c9728b0. The only other difference between the trees is the §8 docs addition from c9728b0 in coordinator-discipline/SKILL.md, which the author's base does not have yet. That is not part of this change.
- Not read: the author's conversation. I re-ran the claims in the handback myself instead of passing them on.
- Scratch copy for the red-before run: the author's tree with `scripts/autonomy.py` replaced by the c9728b0 version.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| AC1 | Every owner script with a read-only flag after `--` is refused, in plain and active projects | PASS | `python3 -m pytest tests/hooks/test_guard_always_human_rework.py tests/hooks/test_guard_always_human.py -q -p no:cacheprovider` in the author's tree → `186 passed`. This includes 8 scripts × {-h, --help, -n} × {plain, active} = 48 cases that expect exit 2 and "owner-only command". A direct `_owner_script` probe also refuses `-- --dry-run` and `-- --list` (see Hostile inputs). |
| AC2 | B-AC10 read-only uses before any `--` still exit 0, including `--help -- spec-x` | PASS | Same run: `test_a_read_only_flag_before_double_dash_stays_allowed` passes all 14 cases (7 commands × 2 projects). Probe: `scripts/approve.sh --help --` → None, `scripts/approve.sh -h -- -h` → None (exempt). |
| AC3 | A `--` before the script name does not change results | PASS | `test_a_double_dash_before_the_owner_script_does_not_change_the_result` passes. Probe: `env -- scripts/approve.sh --help` → None (exempt, same as without `env --`). `env -- scripts/approve.sh -- --help` → `approve.sh` (refused). The search slices `effective[index + 1:]`, so a `--` before the script never reaches it. |
| AC4 | No other guard behaviour changed (diff limited to `_owner_script`) | PASS | `diff -u` of scripts/autonomy.py: one hunk, lines 635–650, inside `_owner_script` only (docstring + 2 lines). The test file is append-only (+57 lines at the end). `scripts/verify-full.sh` in the author's tree → `exit=0`, `OK hooks (235s) 1376 passed`, `OK coordinator 159 passed`, `OK ci-examples 30 passed`, framework OK. |
| AC5 | The new tests are red against the old code | PASS | Scratch copy with the old autonomy.py: `python3 -m pytest tests/hooks/test_guard_always_human_rework.py -q -p no:cacheprovider` → `48 failed, 61 passed`. All 48 failures are `test_a_read_only_flag_after_double_dash_does_not_exempt_an_owner_script` and no other test fails. The 15 negative tests pass on the old code too, which is expected: they guard against regression and are not repro tests. |

## Defects (if FAIL)

None.

## Hostile inputs tried

I called `_owner_script(shlex.split(cmd))` directly with `scratchpad/probe.py`, once on the new tree and once on the old tree.

- `scripts/approve.sh -- -h`, `-- --help`, `spec -- -n` → new `approve.sh` (refused). Old: None (the bug).
- `bash scripts/approve.sh --by a -- spec -h`, `python3 scripts/approve.py --by a -- spec --help` → new: refused. Interpreter-wrapped forms are covered too. Old: None.
- `scripts/approve.sh --by a -- spec -- -h` (two `--`) → refused. The search stops at the first `--`.
- `scripts/release.sh -- --dry-run`, `-- --list` → refused. The other read-only flags are covered.
- `scripts/approve.sh --` and `scripts/approve.sh -- ` (empty operand list) → refused, no crash.
- `scripts/approve.sh --by a --- spec -h` → None (exempt). `---` is not end-of-options, so this matches the pre-existing exemption for `--by a spec -h`. That behaviour is unchanged and outside D10.
- `scripts/approve.sh --by a spec -h` (flag after a positional, no `--`) → None (exempt) on both old and new code. This is the pre-existing B-AC10 design, and the fix leaves it unchanged.

## Approval history

- **2026-10-22 — drafted.** Reviewer run a40318906bfead348. Based on the uncommitted diff in agent-a791a8aea9df4ae78, the backlog row D10, and the commands above.
