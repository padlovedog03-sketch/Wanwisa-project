# QA Report: Jarvis coordinator — Increment 1 plus amendment am1

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-jarvis-coordinator.md · doc/specs/SPEC-jarvis-coordinator-am1-files-list.md · doc/qa/REVIEW-jarvis-coordinator.md · doc/qa/REVIEW-jarvis-coordinator-am1-files-list.md
Date: 2026-10-21

## Verdict: PASS

All 15 criteria (JC-AC1 … JC-AC12, JC-AM1, JC-AM1-RED, JC-AM2) hold at worktree head `0601a0b`. The exit gate `scripts/verify-full.sh` exited 0, and every check was re-run by QA. Live CLI probes confirm two things: the main thread runs as `jarvis`, and a `jarvis` spawn is refused by the guard.

Code under test: `.claude/worktrees/agent-a2b6d5b03efba43ea`, HEAD `0601a0b` (9278b21, 8687655, 91d6ef2, 0601a0b on 5cbe3b6), `git status --short` empty.
Scratch (probe scripts, logs): `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/`

## Spec-level finding (for ba-sa; not rework, verdict unchanged)

A tier-0 bulleted header with `Files:` forgotten is accepted. For example, `- Tier: 0 — bug` / `- Files:` / `- NO_SPEC_BUGFIX: <repro>` → exit 0. So is `- Verify-with: x` after an empty `- Files:`. AM1-ADR-2 defines a label as letters and spaces, so `NO_SPEC_BUGFIX:` (underscores) and `Verify-with:` (hyphen) are read as filled path items. This is the accident AM1-ADR-2 exists to catch, and `NO_SPEC_BUGFIX:` is a real header token on the tier-0 route. The code matches the approved grammar exactly, so it is not rework. Proposed amendment: widen the label to `[A-Za-z][A-Za-z0-9_ -]*` (a `.` or `/` before the colon still marks a path). Reproduce: `scratchpad/probe/guard_probe.py`, the "AM1 adversarial extras" rows.

## Criteria Results

