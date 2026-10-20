# PRD: Agents close work faster — verify tiers, merge gate, less waiting, less rework

Status: Approved
Approval: prd-verify-tiers-merge-gate-2026-10-20
Owner: pm
Upstream: owner request 2026-10-20 ("เราจะอัพเดทการทำงานที่ไวขึ้นให้กับ framework จาวิสตั้งต้นใน folder นี้"; earlier "เราจะทำให้การทำงานของ agent ปิดงานได้ไวขึ้นได้ไหม"; addition "ต้องทำให้ใช้งานได้จริงได้ด้วยนะ"; open questions delegated "เลือกแนวทางที่ดีที่สุด"; scope widened "วางแผนปรับได้เลย") · coordinator transcript measurement 2026-10-20 · external research outside this repo: jarvis-research/reports/ (report 1 "ลดเวลาเทสต์ชุดใหญ่ของเอเจนต์.md"; report 2 the file starting "แนวทางระดับโลกลดเวลาเทสต์", which governs)
Date: 2026-10-20

Risk tier: 2. This changes framework rules: AGENTS.md §4–§5, the engineering-loop and coordinator-discipline skills, the agent definitions, the spec and QA-report templates, `scripts/verify-*.sh`, the interception adapter, and `doc/framework/ADAPTERS.md`.

**References.**
- "Report 1" and "report 2" are the two research reports in the external folder `jarvis-research/reports/`, next to this repo on the owner's machine. They are not part of the template. Where they conflict, report 2 governs.
- "Pilot project" (Thai: โปรเจกต์นำร่อง) is the real downstream project built on this framework. The evidence was measured there, and the trial runs there. Its real name is kept out of the template on purpose.
- The filename keeps the original slug (`verify-tiers-merge-gate`) so the approval slug stays stable. The scope is wider than the slug suggests.

## Problem

In projects built on this framework, an engineer agent spends on average (mean) 51 minutes of active work per run (median 38), and most of it is not spent on the change itself. The time splits as follows:

| Share | What it is |
|---|---|
| 37% | Running and waiting on tests |
| 11% | Polling and waiting on background work, some of it in hand-written sleep loops |
| 23% of all runs | Whole runs that are only rework sent back by QA |

The test cost comes from a framework rule that requires the full suite before every handoff, with QA running it again. Once a suite grows large, that rule costs too much. So people stop following it, and agents fall back to choosing tests by judgement. That choice is unsafe, and the result reads like a pass even though most tests never ran. The framework must make agents close work faster on four fronts:

- run fewer tests, chosen by a machine;
- stop hand-polling;
- send work back less often;
- take fewer model turns.

All of this must keep the guarantee that nothing reports green unless it actually ran. It must also be measured with a repeatable instrument, not estimated.

### Evidence: agent time (coordinator transcript measurement 2026-10-20)

Source: pilot-project agent transcripts from the last 21 days, covering 170 engineer runs, 90 frontend-engineer runs, 27 QA runs and 52 ba-sa runs. Time comes from tool-call timestamps, with internal log events excluded.

| Agent | Active min per run (mean) | Model generating | Tests | Polling / background waits | Other tools | Read/git/edit |
|---|---|---|---|---|---|---|
| engineer | 51 | 19.5 (39%) | 18.5 (37%)¹ | 5.4 (11%) | 5.1 (10%) | 1.3 |
| frontend-engineer | 40 | 41% | 42% | — | — | — |
| qa | 20 | 65% | 9% | — | — | — |
| ba-sa | 22 | 80% | — | — | — | — |

¹ The 18.5 minutes of engineer test time breaks down as:
- 13.6 min running tests
- 2.5 min waiting on background runs
- 2.4 min in hand-written polling loops

Other measurements:
- **Rework.** 39 of 170 engineer runs (23%) were QA rework.
- **Idle time.** The median is 0 min. Idle time is concentrated in about 10% of runs where an agent was reused, and it is out of scope.
- **Owner reply latency.** The median is 2 min, so the owner is not the bottleneck. This is also out of scope.

