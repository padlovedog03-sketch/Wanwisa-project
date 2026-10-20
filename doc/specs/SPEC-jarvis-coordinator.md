# SPEC: Jarvis coordinator — Increment 1 (R1–R8): every message goes to Jarvis, duties applied

Status: In Review
Owner: ba-sa
Upstream: doc/requirements/PRD-jarvis-coordinator.md (Approved, registry key `prd-jarvis-coordinator-2026-10-20`) · owner context in the ba-sa brief of 2026-10-20: D5 = the R5 split as written; D6 = spec both paths (main-thread `agent` setting primary, UserPromptSubmit injection fallback), selected by a measured probe
Date: 2026-10-20

## Overview

When this ships, a session of the primary adapter opened in the repo with no flags runs its main thread as the `jarvis` agent definition. That definition is a pointer to AGENTS.md §0, which states the coordinator duties of R3–R8 in tool-neutral words. A fallback hook injects the same pointer whenever the main thread runs with no named agent. The existing spawn guard gains two checks: it refuses a role-agent brief with no filled `Tier:` or `Files:` line, and it refuses a spawn of `jarvis` itself. One cheap pre-check, `coordinator_lint.py --approve-ready <slug>`, confirms that a document is committed and `In Review` before Jarvis hands the owner an `approve.sh` command. Everything else is self-report, declared as LIMIT lines in ADAPTERS.md.

Out of this increment: the scorecard (R9–R10), task orders (R11), setup and report shape (R12–R13), automatic tier classification, and any check that reads a brief's meaning.

## Probe results (R1 a–d) — run before this spec was written

All probes ran in a throwaway git repo under the session scratch directory (`<scratch>/probe`). The repo held:
- `CLAUDE.md` = `@AGENTS.md`;
- an `AGENTS.md` whose only content is a secret word;
- `.claude/agents/jtest.md` (coordinator stand-in, **no `tools:` line**) and `.claude/agents/roleb.md`;
- a skill `.claude/skills/probe-skill`;
- `.claude/settings.json` with `"agent": "jtest"` and a logging hook on SessionStart, UserPromptSubmit and PreToolUse(Agent). The hook writes each payload's `hook_event_name`, `subagent_type` and `agent_type` to `hook.log`. On UserPromptSubmit it prints a code word.

This repo's `.claude/settings.json` was not touched. CLI: `claude --version` → `2.1.304 (Claude Code)`. The `-p` probes used `--model sonnet --dangerously-skip-permissions`. Hooks fired under that permission mode, which may not be the owner's (it does not change hook loading [INFERRED]).

