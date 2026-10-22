# Backlog

Status: Living
Owner: pm
Upstream: doc/requirements/

Rows are in priority order, one deliverable per row, each linked to its PRD. The scope was re-cut by the owner on 2026-10-20 ("ตัดขอบเขตตามนี้เลย"; doc/memory/smallest-useful-scope-first.md): ship the smallest slice that meets the owner's two goals (agents close work faster, and the assistant runs the work), measure it in the pilot trial, and only then decide what comes next.

VT = [PRD-verify-tiers-merge-gate](../requirements/PRD-verify-tiers-merge-gate.md) · DA = [PRD-delegated-autonomy](../requirements/PRD-delegated-autonomy.md) · JC = [PRD-jarvis-coordinator](../requirements/PRD-jarvis-coordinator.md) (Approved)

## Active

Re-ordered by the owner on 2026-10-22 ("ใช้งานง่ายและจาวิสคุมงานได้ครบ e2e", then "เอาตามนี้ merge B1 แล้วเริ่มเลย"). Three groups, in this order: **1. close what is open**, **2. Jarvis runs work end to end**, **3. easy for other people**. Priorities were renumbered; "(was row N)" keeps the old number, because specs and QA reports cite rows by their old numbers. A "Left:" line was found from git log, doc/qa/ and spec Status lines on 2026-10-22 (head 41b2499).

| Priority | Item | PRD | Status | Why this priority |
|---|---|---|---|---|
| 1 | VT Part A+C: the no-fake-green guarantee and a measurable `verify-full` (was row 3) | VT | Done 2026-10-22: review PASS round 3 (afb16f9) found and fixed AC-AC20 false green (bash 3.2 `-n` misses an open array; also in handoff tier); QA PASS 24/24 (1b42298); fix merged c8c73e1 | Group 1. The handoff tier and the merge gate rest on it. |
| 2 | DA Part B: always-human guards (was row 4) | DA | Done 2026-10-22: review PASS (dca8783), QA re-test 2 PASS 10/10 (7cf1a8c) | Group 1. Guards come before any freedom. Task orders (row 5) depend on it. |
| 3 | VT Part G: no hand-written polling (was row 5) | VT | Done 2026-10-22: QA PASS 8/8 at 18aee03 plus independent review PASS (0fd71b6) | Group 1. Engineer runs lose 2.4 min to hand-written loops and 5.4 min to other waits, and the fix is small. |
| 4 | DA Part E, first half (E-AC1–E-AC4): learning loop, reviewer gate before QA, briefs carry the impact map (was row 6) | DA | Done 2026-10-22: E-AC2 rework (spec read only from `Spec:`/`Slice:`) review PASS (0d92200), QA re-test 3 PASS 4/4 (ea460cc), merged 0cc9c6c | Group 1. Getting it right the first time cuts rework and owner corrections. |
| 5 | DA Part J: task orders, plus the minimum that orders need from F, A, G and C (listed below). Also JC Increment 3 (R11), which adds nothing to the design. Also coordinator friction (d): one-page merge-ready summary with one command for the owner, folded into J-AC6 rather than a separate tool (was row 11) | DA + JC | Not started | Group 2. Directly delivers the owner's "the assistant runs the work end to end". Waits for row 2. J-AC6 merge needs VT Part D, which is done. Increment order 1 → 2 → 3 → 4 set by ba-sa under the owner's D1 ruling (SPEC-jarvis-coordinator, "Increment order"). |
| 6 | Coordinator friction seen 2026-10-21/22: (a) Tier 0 review cap: after review round 1, test-strength findings are parked, not rework (B1 took 2 rework rounds for a one-line grep); (b) no mid-task messages to the owner; (c) per-role brief templates so briefs pass the spawn guard the first time (a QA brief was refused once for `NO_SPEC_BUGFIX` without its colon); (e) `Reviewer-run:` stays hand-filled by the coordinator, because the reviewer cannot see its own run ID (reviewer.md line 25 already allows this): keep as is, no work. (d) is in row 5 | — | (a) and (b) done 7fbc2c4 (doc/memory/easy-and-end-to-end.md, scope-discipline rule 4); (c) not started | Group 2. Each one cost an owner wait or a rework round this session. |
| 7 | Improvement checklist C1 + C3: widen the JC am1 label grammar, and align `coordinator_lint.py` rule 6 with list-form `Files:`, in one amendment | JC | Not started. Amendment to SPEC-jarvis-coordinator (am1), Tier 2 | Group 2. Owner 2026-10-22: after friction items (a)–(c). |
| 8 | Improvement checklist D1: count check for the framework's own test suite | VT | Not started | Group 2. Owner 2026-10-22: after friction items (a)–(c). A silent under-run is a false green. |
| 9 | JC Increment 2 (R9–R10): scorecard for M1–M7, extending DA H-AC1 and the VT meter (was row 10) | JC | Not started | Group 2, last. Increment 1 cannot be judged without before-and-after numbers. Pulls DA H-AC1 forward out of the pilot trial row; no second instrument. |
| 10 | JC Increment 4 (R12–R13): one-command setup with a self-check, new user to first Jarvis session in ≤ 15 min; plain-language final report (was row 12) | JC | Not started | Group 3. "Convenient for other people" is part of the definition. Runs after row 5 (D1 decided by ba-sa: 1 → 2 → 3 → 4). It may start early only while row 5 is blocked on row 2. |
| 11 | Improvement checklist D4 (`coordinator_lint.py --help` crashes) and D7 (`bootstrap.sh` leftover report and substitution include `.claude/worktrees/`) | — | Review PASS (b1c588b) and QA PASS (075b500); fix 1a10f50 on branch worktree-agent-a998e45d25322f524, awaiting owner merge (Tier 0) | Group 3. Both trip a new user during setup. |
| 12 | Pilot trial: VT Part F and DA Part H (less H-AC1, moved to row 9), combined into one trial on the pilot project, with JC M1–M7 (was row 13) | VT + DA + JC | Not started | Group 3, last. Neither PRD is done until this trial passes. It exercises everything above. |

