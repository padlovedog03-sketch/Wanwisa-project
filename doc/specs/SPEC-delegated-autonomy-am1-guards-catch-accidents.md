# SPEC: Amendment 1 — the always-human guards catch accidents, and say what they do not catch (increment B)

Status: Approved
Approval: spec-delegated-autonomy-am1-guards-catch-accidents-2026-10-20
Owner: ba-sa
Upstream: doc/specs/SPEC-delegated-autonomy.md (approved, registry key `spec-delegated-autonomy-2026-10-20`) and its doc/architecture/DESIGN-delegated-autonomy.md · owner ruling of 2026-10-20 recorded in doc/memory/ease-of-use-over-strictness.md (commit 5e7c96f), verbatim: "เอาตามที่แนะนำเลยให้ใช้งานง่าย"
Date: 2026-10-20

## Overview

The approved spec and design stay as they are. This file re-scopes increment B's guard criteria under the owner's ease-of-use ruling: command and path guards exist to catch accidental and casual mistakes. A shell can always spell an action another way. Those spellings are written down as declared limits and caught after the fact where a backstop exists. They are not chased one by one.

What changes:
- **B-AC2, B-AC4, B-AC6 and B-AC7 are re-scoped.** The guard must refuse:
  - the canonical and common spellings;
  - every case in the design's tables;
  - every round-1 bypass already closed.

  The self-inflicted holes that are already closed (stdlib shadowing, `9976550`) must stay closed.
- **The other spellings QA found in re-test 1 become declared limits.** That is 17 of the 20 red pins.
- **Defect 7 is a usability regression and is fixed, not declared.** Ordinary read-only work that names an owner script is refused today in every project. The new criterion B-AC10 makes it allowed. That is the other 3 of the 20 red pins.
- **Two rulings QA asked for are re-judged under ease of use** (AM1-ADR-3, AM1-ADR-4).
- **The anchor stays.** There are no signed approvals until the owner extends autonomy to merging into main or deploying to production (doc/memory/ease-of-use-over-strictness.md, point 3).

The implementation under test is on branch `worktree-agent-aa8662140b00eeca3` at `9976550`.

**What this amendment overrides.**
- B-AC2, B-AC4, B-AC6 and B-AC7 get the new wording below.
- B-AC10 is new.
- The opt-in carve-out in `check_commit` is narrowed (AM1-ADR-3).

Nothing else in the approved spec or design changes. B-AC1, B-AC3, B-AC5, B-AC8 and B-AC9 are unchanged.

**Markers.**
- `[MEASURED: <command>]`: I ran it on 2026-10-20, in the worktree of branch `worktree-agent-aa8662140b00eeca3` at `9976550`, unless another place is named. Guard probes used a throwaway repo built like the QA fixture `_project()`: a plain project, or a project with a live mandate. Each command was fed to `.claude/hooks/guard_bash.py` as a Bash payload. The probe script lives outside the repo.
- `[INFERRED]`: I read it, but did not run it.
- `[RELAYED: QA]`: QA measured it, and I did not re-run it.

## Acceptance criteria — changed wording

Each row gives the approved wording, the new wording and the reason. Every new wording ends with the same sentence: **"Other spellings are the declared limits in §Declared limits."**

### B-AC2 (R8)

**Old (approved):**

> `autonomy.classify_command(cmd)` returns the item IDs for each case in the design's command table (§B.2). It returns `[]` for each allow case: `grep -rn 'git push origin main' doc/`, `git push origin feature/x`, `curl -s https://example.test/x` (a GET), a heredoc that only mentions a banned command, and `python3 -m pytest`.

**New:**

> `autonomy.classify_command(cmd)` returns the item IDs for each case in the design's command table (§B.2), for every round-1 spelling pinned in `tests/hooks/test_regression_always_human_bypasses.py`, and for the canonical command behind the listed wrappers (`env`, `exec`, `nohup`, `time`, `sudo`, `doas`, `command`, `builtin`, `nice`, `timeout`, `stdbuf`, `xargs`, `source`, `.`). It returns `[]` for each allow case: `grep -rn 'git push origin main' doc/`, `git push origin feature/x`, `curl -s https://example.test/x` (a GET), a heredoc that only mentions a banned command, and `python3 -m pytest`. Other spellings are the declared limits in §Declared limits.

