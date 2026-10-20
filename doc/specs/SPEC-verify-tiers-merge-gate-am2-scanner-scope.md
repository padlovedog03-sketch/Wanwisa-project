# SPEC: Amendment 2 — the ban scanner covers pytest only, and says what it does not scan (increment A+C)

Status: Approved
Approval: spec-verify-tiers-merge-gate-am2-scanner-scope-2026-10-20
Owner: ba-sa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md (approved, registry key `spec-verify-tiers-merge-gate-2026-10-20`) and its doc/architecture/DESIGN-verify-tiers-merge-gate.md · owner ruling of 2026-10-20 recorded in doc/memory/ease-of-use-over-strictness.md (commit 5e7c96f), verbatim: "เอาตามที่แนะนำเลยให้ใช้งานง่าย"
Date: 2026-10-20

## Overview

The approved spec and design stay as they are. This file changes how increment A+C's ban check is scoped. It applies the owner's ease-of-use ruling: a guard catches accidents and casual mistakes, and the routes it does not cover are written down as declared limits instead of chased one by one.

- **Built-in bans apply to the pytest family only.** They are matched in pytest's own argv, found in command position.
- **Every other runner is named, never guessed.** A step that runs another runner, or a `VERIFY_TEST_STEPS` step that runs no pytest, prints one `limit:` line. The line is kept in `record.warnings`, and the verdict does not change.
- **Projects declare their own runner's bans** in `VERIFY_EXTRA_BANNED`.
- **The coordinator's rulings on QA rounds 1 and re-test 1** (D3, D7, D8, D9, D11, D12 to D18) are recorded here as accepted, so the approved wording no longer contradicts the code.

The implementation already follows this amendment. It is on branch `worktree-agent-ad1e27705199bd4e4` at `e436d1f` (commits `94e6646`, `21b0a7b`, `e436d1f`).

**What this amendment overrides.**
- AC-AC8 and AC-AC19 are replaced by the wording below.
- AC-AC5 and AC-AC6 gain clauses.
- Design §AC.3 (the ban list) and the `ALLOWLISTABLE` set in ADR-14 are superseded by §"Ban table" below.
- The prune rule in design §AC.2 ("the 20 newest directories") is superseded by AM2-R5.
- The `local:<hostname>` form of `runner.id` in design §AC.1 is superseded by AM2-R4.

Nothing else in the approved spec or design changes.

**Markers.**
- `[MEASURED: <command>]`: I ran it on 2026-10-20, in the worktree of branch `worktree-agent-ad1e27705199bd4e4` at `e436d1f`, unless another place is named. Every test name cited as MEASURED was in a run of `python3 -m pytest tests/hooks/test_verify_tiers.py -q -p no:cacheprovider` that gave `221 passed in 32.06s`.
- `[INFERRED]`: I read it, but did not run it.

## Acceptance criteria — changed wording

Each row gives the approved wording, the new wording and the reason. All of these live in `tests/hooks/test_verify_tiers.py`.

### AC-AC8 (R4): replaced

**Old (approved):**

> For each banned form in the design's ban list (§AC.3), placed either in a configured command or in `verify-fast.sh`'s arguments: Given the form is present, When either tier starts, Then it exits 2 with `BANNED: <token> — <reason>` before any step runs. Given `python3 -m pytest` (the `-m` belongs to the interpreter), Then it is not refused. The only other exception is a marker or deselect filter declared in `VERIFY_ALLOWED_FILTERS` (AC-AC16 to AC-AC19).

**New:**

