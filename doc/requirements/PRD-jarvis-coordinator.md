# PRD: Jarvis — the full coordinator

Status: Approved
Approval: prd-jarvis-coordinator-2026-10-20
Owner: pm
Upstream: owner request 2026-10-20 ("หลังจากนี้ให้ปรับ framework ตามนี้ ทุกสิ่งที่พี่พิมพ์จะเป็นการพิมพ์กับจาวิสเท่านั้นหลังจากนั้นให้จาวิสเป็นคนคุมต่อไม่ใช่ model เฉยๆ แต่จะต้องเป็นจาวิส"; then "เอาเป็นตัวเต็มร่างจริงของจาวิสอัจฉริยะเลยเพราะคือจุดขายของ framework เรา") · doc/memory/stay-on-the-definition.md · builds on doc/requirements/PRD-delegated-autonomy.md and doc/specs/SPEC-delegated-autonomy.md (both Approved)
Date: 2026-10-20

**Risk tier: 2.** This changes AGENTS.md §0 and §5–§6 (who coordinates, and how), the adapter wiring, and `doc/framework/ADAPTERS.md`.

**References.**
- **"Jarvis"** (จาร์วิส) is the coordinating assistant: the main thread that receives every owner message, as named in AGENTS.md §0.
- **"Owner"** is the human who owns the work. **"New user"** is anyone else who sets up the framework.
- **"Pilot project"** is the real downstream project built on this framework. Its name is kept out of the template.
- **"Primary adapter"** is the tool described in `doc/framework/ADAPTERS.md` section ก. **"Other adapters"** are the tools in section ข.
- Claim labels follow `doc/framework/COORDINATOR-CONSTITUTION.md`: **MEASURED** (run in this session, command given), **RELAYED** (taken from the brief or another report), **INFERRED** (reasoned, not proven).

## Problem

The owner wants every message they type to reach one named coordinator, Jarvis, which then runs the work: it classifies, briefs, checks and reports, so that the owner waits for the result. Today Jarvis is only a tone rule (AGENTS.md §0). The duties of a coordinator live in an optional skill (`.agents/skills/coordinator-discipline/SKILL.md`) that nothing loads by default or enforces. What answers the owner is therefore the bare model, and it behaves like one. On 2026-10-20 it let one merge-gate increment run three review rounds chasing deliberate forgeries, reported to the owner every few minutes, and made rulings that were the owner's to make, until the owner stepped in (RELAYED: coordinator brief, 2026-10-20). Owner corrections rose to 5 in the last 7 days, against 1 in the 7 days before (MEASURED: `python3 scripts/correction_rate.py --brief`, 2026-10-20; the brief said 4). Because Jarvis is the framework's selling point, it must also work for people other than the owner, who today follow a setup guide whose steps add up to about 27 minutes before their first message (RELAYED: the sum of SETUP.md's own estimates for §1–§4, 2+10+10+5 minutes; never timed with a real person).

## Goal & Success Metrics

**Goal.** Every owner message goes to Jarvis. Jarvis applies the coordinator duties every time, carries work through to one evidence-backed report, and escalates only what is the owner's to decide. A new user gets the same Jarvis with one command.

The four-part definition (doc/memory/stay-on-the-definition.md) is the scope filter. Each metric below moves one of: easy to use (E), correct (C), convenient for others (O), carries work through (W).

| # | Metric | Def. | Baseline | Target |
|---|---|---|---|---|
| M1 | **Owner interruptions per task**: Jarvis messages to the owner that are not (a) a gate stop required by AGENTS.md §5 for the task's tier, (b) an owner decision under R5, or (c) the one final report | W | To be measured retroactively from transcripts by the R10 instrument | Tier 0–1: 0 per task. Tier 2: 0 beyond the §5 gate stops and R5 decisions |
| M2 | **Owner-correction rate** (`scripts/correction_rate.py`) | C | MEASURED: 5 in the last 7 days, 1 in the 7 days before | ≤ 1 per 7 days within 4 weeks of Increment 1 shipping, and the script reports "down" or flat at ≤ 1 (pm proposal) |
| M3 | **Rounds per increment**: review and QA verdicts per increment slug, counted from `doc/qa/` | C, W | RELAYED: 3 review rounds for verify-tiers Part D on 2026-10-20. Median to be measured by R10 | Median ≤ 2 (one FAIL then PASS). A finding outside the scope-discipline rule 5 threat model never causes a round: 0 such rounds |
| M4 | **Time to first result**: owner message to Jarvis's first message carrying evidence (a run's output, or an artifact path) | W | To be measured by R10 | Reported as a median per tier. Guard only: must not rise after Increment 1. No target until 2 weeks of baseline exist |
| M5 | **New-user setup time**: from a fresh copy of the framework to a first session in which Jarvis answers a request and states its tier (R4) | E, O | RELAYED: ~27 min, the sum of SETUP.md's own estimates for §1–§4 (never timed with a real person) | ≤ 15 min, timed with one person who has not used the framework before (pm proposal) |
| M6 | **Dispatch completeness**: briefs to role agents that carry a `Tier:` line and a `Files:` line | C | Not tracked | 100% where the adapter can intercept (R6). Reported, not enforced, elsewhere |
| M7 | **Lessons without a mechanism** (`correction_rate.py`, second figure) | C | MEASURED: 0 | Stays 0 |

