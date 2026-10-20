# QA Report: Verify tiers — increment G (no hand-written polling, R26–R28)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Date: 2026-10-20

## Verdict: PASS

All 8 G-ACs pass. Each verdict rests on a command run in this round. The full gate `scripts/verify-full.sh` is green (see Test Run).

**Read this first: the brief and G-AC1 conflict on 2 real commands.** I ran 2,204 unique Bash commands from this repo's own session logs through the hook. It refused 3 of them, all for R26, and refused nothing else:

| Count | Shape | Is it a wait? | Verdict |
|---|---|---|---|
| 1 | `until [ -s <task output> ]; do sleep 5; done; tail … \| grep …` | Yes, a poll on a background job's output file | True positive. This is the exact shape R26 exists for |
| 2 | `S=…; for i in $(seq 1 20); do …git init…; sleep 1.1; …; done` | No. It reproduces a file-timestamp race, so the sleep is part of the test | Refused by design. G-AC1 requires refusing `for i in $(seq 20); do cat s; sleep 5; done`, which has the same shape. The guard cannot tell the two apart, and the spec gives it no way to |

The brief says "any normal command refused is a defect". By that rule, the 2 race-harness refusals would be defects. But the implementation does exactly what G-AC1 requires, so `missed-ac` and `regression` would both be false labels. The only label that could fit is `spec-defect`, and deciding that the AC is wrong is the owner's call, not QA's. The cost is small and has a way out: `ALLOW_POLL=1; <same command>` exits 0, as measured below and pinned in `test_regression_the_race_harness_runs_with_the_head_override`. I record it as a PASS with this note. I do not raise it as a defect.

Provenance: the brief confirms the spec is APPROVED and cites the owner's lean-gates ruling ("guard code gets full QA"). **It does not say that a human approved the implementation, which the QA role requires before QA starts. I am flagging that gap here.** The code is under test at commit `18aee03` on branch `worktree-agent-ae5d50e3b8b1cf243`.

## Criteria Results

| # | Criterion | Verdict | Evidence (executed this round) |
|---|---|---|---|
| G-AC1 | The four spec loops are refused on clean and dirty trees; stderr names `rule R26`, says `hand-written polling loop`, and tells the agent to end its turn or do independent work; red-first | PASS | `test_a_hand_written_polling_loop_is_refused` and `test_the_refusal_names_the_rule_and_tells_the_agent_what_to_do` PASSED in the gate. **Red-first reproduced independently:** I put the pre-G guard (`git show 5e7c96f:.claude/hooks/guard_bash.py`) in a scratch copy and ran the engineer's polling suite against it: `66 failed, 86 passed`. That matches the engineer's claim of 66. The failures were 42 refusal cases, 8 message cases, 2 G-AC3 cases and 14 G-AC8 cases. Real logs: the 1 genuine background wait is refused (see above) |
| G-AC2 | `while read … done < f`, `for f in *.py …`, grep of a loop string, heredoc loop, `sleep 60 && cat`, and every `MUST_ALLOW` entry all exit 0 | PASS | `test_ordinary_work_is_not_refused` (NOT_POLLING + imported MUST_ALLOW) PASSED in the gate. Real logs: 2,201 of 2,204 commands exit 0. The 3 refusals are the 3 loop+sleep commands above, so nothing outside the R26 shape was refused. Of the 466 commands that contain the words `while`/`until`/`for` and the 29 that contain `sleep`, none was refused unless a sleep ran inside a loop. New: `test_regression_a_sleep_after_a_closed_loop_is_not_refused` (`done \| sort; sleep`, `done 2>&1; sleep`, nested `done; done; sleep`, an escaped `\"` in the loop list) |
| G-AC3 | `ALLOW_DESTRUCTIVE=1` before a polling loop is still refused | PASS | `test_allow_destructive_without_separator_is_still_refused` and the two HOSTILE_LOOPS cases PASSED. Probe: `ALLOW_DESTRUCTIVE=1 until true; do sleep 1; done` → exit 2, R26. New: the `ALLOW_DESTRUCTIVE=1 <loop>` case in `test_regression_allow_poll_off_the_head_does_not_waive_r26` |
| G-AC7 | `ALLOW_POLL=1; <loop>` and `FOO=bar ALLOW_POLL=1; <loop>` exit 0; `ALLOW_POLL=1; git reset --hard` on a dirty tree is still blocked by A1' | PASS | `test_allow_poll_at_the_head_waives_r26` and `test_allow_poll_does_not_waive_the_destructive_rule` PASSED. Probes, all exit 0: `ALLOW_POLL=1 && <loop>`, `ALLOW_POLL=1\n<loop>`, a leading space before the override, and a tab after `;`. On the real race harness, `ALLOW_POLL=1; ` prefixed → exit 0 (new `test_regression_the_race_harness_runs_with_the_head_override`) |
| G-AC8 | `ALLOW_POLL=1` anywhere but the head is still refused; red-first by swapping in a substring check | PASS | `test_allow_poll_outside_the_head_does_not_waive_r26` PASSED. **Teeth reproduced independently:** in a scratch copy I replaced line 331 with `if poll_reason and not ("ALLOW_POLL=1" in command):`. The polling suite then gave `12 failed, 140 passed`: all 4 spec cases on both trees, plus `ALLOW_POLL=10` and `'ALLOW_POLL=1'` on both. I did not edit the live hook. Extra positions probed, all exit 2: `cd /x; ALLOW_POLL=1; <loop>`, `export ALLOW_POLL=1; <loop>`, `(ALLOW_POLL=1; <loop>)`, `allow_poll=1; <loop>`, `ALLOW_POLL=0;`, `ALLOW_POLL='1';`. These are pinned in `test_regression_allow_poll_off_the_head_does_not_waive_r26` and go red against the pre-G guard (7 failed / 5 passed on the new file) |
| G-AC4 | Existing `test_guard_bash_matrix.py` and `test_guard_bash_bypasses.py` pass unchanged | PASS | `git show --stat 18aee03` touches neither file. Both run green in the `hooks` step of the gate |
| G-AC5 | ADAPTERS.md: adapter ก has `R26 polling guard: enforced` and `completion notification: yes`; adapter ข has `R26: no enforcement`, the fallback (rule text plus R37), what is weaker, and `completion notification: no` with the foreground+timeout substitute | PASS | The three G-AC5 tests in `tests/framework/test_doc_contracts.py` PASSED in the `framework` step. I read the diff: the rows are present in both adapter sections, and ข's R26 row states that its own R37 is `unsupported`, so the fallback is rule text only. That is honest |
| G-AC6 | engineering-loop SKILL.md carries the waiting rule and the anchor phrase | PASS | `test_engineering_loop_carries_the_waiting_rule` PASSED. Section `## Waiting on background work` is present, with `**Never poll.**` and the ADAPTERS.md pointer |

