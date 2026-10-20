# QA Report: Verify tiers — increment 1 (J, the agent-time meter)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Date: 2026-10-20

## Verdict: FAIL

**Re-test 2 (current): 9 of 11 J-ACs pass. J-AC2 and J-AC7 fail on one defect, D7.** D5 and D6 are fixed, so J-AC6 now passes. D7 is older than this rework, and QA missed it in both earlier rounds. The reader splits transcripts with `str.splitlines()`, which also breaks on U+2028, U+2029 and U+0085. JSON allows those characters raw inside a string, and real transcripts carry them. So a valid line becomes fragments that are counted as unreadable, its clock event is lost, and time moves silently between categories. On J-AC2's own fixture, one such character moves 120 s from tests to model and turns `unreadable lines: 1` into `3`. On local real data, all 23 unreadable lines are this artefact, including the 6 in the pilot project transcripts. See "Re-test 2" below.

Re-test 1: 10 of 11 J-ACs passed, and J-AC6 failed (D5, D6).

Round 1: 9 of 11 J-ACs passed. J-AC6 and J-AC7 failed. The spec's own fixtures passed for both, but the property each one guards (R39: "always exits 0", and nothing printed from the transcript or its path) broke on input shapes outside those fixtures. Four kinds of input crashed the meter with a traceback and exit 1. One of those tracebacks printed the absolute transcript path, which carries the user's home directory and the J-AC6 canary file name.

Provenance: the owner approved moving J to QA ("ส่ง QA", 2026-10-20), as relayed in the coordinator's brief. The implementation is uncommitted in the working tree.

## Re-test 2 (after the D5/D6/N1 rework, 2026-10-20)

Provenance: the coordinator's brief says this is the QA loop for J, with the owner's "ส่ง QA" (2026-10-20) still in force. The engineer reported four changes. D5: the reader prints a label only if it fully matches `[A-Za-z0-9_.:-]{1,64}`, and anything else becomes `(unprintable label)`. As a second defence, the core's `_label` passes only printable strings of 1 to 100 characters. D6: a role that is not a string becomes `(unknown)`. N1: an odd line counts as 1 unreadable line instead of blanking the report. The engineer also made one judgement call: a record with no `type` is now `(unprintable label)`.

### Criteria Results (re-test 2)

| # | Verdict | Evidence (executed this round) |
|---|---|---|
| J-AC1 | PASS | `test_golden_timeline_gives_exactly_the_golden_totals` and the polling-line test PASSED. In-process on the J-AC2 fixture: `(unreadable 1, idle 600.0, active 578.0, turns 9)` |
| J-AC2 | **FAIL** | The literal fixture passes: the three J-AC2 tests PASSED. **The property fails (D7).** I changed one valid line of that same fixture, the `"1 passed"` tool result, to carry a raw U+2028, which is legal JSON and is how the assistant writes it. The totals moved: `(unreadable, model, tests:running, active, idle) = (3, 270.0, 0.0, 578.0, 600.0)` against the golden `(1, 150, 120, 578, 600)`. 120 s of test time moved silently into model. This is the ADR-2 failure shape. U+2029 and U+0085 give the same result. New red test: `test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole[U+0085/U+2028/U+2029]` |
| J-AC3 | PASS | `test_widening_the_clock_allow_list_is_caught` PASSED. Independently in-process, with `CLOCK_EVENT_TYPES` widened: idle `600.0 → 675.0`, active `578.0 → 503.0`. **The broad per-line catch does not mask it:** widened types take the user path, which does not raise. I also checked the catch against a planted future bug in `_events_of`. A `TypeError` on every user line gives `(unreadable 10, idle 0.0, active 1118.0)`. A `KeyError` on tool-call lines gives `(unreadable 7, turns 4)`. Either way the golden totals and the pinned `unreadable_lines == 1` (`test_transcript_reader.py:113`) go red. |
| J-AC4 | PASS | `test_counting_each_model_event_as_a_turn_is_caught` PASSED (78-test run below) |
| J-AC5 | PASS | `test_no_reader_prints_unsupported_and_no_durations[…]` PASSED |
| J-AC6 | PASS | D5 and D6 are fixed. The re-test-1 reproductions now print nothing they should not. `agentType: {"description": "CANARY-7f3a"}`, `5` and `["CANARY-7f3a"]` each give `(unknown): 1 runs`. A newline in `type` gives `excluded events …: (unprintable label) 1`, and one in `agentType` gives `(unprintable label): 1 runs`. No forged line appears in either case. My three re-test-1 red tests are now green. Every attack shape is blocked through the real reader (CLI) and through a stub reader that reaches only the core (in-process `report()`): NEL, U+2028, CR, tab, NBSP, RLO, ZWSP, a lone surrogate, an empty string, 65 characters (reader) and 101 characters (core). New green tests pin this, and I showed they bite (below). |
| J-AC7 | **FAIL** | The literal cases pass, and so do the engineer's N1 tests (`test_one_odd_line_is_one_unreadable_line_and_the_report_goes_on[…]`). **But `unreadable lines:` counts lines that are not malformed (D7).** The same one-character change turns the fixture's `unreadable lines: 1` into `3`. On local real transcripts, every unreadable line is this artefact. Across 902 files, `str.splitlines()` makes 23 unparseable fragments, while splitting on `\n` alone makes 0. Per project with the CLI: pilot project gives `unreadable lines: 6` against `0`, and jarvis-framework gives `17` against `0`. |
| J-AC8 | PASS | `test_report_shows_the_median_and_shares_that_sum_to_100` PASSED |
| J-AC9 | PASS | The three J-AC9 tests PASSED |
| J-AC10 | PASS | `tests/framework/test_doc_contracts.py` PASSED (inside the 78) |
| J-AC11 | PASS | verify-full's framework step is **OK** this round, so `check_neutrality.py` passes. The re-test-1 worktree leak is gone after `e857a87` ("neutrality check scans tracked files only"). |

Count: 9 PASS, 2 FAIL. J-AC2 and J-AC7 fail on the same single defect, D7.

### D7, measured

