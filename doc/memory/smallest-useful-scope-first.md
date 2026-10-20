---
name: smallest-useful-scope-first
description: Owner ruling — ship the smallest slice that meets the owner's goal, park the rest in the backlog until a trial shows it is needed
type: feedback
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "ตัดขอบเขตตามนี้เลย" after asking why the upgrade took so long; two PRDs (90 requirements, 19 increments) were run at once and 4 increments landed in a day
mechanism: none — applied by the coordinator when proposing PRDs; the backlog row status "parked" records each deferral
---

Scope kept: finish always-human guards and no-fake-green; no hand-written polling; machine-selected
handoff tier; merge gate; task orders (with whatever they need from mandate/reversibility/§5–6);
pilot trial. Parked until the trial shows need: suite hygiene, earned autonomy, absence mode, daily
digest, self-evolution.

**Why:** large parallel scope plus strict early targets multiplied rework and owner approvals; the
owner's two goals (agents close faster, Jarvis runs work) need only a few increments.

**How to apply:** for any new improvement, propose the minimal increment that moves the owner's
stated goal, ship and measure it, then decide the next. Related: [[ease-of-use-over-strictness]],
[[hostile-inputs-in-every-ac]].