> **AC-AC8a: pytest-family argv.** For each banned form in this amendment's ban table, Given it appears in the argv of a pytest-family runner in any configured step, in `VERIFY_COLLECT_CMD`, in `PYTEST_ADDOPTS` (set in a command or in the environment), or among `verify-fast.sh`'s arguments, When either tier starts, Then the tier exits 2 with `BANNED: <token> — <reason>` before any step runs.
>
> A pytest-family runner is found in command position. That means after leading `NAME=value` assignments, after the shell words `!`, `{`, `if`, `then`, `elif`, `else`, `while`, `until`, `do` and `time [-p]`, and after the wrappers `env`, `uv run`, `coverage run` and `python[N] -m` / `-mX`. The recognised spellings are `pytest`, `py.test` (by basename, so `.venv/bin/pytest` counts), `python3 -m pytest`, `python3 -mpytest`, `coverage run -m pytest` and `uv run pytest`.
>
> Clustered and attached short options count as their parts: `-xq` holds `-x`, `-qk smoke` holds `-k`, and `-mslow` and `-m"not slow"` are `-m`. A value-taking short option ends the cluster (`c n o p r W`), so `-rxXs` and `-p no:x` are not `-x`.
>
> **AC-AC8b: other programs are not scanned for built-in bans.** Given a word appears outside a pytest-family argv, Then it is not refused by a built-in ban. The cases are `git commit -m x`, `tar -x`, `sort -k 2`, `go test -timeout 5m ./...`, `make -C tools/pytest -k`, `echo pytest -x` and `python3 -m pytest` (whose `-m` belongs to the interpreter).
>
> **AC-AC8c: the honest limit.** Given a step's command runs a runner listed in `VERIFY_TEST_RUNNERS` that is not the pytest family, Then exactly one unindented line is printed for that step: `limit: step <label> runs <runner>; its flags are not scanned — declare bans in VERIFY_EXTRA_BANNED`. Given a step listed in `VERIFY_TEST_STEPS` runs no pytest-family runner and no listed runner, Then the same line is printed with `no known runner` as the runner. In both cases, Then the line is also written to the run's `record.warnings`, and the verdict and exit code are unchanged.
>
> **AC-AC8d: project bans.** Given `VERIFY_EXTRA_BANNED` holds a token, Then that token, or `<token>=<value>`, is refused in every program of every step and among `verify-fast.sh`'s arguments, with `BANNED: <token> — project-declared`.
>
> The only exception to AC-AC8a is a filter declared in `VERIFY_ALLOWED_FILTERS` (AC-AC16 to AC-AC19).

**Reason.**
- The approved wording scanned every program in a step for whole tokens. It refused ordinary commands in projects with no conf: `go test -timeout 5m` was refused with `BANNED: -timeout`, `coverage run -m pytest` was refused, and `make -C tools/jest -k` was refused (QA D6, D12, D15). That broke R12, the promise that a project as filled in today stays GREEN.
- The coordinator narrowed the bans to pytest-family argv (rulings D12 to D18). The owner's ease-of-use ruling confirms that direction. The gate does not guess other runners' flags; it names them instead.

**Tests (all present on the branch) `[MEASURED: the 221-pass run above]`:**

| Clause | Tests |
|---|---|
| AC-AC8a | `test_ac8_a_banned_form_in_a_configured_full_step_is_refused_before_any_step_runs`, `test_ac8_a_banned_form_in_the_fast_tier_config_is_refused`, `test_ac8_a_banned_form_passed_to_the_fast_tier_is_refused`, `test_rt1_the_pytest_family_is_found_behind_every_wrapper`, `test_rt1_lf_ff_sw_and_reruns_variants_are_refused`, `test_rt1_shell_grammar_before_pytest_is_not_the_program`, `test_rt1_listing_a_wrapper_as_a_runner_cannot_hide_pytest`, `test_d7_a_ban_hidden_in_a_cluster_an_attached_value_or_an_env_var_is_refused`, `test_d7_a_ban_in_the_environment_at_run_time_is_refused`, `test_d7_the_collect_command_is_scanned_too` |
| AC-AC8b | `test_ac8_the_interpreter_m_flag_is_not_refused`, `test_rt1_only_a_pytest_runner_in_command_position_is_scanned`, `test_d6_a_flag_outside_a_test_runner_is_not_refused`, `test_d6_a_project_as_filled_in_today_with_realistic_commands_stays_green`, `test_ac8_the_shipped_default_steps_pass_the_ban_check` |
| AC-AC8c | `test_rt1_a_test_step_with_no_pytest_runner_states_the_limit`, `test_rt1_a_listed_runner_is_named_and_its_bans_come_from_extra_banned`, `test_rt1_one_limit_line_per_step_and_none_for_a_scanned_step`, `test_rt1_the_full_gate_records_the_limit_and_keeps_its_verdict`, `test_rt1_the_full_gate_names_a_listed_runner`, `test_rt1_a_project_with_no_conf_prints_no_limit_line`, `test_rt1_the_fast_tier_names_a_listed_runner_but_never_no_known_runner`, `test_d7_eval_and_bash_c_are_a_stated_limit_not_a_silent_pass` |
| AC-AC8d | `test_ac8_a_project_can_add_a_banned_token`, `test_rt1_extra_banned_refuses_in_an_unscanned_test_step` |