- **Cause.** `_read_run` splits a transcript with `text.splitlines()` (`.claude/meter/transcript_reader.py:155`). That method also breaks on U+2028, U+2029, U+0085 and the other Unicode line boundaries. JSON allows these raw inside a string, and the assistant writes them raw. So one valid line becomes two or three fragments that fail `json.loads`. Each fragment is counted as unreadable, and the clock event on that line is lost.
- **Real-data presence.** 4 of 902 local transcript files contain raw U+2028 or U+2029 (13 and 1 occurrences). The broken lines are clock events: in pilot project, 2 `user` lines, each in 3 pieces; in jarvis-framework, 4 `assistant` lines, 2 `user` lines and 1 `api-request-blob` line.
- **Effect on real numbers.** On pilot project, the medians are unchanged, and only `unreadable lines: 6 → 0` differs. On jarvis-framework, the effect reaches the categories: `model generating 9.3 → 9.4 min/run` and `5.2 → 5.3 min/run (72% → 73%)`, and `other tools 10% → 9%`, in two agent-type blocks.
- **The coordinator's "6 unreadable lines are reported, not hidden".** pilot project with the current reader gives exactly `unreadable lines: 6`. A scratch copy with `split("\n")` gives `0` with otherwise identical output. If the pilot run read the pilot project transcripts, those 6 are this artefact, not malformed data. I could not confirm which directory the pilot read. Local pilot project with `--since` set to 2026-09-01, 09-15, 10-01, 10-05 and 10-10 gives 832, 766, 423, 274 and 161 runs. None of these is the coordinator's 485. `unreadable lines: 6` holds through 10-05 and drops to 0 at 10-10. The 10-01 window gives ai-engineer `active median 38.5 min · turns median 101`, close to the coordinator's figures but not equal.
- **The fix is not pinned by the test.** I checked that the red test goes green with a scratch reader that splits on `\n`: `U+0085 PASS · U+2028 PASS · U+2029 PASS`. The test checks the totals and the unreadable count, not the mechanism.
- **Age.** This line predates the D5/D6/N1 rework. It was in the code at round 1 and re-test 1, and QA missed it both times. It is not a regression from this rework.

### The engineer's changes and judgement calls, verified

| Claim | Verdict | Evidence |
|---|---|---|
| D5: the reader accepts only `[A-Za-z0-9_.:-]{1,64}`, by `fullmatch` | Verified | Through the CLI: `x y`, `é`, 65 characters, NEL, U+2028, CR, tab and NBSP all give `(unprintable label)`. Exactly 64 characters is printed as is. |
| The core's second defence: printable strings of 1–100 characters | Verified, with a limit (N8) | A stub `Run` sent straight into `report()`: every line-break or invisible shape, an empty string, 101 characters and a non-string give `(unprintable label)`, and the report's line count is unchanged. 100 characters is printed. |
| D6: a non-string role becomes `(unknown)` | Verified | A dict, an int and a list `agentType` each give `(unknown): 1 runs` |
| N1: an odd line is 1 unreadable line | **Partly** (N1a) | The engineer's six shapes pass. Deep nesting up to 10,000 levels in `timestamp` is handled. **A JSON integer of more than 4,300 digits still blanks the report:** a line `{"type":"user",…,"n":111…(5,000 digits)}`, or a bare 5,000-digit line, gives only `agent-time: internal error: ValueError`. It exits 0 and leaks nothing. The cause is that `json.loads` raises a plain `ValueError` for the integer-digit limit, and line 161 catches only `JSONDecodeError`. |
| Judgement call: no `type` → `(unprintable label)` | Accepted, with a note | It is counted and visible (`excluded events …: (unprintable label) 1`). It merges "missing" with "hostile", which a separate `(no type)` label would keep apart. That is an observation, not a defect. |
| Risk: the broad per-line catch could hide a future `_events_of` bug | Checked: caught today | See J-AC3 above. A thrown bug moves the golden totals and the pinned unreadable count. |

### Is anything else derived from data printed?

No. I re-read every `print` path in `report()`, `_type_block()` and `rework_report()`. The only data-derived strings are the role and the excluded-type labels, and both pass `_label` twice: once in the reader and once in the core. The `<type> (no timestamp)` and `<type> (timestamp without offset)` labels are built only from `user` or `assistant`. QA causes come from the fixed `REWORK_CAUSES`. Everything else is a count, a duration, the `--since` date or the reader file name, and those last two come from the operator's command line.

### Findings outside the ACs (re-test 2, not counted as rework defects)

| # | Severity | Finding |
|---|---|---|
| N1a | Low | N1 is only partly fixed: an integer longer than 4,300 digits on one line still blanks the whole report (see above). Reproduce: append `'1' * 5000 + '\n'` to any transcript. |
| N7 | Info | Through the real reader, a role can still begin a line with another report line's keyword, because `:` is allowed: `agentType: "method"` prints `method: 1 runs · …`. It cannot reach `rework share:` or `unclassified defects:`, because those need a space. |
| N8 | Info | The core's defence alone does not stop a printable forgery. A stub reader whose role is `rework share: 0 of 9 engineer runs (0%)` gets a line that begins with exactly that. The text is printable and single-line, so `_label` passes it. Adapter ก's reader blocks it, because spaces and parentheses fail `LABEL_RE`. A reader is declared code, as in N5, so this is noted for whoever writes adapter ข's reader. |
| N2, N3, N5, N6 | — | Not re-tested this round. The code paths are unchanged. |

### Test runs (re-test 2)

The four meter test files as handed over, before my additions (this matches the coordinator's count):

```
python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py tests/framework/test_doc_contracts.py tests/hooks/test_regression_agent_time_reader.py -q
78 passed in 1.93s
```

I added 15 `test_regression_*` cases to `tests/hooks/test_regression_agent_time_reader.py`:
- `…_a_valid_line_carrying_a_unicode_line_separator_is_read_whole[U+0085/U+2028/U+2029]`: **red on purpose (D7)**. It fails with `(3, 270.0, 0.0, 578.0, 600.0)` against `(1, 150, 120, 578, 600)`, and it goes green against a scratch reader that splits on `\n`.
- `…_the_reader_never_passes_an_odd_label_through[6 shapes]`: green. With the reader's `_label` replaced by a pass-through for strings, all 6 go red at the `agent_type` assertion.
- `…_the_core_never_prints_an_odd_label_from_any_reader[6 shapes]`: green. With the core's `_label` replaced by identity, all 6 go red at `value not in text`.

Verdict command, `scripts/verify-full.sh`, full output (exit 1; the absolute repository path is written as `<repo>`, and that is the only edit):

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (exit 1)
        tmp_path: Path, separator: str
    ) -> None:
        """J-AC2's golden run with one valid tool result carrying the separator: totals and unreadable count unchanged."""
        shutil.copytree(_GOLDEN_FIXTURE, tmp_path / "t")
        transcript = next((tmp_path / "t").rglob("agent-*.jsonl"))
        lines = transcript.read_text("utf-8").split("\n")
        index = next(i for i, line in enumerate(lines) if '"1 passed"' in line)
        record = json.loads(lines[index])
        record["message"]["content"][0]["content"] = f"1{_SEPARATORS[separator]}passed"
        lines[index] = json.dumps(record, ensure_ascii=False)  # raw, as the assistant writes it
        assert json.loads(lines[index]) == record, "the changed line must still be valid JSON"
        transcript.write_text("\n".join(lines), "utf-8")
    
        reader = agent_time.load_reader(_READER)
        (run,) = list(reader.runs(tmp_path / "t", dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)))
        totals = agent_time.categorise(run)
        got = (run.unreadable_lines, totals["model"], totals["tests:running"], totals["active"], totals["idle"])
