# Review: coordinator-discipline §8 — brief headers the spawn guard checks

Status: In Review
Owner: reviewer
Upstream: backlog row 6 items (c) and (e); doc/memory/easy-and-end-to-end.md
Author-run: c9728b0
Reviewer-run: agent-a9ca74d3bd7dd5567
Date: 2026-10-22

Verdict: FAIL

## Summary

FAIL on criterion 1. The guide says "Copy the block for the role", but the QA block's `Spec:` line has a comment that contains
`NO_SPEC_BUGFIX:`. Copied as written, that comment switches the guard into bugfix mode, and the guard then refuses a
Tier 1 QA spawn even when a real PASS review exists. Criteria 3 and 4 pass. Criterion 2 passes with one Low gap.

## Read from

- Upstream: backlog row 6 items (c) and (e); doc/memory/easy-and-end-to-end.md
- Change: `git show c9728b0`, which adds 45 lines (the new §8) to `.agents/skills/coordinator-discipline/SKILL.md`
- Checked against: `.claude/hooks/guard_agent_spawn.py`, `AGENTS.md` §5 lines 93–94, `.claude/agents/reviewer.md` line 25, `ci-examples/github-actions.yml` gate 3
- Not read: the author's conversation.

## Criteria Review

Hook runs: `python3 feed.py .claude/hooks/guard_agent_spawn.py SPEC-jarvis-coordinator.md REVIEW-jarvis-coordinator.md SPEC-jarvis-coordinator.md`.
`feed.py` is a reviewer scratch script. It fills in each block and sends `{"tool_name":"Agent","tool_input":{"subagent_type":…,"prompt":…}}` to the guard on stdin. All runs were in the reviewer worktree at c9728b0.

| # | Criterion | Result | Evidence (command run in this review) |
|---|---|---|---|
| 1a | engineer Tier 0 block passes | PASS | `eng-T0: exit=0` |
| 1b | engineer Tier 1 block passes (Approved spec) | PASS | `eng-T1: exit=0` |
| 1c | reviewer block passes, Tier 1 and Tier 0 | PASS | `rev-T1: exit=0`, `rev-T0: exit=0`. The inline `#` comments on the `Files:` item and the `Spec:` line do no harm. |
| 1d | QA Tier 0 block fails only for the review reason | PASS | `qa-T0: exit=2 … doc/qa/REVIEW-bugfix-zz-nonexistent.md: not found` |
| 1e | QA Tier 1 block fails only for the review reason | **FAIL** | Copied with its comment: `qa-T1-verbatim-comment: exit=2 … NO_SPEC_BUGFIX: work must name doc/qa/REVIEW-bugfix-&lt;id&gt;.md on its Review: line, not REVIEW-zz-nonexistent.md`. With a real PASS review, `qa-T1-real-review-verbatim: exit=2` gives the same bugfix-mode refusal, while `qa-T1-real-review-stripped: exit=0`. The header itself sends the guard down the wrong path. |
| 2 | blocks agree with AGENTS.md §5 (Tier 0/1 QA lines, `Spec:` required for non-bugfix QA, 0cc9c6c) | PASS (Low gap) | AGENTS.md lines 93–94: a Tier 1 QA brief needs `Spec:` and `Review: … REVIEW-&lt;slug&gt;.md`, and a Tier 0 one needs `REVIEW-bugfix-&lt;id&gt;.md`. The block has `Spec:` for Tier 1–2 and `NO_SPEC_BUGFIX:` for Tier 0, which matches `git show 0cc9c6c`. Gap: the QA block's `Review:` line gives only `REVIEW-&lt;slug&gt;.md` and has no Tier 0 bugfix alternative. The reviewer block has one. |
| 3 | no upper-case angle-bracket placeholder (CI gate 3) | PASS | `git show c9728b0 -- …/SKILL.md \| grep -n '&lt;[A-Z_]\{3,\}&gt;'` finds no match (exit 1). `scripts/verify-full.sh` exits 0. |
| 4 | reviewer-isolation advice matches `.claude/agents/reviewer.md` line 25 | PASS | Line 25: the run ID is the isolated worktree's `agent-&lt;id&gt;`. If the reviewer cannot see it, it leaves `&lt;id&gt;` and the coordinator fills it from the spawn result. §8 says the same. |
| Gate | brief's Verify with | PASS | `python3 -m pytest tests/coordinator tests/framework tests/ci -q -p no:cacheprovider` gives `564 passed, 1 skipped` |
| Gate | exit gate | PASS (incomplete by design) | `scripts/verify-full.sh` exits 0, with the banner `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests` |

## Defects (if FAIL)

| Severity | Description | Where | Back to |
|---|---|---|---|
| High | The QA block's `Spec:` comment, `# Tier 1–2; for Tier 0 use NO_SPEC_BUGFIX: &lt;repro&gt; instead`, contains the literal override token. The guard checks `"NO_SPEC_BUGFIX:" in prompt` against the whole prompt. A Tier 1 QA brief copied with the comment is therefore refused for not naming a `REVIEW-bugfix-` file, even when a real PASS review exists. §8 exists to prevent exactly this kind of refused spawn. Repro: `qa-T1-real-review-verbatim: exit=2`. Fix: either take the token out of the comment (for example "Tier 0: no Spec line; put the bugfix repro line instead") or split it into separate Tier 0 and Tier 1 QA blocks. | `.agents/skills/coordinator-discipline/SKILL.md` §8, QA block `Spec:` line | author of c9728b0 |
| Low | The QA block's `Review:` line names only `REVIEW-&lt;slug&gt;.md`, but AGENTS.md §5 requires `REVIEW-bugfix-&lt;id&gt;.md` for Tier 0. Add a comment such as `# or REVIEW-bugfix-&lt;id&gt;.md for Tier 0`, as the reviewer block already has, and keep the override token out of it. | same, QA block `Review:` line | author of c9728b0 |

## Hostile inputs tried

- QA Tier 1 block copied with its inline comment: exit 2, bugfix-mode refusal (the High defect above)
- QA Tier 1 block with the comment removed, a real PASS review (`REVIEW-jarvis-coordinator.md`) and `SPEC-jarvis-coordinator.md`: exit 0
- Reviewer block with trailing `#` comments on the `Files:` item and the `Spec:` line: exit 0 (the comment does not hide the path)
- Reviewer Tier 0 block with `Spec:` left out: exit 0
- Engineer Tier 0 block with the `NO_SPEC_BUGFIX:` repro on its own line: exit 0

## Parked

- §8 also says to spawn QA with an isolated worktree so its run ID is known. QA reports have no `Reviewer-run:` line, so this does no harm but is not needed for QA. It is outside the criteria.

## Approval history

- **2026-10-22 — drafted.** Written by reviewer run agent-a9ca74d3bd7dd5567 from `git show c9728b0`, the guard, AGENTS.md §5 and reviewer.md. The author's conversation was not read.