### Evidence: test suite (MEASURED by the coordinator on 2026-10-20 in the pilot project unless tagged)

- The suite has 12,338 test cases. It grew about 9x in 11 weeks, and growth has recently slowed to about 51 test functions per day.
- A full run on the owner's laptop takes 16m52s with 4 workers and 14m28s with 8 workers.
  - The suite is CPU-bound at about 66 CPU-minutes, so on that hardware a full run cannot get below about 16.5 min.
- Time is concentrated in a few tests.
  - The slowest 5% of tests take 48% of the time.
  - The 52% of tests that run under 0.1s take 1.5% of the time.
- 30 tests are red on HEAD in every run.
- A handoff run scoped by judgement, which touched a shared file, pulled in 178 test files and took about 17 min (report 2).
- Several features ran the full suite more than once on a laptop (pilot-project QA reports, quoted in report 2).
- Estimate, not measured: at the current growth rate, the laptop floor rises by about 3–7.5 min per month.

## Goal & Success Metrics

**Goal.** Agents close work faster. The headline measure is engineer active time per run. Every merge still gets one full run by a machine, and every partial result says plainly that it is partial.

Baselines come from the pilot project. "After" numbers come from the real-project trial (R22), measured with the R37 meter.

| # | Metric | Baseline | Target |
|---|---|---|---|
| **M10 (headline)** | Engineer active time per run, median **per size class**, measured with the R37 meter (R41). Size class = distinct files edited in the run. Baseline: coordinator measurement 2026-10-20 over 170 pilot-project engineer runs. | Investigate-only (0 files, 9 runs): 20 min · Small (1–5 files, 71 runs): 20–22 min · Medium (6–10 files, 32 runs): 35 min · Large (11+ files, 58 runs): 73 min | Investigate-only: report only · **Small ≤ 15 min · Medium ≤ 25 min · Large ≤ 50 min**. The owner accepts the result only if these targets are met in real measurement (R22). |
| M10a (report only) | Engineer active time per run, overall mean and median, and by type | Mean 51 min; median 38 min · tier-0 bugfix median 33 min; spec work median 72 min | Report only. The task mix shifts overall numbers, so they carry no target (the earlier ≤ 37 min mean target is reported, not judged). |
| M11 | Share of engineer runs that are QA rework | 23% (39 / 170) | ≤ 15% (pm proposal, A7) |
| M12 | Engineer test share of active time | 37% (18.5 min) | Reported before and after; must not rise |
| M13 | Engineer polling and background-wait share of active time, with hand-written polling loops reported separately | 11% (5.4 min) + 2.4 min in hand-written loops | Hand-written polling loops: 0 per run. The rest is reported before and after. |
| M14 | Model-generating time per run, for each agent type | engineer 19.5 min; frontend-engineer 41%; qa 65%; ba-sa 80% | Reported before and after. The saving is unproven, and a trial result of no gain is acceptable (R36). |
| M1 | Wall time from "code done" to "handoff" per feature, median over trial features | Measured at the start of the trial (replays allowed) | At least 50% lower than the trial's own baseline |
| M2 | Full-suite runs per feature on a developer or agent machine, in an opted-in project | Several | 0 required. The only required full run is 1 per merge, in the merge gate. |
| M3 | Merges with a merge-gate record tied to the merged tree hash, or an explicit "merge gate not run" | 0% | 100% of merges during the trial |
| M4 | Handoffs or QA reports that call a partial run "passed", "green" or "suite passes" without "ran N of M" | Not tracked | 0, checked by a script over the trial's handoffs and QA reports |
| M5 | A planted regression is caught by the handoff tier during the trial | n/a | Caught: red, with the test named |
| M6 | A dropped test is caught by the executed == collected check during the trial | n/a | Red, naming the mismatch |
| M7 | Adoption cost for a bootstrapped project to switch on the new tiers | n/a | Config only, with no edits to framework scripts. At most 6 documented steps and 60 minutes. |
| M8 | Wall time of the merge-gate full run on the runner the pilot project uses | 16m52s on the laptop | Recorded with the runner identity and worker count. No target. |
| M9 | Rule locations that still require a full run before every handoff, or a second full run by QA, with no exception for opted-in projects (R14 patterns) | 12 requiring locations + 3 related | 0. The related locations are consistent. |