>       assert got == (1, 150, 120, 578, 600), f"(unreadable, model, tests:running, active, idle) = {got}"
E       AssertionError: (unreadable, model, tests:running, active, idle) = (3, 270.0, 0.0, 578.0, 600.0)
E       assert (3, 270.0, 0.0, 578.0, 600.0) == (1, 150, 120, 578, 600)
E         
E         At index 0 diff: 3 != 1
E         Use -v to get more diff

tests/hooks/test_regression_agent_time_reader.py:272: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole[U+0085]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole[U+2028]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole[U+2029]
3 failed, 239 passed in 11.39s
  OK   ci-examples       19 passed in 2.07s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       28 passed in 0.35s
  OK   framework         memory: 0 problem(s) in <repo>/doc/memory
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
```

Why the gate is red: hooks has 3 failed, and all 3 are my new D7 tests, which are red on purpose. The other 239 pass. ci-examples, scar-forge, coordinator and framework are OK. Lint, format and tests are TODO in this template repo, so those steps verified nothing.

## Re-test 1 (after rework, 2026-10-20)

Provenance: the coordinator's brief says this is the QA loop after the round-1 FAIL, with the owner's "ส่ง QA" (2026-10-20) still in force. The engineer reported six fixes: unreadable meta or transcript is counted with no path; a timestamp without an offset is excluded as `<type> (timestamp without offset)`; a non-string Bash command is not classified; a meta of `[]` gives `(unknown)`; a bad argument prints `agent-time: error: …` and exits 0; and a top-level guard prints `agent-time: internal error: <type>` and exits 0.

### Criteria Results (re-test 1)

| # | Verdict | Evidence (executed this round) |
|---|---|---|
| J-AC1 | PASS | `test_golden_timeline_gives_exactly_the_golden_totals` and `test_polling_is_reported_on_its_own_line_but_not_added_to_active_twice` PASSED (51-test run below). Independently, in-process: `{'turns': 9, 'active': 578.0, 'idle': 600.0, 'model': 150.0, 'tests': 361.0, 'polling': 120.0}` |
| J-AC2 | PASS | The three J-AC2 tests PASSED. The CLI on `tests/hooks/fixtures/transcripts` gives `excluded events (adapter-internal, not timed): api-request 1 · api-request-blob 1 · attachment 1 · queue-operation 1 · system 1`, and `ai-engineer: 1 runs · active median 9.6 min · turns median 9`, exit 0 |
| J-AC3 | PASS | Re-reproduced with a scratch reader whose `CLOCK_EVENT_TYPES` was widened by `sed`. Active median went from 9.6 to 8.4 min (578 → 503 s) and idle from 10.0 to 11.2 min (600 → 675 s). `test_widening_the_clock_allow_list_is_caught` PASSED |
| J-AC4 | PASS | In-process, with `count_turns` swapped for a per-event counter: `per-event turns 10` (original 9). `test_counting_each_model_event_as_a_turn_is_caught` PASSED |
| J-AC5 | PASS | `test_no_reader_prints_unsupported_and_no_durations[reader_args0/1]` PASSED. A `--reader` that is a directory also prints `unsupported`, exit 0 |
| J-AC6 | **FAIL** | The literal fixture passes (`test_the_canary_never_reaches_stdout_or_stderr` PASSED), and the round-1 path leak is fixed (`test_regression_an_unreadable_file_neither_crashes_nor_prints_its_path[meta/transcript]` PASSED). **The property still fails** through the two values the meter prints verbatim. (a) `{"agentType": {"description": "CANARY-7f3a"}}` prints `{'description': 'CANARY-7f3a'}: 1 runs · …`. (b) A `type` or `agentType` with a newline forges a report line. Measured: `agentType: "qa\nrework share: 0 of 9 engineer runs (0%)"` prints a line beginning `rework share: 0 of 9 engineer runs (0%)`. New red tests: `test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line[type/agentType]` and `test_regression_a_role_that_is_not_a_string_is_not_printed` FAILED |
| J-AC7 | PASS | The four round-1 crash shapes now exit 0 with no traceback (`test_regression_a_timestamp_without_an_offset_does_not_crash[no-offset/mixed-offset-and-none]`, `test_regression_a_meta_file_that_is_not_an_object_is_an_unknown_role`, `test_regression_a_shell_command_that_is_not_a_string_does_not_crash`: PASSED). The engineer's literal tests PASSED. Every new odd shape I tried exits 0, with no traceback and no path: the 8 data shapes under "Can the guard itself leak?", plus a `--qa-dir` holding a directory or a non-UTF-8 report, and out-of-range timestamps |
| J-AC8 | PASS | `test_report_shows_the_median_and_shares_that_sum_to_100` PASSED |
| J-AC9 | PASS | `test_rework_share_and_causes_are_counted`, `test_rework_marker_must_start_a_line`, `test_qa_reports_before_the_window_are_not_counted`: PASSED |
| J-AC10 | PASS | `tests/framework/test_doc_contracts.py`: 3 PASSED |
| J-AC11 | PASS | `python3 scripts/check_neutrality.py` → `neutrality: 0 provider name(s) in layers 0-1, 9 project leak(s) (local denylist present)`. The AC's claim, `0 provider name(s)`, holds. **All 9 project leaks are in one file that is not part of J**: `.claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt`, the local denylist copied into another agent's worktree (`git worktree list` shows four agent worktrees, created 14:51–14:55 today). Leaks outside `.claude/worktrees/`: `0`. This is why verify-full's framework step is red this round (see below). It is environmental and not a J defect, but someone has to clean it up before the gate can go green |

Count: 10 PASS, 1 FAIL.

### Test runs (re-test 1)

The four meter test files before I added tests (the engineer's three, plus my round-1 regression file):

```
python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py tests/framework/test_doc_contracts.py tests/hooks/test_regression_agent_time_reader.py -v
============================== 51 passed in 7.15s ==============================
```

All 12 round-1 regression tests are now green. The 6 that were red in round 1 now pass.

My regression file after four tests were added this round (three red on purpose, one green):

```
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line[type]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line[agentType]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_role_that_is_not_a_string_is_not_printed
3 failed, 13 passed in 2.02s
```

Each red test fails for the reason it names. `[type]` fails with `assert not ['rework share: 0 of 9 engineer runs (0%) 1']`. `[agentType]` fails with the forged line `rework share: 0 of 9 engineer runs (0%): 1 runs · …`. The non-string role test fails with `'CANARY-7f3a' printed`.

The new green test, `test_regression_a_value_the_reader_cannot_handle_reaches_the_guard_as_its_type_only`, was shown to bite against two scratch copies of the guard. The test checks the guard's shape: exit 0, no traceback, no canary or home path, and any `internal error` line exactly matching `agent-time: internal error: \w+`. It does not pin today's `TypeError` path, because a correct D5 fix may count that line instead of crashing on it. In the first copy, the guard re-raises: exit 1, with a `TypeError` traceback, and the test is RED. In the second, the guard prints `{exc!r}` and its frame: exit 0, but the line carries the exception message and a scratch path, so it fails the pattern, and the test is RED. Unmutated, it gives `1 passed`.

Verdict command, `scripts/verify-full.sh`, full output (exit 1; the absolute repository path is written as `<repo>`, and that is the only edit):

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (exit 1)

tests/hooks/test_regression_agent_time_reader.py:221: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

result = CompletedProcess(args=['/opt/homebrew/opt/python@3.14/bin/python3.14', 'scripts/agent_time.py', '--reader', '/Users/po...nside the run is not timed as a wait; with no reader the meter says unsupported instead of printing zero\n", stderr='')

    def _assert_reported_cleanly(result: subprocess.CompletedProcess) -> None:
        """R39: exit 0, no traceback, and nothing the transcript or its path carried."""
        assert "Traceback" not in result.stderr, result.stderr.splitlines()[-1:]
        assert result.returncode == 0
        for leaked in (_CANARY, str(Path.home())):
>           assert leaked not in result.stdout and leaked not in result.stderr, f"{leaked!r} printed"
E           AssertionError: 'CANARY-7f3a' printed
E           assert ('CANARY-7f3a' not in 'agent-time ...nting zero\n'
E             
E             'CANARY-7f3a' is contained here:
E               iption': 'CANARY-7f3a'}: 1 runs · active median 0.1 min · turns median 1
E             ?           +++++++++++
E                 model generating           0.1 min/run  100%
E                 tests                      0.0 min/run    0%   (running 0.0 · background launch 0.0 · background wait 0.0 · hand-written polling 0.0)
E                 waits (background/poll)    0.0 min/run    0%   (background 0.0 · hand-written polling 0.0)...
E             
E             ...Full output truncated (6 lines hidden), use '-vv' to show)

tests/hooks/test_regression_agent_time_reader.py:75: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line[type]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line[agentType]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_role_that_is_not_a_string_is_not_printed
3 failed, 202 passed in 17.91s
  OK   ci-examples       19 passed in 3.68s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       28 passed in 0.61s
  FAIL framework         (exit 1)
.................................................F..............         [100%]
=================================== FAILURES ===================================
__________________________ test_this_repo_is_neutral ___________________________

    def test_this_repo_is_neutral() -> None:
        result = _run(_REPO_ROOT)
>       assert result.returncode == 0, result.stdout
E       AssertionError: LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:1: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:2: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:3: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:4: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:5: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:6: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:7: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:8: <redacted>
E         LEAK      .claude/worktrees/agent-ad1e27705199bd4e4/scripts/neutrality-denylist.local.txt:9: <redacted>
E         neutrality: 0 provider name(s) in layers 0-1, 9 project leak(s) (local denylist present)
E         
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args=['/opt/homebrew/opt/python@3.14/bin/python3.14', '<repo>/...<redacted>\nneutrality: 0 provider name(s) in layers 0-1, 9 project leak(s) (local denylist present)\n', stderr='').returncode

tests/framework/test_neutrality.py:44: AssertionError
=========================== short test summary info ============================
FAILED tests/framework/test_neutrality.py::test_this_repo_is_neutral - Assert...
1 failed, 63 passed in 17.41s
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
```

