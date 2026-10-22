# Review: Verify tiers, Amendment 3: pre-commit refuses a commit on a RED record or a gate-3 placeholder

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-verify-tiers-merge-gate-am3-commit-on-red.md
Author-run: a2efb18032c362ade
Reviewer-run: aa313d07504ca9746
Date: 2026-10-22

## Verdict: PASS

All 21 criteria, AM3-AC1 to AM3-AC21, hold on commands I ran in this review. The new tests fail against the old hook (67 failed, 57 passed) and pass with the change (133 passed, 0 skipped). Four mistakes I planted by hand each turned a test red. In this repo (template mode, 22,813-byte `AGENTS.md`), normal `git commit -a` and `git commit -- path` commits pass in 0.72 s and 0.74 s, and both incident replays are refused. The author's four declared deviations all match what the spec intends. Two findings fall outside the criteria and are parked below.

## Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate-am3-commit-on-red.md` (Approved, `spec-verify-tiers-merge-gate-am3-commit-on-red-2026-10-22`)
- Change: uncommitted files in the author's worktree `agent-a2efb18032c362ade`, compared file by file against this branch's HEAD `6ec6b4b` with `diff -u`:
  - `.githooks/pre-commit` (+49 lines, appended after the existing four-check loop);
  - `scripts/verify_record.py` (the `commit-check` subcommand, a docstring line, and a parser entry; no existing function changed);
  - `tests/framework/test_pre_commit_verify_record.py` (new);
  - `tests/framework/test_pre_commit_placeholders.py` (new);
  - `tests/ci/test_ci_examples.py` (one drift test, a helper, and a 3-case hostile test for the helper);
  - `doc/framework/ADAPTERS.md` (lines 63 and 68, plus a 13-item limits block);
  - `doc/memory/gate-exit-code-before-commit.md` (`mechanism:` line).
  `diff -rq` against HEAD found no other changed files.
- Where it ran: a scratch clone of this branch (`git clone` of the reviewer worktree, at `6ec6b4b`, holding incident commits `7661338` and `e6b4daa`), with the author's 7 files copied on top. HOME and `APPROVAL_LOG` pointed at scratch paths every time. The real registry was never read or written.
- Not read: the author's conversation. The brief's claims (the deviations and their reasons) were re-run, not relayed.

## Criteria Review

