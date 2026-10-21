# Review: Jarvis coordinator — Increment 1 (JC-AC1 … JC-AC12)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-jarvis-coordinator.md
Author-run: a2b6d5b03efba43ea
Reviewer-run: a15dcd429645f8a34
Date: 2026-10-20

Verdict: PASS

## Verdict: PASS

All twelve criteria hold at worktree head `91d6ef2` (commits 9278b21, 8687655, 91d6ef2 on 5cbe3b6). Every check was re-run in this review. There is no accident-class defect: no false GREEN, no crash or leak in new code, and no missing duty. One finding needs the coordinator and ba-sa, not the engineer. JC-AC6, as written, refuses an honest brief whose `Files:` paths are a bullet list under an empty `Files:` line. The engineer built it exactly as specified, so it is under "Spec-level finding" below, not rework.

## Read from

- Upstream: doc/specs/SPEC-jarvis-coordinator.md (Approved, `spec-jarvis-coordinator-2026-10-20`). PRD R1–R8 in doc/requirements/PRD-jarvis-coordinator.md, for the §0 wording check.
- Change: `git diff 5cbe3b6..HEAD` in `.claude/worktrees/agent-a2b6d5b03efba43ea`, HEAD `91d6ef2`, with `git status --short` empty.
- Threat model: .agents/skills/scope-discipline/SKILL.md rule 5, doc/memory/stay-on-the-definition.md.
- Not read: the author's conversation or handback. Every result below comes from a command run in this review.

Scratch (probes, outputs): `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/review-jc1/`

## Gate runs (this review)