### Done

| Item | PRD | Status |
|---|---|---|
| VT Part J + J2: meter of active time per agent type and category, reported per size class (was row 1) | VT | Done (merged a724256, fd6efb2). Every "after" number is measured with this. |
| VT Parts I and H: fewer model turns; less rework (affected tests in spec, engineer self-check, rework causes) (was row 2) | VT | Done (merged). Rework is 23% of engineer runs. |
| VT Part B: handoff tier with machine-selected tests (was row 7) | VT | Done: review PASS and QA PASS at 184b3f4, merged. Tests are 37% of engineer active time. |
| VT Part D: merge gate (was row 8) | VT | Done: review PASS and QA PASS at 1ee6f19, merged. Findings outside the scope-discipline rule 5 threat model are parked, not rework. Replaces "verify-full before every handoff" for opted-in projects. Task-order merges (J-AC6) need it. |
| JC Increment 1 (R1–R8): every owner message goes to Jarvis by default; tier, brief format, decide/escalate split, end-of-task report and lessons-to-mechanisms stated in AGENTS.md; briefs without `Tier:` or `Files:` refused where the adapter intercepts (was row 9) | JC | Done: spec Approved plus am1 (Files: may be a list); review PASS (two runs) and QA PASS 15/15; merged 1057355. Attacked the correction spike (5 against 1; `scripts/correction_rate.py`) and the per-step reporting. |
| Improvement checklist B1: CI gate 3 skips `.claude/worktrees/` | — | Done: review PASS (round 3) and QA PASS; merged 41b2499. |

### Row 5: what task orders need (ACs from SPEC-delegated-autonomy)

- **J (active):** J-AC1 to J-AC7.
  - J-AC8 is parked, because it feeds the earned-autonomy score (C is parked).
  - Until C ships, an owner override of an order decision is recorded **only in that order's final report** (J-AC7). It narrows nothing. This is the parked part of R45 (J7).
  - J-AC6 (merge under an order) needs VT Part D (done). Coordinator friction (d), the one-page merge-ready summary with one owner command, is folded into J-AC6.