The **Verify with** command is `python3 -m pytest tests/framework/test_pre_commit_verify_record.py tests/framework/test_pre_commit_placeholders.py tests/framework/test_pre_commit.py tests/ci/test_ci_examples.py -q -p no:cacheprovider`. Run on the scratch clone with the change, it gave `133 passed in 116.65s`, with no skips: AM3-AC21 ran against the real incident commits. Run with only the new test files on the old hook and old recorder (red-first), it gave `67 failed, 57 passed in 95.54s`. The tests that passed before the change are AC10, the pass rows of AC15, AC16a, AC17 a/b/d/e and AC18, and the drift helper's extra-exclusion plant. The spec allows all of these to pass then. One more also passed, and the spec does not allow it: `test_ac4c_same_ended_at_the_later_directory_name_wins[RED-GREEN-False]`. That row asserts only that the commit went through, so it is green against the old hook as well (defect D1, Low).

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| AM3-AC1 | matching RED full record → refused, named | PASS | `test_ac1…` FAILED on the old hook and passes on the new one. Probe: hook output `FAIL verify record — the newest gate run for the staged tree is RED (.verify/runs/…/record.json)` |
| AM3-AC2 | INCOMPLETE/GREEN/OK pass, verbatim, never GREEN for non-GREEN | PASS | 3 parametrised cases, red-first then green. The test asserts `GREEN` is absent for INCOMPLETE and OK. |
| AM3-AC3 | EMPTY handoff → WARN, no `verify record:` | PASS | `test_ac3…` red-first then green |
| AM3-AC4 | ended_at orders; same second → later name wins | PASS | AC4a and AC4b use names that sort the opposite way to `ended_at`; AC4c covers the tie in both directions. All green. AC4c's pass row is weak (D1). Its GREEN-then-RED sibling was red-first and is refused, so an inverted tie-break or a missing check is still caught, and AC4a already asserts the `verify record: GREEN` line. |
| AM3-AC5 | stale / no `.verify` / empty / dirs with no record / fast null tree / changed mid-run → exactly one WARN naming verify-full | PASS | 6 cases green. Mutant M1 (match on `tree.after` only) → `1 failed, 5 passed` (the changed-mid-run case goes red). |
| AM3-AC6 | `commit -a`, `commit -- f` use git's index | PASS | 3 tests green. Mutant M3 (the hook calls `tree-hash` instead of `write-tree`) → `2 failed, 1 passed`. |
| AM3-AC7 | a record in another checkout never counts | PASS | `test_ac7…` green, with a real `git worktree add` |
| AM3-AC8 | hostile records warn by escaped path; RED-match rows | PASS | 15 hostile cases plus the control-character case, AC8(i) and AC8(ii), all green. Mutant M4 (a newer unreadable record no longer suppresses an older GREEN) → `1 failed`. Deviations are judged below. |
| AM3-AC9 | the lookup exits 3 → refused, names `--no-verify`; recorder missing → WARN; missing object → "could not be hashed" | PASS | 3 tests green. My own probe: a deeply nested record → `commit-check: internal error: RecursionError`, rc=2, and the hook refuses with `the check could not run (exit 2)`. It fails closed, with no traceback (parked P1). |
| AM3-AC10 | `--no-verify` still skips | PASS | `test_ac10…` green, both before and after (it is a pin) |
| AM3-AC11 | the new check adds to `fail` and does not short-circuit | PASS | The output holds both `FAIL scripts/memory_lint.py` and `FAIL verify record` (test green) |
| AM3-AC12 | real `finalize` output: INCOMPLETE passes, RED refused | PASS | The test runs the real `finalize --tier full` over a TODO step and over an exit-1 step. Both green. |
| AM3-AC13 | `tests/framework/test_pre_commit.py` unchanged and green | PASS | `diff -q` shows the file is unchanged. It is part of the 133 that passed. |
| AM3-AC14 | a non-bootstrap token in `doc/qa/QA-x.md` → refused in both modes | PASS | 2 cases, red-first then green |
| AM3-AC15 | exclusions and roots equal CI's | PASS | 8 pass rows (before and after) and 5 refuse rows (red-first then green) |
| AM3-AC16 | template mode: the five pass; mixed line, project mode, index decides, near-miss refused | PASS | All rows green. Mutant M2 (template mode skips the scan) → `7 failed, 9 passed` across AC14, AC16 and AC21. |
| AM3-AC17 | the scan reads what is committed | PASS | (a) to (e) green. (c) was red-first. |
| AM3-AC18 | shapes neither tool matches pass; binary passes; newline path quoted on one line; 20 + "… and N more" | PASS | All green. The 25-hit test asserts lines 1–20 exactly and `… and 5 more`. |
| AM3-AC19 | `git grep` exit 2 → refused with the exact message | PASS | Green. Deviation judged below: I measured that git puts its exec-path first on a hook's PATH. |
| AM3-AC20 | drift test: pattern, roots, exclusions, allowed tokens; the helper names a planted difference | PASS | `test_pre_commit_placeholder_scan_equals_ci_gate_3_and_bootstrap` and its 3 plants are green |
| AM3-AC21 | both real incidents refused, never vacuous | PASS | Both ran (not skipped). Manual replay in this repo, outside the tests: 7661338 → `FAIL placeholder scan — 2 line(s)` (QA-bugfix-gate3-worktree.md:20, :21), rc=1, HEAD unmoved; e6b4daa → `1 line(s)` (SPEC-jarvis-coordinator.md:58), rc=1, HEAD unmoved |

### The author's declared deviations

