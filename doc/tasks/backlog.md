# Backlog

Status: Living
Owner: pm
Upstream: doc/requirements/

Rows are in priority order, one deliverable per row, each linked to its PRD. The scope was re-cut by the owner on 2026-10-20 ("ตัดขอบเขตตามนี้เลย"; doc/memory/smallest-useful-scope-first.md): ship the smallest slice that meets the owner's two goals (agents close work faster, and the assistant runs the work), measure it in the pilot trial, and only then decide what comes next.

VT = [PRD-verify-tiers-merge-gate](../requirements/PRD-verify-tiers-merge-gate.md) · DA = [PRD-delegated-autonomy](../requirements/PRD-delegated-autonomy.md)

## Active

| Priority | Item | PRD | Status | Why this priority |
|---|---|---|---|---|
| 1 | VT Part J + J2: meter of active time per agent type and category, reported per size class | VT | Done (merged a724256, fd6efb2) | Every "after" number is measured with this. |
| 2 | VT Parts I and H: fewer model turns; less rework (affected tests in spec, engineer self-check, rework causes) | VT | Done (merged) | Rework is 23% of engineer runs. |
| 3 | VT Part A+C: the no-fake-green guarantee and a measurable `verify-full` | VT | Finishing under amendment am2 (SPEC-verify-tiers-merge-gate-am2-scanner-scope) | The handoff tier and the merge gate rest on it. |
| 4 | DA Part B: always-human guards | DA | Finishing under amendment am1 (SPEC-delegated-autonomy-am1-guards-catch-accidents) | Guards come before any freedom. Task orders (row 9) depend on it. |
| 5 | VT Part G: no hand-written polling | VT | In progress | Engineer runs lose 2.4 min to hand-written loops and 5.4 min to other waits, and the fix is small. |
| 6 | DA Part E, first half (E-AC1–E-AC4): learning loop, reviewer gate before QA, briefs carry the impact map | DA | In progress | Getting it right the first time cuts rework and owner corrections. |
| 7 | VT Part B: handoff tier with machine-selected tests | VT | Not started | Tests are 37% of engineer active time. |
| 8 | VT Part D: merge gate | VT | Not started | Replaces "verify-full before every handoff" for opted-in projects. Task-order merges (J-AC6) need it. |
| 9 | DA Part J: task orders, plus the minimum that orders need from F, A, G and C (listed below) | DA | Not started | Directly delivers the owner's "the assistant runs the work end to end". |
| 10 | Pilot trial: VT Part F and DA Part H, combined into one trial on the pilot project | VT + DA | Not started | Neither PRD is done until this trial passes. It runs last because it exercises rows 1–9. |

### Row 9: what task orders need (ACs from SPEC-delegated-autonomy)

- **J (active):** J-AC1 to J-AC7.
  - J-AC8 is parked, because it feeds the earned-autonomy score (C is parked).
  - Until C ships, an owner override of an order decision is recorded **only in that order's final report** (J-AC7). It narrows nothing. This is the parked part of R45 (J7).
  - J-AC6 (merge under an order) needs row 8 (VT Part D).
- **F (needed in full):**
  - F-AC1: work under autonomy happens on a branch or worktree.
  - F-AC2: every log entry carries a one-action reverse. J-AC7's final report needs this.
  - F-AC3 is already covered by B-AC3.
- **A (only these):**
  - A-AC3: the `approve-under` mechanism, exercised through `--order`.
  - A-AC4: checks (a), (b), (c), (f) and (g), applied to order stamps.
  - A-AC5: a stamp with no log entry fails.
  - A-AC6 (c): only the owner runs the owner scripts.
  - A-AC7: revocation, used by `revoke.sh <order key>`.
  - A-AC8: with no order or mandate present, every gate works exactly as it does today.
  - A-AC9: key revisions.
  - A-AC10: registry entry kinds.
- **G (only these):**
  - G-AC1, limited to the order wording: approvals trace to an order, which is exception (b) in §6.1.
  - G-AC2: the consistency check over the rule text being reworded.
- **C (dependency outside F/A/G, needs confirmation):**
  - C-AC1 and C-AC2 (the hash-chained decision log, with its tamper check) are needed by A-AC3, A-AC5, J-AC5 and J-AC7.
  - The rest of C stays parked.

## Parked — until the trial shows need (owner 2026-10-20)

| Item | PRD | Notes |
|---|---|---|
| VT Part E: test-suite hygiene (admission bar, retirement, red-main policy, named baseline) | VT | — |
| DA Part C: earned autonomy (override rate, widening, automatic narrowing) | DA | Exception: C-AC1 and C-AC2 (decision log) are pulled into row 9. While C is parked, R45 (J7) overrides go into the order's final report only. |
| DA Part K: absence mode | DA | — |
| DA Part D: daily digest | DA | — |
| DA Part I: continuous self-evolution | DA | — |
| DA Part E, second half (E-AC5, E-AC6): new tests must prove they catch bugs; depth matched to the task | DA | — |
| DA Part A, rest: A-AC1, A-AC2, A-AC4 (d) and (e), A-AC6 (a), (b) and (d) (the standing mandate itself) | DA | Task orders do not need a standing mandate. |
| DA Part G, rest: G-AC1 exceptions (a) mandate and (c) absence | DA | They follow when A or K is un-parked. |

**Not tracked here.** These follow-ups belong to the downstream project sessions (doc/memory/project-reds-belong-to-project-session.md): triage the pilot project's 30 red tests; render each PDF once; set the worker count; set up the runner and sharding; move structure-watching tests to lint; remove change-detector tests; split the layout model.