## Requirements (must-have)

Scope key:
- **T** = ships in the framework template. It must stay neutral and pass `scripts/check_neutrality.py`.
- **A** = adapter-specific. It is declared per adapter in `doc/framework/ADAPTERS.md`.
- **P** = the project configures it.
- **T+P** = the template ships the mechanism and the project supplies the values.

### A. The no-fake-green guarantee. Everything else depends on these.

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R1 | Any run that executed fewer tests than the project's full collected set prints `ran N of M`, with both numbers computed by the script. It never prints GREEN, "suite passes" or any wording reserved for a full run. | T | Report 2 §7: the label must come from the script, not the agent. |
| R2 | When a selected run selects 0 tests, or a shard executes 0 tests, the run ends in a non-pass status. It is neither GREEN nor OK. | T | Both reports. |
| R3 | The full-run tier checks that tests executed == tests collected, summed across shards and workers. A mismatch is red and names the counts. The check must first be shown going red when a test is dropped on purpose, then green after reverting. | T | Report 2 item 8; engineering-loop failure mode #2. |
| R4 | These bans hold in every tier, and each is covered by a test showing it is still refused or flagged: `--lf`/`--last-failed`, `-x`, `-k`/`-m` filtering used to reach green, a cached pass reported as a fresh run, and retries that turn a failure into a pass. | T | Owner brief: the hard bans stay. |
| R5 | No result counts as evidence for a tree other than the one it ran on. Every pass shown in a handoff, QA report or merge-gate record comes from a run on the tree being judged. This PRD introduces no "reused result" status. | T | D2. Report 1: cached passes look identical to fresh ones. |
| R6 | Time-budget warnings (R11) never change a run's pass/fail status. | T | Report 2 item 8(b). |

### B. Handoff tier: tests chosen by machine, not judgement

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R7 | The framework provides a handoff tier whose test selection a machine computes from the tree's actual diff against its base. The agent never picks the tests. Paths the agent supplies can add tests but never remove any, and any difference from the actual diff is reported. QA test: leave out one touched path, and show that its tests still run and the omission is reported. | T | Report 2: selection by judgement is "not safe 74% of the time". |
| R8 | The project declares which inputs its selector cannot track (docs, config, data, fixtures). When a declared input changes, the handoff tier runs the full collected set and says so. If nothing is declared, it runs the full set. | T+P | Report 2 item 5: in the pilot project, 69 test files read `doc/`. |
| R9 | The handoff tier is opt-in per project. A project that has not opted in sees "not configured", never a claimed selection. For that project, `verify-full` before every handoff stays in force. | T | D4. |

### C. Full-run tier: `verify-full`, made measurable

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R10 | `verify-full` prints the wall time of each step. Each run also writes a machine-readable summary containing:<br>• per step: label, exit code and seconds;<br>• per test step: passed, failed, skipped and collected counts;<br>• for the whole run: tree hash, run-id, start and end time, and runner identity. | T | Report 2 item 8. This summary is the merge-gate record. |
| R11 | `verify-full` warns when a step goes over its budget, or a test goes over its per-test budget, and lists the slowest tests. The template ships default warning thresholds by size class (small/medium/large, Google-style), which each project tunes. These are warnings only (R6). | T+P | D3. 5% of tests take 48% of the time. |
| R12 | GREEN / INCOMPLETE / RED keep their current meanings. An existing project's `verify-full` output keeps working without edits. | T | Downstream projects and CI examples parse these words. |