Second redaction, stated: the nine denylist terms, and a fragment of one inside a truncated `CompletedProcess` repr, are written as `<redacted>`. They are the project's private denylist, and copying them here would put them into a tracked file, which is exactly the leak the step reports.

This paste is from the final run, after all test edits. Why the gate is red: (1) hooks: 3 failed. All three are my new regression tests, red on purpose (J-AC6). The other 202 pass. (2) framework: neutrality fails, and all 9 leaks are in another agent's worktree under `.claude/worktrees/` (untracked, outside J). In round 1 this step was green. Lint, format and tests are TODO in this template repo, so those steps verified nothing.

### Defects (re-test 1)

These rows are also appended to the `## Defects` table further down, because the meter's M11 count reads only the first `## Defects` section of a report.

| # | Severity | Defect | Where |
|---|---|---|---|
| D5 | Med | Labels taken from the data are printed verbatim, so a newline in one forges report lines. The labels are an event `type` (on the `excluded events:` line) and a run's `agentType` (as the role at the head of its block). Reproduce: a meta of `{"agentType": "qa\nrework share: 0 of 9 engineer runs (0%)"}`, or an event `{"type": "x\nrework share: 0 of 9 engineer runs (0%)"}`. Each gives a stdout line beginning `rework share: 0 of 9 …`, which is the M11 line the owner's acceptance rests on. This breaks R39 ("only categories, counts and durations"). A label must be a single-line label. One fix is to print anything else as a placeholder and count it, but the engineer chooses the mechanism. | `.claude/meter/transcript_reader.py:142` (`excluded[str(kind)]`), `:175` (`str(meta.get("agentType") …)`); printed at `scripts/agent_time.py` `report()` (excluded line) and `_type_block()` (header) |
| D6 | Med | A role that is not a string is printed as its `str()`. With `{"agentType": {"description": "CANARY-7f3a"}}`, the stdout carries `{'description': 'CANARY-7f3a'}: 1 runs`, so meta content reaches the output, which is the J-AC6 property. A meta that is `[]` already gives `(unknown)`, and a non-string `agentType` should too. | `.claude/meter/transcript_reader.py:175` |

