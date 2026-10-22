# Review: bugfix D8 + D9 (bootstrap tests touch real HOME; coordinator_lint non-UTF-8 traceback)

Status: In Review
Owner: reviewer
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md D8 + D9
Author-run: a95923fef5248e08a
Reviewer-run: af4757abba08b092f
Date: 2026-10-22

## Verdict: PASS

Every criterion for D8 and D9 is met, and each new test fails against the old code or a targeted mutation.

## Read from

- Upstream: `doc/tasks/backlog.md` rows D8 and D9, plus the criteria in the review brief.
- Change: the uncommitted working-tree diff in worktree `agent-a95923fef5248e08a` (3 files: `tests/ci/test_ci_examples.py`, `scripts/coordinator_lint.py`, `tests/coordinator/test_coordinator_lint.py`), compared with `diff -u` against base `65108e8`.
- Not read: the author's conversation. I re-ran every claim myself.
- Method: the worktree guard would not let me run commands inside the author's worktree. I copied base `65108e8` into two scratch trees. `new` holds the base plus the author's 3 files. `old` holds the base code plus only the author's 2 test files. I ran every bootstrap run with `HOME` set to an empty scratch directory, never the real HOME.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| D8-1 | Every bootstrap run in `test_ci_examples.py` goes through a helper that sets HOME to a tmp dir | PASS | `diff -u` shows all 3 direct `subprocess.run(["bash", "scripts/bootstrap.sh"] …)` calls replaced by `_run_bootstrap(repo, tmp_path)`, which sets `env={**os.environ, "HOME": str(tmp_path/"home")}`. Needle count: base file 3, fixed file 1 (the helper). |
| D8-2 | A test proves the real HOME is untouched (sentinel) and that bootstrap reached its registry line | PASS | `test_bootstrap_in_these_tests_never_touches_the_real_home` passes in `new`. Mutation 1: drop the HOME override from the helper → `AssertionError: bootstrap wrote under the real HOME` (1 failed). Mutation 2: replace bootstrap's `mkdir -p ~/.jarvis/approvals && touch …registry.jsonl` line with `true` → 1 failed (the registry assertion catches it). |
| D8-3 | A guard test stops new direct bootstrap calls | PASS | Mutation: append `return ["bash", "scripts/bootstrap.sh"]` to the module → `FAILED …test_bootstrap_runs_only_through_the_isolating_helper`. Against the base file the guard's count is 3 ≠ 1, so it would be red. |
| D8-4 | Real HOME untouched across the suite | PASS | `python3 -m pytest tests/ci tests/coordinator -q -p no:cacheprovider` with a sentinel HOME → `192 passed`, sentinel HOME has 0 entries. Full `scripts/verify-full.sh` with a sentinel HOME → no `.jarvis` written (only Go toolchain caches from the hooks suite, see Parked). |
| D9-1 | Non-UTF-8 file gives exactly `coordinator-lint: cannot read <path>: not UTF-8`, exit 2 | PASS | New test passes in `new`. Hostile probes on latin-1, UTF-16 BOM and a trailing bad byte → rc=2, stdout empty, stderr is exactly that one line. |
| D9-2 | New D9 test is red against the old code | PASS | In the `old` tree: `test_a_non_utf8_file_is_one_plain_error_and_exits_2_not_1` → `UnicodeDecodeError … assert 1 == 2` (1 failed). |
| D9-3 | Nothing else changed | PASS | The diff adds one `except UnicodeDecodeError` branch (3 lines) and nothing else. Old and new lint on `empty.md` and a UTF-8-BOM file: same rc (1/1) and byte-identical output. Missing file and directory still go through the `OSError` branch (rc=2, strerror text). |
| Gate | Brief's verify command plus exit gate | PASS | `pytest tests/ci tests/coordinator` → 192 passed, exit 0. `scripts/verify-full.sh` → exit 0: hooks 1376 passed, ci-examples 32 passed, coordinator 160 passed, framework OK. Lint, format and tests are reported `not configured` (template state, unchanged by this diff). |

## Defects (if FAIL)

None.

## Hostile inputs tried

- latin-1 byte `\xe9` → rc=2, the exact one-line message, no traceback.
- UTF-16 with a `\xff\xfe` BOM → rc=2, the same message.
- Valid text followed by a trailing `\x80` → rc=2, the same message.
- Non-UTF-8 bytes on stdin (`-`) → rc=2, `coordinator-lint: cannot read -: not UTF-8`. This is covered too, but no test pins it.
- Empty file and a UTF-8-BOM file → unchanged from old (rc=1, identical output).
- Path with a space and `é` → read normally.
- Directory and missing path → unchanged `OSError` handling, rc=2.
- Guard test vs a re-pasted direct bootstrap call → red.
- Sentinel test vs a helper without the HOME override → red. Sentinel test vs a bootstrap that never reaches the registry line → red.

## Parked (out of criteria; threat model = mistakes, not fraud)

- The guard matches one literal spelling (`["bash", "scripts/bootstrap.sh"]`). A direct call spelled differently, such as `str(_BOOTSTRAP)` or with different spacing, would get past it. A copy-paste of the old block is caught. LIMIT, not a defect.
- No test covers the stdin non-UTF-8 path. It behaves correctly (probed above).
- The hooks suite writes Go toolchain caches (`~/go`, `~/Library/Application Support/go`) under HOME. This is unrelated to D8's approval registry and outside this change's scope.

## Approval history

- **2026-10-22 — drafted.** By reviewer run af4757abba08b092f, from backlog D8/D9, the author's 3-file working-tree diff and commands re-run in scratch copies.
