# DESIGN: Verify tiers, merge gate, meter, no polling, less rework

Status: Approved
Approval: design-verify-tiers-merge-gate-2026-10-20
Owner: ba-sa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md (which derives from doc/requirements/PRD-verify-tiers-merge-gate.md)
Date: 2026-10-20

This document gives the engineer's view: interfaces, data shapes, algorithms and decisions. It contains no production code, only pseudocode and signatures. Markers work as in the spec: `[MEASURED: cmd]`, `[INFERRED]` and `[RELAYED: PRD]`. Every `[INFERRED]` must be checked before it is built on.

## 0. Layering and neutrality

| Layer | New or changed files | Rule |
|---|---|---|
| 0–1 (core, neutral) | `scripts/agent_time.py`, `scripts/verify_record.py`, `scripts/verify-handoff.sh`, `scripts/verify-merge.sh`, `scripts/verify.conf.example`, `scripts/verify-full.sh`, `scripts/coordinator_lint.py`, `scripts/handback_lint.py`, the skills, the templates, `AGENTS.md`, and `doc/framework/*` (except the exempt files) | No provider or tool names. `scripts/check_neutrality.py` must stay at 0. |
| 3 (adapter ก) | `.claude/meter/transcript_reader.py`, `.claude/hooks/guard_bash.py` | May name the adapter's formats. Declared in `doc/framework/ADAPTERS.md`. |
| exempt core | `scripts/verify-fast.sh` (already exempt: it routes adapter paths to their tests), `doc/framework/SETUP.md` | `ADAPTER_EXEMPT` is unchanged. |

The core must never contain the string `.claude`. The meter's documentation in `scripts/agent_time.py` says "pass `--reader` as declared in ADAPTERS.md".

The local denylist is matched case-insensitively, as a substring, over every text file `[MEASURED: read scripts/check_neutrality.py: leak_hits uses re.IGNORECASE over _all_text_files]`. Fixtures and examples must avoid the pilot project's vocabulary. Use the neutral alias.

---

## J. The meter (increment 1)

### J.1 Files

- `scripts/agent_time.py`: the neutral core. stdlib only. It always exits 0.
- `.claude/meter/transcript_reader.py`: the adapter ก reader.
- `tests/framework/test_agent_time.py` with `tests/framework/fixtures/agent_time/golden_run.json` (neutral events).
- `tests/hooks/test_transcript_reader.py` with `tests/hooks/fixtures/transcripts/<synthetic-session>/subagents/agent-<synthetic>.jsonl` and `.meta.json`, plus `tests/hooks/fixtures/qa/QA-*.md` for the rework case.

### J.2 The neutral event model (core)

```python
# scripts/agent_time.py
@dataclass(frozen=True)
class Event:
    t: datetime                 # timezone-aware
    kind: str                   # "model" | "tool_call" | "tool_result" | "notification" | "inbound"
    message_id: str | None = None    # model events: one id per model response
    tool_id: str | None = None       # tool_call / tool_result pairing
    tool_kind: str | None = None     # "shell" | "read" | "search" | "edit" | "wait" | "other"
    command: str | None = None       # shell text, used for classification only, NEVER printed
    background: bool = False         # tool_call launched as a background job
    job_ids: tuple[str, ...] = ()    # tool_result: job id it announced; notification: ids it reports
    text: str | None = None          # inbound text, used only for the REWORK: marker, NEVER printed

@dataclass(frozen=True)
class Run:
    agent_type: str             # role name, e.g. "ai-engineer"; "(main thread)" for the coordinator
    events: list[Event]         # clock events only, sorted by t
    excluded: Counter[str]      # adapter-internal event types the reader dropped, by type name
    unreadable_lines: int

REWORK_CAUSES = ("missed-ac", "regression", "spec-defect", "test-gap", "env-flaky")
CATEGORIES = ("model", "tests", "waits", "other tools", "read/git/edit")

def categorise(run: Run) -> dict[str, float]          # seconds per category + sub-lines + "idle", "active", "turns"
def report(runs: list[Run], since: datetime) -> str    # text block; never raises
def rework_report(runs: list[Run], qa_dir: Path, since: datetime) -> str
def load_reader(path: Path) -> ModuleType | None       # importlib.util.spec_from_file_location; None if missing
def main(argv: list[str]) -> int                       # always 0
```

The reader contract, which every adapter's reader implements, is documented in the docstring of `agent_time.py`:

```python
def runs(source: Path, since: datetime) -> Iterator[Run]
```

A reader yields only clock events (`user`- and `assistant`-equivalent). It counts every other event type in `Run.excluded`.

### J.3 Adapter ก reader: what the format is (MEASURED on this repo's own transcripts)

