# QA Report: Verify tiers, Amendment 3: pre-commit refuses a commit on a RED record or a gate-3 placeholder

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate-am3-commit-on-red.md
Review: doc/qa/REVIEW-verify-tiers-merge-gate-am3-commit-on-red.md
Date: 2026-10-22

## Verdict: PASS

All 21 criteria (AM3-AC1 to AM3-AC21) hold. The full suite passed (`2111 passed, 1 skipped`, the skip is unrelated). The exit gate reported `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, rc=0. That is INCOMPLETE, not GREEN. The three TODO steps are left unconfigured in this template on purpose (spec F6), and every configured step passed. All six end-to-end checks from the brief behaved as the spec says, in a scratch clone with the hooks turned on: a real RED verify-full record blocks the commit, GREEN and INCOMPLETE records pass and print the verdict, no record gives a warning, a staged placeholder is refused, a normal docs commit passes in about 0.9 s, and both incident replays are refused.

Note: the brief does not say whether the human approved the implementation before QA. It is a Tier 1 brief with a PASS review attached. I am recording that gap here and not treating it as a defect.

## Where this ran

- Base: branch `feat/top3-tiers-mechanisms-deny` at `a803721`. The branch moved after the reviewer's run (`6ec6b4b`). None of the 7 changed paths differ between the worktree's base `8482670` and `a803721` (`git diff --stat 8482670 a803721 -- <the 7 paths>` printed nothing), so copying the files on top undid nothing.
- Change: the 7 files from worktree `agent-a2efb18032c362ade` were copied onto a scratch clone and committed through the new hook as `1688cac`. `git diff --stat a803721 1688cac` shows `7 files changed, 1096 insertions(+), 3 deletions(-)`, the same per-file counts as the worktree's own diff (pre-commit +49, ADAPTERS 20, memory 2, verify_record +80, test_ci_examples +62, plus the 2 new test files).
- Environment: `HOME` and `APPROVAL_LOG` pointed at scratch paths, `VERIFY_*` unset, and `git config core.hooksPath .githooks`. The scratch registry was generated from the documents' own `Approval:` keys so that `verify_approvals.py` passes. It is scaffolding for the commit tests, not an approval. The real registry was never read or written.
- Incident commits `7661338` and `e6b4daa` are reachable in the clone, so AM3-AC21 ran and was not skipped.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AM3-AC1 | matching RED full record → refused, names record | PASS | `test_ac1…` green in the suite. Red on the old hook. End to end with a **real** verify-full RED run (see E2E-1): `pre-commit: FAIL verify record — the newest gate run for the staged tree is RED (.verify/runs/20261022T110628Z-71938/record.json)`, rc=1, HEAD unchanged |
| AM3-AC2 | INCOMPLETE / GREEN / OK pass, verdict printed verbatim | PASS | Suite green. Real records: `verify record: GREEN for the staged tree (…110651Z-73598…)` and `verify record: INCOMPLETE for the staged tree (…110700Z-74356…)`, both rc=0 |
| AM3-AC3 | EMPTY handoff → WARN, no `verify record:` | PASS | Suite green, red-first |
| AM3-AC4 | `ended_at` orders the records; on a tie, the later directory name wins | PASS | Suite green. Low test note D1 below (the AC4c pass row was green on the old hook as well) |
| AM3-AC5 | stale / none / empty / fast null tree / changed mid-run → one WARN naming verify-full | PASS | Suite green. Own probe: a RED `fast` record **with** a matching tree → `WARN no gate record`, rc=0 (fast never counts, R2). A matching RED record with tier `merge` → WARN, rc=0 |
| AM3-AC6 | `commit -a` and `commit -- f` use git's index | PASS | Suite green. Own probe: with the RED tree staged and an unstaged edit elsewhere, plain `git commit` → refused (the index is the RED tree). `git commit -a` on that state → WARN, passes (a different tree; declared limit 2) |
| AM3-AC7 | a record in another checkout never counts | PASS | Suite green |
| AM3-AC8 | hostile records warn by escaped path; the RED-match rows | PASS | Suite green |
| AM3-AC9 | lookup exits 3 → refused and names `--no-verify`; recorder missing → WARN; missing object → "could not be hashed" | PASS | Suite green |
| AM3-AC10 | `--no-verify` still skips the hook | PASS | Suite green (passes before and after, as a pin should). See also E2E-6 |
| AM3-AC11 | the new check adds to `fail` and does not stop the other checks | PASS | Suite green. Own probe: a staged rename into `doc/memory/` plus a token printed both `FAIL scripts/memory_lint.py` and `FAIL placeholder scan` in one run |
| AM3-AC12 | real `finalize` output: INCOMPLETE passes, RED is refused | PASS | Suite green. Also shown with the whole real `verify-full.sh` (E2E-1, E2E-2) |
| AM3-AC13 | `tests/framework/test_pre_commit.py` unchanged and green | PASS | Not in the diff (7-file list above). Green in the full suite |
| AM3-AC14 | non-bootstrap token in `doc/qa/QA-x.md` → refused in both modes | PASS | Suite green, red-first. E2E-4 |
| AM3-AC15 | exclusions and roots equal CI's | PASS | Suite green. The pass rows pass before and after. The refuse rows were red-first |
| AM3-AC16 | template mode: the five pass; a mixed line, project mode, the index deciding, and near-misses are refused | PASS | Suite green. Own probe: right after `scripts/bootstrap.sh` (project mode), the commit passed with only the WARN line, rc=0, 0.84 s |
| AM3-AC17 | the scan reads what is committed | PASS | Suite green |
| AM3-AC18 | shapes neither tool matches pass; binary passes; newline path quoted; 20 lines + "… and N more" | PASS | Suite green. Mutants M5 (drop `-I`) and M6 (`head -n 25`) each turn 1 test red |
| AM3-AC19 | `git grep` exit 2 → refused with the exact message | PASS | Suite green. The `GIT_EXEC_PATH` deviation is judged in the review, and I agree with it |
| AM3-AC20 | drift test, plus the helper naming a planted difference | PASS | Suite green. Against the old hook: `FAILED …test_pre_commit_placeholder_scan_equals_ci_gate_3_and_bootstrap` |
| AM3-AC21 | both real incidents refused, never vacuous | PASS | Ran, not skipped (`-rs` lists only `test_doc_contracts.py:193`). Manual replays, E2E-6 |

## End-to-end checks (scratch clone, hooks on)

- **E2E-1, real RED.** I staged a failing test (`assert 1 == 2`) and a `scripts/verify.conf` whose `STEPS` runs only that test, then ran `scripts/verify-full.sh`. Output: `EXIT GATE RED (exit 1)`, rc=1, record `.verify/runs/20261022T110628Z-71938/record.json` with `tree.before = tree.after = 925cc549…` = `git write-tree`. Then `git commit` → `FAIL verify record — the newest gate run for the staged tree is RED (.verify/runs/20261022T110628Z-71938/record.json)`, rc=1, HEAD unchanged.
- **E2E-1b, the incident-1 shape with the default steps.** I staged `git show e6b4daa:doc/specs/SPEC-jarvis-coordinator.md` over the current file and ran the unmodified `scripts/verify-full.sh` (all default steps). Output: `OK hooks` (1388 passed), `FAIL ci-examples` (gate 3 caught the literal, which is the incident's own cause), `EXIT GATE RED (exit 1)`, record `.verify/runs/20261022T111746Z-56503/record.json` with `tree.before = tree.after = 36b5d344…` = `git write-tree` (no untracked, unignored files were left behind). Then `git commit` printed **both** `FAIL verify record — the newest gate run for the staged tree is RED (.verify/runs/20261022T111746Z-56503/record.json)` and `FAIL placeholder scan — 1 line(s)`, with rc=1 and HEAD unchanged. `git commit --no-verify` on the same tree → rc=0 (the AM3-AC10 escape). The `framework` step in this run also printed one failure; see Parked P4.
- **E2E-2, non-RED records.** Fixed the test and re-ran: `EXIT GATE GREEN`, then the commit printed `pre-commit: verify record: GREEN for the staged tree (.verify/runs/20261022T110651Z-73598/record.json)`, rc=0. With a TODO step added: `verify record: INCOMPLETE for the staged tree (…20261022T110700Z-74356…)`, rc=0. Neither printed GREEN for a run that was not GREEN.
- **E2E-3, no record.** The overlay commit itself (no `.verify` directory) → `pre-commit: WARN no gate record for the staged tree — run scripts/verify-full.sh (scripts/verify-handoff.sh when opted in) before committing; CI runs the gate regardless`, rc=0. A fresh `git init` of the template (first commit, template mode) passed the same way, for both sha1 and sha256 object formats (tree hash 40 and 64 characters).
- **E2E-4, a staged placeholder.** A new `doc/qa/QA-probe.md` holding `&lt;WIDGET_NAME&gt;` → `FAIL placeholder scan — 1 line(s) CI gate 3 would fail on:` / `doc/qa/QA-probe.md:3:Replace &lt;WIDGET_NAME&gt; before shipping.`, rc=1, HEAD unchanged. The same text written as the HTML entity `&amp;lt;ABC_DEF&amp;gt;` passed. A token inside a fenced code block, and one in a CRLF file, are refused. CI refuses both as well.
- **E2E-5, a normal docs commit (template mode).** `git commit -qam` of one line in `doc/memory/README.md`, 3 times: real 0.91 s, 0.98 s, 0.93 s, rc=0, output only the WARN line. The hook alone, run back to back with the old hook (5 pairs): old 0.43–0.67 s, new 0.64–0.73 s. All of these ran while the full suite was running in the background, so they are upper bounds. The reviewer measured the hook alone on a quiet machine: 0.53–0.59 s.
- **E2E-6, incident replays.** `git show 7661338:doc/qa/QA-bugfix-gate3-worktree.md` staged → rc=1, HEAD unchanged, `FAIL placeholder scan — 2 line(s)` (lines 20 and 21). `7661338:doc/qa/REVIEW-bugfix-gate3-worktree.md` → refused, 1 line (27). `e6b4daa:doc/specs/SPEC-jarvis-coordinator.md` → rc=1, HEAD unchanged, 1 line (58). The record check printed nothing for these, which is correct: no gate had run on those trees.

## Test Run

```
# scratch clone at 1688cac (a803721 + the 7 files), HOME/APPROVAL_LOG scratch, VERIFY_* unset
python3 -m pytest tests -q -p no:cacheprovider
2111 passed, 1 skipped in 711.67s (0:11:51)          rc=0
  skipped: tests/framework/test_doc_contracts.py:193 (agent_time.REWORK_CAUSES is the source now)