1. **AC19 through `GIT_EXEC_PATH`, not only a `PATH` shim. Matches the intent.** I measured it in a scratch repo whose pre-commit hook prints its own `PATH`. It printed `HOOK-PATH-HEAD=/Library/Developer/CommandLineTools/usr/libexec/git-core` and `HOOK-git=…/libexec/git-core/git`. Git prepends its exec-path, so a `git` shim that is only on `PATH` is never reached from inside the hook, and the spec's literal setup could not make `git grep` fail. The test sets `GIT_EXEC_PATH` to the shim's directory. The shim exits 2 for `grep` only, and for every other command it unsets `GIT_EXEC_PATH` and runs the real git. Before the change this test failed, because the old hook printed no `FAIL placeholder scan` line.
2. **AC8 prints `\x0a`, not `\n`. Matches the intent.** The spec's Functional Behavior says "Escaping reuses the recorder's existing `_escape`". That function (`scripts/verify_record.py:725`) turns every control character, newline included, into `\xNN`. So AC8's "`\n`/`\xNN`" and the design section disagree inside the spec itself. The author followed the design section, and the goal of AC8 still holds: one display line, and no forged line. The test asserts `"\nforged" not in out`.
3. **AC8: a symlinked run directory warns instead of being skipped silently. Matches the intent.** Functional Behavior step 2 says "skip D if it is a symlink". AC8 lists "a run directory that is a symlink" among the cases that must pass with a `WARN` naming the path. The AC is the testable contract, and the WARN is the safer reading: such a run is never silently counted as a pass (D6). Report the conflict to ba-sa as a spec wording fix. It is not a defect in the code.
4. **Template mode works token by token (awk), not by stripping the five and re-matching (sed). Matches R9.** R9 says "hits whose only tokens are the five … are allowed. A line that also holds any other token is still a hit." The awk loop does exactly that over gate 3's own token shape, and it prints the original line, as the spec requires. There is one case where it differs from the pseudocode in the spec. On the line `x &lt;ABC&lt;PROJECT&gt;DEF&gt; y` in template mode, the hook passed (`moved=yes`), while the spec's `sed` form leaves `&lt;ABCDEF&gt;` and would refuse it. Under gate 3's regex, that line holds only one token, `&lt;PROJECT&gt;`, so the per-token reading is the literal R9 one. The line is not shaped like a mistake (parked P2). Every AC16 row, near-misses included, behaves the same under both readings.

### Ease of use in this repo

These ran on the scratch clone, which is in template mode (the staged `AGENTS.md` holds the PROJECT placeholder, 22,813 bytes). A scratch registry was built from the documents' own `Approval:` keys so that `verify_approvals.py` passes. It is timing scaffolding, not an approval.

- Committing the author's 7 files through the new hook: rc=0, real 0.97 s, output only `WARN no gate record for the staged tree …`. The real repo's 18 gate-3 lines (PROJECT ×14, FRONTEND_REPO ×7, FRONTEND_REPO_PATH ×3, PACKAGE ×3, BACKEND_REPO_PATH ×2) are all allowed in template mode.
- `git commit -a` of a doc edit: rc=0, real 0.72 s.
- `git commit -- doc/memory/README.md` with `README.md` staged as well: rc=0, real 0.74 s. The commit held only `doc/memory/README.md`, and `README.md` stayed staged.
- The hook alone, 5 runs each: new hook 0.53–0.59 s, old hook 0.33–0.35 s, so about +0.2 s. Split by piece: `write-tree` 0.01 s, `commit-check` with no `.verify` 0.11 s (mostly Python start-up), the scan 0.05 s, the template-mode test 0.02 s. That is more than the spec's estimate (about 0.04 s plus "well under 0.1 s"), but still well under a second. Not a defect.

### No placeholder literal added to the scanned roots

I compared the gate-3 scan of the tree before the change (`6ec6b4b`) with the tree after (the overlay commit): 18 lines each, and `diff` reported them identical. Counting per file, `.githooks/pre-commit` holds one token-shaped literal (`&lt;PROJECT&gt;` in the template-mode test), but `.githooks/` is not a gate-3 root. The test files are outside the roots. `ADAPTERS.md` and the memory file hold 0.

### ADAPTERS.md

Line 63 (the adapter-file line) and line 68 (the C1 row) add both checks: "the newest gate record for the staged tree is not RED" and "no placeholder CI gate 3 would fail on". The new block lists 13 declared limits, one for one with the spec's "Declared limits" 1–13 (missing record warns · edit after RED warns · partial staging · agent-writable records · `--no-verify` · `ended_at` then name · other checkouts never count · template mode trusts one line · the scan sees the commit · `-I` · `LC_ALL=C` · drift caught in `tests/ci/` · quoted paths). It also names both test files. `memory_lint.py` passed inside the hook runs above, with the new `mechanism:` line.

## Defects (if FAIL)

None that block. One in scope, Low:

