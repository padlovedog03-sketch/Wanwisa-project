# Review: Jarvis coordinator — Amendment 1 (`Files:` may be a list; JC-AM1, JC-AM1-RED, JC-AM2)

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-jarvis-coordinator-am1-files-list.md
Author-run: a8df05d8a616b9081
Reviewer-run: a540737339c6c396c
Date: 2026-10-21

Verdict: PASS

## Verdict: PASS

All three criteria hold when I re-run them. One rule the spec states in prose (a blank line after the first item ends the list) is implemented correctly but has no test. That is recorded below as a Low, non-blocking gap.

## Read from

- Upstream: doc/specs/SPEC-jarvis-coordinator-am1-files-list.md (Approved, `spec-jarvis-coordinator-am1-files-list-2026-10-21`)
- Change: worktree `.claude/worktrees/agent-a2b6d5b03efba43ea`, commit `0601a0b` (diff `91d6ef2..0601a0b`). It touches 2 files, `.claude/hooks/guard_agent_spawn.py` and `tests/hooks/test_guard_agent_spawn.py`, and nothing outside the spec's file table.
- Not read: the author's conversation. I re-ran every claim in the brief and relayed none of them.
- `Author-run:` and `Reviewer-run:` filled by the coordinator from the spawn results (the reviewer could not see either id).

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| JC-AM1 | An empty `Files:` followed by a filled list is accepted. Every hostile case in the table is refused with the message unchanged. | PASS | `python3 -m pytest tests/hooks -q -p no:cacheprovider` in the worktree gave `1303 passed`. The spawn-guard trio (`test_guard_agent_spawn.py`, `test_regression_guard_agent_spawn_review.py`, `test_regression_autonomy_rework_bypasses.py`) gave `181 passed`, which is 161 + 20 new. I counted the new cases in the diff: 9 accepted (all 9 in the spec table) and 11 hostile. The hostile set is all 10 spec rows, with "`- ` or bare `-`" split into 2 cases, plus `label-item-ends-the-list`. The "last line without newline" variant is the existing `files-empty`. `git diff 91d6ef2..0601a0b` does not change the JC-AC6 refusal message or the `Tier:` logic (AM1-ADR-4). |
| JC-AM1-RED | The new accepted cases are red against the `91d6ef2` guard, and removing the label rule turns the bulleted-header case red. | PASS | Scratch copy with `git show 91d6ef2:.claude/hooks/guard_agent_spawn.py` swapped in: `test_a_filled_brief_header_in_any_field_form_is_accepted` gave `9 failed, 3 passed`, and the 9 failures are exactly the new ids. Each one asserts `2 == 0` with stderr `missing or unfilled: Files:`. The label rule was removed by a single-occurrence swap (`if not item or _LABEL_PATTERN.match(...)` → `if not item:`), confirmed with `diff` as a 1-line change. That gave `2 failed, 12 passed`: `[bulleted-header-files-forgotten]` and `[label-item-ends-the-list]`. The accepted test stayed at `12 passed`. Restored: the real worktree was never edited (`git status --short` is empty, HEAD `0601a0b`). |
| JC-AM2 | The rule-A5 refusal says "never blocked **by this spec gate**". Only that sentence changes. | PASS | A JSON payload for an `ai-engineer` spawn with no spec reference gave exit 2, and stderr ends `` `ba-sa`, `pm`, `Explore`, `reviewer` and the rest are never blocked by this spec gate.`` `grep -rn "never blocked"` shows that the line-311 comment is unchanged. Only the two unrelated hook tests match in `tests/`. The rule-A5 tests are inside the 1303 passed. |

Exit gate: `scripts/verify-full.sh` in the worktree gave exit 0, with hooks 1303 passed, ci-examples 22, coordinator 155 and framework OK. It printed `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. This is already parked and is not raised again here. `verify-handoff.sh --status` reports `not opted in`.

## Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| Low (non-blocking) | **Untested rule.** The spec's list rule says the list stops "at the first blank line after the first item". The code does this: `Files:` + `- <paths>` + blank + `- a.md` gives exit 2, which I probed directly. No test pins it, though. Mutant `m_blankinside` skips blank lines inside the list, and all 26 Files cases still pass under it (`26 passed`). The spec's hostile table does not list this case, so the engineer delivered the contract. A one-line case would close the gap. | tests/hooks/test_guard_agent_spawn.py (hostile parametrize) | ai-engineer (optional, next touch) |

Three more mutants confirm the tests catch them. Each line shows the mutant, then the result:
- Inline `<…>` falls through to list reading: `inline-placeholder-then-list` goes red.
- Non-item lines are skipped instead of ending the list: `paragraph-before-list` goes red.
- The `<` placeholder check is dropped: 3 cases go red.

## Hostile inputs tried

All of these were piped directly to the worktree hook as a `pm` brief starting `Tier: 2 — x`. I list each input, then the exit code and outcome.

- `+ a.md`, `1) a.md`, `– a.md` (en dash), `• a.md` → exit 2. These are not list markers, so the guard fails closed.
- `－ a.md` (full-width hyphen) → exit 0. NFKC turns it into `-`, which is consistent with how the guard already reads text.
- `-\ta.md`, `-` + no-break space + `a.md`, `10. a.md` → exit 0.
- `- ****`, `- *`, `- **<paths>**` → exit 2.
- `- **Verify with:** pytest`, `- Criteria: x` + `- a.md` → exit 2. The label rule works and also ends the list.
- `- Makefile: add target` → exit 2. This false refusal is documented in AM1-ADR-2 and fails closed.
- CR-only line ends, trailing spaces after `Files:`, `**Files:** ` + list, `Files：` (full-width colon) + list → exit 0.
- Two `Files:` lines (the first followed by prose, the second by a list) → exit 0.
- `See Files:` mid-line, `## Files:` heading, lowercase `files:`, zero-width inside `Files` → exit 2.
- `Tier:` + `- 2` → exit 2 (AM1-ADR-4). A bare list with no `Files:` line → exit 2. `## Tier: 2` → exit 2.
- 200,000 blank lines between `Files:` and the item → exit 0, with no slowdown or crash.
- `- <zero-width space>` → exit 0. This is not new: the `91d6ef2` guard also accepts `Files: <zero-width space>` inline, because `str.strip()` does not remove U+200B. The amendment carries the JC-AC6 rule over unchanged, as the spec requires. See Parked.

## Parked

- LIMIT candidate (not rework): a `Files:` value made only of zero-width characters counts as filled, both inline (since JC-AC6) and as a list item. It was inherited unchanged from JC-AC6. An agent is unlikely to write this by mistake.
- The blank-line-inside-list test gap above, as an optional one-line test.

## Approval history

- **2026-10-21 — drafted.** By the reviewer, from the Approved amendment spec, diff `91d6ef2..0601a0b` and commands re-run in this run.
