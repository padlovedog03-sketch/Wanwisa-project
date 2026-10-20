---
name: rework-goes-in-a-fresh-brief
description: Dispatch QA rework as a new agent run whose first message starts with REWORK:, never as a follow-up message to a running agent
type: feedback
status: active
date: 2026-10-20
source: increment J rework, 2026-10-20 — the coordinator sent REWORK: as a mid-run follow-up; the meter (ADR-13) reads only a run's first inbound message, so it counted 0 of 3 engineer runs as rework
mechanism: none — the coordinator brief check that would enforce this ships with delegated-autonomy increment E; until then the meter's "unmarked" line is the only signal
---

Send rework as a fresh dispatch whose brief begins with `REWORK: <QA report> <cause>`.

**Why:** the rework-share metric (M11) is computed from the first message of each run. Rework sent
as a follow-up is invisible to it, which undercounts exactly the number the owner judges the
framework by.

**How to apply:** when QA returns FAIL, start a new engineer run (it may reuse context by reading
the QA report), never `SendMessage` the rework into the old one.
