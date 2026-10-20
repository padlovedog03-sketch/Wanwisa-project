---
name: lean-gates-risk-based-qa
description: Owner ruling — tier-2 work drops the owner review between engineer and QA, may approve PRD+spec together, and uses full QA only for guards/instruments
type: project
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "เอาตามนี้ ปรับได้เลย" on the coordinator's measured step-by-step cost/value table
---

Applies now to framework work in this repo; becomes permanent framework rule in
delegated-autonomy increment G (§5–6 reconcile).

1. No owner review between engineer and QA. The owner reviews once, after QA/review.
2. PRD and spec may be approved together when the work touches no business rule.
3. Risk-based checking: code that is a gate, guard or measuring instrument gets full QA;
   text-only changes to skills/templates/rules already pinned by tests get one independent
   reviewer against the ACs; small increments finished the same day may share one QA round.
4. Unchanged: spec per PRD, coordinator re-verification of every claim, approval registry.

**Why:** measured on the pilot project and this session — the engineer→owner→QA gate never
caught a defect (QA did: 4 real defects in increment J), while it added a wait per increment.

**How to apply:** when an increment lands, classify it (guard/instrument vs text-only) and route
to `qa` or a single reviewer; report to the owner once afterwards. Related: [[this-repo-improves-the-framework]].