| # | Criterion | Verdict | Evidence (command run by QA) |
|---|---|---|---|
| JC-AC1 | `agent` = `"jarvis"`, jarvis.md name, no restricting `tools:` | PASS | `tests/hooks/test_jarvis_entry.py` (in the 1833-test run): the committed entry plus 8 planted hostile copies (key removed, `Jarvis`, `jarvis `, zero-width, md missing/renamed, name differs, tools without Agent, invalid JSON). Read by QA: settings.json line 2 `"agent": "jarvis"`; jarvis.md frontmatter has `name: jarvis` and no `tools:` or `model:` line. |
| JC-AC2 | body is a ≤600-char pointer to AGENTS.md | PASS | Same file: the committed body passes. 601 chars, no AGENTS.md and a placeholder are each red; exactly 600 passes. Body = 2 Thai lines naming `AGENTS.md`. |
| JC-AC3 | `jarvis` refused first, after normalisation | PASS | `scratchpad/probe/guard_probe.py`: `jarvis`, `Jarvis`, ` jarvis `, `jar​vis`, `ｊａｒｖｉｓ`, `JARVIS`, `jarvis­` → exit 2 `…JC-AC3): Jarvis is the main thread, not a role agent`. `jarvis-helper`, `general-purpose`, `Explore`, `Plan`, `claude-code-guide`, `unknown`, `""` → exit 0. **Live:** `claude -p "Use the Agent tool once to spawn the subagent type 'jarvis'…" --allowedTools "Read"` gave `PreToolUse:Agent hook error: […guard_agent_spawn.py]: BLOCKED (… JC-AC3): Jarvis is the main thread, not a role agent …` |
| JC-AC4 | fallback hook injects only when no agent is named | PASS | Direct runs of `inject_jarvis.py`: `{}`, `agent_type` null, `""`, `"  "`, `0`, `false` → rc 0, 114-char body. `jarvis`, `Jarvis `, `jar​vis`, `roleb`, `["x"]` → rc 0, empty. Empty stdin, `garbage`, `[]`, `"str"`, `42`, `null`, invalid UTF-8 → rc 0, empty, no traceback. In a tmp copy of the tree, jarvis.md missing, non-UTF-8 or a directory → rc 0, empty. The registration test and its "entry removed → red" test pass. |
| JC-AC5 | live probes P1–P5, P8, P12 quoted in the handback | PASS on QA re-probe (handback not seen; P8 not re-run) | I did not see the engineer's handback, so QA re-ran the spec's procedure on CLI `2.1.305` (spec measured 2.1.304). The runs used a scratch copy of the worktree (`scratchpad/p12/copy`, rsync without `.git`/`.verify`, then `git init`) with the spec's logging hook (SessionStart, UserPromptSubmit, PreToolUse(Agent) → `hook.log`) and `--allowedTools "Read"`. **P1/P7:** `hook.log` `{"event": "SessionStart", "agent_type": "jarvis"}`, `{"event": "UserPromptSubmit", "agent_type": "jarvis"}`, with no `--agent` flag. **P2:** `{"event": "PreToolUse", "agent_type": "jarvis", "sub": "pm"}`, so the main thread calls Agent. The guard then refused the tier-less brief live: `BLOCKED (… JC-AC6): the brief to \`pm\` has missing or unfilled: Tier:, Files:`. **P3:** the replies follow AGENTS.md §0: Thai, and a `Tier: 0 — …` first line. **P4:** init `skills` begins `['code-quality', 'coordinator-discipline', 'engineering-loop', …]`. **P5:** init `agents` contains `jarvis`. **P6:** live refusal of a `jarvis` spawn (JC-AC3 row). **P12:** with `"agent"` removed in the copy, `hook.log` shows `agent_type: null` on both events. Asked to quote any sentence containing ตัวชี้, the model returned the jarvis.md line `ทำตาม \`AGENTS.md\` — กฎทุกข้ออยู่ที่นั่น ไฟล์นี้เป็นแค่ตัวชี้` "from the hook message". That text exists only in `.claude/agents/jarvis.md` (grep). stream-json does not emit UserPromptSubmit `hook_response`; the direct hook run in JC-AC4 shows the same payload prints the body. **P8** (interactive pty) was not re-run. |
| JC-AC6 | role-agent brief needs a filled `Tier:` and `Files:` | PASS | `guard_probe.py` on `pm`/`ai-engineer`/`ba-sa`. **Each exit 2, naming the line:** no Tier; `Tier:` empty; `Tier: <0\|1\|2>`; `Tier: high`; mid-sentence; `Ti​er: 1`; `tier: 1`; `Files:` empty; `Files: <paths>`; `NO_SPEC_BUGFIX:` with no Tier; neither line (names both, shows `Tier: <0\|1\|2> — <reason>` / `Files: <paths>`); `## Tier: 2`. **Exit 0:** `Tier：1 — x` (full-width colon); `**Tier:** 2 — x` + `- Files: a.py`. **Never checked:** Explore, Plan, general-purpose, claude-code-guide, unknown, empty → 0. A non-Agent tool → 0. Order: JC-AC3 → JC-AC6 → review gate → spec gate, read in `main()`. |
| JC-AC7 | existing spawn-guard suites green with a one-line helper change | PASS | `python3 -m pytest tests/hooks/test_guard_agent_spawn.py tests/hooks/test_regression_guard_agent_spawn_review.py tests/hooks/test_regression_autonomy_rework_bypasses.py -q -p no:cacheprovider` → `181 passed in 5.62s`, rc 0. `git diff 5cbe3b6..HEAD` removes exactly one line in each of the two helper files (the `_run_gate` payload line). No existing test was deleted or weakened, and `test_regression_autonomy_rework_bypasses.py` is untouched. |
| JC-AC8 | AGENTS.md §0/§5 anchors, R5 table, neutrality | PASS | `tests/framework/test_doc_contracts_jarvis.py`: every anchor and R5 item, plus planted removals (each red, naming it). `python3 scripts/check_neutrality.py` → `neutrality: 0 provider name(s) in layers 0-1, 0 project leak(s)`, rc 0. |
| JC-AC9 | ADAPTERS.md rows and JC-L1…JC-L10 once each | PASS | Same file: the committed rows and ids pass. A missing id, a duplicated id or a missing row in ก/ข are each red. |
| JC-AC10 | memory lint 0 problems; 0 lessons with no mechanism | PASS | `python3 scripts/memory_lint.py` → `memory: 0 problem(s) …`, rc 0. `python3 scripts/correction_rate.py --brief` → `… · 0 lesson(s) since 2026-10-08 with no mechanism`, rc 0. |
| JC-AC11 | `--approve-ready` pre-check | PASS | `scratchpad/probe/repo*` tmp git repos. Untracked → `no tracked document matches 'a' — git add and commit it` rc 1. Staged-new → `not committed` rc 1. Committed clean In Review → `scripts/approve.sh a --by <name>` rc 0, also from a subdirectory and with an upper-case slug. Edited, edited+staged, deleted in worktree → `uncommitted changes` rc 1. Draft/Approved/no status/two status lines → `Status is '…'` rc 1. A pair where one doc is dirty → rc 1 for the batch. Zero match → rc 1. A doc outside the approvable folders is not matched. No slug, `""`, `" "`, `a ""` → usage, rc 2. Outside git → `coordinator-lint: not inside a git work tree` rc 2. `PATH=/nonexistent` → `coordinator-lint: git not found on PATH` rc 2. Default mode unchanged (coordinator suite 155 passed). |
| JC-AC12 | doc contracts, neutrality, hooks/coordinator/framework green | PASS | `python3 -m pytest tests/framework/test_doc_contracts.py -q -p no:cacheprovider` → `62 passed, 1 skipped`, rc 0. Neutrality as above. `python3 -m pytest tests/hooks tests/coordinator tests/framework -q -p no:cacheprovider` → `1833 passed, 1 skipped in 246.79s`, rc 0. The skip is the pre-existing `test_doc_contracts.py:193` one the reviewer traced to 5cbe3b6. |
| JC-AM1 | `Files:` may be a list under an empty `Files:` | PASS | `guard_probe.py`, `pm` with `Tier: 2 — x`. **All 9 spec accepted cases → 0**, and also `12. a.md` → 0. **All spec hostile cases → 2 `missing or unfilled: Files:`**: last line with and without `\n`; paragraph first; only `- <paths>`; `- `; bare `-`; blank lines only; indented `  a.md`; `**Task**`; inline `Files: <paths>` + `- a.md`; the bulleted header with Files forgotten (`- Verify with: pytest`). **Unchanged:** `Tier: 1 — x` + `Files:` → 2; `## Tier: 2` → 2. **Extra:** `- **Verify with:** pytest` and `- Upstream: …` after an empty `- Files:` → 2 (the label rule holds). A blank line inside the list ends it (`- <a>` / blank / `- b.md` → 2). `+ a.md` → 2. `- Makefile: add target` → 2, the documented fail-closed case of AM1-ADR-2. |
| JC-AM1-RED | new accepted cases red on 91d6ef2; label rule load-bearing | PASS | `scratchpad/probe/red.py`: all 9 accepted cases against `git show 91d6ef2:.claude/hooks/guard_agent_spawn.py` → exit **2** each. With a copy of the HEAD guard that has the label check removed (`if not item:`), the bulleted-header-forgotten case → exit **0** (red). The HEAD guard gives 2. The case is in the parametrised refusal test (`test_guard_agent_spawn.py:822`). |
| JC-AM2 | spec-gate sentence says "never blocked by this spec gate" | PASS | `git diff 5cbe3b6..HEAD -- .claude/hooks/guard_agent_spawn.py`: the only change in the A5 refusal is `…are never blocked.` → `…are never blocked by this spec gate.`. The docstring sentence is untouched. The rule-A5 tests are green in the 181/1833 runs. |