M1, M3 and M4 reuse the delegated-autonomy instrument R28 / H-AC1 and the verify-tiers meter. No second instrument is built (see R10).

## Requirements (must-have)

Requirements are grouped by increment. Each increment is usable on its own: when it ships, the owner gets a working improvement even if no later increment ever ships (owner ruling: "ทยอยทำจนครบ… แต่ให้ใช้งานได้จริงทุกตัว"). The **Displaces / defers** column applies scope-discipline rule 2.

### Increment 1 — every message goes through Jarvis, with the duties applied

The smallest slice that makes the owner's first sentence true.

| # | Requirement | Rationale | Displaces / defers |
|---|---|---|---|
| R1 | **Identity and entry.** In a fresh session of the primary adapter opened in the repo, with no flags typed, the first reply to any owner message comes from the Jarvis coordinator definition, not the bare model. A test proves that the repo's committed adapter settings name Jarvis as the default main-thread agent, and that the Jarvis definition exists and points to AGENTS.md for its rules. MEASURED: the primary adapter's CLI (2.1.304) lists an `--agent` flag that "overrides the 'agent' setting". INFERRED, to be proven by ba-sa before the spec is approved: (a) a main-thread agent can still dispatch role agents; (b) hooks and the CLAUDE.md → AGENTS.md pull still load in that mode; (c) the Jarvis definition does not also appear as a dispatchable role agent; (d) the default carries into non-interactive and remote-control sessions. Any of (a)–(c) failing blocks R1 as written and comes back to the owner. | "Every message goes to Jarvis" must be true by default, not by remembering a flag. | Displaces the bare model as the default responder. Defers (d) if unproven: the gap is listed in ADAPTERS.md instead of fixed. |
| R2 | **Rules live in AGENTS.md.** AGENTS.md §0 defines Jarvis as the coordinator (not only a voice) and states the duties of R3–R8 in tool-neutral words. The Jarvis definition file holds no rule of its own, only the pointer. `doc/framework/ADAPTERS.md` gets one row per adapter for "coordinator entry", saying how each tool reaches Jarvis and what is weaker (for other adapters: the rules are read from AGENTS.md, nothing is intercepted). `python3 scripts/check_neutrality.py` passes. | AGENTS.md §10: a rule that lives in one tool's file is invisible to the others. | Displaces the "optional" status of coordinator-discipline for the main thread: it becomes a stated duty. Does not rewrite that skill. |
| R3 | **Tier first.** Before dispatching anything for a new task, Jarvis states one line `Tier: <0|1|2> — <reason>`, choosing the higher tier when unsure (AGENTS.md §5). The line appears in Jarvis's first reply and in every brief it sends (R6). Jarvis then follows the §5 route for that tier in order, and at tier 2 ends its turn at each owner gate (§6.1). The existing engineer and QA spawn guards check the order where the adapter intercepts; nothing new is built for it. | Today's overreach started with no tier stated, so no route was fixed. | Defers automatic tier classification by a script: Jarvis classifies, the owner can override. |
| R4 | **Brief format.** Every brief Jarvis sends a role agent carries, on lines of their own: `Tier:`, `Files:` (the scope boundary, scope-discipline rule 3), `Verify with:` (the commands that decide done), and the threat-model sentence of scope-discipline rule 5 for reviewer and QA briefs. A rework brief starts with `REWORK:` (handoff-protocol). | Briefs that name their boundary and their check are what make "found is not done" possible to hold. | Defers checking brief content for truth; only presence is checked (R6). |
| R5 | **What Jarvis decides, and what goes to the owner.** AGENTS.md states the split as a table. **Jarvis decides alone:** the tier (upward only without asking); which role runs and the brief; ordering work inside an approved PRD or spec; whether a reviewer or QA finding is inside the rule 5 threat model, and parking it if not; rework dispatch inside the engineering loop's cap; parking out-of-criteria findings; turning a lesson into a mechanism (R8). **Only the owner decides:** every tier-2 approval gate (§6); any new or changed requirement, business rule or number; changes to the threat model, a memory ruling, or AGENTS.md §3; anything on the delegated-autonomy always-human list (DA Part B); a tier downgrade; a gate red after the loop's cap. Every escalation carries a recommendation and the reason (DA R16). | The bare model made the owner's rulings itself and asked about Jarvis's own. A written split makes both mistakes visible. | Defers decisions on the owner's behalf while the owner is away (DA Part K, parked). |
| R6 | **What is checked by machine, and what is self-report.** Where the adapter intercepts dispatch, a brief to a role agent with no `Tier:` line or no `Files:` line is refused with a message naming the missing line. The existing gates keep running unchanged: the engineer spawn needs an Approved spec; the QA spawn needs a PASS review by another run. The rest of R3–R8 is self-report, and each self-reported duty is listed as one LIMIT line in ADAPTERS.md. Per scope-discipline rule 5, the check catches a forgotten line, not a deliberately false one. | Promising enforcement the framework cannot deliver would itself be a fake green. | Defers any check that reads a brief's meaning. |
| R7 | **Report at task end, with evidence.** For tier 0–1, and between the gate stops of tier 2, Jarvis sends the owner nothing until the task ends, except an R5 owner decision. The end-of-task report is one message: what was done; the evidence (commands run and their results, red lines quoted whole); decisions made by Jarvis under R5; decisions the owner must make; `Parked:`. Scored by M1. | Reporting every few minutes is the measured complaint. | Displaces progress updates. Defers the daily digest (DA Part D, parked). |
| R8 | **Lessons become mechanisms.** When the owner corrects Jarvis, Jarvis records the lesson in `doc/memory/` within the same task, with a `mechanism:` line (AGENTS.md §9). M7 stays 0 and `python3 scripts/memory_lint.py` passes. | Already a rule; listed so the coordinator definition names it. | Nothing new built: reuses memory_lint and correction_rate. |

