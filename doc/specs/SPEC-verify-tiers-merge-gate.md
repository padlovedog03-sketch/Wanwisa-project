# SPEC: Agents close work faster — verify tiers, merge gate, less waiting, less rework

Status: Approved
Approval: spec-verify-tiers-merge-gate-2026-10-20
Owner: ba-sa
Upstream: doc/requirements/PRD-verify-tiers-merge-gate.md (approved by the owner 2026-10-20, registry key `prd-verify-tiers-merge-gate-2026-10-20`)
Date: 2026-10-20

Design: [`doc/architecture/DESIGN-verify-tiers-merge-gate.md`](../architecture/DESIGN-verify-tiers-merge-gate.md). This spec states *what* each increment delivers and how it is proven. The design states the interfaces, data shapes and decisions (ADR-1 … ADR-14).

## Overview

The work ships as nine increments, in the backlog's order. Each one can be built, tested and approved by itself.

1. **J** builds a meter for agent time.
2. **A+C** makes `verify-full` report time and counts, and write a record of every run.
3. **G** has the bash guard refuse hand-written polling loops.
4. **B** adds an opt-in handoff tier, where a machine chooses the tests from the diff.
5. **H** cuts rework with three things:
   - an affected-tests section in every spec;
   - a self-check for each acceptance criterion;
   - a rework cause on every QA defect.
6. **D** adds the merge gate and rewords every "full run before every handoff" rule.
7. **I** makes the coordinator write exact briefs and tells agents to batch their reads.
8. **E** keeps the suite in check: admission bar, retirement review, red-main policy and a named baseline.
9. **F** is the real trial on the pilot project.

Through all nine increments, nothing prints GREEN unless it ran the full collected set on the tree being judged.

## How to read this spec

- **Markers.** `[MEASURED: <command>]` means I ran it, on 2026-10-20, in this repo or a scratch copy. `[INFERRED]` means I derived it by reading and have not executed it. `[RELAYED: PRD]` means the number comes from the PRD and I did not re-measure it. The engineer must check every `[INFERRED]` before building on it (ai-engineer.md, Working Rules).
- **Line numbers.** Every `file:line` comes from the owner's working tree on 2026-10-20, and that tree carries uncommitted edits. Re-grep before editing; do not trust the line numbers.
- **AC IDs.** Each increment has its own prefix (`J-`, `AC-`, `G-`, `B-`, `H-`, `D-`, `I-`, `E-`, `F-`). An AC marked **RED-FIRST** is a proof the PRD names: the engineer pastes the red run (failing line verbatim), then the green run, then a zero-residue `grep -c`.
- **"Opted in" (D4).** A project is opted in when `scripts/verify.conf` exists and sets `VERIFY_HANDOFF_TIER=on`. `scripts/verify-handoff.sh --status` prints `opted in` or `not opted in`, and every reworded rule points at that one command (ADR-4).

## Increments

| # | Increment | Requirements | Needs | Changes agent behaviour? |
|---|---|---|---|---|
| 1 | J — meter | R37, R38, R39, R40, R32 | — | No. It reports only, and only the coordinator or owner runs it. |
| 2 | A+C — no fake green and a measurable `verify-full` | R1–R6, R10–R12 | — | Yes, in every project: new output lines, banned flags refused, an empty run is a failure. Verdict words are unchanged. |
| 3 | G — no polling | R26, R27, R28 | — | Yes, for every role, in every project on adapter ก. |
| 4 | B — handoff tier | R7, R8, R9 | 2 | No, until 6 rewords the rules. The script exists but nothing tells agents to use it yet. |
| 5 | H — rework | R29, R30, R31 | 1 (cause list), 4 (handoff tier for the self-check) | Yes: ba-sa, the engineers and QA. |
| 6 | D — merge gate | R13–R17 | 2, 4 | Yes, but only in opted-in projects. The rule text changes everywhere. |
| 7 | I — fewer turns | R33–R36 | 1 (turn counting) | Yes: the coordinator's briefs and every agent's read habits. |
| 8 | E — hygiene | R18–R21 | 2, 6 | Yes: QA and engineers (admission bar), and anyone reading a red gate (baseline). |
| 9 | F — pilot trial | R22–R25 (and M1–M14) | 1–8 | No framework change. Trial evidence only. |

**Order conflict, flagged rather than reordered.** The backlog puts R21 (named baseline) in E (8), after D (6). D's outcome form "RED, no failures beyond the named baseline" therefore becomes reachable only once E ships. D's ACs cover the other three forms, and E-AC1 covers the fourth. The trial needs R21 (backlog row 8 says so), and the trial is last, so the order still works. Moving R21 into increment 2 would be cleaner, but the backlog belongs to pm, so I have only flagged it.

## Acceptance Criteria

Test-file convention: tests of verify scripts live in `tests/hooks/`, next to the existing `tests/hooks/test_verify_scripts.py`. Tests of documents and of the meter's core live in `tests/framework/`. Both directories are already steps of `verify-full` `[MEASURED: grep -n '"hooks|\|"framework|' scripts/verify-full.sh → lines 18 and 41]`, so no STEPS line has to be added (ADR-11).

### Increment 1 — J: the meter (R37–R40, R32)

The golden timeline is defined in the design (§J.4). It is one synthetic ai-engineer run, and its known totals in seconds are:
- model 150;
- tests 361: running 120, background launch 1, background wait 120, hand-written polling 120;
- other background waits 0;
- other tools 60;
- read/git/edit 7;
- idle 600;
- active 578;
- turns 9, from 10 assistant lines.

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| J-AC1 | R37 | Given the golden timeline as neutral events (`tests/framework/fixtures/agent_time/golden_run.json`), When `agent_time.categorise(run)` runs, Then it returns exactly the golden totals above. Polling loops appear both inside tests and on their own `hand-written polling loops` line, and that line is not added to active time a second time. | tests/framework/test_agent_time.py |
| J-AC2 | R37, R38 | Given the same timeline in adapter ก's transcript format, with `attachment`, `api-request`, `api-request-blob` (no timestamp), `system` and `queue-operation` events interleaved (`tests/hooks/fixtures/transcripts/`), When `python3 scripts/agent_time.py --reader .claude/meter/transcript_reader.py --dir <fixture> --since 2000-01-01` runs, Then the ai-engineer totals equal J-AC1's, and the output has an `excluded events:` line with a count for each type. | tests/hooks/test_transcript_reader.py |
| J-AC3 | R40 **RED-FIRST** | Given the reader's single constant `CLOCK_EVENT_TYPES = {"user", "assistant"}`, When the test widens it with `monkeypatch` to add `"attachment"` and `"api-request"`, Then the J-AC2 assertion fails, and the failure names idle `600 → 675` and active `578 → 503`. The engineer pastes that red line, reverts, and shows green. This is the coordinator's own first-measurement mistake, planted on purpose (PRD brief). | tests/hooks/test_transcript_reader.py |
| J-AC4 | R40 **RED-FIRST** | Given the core counts turns as distinct `message_id` values, When the test swaps the counter for one that counts each model event, Then J-AC1 fails, naming `turns 9 → 10`. | tests/framework/test_agent_time.py |
| J-AC5 | R38 | Given no `--reader` argument, or a `--reader` path that does not exist, When the meter runs, Then stdout contains `unsupported`, no line carries a duration or a share, and exit is 0. A silent zero would be the silent-failure shape. | tests/framework/test_agent_time.py |
| J-AC6 | R39 | Given the fixture plants the canary `CANARY-7f3a` in a tool command, in the first inbound message, in a meta `description` and in a file name, When the meter runs with `--rework`, Then the canary appears nowhere in stdout or stderr. | tests/hooks/test_transcript_reader.py |
| J-AC7 | R39 | Given a missing `--dir`, a fixture with one malformed JSON line, and a run with no events, When the meter runs, Then exit is 0 in every case, and the output says `unreadable lines: 1`, or that the directory is missing, instead of printing numbers. | tests/framework/test_agent_time.py, tests/hooks/test_transcript_reader.py |
| J-AC8 | R37 | Given three neutral runs with active times of 100 s, 200 s and 600 s, When reported, Then the median shown for that agent type is `3.3 min`, the shares sum to 100% ± 1, and the output contains a `method:` line and a `limits:` line. | tests/framework/test_agent_time.py |
| J-AC9 | R32 | Given four ai-engineer runs, one of which has a first inbound message with a line starting `REWORK:`, and a `--qa-dir` fixture whose FAIL reports carry `missed-ac` twice, `test-gap` once and one row with an invalid cause, When `--rework --qa-dir <fixture>` runs, Then the output says `rework share: 1 of 4 engineer runs (25%)`, gives the counts per cause, says `unclassified defects: 1`, and exits 0. | tests/framework/test_agent_time.py |
| J-AC10 | R38, R27 | Given `doc/framework/ADAPTERS.md`, Then adapter ก's table has a row for the R37 meter (supported, naming its reader file), and adapter ข's table has the same row saying `unsupported`. | tests/framework/test_doc_contracts.py |
| J-AC11 | R37 (T) | `python3 scripts/check_neutrality.py` reports `0 provider name(s)` once `scripts/agent_time.py` exists. The existing `test_this_repo_is_neutral` covers this. | tests/framework/test_neutrality.py (unchanged) |

