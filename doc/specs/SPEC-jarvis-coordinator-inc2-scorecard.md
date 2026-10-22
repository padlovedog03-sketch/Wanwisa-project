# SPEC: Jarvis coordinator, Increment 2: the scorecard (R9–R10)

Status: Approved
Approval: spec-jarvis-coordinator-inc2-scorecard-2026-10-22
Owner: ba-sa
Upstream: doc/requirements/PRD-jarvis-coordinator.md (Approved, `prd-jarvis-coordinator-2026-10-20`, R9, R10, M1–M7) · doc/specs/SPEC-delegated-autonomy.md H-AC1 (Approved; its owner-message rule is pulled forward here) · doc/specs/SPEC-verify-tiers-merge-gate.md Part J (the meter `scripts/agent_time.py` and its reader contract) · doc/tasks/backlog.md Active row 9 and checklist A4 · owner rulings 2026-10-22: doc/memory/jarvis-decides-self-improvement.md, doc/memory/easy-and-end-to-end.md
Date: 2026-10-22

## Overview

The scorecard is one report-only flag on the existing meter: `python3 scripts/agent_time.py --reader <reader> --dir <transcripts> --scorecard [--since T] [--until T]`. It prints M1–M7 for a time window, per tier where the metric is per task. It never gates, and it always exits 0. It is the same meter, reader and limits as today, so this adds no second transcript reader (R10).

This spec also **records the BEFORE baseline now**, in the "Baseline" section below. The numbers come from a scratch probe that applies the counting rules of this spec. The probe ran on 2026-10-22, before task orders (DA Part J, backlog row 5) change how work runs. The baseline is recorded now for two reasons:
- once orders land, the per-step-approval way of working is gone, so no new "before" data can arise;
- the transcripts it was measured on may be deleted by the adapter's retention.

The shipped instrument must reproduce these numbers (SC-AC9).

**Size:** Medium. Two source files and two test files, plus fixtures. About 60–90 minutes of engineer time.

**Markers:**
- `[MEASURED: <cmd>]`: I ran the command on 2026-10-22 at HEAD `96bebdb`.
- `[MEASURED: probe]`: `scratchpad/inc2/baseline_probe_v2.py` (sha256 `74b090ca…b971677`), run read-only over this repo's adapter-ก transcript directory: 109 transcript files, 5 main-thread sessions, run at about 09:15 UTC. It applies the rules below exactly: the Tier regex with NFKC, the field-line grammar for M6, the first *clock* event for subagent windows, and the M3 path rule. Its output is byte-identical to an earlier, looser variant, so the numbers do not hinge on those details. It is scratch and dies with the session, so every rule it applied is written out in this spec.
- `[INFERRED]`: I read it but did not run it.
- `[RELAYED]`: taken from another document.

## What the scorecard measures, and how

There are four ideas:
- **owner message**;
- **exchange**: one owner message and everything until the next one;
- **turn end**: a Jarvis message to the owner;
- **Tier line**.

M1, M4 and the per-day owner count are built on them. M3 and M6 read subagent runs. M2 and M7 come from `scripts/correction_rate.py`. M5 is not measured by this command.

