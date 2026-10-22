# QA Report: Jarvis coordinator, Increment 2: the scorecard (R9–R10)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-jarvis-coordinator-inc2-scorecard.md
Review: doc/qa/REVIEW-jarvis-coordinator-inc2-scorecard.md (PASS, reviewer run `ae675b38f138bc90e`)
Date: 2026-10-22

## Verdict: PASS

All 12 criteria (SC-AC1 to SC-AC12) pass on commands run in this QA run. The SC-AC9 replay on the real transcripts matches every cell of the spec's Baseline table for W0 and W1, with no differences. The default time report is byte-identical to HEAD's on a frozen snapshot of the real transcripts. HEAD's unchanged tests pass against the new source.

## What was tested

- Spec: `doc/specs/SPEC-jarvis-coordinator-inc2-scorecard.md` (Approved, `spec-jarvis-coordinator-inc2-scorecard-2026-10-22`).
- Change: the uncommitted files in worktree `agent-a477ed9734a9e26e3`:
  - `scripts/agent_time.py`;
  - `.claude/meter/transcript_reader.py`;
  - `tests/framework/test_agent_time.py`;
  - `tests/hooks/test_transcript_reader.py`;
  - fixture dirs `tests/framework/fixtures/agent_time/scorecard/`, `tests/hooks/fixtures/transcripts/scorecard-owner/` and `tests/hooks/fixtures/transcripts/scorecard-turn-ends/`.
- Scratch copies, all from `git archive` of this branch's HEAD `6ec6b4b`:
  - `base` is HEAD untouched;
  - `new` is HEAD with the files above overlaid;
  - `combo` is HEAD's tests with only the two new source files.