- **F (needed in full):**
  - F-AC1: work under autonomy happens on a branch or worktree.
  - F-AC2: every log entry carries a one-action reverse. J-AC7's final report needs this.
  - F-AC3 is already covered by B-AC3.
- **A (only these):**
  - A-AC3: the `approve-under` mechanism, exercised through `--order`.
  - A-AC4: checks (a), (b), (c), (f) and (g), applied to order stamps.
  - A-AC5: a stamp with no log entry fails.
  - A-AC6 (c): only the owner runs the owner scripts.
  - A-AC7: revocation, used by `revoke.sh <order key>`.
  - A-AC8: with no order or mandate present, every gate works exactly as it does today.
  - A-AC9: key revisions.
  - A-AC10: registry entry kinds.
- **G (only these):**
  - G-AC1, limited to the order wording: approvals trace to an order, which is exception (b) in §6.1.
  - G-AC2: the consistency check over the rule text being reworded.
- **C (dependency outside F/A/G, needs confirmation):**
  - C-AC1 and C-AC2 (the hash-chained decision log, with its tamper check) are needed by A-AC3, A-AC5, J-AC5 and J-AC7.
  - The rest of C stays parked.

## Parked — until the trial shows need (owner 2026-10-20)

| Item | PRD | Notes |
|---|---|---|
| VT Part E: test-suite hygiene (admission bar, retirement, red-main policy, named baseline) | VT | — |
| DA Part C: earned autonomy (override rate, widening, automatic narrowing) | DA | Exception: C-AC1 and C-AC2 (decision log) are pulled into Active row 5. While C is parked, R45 (J7) overrides go into the order's final report only. JC proposed order: 3rd, after absence mode (owner decision D3). |
| DA Part K: absence mode | DA | JC proposed order: 2nd after digest (JC "Later increments", owner decision D3). |
| DA Part D: daily digest | DA | JC proposed order: 1st to un-park, after Active row 5 (JC "Later increments", owner decision D3). |
| DA Part I: continuous self-evolution | DA | JC recommends it stays parked: it moves none of the four definition parts directly (owner decision D3). |
| DA Part E, second half (E-AC5, E-AC6): new tests must prove they catch bugs; depth matched to the task | DA | — |
| DA Part A, rest: A-AC1, A-AC2, A-AC4 (d) and (e), A-AC6 (a), (b) and (d) (the standing mandate itself) | DA | Task orders do not need a standing mandate. |
| DA Part G, rest: G-AC1 exceptions (a) mandate and (c) absence | DA | They follow when A or K is un-parked. |
| CI gate 3 (placeholder scan) also scans `.claude/worktrees/`, so `verify-full` in the main tree goes red while an increment worktree holds a test fixture that contains an upper-case placeholder | — | Done as improvement checklist B1, merged 41b2499. Found 2026-10-21 by ba-sa (JC am1). |
| `coordinator_lint.py` rule 6 still refuses a list-form `Files:` in `Slice:` briefs, so it disagrees with the spawn guard after JC am1 | JC | Found by ba-sa (JC am1). Scheduled: Active row 7 with C1 (owner 2026-10-22). |
| JC am1 label grammar (AM1-ADR-2) is letters and spaces only, so after an empty bulleted `- Files:` the items `- NO_SPEC_BUGFIX: …` or `- Verify-with: x` count as paths and the brief passes | JC | Found by QA 2026-10-21 (doc/qa/QA-jarvis-coordinator.md). Proposed fix: widen the label to `[A-Za-z][A-Za-z0-9_ -]*`, a one-line amendment plus tests. Scheduled: Active row 7 (owner 2026-10-22). |
| Pre-commit refuses a commit whose staged tree's newest `.verify` record is RED | — | Mechanism candidate for doc/memory/gate-exit-code-before-commit.md (coordinator piped verify-full into grep and committed e6b4daa on RED). Parked by the owner 2026-10-22 until a repeat incident (improvement checklist C2). |