| Metric | What is printed | Rule | Proxy or exact |
|---|---|---|---|
| M1 owner interruptions per task | Per tier (0, 1, 2, untiered): exchanges; **extra Jarvis messages** in total; mean per exchange (2 decimals); exchanges with none. A tier with no exchanges prints `no exchanges`, never `0`. | For each exchange: extra = max(0, distinct turn ends in the exchange − 1). | **Upper bound.** Every extra turn end counts. A tier-2 gate stop or an R5 decision usually ends an exchange, because the owner replies. One that does not is counted as an interruption. Each owner message is treated as one task. |
| M2 owner-correction rate | `L in the 7 days to <date> (previous 7: P, down / flat / NOT down)` | `correction_rate.measure(memory_dir, date)`, where date = the UTC date of the last instant before `--until` | Exact, same as the script |
| M3 rounds per increment | Per report slug: `review R · QA Q`. Median of R and of Q over slugs. Runs that wrote no report are counted on their own line. | A `reviewer` run, or a `qa` / `frontend-qa` run, counts once for every slug `S` it edited a report for. The edit paths come from the reader's existing `Event.paths`. A path counts if it matches `(?:^|/)doc/qa/(?:REVIEW|QA)-(.+)\.md$`, and the slug `S` is group 1. A worktree path counts too. `S` is printed only through the label rule. | Exact for runs that write their report. Source changed: see SC-ADR-2. |
| M4 time to first result | Per tier: median minutes (1 decimal) and n; exchanges with no result, counted on their own | From the owner message to the first turn end in the exchange that comes after at least one tool result in the same exchange | **Proxy.** "Evidence" means any tool result before the reply. Content is not judged. |
| M5 new-user setup time | `M5 new-user setup time: not measured by this command (timed by hand, R12)` | — | Never prints a number |
| M6 dispatch completeness | `A of B role-agent briefs carry a Tier: line and a Files: line` | Role types: `pm`, `ba-sa`, `ai-engineer`, `frontend-engineer`, `reviewer`, `qa`, `frontend-qa`. Brief = the run's first inbound text. Presence only: a field line (plain, bulleted, numbered or bold) for `Tier` and one for `Files`. Values are not judged. | Exact for presence. After Increment 1 it is 100% by construction where the guard intercepts, because a refused spawn leaves no subagent transcript. |
| M7 lessons with no mechanism | `N lesson(s) since 2026-10-08 with no mechanism` | `correction_rate.measure(...)["unmechanised"]` | Exact. It is the state of `doc/memory/` now, not windowed. |
| (H-AC1) owner messages per day | `owner messages per day (UTC): 2026-10-20 74 · …` | Count of owner messages by UTC date | Exact under the owner rule |

**Definitions.** The reader computes the parts that depend on the adapter's format. The core counts only neutral events.

- **Owner message.** An inbound event that the reader marks `owner=True`. Adapter ก's reader marks a main-thread `user` line `owner=True` only when all three hold:
  - its `message.content` is a plain string;
  - the string does not start with `<`;
  - `isMeta` is not `true`.

  This is H-AC1's rule. It excludes task notifications, command echoes, meta lines and tool results. In the window before Increment 1 it also excluded 2 user lines with list content: one is `isMeta` and the other is a 29-character line starting `[` `[MEASURED: probe]`. Subagent inbound lines are never `owner`: they are briefs from Jarvis.
- **Exchange.** It starts at an owner message and runs to the next owner message in the same run, or to the end of the run, or to `--until`. An exchange belongs to the window that contains its owner message. Events at or after `--until` are ignored, so a session that is still live gives the same answer on every replay.
- **Turn end.** A `model` event that the reader marks `turn_end=True`. Adapter ก marks an assistant line whose `message.stop_reason` is `end_turn`. Turn ends are counted once per **distinct `message_id`**, because one response spans up to 2 lines: 233 `end_turn` lines against 174 distinct ids in the largest session `[MEASURED: python3 probe over the 5 main-thread files]`. A turn-end event with no id counts as one turn end.
- **Tier of an exchange.** Take the first Jarvis model event in the exchange whose text, after NFKC, has a line matching `^[ \t]*(?:(?:[-*]|\d+\.)[ \t]+)?(?:\*\*)?Tier(?:\*\*)?[ \t]*:(?:\*\*)?[ \t]*([012])`. Its value is the tier. If no such line exists, the exchange is `untiered`. A `Tier:` inside the owner's own text never counts.

**Window.** `--since` and `--until` each take `YYYY-MM-DD` (midnight UTC) or `YYYY-MM-DDTHH:MM:SSZ`. The window includes `since` and excludes `until`. The defaults are 1970-01-01 and now. A subagent run belongs to the window that contains its **first** event (the brief), not its last. A brief never moves, so the count is stable while the run is still going. The existing time report keeps its own rule (last event), unchanged.

**What is never printed.** The output never contains any owner text, Jarvis text or brief text. Slugs are printed only if they match the existing label rule (`[A-Za-z0-9_.:-]{1,64}`), and anything else prints as `(unprintable label)`.

## Baseline (BEFORE), recorded 2026-10-22