- The worktree's base is `65108e8`. `git diff --stat 65108e8 HEAD` over the four changed files and both fixture trees is empty, so the overlay drops nothing.
- The engineer's handback was not read. Every result below comes from this run.
- Approval (flagged): the invocation does not state that the human approved the implementation. On the Tier-1 route in §5, the human approves once, at the brief. The spec is Approved, and the review PASS comes from a different run than the author's (`a477ed9734a9e26e3`). QA ran on that basis.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| SC-AC1 | One block per metric in order; runs alone; "no …" on empty input | PASS | The suite on `new` is green: 2019 passed, 1 skipped (see Test Run).<br>My run on an empty directory exits 0. It prints `no exchanges` for every M1 and M4 tier, `M3 …: no review or QA runs`, `M6 …: no role-agent briefs`, and `owner messages per day (UTC): none`. No `0` appears in M1, M3, M4 or M6.<br>`--scorecard --rework` and `--scorecard --include-probes` each print one line: `agent-time: error: --scorecard runs alone`.<br>`--until` without `--scorecard` prints `agent-time: error: --until needs --scorecard`.<br>No `--reader` prints the existing `unsupported` line.<br>All of these exit 0 with 0 bytes on stderr. |
| SC-AC2 | H-AC1 owner rule through the real reader (RED-FIRST) | PASS | The 4 named test files are green: 306 passed.<br>The spec's planted mistake, `_is_owner` → `return True` (every inbound line is the owner), gives `5 3 failed, 217 passed`.<br>A weaker mutant, which only drops the `startswith("<")` check, gives `1 2 failed, 218 passed`.<br>My hostile main thread has 6 user lines that carry a timestamp. The reader marked 4 of them as owner: a leading-space `" <…"` string, an empty string, `isMeta: "true"` as a string, and plain text. As the spec's rule requires, the list-content line and the line with no offset were not counted. |
| SC-AC3 | Turn ends counted per distinct id (RED-FIRST) | PASS | Mutant: count per line (`ids.add(id(e))`) → `3 2 failed, 218 passed`.<br>Mutant: drop turn ends with no id → `4 2 failed, 218 passed`.<br>Hostile run: `id` null, `id` missing, `id` an object, `stop_reason` a list, `stop_reason` an int, and a `timestamp` that does not parse. Exit 0; malformed lines are counted as unreadable. |
| SC-AC4 | Tier grammar; the first Tier line wins; NFKC | PASS | Mutant: the regex accepts `[0123]` → `2 1 failed, 219 passed` (the `Tier: 3` case).<br>Hostile run through the real reader:<ul><li>owner text with `Tier: 2` and replies with no Tier line → untiered;</li><li>`**Tier**: 0` → tier 0;</li><li>`Tier：2` (full-width colon) → tier 2;</li><li>`Tier: 1 — ok` → tier 1.</li></ul>Printed: one exchange in each of tier 0, tier 1, tier 2 and untiered. |
| SC-AC5 | Window by owner message and first event; malformed times | PASS | Each of these prints one `agent-time: error:` line, exit 0, 0 bytes on stderr:<ul><li>`--until` equal to `--since`;</li><li>`--until` earlier than `--since`;</li><li>`2026-10-22 09:00`;</li><li>`2026-10-22T09:00:00+07:00`;</li><li>`2026/10/22`;</li><li>`2026-02-30`.</li></ul>`--until 9999-12-31T23:59:59Z` and `--since 0001-01-01` run cleanly, 37 lines each.<br>The time report's `--since 2026/10/01` refusal is byte-identical to HEAD's (SC-AC11, case 8). |
| SC-AC6 | M3 per report slug | PASS | Hostile run with absolute paths:<ul><li>a reviewer run edits `REVIEW-ok`, plus a path with `/` inside the slug;</li><li>a qa run edits `QA-ok`, a 70-character slug, and a slug with a space;</li><li>a qa run with no brief edits `QA-ok`;</li><li>a reviewer run edits `REVIEW-ok.md\n`;</li><li>a reviewer run edits a backslash relative path;</li><li>an unknown-role run (bad meta) edits `QA-ok`.</li></ul>Output: `ok: review 1 · QA 2`, `(unprintable label): review 1 · QA 1`, `2 runs wrote no report`. That is the expected result: the unknown role is not counted, and both the newline path and the relative path with no `cwd` count under "wrote no report". |
| SC-AC7 | M6 brief field lines | PASS | Same hostile set: `3 of 5`. The 5 role runs are counted and the 2 unknown-role runs are not. Counted with the lines: a string brief, a list-content brief and the newline-path reviewer's brief. Counted without them: the run with no inbound event, and a brief that starts with U+202E before `Tier:`. |
| SC-AC8 | M2 and M7; missing or unreadable memory | PASS | W0 and W1 print the M2 and M7 values from the Baseline table.<br>`--memory-dir /nonexistent` prints `M2, M7: memory directory not found`.<br>A directory holding a non-UTF-8 `.md` prints `M2, M7: not measured (unreadable memory file)`.<br>In both cases M1, M3, M4 and M6 still print, exit 0, 0 bytes on stderr. |
| SC-AC9 | Baseline replay on the real transcripts | PASS | Command: `--scorecard` with W0 `[2026-10-01T00:00:00Z, 2026-10-21T02:03:54Z)`, then W1 `[2026-10-21T02:03:54Z, 2026-10-22T09:00:00Z)`.<br>Run on the live transcript directory, read only, and on a frozen copy of it (283 files). Both give identical output.<br>`doc/memory/` is unchanged since `96bebdb` (`diff -rq` is empty), so M2 and M7 are pinned as the spec requires.<br>Every cell matches (cell-by-cell table below). |
| SC-AC10 | No transcript text in the output | PASS | Internal-failure probe: a scratch reader whose `runs()` raises `RuntimeError("CANARY-7f3a")`, run with `--scorecard`. It prints exactly `agent-time: internal error: RuntimeError`, exit 0, 0 bytes on stderr, and 0 canary hits. The suite's scorecard-mode test of the same rule (`test_agent_time.py` line 1191) is green.<br>The canary `CANARY-7f3a` was planted in owner text, Jarvis text, two briefs (string and list content) and a non-slug edit path. It appears 0 times in stdout or stderr.<br>My first fixture put the canary in a *valid* slug (`REVIEW-CANARY-7f3a.md`), and it printed. The spec allows that, because slugs that match the label rule are printed. It was a test-design error, not a defect.<br>The real-data outputs (W0, W1, the current window) hold only counts, dates, fixed labels and report slugs. |
| SC-AC11 | Default output byte-identical; existing tests unedited | PASS | `base` against `new`, with stdout, stderr and the exit code compared byte for byte on the frozen snapshot. **IDENT** for all 11 existing-input cases:<ul><li>no flags;</li><li>`--since 2026-10-01`;</li><li>`--since 2026-10-21`;</li><li>`--rework --qa-dir doc/qa`;</li><li>`--targets …`;</li><li>`--targets … --min-runs 1`;</li><li>`--include-probes`;</li><li>`--since 2026/10/01`;</li><li>no `--reader`;</li><li>the neutral fixture;</li><li>a missing `--dir`.</li></ul>Test-file diffs: `test_agent_time.py` 0 lines removed and 410 added; `test_transcript_reader.py` 0 removed and 118 added.<br>`combo` (HEAD's tests + new source) on the 4 named files plus `test_correction_rate`, `test_doc_contracts` and `test_learning_loop`: `328 passed, 1 skipped`. |
| SC-AC12 | M4 first reply after a tool result | PASS | The M4 cells for W0 and W1 match the Baseline (below).<br>The hostile run, with no tool results, prints `no result: 1` for each tier and no median.<br>The tests for cases (a) to (d) are in the green suite. |

### SC-AC9 cell by cell (spec Baseline table against this run)

| Metric | W0 spec | W0 run | W1 spec | W1 run |
|---|---|---|---|---|
| Owner messages | 76 | 2+70+4 = 76 | 8 | 1+7 = 8 |
| M1 tier 0 | — | no exchanges | 1 · 8 extra · 8.00 · 0 none | 1 · 8 · 8.00 · 0 |
| M1 tier 1 | — | no exchanges | no exchanges | no exchanges |
| M1 tier 2 | — | no exchanges | 2 · 0 · 0.00 · 2 none | 2 · 0 · 0.00 · 2 |
| M1 untiered | 76 · 103 · 1.36 · 46 | 76 · 103 · 1.36 · 46 | 5 · 17 · 3.40 · 4 | 5 · 17 · 3.40 · 4 |
| M2 | 6 to 2026-10-21 (prev 1, NOT down) | same | 7 to 2026-10-22 (prev 0, NOT down) | same |
| M3 | 11 slugs · rev med 0 · QA med 1 · max 3 (merge-gate-B 2+1, merge-gate-D 2+1) · 5 no report | 11 slugs · 0 · 1 · B 2+1, D 2+1 (all others ≤ 2) · 5 | 6 slugs · 1 · 1 · max 4 (bugfix-gate3-worktree 3+1) · 4 no report | 6 · 1 · 1 · gate3 3+1 (all others ≤ 2) · 4 |
| M4 | untiered n 54, 0.6 · 22 no result | n 54, 0.6 · 22 | t0 n 1 7.0 · t2 n 1 0.4, 1 no result · untiered n 1 2.1, 4 no result | t0 7.0 (n 1), 0 · t2 0.4 (n 1), 1 · untiered 2.1 (n 1), 4 |
| M6 | 7 of 60 | 7 of 60 | 30 of 30 | 30 of 30 |
| M7 | 0 | 0 | 0 | 0 |

The current-window run (`--since 2026-10-22T09:00:00Z`, live directory, read only) exits 0 with 0 bytes on stderr. It prints all M1–M7 blocks:
- 3 owner messages;
- 3 untiered exchanges;
- M3 with 6 slugs;
- M6 15 of 15.

No transcript folder was written to. Every run read the live directory or a copy in the scratchpad.

## Test Run

```
cd <scratch>/new && python3 -m pytest tests -q -p no:cacheprovider
2019 passed, 1 skipped in 399.46s (0:06:39)

cd <scratch>/new && scripts/verify-full.sh > vfull.log 2>&1 ; echo rc=$?
rc=0
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             (351s) 1388 passed in 349.60s (0:05:49)
  OK   ci-examples       (10s) 32 passed in 8.38s
  OK   scar-forge        (1s) LIMIT (stated limit): ...
  OK   coordinator       (8s) 160 passed in 7.45s
  OK   framework         (106s) memory: 0 problem(s) in ...
counts: not configured — executed == collected NOT checked
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
```

- `scripts/verify-handoff.sh --status` prints `not opted in`, so `verify-full.sh` is the verdict command.
- The `INCOMPLETE` banner reports the template's 3 unconfigured steps (lint, format, tests). Those steps are unconfigured on HEAD too, and this change does not touch them. Every configured step passed.

## Defects (if FAIL)

None.

## Edge Cases Probed

- Real reader, main thread:
  - owner content that is empty, starts with a space before `<`, or has `isMeta` as the string `"true"` → owner;
  - list content, or a timestamp with no offset → not owner;
  - malformed lines (bad JSON, non-JSON text, a JSON array, a JSON string, a 5000-digit int), plus an assistant record whose `id` is an object, plus a bad-JSON subagent meta file → `unreadable lines: 7`. I bisected the assistant records one at a time to find which one counts. After I appended raw invalid UTF-8 bytes (`\xff\xfe\x80`) the result was `unreadable lines: 8`, exit 0, 0 bytes on stderr.
- An assistant `message` that is a string, `content` blocks of `None` or `5`, a text block with `text: null` → no crash.
- Subagents:
  - a meta file with bad JSON, or no meta file → unknown role, excluded from M3 and M6;
  - a U+202E-prefixed brief → not counted as carrying the lines;
  - a backslash relative path → no path (the reader's existing R41 rule).
- Window: equal or reversed bounds, `+07:00`, a space separator, slashes, `2026-02-30` → one error line each. Year-9999 and year-1 bounds → normal output.
- Memory: a missing directory, and a directory with non-UTF-8 content → the named `M2, M7:` line; the other metrics still print.
- Source mutants (5): owner rule → `return True`; ignore `<` in the owner rule; accept `Tier: 3`; count turn ends per line; drop turn ends with no id. Each one turned at least one plain test red.

## Parked (outside SC-AC1…SC-AC12, or a LIMIT under the threat model)

- **The time report's header misstates a time-of-day `--since`.** Low. This is an in-model mistake (the meter misreports its window) that no criterion covers. It is parked because it is outside SC-AC1…SC-AC12, not because it is a LIMIT.
  - `--since 2026-10-21T02:03:54Z` without `--scorecard` used to be refused (`invalid parse_since value`). It is now accepted and filters from 02:03:54. The header still reads `since 2026-10-21`, and the report counts 48 runs where the header's date would give 52.
  - No existing input's output changed (SC-AC11 holds). The spec's Window paragraph gives `--since` both forms.
  - It matches the reviewer's parked item. The fix is to print the full instant, or to keep the time report date-only.
- **Unprintable slugs share one `(unprintable label)` line and count as one slug** in "N slugs" and in the medians. The reviewer saw the same. Low.
- **`1 slugs` grammar.** Cosmetic. Seen by the reviewer too.
- **The two red-first tests that monkeypatch the mistake in cannot catch a regression.** The reviewer saw the same. My source mutants show that the plain tests do catch one. Low.

## Approval history

- **2026-10-22 — drafted.** QA run, based on the spec, the review PASS, and commands run in this run only, on scratch copies of HEAD `6ec6b4b` with the author's worktree files overlaid.