**Not tracked here.** These follow-ups belong to the downstream project sessions (doc/memory/project-reds-belong-to-project-session.md): triage the pilot project's 30 red tests; render each PDF once; set the worker count; set up the runner and sharding; move structure-watching tests to lint; remove change-detector tests; split the layout model.

## Improvement checklist (owner request 2026-10-22)

The owner asked for an audit toward "make Jarvis the best framework" (verification honesty, speed and cost, workflow tiers, self-learning, security, benchmarks). Each point is mapped below. Evidence was measured on commit 018f11b. A is already covered and B1 is done. Owner ruling 2026-10-22 scheduled C1 + C3 (Active row 7) and D1 (Active row 8), started D4 and D7 as Tier 0 (Active row 11), and parked C2, D3 and D5. The rest of D stays parked under doc/memory/smallest-useful-scope-first.md, stay-on-the-definition.md and ease-of-use-over-strictness.md.

### A. Already covered

| Item | Evidence | Severity | Tier / governing spec | Status |
|---|---|---|---|---|
| A1. Workflow tiers (Quick / Standard / High-assurance) | Tiers 0 / 1 / 2 in AGENTS.md §5 | — | AGENTS.md §5 | Covered |
| A2. Fast / full / merge verification split | `verify-fast`, `verify-handoff`, `verify-merge` shipped | — | VT, Done table | Covered (Done) |
| A3. Time meter per agent | Active time per agent type and category | — | VT, Done table | Covered (Done) |
| A4. Scorecard, including false-green rate | Scorecard for M1–M7 planned. Proposed new metric: "false-green rate on a fixed failure-scenario set" | — | JC, Active row 9 | Covered by Active row 9; adding the metric is an owner decision |
| A5. Benchmark, before and after | Pilot trial with JC M1–M7 | — | VT + DA + JC, Active row 12 | Covered (Not started) |
| A6. Lessons become mechanisms | `mechanism:` line rule; `scripts/correction_rate.py` | — | AGENTS.md §9 | Covered |

### B. Fix now

| Item | Evidence | Severity | Tier / governing spec | Status |
|---|---|---|---|---|
| B1. CI gate 3 (placeholder scan) also scans `.claude/worktrees/` | A fixture in a worktree makes `tests/ci/test_ci_examples.py::test_gate_3_is_green_after_bootstrap_runs` fail: 1 failed, 21 passed. Clean tree: 22 passed. Moved here from the Parked table | Medium | Tier 0 (NO_SPEC_BUGFIX) | Done: review PASS (round 3) and QA PASS; fix 632c808 merged 41b2499 |

### C. Owner decisions (spec amendment or new mechanism, not bugs)

| Item | Evidence | Severity | Tier / governing spec | Status |
|---|---|---|---|---|
| C1. JC am1 label grammar lets a brief to a non-engineer role pass with no file list | Approved AM1-ADR-2 allows letters and spaces only. `Files:` followed by `- NO_SPEC_BUGFIX: repro`, `- Verify-with: x` or `- Verify_with: x` gives guard exit 0 for `reviewer` (ai-engineer is already blocked by rule A5). Fix: widen the label to `[A-Za-z][A-Za-z0-9_ -]*`, plus tests. Edge: `- Makefile: build rules` would then end the list | Medium | Tier 2 amendment to SPEC-jarvis-coordinator (am1) | Scheduled: Active row 7 (owner 2026-10-22: amend, after coordinator friction (a)–(c)) |
| C2. Pre-commit refuses a commit when the newest `.verify` record for the staged tree is RED | Mechanism for doc/memory/gate-exit-code-before-commit.md, which today says `mechanism: none` | Medium | New mechanism, no spec yet | Parked (owner 2026-10-22): until a repeat incident |
| C3. `coordinator_lint.py` rule 6 rejects a list-form `Files:` | Disagrees with the spawn guard after JC am1, so a valid brief is reported RED (false red) | Low | Governed by the coordinator_lint spec | Scheduled: Active row 7, same amendment as C1 (owner 2026-10-22) |

