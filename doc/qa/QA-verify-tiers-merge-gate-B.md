# QA Report: verify tiers — increment B (the handoff tier)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Date: 2026-10-20

## Verdict: PASS

Re-verified at `184b3f4`, after the rework of D1 (see "Re-verify" below). D1 is closed: a malformed JUnit report now gives exactly one `HANDOFF TIER RED` banner, exit 1, and a `record.json` with `verdict: RED`. No traceback. All twelve B-ACs hold. My own `scripts/verify-full.sh` run is INCOMPLETE with exit 0 and no RED step. The first-round FAIL at `daf5649` is kept below as history.

The first round's approval note is withdrawn. The owner ruled that there is no owner review between engineer and QA (`doc/memory/lean-gates-risk-based-qa.md`).

## Re-verify (2026-10-20, `184b3f4`)

Rework diff `daf5649..184b3f4`: `scripts/verify-handoff.sh` and `scripts/verify_record.py`, plus two regression tests in `tests/hooks/test_verify_handoff.py` and a changed `test_d10` in `tests/hooks/test_verify_tiers.py`.
- `junit_counts` now counts an unreadable report as one failure (`failed: unreadable JUnit report <file> (<error>)`). It does not count it as a test.
- The wrapper trusts the recorder's exit code only when the last line is a matching banner and `record.json` exists. Otherwise it prints `HANDOFF TIER RED — recorder failed (finalize exit N)`.
- `test_d10` now plants its crash in the copied recorder, because a broken JUnit file no longer crashes it. Its assertions are unchanged, so the test is not weaker.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| D1 | Broken or truncated JUnit gives no traceback, a banner and a record | CLOSED | My own repro, not the engineer's test (`/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/qa2/repro.py`). Truncated, empty, binary, one good plus one broken file, a directory named `x.xml`, and a mode-000 file all gave rc 1, exactly one banner `HANDOFF TIER RED — ran N of 5 …`, 1 record with `verdict=RED`, no `Traceback` on stderr, and no `GREEN`. |
| B-AC1–B-AC11 | unchanged | PASS | 335 passed in the brief's command (below). Their tests are unchanged since `daf5649`. |
| B-AC12 | record with `tier: "handoff"` and both tree hashes | PASS | `test_b12_*` passed. A record is now written on the broken-JUnit path too (repro above, and `test_regression_a_broken_junit_report_*`). |
| Hostile | never a crash, leak or false GREEN | PASS | D1 closed. `test_regression_a_recorder_that_exits_1_without_a_verdict_is_red` covers a recorder that exits 1 with no verdict. |

Counts: B-AC1–B-AC12 PASS (12/12); hostile row PASS; D1 closed.

```
$ python3 -m pytest tests/hooks/test_verify_handoff.py tests/hooks/test_verify_tiers.py -q -p no:cacheprovider   (worktree, 184b3f4)
335 passed in 83.26s (0:01:23)

$ scripts/verify-full.sh   (worktree, 184b3f4)
  TODO lint / format / tests   not configured — this step verified NOTHING
  OK   hooks             (133s) 893 passed in 132.59s (0:02:12)
  OK   ci-examples       (2s) 19 passed in 0.93s
  OK   scar-forge        (1s)
  OK   coordinator       (2s) 111 passed in 1.61s
  OK   framework         (44s) memory: 0 problem(s)
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
exit=0     (git status --short afterwards: empty)
```

Test additions: none. The engineer's regression tests already pin D1, and my repro adds variants (binary, mixed, directory, unreadable file) that fail closed in the same way.

## Round 1 (history, `daf5649`)

### Criteria Results