### D. Merge gate: one full run per merge, by a machine

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R13 | The framework defines a merge-gate tier: one full `verify-full` run per merge candidate, on the final tree, before merge. It produces the R10 record, tied to that tree hash and naming the runner. Outcomes are reported in exactly one of these forms:<br>• GREEN;<br>• "RED, no failures beyond the named baseline" (R21), never shown as GREEN;<br>• RED;<br>• "merge gate not run".<br>An agent-triggered run counts only if both hold:<br>• it ran in a runner process the agent did not edit;<br>• it wrote the record with the tree hash and runner identity.<br>The framework states that this is tamper-evident, not tamper-proof. | T+P | Report 2 item 9 reverses report 1. D6, D8. |
| R14 | Reword every framework rule location that requires a full run before every handoff. The requirement stays in force for projects that have not opted in (R9). Opted-in projects use the handoff tier plus the merge gate.<br>The 12 known locations as of 2026-10-20:<br>• `AGENTS.md:46`<br>• `.agents/skills/engineering-loop/SKILL.md:45,69`, plus the loop diagram<br>• `.claude/agents/ai-engineer.md:30,37`<br>• `.claude/agents/qa.md:18,28`<br>• `scripts/verify-full.sh:2,89`<br>• `doc/framework/SETUP.md:38`<br>• `.claude/agents/frontend-qa.md:15,30`<br>Related locations that must stay consistent:<br>• `.agents/skills/coordinator-discipline/SKILL.md:119`<br>• `doc/framework/WHY.md:150`<br>• `doc/framework/SETUP.md:59`<br>Search patterns: `before every handoff`, `before **every** handoff`, `full suite`, `exit gate`, `verify-full`, `ชุดเต็ม`, `ประตูออก`, `ก่อนส่งมอบ`.<br>Search over: `AGENTS.md`, `.agents/`, `.claude/agents/`, `doc/framework/`, `doc/templates/`, `scripts/verify-full.sh`.<br>ba-sa confirms the list is complete. | T | Report 2: a rule nobody follows is more dangerous than no rule. M9. |
| R15 | In an opted-in project, QA does not grade on any earlier run's record. QA's verdict rests on its own handoff-tier run plus the tests it added, on its own tree, labelled "ran N of M". The merge gate then re-runs the full suite on the final tree before merge. A merge-gate outcome other than GREEN or "RED, no failures beyond the named baseline" blocks the merge and sends the work back to the engineer. | T | D2. |
| R16 | The framework documents where the merge gate runs.<br>• Primary: a self-hosted runner, either a CI agent on a spare machine or a VM.<br>• Fallback: a local background run, detached from any agent session so that it survives that session ending. It is labelled as the weaker local fallback.<br>• A project with neither says so, and its merges are reported "merge gate not run", never green. | T+P | D1, D5; owner addition 4. |
| R17 | The project configures where its merge gate runs, the sharding command if any, and the source of the tree hash. The framework ships a neutral, documented example. Any provider-specific example stays in `ci-examples/` or an adapter. | P (T ships the example) | Keeps layers 0–1 neutral. |

### E. Keeping the suite in check

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R18 | The framework states an admission bar for new tests that a reviewer or script can check per test:<br>1. it was red before the fix, for the right reason;<br>2. it adds coverage no existing test has, or it kills a mutant on the changed lines;<br>3. it fits the per-test budget, or it is labelled slow with a justification;<br>4. it is not a change-detector.<br>A test's author never decides alone whether it is admitted. | T+P | Report 2: suites written by agents grow and stay shallow. |
| R19 | Retirement review runs quarterly, or when the full run exceeds its budget, whichever comes first. Each candidate comes with evidence: coverage and mutation results, never coverage alone. The owner signs off, and the sign-off is recorded in the approval registry. Nothing is deleted automatically. | T+P | D7. |
| R20 | Red-main policy:<br>• A red full run on the main branch is top priority and is triaged before new work. The repo is not frozen.<br>• Each red test ends in one of three states: fixed; converted with owner approval; or quarantined with a named owner and an expiry date.<br>• A quarantined test still runs and is still reported.<br>• A test that fails on every run cannot be quarantined.<br>• A project may adopt the merge gate before its main branch is green. | T | Report 2 item 1. D8. |
| R21 | When a known-red baseline exists, the full-run record lists every failing test by name and compares the failure set against the named baseline for exact equality. Any extra failure is reported as new, and a baseline test that starts passing is reported too. | T | Without this, a planted regression looks like "red as usual". Matches the coordinator-discipline skill. |