### Increment 2 — A+C: no fake green, and a measurable `verify-full` (R1–R6, R10–R12)

Every case runs a copy of the scripts inside a temporary git repo. Stub test commands write synthetic JUnit XML. This is the same copy technique `tests/hooks/test_verify_scripts.py` already uses `[MEASURED: sed -n 87,110p tests/hooks/test_verify_scripts.py]`.

**The copy technique is mandatory, in B and D as well.** The new tests in `test_verify_tiers.py`, `test_verify_handoff.py` and `test_verify_merge.py` must reuse that file's `_copy` helper, including its nested-suite assertions. The real `verify-full.sh` runs `pytest tests/hooks/`, which would collect these files and start `verify-full` again: the unbounded recursion that file's docstring records. `verify-merge.sh` calls `verify-full.sh`, so its tests stub the steps the same way.

**Every new RED condition applies only when the project configures it (R12).** That covers: no JUnit, zero cases, count mismatch, and tree changed during the run.
- The test-step checks apply only to labels listed in `VERIFY_TEST_STEPS` in `scripts/verify.conf`. With no conf, the list is empty.
- The tree-changed check applies only when `scripts/verify.conf` exists.
- Without a conf, a run gains timing, a record and informational lines, and nothing else changes.

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| AC-AC1 | R10 | Given a configured gate, When `verify-full.sh` runs, Then every step row shows its wall time as `(<n>s)`, a record exists at `.verify/runs/<run-id>/record.json`, and the record has `tree.before`, `tree.after`, `run_id`, `started_at`, `ended_at`, `runner.id`, `runner.kind`, and for each step `label`, `exit` and `seconds`. The final banner line is followed by `record: <path>`. | tests/hooks/test_verify_tiers.py |
| AC-AC2 | R10 | Given a test step that writes JUnit with 3 passed, 1 failed and 1 skipped, Then that step's record holds `passed 3, failed 1, skipped 1, reported 5`, and the record lists the failing test by its id (`classname::name`). | tests/hooks/test_verify_tiers.py |
| AC-AC3 | R3 **RED-FIRST** | Given `VERIFY_COLLECT_CMD` prints `5` and the test step's JUnit reports 4 test cases (one dropped on purpose), When `verify-full.sh` runs, Then it exits 1 with `EXIT GATE RED`, and a line names `reported 4 of 5 collected`. Given the stub then reports 5 (the revert), Then the verdict is `EXIT GATE GREEN`. | tests/hooks/test_verify_tiers.py |
| AC-AC4 | R3 | Given two JUnit files in one step's directory (two shards) with 3 and 2 cases, and collected `5`, Then the counts sum to 5 and the gate is GREEN. | tests/hooks/test_verify_tiers.py |
| AC-AC5 | R2 | Given the conf lists the step in `VERIFY_TEST_STEPS`, and that step's JUnit holds 0 test cases or it writes no JUnit at all, When `verify-full.sh` runs, Then it exits 1 with `EXIT GATE RED` and a line `0 tests reported by step <label>` or `no JUnit report written by step <label>`. | tests/hooks/test_verify_tiers.py |
| AC-AC6 | R1 | Given counts are configured, collected is 10, and the fast tier's TEST writes 3 cases, When `verify-fast.sh x.py` runs, Then its last line is `FAST VERIFY OK — partial run: ran 3 of 10`, and no line contains `GREEN` or `suite passes`. Given counts are not configured, Then the last line is `FAST VERIFY OK — partial run: ran ? of ? (counts not configured)`. | tests/hooks/test_verify_tiers.py |
| AC-AC7 | R2 | Given the fast tier's TEST writes a JUnit with 0 cases, Then the last line is `FAST VERIFY EMPTY — ran 0 of 10; nothing was verified`, and exit is 1. | tests/hooks/test_verify_tiers.py |
| AC-AC8 | R4 | For each banned form in the design's ban list (§AC.3), placed either in a configured command or in `verify-fast.sh`'s arguments: Given the form is present, When either tier starts, Then it exits 2 with `BANNED: <token> — <reason>` before any step runs. Given `python3 -m pytest` (the `-m` belongs to the interpreter), Then it is not refused. The only other exception is a marker or deselect filter declared in `VERIFY_ALLOWED_FILTERS` (AC-AC16 to AC-AC19). | tests/hooks/test_verify_tiers.py |
| AC-AC9 | R4, R5 | Given a JUnit file left in `.verify/runs/<older-run>/` by an earlier run, and a test step that writes nothing this run, When `verify-full.sh` runs, Then the old file is not counted, and the gate is RED with `no JUnit report written by step tests`. A cached pass cannot be reported as a fresh one. | tests/hooks/test_verify_tiers.py |
| AC-AC10 | R5 | Given a dirty tree, Then `record.tree.before` equals the hash written through a temporary index, and differs from `HEAD^{tree}`. Given a conf exists and a step edits a tracked file during the run, Then the gate is RED with `tree changed during the run`. Without a conf, the same edit produces the informational line `tree changed during the run (not enforced: no scripts/verify.conf)`, and the verdict is unchanged. | tests/hooks/test_verify_tiers.py |
| AC-AC11 | R6, R11 | Given `VERIFY_STEP_BUDGET_S=0` and a test whose JUnit time exceeds its size-class budget, When the gate otherwise passes, Then `WARN` lines name the step and the test, a `slowest tests:` block lists up to 10 tests, and the verdict is still `EXIT GATE GREEN` with exit 0. | tests/hooks/test_verify_tiers.py |
| AC-AC12 | R11 | `scripts/verify.conf.example` sets `VERIFY_TEST_BUDGET_SMALL_S=1`, `..._MEDIUM_S=10` and `..._LARGE_S=60`, which confirms PRD assumption A5, and documents how size rules work. | tests/framework/test_doc_contracts.py |
| AC-AC13 | R12 | Given there is no `scripts/verify.conf`, Then every existing test in `tests/hooks/test_verify_scripts.py` and `tests/ci/test_ci_examples.py` passes. The only change allowed is to their `_copy` helpers, which must also copy `scripts/verify_record.py`. The three banner strings `EXIT GATE GREEN`, `EXIT GATE INCOMPLETE` and `EXIT GATE RED` are unchanged, as is `FAST VERIFY INCOMPLETE`. | tests/hooks/test_verify_scripts.py, tests/ci/test_ci_examples.py |
| AC-AC16 | R4, R12 (owner ruling on Q4) | Given `scripts/verify.conf` declares `VERIFY_ALLOWED_FILTERS=('-m "not real_sleep"\|real-sleep tests run in the nightly job')`, and a configured step uses `-m "not real_sleep"`, When `verify-full.sh` runs, Then it is not refused, and an unindented line `declared filter: -m "not real_sleep" — real-sleep tests run in the nightly job` is printed on every run. The record lists it under `declared_filters`. | tests/hooks/test_verify_tiers.py |
| AC-AC17 | R4 | Given the same step uses `-m "not slow"`, which is not declared, Then the run exits 2 with `BANNED: -m "not slow" — undeclared filter; declare it with a reason in VERIFY_ALLOWED_FILTERS`, before any step runs. | tests/hooks/test_verify_tiers.py |
| AC-AC18 | R4 **RED-FIRST** | Given an allow-list entry with no reason (`'-m "not real_sleep"'`, or `'-m "not real_sleep"\|'`), Then the run exits 2 with `BANNED: allow-list entry without a reason: -m "not real_sleep"`. This is the planted case: shown red against a parser that accepts reasonless entries, then reverted. | tests/hooks/test_verify_tiers.py |
| AC-AC19 | R4 | Given an allow-list entry for `--lf`, `--last-failed`, `-x`, `--exitfirst`, `--maxfail…`, a retry flag or a cached-result flag, even with a reason, Then the run exits 2 with `BANNED: <token> can never be allow-listed`. Only marker and deselect filters (`-m`, `-k`, `--deselect`) can be declared. Given an allow-listed filter passed as a *runtime* argument to `verify-fast.sh` (not in a configured command), Then it is still refused: the allow-list covers the project's own step commands only. | tests/hooks/test_verify_tiers.py |
| AC-AC14 | R1, R3, R12 | Given counts are not configured, When the gate passes, Then the verdict stays `EXIT GATE GREEN` (R12), and an unindented line says `counts: not configured — executed == collected NOT checked`. The merge gate refuses to run in this state (D-AC2). | tests/hooks/test_verify_tiers.py |
| AC-AC15 | R12 | This is the real R12 proof, a project as filled in today. Given a copy whose STEPS are all filled with real (stub) commands, no `scripts/verify.conf`, test commands that write no JUnit, and a step that creates an untracked, non-ignored file during the run, When `verify-full.sh` runs, Then it still ends `EXIT GATE GREEN` with exit 0. Only timing, the record path and informational lines are added. | tests/hooks/test_verify_tiers.py |

