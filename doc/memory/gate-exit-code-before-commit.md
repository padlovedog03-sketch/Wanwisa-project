---
name: gate-exit-code-before-commit
description: Lesson — never pipe verify-full into grep and chain a commit; the pipe drops the gate's exit code and a RED gate still commits
type: feedback
status: active
date: 2026-10-20
source: coordinator slip 2026-10-20 — `scripts/verify-full.sh | grep … && git commit` committed e6b4daa while the gate printed EXIT GATE RED (ci gate 3: a spec quoted a bootstrap placeholder literal); fixed in 29f0466
mechanism: none — candidate mechanism (pre-commit refuses when the newest .verify record for the staged tree is RED) is parked in doc/tasks/backlog.md
---

The commit must depend on the gate's own exit code: run `scripts/verify-full.sh > <log>` and commit only when its
exit status is 0 and the banner is not RED. A filter after a pipe reports its own status, not the gate's.

**Why:** the same class as the earlier 3-red-tests commit; a lesson that lives only in memory recurs.

**How to apply:** never write `verify-full.sh … | grep … && git commit`. Related: [[stay-on-the-definition]].

**Repeat, 2026-10-22.** The coordinator committed 7661338 (docs only: two QA/review reports) without
running `verify-full`. The reports quoted an upper-case placeholder in angle brackets, so CI gate 3
went red on the branch (`9 failed, 21 passed` in tests/ci) until the literal was escaped. Second
incident of "commit without a green gate", so checklist C2 (pre-commit refuses on a RED or missing
record) meets its un-park condition; that is an owner decision.
