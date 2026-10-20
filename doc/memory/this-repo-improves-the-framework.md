---
name: this-repo-improves-the-framework
description: Work in this repo is framework improvement only — making the template smarter and faster — never real project delivery
type: project
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "งานนี้เป็นงานปรับปรุง framework นะจำไว้ไม่ใช่งานจริง มีหน้าที่อัพเดท framework ของเราให้เก่งมากขึ้น"
---

The job here is to upgrade the framework template so every project built on it gets smarter and
faster. Downstream projects are used only as evidence: measuring them (read-only) and trialling
framework changes on an isolated copy. Their own features, bugs and red tests are not this repo's
work — see [[project-reds-belong-to-project-session]].

**Why:** the owner runs real delivery in each project's own session; mixing the two blurs
approvals and scope.

**How to apply:** every PRD/spec here describes framework behaviour (neutral, opt-in for
projects). When a finding is about a project, report it and hand it over; when it reveals a
framework gap, turn it into framework work.
