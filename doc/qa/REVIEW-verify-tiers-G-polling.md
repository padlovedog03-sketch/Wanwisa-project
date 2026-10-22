# Review: Verify tiers — increment G (no hand-written polling, R26–R28)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Author-run: 18aee03
Reviewer-run: a7f53e8418391b57c
Date: 2026-10-22

Verdict: PASS

## Summary

All eight Part G criteria (G-AC1 to G-AC8) hold at HEAD `ef1f717`. Each one rests on a command run in this review. This is a close-out review: the change was QA-passed earlier (`doc/qa/QA-verify-tiers-G-polling.md`) before the reviewer gate existed, so this is not a re-audit.

## Read from

- Upstream: `doc/specs/SPEC-verify-tiers-merge-gate.md` (Status: Approved, `spec-verify-tiers-merge-gate-2026-10-20`), increment 3 table, G-AC1 to G-AC8.
- Change: `18aee03` (`git show --stat`: guard_bash.py, ADAPTERS.md, engineering-loop SKILL.md, test_doc_contracts.py, new test_guard_bash_polling.py), reviewed as it stands at HEAD `ef1f717`. Ancestry was checked with `git merge-base --is-ancestor`: both `18aee03` and `fe41326` are ancestors of HEAD. Since 18aee03, `guard_bash.py` has changed once more, in `8cccea4` (delegated-autonomy B, merged via fe41326). The Part G tests below were run against that later file.
- Not read: the author's conversation. I did not relay the QA report's results. I re-ran them.

## Criteria Review

Suite command, run unfiltered by file path: `python3 -m pytest tests/hooks/test_guard_bash_polling.py tests/hooks/test_guard_bash_matrix.py tests/hooks/test_guard_bash_bypasses.py tests/framework/test_doc_contracts.py -q` gave `271 passed, 1 skipped`. The one skip is `test_doc_contracts.py:193` ("agent_time.REWORK_CAUSES is the source now"). It belongs to Part J, not G.

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| G-AC1 | Polling loops exit 2. The message names R26 and says to end the turn or do independent work. RED-FIRST. | PASS | Suite green. Direct probe of `for i in $(seq 20); do cat s; sleep 5; done` gave rc=2, and stderr says `rule R26`, `hand-written polling loop`, and "end your turn or do independent work until the completion notification arrives". For red-first, the new test file was run against a `git archive 18aee03^` tree: `66 failed, 86 passed`. |
| G-AC2 | Non-polling loops and single waits exit 0 | PASS | Suite green. Probes: `while read l; do echo $l; done < f` gave rc=0. `sleep 60 && cat out.log` gave rc=0. `for f in *.py; do wc -l $f; done; sleep 2` (sleep after the loop) gave rc=0. `echo "sleep"; for x in a; do echo $x; done` gave rc=0. |
| G-AC3 | `ALLOW_DESTRUCTIVE=1` does not waive R26 | PASS | Probe `ALLOW_DESTRUCTIVE=1; while true; do sleep 1; done` gave rc=2. Suite green. |
| G-AC4 | Matrix and bypass tests pass, unchanged | PASS | `git diff --stat 18aee03^ 18aee03 -- tests/hooks/test_guard_bash_matrix.py tests/hooks/test_guard_bash_bypasses.py` is empty, and so is the same diff from 18aee03 to HEAD. Both files pass inside the 271. |
| G-AC5 | ADAPTERS.md declarations for adapters A and B | PASS | `grep -n "R26\|completion notification" doc/framework/ADAPTERS.md`: line 26 `R26 polling guard: enforced`, line 27 `completion notification: yes`, line 75 `R26: no enforcement` with fallback (rule text plus R37) and what is weaker, line 76 `completion notification: no` with foreground-timeout substitute. Doc-contract test green. |
| G-AC6 | engineering-loop carries the waiting rule | PASS | `.agents/skills/engineering-loop/SKILL.md:83` `## Waiting on background work`: "Never poll … end your turn or do independent work until the completion notification arrives … use the substitute ADAPTERS.md names". Doc-contract test green. |
| G-AC7 | `ALLOW_POLL=1;` at the head waives R26 only | PASS | Probe `FOO=bar ALLOW_POLL=1; while true; do sleep 5; done` gave rc=0. Probe ` ALLOW_POLL=1; while …` (leading space) gave rc=0. A1' still blocking `ALLOW_POLL=1; git reset --hard` on a dirty tree is covered by the green suite. |
| G-AC8 | `ALLOW_POLL=1` anywhere other than the head does not waive. RED-FIRST. | PASS | Probes: `echo ALLOW_POLL=1 && until true; do sleep 1; done` gave rc=2. `until true; do sleep 1; done # ALLOW_POLL=1` gave rc=2. Lowercase `allow_poll=1;` gave rc=2. `ALLOW_POLL=0;` gave rc=2. For red-first, I followed the spec's own method. In a scratch `git archive HEAD` copy, the head check (`not _has_head_override(command, _POLL_OVERRIDE)`) was swapped for `not ("ALLOW_POLL=1" in command)`. `test_guard_bash_polling.py` then gave `12 failed, 140 passed`, and all 12 failures were `test_allow_poll_outside_the_head_does_not_waive_r26[...]`. The unmutated HEAD file is green in the suite run above, and the main tree was never touched (`git status --porcelain` shows only this review file). |