Code: worktree `.claude/worktrees/agent-a40a64389abbb86b6`, branch `worktree-agent-a40a64389abbb86b6`, HEAD `daf5649`.

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| B-AC1 | Selector gets exactly `{a.py, b.py, c.py}`; banner `ran N of M (selected by machine from the diff against <base>)` | PASS | `test_b1_*` in the 93-pass run. My probes: the same selection and banner on a detached HEAD, from a repo root path with spaces and unicode, and in 8 concurrent runs (8 distinct record dirs, all `ran 3 of 5`, rc 0). |
| B-AC2 | Paths the agent leaves out are still selected and named | PASS | `test_b2_*` passed. |
| B-AC3 | A named path adds and never removes | PASS | `test_b3_*` passed. My probes: `../d.py` from `src/` added `d.py`; `./-x.py` was accepted; an empty argument added `.`; `/etc/passwd` added `../…/etc/passwd`. Nothing was removed in any case (the oddities are under Parked). |
| B-AC4 | A changed declared input forces the full set, `ran M of M` | PASS | `test_b4_*` passed (7 cases). |
| B-AC5 | No inputs declared → full set, `no untracked inputs declared` | PASS | `test_b5_*` and `test_leak_exported_untracked_inputs_*` passed. |
| B-AC6 | No conf, or tier not `on` → NOT CONFIGURED, exit 3, nothing run; `--status` → `not opted in` | PASS | `test_b6_*` and `test_leak_*` passed. My probe: a conf saved entirely with CRLF line endings → `--status` gives `not opted in`, a run gives rc 3 with the exact line (fails closed). |
| B-AC7 | 0 cases → `HANDOFF TIER EMPTY — ran 0 of M; nothing was verified`, exit 1 | PASS | `test_b7_*` passed. My probe: stub repo with no tests on the full set → `HANDOFF TIER EMPTY — ran 0 of 0; nothing was verified`, rc 1. Real pytest with no tests → `HANDOFF TIER RED — ran 0 of ?`, rc 1 (pytest exits 5). Fails closed. |
| B-AC8 | stdout never has `GREEN` / `suite passes` | PASS | Asserted by `_run` on all 93 runs. My probes checked every run (about 40) for both strings; none contained either. |
| B-AC9 | Base does not resolve → full set, `base <ref> not found` | PASS | `test_b9_*` passed. My probes: shallow clone without the base → `ran 5 of 5 (full collected set — base base not found)`; base fetched at depth 1 → `no common ancestor with base`; unborn HEAD → `base base not found`, full set; a CRLF conf whose base became `base\r` → `base base\x0d not found`, full set. |
| B-AC10 | Planted regression → `HANDOFF TIER RED — ran N of M`, failing id, exit 1 | PASS | `test_b10_*` passed. The reviewer also showed the rework failing first: 10 failed on `eed72b9`. |
| B-AC11 | Banned form in `VERIFY_SELECT_CMD` → exit 2 `BANNED:` | PASS | `test_b11_*` passed. My probes: `-- a.py` → rc 2 `BANNED: --`; `-x.py` → rc 2. |
| B-AC12 | A handoff run writes a record with `tier: "handoff"` and both tree hashes | FAIL (hostile input only) | `test_b12_*` passed for normal runs. On a malformed JUnit file no `record.json` is written (D1). |
| Hostile | Never a crash, leak or false GREEN (brief; the test file's `_run` checks "never a crash") | FAIL | D1: a traceback ends the run. No leak was found (the reviewer's D1 leak stays closed; `PWNED` from a file named `$(touch PWNED).py` was not created). No false GREEN: every crash or odd input exited non-zero or ran a superset. |

Counts: B-AC1–B-AC11 PASS (11), B-AC12 FAIL (1) · hostile-input row FAIL.

## Test Run

```
$ python3 -m pytest tests/hooks/test_verify_handoff.py -q -p no:cacheprovider   (worktree, daf5649)
93 passed in 41.38s

$ scripts/verify-full.sh   (worktree, daf5649)
  TODO lint / format / tests   not configured — this step verified NOTHING
  OK   hooks             (131s) 889 passed in 130.45s (0:02:10)
  OK   ci-examples       (2s) 19 passed in 0.98s
  OK   scar-forge        (1s)
  OK   coordinator       (2s) 111 passed in 1.65s
  OK   framework         (47s) memory: 0 problem(s)
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
exit=0     (git status --short afterwards: empty)
```

