# SPEC: Amendment 1 — size classes in the meter (R41) and per-size trial acceptance (R22, R23)

Status: Approved
Approval: spec-verify-tiers-merge-gate-am1-size-class-2026-10-20
Owner: ba-sa
Upstream: doc/requirements/PRD-verify-tiers-merge-gate.md (re-approved by the owner 2026-10-20, registry key `prd-verify-tiers-merge-gate-2026-10-20`, after the M10 per-size amendment) · extends doc/specs/SPEC-verify-tiers-merge-gate.md (approved) and its doc/architecture/DESIGN-verify-tiers-merge-gate.md
Date: 2026-10-20

## Overview

The approved spec and design stay as they are. This file adds the following on top of them:

- **New increment J2, after J.** The R37 meter learns the size class of each engineer run: how many distinct files the run edited. It reports, per class, the active-time median and the run count, plus the overall mean and median (R41, M10, M10a). A run whose file count cannot be determined is reported as `size unknown` and is never placed in a class.
- **Amended trial criteria for increment F.**
  - Acceptance is judged per size class against Small ≤ 15, Medium ≤ 25 and Large ≤ 50 min.
  - A class with too few runs is `not enough runs (n)`: the trial is extended for that class, and the class never counts as met.
  - Probe runs are excluded from the measurement and counted.

**What this amendment overrides.** In the approved spec, F-AC2's M10 clause is superseded by F-AM1 and F-AM2 below. F-AC3 gains F-AM3. Nothing else in the approved spec or design changes.

**Markers.** These work as in the approved spec:
- `[MEASURED: <command>]`: I ran it on 2026-10-20.
- `[INFERRED]`: I read it, but did not run it.
- `[RELAYED: PRD]`: a figure from the PRD that I did not re-measure.

## Acceptance Criteria

### Increment J2 — size classes in the meter (R41). Delivered after J, and built on J's reader and categoriser.

**Size-class fixture.** `tests/framework/fixtures/agent_time/size_runs.json` holds neutral events. In the main run (`run-small`), the engineer edits 5 distinct files (a, b, c, d, e) through 8 edit calls, because a, b and c are each edited twice. The run also reads 6 other files (f to k), and reads a and b as well.

How each way of counting classifies `run-small`:

| How files are counted | Count | Class |
|---|---|---|
| Correct: distinct edited paths | 5 | small |
| Each edit call counted (re-edit mistake) | 8 | medium |
| Read-only files included (read mistake) | 11 | large |
| Both mistakes together | 14 | large |