## Test Run

```
$ scripts/verify-full.sh        (in the worktree, with the new QA report and regression file present)
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             408 passed in 19.22s
  OK   ci-examples       19 passed in 0.51s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — [...]
  OK   coordinator       111 passed in 1.63s
  OK   framework         memory: 0 problem(s) in <repo>/doc/memory
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.
Fill those steps in scripts/verify-full.sh before treating this output as a gate.
rc=0

$ python3 -m pytest tests/framework/ -q -p no:cacheprovider     (the framework step's pytest count, which the summary line hides)
100 passed, 1 skipped in 8.14s
```

The hooks step went from 396 to 408. That is the engineer's 396 plus the 12 new `test_regression_*` cases in `tests/hooks/test_regression_guard_bash_polling.py`. The three `TODO` steps are template placeholders that this framework repo does not configure. They are not part of increment G.

## Defects (if FAIL)

None. No G-AC fails.

## Edge Cases Probed

Each line was run through the live hook, and through the pre-G hook for comparison. Results are exit codes.

- Real logs: 2,204 unique Bash commands → 2,201 exit 0, 3 exit 2 (all R26, explained above), 0 tracebacks. Only 1 command left loop depth open at the end (see Parked P1), and it had no sleep after the loop, so nothing was refused because of it.
- Detection, all exit 2: multi-line `while true\ndo\n sleep 1\ndone`; nested loop with sleep in the outer body; `/bin/sleep`; `env sleep`; sleep in the loop condition; sleep inside `if … fi` and `{ …; }` in the body; `sleep $((1+1))`; `for ((i=0;i<3;i++)); do sleep 1; done`.
- Not refused, all exit 0: `case x in a) sleep 1;; esac`; `echo for while until; sleep 1`; a `git commit -m` message holding a loop; a `python3 -c` loop with `time.sleep`; a heredoc fed to bash (declared limit); `echo done; sleep 1`; `{1..3}` brace loop then sleep; `for ((…))` loop then sleep; a `# for each file` comment then sleep.
- Crash inputs: the commands `for`, `done`, `do`, `sleep`, `;`, NUL bytes, Thai text, a 5,000-loop chain, and 2,000-deep nesting all give exit 0/2 with no traceback. Non-string `command` (a list, an int) → exit 0. An unpaired surrogate escape in the JSON → exit 2, R26, no traceback.
- Crash inputs that predate G: a payload that is a JSON list or string, or a `tool_input` that is a string or null, gives a traceback and exit 1 **on both the pre-G and the G hook** (see Parked P4).

## Parked (outside the G-ACs; not defects)

- **P1. False refusals that no G-AC lists.** The `done` that closes a loop is only recognised as a whole token. These spellings leave loop depth open, so a later `sleep` is refused: `…; done<f; sleep 1` (new, the same class as the engineer's declared `done>log`) and `…; done>log; sleep 1`. A quoting mismatch can also hide a separator and leave depth open. In the real logs this happened on 1 command, which had mixed quotes (`"pytest 'x"`, `"pytest \"-x"`) in a `for` list, and it caused 0 refusals because no sleep followed. Correcting the engineer's note: `done& sleep 1` on one line **passes** (exit 0). Only `done&` followed by a separate `sleep` segment trips. None of these is pinned in a test either way, so that a test does not lock in the bug.
- **P2. Misses the ADAPTERS R26 row does not declare.** These pass with exit 0: `while true; do timeout 5 sleep 1; done`, `select x in a b; do sleep 1; done`, and the engineer's own `command sleep`, `& sleep` and `read -t`. The owner ruling says other spellings are declared limits. But these are not in the limits cell of `doc/framework/ADAPTERS.md`. Whether to list them is a doc call for the owner.
- **P3. The override is accepted on a non-loop head.** `ALLOW_POLL=1 true; <loop>` and `ALLOW_POLL=1 | <loop>` exit 0. In bash, the assignment there is scoped to `true` only. It still sits at the head of the first segment and is visible in the log, so it meets G-AC7/G-AC8 as written. `ALLOW_DESTRUCTIVE=1` behaves the same way.
- **P4. Fail-open on malformed payloads, which predates G.** A payload that is a JSON list or string, or a `tool_input` that is a string or null, raises `AttributeError` in `main()` and exits 1. The runtime treats exit 1 as non-blocking, so every rule is skipped for that call. The pre-G hook at `5e7c96f` behaves identically. G did not introduce it.

## Approval history

- **2026-10-20 — drafted.** By qa, against commit `18aee03`. Based on SPEC-verify-tiers-merge-gate.md G-AC1–G-AC8 and an independent scan of the repo's own session logs.
