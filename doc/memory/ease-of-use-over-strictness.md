---
name: ease-of-use-over-strictness
description: Owner ruling — the framework must stay easy to use; command guards catch accidents with declared limits, not every possible bypass; no signed approvals until autonomy reaches merge/production
type: project
status: active
date: 2026-10-20
source: owner, 2026-10-20 — on signed approvals "มันจะเข้มงวดเกินไปหรือไม่"; on size-class sed counting "ไม่ทำให้ยากขนาดนั้น อยากให้ใช้งานง่าย"; then "เอาตามที่แนะนำเลยให้ใช้งานง่าย"
---

1. Approvals stay as today: `scripts/approve.sh` writing the out-of-repo registry. Forgery is made
   evident (verify_approvals, CI), not impossible. No passphrase/keychain/hardware signing.
2. Guards that match shell command text (guard_bash, path guard) exist to catch accidental and
   casual mistakes. A shell can always spell an action another way; those routes are written down
   as declared limits in the spec and ADAPTERS.md instead of chased one by one.
3. Revisit signed or remote approval only when the owner extends autonomy to merging into main or
   deploying to production.
4. The size-class meter counts edit-tool files only and says so; shell edits (`sed -i`, redirects)
   are reported, not counted.

**Why:** two QA rounds on the always-human guard closed 25 routes and found 22 new ones; each fix
added false positives and latency. The owner values a framework people can use over theoretical
completeness. Related: [[lean-gates-risk-based-qa]], [[hostile-inputs-in-every-ac]] (hostile inputs
still apply to crashes, leaks and fake green — this ruling only stops the bypass chase).

**How to apply:** when QA finds another shell spelling of a guarded action, record it as a declared
limit unless it is self-inflicted (e.g. the guard importing agent-writable code) or makes a gate
report green falsely.
