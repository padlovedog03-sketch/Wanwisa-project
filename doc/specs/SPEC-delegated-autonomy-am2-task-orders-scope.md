# SPEC: Amendment 2 — task orders as they will actually be built (row 5: F, A subset, C subset, J)

Status: Approved
Approval: spec-delegated-autonomy-am2-task-orders-scope-2026-10-22
Owner: ba-sa
Upstream: doc/specs/SPEC-delegated-autonomy.md (approved, registry key `spec-delegated-autonomy-2026-10-20`) and its doc/architecture/DESIGN-delegated-autonomy.md · doc/specs/SPEC-delegated-autonomy-am1-guards-catch-accidents.md (approved, `spec-delegated-autonomy-am1-guards-catch-accidents-2026-10-20`) · owner rulings doc/memory/jarvis-decides-self-improvement.md (2026-10-22), doc/memory/ease-of-use-over-strictness.md (point 3), doc/memory/smallest-useful-scope-first.md · doc/tasks/backlog.md "Row 5: what task orders need"
Date: 2026-10-22

## Overview

The approved spec and design stay as they are. This file is an impact check of the approved spec (2026-10-20) against what changed since, for the next build: backlog row 5 (task orders, plus the minimum they need from F, A, C and G). Nine approved criteria (eight in the row-5 list, plus am1's B-AC7) would, if built literally, either do nothing, block the order flow at its first commit, or reach `main`. This amendment rewords them and adds the obligations that am1 placed on later increments.

What changes, in one line each:
- **J-AC6** — a `merge` under an order goes into a non-protected working branch only, and needs a GREEN merge gate (the baseline-RED form is struck). Merging into `main` stays the owner's.
- **C-AC1, C-AC2 (as pulled into row 5)** — the decision log is a plain append-only JSONL log, checked by git diff at commit and in CI. No hash chain. A-AC3's "hash-chained" goes with it.
- **New AM2-AC3** — the commit-msg check (B-AC7 under am1) lets J commit its own outputs: appended log lines, and the owner's new order document.
- **J-AC7** — the order report lives outside the protected `doc/orders/**`, and ends with the one owner command for main (coordinator friction (d), which the backlog folds in here).
- **A-AC3, A-AC4, J-AC3 under an order** — the order grant is checked by document kind; a business-rule touch is allowed when the order grants `business-rules-in-task`; the order document must be committed at HEAD with the registry's task hash (AM1-ADR-4).
- **A-AC5 (3), A-AC7 (spawn half)** — an `Approved-under:` document that fails validation blocks the spawn even when the brief also names an owner-approved spec.
- **New AM2-AC7, AM2-AC8** — `delegate.sh` and `revoke.sh` honour `--help`; the guard lets the agent run the new `autonomy.py` subcommands.

Nothing else in the approved spec, the design, or am1 changes.

**Markers.** `[MEASURED: <command>]` was run on 2026-10-22 at `96bebdb` (branch `feat/top3-tiers-mechanisms-deny`). Probes that need an active order used a throwaway repo in the session scratch directory: branch `feature/x`, a committed `scripts/autonomy.json` with `{"project":"p"}`, and a temp `APPROVAL_LOG` holding two `kind: order` entries for project `p` (`order-p-first-2026-10-22`, `order-p-second-2026-10-22`). Below this is called **the order fixture**. `[INFERRED]` was read, not run; the engineer checks it before building on it.

## Findings per brief bullet

### 1. J-AC6 "merge under an order" — what does it merge into?

The approved spec never says. R41 grants `merge` "with a GREEN merge gate", and R47 (absence, parked) says "merge into main". Read literally, J-AC6 lets the order reach `main`. That contradicts the 2026-10-22 owner ruling (merging into `main` stays human) and the ease-of-use anchor (signed approval is revisited only when autonomy reaches `main`).

Measured facts:
- The B guard already refuses this under an active order: `git merge feature/x` while on `main` → exit 2, `always-human item AH3 — matched: git merge while on main`. On a feature branch, `git merge feature/y` → exit 0 `[MEASURED: order fixture, payload fed to .claude/hooks/guard_bash.py]`. So `main` was never reachable through the guard. The wording is what is wrong, and an engineer building J-AC6 as worded would have to punch a grant-shaped hole in AH3.
- "or RED limited to the baseline" cannot happen. `verify-merge.sh` maps a `RED-BASELINE` record to `MERGE GATE RED`, exit 1 `[MEASURED: sed -n 150-160p scripts/verify-merge.sh, lines 155 and 159]`. No script reads a baseline file `[MEASURED: grep -n "VERIFY_BASELINE" scripts/*.py scripts/*.sh scripts/verify.conf.example → no match]`. The named baseline is VT Part E, which is parked (backlog, Parked table).

→ **Amended: AM2-AC1.**

### 2. C-AC1 and C-AC2 (hash-chained decision log): does J need them?

What J needs from C, traced through the approved criteria:
- A-AC3 and J-AC3 append an `approval` entry; A-AC5 fails a stamp that has **no** entry; J-AC5 appends an `ask`; J-AC7 lists entries with their reverse action; F-AC2 checks the `reverse` field of an entry.
- Each of these needs a log **writer with required fields** and a **reader**. None of them reads `prev`, and none fails or passes on chain integrity.

What the chain adds: detection of an edited, deleted or reordered earlier line. A git diff against the base (C-AC2's own second half, `--append-only <base>`) detects all three, because each shows as a removed or changed line `[INFERRED: git diff semantics]`. The chain does **not** stop a forged *appended* entry, since the agent can compute the hash. Its one extra power is the design's "anchoring" (owner commands record the log head hash in the registry), which belongs to increment C's override machinery and is parked.

R11 asks for a log "append-only and tamper-evident, **at the same level as the approval registry**". The registry is a plain JSONL file with no chain; its tamper evidence is CI reading a copy the agent cannot write `[MEASURED: grep -n "prev\|sha256" scripts/verify_approvals.py → no chain field]`. An append-only check in CI is that same level.

**Decision (AM2-ADR-2):** row 5 ships a plain append-only log. It keeps every C-AC1 field check except `prev`, and C-AC2's append-only half; the hash chain and anchoring stay parked with C. A-AC3's "hash-chained" is struck. This is the smaller option (smallest-useful-scope-first).

One more thing surfaced while checking this, and it decides how C must ship. **Today's commit check refuses every file J writes.** Under the order fixture, `check_commit` refuses `doc/decisions/decision-log.jsonl`, `doc/orders/ORDER-p-first-report.md` and `doc/orders/ORDER-p-second.md`, with no trailer, with `Owner-Approved: order-p-second-2026-10-22`, and with `Owner-Approved: order-p-first-2026-10-22`. Each fails with `AH5 … (a mandate or order key never counts)` `[MEASURED: order fixture, python3 -I -c "… autonomy.check_commit(root, msg)" over the three messages]`. All three paths are protected `[MEASURED: autonomy.is_protected(p, {}) → True, True, True; doc/specs/SPEC-x.md → False]`. So approved J cannot complete a single commit after its first log entry, and no owner trailer can clear a second order document (`_owner_approves` accepts only kind `approval`, autonomy.py:1021-1028 `[INFERRED from reading; consistent with the probe]`).

→ **Amended: AM2-AC2 (log), AM2-AC3 (commit check), AM2-AC4 (report path).**

### 3. A and G criteria in the row-5 list made stale by later changes

| Criterion | Stale? | Why |
|---|---|---|
| A-AC3 | **Yes** | It says "hash-chained" (finding 2). Its Given needs "an active mandate", but row 5 builds no mandate (A-AC1/A-AC2 parked); the backlog says to exercise it through `--order`. It also lacks AM1-ADR-4's binding: am1 says `approve-under` must grant only when the authorising document exists at HEAD. That matters because `_authority` counts **any** live order when the project slug is missing and `doc/orders/` exists `[INFERRED: autonomy.py:961-981, claim_any]`. → AM2-AC5. |
| A-AC4 (a)(b)(c)(f)(g) | **Partly** | (f) "touches an always-human item" collides with the order's **default** grant `business-rules-in-task` (R41). `classify_artifact` maps `touches: business-rules` to AH1 `[INFERRED: autonomy.py:858-859, _TOUCH_ITEMS]`, so every order-run PRD that decides a business rule would be refused. (g) names "the mandate document"; under an order it is the order document. → AM2-AC5. |
| A-AC5 (3), A-AC7 (spawn half) | **Yes** | The engineer spawn passes if **any** named spec is Approved. A brief whose `Slice:` names a missing spec, and which also cites the approved parent spec, passes with rc=0 `[MEASURED: payload with Slice: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md (not yet on disk) + Context: doc/specs/SPEC-delegated-autonomy.md → python3 .claude/hooks/guard_agent_spawn.py; rc=0]`. Every amendment brief cites its parent, so the refusal A-AC5 (3) and A-AC7 promise would be skipped by accident. The QA gate already reads the spec only from a `Spec:`/`Slice:` line (merge `0cc9c6c`); the engineer gate does not. → AM2-AC6 (narrow fix, opt-in only). The general `Slice:` gap is parked. |
| A-AC6 (c) | No | Already built and tested by B-AC4: `scripts/revoke.sh k` is in `tests/hooks/test_guard_always_human.py:120`, and `delegate.sh` is in the same file `[MEASURED: grep -rln "delegate.sh\|revoke.sh" tests/]`. Nothing to build; QA re-runs it. |
| A-AC7 (revoke.sh) | **Partly** | am1 requires every new owner wrapper to honour `--help`/`-h` with no write, carried as a test by the wrapper's own increment. A-AC7 and J-AC1 lack it. → AM2-AC7. |
| A-AC8, A-AC9, A-AC10 | No | Not built yet (`grep -n "\-r{" scripts/approve.py` → no match; `approve.py` has no `kind` field) `[MEASURED]`. The wording still holds. |
| G-AC1 | No | Its anchor phrases are still the ones to add. |
| G-AC2 | **List stale, AC not** | The criterion is a pattern scan, so it will catch new lines by itself. The spec's *location list* (2026-10-20) is out of date. Re-running both of its greps today `[MEASURED: the two grep -rnE commands from the spec's "R27 location list", over AGENTS.md .agents/ .claude/agents/ doc/framework/ doc/templates/]`: AGENTS.md now matches at 31 and 39 (§0, added by the coordinator spec) and §5/§6 moved to 93–95 and 114–115; `qa.md` and `frontend-qa.md` match only the second grep (15, 33 and 15, 35); `coordinator-discipline/SKILL.md:3` no longer matches, :174 does; `pm.md` moved to :31. The refreshed list is below under Affected files. |
| Spec note "test_doc_contracts.py: do not edit while J is uncommitted" | **Yes** | J is committed: `git ls-files scripts/agent_time.py tests/framework/test_doc_contracts.py` prints both `[MEASURED]`. The note no longer applies. |

**Tier 0 one-rework-round rule** (`.agents/skills/scope-discipline/SKILL.md` rule 4): checked; it makes no row-5 criterion stale. It governs how a reviewer judges a Tier 0 bugfix after round 1. No row-5 criterion names review rounds `[MEASURED: grep -n "round" over the J, A, F, G and C rows of SPEC-delegated-autonomy.md → no match]`.

**QA gate `Spec:` line (`0cc9c6c`)**: makes nothing in row 5 stale on the QA side. Its lesson (judge the spec on the brief's own line, not on any mention) is what AM2-AC6 applies to the engineer side, for stamped documents only.

### 4. Also found: the guard refuses every new agent subcommand

`AGENT_SUBCOMMANDS = ("items", "status", "check-commit")` `[MEASURED: scripts/autonomy.py:441]`. Under the order fixture, `python3 scripts/autonomy.py approve-under doc/specs/SPEC-x.md --order order-p-first-2026-10-22` and `python3 scripts/autonomy.py close-order …` both exit 2 with `always-human item AH5 — matched: autonomy.py approve-under` (or `close-order`); `status` exits 0 `[MEASURED: order fixture, guard_bash.py payloads]`. That is correct today. Each row-5 subcommand must be added to the tuple when it ships, or the coordinator cannot use it. → AM2-AC8.

## Acceptance criteria — changed and new

Each new wording carries its own RED-FIRST case where today's code is measured red. Hostile neighbours (what must stay refused) are listed in every row.

| # | Amends | Maps to | Given / When / Then | Test file |
|---|---|---|---|---|
| AM2-AC1 | J-AC6 | R43, R41 **RED-FIRST** | Given an active order **with** the `merge` grant, When the coordinator runs `autonomy.py merge-record --order <key> --into <branch> --record <merge-record> --ref <sha>`, Then it appends a `kind: merge` log entry only when all hold: `<branch>` is not protected (`main`, `master`, or the project's `protected_branches`); the order is live and grants `merge`; and `scripts/verify-merge.sh --check <merge-record> <sha>` prints `MERGE GATE GREEN` and exits 0. **Refused, each naming its reason:** `--into main` → `merging into a protected branch stays with the owner`; an order without `merge` → `outside the order — stop and ask (R42)`; a record whose banner is `MERGE GATE RED` (including one made from a `RED-BASELINE` record) or `MERGE GATE NOT RUN` → `merge gate is not GREEN`. Under the same order, `git merge …` while on `main` and `git push origin main` stay refused as AH3 (B-AC3, unchanged). `approve-under` on a QA report whose `Verdict:` is FAIL is refused (unchanged from J-AC6). **What a red gate blocks:** the `merge` log entry, and therefore close-order's `## Ready for main` (AM2-AC4), which stays `not ready`. A plain `git merge` into a non-protected branch is **not** gated (D-L13; the approved J-AC6 said "a RED record refuses the merge", which no guard does on a working branch: `git merge feature/y` on `feature/x` exits 0 under the order fixture `[MEASURED]`). The red-first case: `merge-record` does not exist today, so the `--into main` refusal is red. The gate's base ref stays its default (`origin/main`, else `main`), so the gate code always comes from the protected branch, never the working branch `[MEASURED: scripts/verify-merge.sh header, VERIFY_MERGE_BASE_REF default]`. **The grant is inert until a project configures the gate:** this repo is `not opted in` and `VERIFY_MERGE_GATE` defaults to `none`, so `verify-merge.sh` prints `MERGE GATE NOT RUN` here `[MEASURED: bash scripts/verify-handoff.sh --status → not opted in; scripts/verify-merge.sh header]`. The GREEN test case builds its record the way `_green_record` does in `tests/hooks/test_verify_merge.py:233` (a temp repo whose committed conf sets `VERIFY_MERGE_GATE=local-fallback`). | tests/framework/test_autonomy_approve.py |
| AM2-AC2 | C-AC1, C-AC2 (row-5 part) | R11, R24 **RED-FIRST** (tamper) | `autonomy.py log` appends one JSON line to `doc/decisions/decision-log.jsonl`. It requires `id`, `ts`, `project`, `kind`, `class`, `under`, `artifact`, `options`, `choice`, `why` and `reverse`, and refuses (exit 2, naming the field) an entry lacking any of them. There is **no `prev` field**. It refuses a free-text field holding a run of 13 or more digits, with `looks like an identifier — describe the shape, not the value` (unchanged). `reverse` follows F-AC2's grammar (unchanged). `autonomy.py verify-log --append-only <base>` exits 1 naming the line when `git diff <base>..HEAD -- doc/decisions/decision-log.jsonl` shows any removed or changed line; it is green when the diff only adds lines at the end. **Planted, each shown red then reverted:** an earlier line edited; a line deleted; two lines swapped. CI: the same command runs as a step in both `ci-examples/*.yml`, identically. | tests/framework/test_decision_log.py, tests/ci/test_ci_examples.py |
| AM2-AC3 | B-AC7 under am1 (new carve-outs) | R11, R39, R9 **RED-FIRST** | Given autonomy is active, When `.githooks/commit-msg` runs `autonomy.py check-commit`, Then these staged changes need no owner trailer:<br>(a) `doc/decisions/decision-log.jsonl` when its staged diff against HEAD only **adds lines after the last existing line** (a new file counts);<br>(b) an **added** (not modified) file that is the `artifact` of a live, unrevoked `kind: order` registry entry of this project, when that entry's key is on an `Owner-Approved:` trailer.<br>**Still refused, naming AH5 and the path:** the log with any removed, changed or inserted-before-the-end line; a modified order document; an added order document whose trailer names a different order, a revoked order, or an expired one; any other protected path (unchanged). The red-first case is the measured probe: under the order fixture, today `check_commit` refuses all of (a), (b) and the report path, even with the order's own key as trailer. | tests/framework/test_commit_msg_owner_trailer.py |
| AM2-AC4 | J-AC7 | R44, R24 | `revoke.sh <order key>` takes effect at the next `approve-under` or spawn, as in A-AC7 (unchanged). `autonomy.py close-order <key>` writes `doc/reports/ORDER-<project>-<s>-report.md` (**not** under the protected `doc/orders/**`) with `Status: In Review`, so CI gate 1 skips it `[MEASURED: ci-examples/github-actions.yml:67-72 checks only Approved/Done documents]`. It lists every log entry under the order with its reverse action, and the owner overrides the coordinator recorded (R45's interim rule while C is parked). It ends with a `## Ready for main` section: the last `merge` entry's gate banner line, the working branch `<branch>`, and exactly one line, asserted byte for byte with `<branch>` and `<key>` substituted:<br>`Owner command: git switch main && git merge --no-ff <branch> -m "Merge order <key>" -m "Owner-Approved: <key>"`<br>The trailer lets the merge commit carry the order document onto `main` through AM2-AC3 (b); git runs the commit-msg hook on a merge commit `[MEASURED: scratch repo, core.hooksPath with a commit-msg that exits 1 → git merge --no-ff refused, "Not committing merge"; git 2.39.5]`. The owner does not re-run the gate: the banner above is the `merge` entry's GREEN record. With no GREEN `merge` entry the section says `not ready: no GREEN merge under this order`, and prints no owner command. It appends one `kind: close-order` log entry. **Refused:** any entry under the order lacking a reverse action; a second `close-order` for the same key (the log already holds one). | tests/framework/test_delegate.py |
| AM2-AC5 | A-AC3, A-AC4, J-AC3 | R40, R41, R3, R4 **RED-FIRST** | Given an active order `<key>` with slug `<s>`, When `autonomy.py approve-under <doc> --order <key>` runs, Then it flips the status line to Approved, adds the approval key line and `Approved-under: order <key>`, adds `approved under order <key> (assistant)` to `## Approval history`, and appends one `approval` entry to the log (no hash chain). No registry line is written. It refuses, naming its reason, when any of these holds:<br>(a) the key is not a `kind: order` registry entry; (b) the order has expired; (c) the order has a revocation entry;<br>(d) **the order document is not committed at HEAD, or its task text's SHA-256 differs from the entry's `task_sha256`** (AM1-ADR-4) → `order document not committed as issued`. The hashed bytes are pinned: `delegate.sh` refuses a task argument containing a newline (exit 2, `the task is one line — point to a PRD for more`); `order.md` holds it on one line `Task: <text>`, verbatim; `task_sha256` is the SHA-256 of the UTF-8 bytes of `<text>` exactly as given, with no trimming or normalisation, and `approve-under` hashes the committed line's bytes after `Task: ` up to (not including) the line end. **Green case (also J-AC1's):** `delegate.sh "  task with spaces  " …`, the owner commits with the order's trailer, then `approve-under` on `SPEC-<s>.md` succeeds;<br>(e) the document's filename lacks `<s>`, or its kind is not granted: `PRD-` needs `prd`, `SPEC-`/`DESIGN-` need `spec`, `QA-`/`REVIEW-` need `qa`; any other document → `outside the order — stop and ask (R42)`;<br>(f) the document touches AH2, AH3, AH4, AH5 or AH-UNSURE; or AH1 when the order lacks `business-rules-in-task`;<br>(g) the document is the order document itself, or `scripts/autonomy.json`;<br>(h) the current branch is protected (F-AC1, `work under autonomy happens on a branch or worktree`).<br>`verify_approvals.py` fails a hand-forged stamp for each of (a)–(g). The red-first case is (d): an order entry naming a document that is not committed. | tests/framework/test_autonomy_approve.py, tests/hooks/test_verify_approvals.py |
| AM2-AC6 | A-AC5 (3), A-AC7 (spawn half) | R3, R5 **RED-FIRST** | Given an engineer brief that names an owner-approved spec **and** a document carrying `Approved-under: order <key>` that fails the shared validator (no log entry, revoked order, expired order), When `guard_agent_spawn.py` runs, Then it exits 2 naming that document and the validator's reason. A brief naming only owner-approved documents behaves exactly as today (A-AC8). The red-first case: a brief naming the approved parent spec plus a revoked-order spec exits 0 today `[MEASURED analogue: the missing-spec probe in finding 3, rc=0]`. | tests/hooks/test_guard_agent_spawn.py |
| AM2-AC7 | J-AC1, A-AC7 | R39, R5 (am1 obligation) | `scripts/delegate.sh --help`, `scripts/delegate.sh -h`, `scripts/delegate.sh "t" --by o --help`, and the same three for `scripts/revoke.sh`, each exit 0 with the registry file byte-identical and `git status` unchanged. `guard_bash.py` allows each of them in a plain project and under the order fixture (B-AC10's reader rule). | tests/hooks/test_approve_script.py, tests/hooks/test_guard_always_human.py |
| AM2-AC8 | — (enabler for A-AC3, J-AC3, J-AC5, J-AC7, AM2-AC1, AM2-AC2) | R40 **RED-FIRST** | Under the order fixture, `guard_bash.py` exits 0 for `python3 scripts/autonomy.py <sub> …` for each row-5 agent subcommand: `log`, `verify-log`, `approve-under`, `ask`, `merge-record`, `close-order`. Each is added to `AGENT_SUBCOMMANDS` in the increment that ships it, not before. An undefined subcommand (for example `autonomy.py grant …`) stays refused as AH5. Red today: `approve-under` and `close-order` exit 2 `[MEASURED: finding 4]`. | tests/hooks/test_guard_always_human.py |

**Clarification, no new machinery: J-AC5's "answered".** While increment D is parked, an `ask` counts as answered when a later log entry has `kind: answer` and `target: <ask id>`. The coordinator writes that entry with `autonomy.py log` when it relays the owner's reply. That entry's `reverse` is `none: <reason>`.

## Declared limits (added to am1's list)

| # | Limit | Backstop |
|---|---|---|
| D-L11 | The append-only commit carve-out (AM2-AC3 a) accepts any appended line, including one the agent wrote by a route the guard does not see (am1 D-L10 writers). | A forged `approval` entry can only support a stamp that `verify_approvals.py` still checks against a live owner order, its grants and its document (AM2-AC5). CI's `verify-log --append-only` catches edits to earlier lines. |
| D-L12 | Before the owner commits a new order document, the agent could write different text at that path. | AM2-AC5 (d) compares the committed task text with the owner's `task_sha256`, which the agent cannot write. |
| D-L13 | Under an order, a plain `git merge` into a non-protected working branch is not gated; a RED or NOT RUN merge gate refuses only the `merge` log entry. | Nothing reaches `main` without the owner's command, which AM2-AC4 prints only after a GREEN `merge` entry; `main` stays AH3-protected. |

## Row-5 increment plan (for the coordinator to brief one at a time)

Each increment is small enough for one engineer brief, ends with its own reviewer and QA, and leaves `main`'s behaviour unchanged for projects that have not opted in (A-AC8).

| # | Increment | ACs | Needs | Notes |
|---|---|---|---|---|
| 1 | **F1: protected-branch commits** | F-AC1 (the `git commit` half) | — | **`guard_bash.py` only**, as the approved F-AC1 row names: the agent's `git commit` on a protected branch is refused while autonomy is active. Do **not** add the rule to `check_commit`: commit-msg also runs for the owner and on merge commits `[MEASURED: see AM2-AC4]`, so it would refuse the owner's own commit of an order document on `main` and the owner's merge command. The `approve-under` half lands in 4. |
| 2 | **Log** | AM2-AC2 (replaces C-AC1/C-AC2 for row 5), F-AC2, AM2-AC3 (a), AM2-AC8 for `log`, `verify-log` | 1 | Ships the commit carve-out **with** the first writer, or the first log commit is refused. CI step in both YAML files. |
| 3 | **Registry and owner commands** | A-AC10, A-AC9, J-AC1, J-AC2, AM2-AC3 (b), AM2-AC7, A-AC7 (registry half: `revoke.sh` writes the revocation entry) | 2 | Shared writer in `approve.py`; `delegate.sh`, `revoke.sh`. A-AC6 (c) is re-run, not built. |
| 4 | **Approve under an order** | AM2-AC5 (= A-AC3, A-AC4 (a)(b)(c)(f)(g), J-AC3 under an order, F-AC1's `approve-under` half), A-AC5 (1) and (2), AM2-AC6 (= A-AC5 (3), A-AC7 spawn half), A-AC7 (`approve-under` and verify halves), A-AC8, AM2-AC8 for `approve-under` | 3 | The shared validator `autonomy.validate_approval` (ADR-3) with the order basis only; the mandate basis waits for A-AC1. CI gate 1 changes in both YAML files identically. |
| 5 | **Order lifecycle** | J-AC4, J-AC5, AM2-AC1 (= J-AC6), AM2-AC4 (= J-AC7), AM2-AC8 for `ask`, `merge-record`, `close-order` | 4 | J-AC4 is mostly test cases over guards that exist (deploy grants are new). |
| 6 | **Rule text** | G-AC1 (order wording only, exception (b)), G-AC2 | 5 | Text last, so it describes what shipped. Uses the refreshed location list below. |

Coordinator note: increments 1–3 change no agent's day-to-day behaviour in a project without `scripts/autonomy.json`, except that the owner gains `delegate.sh` and `revoke.sh`.

## Affected tests / affected files

**How this list was built:**
- `grep -n "^def \|AGENT_SUBCOMMANDS\|PROTECTED_PATHS\|_AUTHORITY_DIRS" scripts/autonomy.py`, and reads of `_authority`, `check_commit`, `_owner_approves`, `_is_opt_in`, `classify_artifact` (autonomy.py:826-1103).
- Reads of `.claude/hooks/guard_agent_spawn.py:279-382`, `scripts/verify-merge.sh:1-200`, `ci-examples/github-actions.yml:50-80`, `grep -n "def \|DOC_DIRS" scripts/approve.py scripts/verify_approvals.py`.
- `grep -rn "work under autonomy happens\|reverse: missing\|approve-under\|approve_under" scripts .claude/hooks tests --include='*.py'` → no match (F-AC1, F-AC2 and `approve-under` are not built) `[MEASURED]`.
- `grep -rln "delegate.sh\|revoke.sh" tests/` → `tests/framework/test_autonomy_items.py`, `tests/hooks/test_guard_always_human.py`, `tests/hooks/test_guard_autonomy_paths.py` `[MEASURED]`.
- `ls tests/framework tests/hooks | grep -i "autonomy\|always\|decision\|delegate"` for the existing B test files `[MEASURED]`.
- The two R27 greps re-run as quoted in finding 3.

| File | Why it is affected | Expected change | Inc. |
|---|---|---|---|
| `scripts/autonomy.py` | Holds the guard rules, `check_commit` and the CLI | F-AC1 rule; `log`, `verify-log`, `approve-under`, `ask`, `merge-record`, `close-order`; `AGENT_SUBCOMMANDS` grows per increment; `check_commit` carve-outs (AM2-AC3); `validate_approval` (order basis) | 1–5 |
| `scripts/approve.py` | Shared registry writer (A-AC9, A-AC10) | `-rN` keys; `kind` field; writer used by the wrappers; refuses a document with `Approved-under:` | 3 |
| `scripts/delegate.sh`, `scripts/revoke.sh` **(new)** | Owner commands | Thin wrappers (ADR-13); `--help`/`-h` (AM2-AC7) | 3 |
| `scripts/verify_approvals.py` | Resolves stamps | `Approved-under: order` through the shared validator; `DOC_DIRS` += `doc/orders` | 4 |
| `.claude/hooks/guard_agent_spawn.py` | Engineer upstream check | AM2-AC6: a failing stamped document blocks | 4 |
| `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml` | Gate 1 and the new log step | Identical edits in both | 2, 4 |
| `doc/templates/order.md`, `doc/templates/order-report.md` **(new)** | J-AC1, AM2-AC4 | — | 3, 5 |
| `doc/orders/`, `doc/decisions/`, `doc/reports/` **(new directories, data)** | Order documents, the log, order reports | — | 2–5 |
| `scripts/verify-fast.sh` | Routing lines for new scripts and tests | `case` lines | each |
| `tests/framework/test_decision_log.py`, `test_autonomy_approve.py`, `test_delegate.py` **(new)** | AM2-AC1, -AC2, -AC4, -AC5, J-AC1/2/5 | — | 2–5 |
| `tests/framework/test_commit_msg_owner_trailer.py` | Pins am1's opt-in carve-out | New AM2-AC3 cases; existing cases must stay green | 2, 3 |
| `tests/framework/test_regression_commit_msg_autonomy.py`, `tests/framework/test_pre_commit.py` | Pin the commit check | Unchanged, must stay green (the carve-outs touch only the log and an added order document) `[MEASURED: grep -n "decision-log\|doc/orders" on both files → no match]` | 2, 3 |
| `tests/hooks/test_guard_always_human.py`, `test_regression_always_human_bypasses.py`, `test_regression_autonomy_rework_bypasses.py`, `test_autonomy_stdlib_shadowing.py`, `test_guard_always_human_rework.py` | Pin the B guard | New cases for F-AC1, AM2-AC7, AM2-AC8; the rest unchanged and green. The one case asserting an undefined subcommand is refused uses `grant` (test_guard_always_human.py:239), which row 5 does not add `[MEASURED: grep -n "autonomy.py [a-z]" over the three guard test files, excluding items/status/check-commit]` | 1–5 |
| `tests/hooks/test_guard_agent_spawn.py` | Engineer and QA spawn gates | New AM2-AC6 cases; existing cases unchanged | 4 |
| `tests/hooks/test_approve_script.py`, `tests/hooks/test_verify_approvals.py` | Registry writer and resolution | New cases (A-AC9, A-AC10, AM2-AC5, AM2-AC7) | 3, 4 |
| `tests/ci/test_ci_examples.py` | Gate 1 is byte-identical in both files | New cases; still byte-identical | 2, 4 |
| `tests/framework/test_neutrality.py`, `tests/framework/test_bootstrapped_project.py` | New core files must be neutral and work in a bootstrapped copy with no `scripts/autonomy.json` | Unchanged, must stay green | all |
| `AGENTS.md`, `.agents/skills/handoff-protocol/SKILL.md`, `.agents/skills/coordinator-discipline/SKILL.md`, `.claude/agents/{pm,ba-sa,ai-engineer,frontend-engineer,qa,frontend-qa}.md`, `doc/framework/{SETUP,WHY,ADAPTERS,COORDINATOR-CONSTITUTION,NORTH-STAR}.md` | G-AC1/G-AC2 text | Order wording only | 6 |
| `tests/framework/test_doc_contracts.py` | G-AC1/G-AC2 contracts | New cases (J is committed, so the approved spec's "wait" note no longer applies) | 6 |

**Refreshed R27 location list (for G-AC2, increment 6).** AGENTS.md:31 and :39 (§0, new), :93–95 (§5 tier table and 👤 path), :114–115 (§6.1, §6.2); `handoff-protocol/SKILL.md`: 13, 18, 40, 44–47; `coordinator-discipline/SKILL.md:174`; `pm.md:31`; `ai-engineer.md`: 15 and 46; `frontend-engineer.md`: 31 and 47; `qa.md`: 15 and 33; `frontend-qa.md`: 15 and 35; plus the `doc/framework/` files listed above. Line numbers are as of `96bebdb`; re-grep before editing.

**Not touched:** the approved spec, design, PRD and am1; `scripts/verify-merge.sh` (used as is); `doc/tasks/backlog.md` (pm owns it); `doc/memory/` (owner rulings; see AM2-ADR-5).

## Decisions (ADR-style)

- **AM2-ADR-1: an order's `merge` goes into a working branch, never a protected one.**
  - **Context:** finding 1. The guard already refuses `main`; J-AC6's silence would have pushed an engineer to add a grant exception to AH3.
  - **Decision:** `merge-record` refuses a protected target; the order report hands the owner one command for `main`.
  - **Consequences:** No signed-approval question arises (ease-of-use point 3 stays untriggered). Extending orders to `main` is a later owner decision, with its own PRD change.
  - **For the owner to review — this narrows what "a RED record refuses the merge" meant.** The approved J-AC6 reads as if a red gate stops the merge itself. Under this amendment a red gate stops the `merge` log entry and the `Ready for main` hand-over, but a plain `git merge` between working branches is not intercepted (D-L13). Gating every `git merge` would mean the guard running the merge gate on each call, which the ease-of-use ruling argues against. What matters to the owner, reaching `main`, stays fully gated. The `merge` grant is also inert in any project that has not configured `VERIFY_MERGE_GATE`.
- **AM2-ADR-2: a plain append-only log, no hash chain, in row 5.** Finding 2. Consequences: C-AC1's `prev` and C-AC2's chain half return with increment C if it is un-parked, as an additive change (a new field on new lines); the design's anchoring waits with it.
- **AM2-ADR-3: the commit check clears J's own outputs narrowly.** Only appended log lines, and only an *added* order document that the owner's trailer-named entry points to. The rest of am1's rule is unchanged. Consequences: D-L11 and D-L12 are declared.
- **AM2-ADR-4: an order's grants are checked by document kind, not by the mandate class vocabulary.** The design's class vocabulary (`tier-0` … `merge`) and the order grants (`prd`, `spec`, …) do not share terms, so "class inside grants" had no defined test `[INFERRED: design §J and ADR-9 read side by side; autonomy.py CLASSES at :822]`. Consequences: an order covers its task whatever its tier, which is R40's intent; the AH checks still apply.
- **AM2-ADR-5 (for human review): the 2026-10-22 ruling and approval under an order.** `doc/memory/jarvis-decides-self-improvement.md` says flipping a document to `Approved` stays human via `approve.sh`. Under an order, `approve-under` flips `Approved`, tracing to the owner's order (R25). That is consistent with the approved PRD, but the memory text will read as contradicted once row 5 ships. Recommendation: when increment 6 lands, the owner adds one line to that memory: "or by `approve-under` inside an order the owner issued". Only the owner changes a memory ruling.

## Traceability

| PRD requirement | Criteria (this amendment) |
|---|---|
| R3 | AM2-AC5, AM2-AC6 |
| R4 | AM2-AC5 |
| R5 | AM2-AC6, AM2-AC7 |
| R9 | AM2-AC3 |
| R11 | AM2-AC2, AM2-AC3 |
| R24 | AM2-AC2, AM2-AC4 |
| R39 | AM2-AC3, AM2-AC7 |
| R40 | AM2-AC5, AM2-AC8 |
| R41 | AM2-AC1, AM2-AC5 |
| R43 | AM2-AC1 |
| R44 | AM2-AC4 |

This amendment has 8 criteria, AM2-AC1 to AM2-AC8 `[MEASURED: grep -c '^| AM2-AC' on this file → 8]`. They amend 9 approved criteria: J-AC6 (→ AM2-AC1); C-AC1 and C-AC2 for row 5 (→ AM2-AC2); am1's B-AC7 (→ AM2-AC3, carve-outs added); J-AC7 (→ AM2-AC4); A-AC3, A-AC4 and J-AC3 under an order (→ AM2-AC5); A-AC5 (3) with A-AC7's spawn half (→ AM2-AC6). AM2-AC7 and AM2-AC8 are new. 11 PRD requirements map to the 8 criteria. Every other row-5 criterion (F-AC1, F-AC2, A-AC5 (1)(2), A-AC6 (c), A-AC7 (other halves), A-AC8, A-AC9, A-AC10, J-AC1, J-AC2, J-AC4, J-AC5, G-AC1, G-AC2) is unchanged.

## Approval history

- **2026-10-22 — approved (human).** Registry key `spec-delegated-autonomy-am2-task-orders-scope-2026-10-22`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-22 — drafted.** ba-sa, an impact check of the approved spec against the changes since 2026-10-20: am1, the QA-gate `Spec:` line (`0cc9c6c`), the Tier 0 one-round rule, and the owner ruling of 2026-10-22. Built at `96bebdb` with probes in a throwaway order fixture. Written as a separate amendment so that the approved spec and design stay unchanged.
