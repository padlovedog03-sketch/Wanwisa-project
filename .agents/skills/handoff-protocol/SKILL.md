---
name: handoff-protocol
description: File-based handoff conventions between the PM, BA/SA, AI Engineer, and QA agents. Use when producing or consuming any document in doc/ so the next agent in the pipeline can pick up work without extra context.
---

# Handoff Protocol

Agents share no memory — all context passes through files in `doc/`. A handoff is complete only when the next agent could start from the files alone.

## Pipeline and Ownership

```
PM ──PRD──▶ 👤 ──▶ BA/SA ──spec+design──▶ 👤 ──▶ AI Engineer ──code+tests──▶ 👤 ──▶ QA ──report──▶ 👤 ──▶ Done
                                                        ▲                                │
                                                        └──────── fail: defects ─────────┘
```

Every `👤` is a **human approval gate** — no stage starts until the human has approved the previous stage's artifact.

| Directory | Owner | Artifact | Naming |
|---|---|---|---|
| `doc/requirements/` | pm | PRD | `PRD-<feature-slug>.md` |
| `doc/tasks/` | pm | Backlog | `backlog.md` |
| `doc/specs/` | ba-sa | Functional spec | `SPEC-<feature-slug>.md` |
| `doc/architecture/` | ba-sa | Technical design / ADR | `DESIGN-<feature-slug>.md` |
| `doc/qa/` | qa | QA report | `QA-<feature-slug>.md` |

Use the same `<feature-slug>` (lowercase, hyphenated) across the whole chain so artifacts link up.

## Document Rules

1. **Always start from the template** in `doc/templates/`. Don't invent your own structure.
2. **Status header** at the top of every document:
   `Status: Draft | In Review | Approved | Done`
3. **Upstream link**: every document names the file it derives from (spec → PRD, design → spec, QA report → spec). A document with no upstream link is an orphan — fix it.
4. **Only the owner edits.** Found a problem in another role's document? Report it in your handoff message; don't edit it yourself.

## Human Approval Gate

Status lifecycle: `Draft` → `In Review` → `Approved` → `Done`. Only the **human** (via the orchestrator) moves a document past `In Review`.

Rules for every agent:

1. **Before starting**: read your upstream document's status header. If it is not `Status: Approved`, STOP immediately and report: "Upstream <file> is at <status> — needs human approval before I can start." Do not work from unapproved input.
2. **When finishing**: set your own artifact to `Status: In Review` — never `Approved`, even if you're confident. Approving your own work defeats the gate.
3. **Revisions**: if the human requests changes, revise the same document (keep `Status: Draft` while working, back to `In Review` when done).
4. **AI Engineer stage** (no document artifact): the code diff + handoff message is the review artifact; the orchestrator must get human approval before invoking `qa`.

## Handoff Message

Your final message when finishing a task must contain:

1. **Artifacts**: exact paths of files created/modified.
2. **Evidence**: verification results (from the engineering loop).
3. **Assumptions**: anything you decided that the human or next agent should know.
4. **Next step**: which agent should act next and on what input.
5. **Could not reach**: every file, service, access right or tool you needed and did not have — or `none`.
6. **Substituted**: everything you mocked, stubbed or guessed in place of the real thing, and why — or `none`.

Fields 5-6 exist because a workaround done in silence reads exactly like a clean result
(`doc/framework/WHY.md` §2). If something you need is missing, the default is **stop and name it** —
never substitute it silently. `none` is a valid answer; an empty or missing field is not. The
coordinator checks the shape with `python3 scripts/handback_lint.py -` (presence only, never truth).

**Engineers add a `Self-check:` block** (`ai-engineer`, `frontend-engineer`; R30): one line per
acceptance criterion in the spec, ending at the first blank line.

```
Self-check:
- AC1: pytest tests/test_x.py::test_y → 1 passed
- AC2: scripts/verify-full.sh → EXIT GATE GREEN
```

Every AC of your increment gets a line with a command and a result; an unfinished one gets `not done`
as its result, which the lint lists as open, never as met. Check it with
`python3 scripts/handback_lint.py --spec <spec> --only <prefix> -`, where `<prefix>` is your increment's
AC-id prefix (`H-` for `H-AC1`, `AC-` for `AC-AC1`; repeat `--only` for more than one). It names each
of those ACs with no line, no command or no result. Without `--only` every AC in the spec is required,
and a prefix that matches no AC exits 2. Again presence only: the lint cannot tell whether the command
was really run.

## Rework dispatch

When QA returns FAIL and the engineer is sent back, that is a **new dispatch**, and its first message
carries the QA report on a line of its own:

```
REWORK: doc/qa/QA-<feature-slug>.md
```

The meter (`scripts/agent_time.py --rework`) counts a run as rework only when the **first message** of
that run has a line starting `REWORK:` (ADR-13). A correction sent as a follow-up message into an
engineer run that is already going is never counted, so a rework sent that way disappears from the
rework share.
