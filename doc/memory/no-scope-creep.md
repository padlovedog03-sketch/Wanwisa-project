---
name: no-scope-creep
description: Owner ruling — every role applies the scope-discipline skill on every task; found is not done, additions name what they displace, edit only listed files, observations go to the backlog
type: feedback
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "อันนี้ก็เป็นผลที่ทำให้งานช้าเหมือนกันเพราะ framework เราชอบขยายงานเพิ่มเอง" then "จดกฎนี้แล้วเริ่มใช้เลย ควรเป็นกฏที่ถูกเรียกทุกครั้งที่สั่งงานเหมือนเป็นหนึ่งในเครื่องมือเลย"
mechanism: .agents/skills/scope-discipline/SKILL.md — named in every role definition under .claude/agents/ so it loads on every dispatch; machine check of Files: against the diff is parked in the backlog
---

The four rules live in the skill, not here — this file records that the owner ordered them and why.

**Why:** today's upgrade widened at every role (coordinator proposals, pm extra requirements, ba-sa
over-strict ACs, engineers' drive-by fixes, QA observations turned into rework) — see
[[smallest-useful-scope-first]].

**How to apply:** every brief carries `Files:`; every handback carries `Parked:` and
`Outside Files:`; the coordinator refuses additions that name nothing they displace.