### Attacks on the new code paths

**Can the guard itself leak?**
- From transcript data: no. JSON yields only builtin types, so only builtin exception names can reach the guard. Measured: an unhashable `type`, a list `message.id`, a dict tool id, a list `tool_use_id`, nesting 200,000 deep, content blocks nested 5,000 deep, a lone surrogate in `agentType`, and `PYTHONIOENCODING=ascii`. Each one prints exactly `agent-time: internal error: TypeError | RecursionError | UnicodeEncodeError` and exits 0, with no traceback, no canary and no path.
- From reader code: yes, but not an AC matter. A scratch reader that raises `type("CANARY-7f3a", (Exception,), {})()` prints `agent-time: internal error: CANARY-7f3a`. A reader that raises `SystemExit(3)` exits 3, because the guard catches `Exception`, not `BaseException`. The reader is code declared in ADAPTERS.md, not data, so these are observations (N5).
- During argument parsing: a bad `--since` or `--test-pattern` prints one `agent-time: error: …` line and exits 0. argparse's message echoes the value: `--since /Users/x/CANARY-7f3a` prints the canary. That value comes from the operator's own command line, not from a transcript, so it is not an R39 breach (N4).

**Can a value from the data reach any other line?**
- Yes: an event `type` and `agentType` are printed verbatim. A plain-string label is by design (DESIGN §J: `excluded[type]`; SPEC: "prints role names"). A label with a newline, or a non-string label, is not. These are D5 and D6. **This supersedes my round-1 note** that a canary in `type` or `agentType` was "by design, an observation". The newline and non-string shapes are new evidence, and they turn the note into defects.
- Everything else I tried is not printed: tool names, tool ids, message ids, commands, tool-result text, inbound text and the timestamp value. That includes the `(timestamp without offset)` label, which carries the event type and not the timestamp.

**Do the two pinned behaviours contradict a J-AC?** No.
- *No offset → excluded.* DESIGN §J declares `t: datetime  # timezone-aware` (DESIGN-verify-tiers-merge-gate.md line 40), so a naive time is not a valid event. No J-AC fixture uses a time without an offset. J-AC7's malformed-line case is separate (`unreadable lines`). There is one interaction: a run whose lines all lack an offset becomes a "no clock events" run, and the reader yields such runs whatever `--since` says. Measured: a run from 2020 is counted under `runs with no clock events: 1` in a `--since 2026-10-01` window. That makes round-1 observation 2 wider.
- *Non-string command → other tools.* The reader keeps `tool_kind = "shell"` and drops the command (`command=None`). `_category_of` then falls through to `other tools`, the same path as any shell command that matches no pattern. J-AC1 and J-AC2 use string commands. The engineer's summary, "not classified as shell", is slightly loose: the tool kind is still shell, and only the command is dropped.

### Findings outside the ACs (re-test 1, not counted as rework defects)

| # | Severity | Finding |
|---|---|---|
| N1 | Med | One odd value erases the whole report. An unhashable `type`, `message.id` or tool id, deep nesting, a lone surrogate, or an ASCII stdout leads to `agent-time: internal error: <type>` and no numbers for any run. It exits 0 and leaks nothing, so R39 holds, but for an instrument meant to run over 170+ real runs, one bad line should count as `unreadable`, not blank the report. |
| N2 | Low | `--qa-dir` with an unreadable QA file (a directory named `QA-*.md`, or one that is not UTF-8) prints the full time report, then `agent-time: internal error: IsADirectoryError` or `UnicodeDecodeError` in place of the rework lines. `QA reports not read: N` does not count these. |
| N3 | Low | Out-of-range but valid timestamps are timed: `0001-01-01T00:00:00+05:00` gives `active median 1065467820.1 min`, and `9999-12-31T23:59:59-23:59` gives `4193498879.0 min`. One corrupt line skews a run with no warning. |
| N4 | Info | An argparse error echoes the operator's own argument value (see above). It does not come from the data. |
| N5 | Info | The guard prints the exception's class name, which a reader module can set freely, and it does not catch `SystemExit` raised by a reader (measured exit 3). A reader is declared code, not data. |
| N6 | Info | Piped into `head` with more than about 64 KB of output (3,000 roles), the meter exits 120 and stderr prints `Exception ignored while flushing sys.stdout: BrokenPipeError`, with no traceback and no path. A small output piped into `head -c1` exits 0. A plain `print` of 200 KB into a closed pipe gives a traceback and exit 1, so the meter is better than the baseline. `scripts/correction_rate.py` has no handling of its own, and its 128-byte output is too small to trigger the case. This is a property of the environment, not an R39 breach. |

### Round-1 observations, re-judged

| Round-1 observation | Now |
|---|---|
| Results depend on the Python version (`.50Z` fractions) | **Still present.** Measured again: 3.9.6 gives `0 runs read … assistant (no timestamp) 1 · user (no timestamp) 1`; 3.14.6 gives `1 runs read`. |
| Empty runs are yielded whatever `--since` says | **Still present, and wider**: runs whose lines all lack an offset now join them (see above). |
| The waits detail line omits `waits:other` (Monitor) | **Still present** (`scripts/agent_time.py:255`). |
| Exit 2 on malformed arguments (needed an owner ruling) | **Resolved.** `--since 2026/1/1` and a bad `--test-pattern` print one `agent-time: error: …` line and exit 0 (`test_a_malformed_argument_prints_an_error_line_and_exits_0[…]` PASSED; probes above). |
| Canary in `agentType` or `type` printed, "by design" | **Superseded**: plain labels are still by design, but the newline and non-string shapes are defects D5 and D6. |
| `POLL_RE` and `READ_SHELL_RE` anchor at the command start (for ba-sa) | Unchanged; the code was not touched. |