**Hostile inputs these clauses cover** (rule: doc/memory/hostile-inputs-in-every-ac.md):
- prefixes and wrappers: `env`, `uv run`, `coverage run`, `python3 -mpytest`, and shell reserved words;
- odd shapes: clusters, attached values, `=` forms, redirections between flags (`pytest >log -x`), and unbalanced quotes. `[MEASURED: check-banned --cmd=…]`: `pytest >log -x` and `pytest 'unbalanced -x` each exit 2 with `BANNED: -x`. `pytest "-x` (an unbalanced double quote glued to the flag) exits 0. That is harmless, because bash refuses the same line as a syntax error, so the step fails RED `[INFERRED; not run as a step]`;
- path and quoting variants: `.venv/bin/pytest`, `./pytest`, `\pytest`, `'pytest'`;
- look-alikes that must not be refused: `tools/pytest` as a path argument, `echo pytest -x`.

Probe `[MEASURED: python3 scripts/verify_record.py check-banned --test-steps=tests "--step=tests|<cmd>"]`:
- `./pytest -x`, `\pytest -x`, `'pytest' -x`, `python3 -m pytest -x`, `uv run pytest -x`, `coverage run -m pytest -x`, `python3 -mpytest -x` and `py.test -x` each exit 2 with `BANNED: -x — hides the other failures`.

### AC-AC19 (R4): amended

**Old (approved):**

> Given an allow-list entry for `--lf`, `--last-failed`, `-x`, `--exitfirst`, `--maxfail…`, a retry flag or a cached-result flag, even with a reason, Then the run exits 2 with `BANNED: <token> can never be allow-listed`. Only marker and deselect filters (`-m`, `-k`, `--deselect`) can be declared. Given an allow-listed filter passed as a *runtime* argument to `verify-fast.sh` (not in a configured command), Then it is still refused: the allow-list covers the project's own step commands only.

**New:**

> Given an allow-list entry for any hard ban in this amendment's ban table, even with a reason, Then the run exits 2 with `BANNED: <token> can never be allow-listed`. The hard bans include `--lf`, `--last-failed`, `--ff`, `--failed-first`, `-x`, `--exitfirst`, `--maxfail…`, `--bail…`, `--sw`, `--stepwise…`, the retry flags and the cached-result flags. Only `-m`, `-k`, `--deselect`, `--ignore` and `--ignore-glob` can be declared, each with a reason. Any other entry exits 2 with `BANNED: <entry> — only -m, -k, --deselect, --ignore and --ignore-glob can be declared`. Given an allow-listed filter passed as a *runtime* argument to `verify-fast.sh`, Then it is still refused: the allow-list covers the project's own step commands only.

**Reason.**
- `--ignore` and `--ignore-glob` are filters of the same kind as `--deselect`. A project may need one, and QA D7 showed that, undeclared, they were a silent bypass. Making them declarable with a reason puts them on the printed list.
- `--ff`, `--failed-first`, `--sw` and `--stepwise` order or stop a run by the last run's failures. They were missing from design §AC.3, and they join the never-declarable set.

Tests: `test_ac19_a_hard_ban_can_never_be_allow_listed`, `test_ac19_only_marker_and_deselect_filters_can_be_declared`, `test_ac19_an_allow_listed_filter_passed_at_runtime_is_still_refused`, `test_d7_ignore_can_be_declared_with_a_reason` `[MEASURED: the 221-pass run]`.

Probe `[MEASURED: check-banned --allow=<entry>]`:
- `--ignore=tests/slow|nightly` → exit 0, and prints `declared filter: --ignore=tests/slow — nightly`.
- `--ignore=tests/slow` with no reason → exit 2, `BANNED: allow-list entry without a reason: --ignore=tests/slow`.
- `--ff|x`, `--reruns 2|x`, `-x|x`, `--sw|x` and `--lf|x` each exit 2 with `BANNED: <token> can never be allow-listed`.

### AC-AC5 (R2): one clause added

**Old (approved):** unchanged, kept in full.

**Added clause:**

> Given two entries in `STEPS` share a label that is listed in `VERIFY_TEST_STEPS`, When `verify-full.sh` starts, Then it prints `EXIT GATE RED — duplicate test step label: <label>; give each test step its own label` and exits 1 before any step runs.

