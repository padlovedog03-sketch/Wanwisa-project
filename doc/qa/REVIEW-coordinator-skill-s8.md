# Review: coordinator-discipline §8 — brief headers the spawn guard checks

Status: In Review
Owner: reviewer
Upstream: backlog row 6 items (c) and (e); doc/memory/easy-and-end-to-end.md
Author-run: c9728b0, 0bfca8b
Reviewer-run: a8147b82828d32e9d
Date: 2026-10-22

Verdict: PASS

## Summary

Round 2 PASS. Commit 0bfca8b splits the QA header into a Tier 0 block and a Tier 1–2 block. The Tier 1–2 block no
longer contains the override token anywhere, including its comment, so the guard now treats a filled Tier 1 or Tier 2
QA brief as non-bugfix and lets it through when a real PASS review exists. The new Tier 0 QA block names
`REVIEW-bugfix-&lt;id&gt;.md` and passes with a real bugfix review, which closes round 1's Low gap. The engineer and
reviewer blocks still pass. The fix adds no upper-case angle-bracket placeholder. There is one Low finding that does
not block: the new isolated-reviewer note contradicts `.claude/agents/reviewer.md` line 22 (see Defects).

## Read from

- Upstream: backlog row 6 items (c) and (e); doc/memory/easy-and-end-to-end.md
- Change: `git show 0bfca8b -- .agents/skills/coordinator-discipline/SKILL.md` (round 2 fix) and the §8 text as it
  stands at HEAD 56bbede
- Checked against: `.claude/hooks/guard_agent_spawn.py` (`_check_review`: `bugfix = _OVERRIDE_TOKEN in prompt` over the
  whole prompt), `.claude/agents/reviewer.md` lines 22 and 25, and `doc/qa/REVIEW-bugfix-d10.md` and
  `doc/qa/REVIEW-jarvis-coordinator.md` as the real reviews
- Not read: the author's conversation.

## Criteria Review

Hook runs: `python3 <scratchpad>/feed2.py <worktree>`. `feed2.py` is a reviewer scratch script. It takes the §8 code
block from SKILL.md, splits it into its five role blocks, fills the placeholders, and sends
`{"tool_name":"Agent","tool_input":{"subagent_type":…,"prompt":…}}` to the guard on stdin. It also checks whether
the Tier 1–2 QA block contains `NO_SPEC_BUGFIX` (`token-in-T12-block: False`). All runs were in the reviewer worktree
at 56bbede, which contains 0bfca8b.

| # | Criterion | Result | Evidence (command run in this review) |
|---|---|---|---|
| 1a | engineer Tier 0 block passes | PASS | `eng-T0: exit=0` |
| 1b | engineer Tier 1 block passes (Approved spec SPEC-jarvis-coordinator) | PASS | `eng-T1: exit=0` |
| 1c | reviewer block passes, Tier 1 and Tier 0 | PASS | `rev-T1: exit=0`, `rev-T0: exit=0` (Tier 0 with the `Spec:` line removed, as the comment says) |
| 1d | QA Tier 0 block with a real bugfix review, `REVIEW-bugfix-d10.md`, gives exit 0 | PASS | `qa-T0-real: exit=0`. Negative case: `qa-T0-missing: exit=2 … doc/qa/REVIEW-bugfix-zz-nonexistent.md: not found` |
| 1e | QA Tier 1–2 block with Spec and a real PASS review (`SPEC-jarvis-coordinator.md` + `REVIEW-jarvis-coordinator.md`) gives exit 0, which was round 1's High | PASS | `token-in-T12-block: False`; `qa-T1-real: exit=0`; `qa-T2-real: exit=0`. Negative cases: `qa-T1-missing: exit=2 … doc/qa/REVIEW-zz-nonexistent.md: not found`, and `qa-T1-nospec: exit=2 … name the spec under test on a Spec: … line`. The refusal is now for the right reason, not bugfix mode. |
| 2 | blocks agree with AGENTS.md §5 (Tier 0 QA names `REVIEW-bugfix-&lt;id&gt;.md`, Tier 1–2 QA names `Spec:` + `REVIEW-&lt;slug&gt;.md`), which was round 1's Low | PASS | The Tier 0 QA block has `NO_SPEC_BUGFIX:` on its own line and `Review: doc/qa/REVIEW-bugfix-&lt;id&gt;.md`. The Tier 1–2 block has `Spec:` and `Review: doc/qa/REVIEW-&lt;slug&gt;.md`. The 1d and 1e runs show the guard accepts both. |
| 3 | no upper-case angle-bracket placeholder (CI gate 3) | PASS | `git diff c9728b0~1 0bfca8b -- …/SKILL.md \| grep -nE '^\+.*<[A-Z_]{3,}>'` finds no match (exit 1). The one match in the whole file is at line 39 and comes from 7bf39dc (`git log -S`), so this change did not add it. `scripts/verify-full.sh` exits 0. |
| 4 | reviewer-isolation advice matches `.claude/agents/reviewer.md` | PASS (Low note) | Line 25: the run ID is the worktree's `agent-&lt;id&gt;`, and the coordinator fills `&lt;id&gt;` from the spawn result. §8 says the same. The new sentence "writes the review there and the coordinator copies it" conflicts with reviewer.md line 22. See Defects (Low). |
| Gate | brief's Verify with | PASS | `python3 -m pytest tests/coordinator tests/framework tests/ci -q -p no:cacheprovider` gives `564 passed, 1 skipped in 56.42s` |
| Gate | exit gate | PASS (incomplete by design) | `scripts/verify-full.sh > vf.log` exits 0, with the banner `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests` |

