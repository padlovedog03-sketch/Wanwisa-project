# SPEC: Delegated autonomy — mandate, always-human list, task orders, absence mode, self-evolution

Status: Approved
Approval: spec-delegated-autonomy-2026-10-20
Owner: ba-sa
Upstream: doc/requirements/PRD-delegated-autonomy.md (approved by the owner 2026-10-20, registry key `prd-delegated-autonomy-2026-10-20`; the owner accepted assumptions A8 and A9)
Date: 2026-10-20

Design: [`doc/architecture/DESIGN-delegated-autonomy.md`](../architecture/DESIGN-delegated-autonomy.md). It holds the interfaces, data shapes and ADR-1 … ADR-16.

## Overview

When this ships, a project can opt in to three ways for the assistant to proceed without stopping at every owner gate. In all three, the owner's power is exercised through owner-only commands, and every result is checked by machine.

- **Standing mandate.** The owner approves it in advance, it is scoped by decision class, and it can be narrowed. The assistant may approve artifacts that fall inside it.
- **Task order.** The owner gives one order for one task, and it covers that task from start to finish.
- **Absence mode.** While the owner is away, the assistant makes provisional, reversible decisions. They become approved only when the owner confirms them.

Three things never change under any of them:
- The always-human list cannot be crossed by any of the three.
- The assistant can never create, widen or renew its own authority.
- Every `Approved` stamp still traces to a human entry in the approval registry.

Around this core, the work adds:
- a decision log, append-only and hash-chained, which the override rate is computed from;
- automatic narrowing, derived from owner overrides, so it never needs the assistant's cooperation;
- a daily digest;
- an independent reviewer before QA, for **all** work (D5);
- the right-first-time aids;
- an owner-triggered self-evolution cycle that cannot touch its own limits.

## How to read this spec

- **Markers.** These work as in `SPEC-verify-tiers-merge-gate.md`:
  - `[MEASURED: <command>]` means I ran it on 2026-10-20.
  - `[INFERRED]` means I read it but did not run it. The engineer checks every `[INFERRED]` before building on it.
  - `[RELAYED: PRD]` means the figure comes from the PRD.
- **Line numbers** come from the working tree on 2026-10-20. Re-grep before editing.
- **IDs.** Each AC ID is prefixed with its increment letter (`B-`, `F-`, `A-`, `G-`, `C-`, `J-`, `K-`, `D-`, `E-`, `H-`, `I-`). **RED-FIRST** means the engineer pastes the red run (failing line verbatim), the green run after the fix, and a `grep -c` showing zero residue.
- **"Autonomy is active"** means at least one of these holds:
  - an approved mandate that has not expired, been revoked or been suspended;
  - an approved order that has not expired or been revoked;
  - an absence period that has started and not ended.

  `python3 scripts/autonomy.py status` prints which one, or `inactive`. Several guards apply only while autonomy is active (ADR-6).
- **Opt-in (R6).** A project opts in by creating `scripts/autonomy.json`. With no such file and no mandate, order or absence entries, every existing gate behaves as it does today. **R19, the independent reviewer, is the one exception: it applies to all work, by D5.**

## Increments (the shipping order given in the brief: guards first)

