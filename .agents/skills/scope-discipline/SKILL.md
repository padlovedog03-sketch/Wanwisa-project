---
name: scope-discipline
description: Scope rules every role applies on every task — found is not done, every addition names what it displaces, edit only the files the brief lists, out-of-criteria observations go to the backlog, gates defend against mistakes not deliberate fraud. Use whenever you dispatch, accept or carry out any task.
---

# Scope Discipline

The framework rewards thoroughness, so without a brake every role widens the work a little — and
the widening compounds into rework, extra approvals and days lost. These five rules are the brake.
They apply to every role on every task, the coordinator included.

## The five rules

1. **Found is not done.** Anything you notice outside the task's criteria goes to the backlog as
   *parked*, in your handoff under `Parked:`. Fix it now only if it makes the work in front of you
   wrong (a bug in the code you are changing, a gate that would report green falsely through a
   mistake or shortcut — see rule 5).
2. **Every addition names what it displaces.** A proposal that adds a requirement, an AC, a file or
   a step must say what it removes or defers. The default answer to "should we also…" is **no**.
3. **Edit only the files the brief lists.** The brief's `Files:` line is the boundary. A file
   outside it needs one line of reason in the handoff (`Outside Files: <path> — <why>`); no reason,
   no edit.
4. **Observations outside the criteria go to the backlog, not back to the author.** QA and
   reviewers report them under `Parked:`; they are not rework and are not given a rework cause.
5. **Gates defend against mistakes, not fraud.** A gate must catch what an agent does by accident
   or as a shortcut. Examples:
   - skipped or filtered tests;
   - an edited gate script or conf;
   - a stray file shadowing a module;
   - a stale record;
   - leaked environment settings.

   Deliberately written fraud is different: test code or a conftest built to fake results, or a
   hostile environment such as a planted `unset` function or a fake `python3` on PATH. A gate is not
   expected to catch it. Reviewers and QA report it under `Parked:` as a proposed one-line LIMIT,
   never as rework; the control is a human reading the diff.

## In the handoff

Every handback ends its scope section with:

```
Parked: <items found and deliberately not done> | none
Outside Files: <path — reason> | none
```

## Why

On 2026-10-20 an upgrade asked as "tests are slow" grew into two PRDs with 90 requirements and 19
increments; pm, ba-sa, engineers, QA and the coordinator each added a little. The owner cut it back
to the few increments that meet the goal (`doc/memory/smallest-useful-scope-first.md`,
`doc/memory/no-scope-creep.md`).