**Reason.** QA D3: two steps with one label shared one JUnit directory and were counted twice. With 3 cases run and collected 6, the gate printed `reported 6 of 6 collected` and `EXIT GATE GREEN`. The coordinator accepted RED with exit 1 (accepted deviation 1).

Tests: `test_d3_two_test_steps_with_one_label_are_refused_before_any_step_runs`, plus QA pin `test_regression_two_steps_sharing_a_test_label_are_not_double_counted` `[MEASURED: both runs, 221 and 18 tests]`.

### AC-AC6 (R1): two clauses made exact

**Old (approved):**

> … Given counts are not configured, Then the last line is `FAST VERIFY OK — partial run: ran ? of ? (counts not configured)`.

**New:** the approved clauses stay, and these are added.

> Given no `VERIFY_COLLECT_CMD` but a TEST that writes JUnit with 3 cases, Then the last line is `FAST VERIFY OK — partial run: ran 3 of ? (counts not configured)`.
>
> Given `VERIFY_COLLECT_CMD` exits non-zero (n), Then the last line is `FAST VERIFY OK — partial run: ran 3 of ? — collect failed (exit n)`. In the full tier, the same failure is RED with `VERIFY_COLLECT_CMD failed (exit n)`.

**Reason.**
- QA D9: the approved AC said `ran ? of ?`, while the Functional Behavior table said `ran N of ?`.
- A failing collect command used to end `(counts not configured)`, which is untrue: the counts were configured, and they broke.

Tests: `test_d9_a_failing_collect_in_the_fast_tier_says_so`, `test_d9_without_a_collect_command_the_fast_tier_says_ran_n_of_unknown`, `test_a_collect_command_that_fails_is_red` `[MEASURED: the 221-pass run; strings read from those tests' assertions at lines 300, 1020 and 1030]`.

### New criteria

| # | Maps to | Given / When / Then | Test |
|---|---|---|---|
| AC-AC20 | R4, R12 (D2, D18) | Given `scripts/verify.conf` has a syntax error on any line, When `verify-full.sh` starts, Then it prints `EXIT GATE RED — scripts/verify.conf failed to load (syntax error); no step was run` and exits 1. When `verify-fast.sh` starts, Then it prints `FAST VERIFY REFUSED — scripts/verify.conf failed to load (syntax error)` and exits 2. The check is `bash -n`. Given the conf's last line returns non-zero (`[ -n "$X" ] && VAR=…`), Then the conf loads, and no `failed to load` line is printed. | `test_d2_the_fast_tier_refuses_a_conf_that_fails_to_load`, `test_rt1_a_fast_conf_whose_last_test_is_false_still_loads`, QA pins `test_regression_a_conf_that_stops_parsing_cannot_drop_the_test_step_check`, `test_regression_a_conf_whose_last_test_is_false_still_loads` `[MEASURED]` |
| AC-AC21 | R10, §8 personal data (D8) | Given `VERIFY_RUNNER_ID` is unset, Then `record.runner.id` is `local:` followed by the first 12 hex characters of sha256(hostname), and the hostname appears nowhere in the record. Given it is set, Then the id is that value. | `test_d8_the_local_runner_id_never_carries_the_hostname`, `test_the_runner_id_comes_from_the_environment_when_set` `[MEASURED]` |
| AC-AC22 | R5 (D11) | Given 25 full-run directories and 1 older `-fast` directory, When one more full run finishes, Then 20 full directories remain and the fast one is kept. Given 25 fast runs, Then the newest full record is kept. Fast and full runs each keep their own 20 slots. | `test_d11_fast_runs_never_evict_a_full_record` `[MEASURED]`. The reverse direction was probed by QA and is not pinned yet (see Affected tests). |
| AC-AC23 | R5 (tree identity) | Given a tracked file is edited during a configured run so that its size and mtime are unchanged, Then the tree hash differs from the committed tree, and the gate is RED with `tree changed during the run`. | `test_rt1_a_same_size_edit_with_an_unchanged_mtime_is_hashed_by_content` `[MEASURED]` |
| AC-AC24 | R4 **RED-FIRST** (AM2-ADR-3) | Given a configured step `pytest --force-flaky`, `pytest --max-runs 3`, `pytest --max-runs=3`, `python3 -m pytest -q --force-flaky`, or `PYTEST_ADDOPTS=--max-runs=2 pytest`, or `--force-flaky` passed to `verify-fast.sh`, When either tier starts, Then it exits 2 with `BANNED: <token> — retries turn a failure into a pass` before any step runs. Given `VERIFY_ALLOWED_FILTERS=('--force-flaky\|flaky suite')`, Then it exits 2 with `BANNED: --force-flaky can never be allow-listed`. Given `pytest --flake-runs 3` alone, Then it is not refused (L7). **Red-first:** each refused case is shown exit 0 against `e436d1f` first `[MEASURED: check-banned on e436d1f gives exit 0 for --force-flaky and --max-runs 3]`, then green after the change. | tests/hooks/test_verify_tiers.py |