### F. Proven in real use (owner addition 2026-10-20: "ต้องทำให้ใช้งานได้จริงได้ด้วยนะ")

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R22 | The change is done only after a trial on the pilot project, run in a separate copy or worktree so that its branches, working tree and in-flight work stay untouched.<br>Scope: at least 3 features or fix tasks. Replays of recent features are allowed.<br>Before and after numbers to record:<br>(a) engineer active time per run, per size class and with its category split, using the R37 meter (M10, M10a, M12–M14). **Acceptance (owner, 2026-10-20: "โอเคพี่รับได้ถ้าเป็นไปตามเป้าจริง"): the change is accepted only if the M10 per-size targets (Small ≤ 15, Medium ≤ 25, Large ≤ 50 min) are met in the real measurement. A size class with too few trial runs to compute a median is reported as "not enough runs (n)" and the trial is extended for that class; it is never counted as met.** M10a is reported only;<br>(b) wall time from "code done" to "handoff" (M1);<br>(c) full-suite runs per feature (M2);<br>(d) merge-gate time and runner (M8);<br>(e) rework share (M11), noting that 3 features are too few to show a rate and are reported as counts.<br>While the pilot project's known reds remain, the merge-gate pass condition is "RED, no failures beyond the named baseline". | P (trial) | Owner addition 1. D8, D9. |
| R23 | During the trial:<br>• a planted regression is caught red by the handoff tier (M5);<br>• a dropped test makes executed == collected go red (M6);<br>• a planted hand-written polling loop is refused, or flagged, by the R26 enforcement point.<br>Each probe is reverted afterwards, with zero residue confirmed. Probe runs are excluded from the M10 per-size measurement, and the trial report says how many were excluded. | P (trial) | Owner addition 2. A guard not broken on purpose is not a guard. |
| R24 | The trial switches the pilot project onto the new tiers by filling in the documented config only. It records the number of steps and the minutes taken (M7). Any edit to a framework script during the switch is a defect. | T+P | Owner addition 3. |
| R25 | The trial does not fix, quarantine or convert any of the pilot project's tests. Existing reds are recorded as the baseline (R21) and handed to that project's own session. | P | doc/memory/project-reds-belong-to-project-session.md. |

### G. No hand-written polling

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R26 | Agents wait on background work through the harness's completion notification, never through hand-written polling loops (`until`/`while` … `sleep`, or a repeated status check with a sleep in between). The enforcement point is the interception adapter's pre-tool command guard: it refuses such a loop and tells the agent to use the completion notification instead. The refusal must first be shown biting on a planted loop. | T (rule) + A (enforcement) | Measurement: 2.4 min per engineer run in hand-written polling loops, plus 5.4 min in other polling and background waits. AGENTS.md §9: a lesson must become a mechanism. |
| R27 | Each adapter in `doc/framework/ADAPTERS.md` declares whether it enforces R26. An adapter without interception declares "no enforcement", names its fallback, and states what is weaker. The fallback is the rule text plus the R37 meter, which reports the polling share after the fact. | A | An exemption nobody can see is a hole (ADAPTERS.md convention). |
| R28 | Where an agent cannot proceed until a background run finishes, the framework rule tells it to end its turn, or do independent work, until the completion notification arrives. Where the adapter has no completion notification, the adapter declares that and names the substitute. | T+A | Removes the reason to poll. |

### H. Less rework

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R29 | The spec template requires an "Affected tests / affected files" section. ba-sa fills it in, and a spec without it cannot move to In Review. | T | 23% of engineer runs are rework. A past design missed 16 broken test files (ai-engineer.md). |
| R30 | Before handoff, the engineer records a self-check for each acceptance criterion in the spec: the criterion, the test or command that shows it passes, and that command's result. It also runs the handoff tier (R7) over its change, or `verify-full` where the project has not opted in. A handoff missing a self-check line for any criterion is incomplete. | T | Catches what QA would otherwise send back. |
| R31 | Every QA FAIL that sends work back records a rework cause, taken from a fixed list that the framework defines. The list covers at least: missed acceptance criterion; regression in untouched behaviour; spec ambiguity or defect; test gap; environment or flaky. Each defect has exactly one cause. | T | The rework rate and its causes can be tracked, and fixes can be aimed at the largest cause. |
| R32 | The R37 meter, or a companion report in the same style, reports the rework share (M11) and the counts per cause over a chosen window. It never gates. | T | M11 is measured by a mechanism, not by hand. |