- `python3 -m pytest tests/hooks tests/coordinator tests/framework -q -p no:cacheprovider` → `1813 passed, 1 skipped in 228.32s`, exit 0. The one skip is pre-existing: `tests/framework/test_doc_contracts.py:193: agent_time.REWORK_CAUSES is the source now` is also in 5cbe3b6. It is not in a new file. Confirmed with `-rs`.
- `scripts/verify-full.sh` (worktree) → exit 0:
  - `OK hooks 1283 passed`
  - `OK ci-examples 22 passed`
  - `OK coordinator 155 passed`
  - `OK framework`
  - `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. That is the template's unconfigured state, the same as in earlier reviews.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| JC-AC1 | `agent: "jarvis"`; jarvis.md, `name: jarvis`, no restricting `tools:` | PASS | Diff: `.claude/settings.json` adds only `"agent": "jarvis"` and the `UserPromptSubmit` block. jarvis.md frontmatter is `name`/`description` only. `pytest tests/hooks/test_jarvis_entry.py` is in `122 passed`, with the hostile set covered: `"Jarvis"`, a `tools:` line without Agent, renamed or missing, invalid JSON. |
| JC-AC2 | Body is a ≤600-char pointer naming AGENTS.md | PASS | The body is 2 Thai lines naming `AGENTS.md` §0 (`echo '{}' \| inject_jarvis.py` gives 114 chars of stdout). Tests `test_a_body_of_exactly_600_characters_passes` and `test_a_body_that_is_not_a_pointer_is_red` are green. |
| JC-AC3 | `jarvis` refused first, normalised | PASS | Probe `guard_probe.py`: `jarvis`, `JARVIS`, `" jarvis\n"`, `jar​vis`, full-width `ｊａｒｖｉｓ` each give exit 2 `JC-AC3: Jarvis is the main thread, not a role agent`. `jarvis-helper` gives 0. A `jarvis` brief with valid Tier/Files is still refused. The check sits first in `main()`, after the Agent-tool check. |
| JC-AC4 | Fallback hook injects only with no agent and is silent on errors | PASS | Probes of `inject_jarvis.py`. `{}`, `agent_type` null, `""`, `"  "` or `"​"` give exit 0 and print the body: it matches jarvis.md below the frontmatter, minus the final newline (`diff` shows only `\ No newline`). `jarvis`, `"Jarvis "`, `roleb` or `5` give exit 0 with empty output. `[]`, `"x"`, `null`, empty input, `not json`, or non-UTF-8 stdin bytes give exit 0 with no stdout and no stderr. In a planted tree, a missing or non-UTF-8 jarvis.md gives exit 0 with nothing printed; a CRLF jarvis.md is read correctly. With `LC_ALL=C` under `env -i`, Thai is printed with exit 0 and no stderr. Registration test is green. |
| JC-AC5 | Live probes re-run, results quoted in the handback | PASS (by version, see note) | `claude --version` → `2.1.304 (Claude Code)`, the same CLI the spec's measured P1–P13 ran on. I did not see the engineer's handback, so the quoted re-run lines are unverified here. See `Could not reach`. |
| JC-AC6 | Role-agent brief needs a filled `Tier:` and `Files:` | PASS (as specified) | `guard_probe.py`: <ul><li>**Accepted (exit 0):** `Tier: 2\nFiles: a.md, b.md`; `**Tier**: 2`; `Tier：1` (full-width colon); `Tier : 2`; CRLF line ends; `Files: none — read-only`; a NO_SPEC_BUGFIX ai-engineer brief carrying Tier/Files; this review's own brief form.</li><li>**Refused (exit 2, message names the line):** no Tier; `Tier: high`; `Tier: <0\|1\|2>`; `TIER: 2`; mid-sentence `Tier: 1`; `Ti​er`; `Files: <paths>`; an empty prompt (names both); NO_SPEC_BUGFIX without Tier.</li><li>**Not checked:** `Explore`, `general-purpose`.</li><li>**Malformed input:** empty stdin gives 0; `not json` gives 0.</li></ul>Also refused, by the spec's "`Files:` empty" case, is an empty `Files:` line with the paths listed underneath (see the spec-level finding). |
| JC-AC7 | Existing suites green with a 1-line helper change | PASS | `git diff` shows exactly one changed line in each helper (`test_guard_agent_spawn.py`, `test_regression_guard_agent_spawn_review.py`). The three files give `161 passed` (124 existing + 37 new). Mutation: in a `git archive` copy with the 5cbe3b6 guard restored, the same files give `24 failed, 137 passed`, so the new cases bite. |
| JC-AC8 | AGENTS.md §0/§5 anchors, R5 table, neutrality | PASS | Read §0 item by item against PRD R5. Jarvis column: 7 rows, each mapping 1:1 (tier upward only; role and brief; order inside an approved PRD or spec; finding in or out of the rule 5 threat model, parked if out; rework within the loop cap; park out-of-criteria findings; lesson to mechanism). Owner column: 6 rows, 1:1 (tier-2 gates; new or changed requirement, rule or number; threat model, memory ruling, §3; DA Part B list; tier downgrade; gate red after the cap). "every escalation carries a recommendation and reason" is present. R3/R4/R7/R8 duties match, and nothing is added beyond the PRD and spec FB6 (the approve-ready duty). The edit to the existing `ขอบเขต:` line ("ข้อนี้" → "ข้อ 1–5 ข้างบน") is needed so the voice-only scope line does not contradict the new duties. Accepted. `python3 scripts/check_neutrality.py` → `0 provider name(s) … 0 project leak(s)`, exit 0. |
| JC-AC9 | ADAPTERS.md rows ก/ข and JC-L1…L10 once each | PASS | Diff: the ก row names `agent`, `.claude/agents/jarvis.md` and `.claude/hooks/inject_jarvis.py`. The ข row says the duties are read from AGENTS.md and nothing is intercepted. L1–L9 are in ก, L10 in ข. `test_doc_contracts_jarvis.py` is green, including its hostile cases (missing or duplicated id, missing row). |
| JC-AC10 | memory_lint 0, no lessons without mechanism | PASS | `python3 scripts/memory_lint.py` → `memory: 0 problem(s)`, exit 0. `python3 scripts/correction_rate.py --brief` → `… · 0 lesson(s) since 2026-10-08 with no mechanism`, exit 0. |
| JC-AC11 | `--approve-ready` for committed and clean vs dirty | PASS | Scratch git repo probe: <ul><li>staged, never committed → `not committed`, exit 1</li><li>committed and clean → `scripts/approve.sh a --by <name>`, exit 0</li><li>run from a subdirectory → exit 0</li><li>upper-case slug → exit 0</li><li>file deleted in the worktree → `uncommitted changes`, exit 1</li><li>two `Status:` lines → `Status is 'In Review, Approved'`, exit 1</li><li>no status → `'(none)'`, exit 1</li><li>file outside the approvable directories → `no tracked document matches`, exit 1</li><li>slug `""`, `"  "` or none → usage, exit 2</li><li>outside a git repo → `not inside a git work tree`, exit 2</li><li>`PATH=/nonexistent` → `git not found on PATH`, exit 2</li></ul>`_APPROVABLE_DIRS` is byte-equal to `approve.py` `DOC_DIRS`, and both filter on the filename, case-insensitive, with `.md`. The default mode is unchanged (`-` still lints). The new tests are green. |
| JC-AC12 | Doc contracts, neutrality, three suites green | PASS | See Gate runs above; `check_neutrality.py` exit 0. |

## Spec-level finding (for the coordinator and ba-sa; not engineer rework)

**An honest brief is refused when `Files:` is written as a list underneath.** Repro: `{"tool_name":"Agent","tool_input":{"subagent_type":"pm","prompt":"Tier: 2 — new feature\nFiles:\n- a.md\n- b.md\n"}}` piped to `.claude/hooks/guard_agent_spawn.py` gives exit 2, `the brief to pm has missing or unfilled: Files:`. `Files:\n  a.md` and `## Tier: 2` (a heading) are refused the same way.
- This matches JC-AC6 as approved: "`Files:` empty → exit 2". It also matches coordinator_lint rule 6 ("an empty field … does not borrow the next line"). The engineer is not at fault.
- Cost: one retry. The refusal message shows the accepted form (`Files: <paths>`), so nothing passes falsely and nothing hangs.
- Options for ba-sa, if the owner wants it: either AGENTS.md §0 ข states "paths on the `Files:` line itself", or a later increment lets a `Files:` line borrow the bullet lines below it.