## Defects (if FAIL)

None block. One Low finding for the author:

| Severity | Description | Where | Back to |
|---|---|---|---|
| Low | §8 now says "An isolated reviewer can write only inside its own worktree, so it writes the review there and the coordinator copies it to the main tree's `doc/qa/`". Line 22 of `.claude/agents/reviewer.md` still says "Write it in the MAIN tree's `doc/qa/`, never inside a worktree". A reviewer that follows its own definition is told to do something its isolation refuses. This run saw the refusal ("This agent is isolated in the worktree …"). §8 describes what actually works, so the fix goes in reviewer.md line 22, which is not in this change's files. | `.claude/agents/reviewer.md` line 22 vs SKILL.md §8 | coordinator (follow-up brief on reviewer.md) |

## Hostile inputs tried

- Searched the Tier 1–2 QA block, comments included, for the override token: none found, so that block cannot switch the guard to bugfix mode
- Tier 1 and Tier 2 QA briefs with a real PASS review: exit 0
- Tier 1 QA brief with the `Spec:` line removed: exit 2, refused for the missing spec, not for bugfix mode
- Tier 1 and Tier 0 QA briefs that name review files that do not exist: exit 2, `not found`
- Reviewer block with the `# or REVIEW-bugfix-&lt;id&gt;.md` comment left in place: exit 0. The lower-case placeholder in the comment is harmless.

## Parked

- Round 1's Parked item still stands: §8 earlier told the coordinator to spawn QA isolated. 0bfca8b now limits that advice to reviewers, so this item is resolved, not parked.

## Review history

- **Round 1 — 2026-10-22, commit c9728b0, reviewer run agent-a9ca74d3bd7dd5567: FAIL.**
  - High: the comment on the QA block's `Spec:` line contained the literal override token. Copied as written, it switched the guard to bugfix mode, and a Tier 1 QA spawn was refused even with a real PASS review (`qa-T1-real-review-verbatim: exit=2`; with the comment removed, `exit=0`).
  - Low: the QA `Review:` line gave no Tier 0 `REVIEW-bugfix-&lt;id&gt;.md` option.
  - Criteria 1a–1d, 3 and 4 passed. The Verify-with run gave `564 passed, 1 skipped`, and `scripts/verify-full.sh` exited 0.
- **Round 2 — 2026-10-22, commit 0bfca8b (HEAD 56bbede), reviewer run agent-a8147b82828d32e9d: PASS.** Both round 1
  defects are fixed and checked with filled blocks fed to the guard. One Low finding (the reviewer.md line 22 conflict) goes to a follow-up.

## Approval history

- **2026-10-22 — drafted (round 2).** Written by reviewer run agent-a8147b82828d32e9d from `git show 0bfca8b`, the
  guard, AGENTS.md §5 and reviewer.md. The author's conversation was not read. The file is written in the reviewer's
  worktree, and the coordinator copies it to the main tree.