| # | Question | Result | Evidence |
|---|---|---|---|
| P1 | Does a main-thread agent load project hooks? | **Yes [MEASURED]** | Run1 (`claude -p … --output-format stream-json --verbose "<5 questions>"`) wrote `hook.log`: `{"event": "SessionStart", "agent_type": "jtest"}`, `{"event": "UserPromptSubmit", "agent_type": "jtest"}`, `{"event": "PreToolUse", "tool": "Agent", "sub": "roleb", "agent_type": "jtest"}` |
| P2 | Can it spawn other subagent types (Agent tool)? | **Yes [MEASURED]**, for a definition with no `tools:` line | Run1 result line 5: `Roleb reply: ROLEB-ALIVE`. Untested for a definition that restricts `tools:`, so JC-AC1 forbids a restricting line |
| P3 | Does it get CLAUDE.md → AGENTS.md? | **Yes [MEASURED]** | Run1 result line 2: `PINEAPPLE-42`, a word that exists only in the probe's AGENTS.md |
| P4 | Do skills load? | **Yes [MEASURED]** | Run1 `system/init` `skills` list begins `['probe-skill', …]`; result line 4: `MANGO-7`, a word that exists only in that skill |
| P5 (R1 c) | Is the coordinator definition also a dispatchable subagent? | **Yes — R1(c) FAILS as written [MEASURED]** | Run1 init `agents` list contains `'jtest'`. Run3 (`claude -p … "Spawn the jtest subagent…"`) returned `JTEST-COORDINATOR`, `No error.` |
| P6 | Can a PreToolUse(Agent) hook refuse that spawn? | **Yes [MEASURED]** | Run5, with the log hook exiting 2 for `subagent_type == "jtest"`: `PreToolUse:Agent hook error: […]: BLOCKED: the coordinator is not a role agent`, `No subagent output.` |
| P7 (R1 d) | Does the default carry into non-interactive (`-p`) sessions? | **Yes [MEASURED]** | Run1 hook log `agent_type: "jtest"` with no `--agent` flag |
| P8 | Does it carry into an interactive session with no flags? | **Yes [MEASURED]** | `expect` drove `claude --model sonnet` in a sized pty: accept the trust dialog (Down, Enter), type `Reply with your identity marker only.` The script printed `SAW-MARKER` (the reply contained `JTEST-COORDINATOR`), and `hook.log` held `SessionStart` and `UserPromptSubmit` with `agent_type: "jtest"` |
| P9 (R1 d) | Remote-control sessions? | **INFERRED, unproven** | Not measured: needs a remote-control session the probe cannot open. Settled by one remote-control session in the repo, asked for its identity. Per R1 it is deferred to a LIMIT line (JC-L8) |
| P10 | `--agent X` versus the setting | **Flag wins [MEASURED]** | Run2 `claude -p --agent roleb "what is your identity"` → `ROLEB-ALIVE`; log `agent_type: "roleb"` |
| P11 | `.claude/settings.local.json` `{"agent":"roleb"}` versus project `jtest` | **Local wins [MEASURED]** | Run4 → `ROLEB-ALIVE`; log `agent_type: "roleb"` |
| P12 | Fallback: no `agent` setting, UserPromptSubmit stdout | **Injected and read [MEASURED]** | Run6 (key removed) → `1) KIWI-9`, `2) PINEAPPLE-42`; log `agent_type: null` on both events |
| P13 | Does a spawned subagent fire UserPromptSubmit? | **No [MEASURED]** | Run1 log has exactly three events. The `roleb` spawn added no UserPromptSubmit line |

**Path selection (D6).**
- P1–P4, P7 and P8 pass, so the **primary path** (the `agent` setting) carries R1.
- P5 fails. The proposed mitigation is P6: the spawn guard refuses `jarvis`. This is owner decision **O1** below, because R1 says a failing (c) comes back to the owner.
- The **fallback hook** is built in either case. It injects only when the payload's `agent_type` is empty (P12). So:
  - while the primary path works, it does nothing (`agent_type: "jarvis"`);
  - it takes over automatically when the setting is absent or overridden to nothing.
- If the owner rejects O1, the engineer removes the `agent` key and keeps `jarvis.md` as the pointer source only. The fallback then carries R1 alone. No other file changes. (`jarvis.md` would still appear as a subagent, and the JC-AC3 guard still refuses it.)

**The engineer re-runs P1–P5, P8 and P12 at implementation time** against the CLI version then installed, using the procedure above, and pastes the results in the handback (JC-AC5). If a result differs from this table, the engineer stops and reports. The engineer does not choose a path.

## Acceptance Criteria