`[INFERRED: arithmetic over the fixture as designed; the test is the measurement]`

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| J2-AC1 | R41 | Given `run-small`, When `agent_time.size_class(run)` runs, Then it returns `("small", 5)`. Given runs with 0, 1, 5, 6, 10 and 11 distinct edited files, Then the classes are investigate-only, small, small, medium, medium and large. The boundaries are inclusive, as R41 writes them. | tests/framework/test_agent_time.py |
| J2-AC2 | R41 **RED-FIRST** | **Planted mistake 1.** Given the test swaps the distinct-path counter for one that counts each edit call, Then J2-AC1 fails and the failure names `small → medium (8)`. **Planted mistake 2.** Given the test adds read-kind calls to the counted set, Then the failure names `small → large (11)`. For each mistake, the engineer pastes the red line, reverts, and shows green. | tests/framework/test_agent_time.py |
| J2-AC3 | R41 | Given a run with one edit-kind tool call whose path cannot be determined (missing or empty in the neutral event), Then that run is counted under `size unknown`, appears in no class's count or median, and is still included in the overall mean and median (M10a). | tests/framework/test_agent_time.py |
| J2-AC4 | R41 | Given a run whose transcript had at least one unreadable line, Then that run is `size unknown`, because an unreadable line may have been an edit. The output reports `size unknown: <k> (path missing: <a> · unreadable lines: <b>)`. | tests/framework/test_agent_time.py |
| J2-AC5 | R41, M10, M10a | Given 3 small runs (active 600 s, 900 s, 1200 s), 1 medium run, 0 large runs and 1 unknown run, When reported, Then:<br>• `small  n=3  median 15.0 min`<br>• `medium n=1  median …`<br>• `large  n=0  no median` (never `0.0`)<br>• `size unknown n=1`<br>• one overall line `all engineer runs n=5  mean … · median …` | tests/framework/test_agent_time.py |
| J2-AC6 | R22 (the meter's half), M10 | Given `--targets small=15,medium=25,large=50 --min-runs 3` and the J2-AC5 runs, Then:<br>• small: `met (median 15.0 ≤ 15)`<br>• medium: `not enough runs (1) — extend the trial for this class; not met`<br>• large: `not enough runs (0) — …; not met`<br>• investigate-only: `report only`<br>• the summary line: `acceptance: NOT met (met 1 of 3 classes)`<br>A class whose median is above its target says `NOT met (median x > target)`. The meter still exits 0, because it reports and never gates (R39). | tests/framework/test_agent_time.py |
| J2-AC7 | R23 | Given 2 of 6 engineer runs whose first inbound message has a line starting `PROBE:`, Then those 2 are excluded from every class, from the overall numbers and from the acceptance line, and the output shows `probe runs excluded: 2`. | tests/framework/test_agent_time.py |
| J2-AC8 | R39 | Given the canary `CANARY-7f3a` planted in an edited file path and in a read path, Then the canary appears nowhere in the meter's output. Paths are used for counting only. | tests/framework/test_agent_time.py |
| J2-AC9 | R41 (A: format), R38 | Given an adapter ก fixture in which `Edit` and `Write` carry `input.file_path`, `MultiEdit` carries `input.file_path`, `NotebookEdit` carries `input.notebook_path`, one `Edit` has no path, and one `Read` has a `file_path`, When read through `.claude/meter/transcript_reader.py`, Then the neutral edit events carry exactly those paths, the pathless `Edit` yields an empty path, and the `Read` contributes no edited path. Relative paths are normalised against the event's `cwd`. | tests/hooks/test_transcript_reader.py |
| J2-AC10 | R41 | `doc/framework/ADAPTERS.md` adds a "meter size class (R41)" row to each adapter: ก is supported (edited paths come from the edit tools' path fields); ข is unsupported. | tests/framework/test_doc_contracts.py |

### Increment F — trial amendments (R22, R23)

All of these are evidence in the trial report `doc/qa/QA-verify-tiers-merge-gate-trial.md`, as in the approved spec.

| # | Maps to | Given / When / Then | Evidence |
|---|---|---|---|
| F-AM1 | R22(a), M10 | This **supersedes the M10 clause of F-AC2.** Given the after-window of trial runs, When `python3 scripts/agent_time.py --reader … --dir … --since <trial start> --targets small=15,medium=25,large=50 --min-runs 3` runs, Then the change counts as accepted only if all three of small, medium and large say `met`. A class that says `not enough runs (n)` extends the trial for that class, and is never reported as met. Investigate-only is reported, not judged. | Trial report §Numbers: the meter output pasted in full |
| F-AM2 | R22(a), M10, M10a | The before numbers must come from the same instrument. The pilot's pre-trial engineer runs are re-measured with the J2 meter, using the same reader and flags. The trial report shows the per-class medians and run counts, `size unknown`, and the overall mean and median. Next to them it shows the PRD's relayed baseline (investigate 20 · small 20–22 · medium 35 · large 73 min; overall mean 51, median 38 `[RELAYED: PRD]`) and explains any difference. The PRD figures came from a throwaway script with its own counting rule `[INFERRED]`. | Trial report §Baseline |
| F-AM3 | R23 | Every probe dispatch carries a `PROBE:` line in its brief, and is excluded by the meter (J2-AC7). The trial report states the number excluded, and it must equal the number of probe dispatches in the trial log. A mismatch is a defect in the trial. | Trial report §Probes |
| F-AM4 | M10a | The overall mean and median are reported, and never judged. The earlier ≤ 37 min figure is shown as report-only. A split by task type (tier-0 bugfix against spec work) is reported by hand from the dispatch log, because the meter has no task-type marker (see Decisions). | Trial report §Numbers |

## Functional Behavior

**Size class of a run** = the number of distinct normalised paths that appear on edit-kind tool calls in that run.

| Rule | Detail |
|---|---|
| Edit-kind calls | Edit, Write, MultiEdit, NotebookEdit for adapter ก. |
| What does not count | Reads, searches, and shell commands. |
| Classes | 0 → investigate-only · 1–5 → small · 6–10 → medium · 11+ → large |
| Size unknown | Any edit-kind call without a determinable path, **or** any unreadable line in the run. A size-unknown run is never placed in a class. |
| Probe runs | Excluded from everything except the `probe runs excluded:` line. |
| Overall mean and median | Computed over all non-probe engineer runs, including size-unknown and investigate-only. "Engineer" means `ai-engineer` and `frontend-engineer`, reported separately per agent type, as J already does. |

**Shell-written files are a stated limit, not a class input.** A file changed by `sed -i`, a redirection or `git apply` is not counted. The meter prints `runs with shell file writes (not counted in size): <k>`, detected by pattern, so the size of this gap is visible. Whether such runs should instead be `size unknown` is owner question 1 below.

## Technical Design (additions to DESIGN §J)

**Neutral event** gains one field:

```python
paths: tuple[str, ...] = ()
```

- The field is set on `tool_call` events whose `tool_kind == "edit"`.
- It holds normalised absolute paths, used for counting only and never printed.
- An empty tuple on an edit call means the path is unknown.

**New core functions** in `scripts/agent_time.py`:

```python
SIZE_CLASSES = (("investigate-only", 0, 0), ("small", 1, 5), ("medium", 6, 10), ("large", 11, None))

def size_class(run: Run) -> tuple[str, int | None]     # ("size unknown", None) when undeterminable
def is_probe(run: Run) -> bool                          # first inbound text has a line matching ^PROBE:
def size_report(runs: list[Run], targets: dict[str, float] | None, min_runs: int) -> str
```

**New CLI flags:**
- `--targets small=15,medium=25,large=50` (minutes; optional);
- `--min-runs N` (default 3; see Decisions);
- `--include-probes` (off by default; for debugging only, and printed when used).

**Adapter ก reader changes.** For `tool_use` blocks named Edit, Write or MultiEdit, the reader takes `input.file_path`. For NotebookEdit it takes `input.notebook_path`. Relative paths are resolved against the line's `cwd` with `os.path.normpath`.

The input keys are:
- `Edit`: `file_path`, `new_string`, `old_string`, `replace_all`. 52 calls seen, all `[MEASURED]`.
- `Write`: `content`, `file_path`. 19 calls, all `[MEASURED]`.
- `MultiEdit` and `NotebookEdit` were not seen in local transcripts, so their keys are `[INFERRED]`; the engineer checks them against the tool schema.

`[MEASURED: python3 heredoc over this repo's own transcripts, printing tool names and sorted input-key tuples only]`.

**Coordinator brief template** (`.agents/skills/coordinator-discipline/SKILL.md`) gains an optional line: `PROBE: <probe name> (trial probe; excluded from the meter)`.

## Decisions (ADR-style)

- **AM1-ADR-1: the minimum run count per class is 3 (`--min-runs 3`).**
  - **Context:** The PRD says a class with "too few trial runs to compute a median" is "not enough runs (n)", but names no number. One run has a median, but a one-run median is just that run.
  - **Decision:** The default is 3, and the flag lets the owner change it.
  - **Consequences:** With at least 3 features in the trial (R22) spread over classes, at least one class will probably report `not enough runs` and need extending `[INFERRED]`. This is owner question 2.
- **AM1-ADR-2: an unreadable line makes the run `size unknown`.**
  - **Context:** R41 says a count that "cannot be determined" is never classed. An unreadable line may have hidden an edit.
  - **Decision:** Conservative: such a run is size unknown.
  - **Consequences:** The size-unknown count is visible, so a reader that degrades shows up as a rising unknown count instead of shrinking classes.
- **AM1-ADR-3: probe runs are marked with a `PROBE:` line, the same mechanism as `REWORK:` (approved ADR-13).**
  - **Context:** R23 requires probe runs to be excluded and counted. The meter must not match prose.
  - **Decision and consequences:** An explicit marker. A probe dispatched without the marker would be counted. F-AM3's equality check against the trial log catches that.
- **AM1-ADR-4: there is no task-type marker in this amendment.**
  - **Context:** M10a's "by type" split (bugfix against spec work) is report-only, and R41 does not ask for it.
  - **Decision:** It is reported by hand in the trial (F-AM4).
  - **Consequences:** No new marker. If the owner wants it mechanised, it is a later PRD.

## Affected tests / affected files

**How this list was built:**
- I read the approved spec's impact rows 1–4 and its J-AC table.
- `grep -n 'M10\|R41\|R22\|R23\|size class\|probe' doc/requirements/PRD-verify-tiers-merge-gate.md`.
- `ls .claude/meter` returned no such directory `[MEASURED]`. Increment J is still being implemented, so J's files do not exist on disk yet, and J2 edits them after J lands.

| File | Change | Whose behaviour changes | Opt-in only? |
|---|---|---|---|
| `scripts/agent_time.py` (created by J) | `paths` field, `size_class`, `is_probe`, `size_report`, and the new flags | Coordinator and owner: per-size output and the acceptance line. It still never gates. | No (report only) |
| `.claude/meter/transcript_reader.py` (created by J) | Extracts edited paths and their `cwd` | None | No |
| `tests/framework/test_agent_time.py` (created by J) | Adds J2-AC1 to J2-AC8 | — | — |
| `tests/framework/fixtures/agent_time/size_runs.json` **(new)** | The size fixture, with the canary paths | — | — |
| `tests/hooks/test_transcript_reader.py` and `tests/hooks/fixtures/transcripts/` (created by J) | J2-AC9: edit and read path extraction | — | — |
| `tests/framework/test_doc_contracts.py` (created by later increments; if it does not exist yet, J2 creates it with only J2-AC10) | The ADAPTERS size-class row | — | — |
| `doc/framework/ADAPTERS.md` | One row per adapter: "meter size class (R41)" | None | — |
| `.agents/skills/coordinator-discipline/SKILL.md` | The optional `PROBE:` brief line | Coordinator: probe dispatches carry the marker | No |

**Existing tests that must keep passing:**
- All J tests. J-AC1's golden totals do not change, because size class is a separate output.
- J-AC7's golden run contains one malformed line, so under AM1-ADR-2 it becomes `size unknown`. That is consistent, and J-AC7 asserts nothing about size `[INFERRED from the approved J-AC7 wording]`.
- `tests/framework/test_neutrality.py`: the new core code must name no provider.
- `tests/framework/test_bootstrapped_project.py`: the new fixture must not use `<…>` placeholders.

**Not touched:**
- the approved SPEC and DESIGN;
- every verify script;
- the guard;
- the templates.

## Traceability

R41 → J2-AC1, J2-AC2, J2-AC3, J2-AC4, J2-AC5, J2-AC9, J2-AC10 · R22 (per-size acceptance, "not enough runs") → J2-AC6, F-AM1, F-AM2 · R23 (probe exclusion) → J2-AC7, F-AM3 · R39 (no identifiers, applied to paths) → J2-AC8 · M10 → J2-AC5, J2-AC6, F-AM1 · M10a → J2-AC3, J2-AC5, F-AM2, F-AM4.

The amended items map to 14 acceptance criteria: J2 has 10, and F has 4.

## Open questions for the owner (none block approval)

1. Should runs that write files through the shell (`sed -i`, redirection, `git apply`) be `size unknown` instead of counted by their edit-tool files only? As written, they are counted and flagged with a visible count. Making them unknown is stricter, but could empty the classes `[INFERRED; the before-measurement in F-AM2 shows how many runs are affected]`.
2. Minimum runs per class for a median: 3 (AM1-ADR-1)?

## Approval history

- **2026-10-20 — approved (human).** Registry key `spec-verify-tiers-merge-gate-am1-size-class-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** ba-sa, from the re-approved PRD (M10 per size class, M10a, R22 acceptance, R23 probe exclusion, R41). Written as a separate amendment so that the approved spec and design, which increment J is being built against, stay unchanged.