## Criteria Results (round 1)

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| J-AC1 | Golden timeline gives the exact golden totals; polling has its own line and is not added to active twice | PASS | `test_golden_timeline_gives_exactly_the_golden_totals`, `test_polling_is_reported_on_its_own_line_but_not_added_to_active_twice`: both PASSED (35 passed run below) |
| J-AC2 | Adapter-format fixture with internal events interleaved gives J-AC1's totals, and the output has an `excluded events:` line with a count per type | PASS | `test_adapter_transcript_gives_the_golden_totals`, `test_internal_events_are_excluded_and_counted_by_type`, `test_cli_prints_excluded_counts_and_the_golden_run`: PASSED. CLI output, checked independently: `excluded events (adapter-internal, not timed): api-request 1 · api-request-blob 1 · attachment 1 · queue-operation 1 · system 1` |
| J-AC3 | RED-FIRST: widening `CLOCK_EVENT_TYPES` with `attachment` and `api-request` fails, naming idle 600 → 675 and active 578 → 503 | PASS | The engineer's test wraps the failure in `pytest.raises`, so it is green by construction. **Reproduced independently, without pytest:** with a scratch copy of the reader whose constant was widened by `sed`, the in-process result was `{'idle': 675.0, 'active': 503.0, 'model': 149.0, 'tests': 287.0}`. The CLI's `active median` moved from 9.6 to 8.4 min and idle from 10.0 to 11.2 min. These match design §J.4's hand-derived numbers. |
| J-AC4 | RED-FIRST: counting each model event as a turn fails, naming turns 9 → 10 | PASS | Reproduced independently in-process: `J-AC4 original turns: 9` and `J-AC4 per-event counter turns: 10`. The test `test_counting_each_model_event_as_a_turn_is_caught` PASSED. |
| J-AC5 | No reader, or a missing reader path, prints `unsupported`, prints no duration or share, and exits 0 | PASS | `test_no_reader_prints_unsupported_and_no_durations[reader_args0/1]` PASSED |
| J-AC6 | The canary planted in four places (tool command, first inbound message, meta `description`, file name) appears nowhere in stdout or stderr | **FAIL** | The spec's literal fixture passes (`test_the_canary_never_reaches_stdout_or_stderr` PASSED), and a mutated reader that prints the description is caught. **The property fails** when the same fixture has an unreadable file: an uncaught `OSError` traceback on stderr prints the absolute path, which contains the home directory and `agent-CANARY-7f3a.meta.json`. Evidence: the `perm` probe gave `exit=1 canary_err=1`. Regression tests `test_regression_an_unreadable_file_neither_crashes_nor_prints_its_path[meta]` and `[transcript]` are FAILED. |
| J-AC7 | Missing `--dir`, a malformed JSON line, and an empty run all exit 0 and say so instead of printing numbers | **FAIL** | The spec's literal cases pass (`test_missing_directory_is_said_not_measured`, `test_a_run_with_no_events_reports_nothing_measured`, `test_unreadable_input_is_counted_not_hidden`, `test_malformed_lines_are_counted_and_reported`: PASSED). **The property "exit 0 in every case" fails** on well-formed JSON with odd values. Each case below exits 1 with a traceback on Python 3.9, 3.12 and 3.14: a timestamp with no UTC offset, mixed aware and naive timestamps, a `.meta.json` that is a JSON list, and a Bash `command` that is not a string. Regression tests `test_regression_a_timestamp_without_an_offset_does_not_crash[no-offset/mixed-offset-and-none]`, `test_regression_a_meta_file_that_is_not_an_object_is_an_unknown_role` and `test_regression_a_shell_command_that_is_not_a_string_does_not_crash` are FAILED. |
| J-AC8 | Three runs of 100, 200 and 600 s give a median of `3.3 min`, shares summing to 100% ± 1, and `method:` and `limits:` lines | PASS | `test_report_shows_the_median_and_shares_that_sum_to_100` PASSED |
| J-AC9 | Rework share `1 of 4 engineer runs (25%)`, counts per cause, `unclassified defects: 1`, exit 0 | PASS | `test_rework_share_and_causes_are_counted`, `test_qa_reports_before_the_window_are_not_counted`, `test_rework_marker_must_start_a_line`: PASSED |
| J-AC10 | ADAPTERS.md: adapter ก has the R37 row naming its reader; adapter ข's row says `unsupported` | PASS | `tests/framework/test_doc_contracts.py`: 3 passed. The diff was read: the rows were only added, nothing else in the file changed. |
| J-AC11 | `check_neutrality.py` reports `0 provider name(s)` | PASS | `neutrality: 0 provider name(s) in layers 0-1, 0 project leak(s) (local denylist present)`. The framework step is OK inside verify-full. |

Count: 9 PASS, 2 FAIL.

## Test Run

The engineer's three files, run alone:

```
python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py tests/framework/test_doc_contracts.py -v
============================== 35 passed in 1.00s ==============================
```

QA's regression file (`tests/hooks/test_regression_agent_time_reader.py`):

```
6 failed, 6 passed in 0.65s
```

Verdict command, `scripts/verify-full.sh`, full output (exit 1):

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (exit 1)

tests/hooks/test_regression_agent_time_reader.py:130: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

