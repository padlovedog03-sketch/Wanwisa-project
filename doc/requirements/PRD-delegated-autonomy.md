# PRD: Delegated autonomy — the assistant runs routine work under an owner-approved mandate

Status: Approved
Approval: prd-delegated-autonomy-2026-10-20
Owner: pm
Upstream: owner request 2026-10-20 ("ฉลาดเสมือนมนุษย์เก่งๆคนหนึ่งโดยที่จาวิสคือคนเก่งมากๆคนนั้นและถอดมนุษย์ออกให้อยู่ใน loop น้อยลงได้"; then, on the coordinator's proposal, "ได้ ให้จาวิสคุมงานแทนพี่เลย แต่ต้องเป็นจาวิสที่ฉลาดมากๆ"; addition "เมื่อแต่งตั้งให้จาวิสเป็นคนคุมแทนมนุษย์แล้วพี่อยากออกแบบให้พี่สามารถสั่งให้จาวิสพัฒนาตัวเองตามโลกสมัยใหม่เรื่อยๆได้ด้วย"; then "พี่อยากมอบอำนาจให้จาวิสมากกว่านี้หน่อย ในระดับที่ตัดสินใจแทนพี่ได้เลยเมื่อพี่ไม่อยู่", "อยากให้ทำงานที่พี่สั่งได้แบบ end to end เลยในกรณีที่พี่บอกว่าอนุญาติให้จาวิสคุมงาน", "เอาตามนี้ เพิ่มเข้า PRD เลย") · coordinator transcript measurement 2026-10-20 · depends on doc/requirements/PRD-verify-tiers-merge-gate.md (Parts J and H) · external research outside this repo: jarvis-research/
Date: 2026-10-20

**Risk tier: 2.** This changes the core rules in AGENTS.md §5–§6 (risk tiers and approval gates). It also touches the approval registry checks, the interception adapter, `doc/framework/ADAPTERS.md`, the agent definitions and the coordinator skill.

**References.**
- **"Pilot project"** (Thai: โปรเจกต์นำร่อง) means the real downstream project built on this framework. The baseline was measured there. Its real name is kept out of the template.
- **"The assistant"** means the coordinating assistant: the main thread, named จาร์วิส in AGENTS.md §0.
- **"Owner"** means the human who owns the work.

## Problem

The owner wants the assistant to run the work the way a very capable senior person would, so that the owner is pulled in less, while quality goes up rather than down.

Today the framework routes every decision through the owner:

- Every tier-2 feature needs 4 owner approvals.
- Over the last 21 days in the pilot project, the owner sent 2,411 messages to the assistant, about 115 a day.
- The owner answers quickly (median reply time 2 minutes). The cost is therefore the owner's attention, not waiting time.
- 23% of engineer runs are rework sent back by QA. Simply removing the owner from the loop would let those mistakes through unchecked.

What is missing is a way for the owner to approve, in advance and within limits, the classes of decisions the assistant may make alone. The assistant would then earn wider limits only through measured good judgement. Owner-only decisions would stay owner-only, mechanically. And the assistant would get right the first time more often, so that fewer decisions need the owner at all. Finally, the owner wants to be able to order the assistant to keep upgrading itself and the framework to current world practice, on demand or on a schedule, without that upgrade path becoming a way around these guards. And the owner wants two stronger forms of delegation: handing one task to the assistant end to end with a single order, and letting the assistant decide on the owner's behalf while the owner is away, provisionally and reversibly.

## Goal & Success Metrics

**Goal.** In a project that adopts a mandate, the owner leaves the loop for routine decisions. Every quality measure holds or improves. Autonomy is earned and can be narrowed. It is never granted unconditionally.

**How the metrics are measured.** Baselines come from the pilot project (coordinator transcript measurement 2026-10-20) unless marked "to be measured". Targets are judged in the real-use trial (R30), with the same instruments used before and after.

| # | Metric | Baseline | Target |
|---|---|---|---|
| N1 | Owner messages per feature | 2,411 messages in 21 days (~115/day). Per-feature figure to be measured with the R28 instrument | At least 50% fewer for features completed within the mandate (pm proposal) |
| N2 | Owner approvals per tier-2 feature | 4 | Features entirely within the mandate: 0 per-feature approvals; the owner reviews the digest instead. Features that touch the always-human list: unchanged, with one approval per always-human item |
| N3 | Override rate: share of mandate decisions the owner reverses or materially changes | n/a (new) | At most 5% over each rolling 14-day window (D1). Above 5%, the mandate narrows (R14) |
| N4 | Rework share: engineer runs that are QA rework | 23% | Must not rise. At most 15% (aligned with PRD-verify-tiers-merge-gate M11) |
| N5 | Escaped defects: defects found after an artifact reached Done or merge, traced to that artifact | To be measured over the 4 weeks before the mandate starts | Must not rise relative to that baseline |
| N6 | Owner-correction rate (`scripts/correction_rate.py`) | As reported over the 4 weeks before the mandate starts | Must not rise |
| N7 | Attempts on the always-human list, the never-grantable list (R41) or the never-while-absent list (R48) that reached execution without owner approval | n/a | 0. Every attempt is refused (where the adapter intercepts) or flagged (where it does not) |
| N12 | Task orders (J) completed end to end without an owner touch between the order and the final report | n/a | Reported per 4 weeks. pm proposes ≥ 60% of orders (A7) |
| N13 | Provisional decisions made in absence mode (K), confirmed vs reversed at the return review | n/a | Reported each return review. pm proposes ≤ 10% reversed (A7). Each reversal counts as an override (N3) |
| N14 | Stop-and-ask events per task order (J4) | n/a | Reported (median per order). No target: a stop-and-ask is correct behaviour, not a failure |
| N8 | Evolution cycles run, compared with cycles scheduled | n/a | 100% of scheduled cycles run, or each missed one is reported with its reason |
| N9 | Adopted evolution ideas that met their stated targets, compared with adopted ideas that missed them (measured after release) | n/a | At least 70% of adoptions meet their stated target (D6). Reported each cycle. Any adopted idea that missed its target is reviewed for rollback in the next cycle |
| N10 | Time from an idea entering the ledger to its adoption | n/a | Reported (median per cycle). No target until 3 cycles exist |
| N11 | Regressions in quality metrics (N4 rework share, N5 escaped defects, verify-tiers E suite health) after any framework release | n/a | 0. A regression triggers rollback consideration in the next digest |

**Quality guard.** Metrics N4, N5, N6 and N11 are guard metrics. If any of them rises over a 4-week window, the mandate narrows automatically (R14), whatever N1 to N3 show.

## Requirements (must-have)

Scope key:
- **T** = ships in the framework template. It must stay neutral and pass `scripts/check_neutrality.py`.
- **A** = declared per adapter in `doc/framework/ADAPTERS.md`.
- **P** = the project configures it.

### A. Delegated mandate

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R1 | A mandate is a document that starts from a framework template. The owner approves it through the normal approval registry, the same way as any other approval. It states:<br>• the decision classes the assistant may decide alone;<br>• the projects it applies to;<br>• budgets: at least a cap on the number of mandate decisions and a cap on spend;<br>• an expiry date;<br>• whether merging into the project's main branch is allowed (default: not allowed);<br>• the override threshold (N3) and the narrowing rule (R14). | T+P | The mandate *is* a human approval, scoped in advance. |
| R2 | Within an active mandate, the assistant may run the whole pipeline (pm → ba-sa → engineer → independent reviewer → qa) for work that falls entirely inside the mandate's decision classes, without stopping at each human gate.<br>**The first mandate** (D3) covers exactly:<br>• tier 0–1 work;<br>• test and infra changes;<br>• framework changes that do not alter business rules.<br>Its spend budget is zero and it expires 30 days after approval. It does not allow merging into main (D2). | T | This is the owner's request. D2, D3. |
| R3 | Each artifact the assistant approves under a mandate is recorded as "approved under mandate `<mandate key>`". The record is distinguishable from an owner approval both to a human reader and to `scripts/verify_approvals.py` and CI. The check fails when any of these is true:<br>• the mandate key does not exist;<br>• the mandate is expired or revoked;<br>• the artifact's decision class is outside the mandate;<br>• the mandate's budget is exhausted. | T | The mandate must be verifiable, not just claimed. |
| R4 | The assistant can never approve, extend, widen or renew its own mandate. It also cannot edit the mandate document, the always-human list (R7), or the code that enforces either. Any attempt is refused where the adapter intercepts, and caught at commit or CI where it does not. Each adapter declares which of these applies to it. Merging standing-mandate work into the project's main branch is refused under the first mandate and for its first 4 weeks in any case (D2). This rule covers the standing mandate only; task orders and absence mode merge only under R41 and R47. After 4 weeks, merging may only be added through a widening proposal (R13) that the owner approves. | T+A | Without this, the assistant could grant itself autonomy. D2. |
| R5 | The owner can revoke a mandate at any moment with one documented action. Revocation takes effect at the assistant's next gate: nothing new is approved under the mandate after revocation, and in-flight work stops at its next gate and waits for the owner. | T | A kill switch is the condition for trusting a mandate. |
| R6 | Adopting a mandate is opt-in per project. In a project with no active mandate (none, expired or revoked), every existing gate in AGENTS.md §5–§6 works exactly as it does today. A test shows this: with no mandate present, an attempt to proceed past a tier-2 gate is refused as it is today. | T | Same principle as verify-tiers D4. |

### B. Always-human list

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R7 | The framework defines an always-human list. These decisions stay with the owner whatever any standing mandate says (task orders and absence mode have their own, stated limits in R41 and R48; items (2), (4) beyond zero spend, and (5) can never be crossed by either):<br>(1) business rules and business numbers;<br>(2) security and personal data (AGENTS.md §8);<br>(3) irreversible or outward-facing actions: deleting data or history, deploying to production, pushing to a protected branch, sending anything outside the project;<br>(4) spending beyond the mandate's budget;<br>(5) changing the mandate, the always-human list, or their enforcement. | T | The owner's list. A standing mandate cannot override it. A task order (J) is a per-task owner approval and may grant only what R41 allows. |
| R8 | The always-human list is machine-checkable. Each item maps to something that can be detected: a decision class, a path pattern, a command pattern or an artifact field. A project can add items but cannot remove the framework's items. | T+P | "Checkable" is the owner's word. A list that can only be read as prose is not a guard. |
| R9 | Where an adapter can intercept, an attempt on the always-human list under a mandate is refused mechanically, and the refusal names the item. Where an adapter cannot intercept, the attempt is caught at commit or CI, and the adapter declares that weaker point in ADAPTERS.md. Each refusal must first be shown biting on a planted attempt for every item class. | T+A | AGENTS.md §9: lessons become mechanisms. A guard not broken on purpose is not a guard. |
| R10 | When the assistant is unsure whether a decision is on the always-human list, it treats the decision as always-human. | T | Mirrors AGENTS.md §5: "when unsure, pick the higher tier". |

### C. Earned autonomy

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R11 | Every decision the assistant makes on the owner's behalf is written to a decision log. Each entry records: date, project, decision class, mandate key, artifact, the options considered, the choice and why, and how to reverse it. The log is append-only and tamper-evident, at the same level as the approval registry. It holds names and counts only, never personal data values (AGENTS.md §8). | T | Override rate and narrowing cannot be computed without it. |
| R12 | The owner can mark any logged decision as overridden, and optionally as significant. The override rate (N3) is computed from the log over a rolling window, by a report-only script. | T | Measured judgement, not claimed judgement. |
| R13 | When the override rate stays at or below the mandate's threshold for the mandate's window (example: ≤ 5% for 4 weeks), the assistant may propose a wider mandate. The proposal includes the evidence. Only the owner approves it, through the registry. | T | Autonomy is earned, and the owner always approves widening. |
| R14 | The mandate narrows automatically when any of these happens:<br>• one significant override. Significant means the decision affected end users or data (D1);<br>• the override rate goes above 5% over a rolling 14-day window (D1);<br>• any quality guard metric (N4, N5, N6) rises over the window.<br>Narrowing removes the affected decision class, or suspends the mandate if the class cannot be identified. Narrowing is announced in the next digest and never needs the assistant's consent. | T | Quality comes first. Narrowing must never depend on the actor being narrowed. |

### D. Daily digest

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R15 | The assistant produces a daily digest in place of per-decision questions. It is delivered as a message at the start of each day's session, and a push notification is sent whenever something awaits the owner (D4). An adapter without notifications reports in the session only, and declares this in ADAPTERS.md. It has three sections:<br>(1) what was done;<br>(2) what was decided under the mandate, each item with its log entry and how to reverse it;<br>(3) what is waiting for the owner. It also shows the mandate's remaining budget, its expiry, and the current override rate. | T+A | It replaces about 115 messages a day with one read. D4. |
| R16 | When the assistant does ask the owner something, the question carries a recommended answer and the reason for it. A question without a recommendation counts as a defect in the digest. | T | A senior person brings an answer, not only a question. |
| R17 | Items waiting for the owner stay in the digest until they are answered. Work blocked on them does not proceed under the mandate. The only exception is absence mode (K): after its trigger, the assistant may proceed provisionally and reversibly (R47), and never with an `Approved` stamp. | T | Silence is not consent. Absence mode does not turn silence into approval; it turns it into a reversible, provisional step that the owner reviews (R50). |

### E. "Very smart" means right the first time

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R18 | **Closed learning loop.** On a regular schedule, a report groups QA rework causes (verify-tiers R31) and owner corrections (`correction_rate.py`) into recurring causes. For each recurring cause, the assistant proposes a mechanism: a gate, a test, a script or a skill change. Each proposal goes to the owner for approval, because changing the mechanism set is always-human item (5). | T | AGENTS.md §9: a lesson becomes a mechanism. |
| R19 | **Independent reviewer before QA.** Every change passes an independent review before QA. This applies to ALL work in every project that adopts this PRD's framework release, not only to mandate work (D5). It is an added step, not a changed approval gate, so R6 still holds for the approval gates. The reviewer is a different agent run from the author and starts from the files, not from the author's conversation. The author is never the grader. A review that finds defects returns the work to the author before QA. | T | Prior evidence: verification-subagent guidance; Meta ACH/TestGen-LLM. D5. |
| R20 | **Impact map.** Before the engineer starts, it receives the affected files and tests (verify-tiers R29), plus the tests a machine selects for the planned change (verify-tiers R7). | T | TDAD (arXiv 2603.17973): telling the agent which tests are affected reduced regressions from 6.08% to 1.82%. |
| R21 | **New tests prove they catch bugs.** A new test written under a mandate meets the verify-tiers admission bar (R18 there). It must also be shown to fail against at least one planted fault, mutation-style, on the lines it covers. | T | Meta ACH: mutant-killing tests. Agent-written tests are often shallow. |
| R22 | **Effort matched to the task.** The assistant states a depth level for each task: quick, standard or deep, chosen from risk tier, size class and novelty. It records the level in the decision log. A deep task always gets the independent review (R19) and a design step. | T | A senior person neither over-thinks a typo nor under-thinks an architecture change. |

### F. Reversibility by default

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R23 | All work under a mandate happens on a branch or in a worktree. Nothing under a mandate rewrites shared history, deletes data, deploys, or sends anything outside the project. Those actions are always-human item (3). | T | Every mandate decision can be undone. |
| R24 | Each digest item decided under a mandate states how to reverse it in one action, for example "revert commit X" or "delete branch Y". | T | Makes R15's "each item reversible" checkable. |

### G. Reconciling with AGENTS.md §5–§6

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R25 | AGENTS.md §6 is reworded so that "only a human can flip `Approved`" stays true. Every `Approved` status traces to a human approval in the registry. That approval is the owner approving this artifact, the owner approving a mandate that covers it in advance, or the owner issuing a task order that covers it (R39). A provisional decision made in absence mode (K) is not `Approved` and never carries an approval key until the owner confirms it (R50). An artifact approved under a mandate names that mandate's key (R3). This PRD does not weaken §6. It records that a scoped, advance human approval exists. | T | Owner constraint: say it explicitly. |
| R26 | AGENTS.md §6.1 ("no walking past the human in tier-2 work") gains these exceptions: (a) tier-2 work entirely within an active mandate's decision classes and off the always-human list; (b) work covered by an active task order, within its grants (R41); (c) provisional work in absence mode (R47), which never becomes `Approved` without the owner. All other tier-2 work keeps the current gates. AGENTS.md §5 states which tiers and classes a mandate may cover. | T | Keeps the existing rules true and complete. |
| R27 | After the change, every rule location that states the per-gate human approval is consistent with R25 and R26. Locations include AGENTS.md §5–§6, the handoff-protocol skill, the coordinator-discipline skill and the agent definitions. ba-sa lists the exact locations with grep, as in verify-tiers R14. | T | A rule that contradicts another rule is a rule nobody follows. |

### H. Measurement and proof in real use

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R28 | A report-only, stdlib-only instrument measures N1 (owner messages per feature) and N2 (owner approvals per feature) from transcripts and the registry. It extends or reuses the verify-tiers meter (Part J, R37–R38). It uses the same per-adapter reader and never gates. | T+A | Before and after numbers need the same instrument. |
| R29 | Escaped defects (N5) are recorded with a link to the artifact they escaped from, and whether that artifact was approved by the owner or under a mandate. | T | Shows whether mandate work leaks more defects than owner-approved work. |
| R30 | The change counts as done only after a trial on the pilot project. The trial runs a narrow first mandate (for example tier 0–1 and test or infra work only) for at least 4 weeks, measures N1–N7 before and after, and plants one attempt per always-human item class to show it is refused (R9). It also runs at least 2 task orders end to end (J) and at least one absence period (K), and plants one attempt per never-grantable and never-while-absent item to show it is refused. It is accepted only if every guard metric (N4–N6) holds and N7 is 0. | P (trial) | Real use, not a design claim. |

### I. Continuous self-evolution (owner area "G", 2026-10-20)

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R31 (G1) | **Trigger.** The owner starts an evolution cycle with a single short command (on demand). The cycle also runs on a monthly schedule by default (D6); the owner can change or turn off the schedule. Both start the same cycle. A scheduled cycle that does not run is reported in the next digest, with the reason. | T+A | Owner request. The scheduling mechanism is adapter-specific and declared in ADAPTERS.md. |
| R32 (G2) | **Horizon scan.** Each cycle researches current practice from primary sources: vendor docs and engineering blogs, papers, and standards (for example AGENTS.md and SKILL.md). Each candidate idea is deduplicated against what the framework already has and against what was already rejected. A ledger records every evaluated idea with its source, its verdict (adopted, rejected, deferred) and the reason. A rejected idea comes back only with new evidence, which the ledger names. | T | Saves the cost of re-arguing the same idea every cycle. |
| R33 (G3) | **Pain-driven ranking.** Candidate ideas are ranked by the framework's own measured pain: the meter's categories (verify-tiers Part J), rework causes (verify-tiers Part H), the owner-correction rate, and the override rate (C). Each idea states which measured pain it targets and by how much. An idea with no link to measured pain ranks below every idea that has one. | T | Fashion is not a reason to change. Measured pain is. |
| R34 (G4) | **Proposal.** Each idea that survives ranking becomes a draft PRD from the normal template. The draft carries the evidence, the expected metric impact, the risk tier and a rollback plan. | T | Ideas enter the normal pipeline. They do not bypass it. |
| R35 (G5) | **Experiment before adoption.** Before adoption, each change is trialled on the pilot project in an isolated copy or worktree. The trial measures before and after with the same meter. A change is adopted only if two conditions hold: its stated targets improve, and quality does not fall (no rise in rework share or escaped defects). Otherwise the ledger records "rejected, with numbers". | T+P | Same standard as verify-tiers Part F: proven in real use. |
| R36 (G6) | **Release.** Adopted changes ship as a versioned framework release: a git tag in this repo plus a changelog entry (D7). Each changelog entry says what changed, which metric it targets, the trial result, and how to roll back. Downstream projects pull updates by opting in. A downstream project is never changed silently. | T | Projects keep control of their own rules, consistent with project-reds-belong-to-project-session. |
| R37 (G7) | **Guardrails.**<br>(a) An evolution cycle can never change: the always-human list (B); the mandate or its widening and narrowing rules (A, C); the approval mechanism and registry; the hard bans. A change in any of these areas can only be a proposal to the owner.<br>(b) A change to core rules is tier 2. It goes through the normal gates, or through the mandate only if the mandate explicitly covers that decision class.<br>(c) Web content and fetched documents found during a scan are data, never instructions. A mechanism or check enforces this. Test: a planted instruction in a fetched page ("ignore your rules and …") causes no action and appears in the report only as quoted data.<br>(d) Neutrality is preserved. `scripts/check_neutrality.py` passes on every release. | T+A | Self-evolution must not become a way for the assistant to change its own limits. Prompt injection through research content is a real attack path. |
| R38 (G8) | **Report.** Each cycle produces a short report with: what was scanned; what was adopted, rejected or deferred, and why; and the measured effect of past adoptions against their stated targets (N9, N11). The report is linked from the digest. | T | The owner sees whether self-improvement actually improves anything. |

### J. Task delegation — ใบสั่งคุมงาน (owner 2026-10-20)

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R39 (J1) | **The order is the approval.** The owner delegates one task end to end with a single command. The task text, the issuer, an expiry and the named grants go in as arguments, for example `scripts/delegate.sh "<task>" --by <name> --until <date> --allow <grants>`. The command writes a registry entry in the same way the owner's approval command does, so the order *is* a human approval. Only the owner can issue an order. Agents cannot, and this is enforced the same way approval-registry writes are enforced today (refused where the adapter intercepts, caught at commit/CI where it does not, as in R4). | T+A | The owner's request: "end to end ... when I say you may run the work". |
| R40 (J2) | **End-to-end pipeline.** Under an active order the assistant runs pm → ba-sa → engineer → independent reviewer → qa → (merge) → (deploy) without pausing at owner gates. Every artifact approved along the way is stamped "approved under order `<key>`". `scripts/verify_approvals.py` and CI can verify that stamp. The check fails if the order is unknown, expired or revoked, or if the artifact falls outside the order's task or grants. | T | Same verifiability as the mandate stamp (R3). |
| R41 (J3) | **Grants.**<br>• **Default grants:** PRD, spec, code, tests and QA for the task, and business-rule decisions inside the task. Each business-rule decision is logged (R11) and listed in the final report.<br>• **Opt-in, granted by name only:** `merge` (requires a GREEN merge gate, verify-tiers R13); `deploy-dev`; `deploy-prod` (must be named explicitly and is never implied by any other grant).<br>• **Never grantable by any order:** deleting data or history; sending anything outside the project; spending; security and personal-data decisions (R7 item 2); changing the mandate, the order mechanism, the always-human list, the approval mechanism or the hard bans; widening the assistant's own powers.<br>A request for a never-grantable action is refused mechanically where the adapter can intercept (R9). | T+A | The owner chose these grants. The never-grantable list keeps R7's core. Security and personal data are on it because J3 does not grant them (A8). |
| R42 (J4) | **Stop and ask.** The assistant stops and asks the owner, with a recommendation (R16), when any of these is true:<br>• the work would go beyond the task as ordered;<br>• a never-grantable action is needed;<br>• a hard gate stays red after the engineering loop's iteration cap.<br>Work on the affected part does not continue until the owner answers. | T | A good delegate knows where the order ends. |
| R43 (J5) | **Gates still run.** An order removes only the waits for owner approval. It never removes or weakens tests, the no-fake-green checks (verify-tiers Part A), the independent reviewer (R19) or the hard bans. A test proves this: under an active order, a red gate still blocks the next step. | T | Speed comes from not waiting, not from skipping checks. |
| R44 (J6) | **Lifecycle.** Every order has an expiry and can be revoked with one owner command; revocation takes effect at the next gate, as in R5. Every order ends with exactly one final report covering: what was done; every decision made on the owner's behalf; the evidence (gate outputs); and how to reverse each item in one action (R24). | T | The order closes with something the owner can check in one read. |
| R45 (J7) | **Scoring.** Owner overrides on order outcomes are logged as overrides (R12) and feed the earned-autonomy score (C). A rate above the threshold, or a significant override (D1), narrows the grants that future orders may carry by default (R14). | T | Orders earn trust the same way the mandate does. |

### K. Absence mode — โหมดพี่ไม่อยู่ (owner 2026-10-20)

| # | Requirement | Scope | Rationale |
|---|---|---|---|
| R46 (K1) | **Trigger.** Absence mode starts in one of two ways:<br>• the owner declares absence with an end date;<br>• the owner has not replied for more than 4 hours to a question the assistant asked with a recommendation (R16).<br>The start, its trigger and the time are logged and shown in the digest. Absence mode ends when the owner returns (any owner message) or the declared end date passes. | T | The owner's request: decide on my behalf when I am not here. |
| R47 (K2) | **Powers while absent.**<br>• Tier-2 PRD, spec and feature decisions: the assistant decides and proceeds. Each decision is stamped "provisional".<br>• Business-rule decisions: the assistant chooses the safest reversible option and proceeds on a branch, stamped provisional. Work containing a provisional business-rule decision is never merged until the owner confirms it.<br>• Merge into main: allowed only when the merge gate is GREEN and the merged work contains no provisional items.<br>Provisional is mechanically distinguishable from `Approved` and never carries an approval key. | T | Progress continues, and everything stays reversible until the owner looks. |
| R48 (K3) | **Never while absent.** Deleting data, deploying to production, sending anything outside the project, spending, security and personal-data decisions, and widening the assistant's own powers. Requests for these are queued for the owner and refused mechanically where the adapter can intercept (R9). | T+A | These cannot be undone, so they wait. |
| R49 | **Order and absence together.** If absence mode starts while a task order is active, the order's grants still apply to that task, except that `deploy-prod` waits for the owner's return. Everything outside the order follows K. | T | This removes the ambiguity when the two overlap. Production deploys never happen unattended. (pm proposal, A9.) |
| R50 (K4) | **Return review.** When the owner returns, the assistant presents one list of every decision it made on the owner's behalf during the absence. The owner can confirm or reverse each item, singly or in bulk. Confirmed items become eligible to merge. Reversed items are undone using their recorded reversal (R24) and count as overrides (R12, N13). | T | One read to catch up, and every decision is still reversible. |

## Nice-to-have (explicitly deferred)

- Different mandates for different projects running at the same time, with a combined digest.
- A digest delivered through a push channel instead of a file or message.
- An automated suggestion of the next widening, ranked by evidence.
- Splitting large tasks automatically (see verify-tiers A10).

## Out of Scope

- **Removing the owner from always-human decisions** (R7), under any mandate.
- **Owner reply latency.** The median is 2 min, so it is not the bottleneck.
- **Changing the model, the provider or the model's settings** to raise "smartness".
- **The design of the mandate format, decision log, digest, reviewer agent or guards.** That is ba-sa's job.
- **Fixing red tests in any downstream project.** That belongs to that project's own session (doc/memory/project-reds-belong-to-project-session.md).
- **Anything the verify-tiers PRD already delivers.** This PRD depends on it and does not restate it: the meter (Part J), rework causes (Part H) and the test admission bar (Part E).

## Dependencies

- **PRD-verify-tiers-merge-gate Part J** (meter, R37–R38, R41). N1, N2 and the time metrics need its transcript reader. R28 builds on it.
- **PRD-verify-tiers-merge-gate Part H** (rework causes, R29–R32). N4 and the learning loop (R18) need classified rework causes. The impact map (R20) needs R29 there.
- **PRD-verify-tiers-merge-gate R7 and R18** (machine-selected tests and the admission bar) are used by R20 and R21.
- **Section I (self-evolution)** depends on the meter (Part J), rework causes (Part H), the decision log and override rate (C here), and the trial standard (R30 here). Its R35 trials use the same isolated-worktree method.

Until those parts ship, this PRD's metrics cannot be measured, so the trial (R30) cannot start.

## Assumptions

- A1. "Feature" for N1 and N2 means one PRD or one tier-0/1 task, traced through to Done.
- A2. "Override" means the owner reverses or materially changes a mandate decision within 14 days of the digest that reported it. The rolling 14-day window matches D1.
- A3. N1 −50% and N4 ≤ 15% are pm proposals. N3 ≤ 5% over 14 days is decided (D1). The owner sets the binding values in each mandate.
- A4. The first mandate is fixed by D3: tier 0–1 work, test/infra changes, and framework changes that do not alter business rules; zero spend; 30-day expiry. It widens only through R13.
- A5. Merging into a project's shared main branch counts as outward-facing (always-human item 3). No mandate merges into main during the first 4 weeks (D2). After that, merging can only be proposed as a widening (R13), approved by the owner, and would still require a GREEN merge gate (verify-tiers R13).
- A7. The N12 (≥ 60%) and N13 (≤ 10% reversed) targets are pm proposals.
- A8. Task orders cannot grant security or personal-data decisions. The owner's grant list (J3) does not mention them, and R7 item (2) keeps them with the owner. See Q8.
- A9. R49 (order plus absence: `deploy-prod` waits for the owner) is a pm proposal that fills a gap between J and K. See Q9.
- A6. The baseline figures come from the coordinator transcript measurement 2026-10-20. pm read them but did not re-measure them.

## Decisions

The owner accepted all of the coordinator's recommendations for Q1–Q7 on 2026-10-20 ("ใช้คำแนะนำทั้งหมด"). These are owner decisions, but they do not approve this PRD: it stays In Review until the owner approves it through the registry.

- **D1 (Q1).** Decided (owner, 2026-10-20). The mandate narrows when either the override rate is above 5% over a rolling 14-day window, or there is one significant override. Significant means the decision affected end users or data. → N3, R14, A2
- **D2 (Q2).** Decided (owner, 2026-10-20). Applies to the standing mandate (A) only; task orders (J, R41) and absence mode (K, R47) have their own merge rules. No mandate merges into main during the first 4 weeks. After that, merging may only be proposed as a widening (C), and the owner approves it. → R1, R2, R4, A5
- **D3 (Q3).** Decided (owner, 2026-10-20). The first mandate covers tier 0–1 work, test/infra changes, and framework changes that do not alter business rules. Spend budget: zero. Expiry: 30 days. → R2, A4
- **D4 (Q4).** Decided (owner, 2026-10-20). The digest is a message at the start of each day's session, plus a push notification whenever something awaits the owner. An adapter without notifications reports in the session only and declares this in ADAPTERS.md. → R15
- **D5 (Q5).** Decided (owner, 2026-10-20). The independent reviewer applies to ALL work, not just mandate work. → R19
- **D6 (Q6).** Decided (owner, 2026-10-20). The evolution cycle runs monthly. N9 target: at least 70% of adoptions meet their target. → R31, N9
- **D7 (Q7).** Decided (owner, 2026-10-20). Releases are git tags plus a changelog. → R36

## Open Questions

Q1–Q7 are closed by D1–D7. Two new questions from areas J and K:

- **Q8.** Should a task order ever be able to grant security or personal-data decisions, for example as a named opt-in grant like `deploy-prod`? pm assumes it cannot (A8).
- **Q9.** If absence mode starts during an order that holds the `deploy-prod` grant, should the production deploy wait for the owner (pm's proposal, R49), or proceed as the order allows?

## Approval history

- **2026-10-20 — approved (human).** Registry key `prd-delegated-autonomy-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** pm, from the owner's two requests of 2026-10-20 and the coordinator transcript measurement 2026-10-20. It depends on PRD-verify-tiers-merge-gate Parts J and H.
- **2026-10-20 — added section I (continuous self-evolution).** pm, from the owner's addition "เมื่อแต่งตั้งให้จาวิสเป็นคนคุมแทนมนุษย์แล้ว…พัฒนาตัวเองตามโลกสมัยใหม่เรื่อยๆได้ด้วย". The owner's area G maps to R31–R38 (G1–G8); it is labelled I because G and H were already in use. Added metrics N8–N11. Status stays In Review.
- **2026-10-20 — revised.** pm recorded the owner's decisions D1–D7 ("ใช้คำแนะนำทั้งหมด"), closed Q1–Q7, and updated N3, N9, R1, R2, R4, R14, R15, R19, R31, R36, A2–A5. Status stays In Review.
- **2026-10-20 — added sections J (task delegation) and K (absence mode).** pm, from the owner's requests "พี่อยากมอบอำนาจให้จาวิสมากกว่านี้หน่อย…" and "อยากให้ทำงานที่พี่สั่งได้แบบ end to end…", then "เอาตามนี้ เพิ่มเข้า PRD เลย". Added R39–R50 and metrics N12–N14, and reconciled R4, R7, R17, R25, R26, R30 and D2 so that the D2 merge rule covers the standing mandate only. Status stays In Review.