### Increment 3 — G: no hand-written polling (R26–R28)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| G-AC1 | R26 **RED-FIRST** | For each of these commands, on a clean tree and on a dirty one:<br>• `until grep -q passed out.log; do sleep 10; done`<br>• `while true; do tail -1 x; sleep 30; done`<br>• `for i in $(seq 20); do cat s; sleep 5; done`<br>• `while ! test -f done.flag; do sleep 2; done`<br>When `guard_bash.py` gets it, Then it exits 2, and stderr names `rule R26`, says `hand-written polling loop`, and tells the agent to end its turn or do independent work until the completion notification. The test is written first and shown red against today's guard, which exits 0. | tests/hooks/test_guard_bash_polling.py |
| G-AC2 | R26 | For each of these, Then exit is 0:<br>• `while read l; do echo $l; done < f`<br>• `for f in *.py; do wc -l $f; done`<br>• `grep -rn "while true; do sleep 1; done" .`<br>• a heredoc whose body holds a loop<br>• `sleep 60 && cat out.log` (a single wait, not a loop; the PRD covers loops only)<br>• every `MUST_ALLOW` entry already in `tests/hooks/test_guard_bash_matrix.py` | tests/hooks/test_guard_bash_polling.py |
| G-AC3 | R26 | Given `ALLOW_DESTRUCTIVE=1` before a polling loop, Then it is still refused. That override waives rule A1' only (`guard_bash.py:230-233`), and R26 has its own override (G-AC7, ADR-9). | tests/hooks/test_guard_bash_polling.py |
| G-AC7 | R26 (owner ruling on Q2) | Given `ALLOW_POLL=1` at the head of the first segment, as `ALLOW_POLL=1; until grep -q passed out.log; do sleep 10; done` or `FOO=bar ALLOW_POLL=1; while true; do sleep 5; done`, When the guard runs, Then it exits 0. Given `ALLOW_POLL=1; git reset --hard` on a dirty tree, Then A1' still blocks: the override waives the polling rule only. The form is `ALLOW_POLL=1;` with a separator, because `ALLOW_POLL=1 until …` is a bash syntax error `[MEASURED: bash -c 'ALLOW_POLL=1 until true; do sleep 0; done' → "syntax error near unexpected token do"; with "ALLOW_POLL=1;" → rc=0]`. | tests/hooks/test_guard_bash_polling.py |
| G-AC8 | R26 **RED-FIRST** | Given `ALLOW_POLL=1` anywhere other than the head position, Then the loop is still refused (exit 2). The cases:<br>• `echo ALLOW_POLL=1 && until true; do sleep 1; done`<br>• `until true; do ALLOW_POLL=1 sleep 1; done`<br>• `until true; do sleep 1; done # ALLOW_POLL=1`<br>• `echo 'ALLOW_POLL=1' ; while true; do sleep 1; done`<br>The proof works the same way as `tests/hooks/test_guard_bash_bypasses.py:105-127` does for `ALLOW_DESTRUCTIVE=1`: swap the head check for a substring check (`"ALLOW_POLL=1" in command`), show these cases go red, then revert. | tests/hooks/test_guard_bash_polling.py |
| G-AC4 | R26 | All existing tests in `tests/hooks/test_guard_bash_matrix.py` and `test_guard_bash_bypasses.py` pass unchanged. | (existing) |
| G-AC5 | R27, R28 | Given `doc/framework/ADAPTERS.md`, Then:<br>• adapter ก declares `R26 polling guard: enforced` and `completion notification: yes`;<br>• adapter ข declares `R26: no enforcement`, names the fallback (rule text plus the R37 meter), states what is weaker, and declares `completion notification: no` with its substitute (a foreground run with the tool's own timeout). | tests/framework/test_doc_contracts.py |
| G-AC6 | R28 | `.agents/skills/engineering-loop/SKILL.md` carries the waiting rule: never poll; end the turn or do independent work until the completion notification arrives; where the adapter has none, use the substitute ADAPTERS.md names. The doc test checks that the rule's anchor phrase is present. | tests/framework/test_doc_contracts.py |

`.claude/settings.json` needs no change, because the guard is already registered for every Bash call `[MEASURED: sed -n 19,28p .claude/settings.json — matcher "Bash" → guard_bash.py]`. `test_the_guard_is_registered_in_settings_json` keeps covering it.

### Increment 4 — B: the handoff tier (R7–R9)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| B-AC1 | R7 | Given an opted-in temp repo whose base commit is at `VERIFY_BASE_REF`, `a.py` changed in a commit, `b.py` modified but uncommitted, and `c.py` untracked, When `verify-handoff.sh` runs with no arguments, Then the stub selector receives exactly `{a.py, b.py, c.py}`, and the output ends `HANDOFF TIER — ran N of M (selected by machine from the diff against <base>)`. | tests/hooks/test_verify_handoff.py |
| B-AC2 | R7 | Given the same tree, When the agent runs `verify-handoff.sh a.py` (leaving out two touched paths), Then the selector still receives all three, and the output says `touched by the diff but not named by you: b.py c.py`. This is the QA test the PRD names. | tests/hooks/test_verify_handoff.py |
| B-AC3 | R7 | Given the agent names `d.py`, which the diff did not touch, Then `d.py` is added to the selection, and the output says `named by you but not touched by the diff: d.py`. A path can add to the selection, never remove from it. | tests/hooks/test_verify_handoff.py |
| B-AC4 | R8 | Given `VERIFY_UNTRACKED_INPUTS="doc/**"` and a changed `doc/x.md`, Then the full-set command runs, the output says `full collected set — declared untracked input changed: doc/x.md`, and the count line reads `ran M of M`. | tests/hooks/test_verify_handoff.py |
| B-AC5 | R8 | Given `VERIFY_UNTRACKED_INPUTS` is empty, Then every run takes the full set, with the reason `no untracked inputs declared`. | tests/hooks/test_verify_handoff.py |
| B-AC6 | R9 | Given there is no `scripts/verify.conf`, or `VERIFY_HANDOFF_TIER` is not `on`, When `verify-handoff.sh` runs, Then it prints `HANDOFF TIER NOT CONFIGURED — this project has not opted in; scripts/verify-full.sh before every handoff stays in force`, exits 3, and runs no tests. `--status` prints `not opted in` and exits 0. | tests/hooks/test_verify_handoff.py |
| B-AC7 | R2 | Given the selector reports 0 cases, Then the output says `HANDOFF TIER EMPTY — ran 0 of M; nothing was verified`, and exit is 1. | tests/hooks/test_verify_handoff.py |
| B-AC8 | R1 | Across every B case, stdout never contains `GREEN` or `suite passes`. | tests/hooks/test_verify_handoff.py |
| B-AC9 | R7 | Given `VERIFY_BASE_REF` does not resolve, Then the full set runs, with the reason `base <ref> not found`. It must never select nothing. | tests/hooks/test_verify_handoff.py |
| B-AC10 | R7 **RED-FIRST** | Given the selector stub fails the test tied to `a.py` (a planted regression), Then the output says `HANDOFF TIER RED — ran N of M`, names the failing test id, and exits 1. | tests/hooks/test_verify_handoff.py |
| B-AC11 | R4 | Given `VERIFY_SELECT_CMD` contains a banned form, Then the tier exits 2 with `BANNED:`. | tests/hooks/test_verify_handoff.py |
| B-AC12 | R5, R10 | A handoff-tier run writes a record with `tier: "handoff"` and both tree hashes, the same way AC-AC10 requires for the full gate. | tests/hooks/test_verify_handoff.py |

### Increment 5 — H: less rework (R29–R31)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| H-AC1 | R29 **RED-FIRST** | `doc/templates/spec.md` has the heading `## Affected tests / affected files`. Given any `doc/specs/SPEC-*.md` whose status is `In Review` and that lacks the heading, Then the doc-contract test fails and names the file. The check covers `In Review` only, which is what R29 says ("cannot move to In Review"). An older spec that is already Approved or Done is never retro-failed, so upgrading a project does not turn its gate red over its history. The planted spec in a temp root is shown red first. This spec carries the section itself. | tests/framework/test_doc_contracts.py |
| H-AC2 | R30 **RED-FIRST** | Given a spec with AC1–AC3, and a handback whose `Self-check:` block has lines for AC1 and AC3 only, When `python3 scripts/handback_lint.py --spec <spec> -` runs, Then it exits 1 with `self-check missing for AC2`. Given all three lines, each carrying a command and a result, Then it exits 0. A line with no result is flagged. | tests/coordinator/test_handback_lint.py |
| H-AC3 | R30 | `ai-engineer.md` and `frontend-engineer.md` require the self-check block, and require running the handoff tier when opted in, or `verify-full` when not. The doc test checks for the anchor phrase. | tests/framework/test_doc_contracts.py |
| H-AC4 | R31 **RED-FIRST** | `doc/templates/qa-report.md`'s Defects table has a `Rework cause` column, and the template lists exactly the vocabulary in `agent_time.REWORK_CAUSES`: `missed-ac`, `regression`, `spec-defect`, `test-gap`, `env-flaky`. Given a `doc/qa/QA-*.md` with `Verdict: FAIL` whose `Date:` is on or after the constant `REWORK_CAUSE_REQUIRED_FROM` (set by the engineer to the day this increment ships, on the model of `MECHANISM_REQUIRED_FROM` in `scripts/correction_rate.py:33`), and whose defect row has no cause, two causes, or an unknown cause, Then the doc-contract test fails and names the file and row. Reports dated earlier are never retro-failed. The planted report is shown red first. | tests/framework/test_doc_contracts.py |
| H-AC5 | R31 | `qa.md` and `frontend-qa.md` require one cause per defect from the fixed list. The doc test checks the anchor. | tests/framework/test_doc_contracts.py |

### Increment 6 — D: merge gate and the rule rewording (R13–R17)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| D-AC1 | R13, R16 | Given a clean temp repo with counts configured and `VERIFY_RUNNER_ID=runner-7`, When `verify-merge.sh HEAD` runs, Then:<br>• `verify-full.sh` runs inside a fresh `git worktree` of HEAD;<br>• the record's `tree.before` equals `git rev-parse HEAD^{tree}`;<br>• `runner.kind` is `runner`;<br>• the last line is `MERGE GATE GREEN — tree <hash> — runner runner-7`. | tests/hooks/test_verify_merge.py |
| D-AC2 | R13, D5 | Each of these cases prints exactly one line matching `^MERGE GATE (GREEN\|RED\|NOT RUN)`:<br>• a failing step → `MERGE GATE RED`, exit 1;<br>• counts not configured → `MERGE GATE NOT RUN — executed == collected is not configured`, exit 3;<br>• `VERIFY_MERGE_GATE=none` → `MERGE GATE NOT RUN — no runner and no local fallback configured`, exit 3. | tests/hooks/test_verify_merge.py |
| D-AC3 | R13, D6 **RED-FIRST** | Given `verify-merge.sh --check <record> <ref>`:<br>• when the record's tree differs from the ref's tree, Then the output says `MERGE GATE NOT RUN — record is for tree X, candidate is tree Y`;<br>• when the record names no runner, Then the output says `MERGE GATE NOT RUN — record names no runner`.<br>The tree-mismatch case is the planted one. | tests/hooks/test_verify_merge.py |
| D-AC4 | R16 | Given no `VERIFY_RUNNER_ID` and `VERIFY_MERGE_GATE=local-fallback`, Then `runner.kind` is `local-fallback`, and the last line ends `(local fallback — weaker: same machine and same user as the agent)`. | tests/hooks/test_verify_merge.py |
| D-AC5 | R13, R5 | Given the caller's working tree is dirty, Then the merge gate still judges the committed HEAD, through its own worktree. The record's tree is the HEAD tree, and the caller's tree is not modified. | tests/hooks/test_verify_merge.py |
| D-AC6 | R14 **RED-FIRST** | Over the R14 search scope (`AGENTS.md`, `.agents/`, `.claude/agents/`, `doc/framework/`, `doc/templates/`, `scripts/verify-full.sh`), every line that matches one of the requirement patterns also carries the opt-in qualifier. The patterns are chosen so that each of the PRD's 12 requiring locations matches at least one; the design (§D, "R14 patterns") gives the full list. A line beginning with `Do not:` is exempt, because it forbids a full run rather than requiring one. That exempts `coordinator-discipline/SKILL.md:144`, which therefore stays unchanged (impact row 18). The qualifier is the literal `verify-handoff.sh --status`, or the words `not opted in` / `ยังไม่ opt-in`. Given a planted line `run verify-full before every handoff` in a temp copy, Then the test fails and names `file:line`. This makes M9 a mechanism. A second assertion checks that the three related locations (`coordinator-discipline/SKILL.md:119`, `WHY.md:150`, `SETUP.md:59`) each mention `verify-merge.sh`. | tests/framework/test_doc_contracts.py |
| D-AC7 | R15 | `qa.md` and `frontend-qa.md` state that an opted-in QA verdict rests on QA's own handoff-tier run plus its added tests, labelled `ran N of M`, and never on an earlier record. The doc test checks the anchor. | tests/framework/test_doc_contracts.py |
| D-AC8 | R17 | `scripts/verify.conf.example` has a neutral merge-gate section, and `doc/framework/SETUP.md` documents runner, fallback and none. Both `ci-examples/*.yml` set `VERIFY_RUNNER_ID` on the gate-2 step. All `tests/ci/test_ci_examples.py` tests pass, and neutrality stays at 0. | tests/ci/test_ci_examples.py, tests/framework/test_neutrality.py |

### Increment 7 — I: fewer model turns (R33–R36)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| I-AC1 | R33 **RED-FIRST** | Given a brief block that starts with `Slice:` and lacks `Files:`, `Criteria:` or `Verify with:`, When `coordinator_lint.py` runs, Then it reports `rule 6` and names the missing field. Given all three are present, Then the brief is clean. The test is written and shown red before the rule exists. | tests/coordinator/test_coordinator_lint.py |
| I-AC2 | R33 | The brief template in `.agents/skills/coordinator-discipline/SKILL.md` carries `Files:`, `Criteria:`, `Verify with:` and the optional `REWORK:` line. `test_a_fully_tagged_report_is_clean` and the other existing tests still pass. | tests/coordinator/test_coordinator_lint.py |
| I-AC3 | R34, R35 | `.agents/skills/engineering-loop/SKILL.md` carries both rules: batch independent reads, searches and commands into one turn; and do not re-read an unchanged large file, but read only the range you need. The doc test checks the anchors. Their effect is measured by M14 in the trial, not here. | tests/framework/test_doc_contracts.py |
| I-AC4 | R36 | The meter reports `turns per run (median)` for each agent type (part of J-AC1/J-AC8). The trial reports M14 as "no gain" when there is none (F-AC6). | tests/framework/test_agent_time.py |

### Increment 8 — E: keeping the suite in check (R18–R21)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| E-AC1 | R21, R13, D8 | Given `VERIFY_BASELINE_FILE` lists `t1` and `t2`, and the run fails exactly `t1` and `t2`, Then:<br>• `verify-full` ends `EXIT GATE RED — no failures beyond the named baseline (2 known)` and exits 1;<br>• `verify-merge` ends `MERGE GATE RED — no failures beyond the named baseline (2 known) — tree … — runner …`;<br>• neither ever prints GREEN. | tests/hooks/test_verify_tiers.py, tests/hooks/test_verify_merge.py |
| E-AC2 | R21 **RED-FIRST** | Given the run fails `t1`, `t2` and `t3`, a planted regression, Then the output says `NEW failure: t3`, and the verdict is plain `EXIT GATE RED`, not the baseline form. | tests/hooks/test_verify_tiers.py |
| E-AC3 | R21 | Given the run fails only `t1`, Then the output says `baseline test now passing: t2 — remove it from the baseline`, and the verdict is plain RED, because the comparison demands exact equality. | tests/hooks/test_verify_tiers.py |
| E-AC4 | R20 | Given a baseline entry `t1 state=quarantined owner=alice expires=2026-01-01` and the run's date is after the expiry, Then the output says `quarantine expired: t1`, and `t1` counts as a new failure. Given a `quarantined` entry with no owner or no expiry, Then the output says `invalid quarantine entry: t1`, and it counts as new. A quarantined test still appears in the record's failure list. | tests/hooks/test_verify_tiers.py |
| E-AC5 | R20 | Given the last 3 retained records all show `t1` failing, and `t1` is marked `quarantined`, Then the output says `quarantine refused: t1 failed in every one of the last 3 runs`, and `t1` counts as new. `state=known-red` stays allowed. | tests/hooks/test_verify_tiers.py |
| E-AC6 | R21, R25 | `verify_record.py baseline-write --record <r> --out <f>` writes the record's failure set as `state=known-red` lines. Running the gate again on the same tree then gives the baseline form. | tests/hooks/test_verify_tiers.py |
| E-AC7 | R18 | `.agents/skills/code-quality/SKILL.md` states the four-point admission bar. `doc/templates/qa-report.md` has a `Tests added` table with the columns `red before fix`, `new coverage or mutant killed`, `within budget or labelled slow`, `not a change-detector` and `admitted by` (never the test's author). | tests/framework/test_doc_contracts.py |
| E-AC8 | R19 | `doc/templates/retirement-review.md` exists, with the trigger (quarterly, or the full run over budget, whichever comes first), a candidate table that needs both coverage and mutation evidence, the statement "nothing is deleted automatically", and a `## Approval history` heading, so the owner signs it off through `scripts/approve.sh`. | tests/framework/test_doc_contracts.py |
| E-AC9 | R20 | The engineering-loop skill states the red-main policy: top priority; triage before new work; no freeze; three end states; and adopting the gate is allowed before main is green. | tests/framework/test_doc_contracts.py |

### Increment 9 — F: pilot-project trial (R22–R25)

These cannot be pytest in this repo, because they need the pilot project. The evidence artifact is `doc/qa/QA-verify-tiers-merge-gate-trial.md`, which qa writes from `doc/templates/qa-report.md`. Each AC names the section and the command output it must paste.

| # | Maps to | Given / When / Then | Evidence |
|---|---|---|---|
| F-AC1 | R22 | Given the trial runs in a separate worktree or copy of the pilot project, Then `git status --porcelain`, `git branch --list` and `git stash list` of the pilot's main working tree are byte-identical before and after the trial. | Trial report §Isolation: both outputs pasted |
| F-AC2 | R22(a–e), M10–M14, M1, M2, M8, M11 | At least 3 features or fixes, replays allowed (D9). Before and after numbers come from `scripts/agent_time.py` (same reader, same flags) and from the merge-gate records: active time and category split, turns, code-done-to-handoff wall time, full-suite runs per feature, merge-gate seconds plus runner, and rework as counts. | Trial report §Numbers: meter output pasted both times |
| F-AC3 | R23, M5, M6 | Three probes, each shown red and then reverted:<br>(a) a planted regression goes red in the handoff tier, naming the test;<br>(b) a dropped test makes `verify-full` red with `reported N of M collected`;<br>(c) a planted polling loop is refused by the guard, naming R26.<br>After revert, `git status --porcelain` is empty and `grep -c <probe marker>` is 0. | Trial report §Probes |
| F-AC4 | R24, M7 | The switch fills in `scripts/verify.conf` and the baseline file only. The step count must be ≤ 6, and the minutes ≤ 60, are recorded. `git diff --stat <upgrade-commit> <switch-commit> -- scripts/ .claude/ .agents/` lists only `scripts/verify.conf`. Any other path is a defect. | Trial report §Adoption |
| F-AC5 | R25 | `git diff --stat <trial-start> <trial-end> -- <pilot test dirs>` is empty apart from reverted probes. The baseline lists the pilot's known reds. The handover note to the pilot's own session is quoted. | Trial report §Reds |
| F-AC6 | R36, M14 | Model-generating minutes and turns per run are shown before and after for each agent type. "No gain" is reported as such and does not fail the trial. | Trial report §Numbers |
| F-AC7 | M4 | `python3 scripts/handback_lint.py --partial-claims <file>` over every trial handoff and QA report flags 0 lines that say `passed`, `green` or `suite passes` without `ran N of M` or a full-gate banner on the same line. Unit coverage: a planted claim is flagged, and a labelled claim passes. | Trial report §Reports, and tests/coordinator/test_handback_lint.py |

## Functional Behavior

The exact output lines are in the ACs above. This section covers the rules that apply across them.

**Verdict vocabulary.** Every tier ends with exactly one banner line.

| Tier | Possible endings | Exit codes |
|---|---|---|
| fast | `FAST VERIFY OK — partial run: ran N of M`, `FAST VERIFY EMPTY …`, `FAST VERIFY INCOMPLETE …` (unchanged), `BANNED: …` | 0, 1, 0, 2 |
| handoff | `HANDOFF TIER — ran N of M …`, `HANDOFF TIER RED — ran N of M …`, `HANDOFF TIER EMPTY …`, `HANDOFF TIER NOT CONFIGURED …`, `BANNED: …` | 0, 1, 1, 3, 2 |
| full | `EXIT GATE GREEN …`, `EXIT GATE RED …`, `EXIT GATE RED — no failures beyond the named baseline (K known)`, `EXIT GATE INCOMPLETE …`, `BANNED: …` | 0, 1, 1, 0, 2 |
| merge | `MERGE GATE GREEN …`, `MERGE GATE RED — no failures beyond the named baseline …`, `MERGE GATE RED …`, `MERGE GATE NOT RUN — <reason>` | 0, 1, 1, 3 |

- GREEN appears only in the full and merge tiers, and only when every configured step passed, counts matched (or are honestly marked not configured, full tier only), and the tree did not change during the run.
- New summary lines are unindented. `test_a_placeholder_step_is_labelled_todo_not_ok` counts the two-space-indented lines that contain `not configured`, so a new indented line containing those words would break it `[MEASURED: sed -n 152,173p tests/hooks/test_verify_scripts.py]`.

**What happens when something is not configured.**

| Missing | fast | handoff | full | merge |
|---|---|---|---|---|
| conf file | current behaviour, plus timing and labels; no new RED condition | NOT CONFIGURED (exit 3) | current behaviour, plus timing and record; no new RED condition (AC-AC15) | NOT RUN |
| `VERIFY_TEST_STEPS` (empty) | — | — | no JUnit, zero-case or count checks; informational lines only | NOT RUN |
| `VERIFY_COLLECT_CMD` | `ran N of ?` | NOT CONFIGURED | GREEN kept, plus the `counts: not configured` line | NOT RUN |
| a git work tree | tree recorded as `null` | NOT CONFIGURED | tree `null`, GREEN kept (R12) | NOT RUN |
| `scripts/verify_record.py` | RED `recorder missing` | RED | RED `recorder missing` | NOT RUN |

A missing recorder is RED rather than a silent skip, because a gate that quietly skipped its own counting would be the very shape of failure it exists to catch.

**Personal data (AGENTS.md §8).** The meter prints role names, counts and durations only. The records carry test ids, step labels and hashes. Neither ever carries transcript text, file contents or user identifiers.

## Impact table — every file touched

"Opt-in only" means the change in *behaviour* happens only in a project that has opted in (D4). The text itself changes in every project.

| # | File | Inc. | What changes | Whose behaviour changes, and how | Opt-in only? |
|---|---|---|---|---|---|
| 1 | `scripts/agent_time.py` **(new)** | J, H | Neutral, stdlib-only meter: categories, medians, turns, rework report, `REWORK_CAUSES` constant | Coordinator and owner gain an instrument. No agent is told to run it. | No (report only) |
| 2 | `.claude/meter/transcript_reader.py` **(new, adapter ก)** | J | Reads adapter ก transcripts into neutral events. Allow-lists `user` and `assistant` as clock events. | None | No |
| 3 | `tests/framework/test_agent_time.py` **(new)** and `tests/framework/fixtures/agent_time/` **(new)** | J | Golden timeline, turn mutation, unsupported, medians, rework | — | — |
| 4 | `tests/hooks/test_transcript_reader.py` **(new)** and `tests/hooks/fixtures/transcripts/` **(new)** | J | Adapter fixture with internal events and the canary. Internal-event mutation. | — | — |
| 5 | `scripts/verify_record.py` **(new)** | A+C, B, D, E | Tree hash, ban check, JUnit counts, record writing, baseline comparison, diff paths, record check | Indirect: it produces the lines every agent now pastes | No (records always written; counts when configured) |
| 6 | `scripts/verify.conf.example` **(new)** | A+C, B, D, E | Commented config: step overrides, the declared filter allow-list (`VERIFY_ALLOWED_FILTERS`), counts, handoff tier, budgets, baseline, merge gate | None until a project copies it to `scripts/verify.conf` | It *is* the opt-in |
| 7 | `scripts/verify-full.sh` | A+C, D, E | Sources the conf (which may override `STEPS`); refuses banned forms; times each step; fresh run dir and `VERIFY_JUNIT_DIR` for each test step; tree hash before and after; calls the recorder; new verdict modifiers. Header lines 2 and 89 reworded (R14). | Every engineer and QA running it sees timing lines, a `record:` path, and RED for a count mismatch, an empty step or a changed tree. Verdict words are unchanged (R12). | No for the mechanics. The rule wording points opted-in projects to the merge gate. |
| 8 | `scripts/verify-fast.sh` | A+C | Sources the conf; refuses banned forms in its arguments and config; ends `partial run: ran N of M`; zero cases is `EMPTY` (exit 1); new routing cases for the new scripts and tests | Engineers: the last line changes, and `--lf`/`-x`/`-k` passed as paths now exit 2 instead of running | No |
| 9 | `scripts/verify-handoff.sh` **(new)** | B | Machine selection from the diff, union with named paths, untracked inputs force the full set, `ran N of M`, `--status` | After D: engineers and QA in opted-in projects use it as their handoff and verdict tier | Yes |
| 10 | `scripts/verify-merge.sh` **(new)** | D, E | Fresh worktree, `verify-full`, record bound to the tree and the runner, the four outcome forms, `--check` | Coordinator or CI: one run per merge candidate | Yes, in effect (a project that has not opted in may still run it) |
| 11 | `tests/hooks/test_verify_tiers.py`, `test_verify_handoff.py`, `test_verify_merge.py` **(new)** | A+C, B, D, E | ACs above | — | — |
| 12 | `.claude/hooks/guard_bash.py` | G | New rule R26: a loop keyword at command position plus `sleep` at command position, across segments. Block message. Override `ALLOW_POLL=1;`, head position only, waiving R26 only (the existing head check generalised to take the token). | **Every role, including the coordinator** `[INFERRED: the hook entry has no role filter; whether it fires inside subagents is settled by the trial probe F-AC3(c)]`. A hand-written polling loop is refused with exit 2. | No. Every project on adapter ก. |
| 13 | `tests/hooks/test_guard_bash_polling.py` **(new)** | G | Block, allow and override cases | — | — |
| 14 | `.claude/settings.json` | G | **No change.** The Bash matcher already runs `guard_bash.py` `[MEASURED: sed -n 19,28p .claude/settings.json]`. | — | — |
| 15 | `doc/framework/ADAPTERS.md` | G, J | Adds `.claude/meter/` to adapter ก's file list. New rows on both adapters: R26 enforcement, completion notification, R37 meter support. Adapter ข's "what is weaker" text. | None directly | — |
| 16 | `AGENTS.md` (§4, line 46) | D, I | §4 lists `verify-handoff.sh` and `verify-merge.sh`. Line 46 gets the opt-in qualifier (R14). | All roles | Wording points to `--status` |
| 17 | `.agents/skills/engineering-loop/SKILL.md` (13, 45, 49, 69) | D, G, I, E | Loop diagram and tier table gain the handoff tier and merge gate, with the qualifier. Lines 49 and 69 made consistent. New rules: waiting (R28), batching (R34), no re-reading (R35), red-main policy (R20). Ban list adds retries. | Engineers, QA, ba-sa, pm: how to verify, how to wait, how to read | Tier choice is opt-in. The waiting and reading rules apply everywhere. |
| 18 | `.agents/skills/coordinator-discipline/SKILL.md` (119, 144, brief template) | D, I | Line 119 consistent with the merge gate. Brief template gains `Files:`, `Criteria:` and `REWORK:`. Line 144 already consistent; checked, unchanged. | Coordinator: briefs must name files, criteria and the tier | Merge-gate wording is opt-in. Brief fields apply everywhere. |
| 19 | `.agents/skills/code-quality/SKILL.md` (line 71 and new text) | A+C, E | "Commands must match" now points at `scripts/verify.conf` when it exists. Adds the admission bar (R18). | Engineers and QA: new tests must meet the bar | No |
| 20 | `.agents/skills/handoff-protocol/SKILL.md` | H | The engineer's handoff message includes the `Self-check:` block (R30). It is checked with `handback_lint.py --spec`. | Engineers; the coordinator pipes handbacks through it | No |
| 21 | `.claude/agents/ai-engineer.md` (30, 37) | D, H | Exit-gate lines get the qualifier: opted-in projects hand off on the handoff tier, and the merge gate does the full run. Adds the self-check requirement. | ai-engineer: no full run per handoff when opted in; must self-check every AC | Tier is opt-in. Self-check applies everywhere. |
| 22 | `.claude/agents/frontend-engineer.md` | H, D | Adds the self-check and the same tier wording. No R14 hit today `[MEASURED: grep -n 'verify-full' .claude/agents/frontend-engineer.md → no output]`. | frontend-engineer | As 21 |
| 23 | `.claude/agents/qa.md` (18, 28) | D, H, E | Verdict tier: opted in → own handoff-tier run plus added tests, `ran N of M`, never an earlier record (R15); otherwise `verify-full`. One rework cause per defect (R31). Admission bar for added tests (R18). | qa: no full suite when opted in | Tier is opt-in. Causes and bar apply everywhere. |
| 24 | `.claude/agents/frontend-qa.md` (15, 30) | D, H | "Run the full suite at least twice" becomes "run your verdict tier twice (single worker, then default parallelism)", where the verdict tier is the handoff tier if opted in and the full suite if not. Rework causes. | frontend-qa | As 23 |
| 25 | `.claude/agents/ba-sa.md` | H | "Affected tests / affected files" section is mandatory (R29). | ba-sa: a spec without it fails the gate | No |
| 26 | `doc/templates/spec.md` | H | Adds `## Affected tests / affected files`. | ba-sa | No |
| 27 | `doc/templates/qa-report.md` | H, E, D | `Rework cause` column and vocabulary; `Tests added` admission table; Test Run block says which tier ran and `ran N of M`. | qa, frontend-qa | No |
| 28 | `doc/templates/retirement-review.md` **(new)** | E | Retirement review with coverage and mutation evidence; owner sign-off through the approval registry | Owner, qa | No |
| 29 | `doc/framework/SETUP.md` (32, 38, 59, new section) | A+C, D | Step 3 points at `scripts/verify.conf`. Line 38 gets the qualifier. Line 59 consistent. A new "switch on the faster tiers" section has ≤ 6 steps (M7) and covers runner, fallback and none (R16). | People setting up a project | Opt-in section |
| 30 | `doc/framework/WHY.md` (150) | D | Consistency: one sentence noting that the merge gate is the machine form of "the coordinator runs the full suite once". | — | — |
| 31 | `README.md` (106) | D | Consistency, outside the R14 scope: `verify-full.sh` described as the exit gate, or the merge gate when opted in. | — | — |
| 32 | `scripts/coordinator_lint.py` | I | Rule 6: a `Slice:` brief must carry `Files:`, `Criteria:` and `Verify with:`. | Coordinator | No |
| 33 | `doc/framework/COORDINATOR-CONSTITUTION.md` (§ machine-checked grammar, line 49) | I | Documents rule 6. | Coordinator | No |
| 34 | `scripts/handback_lint.py` **(untracked owner file)** | H, F | `--spec <spec>` self-check check; `--partial-claims` check (M4). Default behaviour unchanged. | Coordinator | No |
| 35 | `tests/coordinator/test_coordinator_lint.py`, `tests/coordinator/test_handback_lint.py` | I, H, F | New cases. `test_handback_lint.py` is also untracked owner work. | — | — |
| 36 | `tests/framework/test_doc_contracts.py` **(new)** | J, G, H, D, I, E | Document contracts: ADAPTERS rows, spec section, QA causes, R14 qualifier, rule anchors, template columns | — | — |
| 37 | `tests/hooks/test_verify_scripts.py` | A+C | `_copy` also copies `scripts/verify_record.py`. No assertion changes. | — | — |
| 38 | `tests/ci/test_ci_examples.py` | A+C | The gate-2 copy (`test_gate_2_extracted_command_actually_runs`) also copies `scripts/verify_record.py`. | — | — |
| 39 | `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml` | D | Gate-2 step gains `env: VERIFY_RUNNER_ID` from the runner's own name variable. The `run` and `script` strings stay `./scripts/verify-full.sh`, which `test_gate_2_command_is_the_exit_gate…` asserts. | CI | — |
| 40 | `.gitignore` | A+C | Adds `.verify/`, so run records are never committed. | — | — |

**Checked and unchanged:**
- `scripts/check_neutrality.py`: the reader sits outside the core paths, so `ADAPTER_EXEMPT` is unchanged.
- `scripts/bootstrap.sh`: it rewrites only `<PROJECT>`, `<PACKAGE>`, `<BACKEND_REPO_PATH>`, `<FRONTEND_REPO_PATH>` and `<FRONTEND_REPO>` `[MEASURED: grep -n '<' scripts/bootstrap.sh, lines 14 and 22–24]`, and the example conf must use none of them.
- `.claude/agents/pm.md`.
- `.githooks/*`.
- `doc/tasks/backlog.md`: owned by pm. Its status column still says "PRD In Review"; reported in the handoff.
- `CHANGELOG-template.md`: history, untouched.

**R14 location check (ba-sa confirms the list).**
- **Search.** `grep -rnE 'before every handoff|before \*\*every\*\* handoff|full suite|exit gate|verify-full|ชุดเต็ม|ประตูออก|ก่อนส่งมอบ' AGENTS.md .agents/ .claude/agents/ doc/framework/ doc/templates/ scripts/verify-full.sh`, run 2026-10-20 over exactly the PRD's scope, then again repo-wide with `-i` and the same patterns plus `full tier`.
- **The PRD's 12 requiring locations and 3 related locations are all present at the stated lines.** `[MEASURED: grep as above]`
- **Extra hits inside the PRD scope:**
  - `engineering-loop/SKILL.md:13` (the loop diagram, already named by the PRD), `:49` ("the exit gate always runs everything"); handled in row 17.
  - `coordinator-discipline/SKILL.md:144` (already consistent).
  - `code-quality/SKILL.md:71` (row 19).
  - `SETUP.md:32` (row 29).
  - `verify-full.sh:48,74,84`: banner lines that R12 keeps.
- **Hits outside the PRD scope:**
  - `README.md:106` (row 31).
  - Both `ci-examples/*.yml` gate-2 step names `ประตูออก`. Kept, because `tests/ci/test_ci_examples.py:433-434` looks the step up by that name.
  - `CHANGELOG-template.md` (history).
  - Test docstrings.
- **Conclusion.** The PRD's list is complete for *requiring* locations. Five more consistency locations are added: engineering-loop:49, code-quality:71, SETUP.md:32, README.md:106, coordinator-discipline:144 (the last one checked and unchanged).

## Affected tests / affected files

**How this list was built:**
1. `grep -rn` for every R14 pattern (above).
2. `grep -rn 'verify-full\|verify-fast'` repo-wide, excluding `.git`, `__pycache__` and the PRD.
3. A read of each test that asserts on verify-script output: `tests/hooks/test_verify_scripts.py` in full at lines 1–220, `tests/ci/test_ci_examples.py:418-500`, `tests/hooks/test_guard_bash_matrix.py:40-86`, `tests/framework/test_settings_deny.py`, `tests/framework/test_bootstrapped_project.py`.
4. `grep -n '^def \|^_[A-Z_]* =' ` over 10 test files.

A file this search could not see (for example a downstream project's own parser of verify output) is not covered.

**Existing tests that must keep passing, and what constrains them:**

| Test | What it pins | Effect of this work |
|---|---|---|
| `tests/hooks/test_verify_scripts.py` (all 20) | The exact STEPS strings replaced with `count == 1` (`_REAL_*_STEP` at lines 48–79); banner words; step rows start with two spaces plus `TODO` or `OK`; exactly 3 indented `not configured` lines; `"TODO" not in stdout` when fully configured | `_copy` must also copy `verify_record.py`. The STEPS default strings must stay byte-identical. New lines must be unindented and must not contain `TODO`. `[MEASURED: sed -n 41-220p]` |
| `tests/ci/test_ci_examples.py` (gate 2 and gate 4) | The gate-2 command string, the step name `ประตูออก`, the copy run ending `EXIT GATE INCOMPLETE`, and `_HOOKS_TEST_COMMAND` present in verify-full | The copy must include the helper. A non-git temp dir must still reach INCOMPLETE, so tree `null` must not turn it RED (behaviour table). `[MEASURED: sed -n 418-500p]` |
| `tests/hooks/test_guard_bash_matrix.py`, `test_guard_bash_bypasses.py` | A1' block and allow lists, the message format, registration | R26 must not block any `MUST_ALLOW` entry, and must not alter A1' messages |
| `tests/framework/test_neutrality.py::test_this_repo_is_neutral` | 0 provider names in layers 0–1 | New core files (`agent_time.py`, `verify_record.py`, `verify-*.sh`, `verify.conf.example`, `retirement-review.md`, the reworded skills) must name no provider |
| `tests/framework/test_bootstrapped_project.py` | After bootstrap, `tests/framework/` is green | `test_agent_time.py` and `test_doc_contracts.py` must pass in a bootstrapped copy, where placeholders are replaced and `doc/specs/` and `doc/qa/` may be empty |
| `tests/framework/test_settings_deny.py` | Deny rules and the SessionStart hook | Unaffected (settings unchanged) |
| `tests/coordinator/test_coordinator_lint.py` (19) | Existing rules 1–5 | Rule 6 applies only to `Slice:` blocks. Existing fixtures have none, so they stay clean `[MEASURED: grep -c 'Slice:' tests/coordinator/*.py → 0 and 0]`. |
| `tests/coordinator/test_handback_lint.py` | Fields 5–6 | New flags are opt-in. Default behaviour is unchanged. |

**New tests:** rows 3, 4, 11, 13 and 36 of the impact table.

**`scripts/verify-fast.sh` routing (new `case` lines):**
- a touch to `scripts/verify`, `scripts/verify_record.py` or `scripts/verify.conf` → `tests/hooks/test_verify_scripts.py`, `test_verify_tiers.py`, `test_verify_handoff.py` and `test_verify_merge.py`;
- `scripts/agent_time.py` or `tests/framework/test_agent_time.py` → that test file;
- `.claude/meter` → `tests/hooks/test_transcript_reader.py`;
- `tests/framework/test_doc_contracts.py`, `doc/templates`, `.claude/agents` or `.agents/skills` → `tests/framework/test_doc_contracts.py`;
- `scripts/handback_lint.py` is already routed (line 71).

## Technical Design

See the design document for:
- interfaces (Python signatures, 3.9-compatible);
- the record schema;
- the ban list;
- the polling matcher;
- the selection algorithm;
- config keys;
- the golden timeline;
- ADR-1 … ADR-14.

Files to create or modify are listed in full in the impact table above.

## Decisions (ADR-style) — summary

Full context and consequences are in the design.

- **ADR-1** The meter's core is neutral, and reads transcripts only through `--reader <path>`. The adapter ก reader lives in `.claude/meter/`. No reader means `unsupported`.
- **ADR-2** Clock events are an *allow-list* (`user`, `assistant`), not a deny-list. Adapter ก writes at least 8 timestamped event types, and 6 of them are internal `[MEASURED: event-type count over this repo's own 15 transcript files: assistant 733, attachment 658, user 512, api-request 289, system 82, queue-operation 62, api-request-shape 22, file-history-delta 1]`.
- **ADR-3** A turn is a distinct `message.id`. In the same 12 subagent transcripts: 501 assistant lines, 170 distinct ids `[MEASURED]`.
- **ADR-4** Project values live in `scripts/verify.conf`, sourced by every tier and able to override `STEPS`, `LINT` and `TEST`. The opt-in is `VERIFY_HANDOFF_TIER=on` in that file, not the file's mere presence.
- **ADR-5** Counts come from JUnit XML plus a project collect command. `reported` includes skipped cases.
- **ADR-6** The tree hash is computed through a temporary index, before and after the run.
- **ADR-7** The template ships the selection *wrapper*, not a selector. The project supplies `VERIFY_SELECT_CMD`.
- **ADR-8** Unconfigured counts keep GREEN in the full tier (R12), but the merge gate refuses (NOT RUN).
- **ADR-9** R26 has one override, `ALLOW_POLL=1;` at the head of the first segment (owner ruling, 2026-10-20). It waives only R26, and the rule covers Bash only.
- **ADR-14** Filters in configured step commands are allowed only when declared in `VERIFY_ALLOWED_FILTERS` with a reason. They are printed every run. The hard bans can never be allow-listed (owner ruling, 2026-10-20).
- **ADR-10** The merge gate runs in a fresh `git worktree`. The local fallback uses `nohup`, because `setsid` is absent on the owner's machine `[MEASURED: which setsid → "setsid not found"]`.
- **ADR-11** Document contracts are tests inside existing gate steps, not new STEPS lines.
- **ADR-12** R21 stays in increment 8 as the backlog orders it (conflict flagged above).
- **ADR-13** A rework run is marked by a `REWORK:` line in the coordinator's brief.

## Traceability

R1 → AC-AC6, AC-AC14, B-AC8 · R2 → AC-AC5, AC-AC7, B-AC7 · R3 → AC-AC3, AC-AC4, AC-AC14 · R4 → AC-AC8, AC-AC9, AC-AC16, AC-AC17, AC-AC18, AC-AC19, B-AC11 · R5 → AC-AC9, AC-AC10, B-AC12, D-AC5 · R6 → AC-AC11 · R7 → B-AC1, B-AC2, B-AC3, B-AC9, B-AC10 · R8 → B-AC4, B-AC5 · R9 → B-AC6 · R10 → AC-AC1, AC-AC2, B-AC12 · R11 → AC-AC11, AC-AC12 · R12 → AC-AC13, AC-AC14, AC-AC15, AC-AC16 · R13 → D-AC1, D-AC2, D-AC3, D-AC5, E-AC1 · R14 → D-AC6 · R15 → D-AC7 · R16 → D-AC1, D-AC4 · R17 → D-AC8 · R18 → E-AC7 · R19 → E-AC8 · R20 → E-AC4, E-AC5, E-AC9 · R21 → E-AC1, E-AC2, E-AC3, E-AC6 · R22 → F-AC1, F-AC2 · R23 → F-AC3 · R24 → F-AC4 · R25 → F-AC5, E-AC6 · R26 → G-AC1, G-AC2, G-AC3, G-AC4, G-AC7, G-AC8 · R27 → G-AC5, J-AC10 · R28 → G-AC5, G-AC6 · R29 → H-AC1 · R30 → H-AC2, H-AC3 · R31 → H-AC4, H-AC5 · R32 → J-AC9 · R33 → I-AC1, I-AC2 · R34 → I-AC3 · R35 → I-AC3 · R36 → I-AC4, F-AC6 · R37 → J-AC1, J-AC2, J-AC8, J-AC11 · R38 → J-AC2, J-AC5, J-AC10 · R39 → J-AC6, J-AC7 · R40 → J-AC3, J-AC4

Metrics: M1, M2, M8, M10–M14 → F-AC2 · M3 → D-AC1 to D-AC3 (the record exists) plus the F trial · M4 → F-AC7 · M5 → B-AC10, F-AC3 · M6 → AC-AC3, F-AC3 · M7 → F-AC4 · M9 → D-AC6.

**40 requirements → 83 acceptance criteria** `[MEASURED: grep -cE '^\| (J|AC|G|B|H|D|I|E|F)-AC[0-9]+' on this file → 83; a loop over R1–R40 found every one in the traceability line]` (J 11, A+C 19, G 8, B 12, H 5, D 8, I 4, E 9, F 7). Every R1–R40 maps to at least one.

## Open questions for the owner (none block approval)

1. **Collection cost in the fast tier (R1).** R1 asks for "ran N of M" with M computed by the script. In the fast tier that means a collect run on every inner-loop call. Its cost on the pilot suite of about 12k tests is unknown `[INFERRED; settle by timing VERIFY_COLLECT_CMD in the pilot during F]`. If it is large, the fallback is `ran N of ?` in the fast tier only, which would need an owner ruling on R1.
2. **RESOLVED by the owner, 2026-10-20: "ใช้คำแนะนำของจาวิสทั้งสองข้อ".** R26 has an explicit override, `ALLOW_POLL=1`, modelled exactly on `ALLOW_DESTRUCTIVE=1`. It counts only as an env assignment at the head of the first segment, it waives the polling rule only, and it is visible in the transcript (G-AC7, G-AC8, ADR-9).
4. **RESOLVED by the owner, 2026-10-20 (same ruling).** The R4/R12 conflict is settled by a declared allow-list, `VERIFY_ALLOWED_FILTERS`, in `scripts/verify.conf`:
   - A project's own step commands may use only the marker or deselect filters (`-m`, `-k`, `--deselect`) declared there, each with a reason.
   - Any undeclared filter, and any `--lf`/`-x`/`--maxfail`, still exits 2.
   - Declared filters are printed on every run, so they are never silent.
   - `--lf`, `--last-failed`, `-x`, `--exitfirst`, `--maxfail`, retries and cached results can never be allow-listed.
   - The ACs are AC-AC16 to AC-AC19, and the decision is ADR-14.
   - During F's upgrade step, the pilot's existing step commands are still grepped for ban tokens, so that each hit is either declared with a reason or removed. That is config only, and R24 allows it.
3. **Selector for the pilot (ADR-7).** The framework ships no selector. The trial has to choose one for the pilot project, and that choice is pilot config (R24 allows it). The choice can bring in a dev dependency, which the trial records.

## Approval history

- **2026-10-20 — approved (human).** Registry key `spec-verify-tiers-merge-gate-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** ba-sa, from the approved PRD, the backlog order, a read of the current working tree (including the owner's uncommitted edits), the coordinator's throwaway meter scripts (prior art), and probes run in this repo and in a scratch git repo. The pilot-project transcripts could not be read (see the handoff), so every pilot figure here is relayed from the PRD.
- **2026-10-20 — revised (still In Review).** ba-sa applied the owner's ruling "ใช้คำแนะนำของจาวิสทั้งสองข้อ", which resolves Q2 and Q4:
  - R26 gains the `ALLOW_POLL=1` head-position override (G-AC7, G-AC8, ADR-9).
  - The R4/R12 conflict is settled by the declared filter allow-list `VERIFY_ALLOWED_FILTERS` (AC-AC16 to AC-AC19, ADR-14).