### I. Fewer model turns (expected saving unproven)

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R33 | A coordinator brief that dispatches an engineer or QA agent names the exact files to touch or read, the acceptance criteria in scope, and the tests or tier to run. A brief missing any of the three is flagged by the existing coordinator brief check (`scripts/coordinator_lint.py` or its successor). | T | Model generation is 39–80% of active time. Agents spend turns rediscovering what the coordinator already knows. |
| R34 | The framework rule tells agents to issue independent reads, searches and commands together in one turn, rather than one per turn. | T | Fewer round-trips. |
| R35 | The framework rule tells agents not to re-read a large file already read in the same run unless it changed, and to read only the needed range of a large file. | T | Fewer tokens and turns. |
| R36 | The PRD records that the saving from R33–R35 is unproven. The trial measures model-generating time and the number of turns before and after (M14). A result showing no gain is acceptable and is reported as such; it does not fail the trial. | T | Owner instruction: measure it, don't promise it. |

### J. Measurement as a mechanism

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R37 | A neutral, stdlib-only script (the "R37 meter") reads agent transcripts and reports active time per run for each agent type. It splits time into these categories: model generating, tests, polling or background waits (with hand-written polling loops shown separately), other tools, and read/git/edit. It reports medians and shares, excludes the adapter's internal log events, and states its method and limits in its output. It is used for both the baseline and the after numbers. | T (script) + A (format) | The baseline was a one-off hand measurement. The after numbers must come from the same instrument. |
| R41 | The R37 meter reports active-time medians per size class, where size class is the number of distinct files edited in the run: investigate-only (0), small (1–5), medium (6–10), large (11+). For each class it shows the run count beside the median, and it also reports the overall mean and median. A run whose edited-file count cannot be determined from the transcript is counted as "size unknown" and never placed in a class. | T (script) + A (format) | D12. The headline target (M10) is per size class, so the instrument must produce it. |
| R38 | The transcript format is adapter-specific. The meter reads it through a per-adapter reader. `doc/framework/ADAPTERS.md` declares which adapters the meter supports. For an unsupported adapter, the meter says "unsupported" and reports nothing; it never reports zero. | A | A silent zero would be the silent-failure shape. Layers 0–1 stay neutral. |
| R39 | Like `scripts/correction_rate.py`, the meter never gates: it always exits 0 and only reports. It never prints real identifiers or transcript content, only categories, counts and durations. | T | It is a meter, not a gate. AGENTS.md §8: log names and counts, never values. |
| R40 | The meter's categorisation is checked against a small synthetic transcript fixture with known category totals. A planted miscategorisation makes that check fail. | T | The meter is itself a guard on the numbers. |

## Nice-to-have (explicitly deferred)

- Order-only test prioritisation in the full tier.
- Running `verify-full` steps in parallel.
- A periodic full run compared with the handoff-tier selection, to measure the selector's miss rate.
- Mutation testing scoped to changed lines as an automated admission check.
- A merge-queue-style "always green main".
- Meter readers for adapters beyond the first supported one.

## Out of Scope

- **Idle time and agent-reuse time.** The median is 0, and the idle time that exists is concentrated in reused-agent runs.
- **The owner's reply latency.** The median is 2 min, so it is not a bottleneck.
- **Fixing red tests inside any downstream project**, the pilot project included. That is each project's own session's job (doc/memory/project-reds-belong-to-project-session.md). The follow-up is that the pilot project triages its 30 reds.
- **Speed fixes specific to the pilot project.** These are follow-ups for that project's session; item numbers refer to report 2.
  - Render each PDF once per input (item 2).
  - Worker count (item 3).
  - Runner and sharding setup (item 4).
  - Moving structure-watching tests to lint (item 5).
  - Removing change-detector tests (item 6).
  - Splitting the layout model (item 10).