| # | Increment | Requirements | Needs | Changes agent behaviour? |
|---|---|---|---|---|
| 1 | **B** always-human list | R7–R10 | — | The owner-script rule applies to **every** project (agents can no longer run the owner's approval commands). The rest only while autonomy is active. |
| 2 | **F** reversibility | R23, R24 | 1 | Only while autonomy is active |
| 3 | **A** mandate | R1–R6 | 1, 2 | Opt-in |
| 4 | **G** §5–6 reconcile | R25–R27 | 3 | Rule text everywhere. Behaviour only when opted in. |
| 5 | **C** earned autonomy | R11–R14 | 3. verify-tiers **H** for the N4 trigger | Opt-in |
| 6 | **J** task orders | R39–R45 | 3, 5. verify-tiers **D** for the `merge` grant | Opt-in (an order exists only if the owner issues one) |
| 7 | **K** absence mode | R46–R50 | 5, 6 | Opt-in |
| 8 | **D** digest | R15–R17 | 5, 7 | Opt-in |
| 9 | **E** right first time | R18–R22 | verify-tiers **H** (R29–R31), **B** (R7) and **E** (R18) | **R19 applies to all work, not opt-in (D5).** R18 and R20–R22 are opt-in. |
| 10 | **H** measurement and trial | R28–R30 | verify-tiers **J** (implemented, not yet committed) plus all of the above | Report only, plus the trial |
| 11 | **I** self-evolution | R31–R38 | 5, 8, 10. verify-tiers J and H | Opt-in |

### Dependency status on 2026-10-20

**verify-tiers J (the meter) is implemented but not yet committed.** `git status` shows `scripts/agent_time.py`, `.claude/meter/` and `tests/framework/test_agent_time.py` as untracked `[MEASURED]`.

**verify-tiers H (rework causes) has not shipped.** `grep -c 'Rework cause' doc/templates/qa-report.md` gives 0 `[MEASURED]`. Until it ships:
- **N4 trigger.** The rework-share narrowing trigger in R14 cannot be computed. `validate-mandate` therefore **refuses to activate a mandate**, fail-closed (C-AC6, ADR-12), and prints the reason.
- **R18.** The learning loop prints `unavailable: rework causes not shipped`.
- **R20.** The impact map's affected-tests part is unavailable.

**verify-tiers D (the merge gate) has not shipped** `[MEASURED: ls scripts/verify-merge.sh → no such file]`. Until it ships:
- `delegate.sh` refuses the `merge` grant (J-AC2).
- Absence-mode merges are refused (K-AC3).

**R30 (the trial)** cannot start until all three have shipped. That matches the PRD's Dependencies section.

## Acceptance Criteria

Test-file convention:
- **Adapter ก guards** are tested in `tests/hooks/` (a gate step today).
- **Core scripts and documents** are tested in `tests/framework/`.
- **Coordinator linters** are tested in `tests/coordinator/`.

Every test that writes a registry uses a temporary `APPROVAL_LOG`, never the real file. Every test that needs a git repo builds one in `tmp_path`.

### Increment 1 — B: the always-human list (R7–R10)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| B-AC1 | R7, R8 **RED-FIRST** | `python3 scripts/autonomy.py items` prints the five framework items (`AH1` business rules, `AH2` security/personal data, `AH3` irreversible/outward, `AH4` spend, `AH5` mandate/list/enforcement). Each lists at least one matcher of each kind it uses: decision class, path pattern, command pattern or artifact field. Given `scripts/autonomy.json` adds a path pattern to AH1, Then that pattern appears under AH1. Given the project file tries to remove or narrow a framework item (a `disable` key, a redefined item ID, or an empty override of a framework list), Then loading fails with exit 2 and `cannot remove framework item AH<n>`. That is the planted case. | tests/framework/test_autonomy_items.py |
| B-AC2 | R8 | `autonomy.classify_command(cmd)` returns the item IDs for each case in the design's command table (§B.2). It returns `[]` for each allow case: `grep -rn 'git push origin main' doc/`, `git push origin feature/x`, `curl -s https://example.test/x` (a GET), a heredoc that only mentions a banned command, and `python3 -m pytest`. | tests/framework/test_autonomy_items.py |
| B-AC3 | R9 **RED-FIRST** | Given a fixture with an active mandate, For one planted attempt per item class, When `guard_bash.py` receives it, Then it exits 2, and stderr names `always-human item AH<n>` and the matched pattern. The attempts are:<br>• AH3: `git push origin main`, `curl -X POST https://example.test`, `rm -rf data/` (with `data/**` declared as data), `git push origin --delete feature/x`<br>• AH3 deploy: a configured project deploy pattern<br>• AH4: a configured project spend pattern<br>• AH5: `bash scripts/autonomy.py grant …`, or a redirect into `scripts/autonomy.json`<br>Each one is shown red against today's guard, which exits 0. | tests/hooks/test_guard_always_human.py |
| B-AC4 | R4, R9, R39 **RED-FIRST** | **Owner-script rule. This applies in every project, whether autonomy is active or not.** For each of these invocations, `guard_bash.py` exits 2 with `owner-only command`:<br>• `scripts/approve.sh x --by a`<br>• `./scripts/approve.sh x`<br>• `bash scripts/approve.sh x`<br>• `python3 scripts/approve.py x`<br>• `scripts/delegate.sh "t" --by a`<br>• `scripts/revoke.sh k`<br>• `scripts/override.sh d`<br>• `scripts/away.sh --until d`<br>• `scripts/evolve.sh`<br>• `echo '{…}' >> ~/.jarvis/approvals/registry.jsonl`<br>• `tee -a "$APPROVAL_LOG"`<br>The command `scripts/approve.sh --list` stays allowed, because it writes nothing. This closes today's gap: the registry guard watches only Write/Edit/MultiEdit/NotebookEdit `[MEASURED: .claude/hooks/guard_approval_registry.py _WRITE_TOOLS; settings.json matcher "Write\|Edit\|MultiEdit\|NotebookEdit"]`, so an agent's Bash `approve.sh` is not intercepted today `[MEASURED: grep -n approve .claude/hooks/guard_bash.py → no match]`. | tests/hooks/test_guard_always_human.py |
| B-AC5 | R4, R9 | **Release precondition for B-AC4.** The owner's own `!scripts/approve.sh --list` (the shell-prefix path SETUP.md documents) must not be intercepted by PreToolUse hooks. Until a headless or manual run proves it, this is `[INFERRED]`. The proof is pasted into the B handoff: run the owner command once with the new rule in place, and show it is not blocked. If it **is** blocked, B-AC4 ships disabled and the owner decides (open question 1). | B handoff evidence |
| B-AC6 | R9 **RED-FIRST** | Given autonomy is active, When a Write/Edit/MultiEdit/NotebookEdit targets a protected path (design §B.3: `scripts/autonomy.json`, `doc/mandates/**`, `doc/orders/**`, `doc/decisions/**`, `scripts/autonomy.py`, `scripts/approve.py`, `scripts/verify_approvals.py`, the owner scripts, `.claude/hooks/**`, `.claude/settings.json`, `.githooks/**`, `ci-examples/**`), Then the new `guard_autonomy_paths.py` exits 2 naming AH5. Given autonomy is **not** active, Then the same edit is allowed (R6, ADR-6). | tests/hooks/test_guard_autonomy_paths.py |
| B-AC7 | R9 (adapter ข) **RED-FIRST** | Given autonomy is active, and a commit stages a protected path with no `Owner-Approved: <key>` trailer that resolves to an owner registry entry, When `.githooks/pre-commit` runs, Then it refuses and names AH5 and the path. With the trailer present, it passes. | tests/framework/test_pre_commit.py (new cases) |
| B-AC8 | R10 **RED-FIRST** | Given a PRD or spec with no `Decision-class:` header line while autonomy is active, Then `autonomy.classify_artifact` returns `AH-UNSURE`, which is treated as always-human. Given a changed path that matches no class glob, Then the same. Given a `Decision-class:` line that declares `touches: none` while the changed paths match an AH1/AH2 project glob, Then the path match wins, because a field can add an always-human touch but never remove one. | tests/framework/test_autonomy_items.py |
| B-AC9 | R9 | `doc/framework/ADAPTERS.md` gives each adapter a row per point of enforcement: commands, paths and spawn. Adapter ก is enforced (it intercepts). Adapter ข is weaker: it catches at commit and CI only, and cannot stop commands. | tests/framework/test_doc_contracts.py |

### Increment 2 — F: reversibility by default (R23, R24)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| F-AC1 | R23 **RED-FIRST** | Given autonomy is active and the current branch is protected (`main`, `master`, or the project list in `scripts/autonomy.json`), When the agent runs `git commit …`, or `autonomy.py approve-under …`, Then it is refused: `work under autonomy happens on a branch or worktree`. On `feature/x` it is allowed. | tests/hooks/test_guard_always_human.py, tests/framework/test_autonomy_approve.py |
| F-AC2 | R24 **RED-FIRST** | `autonomy.py log` refuses, with exit 2 and `reverse: missing or not one action`, any entry of kind `approval`, `decision`, `provisional` or `merge` whose `reverse` field does not match the one-action grammar. The grammar is `revert <sha>`, `delete branch <name>`, `restore <path> from <sha>`, `remove stamp <path>`, or `none: <reason>` for decisions that have no effect yet. | tests/framework/test_decision_log.py |
| F-AC3 | R23 | Rewriting history, deleting data, deploying and sending outward under autonomy are refused as AH3. B-AC3 covers this; nothing new here. | — |

### Increment 3 — A: the mandate (R1–R6)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| A-AC1 | R1, R2 | `doc/templates/mandate.md` exists. Its `## Terms` block is JSON with these fields: `classes`, `projects`, `max_decisions`, `max_spend`, `expires`, `merge_allowed` (default `false`), `override_threshold`, `override_window_days` and `narrowing`. `autonomy.py validate-mandate <file>` rejects each of these, naming the field:<br>• a missing field;<br>• `merge_allowed: true` while the mandate is less than 28 days old (D2);<br>• a class outside the vocabulary;<br>• a class that is always-human.<br>The shipped example `doc/templates/mandate.md` encodes D3 exactly: classes `tier-0`, `tier-1`, `test-infra`, `framework-non-business`; spend 0; 30 days; no merge. | tests/framework/test_autonomy_mandate.py |
| A-AC2 | R1, R3 | Given an owner runs `scripts/approve.sh mandate-<project>-first --by o` (exact-stem match, ADR-5), Then the registry gains one entry carrying all five required fields, plus `kind: "mandate"`, `expires` and `terms_sha256`. `verify_approvals.py` passes. | tests/hooks/test_approve_script.py (new cases) |
| A-AC3 | R2, R3 | Given an active mandate and an in-class artifact (`Decision-class: test-infra; touches: none`, changed paths under `tests/**`), When `autonomy.py approve-under <doc> --mandate <key>` runs, Then:<br>• the document's status line flips to Approved;<br>• it gains an approval key line and an `Approved-under: mandate <key>` line;<br>• its `## Approval history` gains `approved under mandate <key> (assistant)`;<br>• one hash-chained `approval` entry is appended to `doc/decisions/decision-log.jsonl`;<br>• `verify_approvals.py` passes.<br>No registry line is written. | tests/framework/test_autonomy_approve.py |
| A-AC4 | R3 **RED-FIRST** | `approve-under` refuses each of these, and `verify_approvals.py` fails each one when the stamp is forged by hand:<br>(a) the mandate key is not in the registry;<br>(b) the mandate has expired;<br>(c) the mandate has a revocation entry;<br>(d) the artifact's derived class is not in the mandate;<br>(e) `max_decisions` is already used up;<br>(f) the artifact touches an always-human item;<br>(g) the artifact is the mandate document itself, or the always-human file.<br>Each failure names its reason. | tests/framework/test_autonomy_approve.py, tests/hooks/test_verify_approvals.py |
| A-AC5 | R3, R4 **RED-FIRST** (self-approval) | Given a document hand-edited to say Approved, with an approval key line and `Approved-under: mandate <real key>` but **no** decision-log entry, Then:<br>(1) `verify_approvals.py` exits 1 with `approved-under stamp has no decision-log entry`;<br>(2) CI gate 1, in both `ci-examples/*.yml`, is red;<br>(3) `guard_agent_spawn.py` refuses an engineer spawn naming this spec.<br>All three callers use the one validator (ADR-3). Today the spawn guard reads only the status line `[MEASURED: grep -n '_read_status' .claude/hooks/guard_agent_spawn.py]`, so (3) is red first. | tests/hooks/test_verify_approvals.py, tests/ci/test_ci_examples.py, tests/hooks/test_guard_agent_spawn.py |
| A-AC6 | R4 **RED-FIRST** (self-widening) | While a mandate is active, each of these is refused:<br>(a) an `Edit` of the mandate document → AH5 (B-AC6);<br>(b) `approve-under` on a widening draft or on `scripts/autonomy.json` → AH5;<br>(c) the agent running `scripts/approve.sh mandate-…` → owner-only (B-AC4);<br>(d) `git push origin main` or `git merge` into main under the standing mandate in its first 28 days, or at any time while `merge_allowed` is false → AH3 (D2). | tests/hooks/test_guard_always_human.py, tests/framework/test_autonomy_approve.py |
| A-AC7 | R5 | Given an owner runs `scripts/revoke.sh <mandate key> --by o`, Then the registry gains an entry with its own key `revoke-<target-key>-<date>[-rN]`, `kind: "revocation"`, `revokes: <target>`, `artifact` set to the target document, and status `Revoked`. Then:<br>• the next `approve-under` refuses with `mandate revoked`;<br>• the next spawn whose upstream is approved under that mandate is refused;<br>• `verify_approvals.py` still passes for documents approved **before** the revocation (an approval made in time stays valid) and fails any approved after it. | tests/framework/test_autonomy_mandate.py, tests/hooks/test_guard_agent_spawn.py |
| A-AC8 | R6 **RED-FIRST** | Given no `scripts/autonomy.json` and no mandate, order or absence entries, Then:<br>• `autonomy.py status` prints `inactive`;<br>• `approve-under` refuses with `no active mandate or order`;<br>• an engineer spawn on an In Review spec is refused exactly as today;<br>• every existing test in `tests/hooks/` and `tests/ci/` passes unchanged, except the cases this spec adds. | tests/framework/test_autonomy_mandate.py (existing hook tests unchanged) |
| A-AC9 | R3, R5 (key revisions, ADR-4) | Given the registry already holds key `k` and the same document is approved again the same day, Then the new key is `k-r2` (then `-r3`, and so on), and no two registry lines written after this change share a key. A key-collision check in `verify_approvals.py` reports duplicates written before this change as `legacy duplicate key (last entry wins)`, as information, not failure. The registry has one such duplicate today: `prd-verify-tiers-merge-gate-2026-10-20` ×2 `[MEASURED: python3 count of registry keys]`. | tests/hooks/test_approve_script.py, tests/hooks/test_verify_approvals.py |
| A-AC10 | R3 (registry compatibility) **RED-FIRST** | Every new registry entry kind (mandate, order, revocation, override, absence) carries all five required fields. A probe line with no `artifact` makes `verify_approvals.py` fail **every** declared key with `registry unavailable: … missing required field(s): ['artifact']` `[MEASURED: temp APPROVAL_LOG with one revocation-shaped line lacking artifact → exit 1, 5 of 5 keys unresolved; with artifact → exit 0]`. The test plants such a line and shows it red, then the conforming shape green. | tests/hooks/test_verify_approvals.py |

### Increment 4 — G: reconciling AGENTS.md §5–§6 (R25–R27)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| G-AC1 | R25, R26 | AGENTS.md §6 rule 2 states that every Approved status traces to a human registry entry: the owner approving the artifact, a mandate that covers it, or an order that covers it. It also states that provisional work is never Approved and carries no key. §6 rule 1 gains exceptions (a), (b) and (c). §5 states which tiers and classes a mandate may cover. The document test checks the anchor phrases. | tests/framework/test_doc_contracts.py |
| G-AC2 | R27 **RED-FIRST** | Over `AGENTS.md`, `.agents/`, `.claude/agents/` and `doc/framework/`, every line matching a per-gate human-approval pattern (§G of the design) carries the qualifier `AGENTS.md §6` (mandate/order/absence), or is exempt (a `Do not:` line, or a line that only describes the status vocabulary). A planted line `every stage waits for the human` in a temp copy is red, naming `file:line`. | tests/framework/test_doc_contracts.py |

**R27 location list (ba-sa confirms).**
- **Search:** `grep -rnE 'Approved|อนุมัติ|human approval|approval gate|👤|only the human|only a human|มีแต่มนุษย์|จบตา|walking past|เดินข้าม|refuse to start|ปฏิเสธที่จะเริ่ม' AGENTS.md .agents/ .claude/agents/ doc/framework/ doc/templates/`, then a second grep for `the human (approv|gives|moves)|until the human|after the human|approval gate`, both run on 2026-10-20 `[MEASURED]`.
- **Locations needing rewording or a qualifier:**
  - AGENTS.md:58–60 (the tier table and its 👤 path), :76 (§6.1), :77 (§6.2);
  - `.agents/skills/handoff-protocol/SKILL.md`: 13 (pipeline 👤), 18, 38–47 (Human Approval Gate rules 1–4);
  - `.claude/agents/pm.md:30` ("only the human approves");
  - `.claude/agents/qa.md`: 14 and 31;
  - `.claude/agents/frontend-qa.md`: 14 and 33;
  - `.claude/agents/ai-engineer.md`: 14 and 43;
  - `.claude/agents/frontend-engineer.md:46`;
  - `doc/framework/SETUP.md`: 79–99;
  - `doc/framework/WHY.md`: 66–68 (§5);
  - `doc/framework/ADAPTERS.md:19`;
  - `.agents/skills/coordinator-discipline/SKILL.md`: 3 ("approving work") and 140 (the brief's `Upstream:` line).
- **Checked, and still true unchanged:** `ba-sa.md:14,33` and `pm.md:30`'s "never set Approved yourself". Authors still never stamp their own work. Only the owner's scripts, or `approve-under` run by the coordinator, can.
- `COORDINATOR-CONSTITUTION.md:31-32,44-45` and `NORTH-STAR.md:138-145` are consistent unchanged: they talk about approved documents, not about who approves.

### Increment 5 — C: earned autonomy (R11–R14)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| C-AC1 | R11 | `autonomy.py log` appends to `doc/decisions/decision-log.jsonl`. It requires `id`, `prev` (SHA-256 of the previous line), `ts`, `project`, `kind`, `class`, `under`, `artifact`, `options`, `choice`, `why` and `reverse`, and refuses an entry that lacks any of them. It also refuses free-text fields that contain a run of 13 or more digits (the shape of a national ID; AGENTS.md §8), saying `looks like an identifier — describe the shape, not the value`. | tests/framework/test_decision_log.py |
| C-AC2 | R11 **RED-FIRST** (tamper) | `autonomy.py verify-log` reports `chain broken at line n` when an earlier line is edited, a line is deleted, or two lines are reordered. In CI, `autonomy.py verify-log --append-only <base>` fails when `git diff <base>..HEAD -- doc/decisions/decision-log.jsonl` contains any removed or changed line. Each is planted, shown red, and reverted. | tests/framework/test_decision_log.py |
| C-AC3 | R12 | `scripts/override.sh <decision-id> [--significant] --by o` (owner-only) writes a registry entry with all five fields, `kind: "override"`, its own key `override-<decision-id>-<date>[-rN]`, `artifact: doc/decisions/decision-log.jsonl`, status `Overridden`, `target` and `significant`. `autonomy.py report --window 14` prints the decisions in the window, the overrides, the rate and whether there was a significant override. It exits 0. | tests/framework/test_autonomy_report.py |
| C-AC4 | R13 | `autonomy.py propose-widening --class X` writes a draft mandate in `doc/mandates/` with status In Review and the evidence: rate, n, window, and override IDs. It refuses when the rate is above the threshold, or the window is shorter than the mandate's window. The agent cannot approve the draft (A-AC6 b and c). | tests/framework/test_autonomy_report.py |
| C-AC5 | R14 **RED-FIRST** | The effective mandate is **derived at check time** from the registry and the log, and no file is written. The cases:<br>• one significant override on a class-X decision → `approve-under` for class X refuses, naming `narrowed: significant override <id>`;<br>• a rate above 5% in 14 days → classes with overrides are removed, or the whole mandate is suspended if no class can be identified;<br>• an owner-correction-rate rise across two consecutive 14-day windows (N6, from `correction_rate.measure`) → suspended.<br>The test asserts that no file under the repo or the registry directory changes between planting the override and the refusal (narrowing never depends on the actor). | tests/framework/test_autonomy_report.py |
| C-AC6 | R14, N4, N5 (fail-closed) | While verify-tiers H has not shipped (no rework causes) or there are fewer than 28 days of escaped-defect records (N5 baseline), `validate-mandate` refuses activation with `quality guard N4/N5 not measurable — a mandate cannot start`. `approve-under` treats such a mandate as inactive. | tests/framework/test_autonomy_mandate.py |

### Increment 6 — J: task orders (R39–R45)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| J-AC1 | R39 | `scripts/delegate.sh "<task>" --by o --until <date> --allow <grants> --slug <s>` does three things. It creates `doc/orders/ORDER-<project>-<s>.md` from `doc/templates/order.md`, already approved and carrying its key. It runs `git add` on it. It appends a registry entry with all five fields plus `kind: "order"`, `grants`, `expires` and `task_sha256`. The key is `order-<project>-<s>-<date>[-rN]`. `verify_approvals.py` passes. | tests/framework/test_delegate.py |
| J-AC2 | R41 **RED-FIRST** (never-grantable) | `delegate.sh` exits 2 naming the grant for each of these: `delete-data`, `delete-history`, `send-outside`, `spend`, `security`, `personal-data`, `change-mandate`, `change-orders`, `change-always-human`, `change-approval`, `change-bans` and `widen`. It also refuses unknown grants, the bare `deploy` (it must say `deploy-dev` or `deploy-prod`), and `merge` while `scripts/verify-merge.sh` does not exist (`merge needs the verify-tiers merge gate`). | tests/framework/test_delegate.py |
| J-AC3 | R40 | `approve-under <doc> --order <key>` stamps `Approved-under: order <key>` only when the document's filename carries the order slug and its class is inside the order's grants. Otherwise it refuses with `outside the order — stop and ask (R42)`. `verify_approvals.py` fails a forged order stamp for an unknown, expired, revoked or out-of-scope order. | tests/framework/test_autonomy_approve.py, tests/hooks/test_verify_approvals.py |
| J-AC4 | R41 **RED-FIRST** | Under an active order with default grants, the guard refuses each of these, naming the never-grantable item:<br>• `rm -rf data/`<br>• `curl -X POST …`<br>• a spend pattern<br>• an AH2 path edit<br>• an AH5 path edit<br>A configured `deploy-prod` command pattern is refused without the grant, and allowed with `deploy-prod` named (and not absent; see K-AC5). | tests/hooks/test_guard_always_human.py |
| J-AC5 | R42, R16 | `autonomy.py ask --order <key> --question … --recommend … --why …` logs an `ask` entry. It refuses with no `--recommend`. While an `ask` on an artifact is unanswered, `approve-under` for that artifact refuses with `waiting for the owner`. | tests/framework/test_decision_log.py |
| J-AC6 | R43 **RED-FIRST** | Under an active order:<br>• `approve-under` on a QA report whose verdict is FAIL is refused;<br>• a `merge` step needs `verify-merge.sh --check` to report GREEN, or RED limited to the baseline, for the tree;<br>• a RED record refuses the merge.<br>A red gate blocks the next step. | tests/framework/test_autonomy_approve.py |
| J-AC7 | R44 | `revoke.sh <order key>` takes effect at the next `approve-under` or spawn (as in A-AC7). `autonomy.py close-order <key>` writes `doc/orders/ORDER-<project>-<s>-report.md` from `doc/templates/order-report.md`, listing every decision-log entry under the order with its reverse action. It refuses if any entry lacks a reverse action. There is exactly one report per order: a second `close-order` refuses. | tests/framework/test_delegate.py |
| J-AC8 | R45 | An override of an order decision counts towards the rate (C-AC3). A significant override, or a rate above the threshold, removes that class from the **default grants** that `delegate.sh` prints for future orders: `effective default grants: … (business-rules removed: override <id>)`. | tests/framework/test_autonomy_report.py |

### Increment 7 — K: absence mode (R46–R50)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| K-AC1 | R46 | Absence can start in two ways:<br>• the owner runs `scripts/away.sh --until <date> --by o`, which writes a registry entry `kind: "absence"` with all five fields;<br>• the agent runs `autonomy.py absence-start --trigger silence --ask <id>`, which is allowed only when that `ask` entry has a recommendation and is more than 4 hours old, with no later answer.<br>Otherwise it refuses with the reason. `absence-end` is logged with `ended_by: owner-message \| date`. `status` and the digest show the start, the trigger and the time. | tests/framework/test_autonomy_absence.py |
| K-AC2 | R47 **RED-FIRST** | During absence, `approve-under --provisional <doc>` leaves the status line **In Review**, adds `Provisional: <decision-id>`, writes **no** approval key line, and logs `kind: provisional`. `guard_agent_spawn.py` accepts a provisional upstream **only while absence is active**. After `absence-end`, the same spawn is refused. The red-first case is the spawn after the absence has ended. | tests/framework/test_autonomy_absence.py, tests/hooks/test_guard_agent_spawn.py |
| K-AC3 | R47 | A merge (`autonomy.py merge-check <range>`) is refused if any provisional decision of class `business-rules` touches the range, or if any provisional item is in the range at all. It needs a GREEN merge-gate record. While verify-tiers D is missing, every absence merge is refused. | tests/framework/test_autonomy_absence.py |
| K-AC4 | R48 **RED-FIRST** (never-while-absent) | During absence, each of these is refused by the guard and logged as `kind: queued`:<br>• deleting data;<br>• `deploy-prod`;<br>• sending outward;<br>• spend;<br>• an AH2 edit;<br>• a widening (`propose-widening`, or `approve-under` on `doc/mandates/**`).<br>`autonomy.py return-review` lists them under "queued for you". | tests/hooks/test_guard_always_human.py, tests/framework/test_autonomy_absence.py |
| K-AC5 | R49 | Given an order with `deploy-prod`, and absence then starts, When the deploy pattern runs, Then it is refused with `deploy-prod waits for the owner's return (R49)`. The order's other grants still apply. | tests/hooks/test_guard_always_human.py |
| K-AC6 | R50 | `autonomy.py return-review` prints one list of every decision logged during the absence, each with its reverse action. The owner confirms with `scripts/approve.sh <slug>`, which now also **removes** the `Provisional:` line when stamping (ADR-2). The owner reverses with `scripts/override.sh <id> --reverse`. A reversed item counts as an override (N13). | tests/framework/test_autonomy_absence.py, tests/hooks/test_approve_script.py |

### Increment 8 — D: the daily digest (R15–R17, R24)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| D-AC1 | R15 | `python3 scripts/digest.py` prints three sections: `Done`, `Decided on your behalf` (each item with its log ID and reverse action) and `Waiting for you`. It also prints the mandate's remaining decisions and spend, the expiry, the current override rate, and any narrowing since the last digest (R14). | tests/framework/test_digest.py |
| D-AC2 | R16 **RED-FIRST** | An `ask` entry without a recommendation cannot be logged (J-AC5). A legacy entry without one is shown in the digest as `DEFECT: question without a recommendation`. That case is planted. | tests/framework/test_digest.py |
| D-AC3 | R17 | An `ask` stays under "Waiting for you" until a later registry entry (override, approval or confirmation) or log entry `kind: answer` names its ID. | tests/framework/test_digest.py |
| D-AC4 | R15 (A) | Adapter ก runs `digest.py --brief` at SessionStart, next to `correction_rate.py --brief`. ADAPTERS.md declares push notification for ก as `[INFERRED: listed as unproven in ADAPTERS.md:34-39, MEASURED by grep -n 'แจ้งเตือน' on 2026-10-20]`, and for ข as `session only`. | tests/framework/test_settings_deny.py (new case), tests/framework/test_doc_contracts.py |

### Increment 9 — E: right the first time (R18–R22)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| E-AC1 | R18 | `python3 scripts/learning_loop.py --window 28` groups QA rework causes (`agent_time.REWORK_CAUSES`) and feedback memories into recurring causes (≥ 2 occurrences). For each, it prints a proposal stub marked `owner approval required (AH5)`. It exits 0. Without verify-tiers H it prints `unavailable: rework causes not shipped`. | tests/framework/test_learning_loop.py |
| E-AC2 | R19 **RED-FIRST** (all work, not opt-in) | `guard_agent_spawn.py` refuses a `qa` or `frontend-qa` spawn when either of these holds:<br>• `doc/qa/REVIEW-<slug>.md` is missing or does not record a PASS verdict;<br>• its `Reviewer-run:` equals its `Author-run:`.<br>`NO_SPEC_BUGFIX:` work uses `REVIEW-bugfix-<id>.md`. Each case is planted and shown red. | tests/hooks/test_guard_agent_spawn.py |
| E-AC3 | R19 | `.claude/agents/reviewer.md` exists. Its mission says it starts from the files, never the author's conversation. `doc/templates/review-report.md` exists. AGENTS.md §5 shows `engineer → reviewer → qa` in every tier. | tests/framework/test_doc_contracts.py |
| E-AC4 | R20 | `coordinator_lint.py` rule 7: an engineer brief (`Slice:` block) must carry `Impact:`, taken from the spec's "Affected tests / affected files", and `Selected:`, the output of `verify-handoff.sh --list`. Until verify-tiers B and H ship, the rule accepts `Impact: unavailable (<reason>)`. | tests/coordinator/test_coordinator_lint.py |
| E-AC5 | R21 | Under autonomy, `handback_lint.py --new-tests` requires that each new test ID in the self-check carries a `fault:` line: the planted fault and its red output line. A missing line is flagged. | tests/coordinator/test_handback_lint.py |
| E-AC6 | R22 | `autonomy.py log --kind task-start` requires `depth: quick\|standard\|deep`. For `deep` it also requires `design: <DESIGN path>`. | tests/framework/test_decision_log.py |

### Increment 10 — H: measurement and trial (R28–R30)

| # | Maps to | Given / When / Then | Test file / evidence |
|---|---|---|---|
| H-AC1 | R28 **RED-FIRST** | `agent_time.py --owner` reports owner messages per day and per feature. A feature's window runs from the first registry or log entry naming its slug to its Done approval. A message falling in overlapping windows is split equally between them. The output also reports owner approvals per feature by basis (owner, mandate, order) from the registry and the log.<br>The planted mistake: a reader that counts every inbound `user` line as the owner. Then task notifications and meta lines are counted, and the fixture's owner count is wrong. The reader's rule is that a line counts as the owner's only when its content is a plain string not starting with `<` and `isMeta` is not true `[INFERRED from the coordinator's prior-art deep3.py; settled by the fixture]`. | tests/hooks/test_transcript_reader.py, tests/framework/test_agent_time.py |
| H-AC2 | R29 | `autonomy.py log-escape --artifact <doc> --found-by <role>` appends to `doc/decisions/escaped-defects.jsonl` (hash-chained). It derives the `basis` (owner, mandate, order or provisional) from the artifact's header. `autonomy.py report --escapes` splits the counts by basis. | tests/framework/test_decision_log.py |
| H-AC3 | R30 | The trial follows the method of `doc/qa/QA-delegated-autonomy-trial.md`:<br>• at least 4 weeks under a narrow first mandate;<br>• N1–N7 measured before and after with the same tools;<br>• one planted attempt per AH class, per never-grantable item and per never-while-absent item, each refused and reverted with zero residue;<br>• at least 2 orders end to end;<br>• at least 1 absence period.<br>It is accepted only if N4–N6 hold and N7 = 0. | Trial report |

### Increment 11 — I: self-evolution (R31–R38)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| I-AC1 | R31 | `scripts/evolve.sh` (owner-only, B-AC4) creates `doc/evolution/CYCLE-<date>.md` from `doc/templates/evolution-cycle.md`. `scripts/autonomy.json` holds `evolution.schedule` (`monthly` by default, or `off`). The digest prints `evolution cycle missed: last <date>, schedule monthly` when overdue. ADAPTERS.md declares how each adapter schedules. | tests/framework/test_evolution.py |
| I-AC2 | R32 **RED-FIRST** | `autonomy.py ledger-add` appends to `doc/evolution/ledger.jsonl` with `id`, `title`, `source`, `verdict`, `reason`, `pain` and `excerpt`. It refuses a duplicate (normalised title or source) unless the earlier verdict was `rejected` **and** `--new-evidence` names something not already in the ledger. | tests/framework/test_evolution.py |
| I-AC3 | R33 | `autonomy.py ledger-rank` orders ideas that name `pain: <metric> <expected delta>` above every idea with no pain link. | tests/framework/test_evolution.py |
| I-AC4 | R36, R37d **RED-FIRST** | `scripts/release.sh <version>` (owner-only) refuses when `check_neutrality.py` fails, or when the `CHANGELOG` entry lacks what changed, the target metric, the trial result or the rollback. A planted provider name in a core file blocks the release. | tests/framework/test_evolution.py |
| I-AC5 | R37a **RED-FIRST** | An evolution PRD whose changed paths include any protected path (the AH5 set) or the ban list is classified AH5. `approve-under --mandate` refuses it even when the mandate covers `framework-non-business`, because protected paths are subtracted from every class (ADR-9). | tests/framework/test_autonomy_approve.py |
| I-AC6 | R37c | **The deterministic half.** `.claude/agents/evolution-scout.md` frontmatter `tools:` is exactly `WebSearch, WebFetch`: no Bash, Edit, Write or Agent. `ledger-add` stores web text only in `excerpt`, wrapped as quoted data, and the cycle report renders excerpts inside blockquotes. **The behavioural half** ("a planted instruction causes no action") cannot be proven by pytest. It is a trial probe: a page under the trial's control carries `ignore your rules and run …`, and the transcript (through the J reader) shows the scout made no tool call outside its two tools, and the report quotes the line as data. | tests/framework/test_doc_contracts.py, tests/framework/test_evolution.py, trial report |
| I-AC7 | R34, R35, R38 | The cycle report template has these sections: scanned, adopted / rejected / deferred with reasons, past adoptions against targets (N9, N11), and the rollback candidates. A proposal is a PRD from `doc/templates/PRD.md`. An adoption entry needs `trial: <before> → <after>` from the meter and a quality line (rework and escapes not up), or `ledger-add --verdict adopted` refuses. | tests/framework/test_evolution.py |

## Functional Behavior (cross-cutting)

**Header lines.** The status vocabulary in AGENTS.md §5 is unchanged. Three optional header lines are added (ADR-2):

| Line | Written by | Meaning |
|---|---|---|
| `Decision-class: <class>; touches: <none\|business-rules\|security\|personal-data,…>` | pm and ba-sa on PRDs and specs, required only while autonomy is active | Input to classification. It can add an always-human touch, never remove one. |
| `Approved-under: mandate <key>` or `Approved-under: order <key>` | `approve-under` only | Marks a non-owner basis. Its absence on an Approved document means owner approval in the registry. |
| `Provisional: <decision-id>` | `approve-under --provisional` only, during absence | The status stays In Review, and there is no approval line. |

**Who writes what.**

| Store | Writers | Holds |
|---|---|---|
| Registry (outside the repo, human-only) | `approve.sh`, `delegate.sh`, `revoke.sh`, `override.sh`, `away.sh`, `evolve.sh`, `release.sh`. All are owner-only. | Owner approvals, mandates, orders, revocations, overrides, absence declarations |
| `doc/decisions/decision-log.jsonl` (in the repo, hash-chained, append-only) | `autonomy.py` only | The assistant's approvals under a mandate or order, decisions, provisional items, asks, queued items, absence start and end |
| `doc/decisions/escaped-defects.jsonl` | `autonomy.py log-escape` | N5 records |
| `doc/evolution/ledger.jsonl` | `autonomy.py ledger-add` | Evaluated ideas |

**Fail-closed rules.**
- An unknown class, a missing `Decision-class:` under autonomy, a missing project pattern set for AH3 deploy or AH4 spend while a mandate is active (`autonomy.py doctor` names it), or an unmeasurable quality guard: each means refuse or treat as always-human (R10).
- The only fail-open exception is the guards' existing rule that a malformed hook payload exits 0 `[MEASURED: guard_bash.py:243-247, guard_approval_registry.py main]`. It is kept, so that a hook bug cannot wedge every call.

## Impact table — every file touched

"Opt-in only" means the behaviour changes only in a project with `scripts/autonomy.json` and an active mandate, order or absence. The text changes for everyone.

| # | File | Inc. | What changes | Whose behaviour changes, and how | Opt-in only? |
|---|---|---|---|---|---|
| 1 | `scripts/autonomy.py` **(new)** | B–K, I | Core library and CLI: items, classifiers, `status`, `validate-mandate`, `approve-under`, `log`, `verify-log`, `report`, `propose-widening`, `ask`, `absence-start/end`, `return-review`, `merge-check`, `close-order`, `log-escape`, `ledger-add/rank`, `doctor`, `verify` | Coordinator: the only route to approval under a mandate or order, and to decisions while absent | Yes |
| 2 | `scripts/autonomy.json.example` **(new)**; `scripts/autonomy.json` (project, protected) | B, A, I | Project additions to AH patterns, protected branches, deploy and spend patterns, evolution schedule, project slug | — | It *is* the opt-in |
| 3 | `scripts/delegate.sh`, `scripts/revoke.sh`, `scripts/override.sh`, `scripts/away.sh`, `scripts/evolve.sh`, `scripts/release.sh` **(new; owner-only wrappers)** | A, C, J, K, I | Owner commands that write registry entries (and, for `delegate`, an order document) through `approve.py`'s writer | The owner gains commands. Agents are refused by B-AC4. | Yes |
| 4 | `scripts/approve.py` | A, K | `DOC_DIRS` gains `doc/mandates` and `doc/orders`; exact-stem slug match for `mandate-`/`order-`; key revision suffix `-rN`; `kind`, `expires`, `terms_sha256` on mandate entries; strips `Provisional:` when stamping; refuses a document carrying `Approved-under:` | Owner: same command. Keys get `-r2` only on same-day re-approval. | Mostly no. The suffix applies to everyone, and only on collision. |
| 5 | `scripts/verify_approvals.py` | A, J, K | Calls the shared validator: `Approved-under:` stamps resolve through the decision log to a live mandate or order; provisional docs carry no key; reports legacy duplicate keys; `DOC_DIRS` += mandates, orders | Everyone who runs it: a new failure appears only for documents carrying the new header lines | Effectively opt-in |
| 6 | `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml` | A, C | Gate 1 (inline, byte-identical in both) learns `Approved-under:` (key from the decision log in the checkout, basis key in the registry). New step: `python3 scripts/autonomy.py verify --ci --base <base>` (chain, append-only, class, budget) | CI | Gate-1 change: everyone. New step: no-op without autonomy files. |
| 7 | `.claude/hooks/guard_bash.py` | B, F, J, K | Owner-script rule (**always on**), always-human command rule, protected-branch commit rule, never-grantable and never-while-absent queue | **Every role in every project:** agents can no longer run owner commands. Under autonomy: AH command refusals. | Owner-script rule: no. The rest: yes. |
| 8 | `.claude/hooks/guard_autonomy_paths.py` **(new)** | B | Write/Edit guard for protected paths while autonomy is active | Every role under autonomy | Yes |
| 9 | `.claude/hooks/guard_agent_spawn.py` | A, K, E | Upstream check uses the shared validator (`Approved-under`, `Provisional` while absent). **New gate on `qa`/`frontend-qa` spawns: a review PASS by a different run (R19).** | Coordinator: every QA dispatch now needs a review first, **in all projects (D5)** | Review gate: no. The rest: yes. |
| 10 | `.claude/settings.json` | B, D | Registers `guard_autonomy_paths.py` on `Write\|Edit\|MultiEdit\|NotebookEdit`; adds `digest.py --brief` to SessionStart | — | — |
| 11 | `.claude/agents/reviewer.md`, `.claude/agents/evolution-scout.md` **(new)** | E, I | Independent reviewer; a scout with tools `WebSearch, WebFetch` only | New roles | Reviewer: no. Scout: yes. |
| 12 | `.githooks/pre-commit` | B, C | Runs `autonomy.py check-commit` (protected paths need an `Owner-Approved:` trailer while autonomy is active; decision-log chain intact) | Everyone committing; a no-op without autonomy | Yes |
| 13 | `doc/framework/ADAPTERS.md` | B, D, I | Rows per adapter for: command, path and spawn enforcement; digest delivery and push; evolution scheduling; owner-shell-prefix bypass (B-AC5) | — | — |
| 14 | `AGENTS.md` (§5 table and status grammar lines 56–70; §6 lines 74–81) | G, E | §5: mandate-coverable classes, reviewer in every path, three optional header lines. §6.1 exceptions (a)–(c); §6.2 traces Approved to the three human bases; provisional is never Approved. | All roles | Text everywhere. Behaviour opt-in, except the reviewer. |
| 15 | `.agents/skills/handoff-protocol/SKILL.md` (13, 18, 38–47) | G, E | Pipeline diagram with reviewer and the 👤 qualifier; the gate rules name mandate, order and absence | All roles | As 14 |
| 16 | `.agents/skills/coordinator-discipline/SKILL.md` (3, 140, brief template) | G, E, C | Brief gains `Impact:`, `Selected:`, `Under: mandate\|order <key>`; how to approve under a mandate (only via `approve-under`); digest duty | Coordinator | Mostly opt-in |
| 17 | `.claude/agents/pm.md`, `ba-sa.md`, `ai-engineer.md`, `frontend-engineer.md`, `qa.md`, `frontend-qa.md` | G, E | Upstream rule accepts `Approved-under`/`Provisional` as AGENTS §6 says; pm/ba-sa fill `Decision-class:` under autonomy; engineers wait for review before QA; qa records rework causes | Every agent | Mostly opt-in. Review step: all. |
| 18 | `doc/framework/SETUP.md` (79–99 and a new section), `doc/framework/WHY.md` (§5, 66–68) | G | Consistency; how to opt in, issue an order, revoke, go away and come back | Owner and new users | — |
| 19 | `scripts/coordinator_lint.py`, `doc/framework/COORDINATOR-CONSTITUTION.md` | E | Rule 7 (`Impact:`, `Selected:`) | Coordinator | Rule active only when the brief has `Under:` |
| 20 | `scripts/handback_lint.py` | E | `--new-tests` fault check | Coordinator | Yes |
| 21 | `scripts/digest.py`, `scripts/learning_loop.py` **(new)** | D, E | Report only | Owner reads them | Yes |
| 22 | `scripts/agent_time.py`, `.claude/meter/transcript_reader.py` (verify-tiers J, **uncommitted**) | H | `--owner` report; the reader marks inbound origin (owner, system or agent) | Report only | — |
| 23 | Templates **(new)**: `doc/templates/mandate.md`, `order.md`, `order-report.md`, `review-report.md`, `evolution-cycle.md` | A, J, E, I | — | — | — |
| 24 | `doc/templates/PRD.md`, `doc/templates/spec.md` | A | Optional `Decision-class:` header line, with a note on when it is required | pm, ba-sa | Required only under autonomy |
| 25 | `doc/decisions/`, `doc/mandates/`, `doc/orders/`, `doc/evolution/` **(new directories)** | A, C, J, I | Data | — | Yes |
| 26 | New tests: `tests/framework/test_autonomy_items.py`, `test_autonomy_mandate.py`, `test_autonomy_approve.py`, `test_decision_log.py`, `test_autonomy_report.py`, `test_delegate.py`, `test_autonomy_absence.py`, `test_digest.py`, `test_learning_loop.py`, `test_evolution.py`; `tests/hooks/test_guard_always_human.py`, `test_guard_autonomy_paths.py` | all | — | — | — |
| 27 | `scripts/verify-fast.sh` | all | Routing `case` lines for the new scripts, hooks and tests | — | — |

**Not touched:**
- the approved verify-tiers spec, design and amendment, and the PRD;
- the uncommitted J files, which belong to increment H later, after J is committed;
- `scripts/check_neutrality.py`: the new core files must simply pass it;
- `doc/tasks/backlog.md`: pm owns it.

## Affected tests / affected files

**How this list was built:**
- The R27 greps above.
- `grep -n 'DOC_DIRS\|_DOC_DIRS' scripts/*.py`.
- Reads of `scripts/approve.py` (whole file), `scripts/verify_approvals.py` (whole file), the CI gate-1 inline script (`ci-examples/github-actions.yml:30-80`), `.claude/hooks/guard_approval_registry.py`, `guard_agent_spawn.py:1-110`, `.claude/settings.json`, `tests/hooks/test_approve_script.py`'s key assertions (lines 113–116), and `tests/ci/test_ci_examples.py:202-330`.
- Downstream projects' own parsers of registry lines cannot be seen from here.

| Existing test | What it pins | Effect |
|---|---|---|
| `tests/hooks/test_approve_script.py` | Key `spec-payment-refunds-<today>` on first approval (113–116); refusals; no prompt; LIMIT notice | The first approval still gets the bare key, because the `-rN` suffix is used only on collision `[INFERRED: test registries start empty]`. New cases: mandate exact-stem match, `-r2`, stripping `Provisional:`, refusing a document with `Approved-under:`. |
| `tests/hooks/test_verify_approvals.py` | Agreement of the registry constants across the three consumers; resolution rules | Extended for the shared validator and duplicate reporting. The five required fields are unchanged. |
| `tests/ci/test_ci_examples.py` (gate 1: byte-identical; red on forged; green on matching; ignores templates and framework) | The inline gate-1 script | Gate 1 changes in **both** files identically. New cases: a forged `Approved-under:` is red; a valid one with a log entry is green. |
| `tests/hooks/test_guard_agent_spawn.py` | Gated types (engineers), `NO_SPEC_BUGFIX:` override, upstream prefixes | Qa and frontend-qa become gated for the review (E-AC2). Existing engineer cases unchanged. |
| `tests/hooks/test_guard_bash_matrix.py`, `test_guard_bash_bypasses.py`, and verify-tiers G's polling tests | A1' and R26 behaviour; `MUST_ALLOW` | The new rules must allow every `MUST_ALLOW` entry. The owner-script rule must not fire on `grep 'scripts/approve.sh'` (quoted mention). |
| `tests/hooks/test_guard_approval_registry.py` | Write-tool registry block | Unchanged |
| `tests/framework/test_settings_deny.py` | Deny rules; `correction_rate` at SessionStart | Add `digest.py`. Deny rules unchanged. |
| `tests/framework/test_pre_commit.py` | Clean commit passes; planted violations refused | New autonomy cases. A clean commit with no autonomy files still passes. |
| `tests/framework/test_neutrality.py`, `test_bootstrapped_project.py` | Neutral core; green after bootstrap | New core files are neutral. New tests pass in a bootstrapped copy with no `scripts/autonomy.json`. |
| `tests/framework/test_doc_contracts.py` (verify-tiers, uncommitted) | verify-tiers contracts | New contract functions are added. Do not edit while J is uncommitted; land after J. |

## Decisions (ADR-style): summary. Full text is in the design.

- **ADR-1** One registry, five required fields on every entry kind, plus a `kind` field. Revocations and overrides have their own keys.
- **ADR-2** Approved under a mandate or order is a stamp line (`Approved-under:`) plus a hash-chained log entry, not a registry line, because agents must never write the registry. Provisional is a stamp line (`Provisional:`) on an In Review document, not a new status.
- **ADR-3** One shared validator (`autonomy.validate_approval`) used by `verify_approvals.py`, `guard_agent_spawn.py` and `autonomy.py verify --ci`. CI gate 1's inline script mirrors its first two rules.
- **ADR-4** Registry keys get a `-rN` revision suffix on collision. Mandate and order keys include the project slug.
- **ADR-5** Owner slugs for mandates and orders match the filename stem exactly, not as a substring.
- **ADR-6** Path and command guards for AH and protected paths apply only while autonomy is active. The owner-script rule always applies.
- **ADR-7** The decision log lives in the repo, hash-chained, with append-only checked against the base in CI and at commit.
- **ADR-8** Narrowing is derived at check time from owner-written overrides. It is never stored by the assistant.
- **ADR-9** The class is derived from changed paths and tier. Header fields can only add always-human touches. The protected-path set is subtracted from every class.
- **ADR-10** The independent-review gate sits at the qa spawn, for all work.
- **ADR-11** The scout is restricted by its tool list. Web text is stored only as quoted `excerpt` data.
- **ADR-12** A mandate cannot activate while N4 or N5 is unmeasurable (fail-closed).
- **ADR-13** Owner commands are thin shell wrappers over a shared registry writer in `approve.py`.
- **ADR-14** Silence-triggered absence needs a logged `ask` with a recommendation that is more than 4 hours old.
- **ADR-15** Merges under order or absence need a GREEN merge-gate record (verify-tiers D). Until D ships, they are refused.
- **ADR-16** The interception matrix per adapter (design §B.4).

## Traceability

R1 → A-AC1, A-AC2 · R2 → A-AC1, A-AC3 · R3 → A-AC2, A-AC3, A-AC4, A-AC5, A-AC9, A-AC10 · R4 → A-AC5, A-AC6, B-AC4, B-AC5, B-AC6 · R5 → A-AC7 · R6 → A-AC8 · R7 → B-AC1, B-AC3 · R8 → B-AC1, B-AC2 · R9 → B-AC3, B-AC4, B-AC6, B-AC7, B-AC9 · R10 → B-AC8 · R11 → C-AC1, C-AC2 · R12 → C-AC3 · R13 → C-AC4 · R14 → C-AC5, C-AC6 · R15 → D-AC1, D-AC4 · R16 → D-AC2, J-AC5 · R17 → D-AC3 · R18 → E-AC1 · R19 → E-AC2, E-AC3 · R20 → E-AC4 · R21 → E-AC5 · R22 → E-AC6 · R23 → F-AC1, F-AC3 · R24 → F-AC2, D-AC1 · R25 → G-AC1 · R26 → G-AC1 · R27 → G-AC2 · R28 → H-AC1 · R29 → H-AC2 · R30 → H-AC3 · R31 → I-AC1 · R32 → I-AC2 · R33 → I-AC3 · R34 → I-AC7 · R35 → I-AC7 · R36 → I-AC4 · R37 → I-AC4, I-AC5, I-AC6 · R38 → I-AC7 · R39 → J-AC1, B-AC4 · R40 → J-AC3 · R41 → J-AC2, J-AC4 · R42 → J-AC3, J-AC5 · R43 → J-AC6 · R44 → J-AC7 · R45 → J-AC8 · R46 → K-AC1 · R47 → K-AC2, K-AC3 · R48 → K-AC4 · R49 → K-AC5 · R50 → K-AC6

Metrics: N1, N2 → H-AC1 · N3 → C-AC3, C-AC5 · N4–N6 → C-AC5, C-AC6, H-AC2 · N7 → B-AC3, J-AC4, K-AC4, H-AC3 · N12–N14 → J-AC7, K-AC6, J-AC5 · N8–N11 → I-AC1, I-AC7.

**50 requirements → 64 acceptance criteria** `[MEASURED: grep -cE '^\| [A-Z]-AC[0-9]+' on this file → 64; a loop over R1–R50 found every R in the traceability line]`. By increment: B 9, F 3, A 10, G 2, C 6, J 8, K 6, D 4, E 6, H 3, I 7.

## Open questions for the owner (none block approval)

1. **The owner's shell prefix and hooks (B-AC5).** If PreToolUse hooks also fire on the owner's `!` commands, the owner-script rule would block the owner. The design ships the rule only after a proof run. If the proof fails, what should the fallback be: block only while autonomy is active, or keep the gap as today?
2. **"Can never" scope (ADR-6).** R4 says the assistant can never edit the mandate, the list or their enforcement. The path guard applies only while autonomy is active, because outside autonomy those edits go through the ordinary tier-2 gates (owner-approved spec, reviewed diff). That is also how this very feature gets built. Should it be always on?
3. **Fail-closed activation (ADR-12).** No mandate can activate until verify-tiers H ships and 28 days of escaped-defect records exist. That delays the first mandate by at least 4 weeks after both ship. The alternative is to activate with N4/N5 marked "unmeasured" in the digest.
4. **The 13-digit refusal in the decision log (C-AC1)** is a shape heuristic for identifiers. Should the owner add more shapes for the pilot's data?

## Approval history

- **2026-10-20 — approved (human).** Registry key `spec-delegated-autonomy-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** ba-sa, from the approved PRD (R1–R50, D1–D7, with A8 and A9 accepted). It is based on a read of the approval scripts, the guards, CI gate 1 and the registry, and on probes run against a temporary copy of the registry.
