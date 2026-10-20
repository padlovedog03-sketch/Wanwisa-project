---
name: project-reds-belong-to-project-session
description: Red tests inside a project built on this framework are fixed by that project's own assistant session, not by work in this framework repo
type: project
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "งานแดงให้เป็นหน้าที่ของจาวิสที่ฝั่งแต่ละ G ไป"
---

Work in this repo changes the framework template only. When a measurement in a downstream
project turns up failing tests, report them and hand them to that project's own
session; do not fix them from here.

**Why:** each project has its own rules, approvals and in-flight work; fixing it from the
framework session crosses those boundaries.

**How to apply:** framework PRDs/specs list project-specific fixes as out of scope / follow-ups.