## Test Run

```
cd .claude/worktrees/agent-a2b6d5b03efba43ea
scripts/verify-handoff.sh --status          → not opted in
scripts/verify-full.sh > verify-full.log 2>&1; rc=$?   → rc=0
  TODO lint / format / tests   not configured — this step verified NOTHING
  OK   hooks        (191s) 1303 passed in 190.91s
  OK   ci-examples  (3s) 22 passed in 2.53s
  OK   scar-forge   (1s)
  OK   coordinator  (3s) 155 passed in 3.57s
  OK   framework    (47s) memory: 0 problem(s)
  EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
  Everything configured passed, and that is ALL this run proves.
  record: .verify/runs/20261021T013239Z-94512/record.json
```

The INCOMPLETE line (lint, format and tests not configured) is the already-parked template state. Every configured step passed.

## Defects (if FAIL)

None.

## Edge Cases Probed

- A brief with `Files:` as a bullet list → accepted (`-`, `*`, `1.`, `12.`, indented, bold `**Files:**`, blank line before the first item, CRLF).
- A brief with no `Tier:` → refused: `the brief to \`pm\` has missing or unfilled: Tier:. Add each on a line of its own: Tier: <0|1|2> — <reason> / Files: <paths>`.
- A `NO_SPEC_BUGFIX:` engineer brief with no Tier → refused (the override does not open the check).
- Spawning `jarvis` → refused, both by direct hook runs and live through the CLI.
- approve-ready on an uncommitted doc (untracked → "no tracked document"; staged-new → "not committed"), on a Draft doc (`Status is 'Draft'`), and on a committed `In Review` doc (prints the approve.sh command, rc 0). A committed doc that is then edited, staged or deleted is refused.
- inject_jarvis with odd `agent_type` values (`0`, `false` → injects; a list → silent) and with CRLF in jarvis.md (still injects, because Python reads it with universal newlines).
- New, not raised by either reviewer: after an empty bulleted `- Files:`, an item whose label has a non-letter is read as a path. So `- NO_SPEC_BUGFIX: repro` and `- Verify-with: pytest` → exit 0. See "Spec-level finding".
- Live in the adapter: a `pm` brief with no `Tier:`/`Files:` was refused by the JC-AC6 message.
- Already parked by the reviewers and not re-raised here, but confirmed by QA:
  - the JSON-array traceback (also present at 5cbe3b6);
  - exact-case role-type matching (`QA`, ` qa` and `Pm` are not checked);
  - approve-ready refusing `Status: In Review ` with a trailing space;
  - the `UnicodeDecodeError` traceback on a non-UTF-8 doc;
  - the stripped trailing newline in the injected body.

