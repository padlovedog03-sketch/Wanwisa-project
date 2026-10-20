---
name: hostile-inputs-in-every-ac
description: Every increment ships with hostile-input acceptance criteria, an engineer self-attack, design claims probed by ba-sa, and one owner per file
type: feedback
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "เอาตามข้อเสนอปรับกระบวนการทั้ง 4 ข้อ"; measured the same day — every increment that reached QA (J ×3, H ×2, B, A+C) was sent back for hostile inputs the ACs never named, and engineers found ≥7 wrong INFERRED design claims
mechanism: none — enforced today only by the coordinator's briefs; the machine check ships with delegated-autonomy increment E (right first time)
---

1. **ACs name hostile inputs.** Every gate, guard or instrument AC carries "never crashes, never leaks, never reports green" cases: malformed and odd-shaped input, invisible/look-alike characters, prefixes and wrappers, case and symlink variants.
2. **Engineer self-attack.** Before handoff the engineer tries to break their own work the way QA would, and lists what was tried in the handback.
3. **ba-sa probes before claiming.** A design claim that a short command can check is checked and tagged `[MEASURED]`; otherwise it is not written as fact.
4. **One owner per file.** A spec assigns each new or edited file to exactly one increment; shared files are named with an explicit merge order.

**Why:** rework share in this repo was 30% (3 of 10 engineer runs, all `missed-ac`), each round costing an engineer run plus a QA run.

**How to apply:** put all four into every ba-sa and engineer brief from now on; QA keeps attacking regardless. Related: [[lean-gates-risk-based-qa]], [[rework-goes-in-a-fresh-brief]].