**AC-AC1's wording is unchanged.** It requires `runner.id` and does not fix its form. AC-AC21 adds the form.

## Ban table (supersedes design §AC.3 and ADR-14's `ALLOWLISTABLE`)

This table is matched in pytest-family argv only (AC-AC8a). The code that implements it is `HARD_BANS`, `PREFIX_BANS` and `FILTER_REASONS` in `scripts/verify_record.py`, branch `worktree-agent-ad1e27705199bd4e4` `[MEASURED: git show <branch>:scripts/verify_record.py, lines 52-92]`.

| Token(s) | Kind | Reason printed |
|---|---|---|
| `--lf*`, `--last-failed*` (prefix) | hard | selects nothing after a green run |
| `--ff*`, `--failed-first*` (prefix) | hard | orders the run by the last run's failures |
| `-x` (also inside a cluster), `--exitfirst`, `--maxfail[=n]`, `--bail[=n]` | hard | hides the other failures |
| `--sw*`, `--stepwise*` (prefix; so `--sw-skip`, `--sw-reset` too) | hard | hides the other failures |
| `--reruns*` (prefix), `--retries`, `--retry`, `--flake-finder`, `--force-flaky`, `--max-runs`, `--max-runs=*` | hard | retries turn a failure into a pass |
| `--cache_test_results*`, `--cache-test-results*` (prefix) | hard | a cached result reported as a fresh run |
| `-k`, `-m` (except the interpreter's `-m`), `--deselect`, `--ignore`, `--ignore-glob` | declarable filter | `undeclared filter; declare it with a reason in VERIFY_ALLOWED_FILTERS` (configured), or the filter's own reason (runtime) |
| anything in `VERIFY_EXTRA_BANNED` | project | `project-declared` (matched in every program) |

`--cache-clear` is allowed, because it makes a run fresher, not staler.

## Declared limits

These routes are not refused by the ban check. Each was chosen under the owner's ruling and is stated, not chased. The "Behaviour" column says what the gate actually does, as measured.

Probe: `[MEASURED: python3 scripts/verify_record.py check-banned --test-steps=tests "--step=tests|<cmd>"`, and the same with `--step=lint|…` and with `--runtime=…`, branch at `e436d1f`]`.

| # | Limit | Example | Behaviour | What catches it afterwards |
|---|---|---|---|---|
| L1 | Unlisted wrappers before pytest | `timeout 600 pytest -x`, `nice pytest -x`, `poetry run pytest -x`, `exec pytest -x`, `command pytest -x`, `xargs pytest -x` | In a `VERIFY_TEST_STEPS` step: exit 0 with `limit: step tests runs no known runner; …`. In any other step: exit 0, silent. | The count check, when counts are configured: `-x` stopping early gives `reported N of M collected` → RED `[INFERRED from AC-AC3's rule; not run with these wrappers]` |
| L2 | Wrapper options that take values | `uv run --with foo pytest -x`, `coverage run --rcfile x -m pytest -x`, `env -S 'pytest -x'` | As L1 | As L1 |
| L3 | Unknown interpreters | `pypy3 -m pytest -x`, `py -m pytest -x` | As L1 | As L1 |
| L4 | Name tricks | `pytest3 -x`, or a renamed copy or alias of pytest | As L1 | As L1 |
| L5 | Flags in a variable or a command substitution | `pytest $FLAGS`, `pytest $(echo -x)` | Exit 0 and **silent, even in a test step**, because pytest itself was found and scanned. | Filtering and stopping forms: the count check, as L1. Retries through a banned flag never get this far (AC-AC24); a retry flag hidden in `$FLAGS`: nothing. |
| L6 | Runtime arguments to `verify-fast.sh` are scanned with pytest's table, whatever the project's runner | `verify-fast.sh src -b`, `--onlyFailures`, `-t name` all exit 0. `verify-fast.sh src -x` exits 2 for every runner. | Silent for other runners' flags | The fast tier claims a partial run only (`ran N of M`), never GREEN. The full gate re-runs everything. |
| L7 | `--flake-runs` | `pytest --flake-runs 3` | Exit 0, silent | It only takes effect together with `--flake-finder`, which is a hard ban, so on its own it repeats nothing `[INFERRED from the plugin's documented flags; not installed or run here]`. `--force-flaky` and `--max-runs` are hard bans since AM2-ADR-3 (AC-AC24). |
| L8 | `eval` and a shell's `-c` string | `eval "pytest --lf"`, `bash -c "pytest -x"` | Exit 0 with `limit: flags inside eval or a shell's -c string are not scanned: …` | As L1 |

**Text for the spec and for `scripts/verify.conf.example`.** The example conf on the branch already carries this text under `LIMIT:`. The engineer extends it with L3, L4, L6 and L7, so that one place in the project lists all eight.

**Text for `doc/framework/ADAPTERS.md`.** This is a new section, added after the adapter tables. It is written in Thai to match the file.

```markdown
## ประตูตรวจ (verify tiers) — ข้อจำกัดที่ประกาศไว้

ด่านห้ามธง (`scripts/verify_record.py check-banned`) อ่านเฉพาะอาร์กิวเมนต์ของ pytest ที่อยู่ตำแหน่งคำสั่ง
(หลัง `env`, `uv run`, `coverage run`, `python -m`) ตัวรันเทสต์อื่นไม่ถูกเดาธง แต่ถูก*ประกาศชื่อ*ในบรรทัด
`limit:` และโปรเจกต์ห้ามธงของตัวเองได้ใน `VERIFY_EXTRA_BANNED` ข้อนี้เหมือนกันทุกตัวเชื่อม เพราะด่านเป็นสคริปต์ชั้นแก่น

ที่ด่านนี้มองไม่เห็น (ไม่ไล่ปิดทีละทาง ตามมติเจ้าของงาน 2026-10-20):
- ตัวห่ออื่นหน้า pytest (`timeout`, `nice`, `poetry run`, `exec`, `command`, `xargs`) และตัวเลือกของตัวห่อที่รับค่า
  → ในขั้นที่อยู่ใน `VERIFY_TEST_STEPS` มีบรรทัด `limit:` ขั้นอื่นเงียบ
- ตัวแปลภาษาที่ไม่รู้จัก (`pypy3`, `py`) และการเปลี่ยนชื่อ pytest → เหมือนข้อบน
- ธงในตัวแปรหรือ `$(…)` → เงียบ
- อาร์กิวเมนต์ที่พิมพ์ให้ `verify-fast.sh` ตรวจด้วยตารางของ pytest เสมอ → ธงของตัวรันอื่นผ่านเงียบ
- `--flake-runs` → เงียบ แต่ไม่มีผลถ้าไม่มี `--flake-finder` ซึ่งถูกห้ามอยู่แล้ว (ส่วน `--force-flaky`, `--max-runs` ถูกห้ามเสมอ เพราะการรันซ้ำทำให้เทสต์ที่พังกลายเป็นผ่าน และการนับจำนวนจับไม่ได้)
- `eval` และ `bash -c "…"` → มีบรรทัด `limit:`

ตัวจับย้อนหลัง: เมื่อตั้ง `VERIFY_COLLECT_CMD` กับ `VERIFY_TEST_STEPS` แล้ว การกรองหรือหยุดกลางทางทำให้จำนวนที่รันไม่เท่าจำนวนที่เก็บได้ → RED
ยกเว้นการรันซ้ำ ซึ่งจำนวนยังเท่าเดิม
```

## Accepted rulings, recorded

| # | Ruling | Where it now lives | Evidence |
|---|---|---|---|
| AM2-R1 | D3: a duplicate `VERIFY_TEST_STEPS` label → RED, exit 1, before any step runs | AC-AC5 added clause | `test_d3_…` `[MEASURED]` |
| AM2-R2 | `--ignore` and `--ignore-glob` are declarable with a reason | AC-AC19 | `test_d7_ignore_can_be_declared_with_a_reason` and the `--allow` probe `[MEASURED]` |
| AM2-R3 | `--ff`, `--sw`, `--reruns`, `--lf` and `-x` (and their family) can never be declared | AC-AC19, Ban table | `test_ac19_a_hard_ban_can_never_be_allow_listed` and the `--allow` probe `[MEASURED]` |
| AM2-R4 | `runner.id` is `local:<12 hex of sha256(hostname)>` (AGENTS.md §8) | AC-AC21 | `test_d8_…` `[MEASURED]` |
| AM2-R5 | Fast and full runs are pruned separately, 20 each | AC-AC22 | `test_d11_…` `[MEASURED]` |
| AM2-R6 | A failing collect command is reported as `collect failed (exit n)` (fast), and RED with `VERIFY_COLLECT_CMD failed (exit n)` (full) | AC-AC6 | `test_d9_…`, `test_a_collect_command_that_fails_is_red` `[MEASURED]` |
| AM2-R7 | The conf is checked with `bash -n` before it is sourced | AC-AC20 | `test_d2_…`, `test_rt1_a_fast_conf_whose_last_test_is_false_still_loads` `[MEASURED]` |
| AM2-R8 | The racy tree hash is fixed: the throwaway index copy gets mtime 1, so git re-reads every file's content | AC-AC23 | `test_rt1_a_same_size_edit_with_an_unchanged_mtime_is_hashed_by_content` `[MEASURED]`. The commit message of `21b0a7b` reports 3 failures in 24 runs before the fix and 0 in 24 after `[RELAYED: commit 21b0a7b; I did not re-run 24 times]` |

## QA regression pins

Two pins are retired. The QA file is `tests/hooks/test_regression_verify_tiers_qa.py`. On the branch it gives `2 failed, 16 passed`, and both failures are these two pins `[MEASURED: python3 -m pytest tests/hooks/test_regression_verify_tiers_qa.py -q -p no:cacheprovider]`.

| Pin | Action | Replaced by |
|---|---|---|
| `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[bazel test //... --cache_test_results=yes---cache_test_results=yes]` | Retire | `test_rt1_a_test_step_with_no_pytest_runner_states_the_limit[bazel …]` and `test_rt1_a_listed_runner_is_named_and_its_bans_come_from_extra_banned[bazel test-…]` |
| `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to[cargo nextest run --retries 2---retries]` | Retire | `test_rt1_a_test_step_with_no_pytest_runner_states_the_limit[cargo …]` and `test_rt1_a_listed_runner_is_named_and_its_bans_come_from_extra_banned[cargo nextest-…]` |

The function has exactly these two parameters `[MEASURED: grep -n -A3 'parametrize' at lines 200-204 of that file]`, so the whole function `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to` is deleted. Its docstring's claim that a non-pytest tool's flag is refused is now false by design. The QA report's re-test 1 note for D14 should point to this amendment.

The other 16 pins stay unchanged and green.

## Affected tests / affected files

**How this list was built:**
- `git diff --stat 9a97bc6..worktree-agent-ad1e27705199bd4e4` over `scripts/`, `tests/` and `doc/` (9a97bc6 is the merge base with this branch).
- `git show --stat` of `94e6646`, `21b0a7b` and `e436d1f`.
- `grep -n "^def test_"` over `tests/hooks/test_verify_tiers.py` and `tests/hooks/test_regression_verify_tiers_qa.py` on the branch.
- `git diff 9a97bc6 worktree-agent-ad1e27705199bd4e4 --stat -- doc/framework/ADAPTERS.md` → no change `[MEASURED]`.

One owner per file:

| File | Owner (increment) | Change | Whose behaviour changes |
|---|---|---|---|
| `scripts/verify_record.py` | A+C rework, ai-engineer | Add `--force-flaky` and `--max-runs` to `HARD_BANS` (and `--max-runs` as a `=` form) with the reason `retries turn a failure into a pass` (AC-AC24, AM2-ADR-3). Everything else already follows this amendment `[MEASURED: 221 passed]`. | Projects whose step uses those flags: refused (exit 2) |
| `scripts/verify-full.sh`, `scripts/verify-fast.sh` | A+C rework, ai-engineer | None | — |
| `scripts/verify.conf.example` | A+C rework, ai-engineer | Extend the `LIMIT:` text with L3, L4, L6 and L7 | Project authors |
| `tests/hooks/test_verify_tiers.py` | A+C rework, ai-engineer | AC-AC24 cases (red-first). Optional: pin the reverse direction of AC-AC22 (QA's probe: 25 full plus 1 older fast) | — |
| `tests/hooks/test_regression_verify_tiers_qa.py` | qa | Delete `test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to` (2 parameters) | — |
| `doc/qa/QA-verify-tiers-AC.md` | qa | A re-test note: D14 is retired by this amendment, not fixed | — |
| `doc/framework/ADAPTERS.md` | A+C rework, ai-engineer: **the verify-tiers section only** | Add the Thai section above. **Merge order: the autonomy-B rework merges its ADAPTERS.md section first (its branch already edits the file); A+C rebases and adds its section after it.** | Readers of the adapter table |
| `tests/framework/test_doc_contracts.py` | A+C rework, ai-engineer (shared with the autonomy-B rework, which adds its own case; same merge order as ADAPTERS.md: B first) | One case: ADAPTERS.md contains the heading `ประตูตรวจ (verify tiers) — ข้อจำกัดที่ประกาศไว้` and the words `VERIFY_EXTRA_BANNED` and `limit:` | — |

**Must stay green:**
- all of `tests/hooks/test_verify_tiers.py` (221);
- the other 16 tests in `tests/hooks/test_regression_verify_tiers_qa.py`;
- `tests/hooks/test_verify_scripts.py` and `tests/ci/test_ci_examples.py` (AC-AC13);
- `tests/framework/test_neutrality.py`, because the conf example and the record code must name no provider.

**Not touched:**
- the approved spec and design;
- the guard hooks;
- the templates.

## Decisions (ADR-style)

- **AM2-ADR-1: built-in bans are pytest's, and other runners are named, not guessed.**
  - **Context:** Scanning every program over-refused real stacks (D6, D12, D15). Guessing other runners' flags got some wrong: go's `-x` prints commands.
  - **Decision:** pytest family only, with a `limit:` line for anything else, and project bans in `VERIFY_EXTRA_BANNED`.
  - **Consequences:** A non-pytest project gets no built-in protection until it fills `VERIFY_EXTRA_BANNED`. It is told so on every run of a listed test step.
- **AM2-ADR-2: limits are stated, not chased (owner ruling 2026-10-20).**
  - **Context:** Each closed spelling added code and false positives.
  - **Decision:** L1 to L8 are declared, in the conf example and in ADAPTERS.md.
  - **Consequences:** An agent can still reach a filtered run through L1 to L5. When counts are configured, the count check turns it RED. Retry flags are hard bans (AC-AC24), because the count check cannot see a retry.
- **AM2-ADR-3 (decided by the coordinator, 2026-10-20): retry-plugin flags are hard bans, never declarable.**
  - **Context:** The memory file says a route is *not* a declared limit if it "makes a gate report green falsely". L7 does exactly that, and the count check cannot see it, because a retried test is still one test `[INFERRED]`.
  - **Decision:** `--force-flaky` and `--max-runs` join the hard-ban table (AC-AC24). This is one list entry each, not a chase. `--flake-runs` stays a declared limit (L7), because it only takes effect together with `--flake-finder`, which is already banned `[INFERRED from the plugins' documented flags; not installed or run here]`.
  - **Consequences:** A project that genuinely uses the flaky plugin must remove those flags from its gate commands. They can never be declared in `VERIFY_ALLOWED_FILTERS`. Retries stay available outside the gate.

## Traceability

| PRD requirement | Criteria |
|---|---|
| R1 | AC-AC6 (amended) |
| R2 | AC-AC5 (amended) |
| R4 | AC-AC8a, AC-AC8b, AC-AC8c, AC-AC8d, AC-AC19 (amended), AC-AC20, AC-AC24 |
| R5 | AC-AC22, AC-AC23 |
| R10 | AC-AC21 |
| R12 | AC-AC8b, AC-AC20 |

AC-AC1 to AC-AC4, AC-AC7, AC-AC9 to AC-AC18 and their trace are unchanged.

In all, this amendment touches 12 criteria: 3 amended (AC-AC5, AC-AC6, AC-AC19), AC-AC8 replaced by 4 clauses, and 5 new (AC-AC20 to AC-AC24). They trace to 6 PRD requirements.

## Approval history

- **2026-10-20 — approved (human).** Registry key `spec-verify-tiers-merge-gate-am2-scanner-scope-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** ba-sa, from the owner's ease-of-use ruling (doc/memory/ease-of-use-over-strictness.md, commit 5e7c96f) and the coordinator's rulings D3 and D6 to D18 on doc/qa/QA-verify-tiers-AC.md. Built against branch `worktree-agent-ad1e27705199bd4e4` at `e436d1f`. Written as a separate amendment so that the approved spec and design stay unchanged.