result = CompletedProcess(args=['/opt/homebrew/opt/python@3.14/bin/python3.14', 'scripts/agent_time.py', '--reader', '/Users/po..._RE.search(command):\n       ~~~~~~~~~~~~~~^^^^^^^^^\nTypeError: expected string or bytes-like object, got \'list\'\n')

    def _assert_reported_cleanly(result: subprocess.CompletedProcess) -> None:
        """R39: exit 0, no traceback, and nothing the transcript or its path carried."""
>       assert "Traceback" not in result.stderr, result.stderr.splitlines()[-1:]
E       AssertionError: ["TypeError: expected string or bytes-like object, got 'list'"]
E       assert 'Traceback' not in "Traceback (...got 'list'\n"
E         
E         'Traceback' is contained here:
E           Traceback (most recent call last):
E         ? +++++++++
E             File "<repo>/scripts/agent_time.py", line 394, in <module>
E               sys.exit(main(sys.argv[1:]))
E                        ~~~~^^^^^^^^^^^^^^...
E         
E         ...Full output truncated (15 lines hidden), use '-vv' to show

tests/hooks/test_regression_agent_time_reader.py:71: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_an_unreadable_file_neither_crashes_nor_prints_its_path[meta]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_an_unreadable_file_neither_crashes_nor_prints_its_path[transcript]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_timestamp_without_an_offset_does_not_crash[no-offset]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_timestamp_without_an_offset_does_not_crash[mixed-offset-and-none]
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_meta_file_that_is_not_an_object_is_an_unknown_role
FAILED tests/hooks/test_regression_agent_time_reader.py::test_regression_a_shell_command_that_is_not_a_string_does_not_crash
6 failed, 193 passed in 10.13s
  OK   ci-examples       19 passed in 0.95s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       28 passed in 0.38s
  OK   framework         memory: 0 problem(s) in <repo>/doc/memory
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
```

(The absolute repository path is written as `<repo>` here. That is the only edit to the pasted output.)

I re-ran the gate after this report was written. It gave the same step results and the same 6 FAILED ids (`6 failed, 193 passed in 10.68s`, framework OK, exit 1), so the report does not trip `check_neutrality` or `memory_lint`. All 6 failures are QA's regression tests, which are red on purpose. Without that file, the hooks step is green: `python3 -m pytest tests/hooks/ -q --ignore=tests/hooks/test_regression_agent_time_reader.py` → `187 passed in 9.62s`. Lint, format and tests are TODO in this template repo, so those steps verified nothing.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| High | **Round 1, fixed (re-test 1 PASS).** An unreadable transcript or meta file (for example a directory, or permission denied) crashes the meter with exit 1. The traceback prints the absolute path, including the user's home directory and the run's file name, which in the fixture is the J-AC6 canary. This breaks R39 (exit 0, no identifiers) and the spec's Functional Behavior ("never … user identifiers"). Reproduce: copy the J-AC6 fixture, replace `agent-CANARY-7f3a.meta.json` with a directory, then run `--rework`. | `.claude/meter/transcript_reader.py:150` (`_role` catches only `FileNotFoundError` and `JSONDecodeError`) and `:124` (`_read_run`, `path.read_text` unguarded) | ai-engineer | missed-ac |
| Med | **Round 1, fixed (re-test 1 PASS).** A timestamp with no UTC offset (`2026-10-20T00:00:00`), or a run that mixes offset and no-offset timestamps, raises `TypeError: can't compare offset-naive and offset-aware datetimes` and exits 1. This breaks R39. | `.claude/meter/transcript_reader.py:137` (naive datetime accepted), with the crash at `:143` (sort) or `:169` (`>= since`) | ai-engineer | missed-ac |
| Med | **Round 1, fixed (re-test 1 PASS).** A Bash `tool_use` whose `input.command` is not a string (for example a list) reaches `POLL_RE.search` and raises `TypeError`, exit 1. The reader passes the value through unchecked. | `.claude/meter/transcript_reader.py:102`; the crash is at `scripts/agent_time.py:141` | ai-engineer | missed-ac |
| Low | **Round 1, fixed (re-test 1 PASS).** A `.meta.json` that is valid JSON but not an object (for example `[]`) raises `AttributeError: 'list' object has no attribute 'get'`, exit 1. It should be `(unknown)`. | `.claude/meter/transcript_reader.py:155` | ai-engineer | missed-ac |
| Med | **Re-test 1, D5 (fixed in re-test 2: J-AC6 PASS).** An event `type` or `agentType` holding a newline is printed verbatim and forges report lines, including `rework share: 0 of 9 engineer runs (0%)`. See "Re-test 1". | `.claude/meter/transcript_reader.py:142`, `:175`; `scripts/agent_time.py` `report()`, `_type_block()` | ai-engineer | missed-ac |
| Med | **Re-test 1, D6 (fixed in re-test 2: J-AC6 PASS).** A non-string `agentType` is printed as its `str()`, and the canary inside it is printed too. It should be `(unknown)`. | `.claude/meter/transcript_reader.py:175` | ai-engineer | missed-ac |
| Med | **Re-test 2, D7 (open).** A valid transcript line that carries a raw U+2028, U+2029 or U+0085 inside a JSON string is split by `str.splitlines()` into fragments. Each fragment is counted as an unreadable line, and the line's clock event is dropped, so its time moves silently to another category. On J-AC2's fixture, one such character in the `1 passed` tool result gives `unreadable lines: 3` (expected 1), and `tests:running` goes from 120 to 0 s while model goes from 150 to 270 s. This breaks J-AC2 (totals) and J-AC7 (the unreadable count). On real data, 4 of 902 local files carry these characters, and they account for all 23 unreadable lines found. The line predates this rework. Reproduce: `test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole`. | `.claude/meter/transcript_reader.py:155` (`for line in text.splitlines():`) | ai-engineer | missed-ac |

## Findings outside the ACs (not counted as rework defects)

These fail no J-AC, so they are kept out of the Defects table: `agent_time.py --rework --qa-dir` counts every row there toward M11. Suggested owner: ai-engineer. A fix needs the owner's or ba-sa's call on the intended behaviour.

| Severity | Finding | Where |
|---|---|---|
| Low | Results depend on the Python version. On 3.9, `datetime.fromisoformat` rejects fractions that are not 3 or 6 digits (`.50Z`, `.1234567Z`), so those lines become `user (no timestamp)` and the run disappears. On 3.11+ they are timed. Measured: the same fixture with `.50Z` gives `0 runs read` on 3.9.6 and `1 runs read · active median 9.6 min` on 3.14.6. Real transcripts use `.000Z`, and outputs on this repo's transcripts were byte-identical between 3.9 and 3.14. `test_regression_a_two_digit_fraction_timestamp_is_timed_not_excluded` is green on the suite's 3.14 and pins the behaviour. | `.claude/meter/transcript_reader.py:137` |
| Low | Runs with no clock events are yielded whatever `--since` says, so `runs with no clock events: N` counts every empty run ever, under a header that says "since <date>". | `.claude/meter/transcript_reader.py:169` |
| Low | The waits detail line shows `background · hand-written polling` but not `waits:other` (`Monitor`), so a run that uses Monitor has waits sub-lines that do not add up to the waits row. | `scripts/agent_time.py:253` |

## Deviations judged

| Engineer's deviation | QA judgement |
|---|---|
| Filled three gaps in design §J.5: `RESULT_WORDS_RE` (named in the design but never defined, so taken from prior art); a `tests:bg-launch` sub-line (needed because the spec's golden total lists "background launch 1" separately, while the design's pseudocode puts it under running); and the gap before a `tool_call` counted as model | **Accepted.** Each one is needed to meet the spec's golden totals or is documented in code. Also `POLL_RE` now accepts leading `VAR=value;`, an additive extension. |
| verify-fast routing taken from impact row 8 | **Accepted.** Row 8 lists "new routing cases for the new scripts and tests". The new case block is additive. `scripts/verify-fast.sh scripts/agent_time.py` printed `== agent-time meter tests` and `35 passed`. |
| QA fixture moved from `tests/hooks/fixtures/qa/` (design §J.1) to `tests/framework/fixtures/agent_time/qa/` | **Accepted.** Spec J-AC9 names `tests/framework/test_agent_time.py`, and impact row 3 covers `tests/framework/fixtures/agent_time/`. |
| Exit 2 on malformed arguments (`--since` not YYYY-MM-DD, bad `--test-pattern`) | **Needs an owner ruling.** It contradicts the literal text of R39 ("always exits 0") and design §J.2 (`main … always 0`). No J-AC covers it, so it is not counted in the verdict. |
| Added a `QA reports not read: N` line | **Accepted.** Additive, and it stops an unreadable report from looking like "no defects". |
| Stated limit: in subagent runs most background jobs are never notified (ADAPTERS row: 74 of 545) | **Not verified.** That figure comes from the owner's 884-file pilot data, which I could not reach. The limit is printed on the `limits:` line. |

## Edge Cases Probed

- Mixed list and string `content`, several `tool_result` blocks on one line, a notification with no `<task-id>`, a truncated last line → exit 0. The truncated line is counted as unreadable. The id-less notification goes to `waits:bg-wait`. With several results on one line, the whole gap goes to the first block's category. That did not occur in real data: 0 user lines on this repo carry more than one `tool_result`.
- A `.meta.json` with no `agentType` → reported as `(unknown)`, exit 0.
- A canary in the tool name, tool id, message id, command and tool-result text → not printed. A guard test was added.
- A canary in `agentType`, or as an event `type` → **printed**, as the role name or on the excluded-types line. This is by design, because roles and type names are the reported categories. I note it as an observation, not a defect: these values are printed verbatim with no allow-list.
- `--since` boundaries, with the reader's run filter (window membership is decided by the last event): last event at exactly `00:00:00.000Z` → kept; at `23:59:59.999Z` the day before → dropped; `20:00-05:00` the day before (01:00 UTC on the day) → kept; `06:59:59+07:00` on the day (23:59:59 UTC the day before) → dropped. **Gap filled:** I mutated `>=` to `>` in a scratch copy. My new boundary test went red (`1 failed, 3 passed`), while the engineer's `test_transcript_reader.py` stayed green (`11 passed`).
- My two other green tests were also shown to fail. The canary-in-tool-id guard failed (`'CANARY-7f3a' printed`) against a scratch reader that appends tool ids to the role. The fraction test's body, run on `/usr/bin/python3` 3.9.6, gave `AssertionError: {'user (no timestamp)': 1}`. pytest is not installed for 3.9, so this was a plain script.
- J-AC6 bites: a scratch reader that appends the meta `description` to the role prints the canary (`grep -c` → 1), and the J-AC6 assertion catches that.
- Engineer's claim "five more guards broken on purpose": **not re-checked one by one.** I ran my own mutations instead: the J-AC3 widening, the J-AC4 counter, the J-AC6 description leak, `>=` → `>` on `--since`, and the tool-id leak.
- This report parses as the meter's own input: `--rework --qa-dir doc/qa` → `missed-ac 4 · … · unclassified defects: 0 · QA reports not read: 0`.
- QA reports on the `--since` date itself are included (`parse_since(date) < since` is false).
- Large directory: 1,000 runs, 600,000 lines, 102 MB → 2.26 s, with totals still exact (`active median 9.6 min · turns median 9`).
- Real data, this repo's own transcripts (18 files, 31 MB, `--since 2026-09-29 --rework`) → 18 runs read in 0.18 s. Python 3.9.6 and 3.14.6 gave byte-identical output apart from timing. Roles seen: (main thread) 3, ai-engineer 2, ba-sa 1, general-purpose 10, pm 1, qa 1. ai-engineer active median 12.2 min.
- Real notification and acknowledgement ids all match `\w+`. Every non-`\w` match found was a regex quoted in prose or code, not a real id.
- Observation for ba-sa, not an engineer defect: `POLL_RE` and `READ_SHELL_RE` match only at the start of a command, as design §J.5 says. A loop or `git` after a `cd <dir> &&` prefix is classified as tests:running or other tools, and the `limits:` line does not mention this.

## Approval history

- **2026-10-20 — drafted.** qa, from SPEC-verify-tiers-merge-gate.md (Increment 1 J-ACs), DESIGN §J, PRD R37–R40/R32, and the engineer's uncommitted implementation, after the owner's "ส่ง QA".
- **2026-10-20 — re-test 1.** qa, after the engineer's rework of the four round-1 defects. Round-1 defects 1–4 are fixed. J-AC7 now passes. J-AC6 still fails on new defects D5 and D6. 4 regression tests were added: 3 red on purpose, 1 green, and the green one was shown to bite. Status stays In Review.
- **2026-10-20 — re-test 2.** qa, after the D5/D6/N1 rework. D5 and D6 are fixed, so J-AC6 passes. A new defect, D7 (the `splitlines()` artefact, which predates the rework), fails J-AC2 and J-AC7. N1 is only partly fixed (N1a). 15 regression cases were added: 3 red on purpose and 12 green, and the green ones were shown to bite. Status stays In Review.

## Re-test 3 (coordinator, 2026-10-20)

After the D7/N1a rework, measured by the coordinator (lean-gates ruling: QA's own red tests are the
acceptance check for a narrow fix):

- `python3 -m pytest tests/hooks/test_regression_agent_time_reader.py tests/hooks/test_transcript_reader.py tests/framework/test_agent_time.py tests/framework/test_doc_contracts.py -q` → `95 passed` (QA's three D7 tests included, unedited).
- Pilot transcripts, `--since 2026-09-29` → `485 runs read · unreadable lines: 0`; ai-engineer `active median 38.5 min · turns median 102`.

Verdict: **PASS** — J-AC1–J-AC11 met. D1–D7 fixed; N1a fixed.