There are two windows, both in UTC.
- **W0, before Increment 1:** `[2026-10-01T00:00:00Z, 2026-10-21T02:03:54Z)`. The upper bound is the merge time of Increment 1, commit `1057355` (`2026-10-21 09:03:54 +0700`) `[MEASURED: git log -1 --format=%ci 1057355]`.
- **W1, after Increment 1 and before task orders:** `[2026-10-21T02:03:54Z, 2026-10-22T09:00:00Z)`.

All numbers are `[MEASURED: probe]`, except M2 and M7, which are `[MEASURED: python3 -c "correction_rate.measure(Path('doc/memory'), date(2026,10,21|22))"]`.

| Metric | W0 (before Increment 1) | W1 (after Increment 1, before orders) |
|---|---|---|
| Owner messages | 76 | 8 |
| M1 tier 0 | — (no Tier lines existed) | 1 exchange · 8 extra · mean 8.00 · 0 with none |
| M1 tier 1 | — | no exchanges |
| M1 tier 2 | — | 2 exchanges · 0 extra · mean 0.00 · 2 with none |
| M1 untiered | 76 exchanges · 103 extra · mean 1.36 · 46 with none | 5 exchanges · 17 extra · mean 3.40 · 4 with none |
| M2 | 6 in the 7 days to 2026-10-21 (previous 7: 1, NOT down) | 7 in the 7 days to 2026-10-22 (previous 7: 0, NOT down) |
| M3 | 11 slugs · review median 0 · QA median 1 · max total 3 (`verify-tiers-merge-gate-B` 2+1, `verify-tiers-merge-gate-D` 2+1) · 5 runs wrote no report | 6 slugs · review median 1 · QA median 1 · max total 4 (`bugfix-gate3-worktree` 3+1) · 4 runs wrote no report |
| M4 | untiered: n 54, median 0.6 min · 22 with no result | tier 0: n 1, 7.0 min · tier 2: n 1, 0.4 min, 1 no result · untiered: n 1, 2.1 min, 4 no result |
| M5 | not measured. RELAYED estimate: ~27 min (PRD) | same |
| M6 | 7 of 60 | 30 of 30 |
| M7 | 0 | 0 |

**Reading the baseline honestly:**
- **There is no per-tier figure for W0.** No exchange before Increment 1 carries a `Tier:` line, so W0 can only be compared with W1 and later as "all exchanges".
- **W1 is small:** 8 owner messages. Its tier-0 exchange is the B1 bugfix, with 8 extra messages. That is the incident behind doc/memory/easy-and-end-to-end.md.
- **M3 and the PRD differ.** For Part D, the PRD says "3 review rounds" `[RELAYED]`, while the probe counts 2 reviewer runs that wrote `REVIEW-verify-tiers-merge-gate-D.md`. The third reviewer run for D wrote no report file, so it is in "wrote no report". The known answer for gate3 matches: 3 reviews and 1 QA, as in backlog item B1.
- **M2 rose:** 6 then 7 corrections. The number is reported, not judged here.
- **M2 and M7 are not frozen.** They read the working `doc/memory/`, not a commit, and they are date-granular. The baseline is pinned to `doc/memory/` at `96bebdb`. A feedback lesson recorded later with a date of 2026-10-22 or earlier changes W1's M2, for example from 7 to 8. That is an expected SC-AC9 difference: the handback names the file.
- **Per-tier M1 covers only exchanges where Jarvis restated the tier.** An owner follow-up inside one task, such as a gate reply or "go ahead", gets a reply with no Tier line, so it lands in `untiered`. In W1, 5 of 8 exchanges are untiered. After Increment 1, `untiered` therefore mixes tiers, and a per-tier figure undercounts later exchanges of the same task. This goes on the `limits:` line. A "sticky" tier, which carries the last stated tier forward, would change the measured baseline, so it is not adopted here.

**Retention deadline.** No `cleanupPeriodDays` is set in the adapter's user settings `[MEASURED: grep -l cleanupPeriodDays ~/.claude/settings*.json .claude/settings*.json → no match]`. The adapter's default retention then applies; I believe it is 30 days `[INFERRED: adapter documentation, not measured]`. So the oldest W0 sessions (2026-10-08) may be deleted from about 2026-11-07. **SC-AC9 must run before 2026-11-06.** After that date, this table is the only record of the baseline.

## Acceptance Criteria