These facts were measured over this repo's own 15 transcript files `[MEASURED: python3 heredoc over ~/.claude/projects/<this repo's slug>/*.jsonl and */subagents/*.jsonl, printing only type names and counts]`.

- **Layout.** Subagent runs are `<dir>/<session>/subagents/agent-<id>.jsonl`, each with a sibling `agent-<id>.meta.json`. The meta keys are `agentType`, `description`, `finished`, `launchedWithDefaults`, `requestNonInteractive`, `requestShape`, `spawnDepth` and `toolUseId`. `[MEASURED: 12 meta files]`
- **Main-thread sessions** are `<dir>/<session>.jsonl` `[MEASURED: ls]`.
- **Event types**, counted as `(type, has timestamp)`:

  | Type | Timestamp | Count |
  |---|---|---|
  | `assistant` | yes | 733 |
  | `attachment` | yes | 658 |
  | `user` | yes | 512 |
  | `api-request-blob` | **no** | 383 |
  | `api-request` | yes | 289 |
  | `system` | yes | 82 |
  | `atis-latch` | no | 80 |
  | `last-prompt` | no | 79 |
  | `mode` | no | 74 |
  | `permission-mode` | no | 74 |
  | `ai-title` | no | 73 |
  | `queue-operation` | yes | 62 |
  | `file-history-snapshot` | no | 24 |
  | `api-request-shape` | yes | 22 |
  | `cost-state` | no | 2 |
  | `file-history-delta` | yes | 1 |

  `[MEASURED]`
- **`api-request-blob` events carry content blocks of type `tool_use` and `tool_result`** (93 and 47 in the subagent files) `[MEASURED]`. A reader that took content blocks from every event would double-count tools. This is a second reason for the allow-list (ADR-2).
- **One model response spans several `assistant` lines.** There were 501 assistant lines and 170 distinct `requestId` values, which equals 170 distinct `message.id` values `[MEASURED]`. Hence ADR-3.
- **Content blocks seen.** `assistant` lines carry `tool_use`, `thinking`, `text`, `server_tool_use` and `advisor_tool_result`. `user` lines carry `tool_result` `[MEASURED]`.
- **Background completion.** A user event whose text contains `task-notification` is how a background job's completion arrives. 2 such events were seen locally `[MEASURED]`. The id format `<task-id>…</task-id>`, and the launch acknowledgement `background with ID: <id>`, are taken from the coordinator's prior-art scripts `[INFERRED: not observed locally, because 0 background tool_use calls were found in the local subagent files; the fixture encodes the prior-art shape, and the trial must confirm it on pilot transcripts]`.

Mapping from the adapter format to neutral events:

| Adapter line | Neutral event |
|---|---|
| `type == "assistant"` | `model` with `message_id = message.id`. For each `tool_use` block, also a `tool_call` at the same `t`. `tool_kind` comes from the tool name: `Bash` → shell; `Read` → read; `Grep`/`Glob` → search; `Edit`/`Write`/`MultiEdit`/`NotebookEdit` → edit; `Monitor` → wait; everything else → other. `background = input.run_in_background`. |
| `type == "user"` with `tool_result` blocks | `tool_result` per block. `job_ids` comes from `background with ID: (\w+)` in the result text. |
| `type == "user"` with `task-notification` text | `notification` with `job_ids` from `<task-id>(\w+)</task-id>` |
| `type == "user"`, anything else | `inbound` (`text` kept in memory only) |
| any other `type` | dropped, and counted in `excluded[type]` |
| a line without `timestamp`, or a JSON error | dropped. A JSON error is counted in `unreadable_lines`. |

The single constant the mutation targets is `CLOCK_EVENT_TYPES = frozenset({"user", "assistant"})`.

### J.4 Golden timeline (fixture; times in seconds from t0)

| t | Event | Gap ends as |
|---|---|---|
| 0 | inbound brief (contains canary in J-AC6 variant) | — |
| 60 | model m1 (thinking) | model 60 |
| 70 | model m1, tool_call T1 shell `pytest tests/x` | model 10 |
| 190 | tool_result T1 | tests (running) 120 |
| 200 | model m2, tool_call T2 read | model 10 |
| 205 | tool_result T2 | read/git/edit 5 |
| 215 | model m3, tool_call T3 shell `scripts/verify-full.sh` background | model 10 |
| 216 | tool_result T3, announces job `b1` | tests (background launch) 1 |
| *217* | *internal `api-request`* | *(excluded)* |
| 226 | model m4, tool_call T4 shell `until grep -q passed out.log; do sleep 10; done` | model 10 |
| *300* | *internal `attachment`* | *(excluded)* |
| 346 | tool_result T4 | tests (hand-written polling) 120 |
| 356 | model m5 (text, ends turn) | model 10 |
| 476 | notification for `b1` | tests (background wait) 120 |
| 486 | model m6 | model 10 |
| *700* | *internal `system`, `queue-operation`* | *(excluded)* |
| 1086 | inbound coordinator message | idle 600 |
| 1096 | model m7, tool_call T5 edit | model 10 |
| 1098 | tool_result T5 | read/git/edit 2 |
| 1108 | model m8, tool_call T6 shell `make docs` | model 10 |
| 1168 | tool_result T6 | other tools 60 |
| 1178 | model m9 (final text) | model 10 |

There are also `api-request-blob` lines with no timestamp, which carry `tool_use` and `tool_result` blocks reusing T1's id, and one malformed line.

**Totals:**
- model 150;
- tests 361 (120 + 1 + 120 + 120);
- of which hand-written polling 120;
- waits 0;
- other tools 60;
- read/git/edit 7;
- idle 600;
- active 578;
- span 1178;
- turns 9;
- assistant lines 10 (m1 has two lines).

**Under the J-AC3 mutation** (`attachment` and `api-request` treated as clock events, falling through to `inbound`):
- the gap 216→217 becomes idle 1, and 217→226 becomes model 9;
- the gap 226→300 becomes idle 74, and 300→346 becomes polling 46;
- so idle is 675, active 503, model 149 and tests 287.

These numbers are derived by hand from the table `[INFERRED: the engineer's test is the measurement]`.

### J.5 Categorisation (core)

```
prev = first event; for e in events[1:]:
    gap = e.t - prev.t
    if e.kind == "model": cat = "model"
    elif e.kind == "tool_result": cat = category_of(pending.pop(e.tool_id))   # unmatched → "other tools"
    elif e.kind == "notification": cat = "tests:bg-wait" if any(id in test_jobs for id in e.job_ids) else "waits:bg-wait"
    else (inbound): cat = "idle"
    add gap to cat; prev = e
category_of(call):
    shell and POLL_RE matches command  → ("tests:polling" if TEST_RE or RESULT_WORDS_RE matches else "waits:polling")
    shell and TEST_RE matches          → "tests:running" (if background: also remember the announced job id in test_jobs)
    tool_kind in {read, search, edit}, or shell starting with grep/rg/cat/sed -n/head/tail/ls/find/wc/git → "read/git/edit"
    tool_kind == "wait"                → "waits:other"
    otherwise                          → "other tools"
turns = len({e.message_id for e in events if e.kind == "model"})
```

- `TEST_RE = r"verify-|pytest|playwright|vitest|jest|npm (run )?test|go test|cargo test"`. These are neutral tool names, not providers. The project can extend it with `--test-pattern`.
- `POLL_RE`: the meter's own text matcher, for after-the-fact detection. It is a loop keyword (`until`, `while`, `for`) at the start, with `sleep` in the body. It is deliberately independent of the guard, so that adapter ข projects also get a reading.

### J.6 Output (example shape; all numbers from the computation)

```
agent-time — <N> runs read since <date> · reader: <reader file name> · unreadable lines: <k>
excluded events (adapter-internal, not timed): api-request 289 · attachment 658 · …
ai-engineer: 170 runs · active median 51.0 min · turns median 34
  model generating        19.5 min/run  39%
  tests                   18.5 min/run  37%   (running 13.6 · background wait 2.5 · hand-written polling 2.4)
  waits (background/poll)  5.4 min/run  11%   (hand-written polling 0.0)
  other tools              5.1 min/run  10%
  read/git/edit            1.3 min/run   3%
  hand-written polling loops, all categories: 2.4 min/run (already counted above)
  idle (not active): median 0.0 min/run
method: gaps between consecutive clock events, attributed to the event that ends the gap; …
limits: commands are classified by pattern, not meaning; a loop hidden inside a script is not seen; …
```

The figures above illustrate the shape using the PRD's baseline `[RELAYED: PRD]`. They are not a claim about what the meter will print. Per-run figures are means for the category split, and medians for active time and turns. The `method:` line says which is which.

### J.7 Rework report (`--rework [--qa-dir doc/qa]`)

- **Rework share.** An engineer run (`ai-engineer`, `frontend-engineer`) is a rework run when its first inbound text has a line matching `^REWORK:` (ADR-13). The report prints `rework share: k of n engineer runs (p%)`. Before the marker is adopted, rework is only reported as `unmarked` (the PRD's 23% baseline is `[RELAYED: PRD]` and came from a heuristic).
- **Causes.** For each `QA-*.md` in `--qa-dir` whose `Date:` falls in the window and whose verdict line says FAIL, the Defects table's `Rework cause` cell must be exactly one of `REWORK_CAUSES`. The report prints counts per cause and `unclassified defects: k`.

### J.8 Stated limits (printed on the `limits:` line)

- Classification uses patterns.
- Agent reuse inflates idle time, not active time.
- A run's window membership is decided by its last event.
- "Unsupported" is printed instead of zero when no reader is given.

---

## AC. Full-run tier and the no-fake-green guarantee (increment 2)

### AC.1 `scripts/verify.conf` (the project's file; the template ships `scripts/verify.conf.example`)

This is a bash file. Every tier sources it with `[ -f scripts/verify.conf ] && . scripts/verify.conf`, after exporting the run variables (`VERIFY_RUN_DIR`, `VERIFY_JUNIT_DIR`). Commands are therefore stored as strings and run with `eval`, so that `$VERIFY_JUNIT_DIR` expands per step `[INFERRED: bash expands unquoted variables at assignment time; single-quoting in the conf plus eval at run time avoids that — the engineer verifies with a probe]`.

| Key | Default | Used by | Meaning |
|---|---|---|---|
| `LINT`, `TEST` (arrays) | the in-script TODO defaults | fast | Overrides the fill-in block, so that a project never edits the script (R24). |
| `STEPS` (array) | the in-script defaults | full | As above. The in-script default strings stay byte-identical (the tests pin them). |
| `VERIFY_TEST_STEPS` | empty; the example conf suggests `"tests"` | full | Labels of steps that run tests. Each must write JUnit into `$VERIFY_JUNIT_DIR`. Empty means no JUnit, zero-case or count checks at all (R12, AC-AC15). |
| `VERIFY_COLLECT_CMD` | empty | all | Prints one integer: the number of tests the full run would report. Example (pytest, in a comment): `pytest --collect-only -q | tail -1`, parsed by the recorder. |
| `VERIFY_HANDOFF_TIER` | `off` | handoff, rules | `on` = opted in (D4). |
| `VERIFY_BASE_REF` | `origin/main` | handoff | The base for the diff. |
| `VERIFY_SELECT_CMD` | empty | handoff | Gets the selected paths as arguments, runs the related tests, and writes JUnit into `$VERIFY_JUNIT_DIR`. |
| `VERIFY_FULL_TEST_CMD` | empty | handoff | Runs the full collected set, writing JUnit (the R8 fallback). |
| `VERIFY_UNTRACKED_INPUTS` | empty | handoff | Space-separated globs the selector cannot track. Empty means the full set every time (R8). |
| `VERIFY_STEP_BUDGET_S` | `900` | full | A per-step warning threshold. |
| `VERIFY_TEST_BUDGET_SMALL_S` / `_MEDIUM_S` / `_LARGE_S` | `1` / `10` / `60` | full | Per-test warnings by size class. This confirms A5. |
| `VERIFY_TEST_SIZE_RULES` | empty | full | `glob=class` pairs, matched against the test id's file part. Unmatched tests are `small`. |
| `VERIFY_BASELINE_FILE` | empty | full, merge | The R21 baseline (§E). |
| `VERIFY_MERGE_GATE` | `none` | merge | `runner`, `local-fallback` or `none`. |
| `VERIFY_RUNNER_ID` | empty (env) | full, merge | Set by the runner. If empty, the record says `local:<hostname>`. |
| `VERIFY_EXTRA_BANNED` | empty | all | Extra banned tokens the project adds (it can only add, never remove). |
| `VERIFY_ALLOWED_FILTERS` (array) | empty | all | Declared marker and deselect filters the project's own step commands may use. Each entry is `"<filter exactly as written in the command>\|<reason>"`. Rules are in §AC.3 (ADR-14). |

### AC.2 `verify-full.sh` flow (pseudocode)

```
cd repo root; RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$$; RUN_DIR=.verify/runs/$RUN_ID; mkdir -p
export VERIFY_RUN_DIR=$RUN_DIR; source conf if present
[ -f scripts/verify_record.py ] || { print "EXIT GATE RED — recorder missing (scripts/verify_record.py)"; exit 1; }
python3 scripts/verify_record.py check-banned -- "${STEPS[@]}" $VERIFY_EXTRA_BANNED || exit 2
TREE_BEFORE=$(python3 scripts/verify_record.py tree-hash)          # "null" outside a git work tree
COLLECTED=$( [ -n "$VERIFY_COLLECT_CMD" ] && eval "$VERIFY_COLLECT_CMD" | verify_record.py parse-int )
for entry in STEPS:
    TODO branch unchanged (prints the same row; records todo=true)
    if label in VERIFY_TEST_STEPS: export VERIFY_JUNIT_DIR=$RUN_DIR/junit/$label; mkdir -p
    t0=$(date +%s); eval cmd; rc; secs=$(( $(date +%s) - t0 ))
    row unchanged except "(${secs}s)" inserted before the tail text
    append "label\trc\tsecs\ttodo\tjunit_dir" to $RUN_DIR/steps.tsv
TREE_AFTER=$(… tree-hash)
python3 scripts/verify_record.py finalize --run-dir $RUN_DIR --tier full --tree-before … --tree-after … \
        --collected "$COLLECTED" --baseline "$VERIFY_BASELINE_FILE"        # prints unindented summary lines,
                                                                        # writes record.json, last line VERDICT=<v>
banner chosen from: step failure | count mismatch | empty step | tree changed | new failures  → RED
                    failures == baseline exactly                                                → RED (baseline form)
                    todo > 0                                                                     → INCOMPLETE
                    else                                                                         → GREEN
echo "record: $RUN_DIR/record.json"
```

- The existing precedence holds: RED outranks INCOMPLETE `[MEASURED: read scripts/verify-full.sh:73-88]`.
- The step row keeps its 2-space indent and its `OK`/`FAIL`/`TODO` prefix.
- The recorder prunes `.verify/runs/` to the 20 newest directories.

### AC.3 Ban list (R4). Matched on whole tokens, in configured commands and in verify-fast's arguments.

Today no script enforces the bans: they exist only as comments `[MEASURED: grep -rn -- '--lf\|last-failed\|exitfirst' scripts .claude/hooks → only verify-fast.sh:6 (a comment) and coordinator_lint.py:63,72 (which governs MEASURED: claims, not runs)]`.

| Token(s) | Reason printed |
|---|---|
| `--lf`, `--last-failed` | selects nothing after a green run |
| `-x`, `--exitfirst`, `--maxfail`, `--maxfail=*`, `--bail`, `--bail=*` | hides the other failures |
| `-k`, `-k*` | filter used to reach green |
| `-m`, unless the previous token's program name starts with `python` | marker deselection used to reach green |
| `--reruns`, `--reruns=*`, `--retries`, `--retries=*`, `--retry`, `--retry=*`, `--flake-finder` | retries turn a failure into a pass |
| `--cache_test_results*`, `--cache-test-results*` | a cached result reported as a fresh run (build-tool result caching) `[INFERRED: flag spelling per build tool; the engineer checks it against each tool's docs, and the project extends the list with VERIFY_EXTRA_BANNED]` |
| anything in `VERIFY_EXTRA_BANNED` | project-declared |

- Selection tools whose selection *runs* tests are not banned. Only the R4 shapes are.

**The declared allow-list (`VERIFY_ALLOWED_FILTERS`, owner ruling 2026-10-20, ADR-14).**

```python
ALLOWLISTABLE = frozenset({"-m", "-k", "--deselect"})          # marker / deselect filters only
NEVER_ALLOWLISTABLE = ("--lf", "--last-failed", "-x", "--exitfirst", "--maxfail", "--bail",
                       "--reruns", "--retries", "--retry", "--flake-finder",
                       "--cache_test_results", "--cache-test-results")   # prefix match on '=' forms too

def parse_allowlist(entries: list[str]) -> list[Allowed] | Error
    # entry "<filter>|<reason>": split on the LAST '|'; filter = shlex.split(left) → [flag, value]
    # flag ∉ ALLOWLISTABLE              → Error("<flag> can never be allow-listed") if flag in NEVER… else Error("only -m/-k/--deselect can be declared")
    # reason.strip() == ""              → Error("allow-list entry without a reason: <filter>")
def check_banned(command_tokens, allowed, source: "configured" | "runtime") -> list[Violation]
    # a (flag, value) pair in a CONFIGURED command is waived iff (flag, value) ∈ allowed — exact value match
    # source == "runtime" (verify-fast "$@", handoff "$@"): the allow-list never applies
```

- Tokens are compared after `shlex.split`, so `-m "not real_sleep"` in the conf and in the command compare as `["-m", "not real_sleep"]` `[INFERRED: shlex matches bash word-splitting for these simple quoted forms; the engineer pins it with AC-AC16]`.
- Each declared filter prints the unindented line `declared filter: <filter> — <reason>` on every run of every tier. The record stores it as `declared_filters: [{"filter", "reason"}]`.
- A declared deselect also has to be applied by `VERIFY_COLLECT_CMD`, or the count check reports a mismatch (RED). That is the honest outcome: the record states what was left out and why.
- The structural defence against cached passes is that counts are read only from this run's fresh `$RUN_DIR`.
- This is a stated limit: a ban can be hidden inside a script the step calls. The rule is tamper-evident, not tamper-proof.

### AC.4 Counts

```python
# scripts/verify_record.py
def junit_counts(dir: Path) -> Counts            # sums every *.xml under dir; Counts(passed, failed, skipped, reported, files,
                                                  #   failing_ids: list[str], durations: list[(id, seconds)])
```

- `reported` = the number of `<testcase>` elements. Skipped cases count, because they were collected and reached the runner.
- A case is failed if it has a `<failure>` or `<error>` child, and skipped if it has a `<skipped>` child.
- The id is `classname::name`.
- Several files in one directory are summed. These are shards. A worker-parallel run writes one file through its controller `[INFERRED for pytest-xdist; the trial confirms]`.
- `files == 0` → `no JUnit report written by step <label>`. `reported == 0` → `0 tests reported by step <label>`. Both are RED (R2).
- The count check: the sum of `reported` over the test steps must equal `COLLECTED`, or the result is RED with `reported N of M collected`.

### AC.5 Tree identity (R5)

`tree-hash`:
1. Copy `.git/index` to a temporary file.
2. Run `GIT_INDEX_FILE=<tmp> git add -A`.
3. Run `GIT_INDEX_FILE=<tmp> git write-tree`.
4. Delete the temporary file.

`[MEASURED in a scratch repo: dirty-tree hash 798b662… ≠ HEAD tree 3be22be…; repeat gives the same hash; afterwards `git status --porcelain` still shows ` M f` and `?? new`, and `git diff --cached` is empty, so the real index is untouched.]`

- The hash includes untracked files that are not ignored. `.verify/` is git-ignored, so the run's own outputs never change the hash `[INFERRED: depends on the .gitignore entry; test AC-AC10 covers it]`.
- `before != after` → RED: `tree changed during the run — this run is evidence for neither tree`. This applies only when `scripts/verify.conf` exists. Without it, the same line is printed as informational, with `(not enforced: no scripts/verify.conf)`, so a project whose tests write non-ignored artifacts keeps its verdict (R12, AC-AC15).
- A project that opts in must git-ignore every artifact its tests write. `SETUP.md`'s switch section says so as one of its steps.

### AC.6 Record schema (`.verify/runs/<run-id>/record.json`, `schema: 1`)

```json
{
  "schema": 1, "tier": "full|handoff|fast|merge", "run_id": "...", "started_at": "ISO-8601Z", "ended_at": "...",
  "tree": {"before": "hash|null", "after": "hash|null", "head": "sha|null", "dirty": true},
  "runner": {"id": "...", "kind": "runner|local|local-fallback"},
  "steps": [{"label": "tests", "exit": 0, "seconds": 812, "todo": false,
             "tests": {"passed": 0, "failed": 0, "skipped": 0, "reported": 0, "files": 1}}],
  "collected": 12338, "count_check": "ok|mismatch|not-configured",
  "failures": ["classname::name"],
  "baseline": {"file": "...", "known": [], "new": [], "now_passing": [], "expired": [], "invalid": [], "refused": []},
  "selection": {"base": "...", "diff": [], "named": [], "touched_not_named": [], "named_not_touched": [], "full_set_reason": null},
  "warnings": ["..."], "slowest": [{"id": "...", "seconds": 0.0, "size": "small"}],
  "verdict": "GREEN|RED|RED-BASELINE|INCOMPLETE|EMPTY|NOT-CONFIGURED"
}
```

The record holds test ids, labels and hashes, and never file contents or output text. `collected: 12338` in the example is the pilot's figure `[RELAYED: PRD]`, used only for illustration.

### AC.7 Fast tier changes

- It sources the conf.
- It runs `check-banned` over `"$@"` and the configured `LINT`/`TEST`. Exit 2 means banned.
- It exports a fresh `VERIFY_JUNIT_DIR` before the TEST command runs.
- The last line comes from `finalize --tier fast`:
  - `FAST VERIFY OK — partial run: ran N of M`;
  - `… ran ? of ? (counts not configured)` when the TEST command writes no JUnit or `VERIFY_COLLECT_CMD` is empty;
  - `FAST VERIFY EMPTY — ran 0 of M; nothing was verified` (exit 1) when JUnit exists but holds 0 cases.
- The existing `FAST VERIFY INCOMPLETE` branch is unchanged.

---

## G. No hand-written polling (increment 3)

The polling rule in `.claude/hooks/guard_bash.py` reuses `_executable_segments`.

**What the segments look like today `[MEASURED: python3 -c over guard_bash._executable_segments]`:**
- `until grep -q passed out.log; do sleep 10; done` → `[['until','grep',…], ['do','sleep','10'], ['done']]`.
- `while true; do tail -1 x; sleep 30; done` → `[['while','true'], ['do','tail',…], ['sleep','30'], ['done']]`.
- `for i in $(seq 20); …` produces a `['for',…]` segment and a `['sleep','5']` segment.
- `while read l; do echo $l; done < f` has no `sleep` segment.
- A quoted mention and `bash -c "<loop>"` both collapse into one segment whose program is `grep` or `bash`.

```python
_LOOP_KEYWORDS = frozenset({"while", "until", "for"})
_BODY_KEYWORDS = frozenset({"do", "then", "else", "elif", "{", "!"})

def _program_after_keywords(tokens: list[str]) -> str: ...      # strip leading _BODY_KEYWORDS, return program name
def _polling_loop_reason(segments: list[list[str]]) -> str | None:
    has_loop  = any(seg[0] in _LOOP_KEYWORDS for seg in segments)
    has_sleep = any(_program_after_keywords(seg) == "sleep" for seg in segments)
    return "a hand-written polling loop (loop + sleep)" if has_loop and has_sleep else None
```

- It runs in `main()` after the A1' loop and is independent of tree state.
- The block message: `BLOCKED (.claude/hooks/guard_bash.py, rule R26): <reason>. Do not poll. If you launched the work in the background, end your turn or do independent work — the completion notification will arrive. See AGENTS.md / engineering-loop "Waiting on background work".`
- The rule ignores `ALLOW_DESTRUCTIVE=1`.

**Override `ALLOW_POLL=1` (owner ruling 2026-10-20, ADR-9).** The existing `_has_head_override(command)` is generalised to `_has_head_override(command, assignment)`, with the same logic as `guard_bash.py:226-240`:
- It looks at the first segment only.
- It walks the leading env-assignment tokens.
- It returns True only if one of them equals the given assignment.

The two rules then use it like this:
- A1' calls `_has_head_override(command, "ALLOW_DESTRUCTIVE=1")`.
- R26 calls `_has_head_override(command, "ALLOW_POLL=1")`.
- Neither override waives the other's rule.

The working form is `ALLOW_POLL=1; <loop>`. An assignment directly before `until`/`while`/`for` is a bash syntax error `[MEASURED: bash -c 'ALLOW_POLL=1 until true; do sleep 0; done' → syntax error near unexpected token 'do'; 'ALLOW_POLL=1; until …' → rc=0]`. The first segment of `ALLOW_POLL=1; until …` is `['ALLOW_POLL=1']` `[MEASURED: guard_bash._SEGMENT_SPLIT_PATTERN.split(...)[0].split()]`, which the head check accepts. The first segments of `echo ALLOW_POLL=1 && …` and `until true; do ALLOW_POLL=1 sleep 1; done` are `['echo','ALLOW_POLL=1']` and `['until','true']` `[MEASURED, same probe]`, which it rejects.

The block message names the override: `…if this loop is genuinely not a wait on background work, re-run it as "ALLOW_POLL=1; <loop>" so the choice is on the record.`

**Stated limits**, recorded in ADAPTERS.md:
- A loop inside `bash -c "…"`, inside a heredoc, or inside a script file is not seen.
- Tools other than Bash (for example a harness's own monitor tool) are outside the matcher `[MEASURED: settings.json matcher is "Bash"]`.
- The R37 meter reports the residue after the fact.

**Q12 (does the rule apply to the coordinator?):**
- The hook entry has no role filter, so it applies wherever PreToolUse hooks fire.
- That it fires for the main thread is `[INFERRED from guard_agent_spawn.py, a PreToolUse hook that by design intercepts the main thread's spawns]`.
- That it fires inside subagents is `[INFERRED]`, and F-AC3(c) settles it.

---

## B. Handoff tier (increment 4)

```
verify-handoff.sh [--status] [paths…]
  --status: print "opted in" if conf sets VERIFY_HANDOFF_TIER=on else "not opted in"; exit 0
  not opted in → HANDOFF TIER NOT CONFIGURED …; exit 3
  check-banned over VERIFY_SELECT_CMD, VERIFY_FULL_TEST_CMD, LINT, "$@"
  sel = verify_record.py diff-paths --base "$VERIFY_BASE_REF" -- "$@"
        diff  = git diff --name-only <merge-base(base, HEAD)>  (committed)
              ∪ git diff --name-only HEAD                         (unstaged + staged)
              ∪ git ls-files --others --exclude-standard          (untracked)
        named = "$@"; selected = diff ∪ named
        touched_not_named = diff − named (only reported when named ≠ ∅); named_not_touched = named − diff
        full_set_reason = "base <ref> not found" | "no untracked inputs declared"
                        | "declared untracked input changed: <p>" | null
  LINT over selected paths (fast tier's LINT), if configured
  if full_set_reason: eval VERIFY_FULL_TEST_CMD   else: eval "$VERIFY_SELECT_CMD <selected…>"
  finalize --tier handoff → "HANDOFF TIER — ran N of M (selected by machine from the diff against <base>)"
                           | "HANDOFF TIER — ran M of M (full collected set — <reason>)"
                           | RED / EMPTY forms; never GREEN
```

- Globs are matched with `fnmatch` on POSIX paths, and `**` is treated as matching across directories `[INFERRED: fnmatch's * already crosses '/'; the engineer pins this with a test]`.
- The selector's own safety is the project's concern (ADR-7). The wrapper guarantees five things: the input is never narrower than the diff; untracked inputs force the full set; zero cases is never a pass; the label is honest; and a record exists.

---

## H. Rework (increment 5)

- **Spec section (R29).** The heading is exactly `## Affected tests / affected files`. `tests/framework/test_doc_contracts.py::test_every_reviewed_spec_lists_affected_tests(root)` is parametrised on a root directory so that the planted case can run in `tmp_path`.
- **Self-check grammar (R30).** In the handback, a line `Self-check:` is followed by lines matching `^\s*[-*]?\s*(<AC-ID>)\s*:\s*(.+?)\s*(→|->)\s*(.+)$`, where the groups are command and result. `handback_lint.py --spec <path>` reads AC ids from the spec's first table column (`^\|\s*([A-Z]*-?AC\d+)\s*\|`), and reports each missing id, and each line with an empty command or result.
- **QA rework cause (R31).** The QA template's Defects table gets a fifth column, `Rework cause`, and a line under it listing the vocabulary. The doc-contract test imports `REWORK_CAUSES` from `scripts/agent_time.py`, so the list has one source.
- **No retro-failing (upgrade safety).** The R29 check applies to specs at `In Review` only. The R31 check applies to FAIL reports dated on or after `REWORK_CAUSE_REQUIRED_FROM`, a constant the engineer sets to the ship date, as `correction_rate.py:33` does. `tests/framework/` runs inside every downstream project's gate, so a check that judged old documents would turn an upgraded project red over its history, and would force the trial to edit pilot documents (R24, R25).

## D. Merge gate (increment 6)

```
verify-merge.sh [<ref>=HEAD]
  source conf; mode=$VERIFY_MERGE_GATE
  mode == none                         → MERGE GATE NOT RUN — no runner and no local fallback configured; exit 3
  VERIFY_COLLECT_CMD empty             → MERGE GATE NOT RUN — executed == collected is not configured; exit 3
  sha=$(git rev-parse <ref>^{commit}); want=$(git rev-parse <ref>^{tree})
  wt=$(mktemp -d)/merge-gate-$sha; git worktree add --detach "$wt" "$sha"
  copy scripts/verify.conf and the baseline file into $wt if untracked     [INFERRED: a project may keep them untracked]
  runner kind: VERIFY_RUNNER_ID set → "runner" ; else mode == local-fallback → "local-fallback", id "local:<host>"
  (cd "$wt" && VERIFY_RUNNER_KIND=… scripts/verify-full.sh); rc
  record = newest $wt/.verify/runs/*/record.json; copy it to .verify/merge/<sha>.json in the caller's repo
  verify_record.py check-record --record … --tree "$want" → one of the four forms, appending " — tree <want> — runner <id>"
  local-fallback suffix: "(local fallback — weaker: same machine and same user as the agent)"
  git worktree remove --force "$wt"