Test files are new unless noted. "Exit 2" means block with stderr shown to the model; exit 0 means allow.

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| JC-AC1 | R1 | **Given** the committed `.claude/settings.json`, **When** the test parses it, **Then** `agent` equals exactly `"jarvis"`, and `.claude/agents/jarvis.md` exists. Its frontmatter `name:` is exactly `jarvis`. It has no `tools:` line, or one that lists `Agent` (P2 is proven only without a restriction). **Hostile, each red with a message naming the defect:** the `agent` key removed; the value `"Jarvis"`, `"jarvis "` or `"jarvis​"`; `jarvis.md` renamed or missing; `name:` different from the setting; a `tools:` line without `Agent`; `settings.json` not valid JSON. Each is checked by running the same assertion helper against a planted copy under `tmp_path`, never against an edited repo file. | tests/hooks/test_jarvis_entry.py |
| JC-AC2 | R1, R2 | **Given** `.claude/agents/jarvis.md`, **When** the test reads the body below the frontmatter, **Then** it names `AGENTS.md` and is at most 600 characters, so it holds a pointer and no rule. It contains none of the R14 patterns (the existing R14 test already scans `.claude/agents`). It contains no `<UPPER_CASE>` placeholder that `bootstrap.sh` would rewrite. **Hostile:** a planted body of 601 characters, or a body without `AGENTS.md`, is red. | tests/hooks/test_jarvis_entry.py |
| JC-AC3 | R1 (c), mitigation O1 | **Given** a PreToolUse payload `{"tool_name":"Agent","tool_input":{"subagent_type": T}}`, **When** `.claude/hooks/guard_agent_spawn.py` runs, **Then** it exits 2 with `Jarvis is the main thread, not a role agent` for every T that equals `jarvis` after NFKC, removal of whitespace and format (Cf) characters, and casefold: `jarvis`, `Jarvis`, ` jarvis `, `jar​vis`, `ｊａｒｖｉｓ`. This check runs first, before any other. **Unchanged:** `jarvis-helper`, `general-purpose`, `Explore` and every other type are not affected by this check. | tests/hooks/test_guard_agent_spawn.py (existing, new cases) |
| JC-AC4 | R1, D6 fallback | **Given** `.claude/hooks/inject_jarvis.py` registered under `UserPromptSubmit` in `.claude/settings.json`, **When** it receives a payload, **Then**: (a) `agent_type` is absent, `null` or `""` → exit 0, and stdout is exactly the body of `.claude/agents/jarvis.md` below its frontmatter; (b) `agent_type` is `"jarvis"` (same normalisation as JC-AC3) → exit 0, empty stdout; (c) `agent_type` names any other agent → exit 0, empty stdout (a deliberately chosen agent is left alone, PRD A3; owner decision O2). **Hostile:** malformed JSON, empty stdin or a JSON array → exit 0, empty stdout, no traceback; `jarvis.md` missing or not UTF-8 (planted in a tmp copy of the hook's tree) → exit 0, empty stdout, no traceback; the hook's entry removed from `settings.json` → the registration test is red. | tests/hooks/test_jarvis_entry.py |
| JC-AC5 | R1 (a)–(d), D6 selection | **Given** the CLI installed at implementation time, **When** the engineer re-runs probes P1–P5, P8 and P12 with the procedure in "Probe results", **Then** the handback quotes each result line. If P1–P4 or P8 fail, the engineer stops and reports to the owner without choosing a path. The probe runs in a scratch repo and never edits this repo's settings. Not automated: it needs a live model session, so it is run once per implementation and re-run when the adapter's major version changes (JC-L8). | handback evidence (manual probe) |
| JC-AC6 | R4, R6 | **Given** an Agent payload whose `subagent_type` is one of the role agents `pm`, `ba-sa`, `ai-engineer`, `frontend-engineer`, `reviewer`, `qa`, `frontend-qa`, **When** the guard runs, **Then** it exits 2 unless the prompt has both lines below. Each line may be plain, bulleted (`-`, `*`, `1.`), bold (`**Tier:**`) or indented, as the existing `_FIELD_LINE` reads it, after NFKC normalisation of the prompt. (1) A `Tier:` line whose value, with `*` and whitespace stripped, starts with `0`, `1` or `2`. (2) A `Files:` line whose value is non-empty and does not start with `<`. The message names every missing or unfilled line (`Tier:`, `Files:` or both) and shows the expected form `Tier: <0|1|2> — <reason>` / `Files: <paths>`. This check runs after JC-AC3 and before the spec gate and the review gate. **Hostile, each exit 2 naming the line:** no `Tier:` line; `Tier:` empty; `Tier: <0|1|2>`; `Tier: high`; `Tier` only mid-sentence ("set the Tier: 1 line"); `Ti​er: 1`; lowercase `tier: 1`; `Files:` empty; `Files: <paths>`; a prompt that carries `NO_SPEC_BUGFIX: <repro>` but no `Tier:` (the override never opens this check). **Accepted:** `Tier：1 — x` (full-width colon, NFKC); `**Tier:** 2 — x`; `- Files: a.py`. **Never checked:** `Explore`, `Plan`, `general-purpose`, `claude-code-guide`, an unknown type, an empty type. **Unchanged:** malformed payload → exit 0; a non-Agent tool → exit 0. | tests/hooks/test_guard_agent_spawn.py (existing, new cases) |
| JC-AC7 | R6 (existing gates unchanged) | **Given** the two existing spawn-guard suites, **When** each `_run_gate` helper appends `"\nTier: 1 — test\nFiles: x"` to the prompt it sends (one line changed per file, nothing else), **Then** all 124 existing tests in `tests/hooks/test_guard_agent_spawn.py`, `tests/hooks/test_regression_guard_agent_spawn_review.py` and `tests/hooks/test_regression_autonomy_rework_bypasses.py` pass, and `python3 -m pytest tests/hooks -q -p no:cacheprovider` is green. | the three existing files |
| JC-AC8 | R2, R3, R4, R5, R7, R8 | **Given** AGENTS.md, **When** the test reads §0, **Then** §0 states that Jarvis is the coordinator (the main thread that receives every owner message), not only a voice. It carries these anchors, each checked by exact substring: `Tier: <0|1|2>` (R3, with "first reply" and "higher tier when unsure"); the brief lines `Tier:`, `Files:`, `Verify with:` and `REWORK:` (R4); a two-column table whose header cells are `Jarvis ตัดสินเอง` and `เจ้าของงานตัดสินเท่านั้น`, with the R5 items exactly as listed in the PRD (D5); the end-of-task report fields, including `Parked:` (R7); and `mechanism:` with `doc/memory/` (R8). §5 states that every brief to a role agent carries `Tier:` and `Files:` and is refused where the adapter intercepts. **Hostile:** each anchor removed from a planted copy of AGENTS.md → red, naming the anchor. `python3 scripts/check_neutrality.py` → `0 provider name(s)` (§0 names no tool, setting or hook). | tests/framework/test_doc_contracts_jarvis.py |
| JC-AC9 | R2, R6 | **Given** `doc/framework/ADAPTERS.md`, **When** the test reads it, **Then** section ก has a "coordinator entry" row naming the `agent` setting, `.claude/agents/jarvis.md` and `.claude/hooks/inject_jarvis.py`. Section ข has a row saying the rules are read from AGENTS.md and nothing is intercepted. Each of JC-L1 … JC-L10 (below) appears once, by its id. **Hostile:** a planted copy missing any id or either row → red, naming it. | tests/framework/test_doc_contracts_jarvis.py |
| JC-AC10 | R8 | **Given** the repo at handoff, **When** `python3 scripts/memory_lint.py` and `python3 scripts/correction_rate.py --brief` run, **Then** the first prints `0 problem(s)`, and the second's lessons-with-no-mechanism figure is `0` (M7). Baseline [MEASURED 2026-10-20]: `memory: 0 problem(s) …` and `… · 0 lesson(s) since 2026-10-08 with no mechanism`. | command output in the handback |
| JC-AC11 | owner slip 2026-10-20 (approve.sh refused an uncommitted PRD) | **Given** `python3 scripts/coordinator_lint.py --approve-ready <slug> [<slug>…]`, **When** it runs in a git repo, **Then** it resolves documents the way `approve.py` does: tracked files under `doc/`, whose filename contains the slug, case-insensitive. It exits 0 and prints `scripts/approve.sh <slug…> --by <name>` only when every resolved document (a) exists in `HEAD` (`git cat-file -e HEAD:<path>`), (b) has no staged or unstaged change against `HEAD` (`git diff --quiet HEAD -- <path>`), and (c) has exactly one `Status: In Review` line. Otherwise it exits 1, with one line per problem: `no tracked document matches '<slug>' — git add and commit it`; `<path>: not committed — commit before handing over approve.sh`; `<path>: uncommitted changes — commit before handing over approve.sh`; `<path>: Status is '<x>', approve.sh accepts only In Review`. **Hostile:** untracked file; staged-only file; committed then edited; committed then edited and staged; a slug matching 0 documents; a slug matching 2 documents where one is dirty (whole batch exit 1, like approve.py); no slug, or an empty or whitespace slug → exit 2 with usage; run outside a git work tree, or with git missing from PATH → exit 2 with a one-line message and no traceback. The existing lint modes are unchanged (the 41 existing tests stay green). Each case runs in a `tmp_path` git repo: the function takes the repo root as a parameter, and `approve.py` is not imported or changed (PRD out of scope: the approval mechanism). | tests/coordinator/test_coordinator_lint.py (existing, new cases) |
| JC-AC12 | R2, all | **When** `python3 -m pytest tests/framework/test_doc_contracts.py -q -p no:cacheprovider`, `python3 scripts/check_neutrality.py` and `python3 -m pytest tests/hooks tests/coordinator tests/framework -q -p no:cacheprovider` run, **Then** all are green. | existing |

## Declared LIMIT lines (self-reported duties) — ready for ADAPTERS.md

Each line is pasted as-is (the id first) into ADAPTERS.md section ก, except JC-L10, which goes in section ข. Per scope-discipline rule 5, the checks catch forgetting, not a deliberately false line.

- **JC-L1** — The `Tier:` line in Jarvis's first reply is self-reported; nothing reads Jarvis's replies.
- **JC-L2** — After the tier, the §5 route order is checked only at the engineer spawn (Approved spec) and the QA spawn (independent PASS review); every other step, and ending the turn at tier-2 gates, is self-reported.
- **JC-L3** — In a brief, only the presence of a filled `Tier:` and `Files:` line is checked, never truth; `Verify with:`, the threat-model sentence for reviewer and QA, and the `REWORK:` prefix are self-reported.
- **JC-L4** — The R5 split (what Jarvis decides, what goes to the owner) is self-reported; a ruling Jarvis made that was the owner's shows only in the end-of-task report.
- **JC-L5** — Staying silent until the task ends (R7) is self-reported; it is measured afterwards by M1 (Increment 2), not prevented.
- **JC-L6** — Recording a lesson after an owner correction (R8) is self-reported; `memory_lint.py` checks the format and `correction_rate.py` counts lessons with no mechanism, but nothing checks that a correction produced a lesson.
- **JC-L7** — `coordinator_lint.py --approve-ready` runs only when Jarvis runs it before handing the owner an `approve.sh` command.
- **JC-L8** — Jarvis is the default through the committed `agent` setting; a typed `--agent`, or a local or user `agent` setting, replaces it (measured on CLI 2.1.304). When the replacement is "no agent", the UserPromptSubmit hook injects the Jarvis pointer; when it names another agent, nothing does (by design, PRD A3). Remote-control sessions are unproven. Re-probe on a major CLI upgrade.
- **JC-L9** — The Jarvis definition still appears in the subagent list (measured); the spawn guard refuses to dispatch it.
- **JC-L10** (section ข) — Other adapters read Jarvis's duties from AGENTS.md; nothing is intercepted, and briefs without `Tier:` or `Files:` are not refused.

## Functional Behavior

1. **Entry (R1).** `.claude/settings.json` gains `"agent": "jarvis"` and a `UserPromptSubmit` hook entry, `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/inject_jarvis.py"`. All other keys stay byte-identical, the `permissions.deny` list included (`test_settings_deny.py`).
2. **Jarvis definition (R1, R2).** `.claude/agents/jarvis.md`:
   - frontmatter `name: jarvis`, and a `description` saying it is the main-thread coordinator and not for dispatch;
   - no `tools:` line and no `model:` line;
   - a body of a few lines: "You are Jarvis, the coordinator defined in AGENTS.md §0. Follow AGENTS.md; it holds every rule." Written in the language AGENTS.md uses.
3. **Fallback injection (D6).** `inject_jarvis.py` reads stdin JSON. When `agent_type` is empty after normalisation, it prints the jarvis.md body. Otherwise it prints nothing. It always exits 0: a hook bug must not wedge every prompt, as with the existing guards.
4. **Spawn guard (R1 c, R6).** In `main()`, after the payload is parsed and the `Agent` tool is confirmed, two checks run in this order: refuse `jarvis` (JC-AC3), then the role-agent `Tier:`/`Files:` check (JC-AC6). Then the existing review gate and spec gate run, unchanged. The module docstring changes its "gating ba-sa or pm would block ordinary investigation" paragraph: role agents are now checked for brief *presence* only, and `Explore`, `Plan` and `general-purpose` stay ungated.
5. **Approve pre-check (slip).** A `--approve-ready` mode in `coordinator_lint.py`, as JC-AC11. The default `<file>|-` mode is unchanged.
6. **AGENTS.md §0** gains: the coordinator definition; tier first; the brief format; the R5 table, exactly as the PRD lists it; the end-of-task report; lessons to mechanisms; and "before handing the owner an `approve.sh` command, run `coordinator_lint.py --approve-ready <slug>`". **§5** gains one sentence on brief lines. The text is tool-neutral and in Thai, like the rest of the file.
7. **ADAPTERS.md** gains the two rows and JC-L1 … JC-L10.

## Technical Design

- **Files to create:** `.claude/agents/jarvis.md`, `.claude/hooks/inject_jarvis.py`, `tests/hooks/test_jarvis_entry.py`, `tests/framework/test_doc_contracts_jarvis.py`.
- **Files to modify:** `.claude/settings.json`, `.claude/hooks/guard_agent_spawn.py`, `scripts/coordinator_lint.py`, `AGENTS.md` (§0, one sentence in §5), `doc/framework/ADAPTERS.md`, `tests/hooks/test_guard_agent_spawn.py`, `tests/hooks/test_regression_guard_agent_spawn_review.py`, `tests/coordinator/test_coordinator_lint.py`.
- **Not modified:** `scripts/approve.py`/`approve.sh` (approval mechanism, out of scope); `.agents/skills/coordinator-discipline/SKILL.md` (R2: not rewritten); `doc/framework/SETUP.md` (a clone picks up the committed setting; setup work is Increment 4); `scripts/verify-fast.sh`.
- **Interfaces (signatures only):**
  - `guard_agent_spawn.py`:
    - `_ROLE_AGENTS: frozenset[str]` = the 7 types in JC-AC6;
    - `_COORDINATOR = "jarvis"`;
    - `_normalise_type(value: str) -> str`, reusing `_normalise_run_id`;
    - `_missing_brief_lines(prompt: str) -> list[str]`, which returns e.g. `["Tier:", "Files:"]`.
  - `inject_jarvis.py`:
    - `pointer_text(agents_dir: Path) -> str | None`;
    - `main() -> None`.
  - `coordinator_lint.py`:
    - `approve_ready(slugs: list[str], root: Path) -> tuple[int, list[str]]`, which returns an exit code and output lines;
    - `main()` routes `--approve-ready`.
- **Data:** none persisted.

## Affected tests / affected files

| File | Why it is affected | Expected change |
|---|---|---|
| `.claude/settings.json` | R1 setting and fallback registration | add `agent`, add a `UserPromptSubmit` entry |
| `.claude/agents/jarvis.md` | R1/R2 pointer definition | new |
| `.claude/hooks/inject_jarvis.py` | D6 fallback | new |
| `.claude/hooks/guard_agent_spawn.py` | JC-AC3, JC-AC6 | two checks plus a docstring paragraph |
| `scripts/coordinator_lint.py` | JC-AC11 | new `--approve-ready` mode |
| `AGENTS.md` | R2–R8 duties (§0), brief lines (§5) | edit. Verify-tiers D also edited it; that work is merged (4a209d6) and `git status --short AGENTS.md` is clean [MEASURED], so this increment edits it on top of that merge |
| `doc/framework/ADAPTERS.md` | R2 rows, JC-L1…L10 | edit |
| `tests/hooks/test_guard_agent_spawn.py` | 78 of its tests send role-agent prompts without `Tier:`/`Files:` | helper appends the header (1 line); new JC-AC3/JC-AC6 cases |
| `tests/hooks/test_regression_guard_agent_spawn_review.py` | 8 tests break, for the same reason | helper appends the header (1 line) |
| `tests/hooks/test_regression_autonomy_rework_bypasses.py` | runs hooks; its 3 tests stayed green under the prototype | unchanged, must stay green |
| `tests/coordinator/test_coordinator_lint.py` | 41 existing tests on the default mode | unchanged plus new JC-AC11 cases |
| `tests/hooks/test_jarvis_entry.py` | JC-AC1, AC2, AC4 | new |
| `tests/framework/test_doc_contracts_jarvis.py` | JC-AC8, AC9 | new. A separate file so this increment does not share `tests/framework/test_doc_contracts.py` with other in-flight increments (one owner per file) |
| `tests/framework/test_doc_contracts.py` | R14 scan covers `.claude/agents` (line 456); §5 tier-row ordering test reads AGENTS.md | unchanged, must stay green |
| `tests/framework/test_settings_deny.py` | reads `settings.json` | unchanged, must stay green |
| `tests/hooks/test_guard_bash_matrix.py`, `tests/hooks/test_stop_report_background.py` | read `settings.json` hook registration | unchanged, must stay green |
| `tests/framework/test_neutrality.py`, `scripts/check_neutrality.py` | AGENTS.md is layer 0 | unchanged, must report 0 |
| `scripts/bootstrap.sh`, `tests/framework/test_bootstrapped_project.py` | bootstrap copies `.claude` and rewrites `<UPPER>` placeholders | unchanged; jarvis.md carries no such placeholder (JC-AC2) |
| `doc/tasks/backlog.md` | row 9 status | ba-sa: status only |

How this list was built:
- `grep -rn 'claude/agents\|"agent"\|UserPromptSubmit\|settings\.json' tests scripts .githooks`;
- `grep -rln "guard_agent_spawn\|coordinator_lint\|settings.json\|\.claude/agents" tests scripts .githooks`;
- `grep -rn "claude -p\|claude --print" scripts tests .githooks` → no hits [MEASURED], so no automation in the repo starts a main-thread session that would now run as Jarvis;
- `grep -n "claude\|agents" scripts/bootstrap.sh tests/framework/test_bootstrapped_project.py`.

The breakage count is **[MEASURED]**. The repo was rsynced to `<scratch>/proto` and the JC-AC6 check was prototyped in the hook copy. Then `python3 -m pytest tests/hooks/test_guard_agent_spawn.py tests/hooks/test_regression_guard_agent_spawn_review.py tests/hooks/test_regression_autonomy_rework_bypasses.py -q -p no:cacheprovider` was run three times:
- baseline: `124 passed`;
- with the check: `86 failed, 38 passed` (78 + 8 by file);
- with the one-line helper change in each of the two files: `124 passed`.

## Decisions (ADR-style)

- **Both D6 paths coexist, keyed on `agent_type`.**
  - Context: the setting can be removed or overridden. P11 shows a local file wins, and P12 shows `agent_type` is `null` without a setting.
  - Decision: the fallback hook injects only when `agent_type` is empty.
  - Consequences: no double instructions while the primary path works [MEASURED: P1 shows `agent_type: "jtest"`]. Switching to fallback-only is a one-key change. If a future CLI renames the field, the pointer is injected twice. That is harmless and covered by the JC-L8 re-probe.
- **The pointer text has one home: jarvis.md.**
  - Context: R2 requires no rules outside AGENTS.md.
  - Decision: the fallback hook prints jarvis.md's body instead of holding its own text.
  - Consequences: one file to keep neutral and short (JC-AC2).
- **The Tier/Files check lives in the existing spawn guard**, not in a new tool (brief instruction; PRD R6).
  - It covers all 7 role agents, and only them.
  - Consequences: 86 existing tests need a one-line helper change [MEASURED]. The guard's "do not gate ba-sa/pm" rationale narrows to "do not gate investigation types".
- **The approve pre-check is a coordinator_lint mode, not an approve.py change.**
  - Context: the PRD puts the approval mechanism out of scope. approve.py checks only `git ls-files` [MEASURED: `scripts/approve.py` `validate()`], so a tracked but uncommitted or edited file passes it.
  - Decision: `--approve-ready` adds the committed-and-clean check.
  - Consequences: running it is self-reported (JC-L7). The four git states were measured in a scratch repo: untracked → 128, staged-only → 128, committed-clean → 0, committed-then-modified → 1, committed-then-staged-edit → 1 (`git cat-file -e HEAD:<p> && git diff --quiet HEAD -- <p>`).

## Increment order (D1, decided by ba-sa under the owner's ruling of 2026-10-20)

**Order: 1 → 2 → 3 → 4.** Increment 2 may run alongside Increment 3. Increment 4 starts early only while Increment 3 is blocked.

Rationale, against dependencies and the four-part definition (doc/memory/stay-on-the-definition.md):

- **Increment 1 first.** It has no dependency and makes the owner's first sentence true ("every message goes to Jarvis").
- **Increment 2 next.** It is small, report-only and unblocked. It also serves the definition's "correct" part: without its before-and-after numbers from one instrument, nobody can say whether Increment 1 worked. M2's 4-week window and M4's "must not rise" guard both start counting at Increment 1.
- **Increment 3 third.** It is the largest move on "carries work through", the selling point that lets the owner wait for the result. The merge-gate dependency is gone: VT D merged in 4a209d6 [RELAYED: coordinator message; MEASURED: `git log --oneline` shows `4a209d6 Merge branch …`]. It still waits on backlog row 4 (DA Part B, "finishing under amendment am1" [MEASURED: doc/tasks/backlog.md row 4]).
- **Increment 4 last.** It serves "easy" and "convenient for others". R12 builds on R1's entry and R13 on R7's report, both from Increment 1, so nothing else blocks it. It runs last so that M5 (≤ 15 min) is timed once, on the Jarvis that new users will actually receive, including task orders. If row 4 keeps Increment 3 blocked after Increment 2 ships, Increment 4 fills the gap rather than leaving the queue idle.

## Decisions needed from the owner

- **O1 (blocks R1 as written).** R1(c) failed: the Jarvis definition is listed as a subagent and can be spawned [MEASURED P5]. **Recommendation:** accept "listed, but every spawn refused by the guard" [MEASURED P6] as meeting (c), and declare JC-L9. Alternative: fallback only (D6), which removes the `agent` key. Jarvis then rides on an injected pointer in the bare main thread. Under that alternative, the definition would still be listed as a subagent unless it moves out of `.claude/agents/`.
- **O2.** When the owner deliberately starts another named agent (`--agent X`), the fallback leaves it alone (PRD A3). **Recommendation:** keep that.

D1–D4 do not affect this increment. D5 is applied as written in R5.

## Traceability

- R1 → JC-AC1, AC2, AC3, AC4, AC5
- R2 → JC-AC2, AC8, AC9, AC12
- R3 → JC-AC6 (`Tier:` in briefs), AC8, JC-L1, JC-L2
- R4 → JC-AC6, AC8, JC-L3
- R5 → JC-AC8, JC-L4
- R6 → JC-AC6, AC7, AC9
- R7 → JC-AC8, JC-L5
- R8 → JC-AC8, AC10, JC-L6
- Owner slip (approve.sh on an uncommitted document) → JC-AC11, JC-L7

8 requirements → 12 criteria + 10 declared LIMIT lines.

## Approval history

- **2026-10-20 — drafted.** By ba-sa, from the Approved PRD, the owner context in the brief (D5, D6), probes P1–P13 run in a scratch repo, and a prototype of the spawn check run on a scratch copy of this repo.
