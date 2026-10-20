# Backlog

Status: Living
Owner: pm
Upstream: doc/requirements/

Ordered by priority. Each row is one deliverable and links to its PRD. Rows 1–9 belong to one PRD and share one approval. Each part is specced and shipped in the order below.

| Priority | Item | PRD | Tier | Status | Why this priority |
|---|---|---|---|---|---|
| 1 | Part J — measurement as a mechanism: a neutral, stdlib-only meter of active time per agent type and category, with a rework report (R37–R40, R32) | [PRD-verify-tiers-merge-gate](../requirements/PRD-verify-tiers-merge-gate.md) | 2 | PRD Approved | Every "after" number depends on it. The headline target (per-size medians: Small ≤ 15, Medium ≤ 25, Large ≤ 50 min) can only be checked with the same instrument used for the baseline. It is cheap and reports only, so it carries little risk. |
| 2 | Part A+C — the no-fake-green guarantee and a measurable `verify-full` (R1–R6, R10–R12) | same | 2 | PRD Approved | The handoff tier and the merge gate rest on this. It supplies "ran N of M", the executed == collected check and the run record. |
| 3 | Part G — no hand-written polling: an adapter guard plus per-adapter declarations (R26–R28) | same | 2 | PRD Approved | Small, self-contained, and it pays off at once: 2.4 min per engineer run in hand-written loops, plus 5.4 min in other waits. AGENTS.md §9 requires the lesson to become a mechanism. |
| 4 | Part B — opt-in handoff tier that the machine selects, with a forced full run when undeclared or untracked inputs change (R7–R9) | same | 2 | PRD Approved | Biggest cut to test time, which is 37% of engineer active time. It must not ship before Part A+C. |
| 5 | Part H — less rework: affected tests/files listed in the spec, engineer self-check per acceptance criterion, QA rework classified by cause (R29–R31) | same | 2 | PRD Approved | 23% of engineer runs are QA rework. The self-check uses the Part B handoff tier, so this comes after it. |
| 6 | Part D — merge gate: one machine full run per merge on the final tree, QA grading on its own tree, rule rewording at every R14 location, runner plus local fallback (R13–R17) | same | 2 | PRD Approved | Replaces "verify-full before every handoff" for opted-in projects. It needs the Part A+C record and the Part B tier first. |
| 7 | Part I — fewer model turns: exact briefs, batched reads, no re-reading large files (R33–R36) | same | 2 | PRD Approved | Model generation is 39–80% of active time, but the saving is unproven. It ranks below the parts that have measured payoffs. The trial may show no gain. |
| 8 | Part E — suite hygiene: admission bar, retirement review, red-main policy, named baseline failures (R18–R21) | same | 2 | PRD Approved | Controls suite growth, but speed does not depend on it. R21 must be in place before the trial so a planted regression can be told apart from the known reds. |
| 9 | Part F — real-project trial on the pilot project in a separate worktree, with before/after numbers M1–M14 (R22–R25) | same | 2 | PRD Approved | Per the owner's 2026-10-20 ruling, the work is not done until this passes. It runs last because it exercises every other part. |
| 10 | Delegated autonomy: an owner-approved mandate, an always-human list, earned autonomy, a daily digest, right-the-first-time, reversibility, continuous self-evolution, task orders and absence mode (R1–R50) | [PRD-delegated-autonomy](../requirements/PRD-delegated-autonomy.md) | 2 | PRD In Review | High value: about 115 owner messages a day, and 4 owner approvals per tier-2 feature. It still comes after verify-tiers because its metrics need Part J (the meter) and Part H (rework causes), and it cannot start its trial until those ship. Within this PRD, ship in this order: always-human list and guards (B), then reversibility (F), then mandate and registry (A), then §5–§6 rewording (G), then the decision log and narrowing (C), then the digest (D), then right-the-first-time (E), then the trial (H), then task orders (J) and absence mode (K), then self-evolution (I), which needs the decision log, the override rate and a working trial method. Guards come before any freedom. |

**Not tracked here.** These follow-ups belong to the downstream project sessions (doc/memory/project-reds-belong-to-project-session.md):
- triage the pilot project's 30 red tests
- render each PDF once
- set the worker count
- set up the runner and sharding
- move structure-watching tests to lint
- remove change-detector tests
- split the layout model