- **Changing the model, the provider, or the model's settings** to cut generation time.
- **Buying CI hardware or runner licences.**
- **Choosing the selector, the sharding tool, the record format, the meter's internals or the guard's matching rules.** These are ba-sa's design.
- **A "reused result" status** (D2).
- **Relaxing any hard ban in R4.**
- **Changing the approval gates, the pm role, the approval registry, or AGENTS.md §5–§6**, beyond the rewording required by R14.

## Assumptions

- A1. Report 2 governs where the two reports conflict. For opted-in projects, the merge gate replaces "verify-full before every handoff".
- A2. "Faster" is measured as engineer active time per run (M10, the headline) and time from "code done" to "handoff" (M1). It is not measured by the speed of the full suite itself.
- A3. The trial runs from the framework session in a separate worktree. It touches the pilot project's tests only to plant probes and then revert them (R23).
- A4. Two targets are pm proposals: the 6 steps / 60 min adoption target (M7) and the 50% reduction for M1.
- A5. The default per-test warning thresholds in R11 are pm proposals: small 1s, medium 10s, large 60s. They are confirmed at spec time.
- A6. The research reports, the pilot-project figures and the transcript measurement are inputs that pm read but did not re-measure.
- A7. The M11 target of ≤ 15% is a pm proposal. It assumes R29–R31 remove about a third of today's rework. A 3-feature trial cannot confirm a rate, so M11 is confirmed over the first 4 weeks of use after adoption, and the trial reports counts only.
- A8. The headline target (M10) is per size class (Small ≤ 15, Medium ≤ 25, Large ≤ 50 min), set by the coordinator and accepted by the owner on condition that it is met in real measurement ("โอเคพี่รับได้ถ้าเป็นไปตามเป้าจริง"). It is not met by projection: only R37/R41 meter numbers from the trial count. pm reads the savings as coming mainly from tests and polling (hand-written loops 2.4 min, plus part of the 18.5 min of test time and the 5.4 min of waits); fewer model turns (I) is upside not counted on. The earlier ≤ 37 min figure was set against the 51 min **mean**, not a median; it is kept as a report-only number (M10a).
- A10. Report only, no target: large runs (11+ files) are where most of the time is. Splitting large tasks is the likely lever for bringing them nearer 30 min. That is a possible follow-up and is not in this PRD's scope.
- A9. The first adapter the R37 meter supports is the interception adapter (adapter ก in ADAPTERS.md), because the baseline came from its transcripts.

## Decisions

The owner delegated the open questions on 2026-10-20 ("เลือกแนวทางที่ดีที่สุด"). The delegation is not approval, so this PRD stays In Review, and the owner can reverse any decision at approval. The owner then widened the scope on 2026-10-20 ("วางแผนปรับได้เลย"), and the coordinator recommended keeping a single PRD.