This is the expected INCOMPLETE with no RED step. It is necessary for a PASS but does not cancel D1: no existing test covers that input, so the gate cannot see it.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Medium | D1 (CLOSED at `184b3f4`, see Re-verify). A malformed JUnit report crashes the tier with no banner and no record. Repro: B-AC1 fixture (`_repo`) with `VERIFY_SELECT_CMD='python3 scripts/bad.py'`, where `bad.py` writes `<testsuites><testsuite><testcase name="a"` to `$VERIFY_JUNIT_DIR/x.xml` (an empty file does the same). Result: rc 1; stdout ends `  OK   select            (0s)`; stderr ends `xml.etree.ElementTree.ParseError: unclosed token: line 1, column 23`; the run dir has no `record.json`. Cause: `junit_counts` raises out of `finalize_handoff`, and Python exits 1. The wrapper's `case "$fin_rc"` branch for exit 0 or 1 treats that 1 as a normal verdict, so its `HANDOFF TIER RED — recorder failed` branch never runs. `verify-full.sh` survives the same crash because it reads the `VERDICT=` line. Realistic trigger: pytest killed mid-write (timeout, OOM, disk full). | scripts/verify-handoff.sh (final `case "$fin_rc"`); scripts/verify_record.py `junit_counts` / `finalize_handoff` | ai-engineer | missed-ac |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

## Edge Cases Probed

Probe scripts (not added to the repo): `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/qa/probe.py` and `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/qa/probe2.py`. Each one imports the worktree test file's own `_repo`/`_conf_text` fixtures.

- 8 concurrent runs in one repo → 8 distinct run dirs, each `ran 3 of 5`, rc 0, no tree-change RED.
- Untracked files named `my file.py`, `ünï.py`, `-x.py`, `--lf`, `new\nline.py`, `$(touch PWNED).py` and NFD `é.py` → all reached the selector intact. `-x.py` became `./-x.py` and `--lf` became `./--lf`. No command injection.
- Named `my file.py`, `./-x.py`, NFC `é.py` against an NFD file → accepted with no duplicate. Named `-x.py` → rc 2 `BANNED: -x.py — hides the other failures`. Named `-- a.py` → rc 2.
- Repo root path with spaces, unicode and `-lead` → normal selection.
- Detached HEAD → normal selection.
- Shallow clone (base missing, or base with no merge-base) → full set with the reason given.
- Unborn HEAD (no commits) → full set, `base base not found`.
- Repo with no tests: stub → EMPTY rc 1; real pytest → RED rc 1.
- CRLF conf: all lines CRLF → not opted in / rc 3; CRLF on every line except the tier switch → full set because the base reads `base\r`, rc 0. Neither case runs less than it should.
- Empty or truncated JUnit file → D1.

Test additions: none. A regression test for D1 would turn the gate RED in the engineer's worktree. The repro above is precise enough to become `test_regression_*` with the fix.

## Parked

Outside the B-ACs; for the backlog owner, not rework. The reviewer's P2–P7 stay parked unchanged.

- **Q1 (Low).** Select mode never checks that N ≤ M. A collect command that disagrees with the selector prints `ran 3 of 0` or `ran 10 of 5` with rc 0.
- **Q2 (Low).** A CRLF conf is reported as `this project has not opted in`, which hides the real cause. In a partly CRLF conf the base becomes `base\r` and the tier silently runs the full set. Both fail closed; a CR check with its own message would help.
- **Q3 (Low).** A named path outside the repo (`/etc/passwd`) is passed to the selector as `../../…/etc/passwd`. An empty argument becomes `.` (everything), but the run is still labelled "selected by machine".
- **Q4 (Low).** A file whose name starts with `-` cannot be named directly. `-x.py` is rejected as `BANNED: -x.py — hides the other failures`, a message about the `-x` flag, not the path. `./-x.py` works.
- **Q5 (Low, outside B).** `verify-fast.sh` hands its exit to `finalize --tier fast` through `exec`, so the same malformed-JUnit traceback probably reached the fast tier with no banner. The rework fixed the shared `junit_counts`, which probably closes the parse crash there too. I did not probe the fast tier in either round.

Parked: Q1–Q5 above; reviewer's P2–P7 unchanged.
Outside Files: none.

## Approval history

- **2026-10-20 — drafted.** By qa from the spec's Increment 4, the reviewer's PASS at `daf5649`, and this run's own commands. Verdict FAIL on D1.
- **2026-10-20 — re-verified.** By qa at `184b3f4` after the REWORK of D1. D1 is closed and B-AC1–B-AC12 pass. Verdict PASS. Awaiting the human.
