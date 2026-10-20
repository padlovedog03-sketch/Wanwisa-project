---
name: stay-on-the-definition
description: Owner ruling — Jarvis is defined as easy, correct, usable by other people, and smart enough to run work while the human waits for the result; gates defend against agent mistakes and shortcuts, not deliberate fraud
type: feedback
status: active
date: 2026-10-20
source: owner, 2026-10-20 — "เราเน้นให้จาวิสใช้งานง่ายและถูกต้อง ผู้ใช้งานท่านอื่นใช้งานได้สะดวกและใช้ได้ดี มีจาวิสอัจฉริยะคอยทำงานให้โดยมนุษย์สามารถรอดูผลลัพธ์ได้" then, after the merge gate went three review rounds chasing forgeries, "เริ่มไปไกลแล้วอย่าไปลึกเกิน ให้คงอยู่ตามนิยาม"
mechanism: .agents/skills/scope-discipline/SKILL.md rule 5 (threat model) — loaded by every role, reviewers and QA included
---

**The definition.** Jarvis is:
- easy to use;
- correct, meaning it never reports green without actually running;
- convenient for people other than the owner;
- a smart worker that carries a task through, so the human can wait for the result instead of watching each step.

Any work that does not move one of these four is out of scope.

**Threat model for gates.** A gate defends against what an agent does by mistake or as a shortcut:
- skipping or filtering tests;
- editing a gate script or a conf;
- a stray file that shadows a module;
- a stale record;
- leaked environment settings.

A gate does not defend against deliberately written fraud, such as test code or a conftest built to fake results, or a hostile environment. Those are recorded as one LIMIT line and controlled by a human reviewing the diff. They are never rework.

**Why:** the merge gate (verify-tiers D) went three review rounds. The later rounds were forgeries that only a deliberate attacker would write. This is the same chase the owner stopped for command guards in [[ease-of-use-over-strictness]]. Meanwhile the piece that lets the owner wait for results (task orders) sat in the queue. The owner was being reported to every few minutes.

**How to apply:**
- Reviewer and QA briefs state this threat model. A finding outside it goes under `Parked:` as a proposed LIMIT line, with no rework cause.
- The coordinator ships the increments that move the definition, and reports to the owner at the end of a task, not every step.
- Related: [[no-scope-creep]], [[smallest-useful-scope-first]].