## Defects

None at rework level.

## Hostile inputs tried

- Spawn guard: 31 typed cases and 6 raw payloads (list in `scratchpad/review-jc1/probes/guard_probe.py`). Results are summarised under JC-AC3 and JC-AC6. A JSON-array payload gives a traceback with exit 1. The 5cbe3b6 guard does the same, so this is not new (Parked).
- inject_jarvis: 17 payload shapes, non-UTF-8 stdin, `LC_ALL=C`, and a planted tree with a missing, non-UTF-8 or CRLF definition. No case printed to stderr or exited non-zero.
- approve-ready: 15 git states and arguments, as listed under JC-AC11. A trailing-space status and a non-UTF-8 document are under Parked.
- Mutation: base guard restored → 24 new tests red.

## Parked

None of these is rework; each is outside the threat model or fails closed.
- `guard_agent_spawn.py:307`, in the spec-gate refusal: "`ba-sa`, `pm`, `Explore`, `reviewer` and the rest are never blocked". This is now untrue for the brief-line check. Judged not misleading enough for rework:
  - it is shown only inside an engineer spec-gate refusal;
  - a pm, ba-sa or reviewer spawn that trusts it gets an immediate and explicit JC-AC6 message, so there is no false GREEN and no stuck state.
  - Proposed one-word fix: "never blocked *by this spec gate*".
- approve-ready refuses `Status: In Review ` (a trailing space), and approve.py `.strip()`s and accepts it. This fails closed and the message shows the quoted value.
- approve-ready does not check approve.py's `## Approval history` requirement, so it can print a command that approve.sh then refuses. Not in JC-AC11's (a)–(c). This fails closed.
- approve-ready on a tracked non-UTF-8 document gives a `UnicodeDecodeError` traceback; approve.py crashes on the same file.
- Pre-existing: the guard gives a traceback on a top-level JSON-array payload (exit 1, fails open). This is unchanged from 5cbe3b6.
- Pre-existing: role-agent and review-gate matching is exact-case (`QA` is not checked). The CLI resolves types exactly.
- A Cyrillic look-alike `jаrvis` is not refused by JC-AC3. The CLI cannot resolve that type, so the spawn fails anyway.
- inject_jarvis prints the body stripped of its final newline, not byte-for-byte. The text is identical.

## Could not reach

- The engineer's handback with the JC-AC5 live probe quotes. This review is from the files only. The CLI version matches the spec's measured run (2.1.304); the quoted re-run lines are unverified by me.
- `Reviewer-run:` is left as `<id>` per the brief; the coordinator fills it from the spawn result.

## Approval history

- **2026-10-20 — drafted.** By reviewer, from SPEC-jarvis-coordinator (Approved), PRD R1–R8 and `git diff 5cbe3b6..91d6ef2`. Every result was re-run in this review.