- **D1 (Q1).** Decided (coordinator, under owner delegation 2026-10-20). The merge gate runs on a machine runner. The primary option is a self-hosted runner, either a CI agent on a spare machine or a VM. The documented fallback is a local background run, detached and labelled weaker. → R16
- **D2 (Q2).** Decided (coordinator, under owner delegation 2026-10-20). QA does not grade on a reused record. QA runs its own handoff-tier run plus its new tests on its own tree, and the merge gate re-runs the full suite on the final tree. → R5, R15
- **D3 (Q3).** Decided (coordinator, under owner delegation 2026-10-20). The template ships default warning thresholds by size class, and projects tune them. They are warnings only. → R6, R11, A5
- **D4 (Q4).** Decided (coordinator, under owner delegation 2026-10-20). The handoff tier is opt-in per project. Until a project opts in, verify-full before handoff stays in force. → R9, R14
- **D5 (Q5).** Decided (coordinator, under owner delegation 2026-10-20). A project with neither option reports "merge gate not run", never green. → R13, R16
- **D6 (Q6).** Decided (coordinator, under owner delegation 2026-10-20). An agent-triggered run counts as the merge gate only if it ran in a runner process the agent did not edit, and it records the tree hash and runner identity. This makes tampering evident; it does not prevent it. → R13
- **D7 (Q7).** Decided (coordinator, under owner delegation 2026-10-20). Retirement review runs quarterly, or when the full run goes over budget, whichever comes first. The owner signs off. → R19
- **D8 (Q8).** Decided (coordinator, under owner delegation 2026-10-20). "RED, no failures beyond the named baseline" is reported exactly as such, never as GREEN. A project may adopt the gate before its main branch is green. → R13, R20, R22
- **D9 (Q9).** Decided (coordinator, under owner delegation 2026-10-20). The trial may replay recent features as its baseline. → R22, M1
- **D10 (Q10).** Decided (coordinator, under owner delegation 2026-10-20). Use the neutral alias "pilot project". The reports are cited as external. → whole document
- **D11 (scope).** Decided (coordinator recommendation, owner "วางแผนปรับได้เลย" 2026-10-20). Keep this as one PRD with the widened goal "agents close work faster", sections G–J and headline metric M10. The filename stays the same so the approval slug is stable.
- **D12 (headline per size class).** Decided (owner, 2026-10-20: "โอเคพี่รับได้ถ้าเป็นไปตามเป้าจริง", on the coordinator's per-size proposal). M10 becomes a per-size-class median target (Small ≤ 15, Medium ≤ 25, Large ≤ 50 min; investigate-only report only). Overall mean and median are report only (M10a). Acceptance requires the targets to be met in real measurement. The meter must report per size class (R41). This also corrects a factual error: the earlier M10 called 51 min a median; it is the mean, and the measured median is 38 min. → M10, M10a, R22, R23, R41, A8, A10

## Open Questions

None of these block approval. The owner may reverse any of D1–D12.

- **Q11.** Is ≤ 15% the right rework target (M11, A7)? The alternative is to report rework only until the first 4 weeks of data exist.
- **Q12.** Should R26 apply to the coordinator (the main thread) as well as to subagents? pm assumes it applies to every agent role, because the mechanism sits in the adapter and does not depend on the role.

## Approval history

- **2026-10-20 — approved (human).** Registry key `prd-verify-tiers-merge-gate-2026-10-20`, carried on the canonical `Approval:` line above.
- **2026-10-20 — approved (human).** Registry key `prd-verify-tiers-merge-gate-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** pm, from the owner's requests of 2026-10-20, including the addition "must actually work in real use". Inputs were the two external research reports and the pilot-project measurements the coordinator took on 2026-10-20.
- **2026-10-20 — revised.** pm recorded decisions D1–D10, which the coordinator made under the owner's delegation ("เลือกแนวทางที่ดีที่สุด"). The delegation is not approval, so the PRD stays In Review. pm also replaced the project name with a neutral alias and switched the report paths to the external `jarvis-research/`.
- **2026-10-20 — expanded.** The owner said "วางแผนปรับได้เลย". pm widened the goal to "agents close work faster" and added sections G (no hand-written polling), H (less rework), I (fewer model turns) and J (measurement as a mechanism), from the coordinator transcript measurement 2026-10-20. pm also added the headline metric M10 (51 → ≤ 37 min) and metrics M11–M14, and retitled the PRD while keeping the filename. The PRD stays In Review.
- **2026-10-20 — approved (key prd-verify-tiers-merge-gate-2026-10-20); amended same day: M10 per size class, re-approval pending.** pm, on the owner's acceptance of per-size targets ("โอเคพี่รับได้ถ้าเป็นไปตามเป้าจริง"). Changes: M10 per size class with M10a report only; corrected M10's "median 51 min" to mean 51 / median 38; R41 (meter reports per size class); R22/R23 and A8 make acceptance conditional on real measurement; A10 note on splitting large tasks; D12. The `Approval:` line was removed and the status reset to In Review; the registry keeps the earlier entry, and approve.sh stamps a new key on re-approval.