| Severity | Description | Where | Back to |
|---|---|---|---|
| Low | D1. The AC4c pass row (`[RED-GREEN-False]`) asserts only that the commit passed, so it was green on the old hook too (red-first run above). The spec's RED-FIRST rule lists no exception for it. Fix: in the pass branch, add `assert "verify record: GREEN" in out`. It does not change the verdict: the sibling row and AC4a cover the behaviour. | `tests/framework/test_pre_commit_verify_record.py:207` | ai-engineer (optional; can ride with the next touch) |

Parked (outside AM3-AC1…AC21, or in the deliberate-fraud class):

| # | Observation | Where | Why parked |
|---|---|---|---|
| P1 | A record nested very deeply (200,000 `[` in 400 KB, under the 1 MiB cap) makes `json.loads` raise `RecursionError`. `commit-check` exits 2, and the hook refuses with `the check could not run (exit 2)`. Step 2 of the spec would call it "not a JSON object → unreadable → WARN". | `scripts/verify_record.py` `_readable_record` (the `except` lists `OSError, UnicodeDecodeError, ValueError` only) | AC8 does not list it. It fails closed, prints no traceback, and `--no-verify` is the escape. A crash or a typo never writes such a file. If it matters, the fix is adding `RecursionError` to the `except`. |
| P2 | Template mode allows `&lt;ABC&lt;PROJECT&gt;DEF&gt;`, a token nested inside a non-token. The spec's `sed` sketch would refuse it. | `.githooks/pre-commit`, the awk block | Not shaped like a mistake. It matches R9's per-token wording. |
| P3 | The drift test checks that CI's pattern and roots strings appear somewhere in the hook text, not that they sit on the `git grep` line. A copy left in a comment would satisfy it. The awk regex, `<[A-Z_][A-Z_][A-Z_][A-Z_]*>`, is a second spelling of the pattern that is not drift-checked. | `tests/ci/test_ci_examples.py::_hook_gate_3_drift` | A deliberate-evasion shape, outside AC20's wording. |
| P4 | Spec wording: Functional Behavior step 2 ("skip D if it is a symlink") and AC8 ("warn" for a symlinked run directory) disagree. So do AC8's `\n` and the `_escape` it says to reuse (`\x0a`). | the spec | For ba-sa or the coordinator. The code follows the AC and the design. |

## Hostile inputs tried

- A deeply nested JSON record (400 KB) → hook refuses, `commit-check: internal error: RecursionError`, rc=2 (P1)
- `x &lt;ABC&lt;PROJECT&gt;DEF&gt; y` in `.claude/p4.md`, template mode → passes (P2)
- A pre-commit hook in a scratch repo printing its `PATH`, with a failing `git` shim first on `PATH` → the hook's `git` resolves to `…/libexec/git-core/git` (backs deviation 1)
- `git -c color.grep=always`, `color.ui=always`, `grep.patternType=perl`, `grep.lineNumber=false`, `grep.fullName=false` → scan output unchanged in shape (`--no-color`, `-G` and `-n` are explicit). `grep.column=true` adds `:col:` to each line, which is still reported as a hit.
- Four planted mistakes (M1 to M4 above): each killed by at least one test
- Incident replays 7661338 and e6b4daa in this real repo → both refused, HEAD unmoved

## Exit gate

I ran `scripts/verify-full.sh` on the scratch clone with the change committed, with HOME and `APPROVAL_LOG` at scratch paths. That clone's HEAD is the author's 7 files plus my two probe commits on top (`probe -a` and `probe path`, each adding one junk line to `doc/memory/README.md`). The output:

- `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, rc=0.
- The three TODO steps are this template's own by design (F6).
- The configured steps all passed: `OK hooks` (1376 passed), `OK ci-examples` (36 passed), `OK scar-forge`, `OK coordinator` (160 passed), `OK framework` (memory: 0 problems).
- Record: `.verify/runs/20261022T105209Z-86741/record.json`.

This is INCOMPLETE, not GREEN.

**QA spawn gate check:** I ran `guard_agent_spawn._review_problem(<this file>, _spec_under_test("Spec: doc/specs/SPEC-verify-tiers-merge-gate-am3-commit-on-red.md"))`. It returned `None`, so the gate opens. The same call with the am2 spec was refused: `its Upstream: does not name SPEC-verify-tiers-merge-gate-am2-scanner-scope.md`.

## Approval history

- **2026-10-22 — drafted.** Reviewer run `aa313d07504ca9746`, from the spec, the author's 7 files (read and diffed against `6ec6b4b`), and commands run in a scratch clone. The author's conversation was not read.