verify-merge.sh --check <record> [<ref>]   → re-checks an existing record (e.g. pulled from CI) against <ref>'s tree
```

- **Detached local fallback (R16).** Start it as `nohup scripts/verify-merge.sh <ref> > .verify/merge/<sha>.log 2>&1 &`. Where the adapter has background jobs with a completion notification, start it through that facility, so the caller is notified without polling. `setsid` is unavailable on the owner's machine `[MEASURED: which setsid → not found; nohup → /usr/bin/nohup]`. Whether a `nohup` child survives the agent session ending is `[INFERRED]`, and the trial checks it once, as an extra probe.
- **CI (R17).** In both `ci-examples/*.yml`, the gate-2 step gains an `env` entry `VERIFY_RUNNER_ID` set from the platform's runner-name variable. The `run`/`script` string stays `./scripts/verify-full.sh` `[MEASURED: tests/ci/test_ci_examples.py:432-440 asserts that exact string]`. The provider-specific variable names live only in `ci-examples/`, which is not core.
- **R14 patterns (D-AC6).** Each requiring location must match at least one pattern `[INFERRED from the grep output of 2026-10-20; the engineer asserts this mapping in the test itself]`:

  | Pattern | Requiring locations it matches |
  |---|---|
  | `before every handoff` | `verify-full.sh:2` |
  | `before \*\*every\*\* handoff` | `engineering-loop:45` |
  | `ก่อนส่งมอบทุกครั้ง` | `AGENTS.md:46` |
  | `ก่อนถือว่าเสร็จ` | `SETUP.md:38` |
  | `exit gate, before the handoff` | `ai-engineer:30` |
  | `verify-full\.sh\`? output` | `ai-engineer:37`, `engineering-loop:69` |
  | `the verdict command is the exit gate` | `qa:18` |
  | `run the full suite` | `qa:28`, `frontend-qa:15`, `frontend-qa:30` |
  | `EXIT GATE \(full tier\)` | `engineering-loop:13` |
  | `Paste this output in the handoff` | `verify-full.sh:89` |

  - **Exemption:** lines beginning `Do not:`, which covers `coordinator-discipline:144`.
  - **The banner.** `verify-full.sh:89` is a banner: the words `EXIT GATE GREEN` stay (R12), and only the tail changes, to `Paste this output in the handoff when not opted in; when opted in, the merge gate's record is the evidence.`
- **Rule rewording (R14).** The qualifier wording is fixed so that D-AC6 can match it. Every requiring line gains either "(when `scripts/verify-handoff.sh --status` says *not opted in*; an opted-in project hands off on the handoff tier and runs the full suite once per merge in the merge gate)", or its Thai equivalent with `ยังไม่ opt-in`.

## I. Brief check (increment 7)

In `coordinator_lint.py`, rule 6 works as follows:
- For each line `^Slice:`, the block runs until the next blank-line-separated `Slice:` or the end of the text.
- The block must contain `^Files:\s*\S`, `^Criteria:\s*\S` and `^Verify with:\s*\S`.
- A violation reads `rule 6 (line n): brief has no 'Files:' line — name the exact files to touch or read`.
- The brief template gains:
  ```
  Files:        <exact paths to touch · to read>
  Criteria:     <AC ids in scope>
  REWORK:       <doc/qa/QA-….md> (only when this dispatch is QA rework)
  ```

## E. Baseline and quarantine (increment 8)

Baseline file format, one test per line:

```
<classname::name>  state=known-red
<classname::name>  state=quarantined owner=<name> expires=<YYYY-MM-DD>
# comments allowed
```

The comparison runs inside `finalize`:

```
F = failing ids this run; B = ids in file
new          = F − B
now_passing  = B − F
expired      = quarantined entries with expires < today ∧ id ∈ F      → moved into new
invalid      = quarantined entries missing owner or expires ∧ id ∈ F  → moved into new
refused      = quarantined entries failing in every one of the last 3 retained records ∧ this run → moved into new
verdict      = RED-BASELINE iff step failures come only from test steps ∧ new == ∅ ∧ now_passing == ∅ ∧ every other check passed
```

`baseline-write --record <r> --out <f>` writes `F` as `state=known-red` lines, sorted.

## F. Trial (increment 9): procedure outline (for qa and the coordinator, run from this framework's session)

1. Create a worktree or copy of the pilot project (A3). Record its `git status`, branches and stash list.
2. **Upgrade:** copy the new framework files into the worktree, and commit them as `<upgrade-commit>`.
3. **Switch:** write `scripts/verify.conf` (moving the pilot's step commands into it) and the baseline from `baseline-write`. Count the steps and the minutes. Commit as `<switch-commit>`.
4. Measure the before numbers with the meter over the pilot's transcripts (same flags as after).
5. Run at least 3 features or replays through the opted-in pipeline, and run the merge gate per merge.
6. Run the three probes, revert them, and show zero residue.
7. Measure the after numbers. Run `handback_lint.py --partial-claims` over every report. Write `doc/qa/QA-verify-tiers-merge-gate-trial.md`.

---

## ADRs

- **ADR-1: the reader lives in the adapter; the meter takes `--reader <path>`.**
  - **Context:** R37 wants a neutral script, and R38 a per-adapter reader. Any reader under `scripts/` would name the adapter's format and break neutrality, or would need a new `ADAPTER_EXEMPT` entry.
  - **Decision:** The core loads a reader module from a path. ADAPTERS.md publishes the path per adapter.
  - **Consequences:** Adding an adapter means adding a reader file and an ADAPTERS row, with no core edit. A missing reader prints `unsupported` (R38).
- **ADR-2: the clock-event allow-list is `{user, assistant}`.**
  - **Context:** The coordinator's first measurement counted internal events, and idle came out at 35 min instead of 28 `[RELAYED: brief]`. Locally there are at least 6 timestamped internal types, and `api-request-blob` carries copies of tool blocks `[MEASURED, §J.3]`.
  - **Decision:** Allow-list in one constant. Count everything else and print the counts.
  - **Consequences:** A new internal type the adapter adds later is excluded by default and stays visible in the `excluded events:` line. A new *real* event type would be missed until it is added. The visible counts make that reviewable.
- **ADR-3: turns are distinct `message.id` values.**
  - **Context:** 501 lines against 170 responses `[MEASURED]`.
  - **Decision:** Count distinct ids.
  - **Consequences:** M14's turn counts are about 3x lower than a line count would give, and comparable before and after.
- **ADR-4: project values live in `scripts/verify.conf`; the opt-in is an explicit flag.**
  - **Context:** R24 calls any framework-script edit during the switch a defect. Today a project configures by editing the fill-in blocks of `verify-*.sh` `[MEASURED: verify-fast.sh:11-14, verify-full.sh:8-43]`. R12 says existing scripts and their output keep working.
  - **Decision:** An optional sourced conf that may override `LINT`, `TEST` and `STEPS`, with the in-script blocks as the fallback. Opted in means `VERIFY_HANDOFF_TIER=on`, because a project may adopt the conf only to move its STEPS out of the script.
  - **Consequences:** Framework upgrades become a file copy. Existing projects without a conf see no change in their verdict words.
- **ADR-5: counts come from JUnit XML plus a project collect command.**
  - **Context:** The framework is stack-agnostic. JUnit XML is the common report format across test runners `[INFERRED]`.
  - **Decision:** As in §AC.4.
  - **Consequences:** A runner that cannot emit JUnit leaves counts not configured, which keeps the honest `?` and NOT RUN for the merge gate.
- **ADR-6: the tree hash goes through a temporary index, taken before and after.**
  - **Context:** `HEAD^{tree}` misdescribes a dirty tree (R5) `[MEASURED, §AC.5]`.
  - **Decision and consequences:** A run is bound to the exact bytes it saw, and edits during the run invalidate it.
- **ADR-7: the template ships the selection wrapper, not a selector.**
  - **Context:** Choosing a selector is ba-sa's to design (PRD, Out of Scope). A neutral, stack-agnostic selector does not exist, and a language-specific import-graph walker would break the stack-agnostic template.
  - **Decision:** Projects plug in their test tool's own related-test or impact selection through `VERIFY_SELECT_CMD`. The wrapper enforces the PRD's guarantees around it.
  - **Consequences:** The pilot trial must choose and record a selector. Selector miss rate is measured only by the deferred periodic comparison (PRD, Nice-to-have).
- **ADR-8: unconfigured counts keep GREEN in the full tier, and the merge gate refuses.**
  - **Context:** R3 and R12 pull in opposite directions for projects that have not configured counts.
  - **Decision:** The full tier keeps its R12 meaning and prints an explicit `counts: not configured` line. The merge gate, the new tier whose GREEN carries the merge decision, refuses.
  - **Consequences:** No merge is ever GREEN without the count check, and no existing project's gate changes colour.
- **ADR-9: R26 has one head-position override, `ALLOW_POLL=1`, and covers Bash only.**
  - **Context:** `ALLOW_DESTRUCTIVE=1` is scoped to A1' by design (`guard_bash.py:226-240`). Legitimate retry loops with a sleep exist. The owner ruled on Q2 on 2026-10-20: "ใช้คำแนะนำของจาวิสทั้งสองข้อ".
  - **Decision:** A separate `ALLOW_POLL=1` override, accepted only as an env assignment at the head of the first segment, waiving R26 only. A substring anywhere else does not count (G-AC8).
  - **Consequences:** False positives have a visible escape. Every use is in the transcript, and the R37 meter still counts the loop's time as hand-written polling.
- **ADR-14: a declared filter allow-list settles R4 against R12.**
  - **Context:** The ban check covers configured step commands. A project's own legitimate marker split (for example `-m "not real_sleep"`) would exit 2 after upgrade without any edit of its own. The owner ruled on Q4 on 2026-10-20 (same words).
  - **Decision:** `VERIFY_ALLOWED_FILTERS` in `scripts/verify.conf`:
    - only `-m`, `-k` and `--deselect`;
    - each with a non-empty reason;
    - an exact value match;
    - configured commands only, never runtime arguments;
    - printed on every run and recorded.
    
    `--lf`, `--last-failed`, `-x`, `--exitfirst`, `--maxfail`, retries and cached-result flags can never be declared.
  - **Consequences:** Adopting the tiers stays config only (R24). No filter is ever silent. An undeclared or reasonless filter is refused before anything runs.
- **ADR-10: the merge gate runs in a fresh worktree, and the local fallback uses `nohup`.**
  - **Context:** D6 needs a run the agent did not edit. The agent's working tree may be dirty. `setsid` is absent `[MEASURED]`.
  - **Decision:** As in §D.
  - **Consequences:** Disk and time for a checkout. The local fallback stays labelled weaker.
- **ADR-11: document contracts are tests inside existing gate steps.**
  - **Context:** New STEPS lines would change the strings `tests/hooks/test_verify_scripts.py` and `tests/ci/test_ci_examples.py` pin with `count == 1` `[MEASURED]`.
  - **Decision:** New tests go under `tests/framework/` and `tests/hooks/`, which the gate already runs.
  - **Consequences:** No change to the pinned strings.
- **ADR-12: R21 ships in increment 8, as the backlog orders.**
  - **Context and consequences:** D's baseline outcome form arrives with E. This is flagged to the owner, not reordered.
- **ADR-13: a rework run is marked by a `REWORK:` line in the brief.**
  - **Context:** The baseline's 23% came from a heuristic over first prompts `[RELAYED: PRD; prior-art deep3.py used a regex]`, and the meter must not depend on prose matching for a tracked metric.
  - **Decision:** An explicit marker, written by the coordinator, and checked only for presence.
  - **Consequences:** Rework from before adoption reads as `unmarked`, so the M11 baseline stays the relayed figure.

## Approval history

- **2026-10-20 — approved (human).** Registry key `design-verify-tiers-merge-gate-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it. Dates and amendment
     history belong here, never on the canonical status line. -->

- **2026-10-20 — drafted.** ba-sa, alongside SPEC-verify-tiers-merge-gate.md.
- **2026-10-20 — revised (still In Review).** Owner ruling "ใช้คำแนะนำของจาวิสทั้งสองข้อ": ADR-9 now has the `ALLOW_POLL=1` override, and ADR-14 (the declared filter allow-list) is added.