scripts/verify-full.sh > log
EXIT GATE — full verify
  TODO lint / format / tests   not configured — this step verified NOTHING
  OK   hooks        (341s) 1388 passed in 339.35s
  OK   ci-examples  (8s) 36 passed in 7.28s
  OK   scar-forge   (1s)
  OK   coordinator  (8s) 160 passed in 7.16s
  OK   framework    (294s) memory: 0 problem(s)
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
record: .verify/runs/20261022T111809Z-59094/record.json          rc=0

# red-first, the 2 new files against the old hook and old recorder (a803721)
64 failed, 24 passed in 117.98s
```

The 24 that passed on the old hook are the ones the spec allows (AC10, AC15 pass rows, AC16a, AC17 a/b/d/e, AC18 pass rows) plus one it does not: `test_ac4c_same_ended_at_the_later_directory_name_wins[RED-GREEN-False]` (D1). This matches the reviewer's count once `tests/ci` is left out.

## Defects (if FAIL)

None. Test note (Low, does not change the verdict, recorded as the brief asks): **D1.** The AC4c pass row (`[RED-GREEN-False]`, `tests/framework/test_pre_commit_verify_record.py:207`) only checks that the commit passed, so it was green against the old hook too. I confirmed this in my own red-first run. Its sibling row and AC4a cover the behaviour. The fix is `assert "verify record: GREEN" in out` in the pass branch. Owner: ai-engineer, optional, can go in with the next change to that file.

## Mutation probes (my own)

| # | Mutant | Result |
|---|---|---|
| M5 | the hook's `git grep` without `-I` | 1 failed, 87 passed (caught, the AC18 binary row) |
| M6 | `head -n 25` instead of 20 | 1 failed, 87 passed (caught, the AC18 overflow row) |
| M7 | `git grep` without `LC_ALL=C` | 88 passed (not caught: this machine's locale already keeps `[A-Z]` to ASCII. This is declared limit 11, so I parked it) |

## Edge Cases Probed

- Matching RED `handoff` record → refused, names `…-handoff/record.json`.
- Matching RED `fast` record with a real tree (not null) → WARN, passes. Fast never counts (R2).
- Matching RED record with tier `merge` → WARN, passes. Only `full` and `handoff` count, as the spec says.
- `git commit` from the subdirectory `doc/memory/` with a matching RED record → refused (the hook `cd`s to the top level).
- A repo path that contains a space → RED refused, and a commit with no record passes.
- The first commit in a fresh repo (no HEAD), sha1 and sha256 → RED refused, and with no record it passes with the WARN line.
- Right after `scripts/bootstrap.sh` (the staged `AGENTS.md` no longer holds the PROJECT token, so project mode) → passes. The hook does not block a freshly bootstrapped project.
- 300 non-matching GREEN records plus 1 matching RED → refused. `commit-check` alone took 0.21 s.
- An older GREEN and a newer RED on the same tree → refused.
- The HTML-entity escape of a token (`&amp;lt;ABC_DEF&amp;gt;`) → passes. A raw token in a fenced code block or a CRLF file → refused, which matches CI.
- A rename into `doc/memory/` plus a token → both memory-lint and the placeholder scan FAIL in the same run (no short-circuit).

## Parked

| # | Observation | Why parked |
|---|---|---|
| P1 | M7: no test fails if `LC_ALL=C` is dropped from the scan, because this machine's locale already makes `[A-Z]` ASCII-only. | Outside AM3-AC1…AC21. Declared limit 11. A mistake here could only make the hook stricter than CI on some runner, never let a placeholder through |
| P2 | The reviewer's P1 to P4 (a `RecursionError` on deeply nested JSON fails closed, a nested-token line in template mode, the drift test matching a string anywhere in the hook, spec wording in AC8 versus step 2) stand. I did not re-run them. | Already parked in the review |
| P4 | In the E2E-1b run (incident-1 replay, which ran at the same time as the main verify-full in a second clone), the `framework` step printed one failure: `FAILED tests/framework/test_pre_commit_placeholders.py::test_ac15_paths_next_to_the_exclusions_are_refused[AGENTS.md]`. The commit had gone through with only the WARN line. I could not reproduce it. In that same clone and on the same tree, the parametrised test passed 3 times out of 3 (`5 passed`), the whole file passed (`43 passed`), and `tests/framework` passed when run on its own (`511 passed, 1 skipped`). The main exit-gate run's `framework` step was also green. My best guess is interference between two pytest sessions sharing one temp root while three runs went at once, but I did not prove that. | Not reproduced, so it is not a defect against the change. If it appears again in a run with nothing else going on, it becomes a `test-gap` or `env-flaky` item for ai-engineer |
| P3 | Hook timing went from roughly 0.45 s to 0.7 s while the machine was loaded (about +0.2 s, the same as the reviewer's quiet-machine figure). This is above the spec's "well under 0.1 s" estimate for the lookup. | Not a criterion. The commit still finishes in under a second |

## Approval history

- **2026-10-22 — drafted.** QA run, from the spec, the review, and the author's 7 files overlaid on `a803721` in a scratch clone. Every result above comes from a command run in that clone. The author's conversation was not read.