**Reason.**
- Re-test 1 found five more push spellings: three unlisted wrappers, a git alias and `--repo=`. It also found git operations that rewrite a protected path.
- Round 1 had already closed 25 routes. Each new fix added false positives (defect 7) and code.
- The owner ruled that these spellings are stated, not chased.

**Probe** `[MEASURED]`, with a live mandate:
- `git push origin main`, `env git push origin main` and `nohup git push origin main` → exit 2, `always-human item AH3 — matched: git push <remote> main`.
- `git push origin feature/x` → exit 0.

### B-AC4 (R4, R9, R39)

**Old (approved):** the owner-script rule, in every project. `guard_bash.py` exits 2 with `owner-only command` for each of 11 listed invocations: `scripts/approve.sh x --by a`, `./scripts/approve.sh x`, `bash scripts/approve.sh x`, `python3 scripts/approve.py x`, `scripts/delegate.sh "t" --by a`, `scripts/revoke.sh k`, `scripts/override.sh d`, `scripts/away.sh --until d`, `scripts/evolve.sh`, `echo '{…}' >> ~/.jarvis/approvals/registry.jsonl`, and `tee -a "$APPROVAL_LOG"`. `scripts/approve.sh --list` stays allowed.

**New:**

> In every project, whether autonomy is active or not, `guard_bash.py` exits 2 with `owner-only command` for:
> - each of the 11 approved invocations;
> - each round-1 spelling pinned in `tests/hooks/test_regression_always_human_bypasses.py`;
> - an owner script found anywhere in the argv of a program that is not a reader (B-AC10's list).
>
> Read-only uses stay allowed:
> - `scripts/approve.sh --list`;
> - the read-only uses in B-AC10.
>
> The rule keeps working when the core cannot be imported. It fails closed for owner scripts, and it is not switched off by an agent-written `scripts/<stdlib name>.py`.
>
> Other spellings are the declared limits in §Declared limits.

**Reason.**
- Re-test 1 found that some programs on the reader list can still run a file: `git -c alias…`, `git bisect run`, and `awk system()`. It also found registry writes through a symlink made in the same command, or through `cd $HOME/…`.
- Under the ruling these are declared. The shadowing hole is different: it is self-inflicted (the guard imported code the agent can write), so it stays closed.

**See AM1-ADR-1.** Several of these limit classes can forge an approval that a *local* `verify_approvals.py` run accepts. Only CI's registry check, which reads a registry the agent cannot write, catches it. That needs the owner's eye.

### B-AC6 (R9)

**Old (approved):**

> Given autonomy is active, When a Write/Edit/MultiEdit/NotebookEdit targets a protected path (design §B.3 …), Then the new `guard_autonomy_paths.py` exits 2 naming AH5. Given autonomy is **not** active, Then the same edit is allowed (R6, ADR-6).

**New:** the approved wording is unchanged, and these are added.

> Given autonomy is active, a shell write to a protected path through a redirect, `tee`, `sed -i`, `cp`, `mv` or `rm` (the design §B.2 list) is refused naming AH5.
>
> Given autonomy is active and an agent-written `scripts/shlex.py` (or `argparse.py`, `dataclasses.py`, `datetime.py`) raises on import, Then both guards still exit 2 on a protected write and on `git push origin main`.
>
> The design list of writers is exhaustive for the guard. Other writers, and rewinding the tree, are the declared limits in §Declared limits.

**Reason.**
- QA asked whether the §B.2 writer list is exhaustive (its "Low (ruling)" row). Under the ruling, it is.
- The shadowing case is self-inflicted and stays covered.

**Probe** `[MEASURED]`, with a live mandate:
- Refused with exit 2 and `AH5 — matched: write to protected path …`: `echo x > .claude/settings.json`, `sed -i '' s/a/b/ scripts/autonomy.json` and `cp x doc/mandates/M.md`.
- Exit 0, now declared: `perl -pi -e … .claude/settings.json`, `truncate -s0 scripts/autonomy.json`, `unlink doc/mandates/…`, `rsync x .claude/settings.json`, `find doc/mandates -delete`, `patch .claude/settings.json p.diff` and `chmod 000 scripts/autonomy.json`.

Shadowing: `tests/hooks/test_autonomy_stdlib_shadowing.py` collects 15 tests, all green. QA's two shadow pins in the rework file are green too `[MEASURED: python3 -m pytest … -q → 213 passed over the B test files listed under Affected tests]`.

### B-AC7 (R9, adapter ข)

**Old (approved):**

> Given autonomy is active, and a commit stages a protected path with no `Owner-Approved: <key>` trailer that resolves to an owner registry entry, When `.githooks/pre-commit` runs, Then it refuses and names AH5 and the path. With the trailer present, it passes.

**New:**

> Given autonomy is active, and a commit stages a protected path with no `Owner-Approved: <key>` trailer that resolves to the owner's approval of a changed protected path or of the governing mandate document, When `.githooks/commit-msg` runs, Then it refuses and names AH5 and the path. With the trailer present, it passes.
>
> The opt-in commit (the one that first adds `scripts/autonomy.json`, with a trailer naming a live mandate or order of that project) clears only:
> - `scripts/autonomy.json`;
> - the document that the trailer's registry entry names as its `artifact`.
>
> Every other protected path it adds still needs an owner trailer (AM1-ADR-3).
>
> Given an agent-written `scripts/argparse.py` shim, Then the check still runs (the CLI is started with `-I`).
>
> A tree rewound before the opt-in is a declared limit in §Declared limits.

**Reason.**
- The check runs in `.githooks/commit-msg`, not pre-commit, because pre-commit cannot see the message. The old wording named the wrong hook `[MEASURED: git ls-tree --name-only HEAD .githooks/ → commit-msg, pre-commit; grep -n check-commit .githooks/commit-msg → line 17, python3 -I scripts/autonomy.py check-commit]`. This is a correction to approved wording, beyond the re-scope; the owner should see it.
- The carve-out is narrowed per AM1-ADR-3.
- The shadowing case is self-inflicted and stays covered by `test_regression_a_shadow_module_cannot_switch_the_commit_check_off` `[MEASURED: green in the 213-pass run]`.

### B-AC10 (new): reading an owner script is allowed in every project (defect 7)

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| B-AC10 | R4, R9 (usability) **RED-FIRST** | Given a plain project, and separately a project with a live mandate, When `guard_bash.py` receives each command below, Then it exits 0. The commands are:<br>• `find . -name approve.sh`<br>• `ruff check scripts/approve.py`<br>• `scripts/approve.sh --help`<br>• `scripts/approve.sh -h`<br>• `scripts/approve.sh spec-x --by a --help`<br>• `nl scripts/approve.sh`<br>• `sort scripts/approve.sh`<br>• `bash -n scripts/approve.sh`<br>• `python3 -m py_compile scripts/approve.py`<br>**Hostile neighbours stay refused, with exit 2 and `owner-only command`:**<br>• `find . -name approve.sh -exec sh {} \;`<br>• `find . -name approve.sh -execdir sh {} \;`<br>• `find . -name approve.sh -ok sh {} \;`<br>• `bash scripts/approve.sh x`<br>• `sh scripts/approve.sh x`<br>• `python3 scripts/approve.py x`<br>• `scripts/approve.sh x --by a`<br>• `python3 -m py_compile scripts/approve.py && python3 scripts/approve.py x` (the second segment is judged on its own)<br>Each allowed case is shown red against `9976550` first. | `tests/hooks/test_regression_autonomy_rework_bypasses.py` (the 3 existing pins, kept), plus new cases in `tests/hooks/test_guard_always_human.py` |

**Probe** `[MEASURED]`, plain project, at `9976550`:
- **Refused today with exit 2, and must become allowed:** `find . -name approve.sh`, `ruff check scripts/approve.py`, `scripts/approve.sh --help`, `scripts/approve.sh -h`, `nl …`, `sort …`, `bash -n scripts/approve.sh` and `python3 -m py_compile scripts/approve.py`. Each printed `owner-only command — matched: owner-only approve.sh` (or `approve.py`).
- **Already allowed:** `cat scripts/approve.sh`, `grep -n x scripts/approve.sh` and `scripts/approve.sh --list`.
- **Refused today with exit 2, and must stay refused:** `find . -name approve.sh -exec sh {} \;`, `bash scripts/approve.sh x`, `python3 scripts/approve.py x` and `scripts/approve.sh x --by a`.

**Why `--help` is safe anywhere in the argv:**
- `scripts/approve.sh` is `exec "$PY" approve.py "$@"` and does nothing else `[MEASURED: grep -v '^#' scripts/approve.sh]`.
- `approve.py` parses with `argparse`, which exits on `--help` or `-h` before any write `[MEASURED: APPROVAL_LOG=<empty temp file> python3 scripts/approve.py spec-x --by a --help, and again with -h → rc=0 both times, the registry still 0 bytes, git status unchanged]`.
- The owner wrappers that do not exist yet (`delegate.sh`, `revoke.sh`, `override.sh`, `away.sh`, `evolve.sh`, `release.sh`) must honour `--help`/`-h` the same way. Each one's own increment carries that as a test.

**Design for the engineer (pseudocode, not code):**
- Add `--help` and `-h` to `READ_ONLY_FLAGS`.
- Make the program a reader when either:
  - its basename is `find`, `nl`, `sort` or `ruff`, and, for `find`, none of `-exec`, `-execdir`, `-ok`, `-okdir` or `-delete` is in its argv;
  - it is an interpreter (`bash`, `sh`, `zsh`, `dash`, `ksh`) whose options before the script include `-n`;
  - it is `python[N] -m py_compile`.
- `bash -n` is refused today even though `-n` is in `READ_ONLY_FLAGS`, because that set is only searched after the script word `[MEASURED: probe above; INFERRED cause from autonomy.py _owner_script, lines 610-621]`.

## Declared limits

These are the spellings the guard does not refuse. Each one was measured passing at `9976550`. The backstop column says honestly what catches it afterwards.

| # | Limit | Example (QA pin) | Backstop |
|---|---|---|---|
| D-L1 | A git alias | `git -c alias.ok='!scripts/approve.sh' ok spec-x --by agent`; `git -c alias.p=push p origin main` | Push: the remote's branch protection, if the project configured it `[INFERRED; outside this repo]`. Owner script: **see AM1-ADR-1** |
| D-L2 | `git bisect run` | `git bisect run scripts/approve.sh spec-x --by agent` | **See AM1-ADR-1** |
| D-L3 | `awk system()` | `awk 'BEGIN{system(ARGV[1])}' scripts/approve.sh` | **See AM1-ADR-1** |
| D-L4 | Rewinding the tree, or stash | `git checkout <pre-opt-in>`, `git reset --hard <pre-opt-in>`, `git stash -u` of an uncommitted opt-in | Guards and commit-msg both read `inactive` while rewound `[INFERRED from _authority, lines 919-960]`. The remaining backstops are the PR diff, which shows the opt-in files gone, and CI's registry check on stamped docs (AM1-ADR-1). |
| D-L5 | Restoring a protected path from another ref | `git checkout <ref> -- .claude/settings.json`, `git checkout <ref> -- doc/mandates`, `git restore --source=<ref> doc/mandates/…` | commit-msg refuses the commit without an owner trailer, when the tree is not rewound `[INFERRED: the staged path is protected, so check_commit applies]`. CI: the diff. |
| D-L6 | A symlink created in the same command | `ln -s <registry> r && echo x >> r`; the directory form | **See AM1-ADR-1**. Protected repo paths: commit-msg, as D-L5. |
| D-L7 | Unlisted wrappers | `arch -arm64 git push origin main`, `caffeinate -i …`, `script -q /dev/null …` | The remote's branch protection `[INFERRED]` |
| D-L8 | `--repo=` | `git push --repo=origin main` | As D-L7 |
| D-L9 | `cd` through a variable | `cd $HOME/.jarvis/approvals && echo x >> registry.jsonl` | **See AM1-ADR-1** |
| D-L10 | Writers outside the design list | `perl -pi`, `truncate`, `unlink`, `rsync`, `find -delete`, `patch`, `chmod` | Protected repo paths: commit-msg (D-L5). The registry: a truncate or deletion makes `verify_approvals` fail for every approved doc `[INFERRED: an approved doc without its registry entry is a failure]`. An in-place forged line: **see AM1-ADR-1**. |
| (approved) | Commands in `bash -c`, `python -c`, a heredoc or pipe into a shell, or inside a script | — | Unchanged from the approved design §B.4 |

**Text for the spec.** This table is the spec text.

**Text for `doc/framework/ADAPTERS.md`.** It replaces the paragraph `**ข้อจำกัดที่พูดตรง ๆ:** …` under `## รายการที่มนุษย์ตัดสินเสมอ — จุดบังคับต่อตัวเชื่อม`, a section that exists on the B branch only. It is written in Thai to match the file.

```markdown
**ข้อจำกัดที่ประกาศไว้ (มติเจ้าของงาน 2026-10-20: ด่านจับความพลาด ไม่ไล่ปิดทุกทาง):** ด่านคำสั่งอ่าน*ข้อความ*ของคำสั่ง
shell จึงสะกดการกระทำเดียวกันแบบอื่นได้เสมอ ทางเหล่านี้ด่านไม่กัน และไม่ไล่ปิดทีละทาง:
- คำสั่งที่ซ่อนในสคริปต์ ใน `bash -c "…"`, `python -c`, heredoc หรือ pipe เข้า shell
- git alias (`git -c alias.x=…`), `git bisect run`, `awk` ที่เรียก `system()`
- ย้อนต้นไม้ไปก่อนเปิดใช้ (`git checkout`/`reset --hard` ไปคอมมิตก่อนหน้า, `git stash -u`) และดึงไฟล์ที่ป้องกันจาก ref อื่น (`git checkout <ref> -- <path>`, `git restore --source`)
- symlink ที่สร้างในคำสั่งเดียวกัน และ `cd $HOME/…`
- ตัวห่อที่ไม่อยู่ในรายการ (`arch`, `caffeinate`, `script`) และ `git push --repo=…`
- ตัวเขียนไฟล์นอกรายการของแบบ (`perl -pi`, `truncate`, `unlink`, `rsync`, `find -delete`, `patch`, `chmod`)

ตัวจับย้อนหลัง: commit-msg (เส้นทางที่ป้องกันต้องมี trailer ของเจ้าของ), การป้องกันสาขาที่ฝั่ง remote และ CI
บรรทัดทะเบียนที่เขียนผ่านทางเหล่านี้ผ่าน `verify_approvals` *ในเครื่อง* ได้ เพราะหน้าตาเหมือนของจริง แต่ CI อ่านทะเบียนจาก secret
`APPROVAL_REGISTRY` ที่เอเจนต์เขียนไม่ได้ เอกสารที่ประทับคีย์ปลอมจึงแดงที่ CI — **เฉพาะโปรเจกต์ที่ตั้งขั้นนั้นไว้** และเจ้าของงาน
ต้องเพิ่มบรรทัดเข้า secret ทีละบรรทัด ห้ามคัดลอกไฟล์ทะเบียนในเครื่องไปทั้งไฟล์ การปลอมจึง*ทิ้งร่องรอย* ไม่ใช่*เป็นไปไม่ได้*
งานอ่านอย่างเดียว (`find -name`, `ruff check`, `--help`, `nl`, `sort`, `bash -n`, `py_compile`) ที่เอ่ยชื่อสคริปต์ของเจ้าของ ผ่านเสมอ
```

## QA regression pins: the 20 still red

File: `tests/hooks/test_regression_autonomy_rework_bypasses.py`. At `9976550` it gives `20 failed, 2 passed` `[MEASURED: python3 -m pytest tests/hooks/test_regression_autonomy_rework_bypasses.py -q -p no:cacheprovider]`. The 2 that pass are the shadowing pins, closed by `9976550`.

**17 pins are retired, and the parametrize entries are deleted.** They are not converted to assert exit 0. A test that pins a hole open goes red on the day someone closes it, and the guard prints nothing for a limit, so there is no "limit behaviour" to assert. The declared list is instead pinned once, by a doc-contract case (see Affected tests).

| # | Pin | Action | Limit |
|---|---|---|---|
| 1 | `test_regression_rewinding_past_the_opt_in_keeps_guards_on[checkout-pre-opt-in]` | Retire | D-L4 |
| 2 | `test_regression_rewinding_past_the_opt_in_keeps_guards_on[reset-hard-pre-opt-in]` | Retire | D-L4 |
| 3 | `test_regression_stashing_an_uncommitted_opt_in_keeps_guards_on` | Retire | D-L4 |
| 4 | `test_regression_restoring_a_protected_path_from_another_ref_is_refused[git checkout pre-opt-in -- .claude/settings.json]` | Retire | D-L5 |
| 5 | `…restoring_a_protected_path_from_another_ref_is_refused[git checkout pre-opt-in -- doc/mandates]` | Retire | D-L5 |
| 6 | `…restoring_a_protected_path_from_another_ref_is_refused[git restore --source=pre-opt-in doc/mandates/MANDATE-proj-first.md]` | Retire | D-L5 |
| 7 | `test_regression_owner_script_run_through_a_reader_is_refused[git -c alias.ok='!scripts/approve.sh' ok spec-x --by agent]` | Retire, unless AM1-ADR-1 option (b) is chosen | D-L1 |
| 8 | `…owner_script_run_through_a_reader_is_refused[git bisect run scripts/approve.sh spec-x --by agent]` | Retire, unless AM1-ADR-1 option (b) is chosen | D-L2 |
| 9 | `…owner_script_run_through_a_reader_is_refused[awk 'BEGIN{system(ARGV[1])}' scripts/approve.sh]` | Retire, unless AM1-ADR-1 option (b) is chosen | D-L3 |
| 10 | `test_regression_registry_write_is_refused[file-link-same-command]` | Retire | D-L6 |
| 11 | `test_regression_registry_write_is_refused[dir-link-same-command]` | Retire | D-L6 |
| 12 | `test_regression_registry_write_is_refused[cd-through-HOME]` | Retire | D-L9 |
| 13 | `test_regression_push_to_a_protected_branch_is_refused[arch -arm64 git push origin main]` | Retire | D-L7 |
| 14 | `…push_to_a_protected_branch_is_refused[caffeinate -i git push origin main]` | Retire | D-L7 |
| 15 | `…push_to_a_protected_branch_is_refused[script -q /dev/null git push origin main]` | Retire | D-L7 |
| 16 | `…push_to_a_protected_branch_is_refused[git -c alias.p=push p origin main]` | Retire | D-L1 |
| 17 | `…push_to_a_protected_branch_is_refused[git push --repo=origin main]` | Retire | D-L8 |

**3 pins are kept unchanged and must turn green (B-AC10, defect 7):**

| # | Pin | Action |
|---|---|---|
| 18 | `test_regression_reading_an_owner_script_stays_allowed[find . -name approve.sh]` | Keep; fix |
| 19 | `test_regression_reading_an_owner_script_stays_allowed[ruff check scripts/approve.py]` | Keep; fix |
| 20 | `test_regression_reading_an_owner_script_stays_allowed[scripts/approve.sh --help]` | Keep; fix |

The module docstring of that file, which says "None is one of the declared limits", must be rewritten to point here. The two shadowing pins stay.

## Affected tests / affected files

**How this list was built:**
- `git log --oneline` and `git show --stat` over branch `worktree-agent-aa8662140b00eeca3`, from the merge base 9a97bc6 to `9976550`.
- `grep -rn "opt.in\|Owner-Approved: {_MANDATE_KEY}" tests/ --include='*.py'` on the branch, to find every test that commits an opt-in.
- `git diff 9a97bc6 worktree-agent-aa8662140b00eeca3 --stat -- doc/framework/ADAPTERS.md` → 18 lines added on this branch `[MEASURED]`.
- A carve-out probe in a scratch copy of the branch (`git archive HEAD`), with the AM1-ADR-3 rule patched in. Over `tests/framework/test_regression_commit_msg_autonomy.py`, `test_commit_msg_owner_trailer.py`, `test_pre_commit.py`, `tests/hooks/test_autonomy_stdlib_shadowing.py` and `test_guard_always_human_rework.py`, it gave `1 failed, 79 passed`. The one failure is `test_regression_deleting_the_project_file_needs_an_owner_trailer`, whose opt-in commit also adds `.githooks/commit-msg`, `scripts/autonomy.py` and `scripts/verify_approvals.py`. The control, without the patch, gave `2 passed` for that file `[MEASURED]`.

One owner per file:

| File | Owner | Change |
|---|---|---|
| `scripts/autonomy.py` | B rework, ai-engineer | B-AC10: `READ_ONLY_FLAGS` gains `--help` and `-h`, plus the reader rules. AM1-ADR-3: the carve-out is narrowed. AM1-ADR-1 (b), only if the owner chooses it. |
| `tests/hooks/test_guard_always_human.py` | B rework, ai-engineer | B-AC10 cases (allowed and hostile, in plain and active projects) |
| `tests/framework/test_regression_commit_msg_autonomy.py` | B rework, ai-engineer | `test_regression_deleting_the_project_file_needs_an_owner_trailer`: commit the framework files in a base commit while the registry is empty, then opt in with `scripts/autonomy.json` only (the pattern `test_commit_msg_owner_trailer.py` already uses). Its assertion is unchanged. |
| `tests/framework/test_commit_msg_owner_trailer.py` | B rework, ai-engineer | New cases for AM1-ADR-3. The opt-in commit that also adds `doc/orders/ORDER-self.md`, `doc/mandates/MANDATE-wide.md`, `scripts/release.sh` or `.githooks/post-checkout` is refused naming that path. The mandate document that the trailer's entry names is cleared. |
| `tests/hooks/test_regression_autonomy_rework_bypasses.py` | qa | Delete the 17 parametrize entries or functions listed above. Keep the 3 B-AC10 pins and the 2 shadowing pins. Rewrite the docstring. |
| `doc/qa/QA-delegated-autonomy-B.md` | qa | A re-test 2 note: 17 pins are retired by this amendment, and the two rulings are answered. |
| `doc/framework/ADAPTERS.md` | B rework, ai-engineer: **the always-human section only** | Replace the limits paragraph with the Thai text above. **Merge order: B merges first; the verify-tiers A+C rework (SPEC-verify-tiers-merge-gate-am2) rebases and adds its own section after.** |
| `tests/framework/test_doc_contracts.py` | B rework, ai-engineer | One case: the always-human section of ADAPTERS.md names each D-L class (`alias`, `bisect`, `awk`, `stash`, `restore`, `symlink`, `caffeinate`, `--repo=`, `cd $HOME`, `perl -pi`) and the read-only line. **Shared with the A+C rework, which adds its own case. Merge order as for ADAPTERS.md.** |

**Must stay green** `[MEASURED: 213 passed over these files at 9976550]`:
- `tests/hooks/test_regression_always_human_bypasses.py` (24 round-1 pins);
- `tests/hooks/test_autonomy_stdlib_shadowing.py` (15);
- `tests/framework/test_regression_commit_msg_autonomy.py`;
- `tests/hooks/test_guard_always_human.py`;
- `tests/hooks/test_guard_autonomy_paths.py`;
- `tests/framework/test_autonomy_items.py`;
- `tests/framework/test_pre_commit.py`;
- `tests/framework/test_commit_msg_owner_trailer.py`.

Also `tests/framework/test_neutrality.py`.

**Not touched:**
- the approved spec and design;
- `scripts/approve.py`, `scripts/approve.sh` and `scripts/verify_approvals.py`;
- `.claude/hooks/*`, unless B-AC10 needs a wiring change there `[INFERRED: the rules live in the core]`.

## Decisions (ADR-style)

- **AM1-ADR-1 (for human review): a forged registry line passes locally and is caught at CI, if the project set CI up.**
  - **Context:**
    - D-L1, D-L2 and D-L3 (an owner script run through git or awk), plus D-L6, D-L9 and an in-place D-L10 write to the registry, can each append a line to the **local** registry.
    - QA carried the git alias end to end. It wrote a registry line and stamped the document `Approved` `[RELAYED: QA re-test 1, B-AC4 row]`.
    - Locally, `scripts/verify_approvals.py` cannot tell that line from the owner's. It checks that the required keys are present (`key`, `artifact`, `status`, `approved_by`, `approved_at`), not who wrote them `[INFERRED: _REQUIRED_REGISTRY_KEYS, line 79]`. So a local run reports green over a forged approval.
    - CI does not read the local file. Both CI examples write the registry from the secret `APPROVAL_REGISTRY` to `/tmp/registry.jsonl`, and fail any document whose `Approval:` key is not in it. SETUP.md says to keep that registry in a secret or in a repo only people can write. `[MEASURED: grep -n "APPROVAL_LOG\|registry\|verify_approvals" ci-examples/*.yml doc/framework/SETUP.md → github-actions.yml:50-78, azure-pipelines.yml:34-59, SETUP.md:66-68]`
    - So the forged stamp turns CI red on a protected branch. That is the brief's "caught after the fact by verify_approvals and CI" `[INFERRED: CI not run here]`.
    - It holds only if two things are true:
      - the project configured that CI step and branch protection;
      - the owner never syncs the secret by copying the whole local registry file, because a blind copy would carry the forged line into CI.
  - **Options:**
    - **(a) Declare, as the brief asks.** CI is the backstop. This amendment is written this way.
    - **(b) Also close the three cheapest local routes.** `git` counts as a reader only with a read subcommand (`log`, `diff`, `show`, `blame`, `grep`, `status`, `ls-files`) and no `-c` before it, and `awk` leaves the reader list. That is two list changes, not a chase. Pins 7 to 9 would then be kept, and must go green. D-L6, D-L9 and D-L10 stay declared.
  - **Recommendation:** (a), plus one sentence in SETUP.md: "add registry lines to the CI secret one at a time, never by copying the local file". That keeps CI an honest backstop at no code cost. (b) is optional, and it is cheap if the owner wants the local guard to stop the route QA proved end to end.
  - **Consequences:**
    - Under (a), a project without the CI step has no backstop for these routes. ADAPTERS.md says so.
    - Under (b), `git log scripts/approve.sh` and `git diff scripts/approve.py` stay allowed, and `awk '…' scripts/approve.sh` is refused (a rare read).
    - Either way, the signed-approval question stays closed until autonomy reaches merge or production (ruling point 3).
    - The SETUP.md sentence is a doc change outside both amendments' file lists. If the owner accepts it, it goes to the B rework engineer.
- **AM1-ADR-2: the §B.2 writer list is exhaustive for the guard.**
  - **Context:** QA asked (its "Low (ruling)" row).
  - **Decision:** Yes. Other writers are D-L10.
  - **Consequences:** The commit-msg check is the backstop for repo paths.
- **AM1-ADR-3 (QA ruling 1): the opt-in carve-out clears `scripts/autonomy.json` and the trailer entry's own mandate or order document, and nothing else.**
  - **Context:**
    - Today the opt-in commit clears every protected path it adds. That includes a new `doc/orders/ORDER-self.md`, a second mandate, an owner wrapper and a new git hook `[RELAYED: QA probe, exit 0]`.
    - The brief's candidate, "clears only `scripts/autonomy.json`", would block the owner's normal flow. A mandate document that `approve.sh` has just stamped is new in the opt-in commit. `_owner_approves` never accepts a mandate-kind key `[INFERRED: autonomy.py, the docstring and the `kind` check of _owner_approves]`, so the opt-in is that document's only route in.
    - The registry entry, which the agent cannot write, names that one path.
  - **Decision:** Clear `scripts/autonomy.json`, plus the `artifact` path of the live mandate or order named in the trailer. Everything else needs an owner trailer, or must already be at HEAD.
  - **Consequences:**
    - One existing test needs its fixture split into a base commit and an opt-in commit (`test_regression_deleting_the_project_file_needs_an_owner_trailer`) `[MEASURED: scratch probe, 1 failed, 79 passed]`.
    - Projects whose framework files are committed at install, before opting in, are unaffected `[INFERRED: test_pre_commit._opt_in follows this pattern and stays green in the probe]`.
- **AM1-ADR-4 (QA ruling 2): a project claiming another project's mandate is deferred to increment C, as a named precondition.**
  - **Context:**
    - An agent may write `scripts/autonomy.json` with another project's slug while the project is inactive. `status` then reports that mandate.
    - In increment B this only switches guards *on*, the safe direction `[RELAYED: QA "harmless today"]`.
    - Harm needs `approve-under`, which arrives in increment C.
  - **Decision:** No change in B. Increment C's spec must make `approve-under` grant only when the mandate's `artifact` document exists at HEAD of this repository, committed through the opt-in rule above.
  - **Consequences:**
    - B gains no machinery.
    - C cannot be approved without stating this binding.
    - If the owner wants a stronger binding later (for example, recording the repository's first commit id in the mandate's registry entry), that is a change to the owner scripts, made when autonomy extends further (ruling point 3).

## Traceability

| PRD requirement | Criteria |
|---|---|
| R4 | B-AC4 (amended), B-AC10 |
| R8 | B-AC2 (amended) |
| R9 | B-AC4, B-AC6, B-AC7 (amended), B-AC10 |
| R39 | B-AC4 (amended) |

R7 and R10 are unchanged (B-AC1, B-AC3, B-AC8). B-AC5 and B-AC9 are unchanged.

In all, this amendment touches 5 criteria: 4 amended and 1 new.

## Approval history

- **2026-10-20 — approved (human).** Registry key `spec-delegated-autonomy-am1-guards-catch-accidents-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** ba-sa, from the owner's ease-of-use ruling (doc/memory/ease-of-use-over-strictness.md, commit 5e7c96f) and doc/qa/QA-delegated-autonomy-B.md re-test 1. Built against branch `worktree-agent-aa8662140b00eeca3` at `9976550`. Written as a separate amendment so that the approved spec and design stay unchanged.