## Parked

- Spec-level finding above: the label grammar in AM1-ADR-2 lets `- NO_SPEC_BUGFIX:` and `- Verify-with:` count as paths after an empty bulleted `- Files:`. It goes to ba-sa as a proposed amendment, not engineer rework.
- The CLI is now 2.1.305. JC-L8 asks for a re-probe only on a major upgrade, so there is nothing to do.

## Could not reach

- The engineer's handback with the JC-AC5 probe quotes. QA re-ran P1–P7 and P12 on CLI 2.1.305 in a scratch copy instead (see the JC-AC5 row). P8 (interactive pty session with a trust dialog) was not re-run.
- Confirmation that the human approved the implementation before this QA run. The brief names the reviewer PASS files, but no human approval of the implementation.

## Substituted

- For JC-AC5, QA's own non-interactive probes stand in for the engineer's quoted lines. They ran in a scratch copy of the worktree with a logging hook added, never in the worktree's settings. `agent_type` comes from the hook log, which is mechanical. That the injected text reached the model in P12 rests on the model's verbatim quote of a sentence that exists only in jarvis.md.
- For JC-AM1-RED, the label rule was removed in a scratch copy of the guard (`scratchpad/probe/guard_nolabel.py`). The worktree hook was not edited.

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-21 — drafted.** By qa, from both Approved specs and both reviewer PASS files. Every result above is from commands QA ran against worktree HEAD `0601a0b`.