Fixtures are neutral JSON for the stub reader (`tests/framework/fixtures/agent_time/`) unless a criterion names the real reader. Every scorecard criterion also asserts exit 0.

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| SC-AC1 | R9 | **Given** a fixture with one main-thread run and some role-agent runs, **When** `--scorecard` runs, **Then** the output prints one line or block for each of M1–M7 and the per-day owner line, in that order, and prints nothing from the time report.<ul><li>M5 reads exactly `not measured by this command`.</li><li>A tier with no exchanges reads `no exchanges`.</li><li>`--scorecard` combined with `--rework`, `--targets`, `--min-runs` or `--include-probes` prints one `agent-time: error: --scorecard runs alone` line.</li><li>`--until` without `--scorecard` prints `agent-time: error: --until needs --scorecard`.</li></ul>**Hostile:**<ul><li>an empty directory prints every metric as "no …", never `0` for M1, M3, M4 or M6;</li><li>no `--reader` prints the existing `unsupported` line and no scorecard.</li></ul> | tests/framework/test_agent_time.py |
| SC-AC2 | R9, R10 (H-AC1 rule) **RED-FIRST** | **Given** a real-format transcript fixture for adapter ก, whose main thread holds 3 owner lines, 2 `<task-notification>` lines, 1 `<command-name>` line, 1 `isMeta: true` plain-string line, 1 list-content text line and 4 tool-result lines, **When** the scorecard runs through `.claude/meter/transcript_reader.py`, **Then** it reports exactly 3 owner messages and 3 exchanges. **Planted mistake:** a reader that marks every inbound `user` line as owner. It must make this test red (H-AC1's own mutation). The engineer pastes the red line. | tests/hooks/test_transcript_reader.py |
| SC-AC3 | R9 (M1) **RED-FIRST** | **Given** one exchange whose single reply spans 2 assistant lines with the same `message.id`, both `stop_reason: end_turn`, followed by a notification and a second reply with a new id, **When** the scorecard runs, **Then** M1 counts 2 turn ends and 1 extra. **Planted mistake:** counting turn ends per line gives 3 and 2, and must be red. **Hostile cases:**<ul><li>a turn end with no `message.id` counts as 1 and does not crash;</li><li>a `stop_reason` of `tool_use` is not a turn end;</li><li>a `stop_reason` that is not a string is not a turn end;</li><li>an assistant line with no timestamp is excluded, as today.</li></ul> | tests/hooks/test_transcript_reader.py (reader marks), tests/framework/test_agent_time.py (core counting) |
| SC-AC4 | R9 (per tier) | **Given** exchanges whose first Jarvis text holds, in turn:<ul><li>`Tier: 1 — x`;</li><li>`- **Tier:** 2 — y`;</li><li>`Please state the Tier: 0 line` (mid-sentence);</li><li>no Tier line;</li><li>a Tier line only in the owner's message;</li><li>`Tier: 3`;</li><li>`Tier：0` (full-width colon, read after NFKC, as the guard reads it);</li></ul>**When** the scorecard runs, **Then** they fall into tier 1, tier 2, untiered, untiered, untiered, untiered and tier 0. **And** a later Tier line in the same exchange does not change the first one. | tests/framework/test_agent_time.py |
| SC-AC5 | R9 (window) | **Given** a main-thread run with owner messages at T−1h, T and T+1h, with replies straddling `--until`, **When** `--since T --until T+30m` runs, **Then** exactly one exchange is counted. Its turn ends at or after `--until` are ignored, and the exchange of the T−1h message is not counted, even though its reply falls inside the window. A subagent run whose first event is before `--since` and whose last event is inside the window is not counted for M3 or M6. **Hostile:**<ul><li>`--until` equal to or earlier than `--since`;</li><li>a malformed time (`2026-10-22 09:00`, `2026-10-22T09:00:00+07:00`, `2026/10/22`);</li></ul>each prints one `agent-time: error: …` line, exit 0. `YYYY-MM-DD` keeps working for `--since`, and the existing `2026/10/01` refusal test stays green. | tests/framework/test_agent_time.py |
| SC-AC12 | R9 (M4) | **Given** these exchanges, **When** the scorecard runs, **Then** each gives the stated M4 result:<ul><li>(a) owner message at 0 s, a tool result at 30 s, then a turn end at 90 s: 1.5 min.</li><li>(b) owner message, a turn end at 10 s, a tool result at 20 s, a turn end at 60 s: 1.0 min. The first reply came before any result, so it does not count.</li><li>(c) owner message and a turn end with no tool result: counted under "no result", and not in the median.</li><li>(d) a tool result **before** the owner message, then a turn end: "no result". Only results inside the exchange count.</li></ul>The median is printed to 1 decimal per tier. A tier where every exchange has no result prints `no result: N` and no median. | tests/framework/test_agent_time.py |
| SC-AC6 | R9 (M3) | **Given** reviewer runs editing `/w/.claude/worktrees/agent-x/doc/qa/REVIEW-a.md` (twice in one run), `doc/qa/REVIEW-a.md`, `doc/qa/QA-a.md`, and a reviewer run that edits nothing, **When** the scorecard runs, **Then** M3 prints `a: review 2 · QA 1` and `1 run wrote no report`. **Hostile:**<ul><li>an engineer run editing `doc/qa/QA-a.md` is not counted, because only review and QA types count;</li><li>`doc/qa/REVIEW-.md` and `doc/qa/REVIEW-a.md.bak` are not slugs;</li><li>a slug longer than 64 characters, or one holding a space or `/`, prints as `(unprintable label)` and writes no line of its own;</li><li>a path with a newline before `.md` does not match, so the run counts under "wrote no report";</li><li>a run with a pathless edit counts under "wrote no report" and does not crash.</li></ul> | tests/framework/test_agent_time.py |
| SC-AC7 | R9 (M6) | **Given** role-agent runs whose briefs are:<ul><li>`Tier: 1 — x\nFiles: a`;</li><li>`- **Tier:** 2\n- Files:\n  - a`;</li><li>`Files: a` only;</li><li>`Tier: 1` only;</li><li>`see the Tier: 1 and Files: a lines` (mid-sentence);</li></ul>plus an `Explore` run with neither line, **When** the scorecard runs, **Then** M6 prints `2 of 5`. The non-role run is not counted. A run with no inbound event counts as a brief without the lines. | tests/framework/test_agent_time.py |
| SC-AC8 | R9 (M2, M7) | **Given** a memory directory with feedback entries dated 3 and 9 days before `--until`, and one entry with no `mechanism:` dated after 2026-10-08, **When** the scorecard runs with `--memory-dir`, **Then** M2 prints `1 in the 7 days to <date> (previous 7: 1, flat)` and M7 prints `1`. **Hostile:**<ul><li>a missing directory prints `M2, M7: memory directory not found` and never `0`;</li><li>a memory file that is not UTF-8 prints `M2, M7: not measured (unreadable memory file)`, and M1, M3, M4 and M6 still print;</li><li>no traceback in either case.</li></ul> | tests/framework/test_agent_time.py |
| SC-AC9 | R9 (baseline), R10 | **Given** this repo's adapter-ก transcript directory, on the owner's machine before 2026-11-06, **When** the engineer runs `--scorecard` with W0's bounds and then with W1's, **Then** every number in the Baseline table is reproduced, **or** the handback names each difference and its cause (for example, a transcript the adapter deleted). The engineer pastes both outputs. The output carries counts only. | manual, pasted in the engineer handback. Transcripts are private and never become a fixture. |
| SC-AC10 | R9 (never leaks) | **Given** fixtures whose owner text, Jarvis text, brief text and a non-slug edit path all contain the canary `CANARY-7f3a`, **When** the scorecard runs, **Then** `CANARY-7f3a` appears nowhere in stdout or stderr. **And** an internal failure prints only `agent-time: internal error: <type>`, as today. | tests/framework/test_agent_time.py |
| SC-AC11 | R10 (one instrument) | **Given** the meter without `--scorecard`, **When** the existing suites run, **Then** every existing output is byte-identical. `test_agent_time.py`, `test_transcript_reader.py` and the two `test_regression_agent_time_*` files stay green with no edits to existing tests. The new `Event` fields (`owner`, `turn_end`) default to `False`, and model events may now carry `text`, which the time report never reads. `[MEASURED: proto — in a git-archive copy of 96bebdb, I added both fields, set turn_end and text on model events and owner on plain-string inbound lines in the reader; the four files gave 246 passed, the same as HEAD]` | the four files named |

## Functional Behavior

**Reader contract additions** (`scripts/agent_time.py` docstring, `Event`):

```python
@dataclass(frozen=True)
class Event:
    ...                      # unchanged fields
    owner: bool = False      # inbound only: the reader judged this an owner message (H-AC1)
    turn_end: bool = False   # model only: this response ended the turn (a message to the owner)
    # `text` (existing) may now also be set on model events: the response's text, for Tier lines. Never printed.
```

Changes to adapter ก's reader (`.claude/meter/transcript_reader.py`, in `_events_of` and `_read_run`):
- A main-thread `user` line whose content is a plain string not starting with `<`, and whose record has no `isMeta: true`, becomes `Event(t, "inbound", text=…, owner=True)`. `_read_run` needs the record, not just the message, to see `isMeta`, and it needs to know whether the run is the main thread.
- An assistant line gets `turn_end = (message.get("stop_reason") == "end_turn")`, and `text` is set to its text blocks joined.

**Core** (`scripts/agent_time.py`), pseudocode:

```python
def scorecard(runs, since, until, memory_dir) -> str:
    events_in = lambda r: [e for e in r.events if e.t < until]
    exchanges = []                                   # (tier, extra, minutes_to_first_result | None, day)
    for r in runs:
        ev = events_in(r)
        for start, end in owner_message_spans(ev):   # owner event → next owner event / end
            if not since <= ev[start].t < until: continue
            ...count distinct turn-end ids, first Tier line, first turn end after a tool_result...
    role_runs = [r for r in runs if r.agent_type in ROLE_TYPES and r.events
                 and since <= r.events[0].t < until and not is_probe(r)]
    ...M3 from review/QA runs' edit paths; M6 from _first_inbound_text...
    try: m = correction_rate.measure(memory_dir, (until - 1µs).date())
    except (OSError, UnicodeDecodeError, ValueError): ...print "not measured"
    return block
```

The engineer may shape it differently. The criteria are the contract.

**Output shape** (illustrative; the labels are fixed by the criteria):

```
scorecard — window [2026-10-21T02:03:54Z, 2026-10-22T09:00:00Z) · reader: transcript_reader.py · unreadable lines: 0
M1 extra Jarvis messages per owner message (upper bound: gate stops and owner decisions are not told apart)
  tier 0: 1 exchanges · 8 extra · mean 8.00 · 0 with none
  tier 1: no exchanges
  ...
M2 owner corrections: 7 in the 7 days to 2026-10-22 (previous 7: 0, NOT down)
M3 review and QA runs per report slug: review median 1 · QA median 1 · 4 runs wrote no report
  bugfix-gate3-worktree: review 3 · QA 1 · ...
M4 minutes from owner message to first reply after a tool result: tier 0 7.0 (n 1) · ... · no result: 5
M5 new-user setup time: not measured by this command (timed by hand, R12)
M6 role-agent briefs with a Tier: line and a Files: line: 30 of 30
M7 lessons with no mechanism: 0
owner messages per day (UTC): 2026-10-21 1 · 2026-10-22 7
method: …   limits: …
```

The `limits:` line states:
- M1 is an upper bound and treats one owner message as one task;
- an exchange with no Tier line in Jarvis's reply is `untiered`, even inside a tiered task;
- M2 reads the working memory folder, by date;
- M4's "result" is any tool result;
- M3 counts only runs that edit their report file;
- M6 checks presence only and is 100% by construction where the guard intercepts;
- M7 is not windowed;
- the transcripts the adapter keeps decide how far back any figure can go.

**Threat model (scope-discipline rule 5).** This is a report. It must not crash, leak or print a misleading zero on odd input. It does not defend against transcripts edited to flatter the numbers.

## What this increment explicitly does not do

- **No gate and no target judgement.** It prints numbers and never compares them with the PRD targets. The owner reads them.
- **Not all of H-AC1.** Only H-AC1's owner-message rule (with its planted mistake) and the per-day count are pulled forward. Owner messages **per feature** (registry and log windows by slug) and approvals by basis stay with DA Part H in backlog row 12. M1–M7 do not need them. See SC-ADR-3.
- **No false-green rate (checklist A4).** It is dropped and parked. See SC-ADR-4.
- **No M5 timing.** M5 is timed by hand with a first-time user in Increment 4 (R12).
- **No meaning checks.** It does not judge whether a reply carries real evidence, whether a turn end was a legitimate gate stop, or whether a `Files:` value is right.
- **No new reader, no new adapter support.** Adapter ข stays `unsupported`.
- **No change to `scripts/correction_rate.py`.** It is imported, not edited.

## Decisions (ADR-style)

- **SC-ADR-1: M1 is "extra Jarvis messages per owner message", an upper bound.**
  - **Context:** The PRD's M1 excludes gate stops, R5 decisions and the final report. Telling those apart needs the meaning of a message. The PRD defers meaning checks (nice-to-have list).
  - **Decision:** Count the turn ends beyond the first in each exchange. A gate stop or an owner decision normally ends the exchange, because the owner answers, so it is not counted. Only an unanswered one inflates the count.
  - **Consequences:**
    - The number can only overstate interruptions, never hide them.
    - The tier-0/1 target "0 per task" becomes "0 extra per exchange", which is directly readable.
- **SC-ADR-2: M3 is counted from review and QA runs that edit their report, not by parsing `doc/qa/`. This needs human review: it changes the PRD's stated source.**
  - **Context:** The PRD says "counted from `doc/qa/`". The files record rounds in at least four shapes:
    - `## Verdict:`;
    - `### Verdict:` under `## Re-test N`;
    - `### Round 2 — …, result PASS`;
    - history bullets.

    Some rounds overwrite the file. `REVIEW-verify-tiers-AC.md` holds 1 `Verdict` line for 3 rounds, and `REVIEW-…-merge-gate-D.md` holds 2 `Verdict` lines for one current verdict `[MEASURED: grep -nE "Verdict|[Rr]ound [0-9]|Re-test" doc/qa/*.md]`.
  - **Decision:** Count runs instead, keyed by the report file each run edits. The meter already reads those paths.
  - **Consequences:**
    - R10 holds: there is no second parser.
    - A run that reports only in its handback is counted under "wrote no report" rather than lost.
    - If the owner wants the `doc/qa/` source kept, the alternative is a fixed `Verdict` grammar, which must first be imposed on the templates. That is a larger change.
- **SC-ADR-3: pull forward only the part of H-AC1 that M1–M7 use.**
  - **Context:** R10 "pulls DA H-AC1 forward". H-AC1 also asks for per-feature windows from the approval registry and approvals by basis. Neither feeds M1–M7, and "by basis" (mandate, order) has no data until task orders exist.
  - **Decision:** The owner rule and the per-day count ship here. The per-feature part stays in backlog row 12.
  - **Consequences:** The coordinator should change row 12's wording from "less H-AC1" to "less H-AC1's owner rule". I cannot edit the backlog: it is outside my `Files:` (Parked).
- **SC-ADR-4: drop the false-green rate (A4) and park it.**
  - **Context:** The brief allowed it only if it is cheap from existing records. No fixed failure-scenario set exists as a record. The fake-green routes live as regression tests inside the suite, in 3 test files and 5 QA or review reports that mention false or fake green `[MEASURED: grep -rlni "false.green\|fake.green" tests/ doc/qa/ scripts/]`. Those tests must already be green, so a rate over them reads 100% whenever verify passes, which tells us nothing. A real rate needs a new, separately run scenario set.
  - **Decision:** Not in this increment. Park it with that reason.
  - **Consequences:** The scorecard stays M1–M7 as the PRD lists them.
- **SC-ADR-5: the scorecard is a mode of `agent_time.py`, and runs alone.**
  - **Context:** R10 calls for one instrument.
  - **Decision:**
    - `--scorecard` replaces the time report rather than appending to it, so both outputs keep a fixed shape.
    - `--until` exists only for the scorecard, so the time report's existing window rule is not touched (SC-AC11).
  - **Consequences:** Two new error lines (SC-AC1). Comparing time and scorecard needs two runs.
- **SC-ADR-6: subagent runs are windowed by their first event, and exchanges by their owner message.**
  - **Context:** The meter windows runs by their last event, which moves while a session is live. Two of the baseline windows end inside a live session.
  - **Decision:** Window by the event that cannot move.
  - **Consequences:** The baseline replays exactly. It differs from the time report's rule, and the `method:` line says so.

## Affected tests / affected files

**How this list was built** (all `[MEASURED]` at `96bebdb`):
- `grep -rln "agent_time\|transcript_reader\|correction_rate" tests` returned 9 files:
  - `tests/framework/fixtures/agent_time/neutral_reader.py`;
  - `tests/framework/test_agent_time.py`;
  - `tests/framework/test_correction_rate.py`;
  - `tests/framework/test_doc_contracts.py`, which reads `agent_time.REWORK_CAUSES` only (line 181);
  - `tests/framework/test_learning_loop.py`;
  - `tests/framework/test_settings_deny.py`, which asserts that `correction_rate.py` runs at session start (line 39);
  - `tests/hooks/test_regression_agent_time_reader.py`;
  - `tests/hooks/test_regression_agent_time_size_class.py`;
  - `tests/hooks/test_transcript_reader.py`.
- `grep -n "Event("` in those tests: every construction uses keywords, so two new fields with defaults keep them valid `[INFERRED from the grep lines]`.
- The stub reader builds `Event(**fields)` from the fixture JSON, so the new fields need no code change there `[INFERRED: read neutral_reader.py lines 20–35]`.

**One owner per file.** Every file below belongs to this increment only. SPEC-jarvis-coordinator-am2-brief-labels touches none of them, and this increment touches none of its four files. There is no merge order to set.

| File | Change | Whose behaviour changes |
|---|---|---|
| `scripts/agent_time.py` | `Event.owner`, `Event.turn_end`; `--scorecard`, `--until`, `--memory-dir`; time-of-day parsing; `scorecard()`; docstring usage and reader contract | New report mode only (SC-AC11) |
| `.claude/meter/transcript_reader.py` | marks `owner` and `turn_end`; sets `text` on model events | Reader output gains fields; the time report is unchanged |
| `tests/framework/test_agent_time.py` | SC-AC1, SC-AC3 (core), SC-AC4–SC-AC8, SC-AC10, SC-AC12 | — |
| `tests/framework/fixtures/agent_time/` (new JSON fixtures) | scorecard fixtures | — |
| `tests/hooks/test_transcript_reader.py` | SC-AC2, SC-AC3 (reader) | — |
| `tests/hooks/fixtures/transcripts/` (new fixture files) | the real-format SC-AC2 and SC-AC3 transcripts | — |

**Must stay green, unchanged:**
- `tests/hooks/test_regression_agent_time_reader.py`;
- `tests/hooks/test_regression_agent_time_size_class.py`;
- `tests/framework/test_correction_rate.py`;
- `tests/framework/test_doc_contracts.py`;
- `tests/framework/test_learning_loop.py`;
- `tests/framework/test_settings_deny.py`.

**Not touched:**
- `scripts/correction_rate.py`;
- `doc/framework/ADAPTERS.md`: the R37 row already names the meter and its reader, and the scorecard's limits print in its own output;
- the PRD;
- the backlog (see SC-ADR-3 and Parked).

## Traceability

- R9 (one report-only command, M1–M7, per tier, baseline then comparison) → SC-AC1, SC-AC3, SC-AC4, SC-AC5, SC-AC6, SC-AC7, SC-AC8, SC-AC9, SC-AC10, SC-AC12.
- R10 (extends H-AC1 and the VT meter, no second reader) → SC-AC2, SC-AC9, SC-AC11.
- By metric: M1 → SC-AC3, SC-AC4 · M2 → SC-AC8 · M3 → SC-AC6 · M4 → SC-AC12, SC-AC5 · M5 → SC-AC1 · M6 → SC-AC7 · M7 → SC-AC8.

That is 2 requirements and 7 metrics, mapping to 12 criteria.

## Approval history

- **2026-10-22 — approved (human).** Registry key `spec-jarvis-coordinator-inc2-scorecard-2026-10-22`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it. -->

- **2026-10-22 — drafted.** ba-sa, from PRD-jarvis-coordinator R9–R10, DA H-AC1, the VT Part J meter, and a read-only baseline probe over this repo's transcripts at `96bebdb`.