### Increment 2 — the scorecard: knowing whether Jarvis works

| # | Requirement | Rationale | Displaces / defers |
|---|---|---|---|
| R9 | One report-only command prints M1–M7 for a date window, per tier where the metric is per task. It never gates. Run over transcripts from before Increment 1, it gives the baseline; run after, the comparison. | Increment 1 cannot be judged without before-and-after numbers from the same instrument. | Displaces ad-hoc counting in reports. Defers per-agent breakdowns beyond what the VT meter already gives. |
| R10 | R9 extends the delegated-autonomy owner-message instrument (DA R28, H-AC1) and the verify-tiers meter. It does not add a second transcript reader. | One instrument, one set of limits. | Pulls DA H-AC1 forward out of the pilot-trial row; the rest of DA Part H stays in that row. |

### Increment 3 — carry-through: task orders

| # | Requirement | Rationale | Displaces / defers |
|---|---|---|---|
| R11 | Jarvis carries a task end to end through **task orders** exactly as approved in DA Part J (R39–R45) and SPEC-delegated-autonomy J-AC1–J-AC7, with the dependencies listed in backlog row "DA Part J". This PRD adds no requirement to task orders. Its only addition is the outcome that, under an order, R7's final report **is** the order's final report (J-AC7), so the owner reads one report, not two. | The owner's "Jarvis runs the work" is already designed and approved. Redesigning it would be scope creep. | Defers J-AC8 (scoring) with DA Part C, as already parked. |

### Increment 4 — for other people

| # | Requirement | Rationale | Displaces / defers |
|---|---|---|---|
| R12 | **One-command setup.** A new user runs one command (or follows a checklist of at most 5 steps) that names the project, turns on the repo hooks, makes Jarvis the default entry (R1), and ends by printing a self-check: each item PASS or FAIL with the fix for each FAIL. M5 ≤ 15 min, timed once with a first-time user before this increment is called done. | Convenience for other people is one of the four parts of the definition. | Displaces SETUP.md §1 and §4 as separate manual steps. Defers CI and branch-lock setup (SETUP.md §5), which stays a manual step. |
| R13 | **Plain-language report.** Jarvis's final report (R7) follows AGENTS.md §0: Thai, every file or function name followed at once by a plain explanation, and a "what you need to decide" section that a first-time user can answer without reading code. A report shape check confirms the sections are present (presence only). | A new user cannot act on a report written for the owner's memory. | Defers translations into other languages. |