Exit gate: `scripts/verify-full.sh` was run in this review and is **RED, rc=1**: `EXIT GATE RED (exit 1).` The only failing step is `FAIL   ci-examples       (8s) (exit 1)`, with `9 failed, 21 passed`, every one of them in `tests/ci/test_ci_examples.py::test_gate_3_*`. The cause is outside Part G. Gate 3 (the leftover-placeholder scan) finds literal `&lt;ABC_DEF&gt;` text in the committed gate-3 bugfix reports, `doc/qa/REVIEW-bugfix-gate3-worktree.md:27` and `doc/qa/QA-bugfix-gate3-worktree.md:20-21` (from `pytest ... -vv`).

I checked that this review file is not the cause. I moved it aside and re-ran `python3 -m pytest tests/ci/test_ci_examples.py -q`: still `9 failed, 21 passed`. This file holds no `&lt;UPPER_CASE&gt;` placeholder. The gate also printed `TODO lint / format / tests not configured — this step verified NOTHING` and `counts: not configured — executed == collected NOT checked`. So the gate is no evidence for Part G either way. The Part G evidence is the 271-pass suite plus the probes above. See Parked.

## Defects (if FAIL)

None.

## Hostile inputs tried

- `while  true ;do sleep 1;done` (odd spacing) gave rc=2.
- A multi-line `while true\ndo\nsleep 1\ndone` gave rc=2.
- `while :; do sleep 1; done` gave rc=2.
- `while true; do /bin/sleep 1; done` (path-qualified sleep) gave rc=2.
- `UNTIL true; do sleep 1; done` gave rc=0. This is correct: `UNTIL` is not a bash keyword, so the command is not a loop.
- An empty command gave rc=0 (no crash, no false block).
- `bash -c "while true; do sleep 1; done"` gave rc=0. This is a LIMIT already declared at ADAPTERS.md:26, not a defect.
- `while true; do command sleep 1; done` gave rc=0. Parked below.

## Parked

- **Proposed LIMIT line, outside the ACs:** `command sleep` inside a loop is not seen as `sleep` at command position, so R26 passes it (rc=0). No G-AC names this form. Under the mistakes-only threat model, an agent is unlikely to write it by accident. Proposed fix: add it to the declared-limits cell at ADAPTERS.md:26, or teach the matcher the `command`/`builtin` prefixes. That is the owner's call.

- **Exit gate red, outside Part G (not a G defect):** `scripts/verify-full.sh` exits 1 because the gate-3 tests in `tests/ci/test_ci_examples.py` scan the committed `doc/qa/REVIEW-bugfix-gate3-worktree.md` and `doc/qa/QA-bugfix-gate3-worktree.md`, and both quote `&lt;ABC_DEF&gt;` literally. The fix belongs to the gate-3 bugfix owner. Either reword those reports so they do not reproduce the placeholder shape, or decide that gate 3 should skip `doc/qa/`.

## Approval history

- **2026-10-22 — drafted.** Reviewer run a998e45d25322f524. Close-out independent review of increment G at HEAD ef1f717, based on the spec, commit 18aee03, and commands re-run in this run.
