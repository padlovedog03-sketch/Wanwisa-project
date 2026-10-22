---
name: jarvis-decides-self-improvement
description: Owner ruling — for framework self-improvement, Jarvis makes the decisions the owner used to make and carries the work to the end; only the mechanical human gates stay (Approved flips via approve.sh, merge to main)
type: project
status: active
date: 2026-10-22
source: owner, 2026-10-22 — "พี่ไม่ตัดสินให้จาวิสตัดสินใจพัฒนาตัวเองจนจบ" after a report that listed four owner decisions
---

**Scope.** Work in this repo that improves the framework (doc/memory/this-repo-improves-the-framework.md).

**Jarvis now decides:** backlog order and cuts, which recommendation to take on an open decision,
merging Tier 0 and Tier 1 work into the working branch, and whether a parked item is un-parked.
Each decision is written into the final report with its reason.

**Still human, unchanged:**
- flipping a document to `Approved` (AGENTS.md §6.2; `scripts/approve.sh` is owner-only and the
  guard refuses agents) — Jarvis batches every ready approval into one command list at the end,
  checked with `scripts/coordinator_lint.py --approve-ready`;
- merging into `main`, deploying, and the always-human list (delegated autonomy Part B);
- changing the threat model, AGENTS.md §3, or a memory ruling of the owner.

**How to apply:** do not ask the owner to choose between options; choose, act, and report. Stop
only at the gates above. Related: [[easy-and-end-to-end]], [[stay-on-the-definition]].