### Later increments — parked autonomy features (owner decision D3)

These stay parked under the owner's re-cut of 2026-10-20 ("park until the trial shows need"; backlog "Parked"). They belong to "full Jarvis" because each one moves "carries work through". The recommended order if the owner un-parks them:

| Order | Feature (DA part) | Why in this place | Prerequisite |
|---|---|---|---|
| 5 | Daily digest (D) | Lets the owner read one summary per day across several orders, instead of one report each. Lowest risk: report only. | Increment 3, so there are orders to summarise |
| 6 | Absence mode (K) | The strongest form of "wait for the result", and the riskiest: decisions on the owner's behalf. Everything stays provisional. | Increments 3 and 5, so the owner can review provisional decisions on return |
| 7 | Earned autonomy (C) | Widens and narrows grants from the override rate. Needs weeks of order and absence data before its numbers mean anything. | Increments 2 and 6 |
| — | Self-evolution (I) | Recommended to **stay parked**. It moves none of the four definition parts directly. | — |

## Nice-to-have (explicitly deferred)

- Automatic tier classification by a script (R3 keeps it a stated judgement).
- A check that reads a brief's meaning, for example that `Files:` matches the task (R6 checks presence only).
- Push notifications when a task ends (ADAPTERS.md section ก lists the idea; unproven).
- Earned autonomy, absence mode, daily digest and self-evolution: see "Later increments".

## Out of Scope

- Any change to the task-order design, the always-human list, the mandate or the approval mechanism. These are approved in PRD-delegated-autonomy and SPEC-delegated-autonomy.
- Any change to the verify-tiers gates (merge gate, handoff tier, no-fake-green). They are referenced, not changed.
- Defending against deliberate fraud by an agent (scope-discipline rule 5).
- Interception for other adapters. They get the rules through AGENTS.md and an honest LIMIT line, nothing more.
- Naming the pilot project, or any real user or host, in framework files.

## Assumptions

- A1. **Path.** The brief named `doc/prd/PRD-jarvis-coordinator.md`. That folder does not exist; PRDs live in `doc/requirements/` (handoff-protocol, pm role). Written there.
- A2. **Status.** The brief asked for `Status: Draft`, and this file says Draft. The pm role and `scripts/approve.py` (`APPROVABLE_FROM = "In Review"`) require `In Review` before the owner can approve. The status must be flipped to `In Review` before `approve.sh` will accept it.
- A3. "Every message goes to Jarvis" means the default main-thread entry of the primary adapter. A user who deliberately starts the tool with another agent or flag is not prevented (scope-discipline rule 5; doc/memory/ease-of-use-over-strictness.md).
- A4. INFERRED: the transcripts kept by the primary adapter go back far enough for R9 to compute a baseline after Increment 1 ships. RELAYED: the verify-tiers meter read 884 transcript files on the owner's machine (ADAPTERS.md section ก, measured there 2026-10-20).
- A5. Tier-2 gate stops are not interruptions (M1 (a)): §6.1 requires them.
- A6. Targets marked "pm proposal" are proposals for the owner to confirm (D4).

## Open Questions

- D1. **Increment order.** Is 1 → 2 (scorecard) → 3 (task orders) → 4 (new users) right? The alternative is 4 before 3, because task orders cannot start until the verify-tiers merge gate (Part D) passes, while setup has no dependency.
- D2. **Increment 1 priority against in-flight work.** Should Increment 1 go ahead of DA Part J (task orders) in the backlog, as proposed? It is small and attacks this week's correction spike.
- D3. **Parked features.** Confirm the order digest → absence → earned autonomy, and confirm that self-evolution stays parked. Or name a different order.
- D4. **Targets.** Confirm M2 (≤ 1 correction per 7 days within 4 weeks) and M5 (≤ 15 minutes for a new user).
- D5. **The R5 split.** Is anything on the "Jarvis decides alone" list one the owner wants to keep? Is anything on the owner's list one the owner is happy to hand over?
- D6. **If R1 (a)–(c) fail** when ba-sa tests them: should Jarvis instead be loaded as standing instructions in the bare main thread, with the gap stated in ADAPTERS.md?

## Approval history

- **2026-10-20 — approved (human).** Registry key `prd-jarvis-coordinator-2026-10-20`, carried on the canonical `Approval:` line above.
- **2026-10-20 — drafted.** By pm, from the owner's two messages of 2026-10-20, doc/memory/stay-on-the-definition.md, the approved delegated-autonomy PRD and spec, and the commands quoted above. Awaiting the owner.