### D. Parked with evidence

| Item | Evidence | Severity | Tier / governing spec | Status |
|---|---|---|---|---|
| D1. The framework's own test suite has no count check | `verify-full` prints `counts: not configured — executed == collected NOT checked`; this repo has no `scripts/verify.conf`. A silent under-run of the framework's own suite is possible (mission: no false green) | High | VT Part A+C (Active row 1 area) | Scheduled: Active row 8 (owner 2026-10-22: after coordinator friction (a)–(c)) |
| D2. `verify-full` in this repo exits 0 while printing `EXIT GATE INCOMPLETE` | Lint, format and tests are `echo TODO:` by design in the template. Approved behaviour (SPEC-verify-tiers-merge-gate behaviour table). Risk: a CI that reads only the exit code | Low | SPEC-verify-tiers-merge-gate | Declared limit. No change proposed |
| D3. `verify-full` is slow on the framework itself | 3m56s wall time; the `hooks` step is 183s of it (1303 tests). Candidate: confirm the handoff tier's test selection covers the framework's own suite | Medium | VT Part B (Done table) | Parked (owner 2026-10-22) |
| D4. `python3 scripts/coordinator_lint.py --help` crashes | Prints a `FileNotFoundError` traceback instead of help | Low | Tier 0 | In progress (Tier 0); Active row 11 |
| D5. Areas not yet in any PRD | Security review (prompt injection through fetched or external content, tool permissions, secret scanning in commits, dependency pinning); adapter conformance tests per tool; timeout, budget and cancellation policy for agent runs; resuming interrupted tasks (part may land with row 11 task orders) | Unknown until assessed | None yet (would be Tier 2) | Parked (owner 2026-10-22) until the pilot trial (Active row 12) shows need |
| D6. Owner correction rate is not going down | `scripts/correction_rate.py`: 6 in the last 7 days against 0 in the previous 7 | High | JC, Active row 9 | Tracked by Active row 9 |
| D7. `scripts/bootstrap.sh` leftover report and placeholder substitution still include `.claude/worktrees/` | Found by review and QA of B1: bootstrap lines 14 and 56–58 lack the new exclusion, so its leftover list shows worktree files that CI gate 3 now skips, and substitution rewrites `<PROJECT>` inside agent worktrees. `test_gate_3_exclusions_match_bootstraps_own_leftover_check` still compares only the three older exclusions | Low | Tier 0 | In progress (Tier 0); Active row 11 |
| D8. Tests that run bootstrap touch the real `~/.jarvis/approvals/registry.jsonl` (mkdir and touch only) | Review and QA of D4+D7 (doc/qa/QA-bugfix-d4-d7.md) | Low | Tier 0 candidate | Parked |
| D9. `coordinator_lint.py` on a non-UTF-8 file: `UnicodeDecodeError` traceback, exit 1 (same as "violations") | Review and QA of D4 | Low | Tier 0 candidate | Parked |
| D10. `scripts/approve.sh --by a -- <slug> -h` passes the always-human guard: the read-only-flag search does not stop at `--` | Review and QA of DA B (doc/qa/QA-delegated-autonomy-B.md re-test 2); guard probe exit 0 | Medium | Owner decision: (a) declared limit or (b) one-line fix | Owner decision. Recommendation: (b) |
| D11. Declared-limit candidates from close-out reviews: open heredoc in verify.conf not caught by bash 3.2 `-n`; CRLF/BOM conf refused without naming the cause; `while true; do command sleep 1; done` passes R26; `SCRIPTS/APPROVE.SH` upper-case passes the guard | REVIEW-verify-tiers-AC.md, QA-verify-tiers-AC.md, REVIEW-verify-tiers-G-polling.md, QA-delegated-autonomy-B.md | Low | Declared limits | Parked |
