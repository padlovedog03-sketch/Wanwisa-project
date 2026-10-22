---
name: easy-and-end-to-end
description: Owner ruling — the upgrade goal is "easy to use and Jarvis runs work end to end"; a Tier 0 bugfix gets one review rework round, then test-strength findings are parked; no mid-task messages
type: feedback
status: active
date: 2026-10-22
source: owner, 2026-10-22 — "ยังอยู่ในนิยามใช้งานง่ายอยู่ไหม" after a one-line grep fix (B1) took 7 agent runs and 2 rework rounds chasing mutants; then "ใช้งานง่ายและจาวิสคุมงานได้ครบ e2e" and "เอาตามนี้"
mechanism: .agents/skills/scope-discipline/SKILL.md rule 4 (Tier 0 review cap) — loaded by every role; reviewer briefs restate it
---

**The goal.** Work that does not make Jarvis easier to use, or let it carry a task end to end while
the owner waits, is parked. Order and cuts live in doc/tasks/backlog.md.

**Lesson.** Bugfix B1 (CI gate 3 skips `.claude/worktrees/`) was correct after the first engineer
run. Review round 1 and round 2 then failed it for tests that missed a mutant (`^` dropped, then
`/` dropped). Each round cost an engineer and a reviewer run, about 15 minutes. Correctness never
changed.

**How to apply:**
- Tier 0: one rework round. After it, "tests could be stronger" goes under `Parked:`. A wrong fix
  still fails.
- No messages to the owner between dispatch and the final report, except decisions that only the
  owner makes (AGENTS.md §0 duty ง).
- Related: [[stay-on-the-definition]], [[smallest-useful-scope-first]], [[ease-of-use-over-strictness]].
