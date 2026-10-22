# QA Report: delegated-autonomy amendment 2 (task orders), row-5 increments

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy-am2-task-orders-scope.md
Date: 2026-10-22

## Verdict: PASS

Increment 3 (Registry and owner commands): A-AC10, A-AC9, J-AC1, J-AC2, AM2-AC3 (b), AM2-AC7, A-AC7 (registry half), A-AC6 (c) and A-AC8 all pass. They were tested end to end in throwaway repos through the real wrappers and the real `commit-msg` hook, and the same harness runs red on HEAD. The two post-review fixes are confirmed: `--by` and the task refuse control characters, and `verify-fast.sh` routes the new files. The full suite (`2465 passed, 3 skipped`) and `scripts/verify-full.sh` are green (rc=0). No defects. The open items are parked (see Increment 3).

Increment 2 (Log): AM2-AC2, F-AC2, AM2-AC3 (a), AM2-AC8 for `log`/`verify-log` and A-AC8 all pass, end to end in throwaway repos, with the full suite and `scripts/verify-full.sh` green (rc=0). No defects. Five observations are parked (see Increment 2 — Log).

Increment 1 (F1), re-test 2: F-AC1 (commit half) and A-AC8 (guard half) both pass. Both defects from the first QA run are closed. A commit into a `wip/x` worktree is now allowed when the hook's cwd is on `main`, and a commit on an unborn `main` is now refused under autonomy. The reverse direction (a worktree cwd committing into `main`) is refused. With no live autonomy, behaviour is unchanged. The first run's FAIL is kept below as history.

## Increment 3 — Registry and owner commands

### Scope and provenance

- Tier 1. The human approved at the brief. Review PASS: doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md (Reviewer-run a6edbcdf772e6fa2d, Author-run a302faca16121a04e). After the review, the engineer refused control characters in `--by` and the task, and added `verify-fast.sh` routing. Both changes are checked below. Jarvis decided that `--allow` names the grants exactly, and that the defaults apply only when `--allow` is omitted (review Q1).
- Change under test: the 12 uncommitted files in worktree `.claude/worktrees/agent-a302faca16121a04e`. Its HEAD is be34406, and between be34406 and this branch's HEAD 9e00765 only the REVIEW file differs. The 12 files:
  - Changed: `scripts/approve.py`, `scripts/autonomy.py`, `scripts/verify-fast.sh`, `scripts/verify_approvals.py`, `tests/framework/test_commit_msg_owner_trailer.py`, `tests/hooks/test_approve_script.py`, `tests/hooks/test_guard_always_human.py`, `tests/hooks/test_verify_approvals.py`.
  - New: `scripts/delegate.sh`, `scripts/revoke.sh`, `doc/templates/order.md`, `tests/framework/test_delegate.py`.
- Scratch copies are in the QA scratchpad `qa3-1792685002/`. `old` is `git archive 9e00765`. `new` is the same plus the 12 files, and `diff -rq old new` shows exactly those 12. `vf` is `new` made into a git repo, for the exit gate.
- Registry safety: every owner command ran as a subprocess inside my scratch pytest harness `harness/test_qa3_e2e.py`. Each repo had `HOME` and `APPROVAL_LOG` under pytest `tmp_path` and used the tree's own `.githooks/commit-msg` through `core.hooksPath`. The real registry was never read or written. My own shell's guard refused two direct commands, as it should (`owner-only approve.py`, `owner-only delegate.sh`), and I did not work around it.
- Existing tests unchanged: `diff -u old/<f> new/<f> | grep -c '^-[^-]'` over the 4 changed test files → 0, 0, 0, 0.
- The harness (64 cases) on `new` → `64 passed`. The same harness on `old` → `56 failed, 8 passed`. The 8 that pass on old are expected passes: the 6 `opted_in=False` owner-command guard refusals (A-AC6 (c) was already built, per the spec), the missing-`artifact` verifier probe (already measured on HEAD, per A-AC10), and the `approve.sh` parity case (old against old).

### Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| J-AC1 | `delegate.sh` writes `doc/orders/ORDER-&lt;project&gt;-&lt;s&gt;.md` from `order.md`, approved with its key, runs `git add`, and appends one entry: the 5 fields plus `kind: order`, `grants`, `expires` and `task_sha256`. The key is `order-&lt;project&gt;-&lt;s&gt;-&lt;date&gt;[-rN]`. `verify_approvals.py` passes | PASS | `test_e2e_issue_commit_status_revoke`, on branch `wip/x` with `scripts/autonomy.json` `{"project":"proj"}`. The task was `"  task with spaces <key> <task> ünïcode  "`. Result: rc 0. `git diff --cached --name-only` → exactly `doc/orders/ORDER-proj-first.md`. The document has one `Status: Approved` line and `Approval: order-proj-first-2026-10-22`, with no template marker left. There is 1 registry entry: all 5 fields, `kind: order`, `grants` = the 6 defaults, and `expires` = `--until`. Committed with the printed trailer → rc 0. The committed blob's one `Task: ` line, split on `\n`, holds the task's bytes verbatim, and its SHA-256 equals `task_sha256`. The marker-shaped text in the task stayed literal. `autonomy.py status` → `order order-proj-first-2026-10-22`. `verify_approvals.py` → rc 0, but it checked 0 documents ("nothing to verify"), because `doc/orders` is not yet in `_DOC_DIRS`. Order documents are resolved in increment 4. `--allow merge` → `grants: ["merge"]`, and `--allow spec,deploy-dev` → `["spec","deploy-dev"]`. That is exact naming, as Jarvis decided. |
| J-AC2 | Each of the 12 never-grantable grants, unknown grants, bare `deploy`, and `merge` without `verify-merge.sh` → exit 2 naming the grant | PASS | `test_refused_grants_write_nothing`. Each of the 12 → rc 2 `refused — nothing written: grant <g> is never grantable by an order (R41)`. `deploy` → `grant deploy is ambiguous — say deploy-dev or deploy-prod`. `fly` → `unknown grant fly`. `SPEC` → `unknown grant SPEC`. An empty value → `unknown grant (empty)`. `spec,widen` → names `widen`. In every case the registry bytes and `git status --porcelain` are unchanged, and no `doc/orders/` directory is created. `test_merge_without_gate_refused`: with `scripts/verify-merge.sh` removed, `--allow spec,merge` → rc 2 `merge needs the verify-tiers merge gate (scripts/verify-merge.sh is missing)`, and nothing is written. |
| AM2-AC3 (b) | An added order document commits under its own live, unrevoked order key. Still refused, naming AH5 and the path: a modified order document, or one under a different, revoked or expired order, and other protected paths | PASS | Real `git commit` through `commit-msg`. With no trailer → rc 1 `check-commit: always-human item AH5: doc/orders/ORDER-proj-first.md is protected while autonomy is active`. Under its own key → rc 0. `test_order_doc_commit_refusals`, each refused with rc 1 and AH5 naming the path: order 2 under order 1's key; order 2 under its own key after `revoke.sh`; a hand-seeded order whose `expires` is yesterday; the committed order 1 edited and committed under its own key; and `scripts/autonomy.json` edited under order 1's key. |
| AM2-AC7 | `--help`, `-h`, and `"t" --by o --help` for both wrappers → rc 0, registry byte-identical, `git status` unchanged. The guard allows each one in a plain project and under an order | PASS | `test_help_writes_nothing_and_guard_allows`: 6 forms × {a live order, no opt-in} = 12 cases. Each gives rc 0, prints `usage:`, and leaves the registry bytes and `git status --porcelain` unchanged. The live-order case has a staged order and one registry line. `guard_bash.py`, with cwd set to that repo, → rc 0 for each. |
| A-AC7 (registry half) | `revoke.sh <key> --by o` → key `revoke-&lt;target&gt;-&lt;date&gt;[-rN]`, `kind: revocation`, `revokes`, the target's `artifact`, status `Revoked` | PASS | In the e2e test, rc 0, and the last entry is `revoke-order-proj-first-2026-10-22-2026-10-22`, `kind: revocation`, `revokes: order-proj-first-2026-10-22`, `artifact: doc/orders/ORDER-proj-first.md`, `status: Revoked`, with all 5 fields. `status` goes from `order …` to `inactive`. A second `revoke.sh` of the same key → rc 2, and the registry is byte-identical. The `approve-under` and spawn halves are increment 4. |
| A-AC9 | A same-day re-approval gets `k-r2`, then `-r3`. No two new lines share a key. Legacy duplicates are reported as information | PASS | `test_approve_revisions_and_batch`: `approve.sh thing` approves `SPEC-thing.md` and `DESIGN-thing.md` in one batch, giving 2 distinct keys. Reopening the SPEC and running `approve.sh spec-thing` gives `spec-thing-2026-10-22-r2`, then `-r3`, on both the registry line and the document's `Approval:` line. All keys are unique, and `verify_approvals.py` → rc 0 with no duplicate note. A duplicate line appended by hand → rc 0 with `note: legacy duplicate key (last entry wins)`. `test_order_key_revision`: with `order-proj-second-<today>` and `-r2` already in the registry, `delegate.sh --slug second` → `-r3`, also on the document's `Approval:` line. |
| A-AC10 | Every new entry kind has the 5 fields. A probe line without `artifact` is red, and the conforming shape is green | PASS | `test_line_without_artifact_fails_every_key`: after a real approval, `verify_approvals.py` → rc 0. A revocation-shaped line with no `artifact` → rc 1 `missing required field(s): ['artifact']`. With `artifact` added → rc 0. The order and revocation entries in the J-AC1 and A-AC7 rows carry all 5 fields. |
| A-AC6 (c) | The agent running an owner command is refused | PASS | `test_guard_refuses_owner_commands`, 6 spellings × {live order, no opt-in}: `scripts/delegate.sh …`, `bash scripts/revoke.sh …`, `./scripts/delegate.sh …`, `python3 scripts/approve.py --delegate …`, `python3 scripts/approve.py --revoke …` and `scripts/approve.sh thing --by o`. Each → rc 2 `owner-only`. My own shell was refused twice by the same rule during this QA. |
| A-AC8 | No opt-in → unchanged, and `approve.sh &lt;slug&gt;` with no collision behaves as before | PASS | `test_approve_unchanged_without_collision` runs `--list`, then `thing --dry-run`, then `thing --by o` in identical repos on `old` and `new`. The rc, stdout (registry path masked), stderr, both stamped documents, and the registry entries (minus `approved_at`) are all identical. No existing test line was removed (above). For the full suite and exit gate, see Test Run. |
| Post-review: control characters | `--by` and the task refuse control and line-separator characters | PASS | `test_control_characters_refused`: `--by` set to `o\nStatus: Done`, `o\v`, `o` U+2028 `x` or `o` U+0085, and the task set to `a` U+2028 `b`, U+2029, `\f` or `\t`. Each → rc 2 `… contains a control character — write it as plain text on one line`, and nothing is written. Every one of these was accepted on old, or the wrapper was absent there. `test_newline_task_refused_with_spec_message`: `line one\nline two`, `a\r` and `\n` → rc 2 `the task is one line — point to a PRD for more` (AM2-AC5 (d)'s wording). |
| Post-review: verify-fast routing | The new files route to a suite | PASS | `test_verify_fast_routes_new_files`, with `python3` stubbed to echo its arguments. On new, `scripts/delegate.sh`, `scripts/revoke.sh`, `doc/templates/order.md` and `tests/framework/test_delegate.py` each print `== always-human list tests` and `python3 -m pytest tests/framework/ tests/hooks/ -q`. On old, all 4 print only `== lint`/`== tests`. |

### Test Run (increment 3)

```
python3 -m pytest test_qa3_e2e.py -q -p no:cacheprovider   (scratch harness, TREE=new)
64 passed in 22.31s
same harness, TREE=old (red reference)
56 failed, 8 passed in 11.87s   (the 8 are listed under Scope and provenance)

python3 -m pytest tests -q -p no:cacheprovider          (on new, HOME/APPROVAL_LOG at tmp)
2465 passed, 3 skipped in 620.40s (0:10:20)   rc=0

scripts/verify-handoff.sh --status  → not opted in
scripts/verify-full.sh > verify-full.log 2>&1           (on vf = new as a git repo, HOME/APPROVAL_LOG at tmp)
  TODO lint/format/tests  not configured — this step verified NOTHING   (template placeholders, as on HEAD)
  OK   hooks             (261s) 1521 passed in 260.00s (0:04:20)
  OK   ci-examples       (10s) 43 passed in 9.72s
  OK   scar-forge        (1s)
  OK   coordinator       (6s) 174 passed in 5.10s
  OK   framework         (344s) memory: 0 problem(s)
Everything configured passed, and that is ALL this run proves.
verify-full rc=0
```

### Parked (increment 3; outside the criteria or the threat model, or tests could be stronger)

- **Q7 — the files table's `approve.py` "refuses a document with `Approved-under:`" is not built.** `grep -n "Approved-under" scripts/approve.py` → nothing. None of increment 3's criteria requires it. It belongs with increment 4's `approve-under` work. This is for the coordinator to place.
- **Q8 — a tab in the task is refused.** AM2-AC5 (d) refuses only a newline, and hashes the bytes verbatim. A tab is refused here as a control character. That fails closed, and the owner can retype. This is a choice, not a breach.
- **Limits of this run.** A NUL in `--by` or the task cannot be tested, because argv cannot carry it. `approve.sh thing` refused the second round as a whole batch, because `DESIGN-thing.md` was already Approved. That is existing batch-atomic behaviour, so the reopen rounds used the narrower slug `spec-thing`. `verify_approvals.py` does not resolve order documents until increment 4 (J-AC1 row).
- Review Q2–Q6 are still open as the reviewer recorded them. Q1 is settled by Jarvis (exact naming). The review's Low `--by` defect and its verify-fast routing defect are closed (rows above).

## Increment 2 — Log

### Scope and provenance

- Tier 1. The human approved at the brief. Review PASS: doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md (Reviewer-run a10b15a401c97dfa2, Author-run a652078d3d8838f6b). It parked P1–P8.
- Change under test: the uncommitted 8-file diff in worktree `.claude/worktrees/agent-a652078d3d8838f6b`. Its HEAD is d535bfb, and between d535bfb and this branch's HEAD 996c3e4 only the REVIEW file differs. The 8 files are `scripts/autonomy.py`, `scripts/verify-fast.sh`, both `ci-examples/*.yml`, `tests/ci/test_ci_examples.py`, `tests/framework/test_commit_msg_owner_trailer.py`, `tests/hooks/test_guard_always_human.py` and the new `tests/framework/test_decision_log.py`.
- Scratch copies in the QA scratchpad `qaf2-1792678957/`: `old` = `git archive 996c3e4`, and `new` = the same plus the 8 files. `diff -rq old new` shows exactly those 8. Every throwaway repo had `HOME` and `APPROVAL_LOG` pointed at temp dirs, so the real registry was never read or written. Each one used the tree's own `.githooks/commit-msg` through `core.hooksPath`.
- The reviewer's Low defect (the stray whitespace in `entries, _ =verify_approvals.load_registry`) is closed. `grep -n "entries, _ ="` over the worktree's `scripts/autonomy.py` → line 1210 `entries, _ = verify_approvals.load_registry(…)`.

### Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AM2-AC2 (writer) | `log` appends one JSON line, requires 11 fields with no `prev`, exits 2 naming the field, and refuses a run of 13+ digits | PASS | `e2e.sh` in a repo with a live order (`status` → `order order-proj-first-2026-10-22`). Two full entries (`decision`, `approval`) → rc 0. Missing `why` → rc 2 `log: missing field: why`. `why` holding `1234567890123` → rc 2 `log: why: looks like an identifier — describe the shape, not the value`. 12 digits → rc 0. 13 digits in `choice` → rc 2 naming `choice`. 13 Thai digits in `options` → rc 2 naming `options`. Not JSON → rc 2 `the entry is not JSON`. A JSON list → rc 2 `an entry is one JSON object`. Afterwards the log holds exactly the 3 accepted lines (`wc -l` → 3), and `grep -c '"prev"'` → 0. Run from a subdirectory, `log` writes to the repo root's `doc/decisions/decision-log.jsonl`, not under the subdirectory. |
| AM2-AC2 (verify-log) | `verify-log --append-only &lt;base&gt;` exits 1 naming the line on any removed or changed line, and is green on appends at the end. Planted red: edit, delete, swap | PASS | Same repo. After two committed appends: `verify-log --append-only <first log commit>` → rc 0 `only grows at the end`. The tampered commits went in with `--no-verify`, the route the hook does not see. An edited line 1 → rc 1 `line 1 was removed or changed … the decision log is append-only`. Lines 1 and 2 swapped → rc 1, line 1. Line 2 deleted → rc 1, line 2. The whole log deleted → rc 1, line 1. Each was reverted (`git reset --hard`), and the check was green again → rc 0. `nosuchref` → rc 2 `is not a commit` (fails closed). |
| AM2-AC2 (CI) | The same command runs as a step in both `ci-examples/*.yml`, identically | PASS | I extracted the gate-6 script from each YAML, from the `run: \|` / `- script: \|` line down to the `verify-log` line, and stripped the indent. `diff` → identical, 5 lines. I ran the GitHub script itself in the throwaway repo, with a bare `origin` whose `main` held the first log commit and then moved on by an unrelated commit. With `GITHUB_BASE_REF=main`, an append-only PR → rc 0, with the merge-base as the base. A PR editing line 1 → rc 1 naming line 1. A PR swapping lines → rc 1. Azure spelling (`GITHUB_BASE_REF` unset, `SYSTEM_PULLREQUEST_TARGETBRANCH=refs/heads/main`) → rc 0 on the append-only PR. |
| F-AC2 | `approval`/`decision`/`provisional`/`merge` with a `reverse` outside the one-action grammar → exit 2 `reverse: missing or not one action` | PASS | `approval` `revert abc1234; rm -rf x` → rc 2. `merge` `git revert HEAD` → rc 2. `provisional` `delete branch wip/x and revert abc1234` → rc 2. `approval` with `reverse: null` → rc 2. `decision` `none:   ` (blank reason) → rc 2. Each message is `log: reverse: missing or not one action`. Accepted: `none: nothing applied yet`, `revert abc1234`, `delete branch wip/y` (on a `merge`), `restore doc/a.md from abc1234` and `remove stamp doc/specs/SPEC-x.md` → rc 0. |
| AM2-AC3 (a) | Under autonomy, a log commit that only appends needs no trailer (a new file counts). Any other change is refused, naming AH5 and the path | PASS | Live order, real `git commit` through `.githooks/commit-msg`, no trailer. New log → rc 0. Append → rc 0. Append plus an unprotected `README.md` → rc 0. Refused with rc 1 `check-commit: always-human item AH5: doc/decisions/decision-log.jsonl is protected while autonomy is active`: an edited line 1, the same edit with `Owner-Approved: order-proj-first-2026-10-22` (`a mandate or order key never counts`), swapped lines 1 and 2, a line inserted before the end, and deleting the log. Red on old: the same live-order repo on `old`, with a new hand-written log and no trailer → refused with the same AH5 line. |
| AM2-AC8 (`log`, `verify-log`) | Under an order, `guard_bash.py` allows `autonomy.py log`/`verify-log`. An undefined subcommand stays AH5 | PASS | Guard payloads, cwd = the live-order repo. On new, `python3 scripts/autonomy.py log --entry '{}'` → 0 and `python3 -I scripts/autonomy.py verify-log --append-only main` → 0. `grant x`, `close-order k` and `approve-under doc/specs/SPEC-x.md` → 2 `always-human item AH5 — matched: autonomy.py <sub>`; those wait for later increments. Red on old: `log` and `verify-log` → 2 AH5. |
| A-AC8 | No live autonomy → nothing changes | PASS | `aac8.sh`: no `scripts/autonomy.json` and an empty registry, run on old and new. A hand-written log, then a new-log commit, an edit, a swap and a delete. Old and new give identical results: every commit rc 0, `status` → `inactive`, and the guard allows `git commit -m x`, `git push origin main`, `git merge feature/x` and `autonomy.py log …` (rc 0) on both. On new without autonomy, `log` and `verify-log` work the same as under the order (`e2e.sh … none`), and the guard allows `grant`/`close-order`/`approve-under` as before. The full suite and the exit gate are green (Test Run). |

### Test Run (increment 2)

```
python3 -m pytest tests -q -p no:cacheprovider          (on new)
2365 passed, 3 skipped in 530.27s (0:08:50)   rc=0

scripts/verify-handoff.sh --status  → not opted in
scripts/verify-full.sh > verify-full.log 2>&1           (on new, made a git repo for the run)
  TODO lint/format/tests  not configured — this step verified NOTHING   (template placeholders, as on HEAD)
  OK   hooks             (249s) 1489 passed in 248.82s (0:04:08)
  OK   ci-examples       (9s) 43 passed in 8.32s
  OK   scar-forge        (1s)
  OK   coordinator       (10s) 174 passed in 4.94s
  OK   framework         (260s) memory: 0 problem(s)
Everything configured passed, and that is ALL this run proves.
verify-full rc=0
```

### Edge Cases Probed (beyond the table)

- The `none` e2e run on new looked like a refusal on "edit with the order key trailer" (rc 1). It is not one: `git log` shows the edit was already committed as `de4b1a0 chore: edit` one step earlier, so there was nothing to commit. Inactive behaviour is judged by `aac8.sh` only.
- On old, `e2e.sh` writes nothing, because argparse rejects `log`/`verify-log` (`usage: … {items,status,check-commit}`, rc 2). So old's gate-6 rows say nothing either way. They are not counted as evidence.

### Parked (increment 2; outside the threat model or tests could be stronger)

- **Q5 — one problem hides the others.** `log_problems` returns early on the `reverse` problem. `{"kind":"approval","reverse":"bad"}` → rc 2 naming only `reverse: missing or not one action`, not the 9 missing fields. It still exits 2 on an entry that lacks fields, so AM2-AC2 is met. Only the diagnostic is incomplete.
- **Q6 — empty strings count as present.** `why: ""` → rc 0. This repeats reviewer P2.
- **Q7 — `log` trusts the file to end with a newline.** `append_log` opens in append mode and writes `json + "\n"`. A hand-edited log without a final newline would get the new entry glued onto its last line. Every line `log` writes ends in a newline, and a glued line is caught as a change by `verify-log` and the commit carve-out. Not probed further.
- Reviewer P1, P3, P4, P5, P6, P7 and P8 are unchanged, and I saw nothing that moves them into scope.

## Increment 1 — F1

### Scope and provenance

- Tier 1. The human approved at the brief. Review PASS: doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md (Reviewer-run a0705137a137aecbc, Author-run ab74ef54c3710742d).
- Change under test: the uncommitted 3-file diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d` over HEAD b50406e. The files are `.claude/hooks/guard_bash.py`, `scripts/autonomy.py` (new `protected_commit`) and `tests/hooks/test_guard_always_human.py` (additions only). `git status --short` in the worktree shows exactly these 3 files.
- Every run below used scratch copies in the QA scratchpad `qaf1-1792671252/`. `old` is `git archive b50406e`. `new` is the same plus the 3 files, and `diff -rq old new` shows exactly those 3 files. Throwaway repos had `HOME` and `APPROVAL_LOG` pointed at temp dirs, so the real registry was never read or written.
- Criteria under test: F-AC1, commit half only (SPEC-delegated-autonomy.md line 106, narrowed by am2's increment plan row 1 to `guard_bash.py` only). A-AC8, guard half only (line 121).

### Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| F-AC1 (commit half) | Autonomy active and current branch protected (`main`, `master`, project list) → agent `git commit …` refused with `work under autonomy happens on a branch or worktree`. On `feature/x` it is allowed. `guard_bash.py` only | **FAIL** | Probe `probe.py` fed `git commit -m x` payloads to the old and new guards across 31 scenarios (state × branch). With a live mandate, order or absence on `main`, `master` and listed `release`: old=0, new=2 `rule F-AC1` (9/9). On `feature/x` under each: new=0 (3/3). The message contains the required phrase (`… — work under autonomy happens on a branch or worktree`). **Fails on two cases (Defects 1, 2):** unborn `main` → new=0; `cd <wip worktree> && git commit` from a `main` cwd → new=2. |
| A-AC8 (guard half) | No live autonomy → nothing changes | PASS | Wide probe: 12 commands × 31 scenarios, 372 rows (`probe-wide.log`). Every row where old ≠ new is an *active* state (mandate, order or absence) on a protected branch with a `git commit` command. The inactive states show old = new on every command, including `git commit`, `git merge`, `git push origin main`, `scripts/approve.sh`, `rm -rf data` and `git reset --hard`. Those states are: opted in with an empty registry, revoked order, expired order, ended absence, and never opted in with a live mandate, order or absence. The existing tests are unchanged: `diff old new` on the test file shows 0 removed lines. `python3 -m pytest tests/hooks tests/ci -q` on `new` → all pass (see Test Run). |
| Red-first | New refusal tests red on the old code | PASS | The author's test file on `old`: `12 failed, 84 passed in 16.58s`. The 12 failures are exactly `test_a_commit_on_a_protected_branch_is_refused_under_autonomy[*]`. |
| commit-msg untouched; owner commit on `main` | Rule not added to `check_commit` (am2 increment plan row 1) | PASS | `cmp` of `.githooks/commit-msg` and `.githooks/pre-commit` old vs new → identical. The `scripts/autonomy.py` diff has 0 removed lines. Script `owner.sh` used a real repo on `main`, `status` = `order order-proj-a-2026-10-22`, and `core.hooksPath` pointing to a dir holding only `.githooks/commit-msg`. Old and new gave the same results: owner commit on `main` rc=0, commit on `feature/y` rc=0, owner `git merge --no-ff feature/y` into `main` rc=0. |

### Test Run

```
python3 -m pytest tests -q -p no:cacheprovider        (on new)
2198 passed, 3 skipped in 442.97s (0:07:22)   rc=0

python3 -m pytest tests/hooks tests/ci -q -p no:cacheprovider   (on new)
1499 passed in 265.56s (0:04:25)   rc=0

scripts/verify-full.sh > verify-full.log 2>&1         (on new, made a git repo for the run)
OK hooks 1463 passed · OK ci-examples 36 passed · OK scar-forge · OK coordinator 174 passed · OK framework
lint/format/tests: template TODO placeholders ("this step verified NOTHING"), as on HEAD
"Everything configured passed, and that is ALL this run proves."   verify-full rc=0
```

The suite is green. The FAIL comes from two cases that no test covers (Defects below).

### Edge Cases Probed (new guard, live order, `main` unless stated)

- Refused (rc 2, F-AC1), correctly:
  - `git commit -m x` from a subdirectory
  - `git commit -F -` fed by a heredoc
  - newline-separated `git status⏎git commit -m x`
  - `true | git commit -m x`
  - `git commit -m x &`
  - `echo $(git commit -m x)`
  - `echo -m | xargs git commit`
  - `GIT_DIR=.git git commit -m x`
  - `git commit --amend --no-edit`
  - `git add . && git commit -m x`
- Refused, harmlessly: `git commit --dry-run` (writes nothing). See Parked Q3.
- Allowed, correctly:
  - `echo "git commit -m x"`
  - `git config alias.ci commit`
  - detached HEAD at `main`'s commit (no branch moves)
  - a `wip/x` worktree of a `main` repo when the hook's cwd is that worktree
  - outside any repo
- Malformed payloads exit 0 on both old and new:
  - empty input
  - `not json`
  - no `tool_input`
  - `command` set to null or to 123
  - `tool_name: Write`

  This matches the guard's stated policy ("Malformed input exits 0").
- Allowed, not caught (rc 0, old = new = 0), spellings outside F-AC1's wording, Parked:
  - `git cherry-pick HEAD`
  - `git revert --no-edit HEAD`
  - `git commit-tree`
  - `bash -c 'git commit -m x'`
- **Unborn `main`** (`git init -b main`, `scripts/autonomy.json` on disk, no commits): `autonomy.py status` → `order order-proj-a-2026-10-22`. `git symbolic-ref --short HEAD` → `main`. `git rev-parse --abbrev-ref HEAD` → rc 128. Guard result: `git commit -m x` → **rc 0**. → Defect 1.
- **Branch is read from the hook's cwd, not from where the commit lands.**
  - Hook cwd on `main`:
    - `cd <wip/x worktree> && git commit -m x` → **rc 2 F-AC1**. → Defect 2.
    - `git -C <wip/x worktree> commit -m x` → **rc 2 F-AC1**. → Defect 2.
  - Hook cwd on `feature/x`:
    - `cd <main repo> && git commit -m x` → rc 0.
    - `git -C <main repo> commit -m x` → rc 0.
    - `git switch main && git commit -m x` → rc 0.
    - `git checkout main; git commit -m x` → rc 0.

    These are Parked under Q1.

### Parked (outside increment 1's criteria or the declared threat model; for the coordinator)

- **Q1 — same root as Defect 2, the evasion direction.** The guard reads the hook's cwd branch. A command that changes the target, via `cd X &&`, `git -C X` or `git switch main && git commit`, commits on `main` with rc 0. `switch main && commit` and `cherry-pick`/`revert` (reviewer P1) are the forms an agent could reach by plain mistake. The brief declares other shell spellings a limit, so these are Parked, not FAIL. A fix for Defect 2 that resolves the target directory would also close the `cd`/`-C` forms.
- **Q2 — absence is not pinned by a test** (same as reviewer P2). The behaviour is right: the probe gives `main` + absence → rc 2 F-AC1. Nothing in `tests/` covers it. QA's `Files:` covers only this report, so no test was added.
- **Q3 — `git commit --dry-run` is refused** on a protected branch under autonomy. It is a false refusal of a read-only form, but harmless.
- **Q4 — the owner check ran through `commit-msg` only.** `pre-commit` fails the same way on old and new in a fresh copy of the framework, because 16 framework docs carry `Approval:` keys that the temp registry lacks. That is unrelated to F1.

### Defects

See the top-level `## Defects` table below (rows tagged "Inc. 1").

## Increment 1 — F1, re-test 2

### Scope and provenance

- Tier 1, re-test after rework. Review PASS at round 3 (commit db71dda; doc/qa/REVIEW-delegated-autonomy-am2-task-orders-scope.md). The brief was dispatched under the tier-1 approval at the brief. This QA run did not see the human approval itself.
- Change under test: the uncommitted 3-file diff in worktree `.claude/worktrees/agent-ab74ef54c3710742d`, over this branch's HEAD db71dda. The worktree is based on b50406e, and HEAD differs from it only in `doc/qa/`. The files are `.claude/hooks/guard_bash.py` (unchanged since round 1), `scripts/autonomy.py` (`protected_commit` now follows `cd`/`-C` and `( )` scope, and `current_branch` falls back to `symbolic-ref`), and `tests/hooks/test_guard_always_human.py` (additions only, 0 removed lines). `git status --short` in the worktree shows exactly these 3 files.
- Scratch copies are in the QA scratchpad `qaf1r2-1792674955/`. `old` is `git archive HEAD`. `new` is the same plus the 3 files, and `diff -rq old new` shows exactly those 3 files. Every probe pointed `HOME` and `APPROVAL_LOG` at temp dirs, so the real registry was never read or written. The author's worktree was only read.
- `scripts/verify-handoff.sh --status` → `not opted in`, so `scripts/verify-full.sh` is the exit gate.

### Criteria Results (re-test 2)

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| Defect "worktree from a `main` cwd" (first run, Medium) | A commit that lands on a working branch is allowed | PASS (closed) | `tools/hostile.sh` (the first run's repro script, re-run as is) with the hook cwd on `main` and a live order, old/new rc: `cd WT && git commit -m x` 0/**0** · `git -C WT commit -m x` 0/**0** (first run: new=2). `tools/cdcases.sh`, new rc 0: `cd WT; git commit` · `(cd WT && git commit)` · relative `cd ../a-wt` and `git -C ../a-wt` · `cd -- WT` · a quoted worktree path with a space · `cd WT && git add . && git commit` · `cd WT && git commit --amend --no-edit` · `pushd WT && git commit`. |
| Defect "unborn `main`" (first run, Low) | Unborn `main` + live autonomy → `git commit` refused | PASS (closed) | `hostile.sh`, unborn `main` with a live order: old=0, new=**2 rule F-AC1** (first run: new=0). `tools/unborn.py`, 112 rows (unborn `main` and `feature/x` × opted in or not × 7 registry states × 4 commands): `git commit -m x` is new=2 F-AC1 under mandate, order and absence on `main`, and 0 on unborn `feature/x`. |
| F-AC1 refused half (reverse direction and regression) | Every commit that lands on a protected branch under autonomy is refused | PASS | Hook cwd on `feature/x`, new rc 2 F-AC1: `cd MAIN && git commit` · `git -C MAIN commit` · `cd ../a && git commit` · `git -c core.x=1 -C MAIN commit` · `git --no-pager -C MAIN commit` · `(cd MAIN && git commit)` · `cd WT && git commit && cd MAIN && git commit -m y`. Hook cwd on `main`, new rc 2 F-AC1: `cd /missing && git commit` · `(cd WT) && git commit` · `git -C /missing commit` · `cd sub && git commit` · `git commit -m x; cd WT`. The first run's 10 refused spellings (subdir, heredoc, newline, pipe, `&`, `$( )`, xargs, `GIT_DIR=`, `--amend`, `add &&`) all still give new=2. `tools/probe.py`, 31 scenarios: `git commit` on `main`/`master`/listed `release` under mandate, order or absence → new=2 (9/9). On `feature/x` → 0. |
| A-AC8 (guard half) | No live autonomy → nothing changes | PASS | `probe.py`, 8 commands × 31 scenarios = 248 rows (`probe-wide.log`): 18 rows differ, and every one is an *active* state on a protected branch running `git commit -m x` or `cd .. && git commit -m x`. In every inactive state (empty registry, revoked order, expired order, ended absence, and never opted in with a mandate, order or absence), old = new on all 8 commands. `unborn.py`: the inactive states on unborn repos give old = new on all rows. |
| Owner commit path untouched | `commit-msg`/`pre-commit` unchanged; owner commit and merge on `main` still work | PASS | `cmp` of `.githooks/commit-msg` and `.githooks/pre-commit` old vs new → identical. `tools/owner.sh`, real repo on `main`, status `order order-proj-a-2026-10-22`, old and new: owner commit on `main` rc=0, commit on `feature/y` rc=0, owner `git merge --no-ff feature/y` into `main` rc=0. |
| Red-first | New tests red on the code without the fix | PASS | The new test file on `old`: `25 failed, 89 passed in 21.26s`. The failures include `test_a_commit_on_an_unborn_main_is_refused_under_autonomy`, both `test_a_commit_aimed_at_main_from_a_worktree_is_refused[*]`, the 6 `test_a_commit_that_does_not_land_in_the_worktree_is_judged_on_main[*]` and `test_a_failed_cd_does_not_move_a_relative_git_dash_c`. The worktree-allowed tests pass on `old`, as they should: `old` allowed everything. |

### Test Run (re-test 2)

```
python3 -m pytest tests -q -p no:cacheprovider         (on new)
2216 passed, 3 skipped in 441.86s (0:07:21)   rc=0

scripts/verify-full.sh > verify-full.log 2>&1          (on new, made a git repo for the run)
  TODO lint/format/tests   not configured — this step verified NOTHING   (template placeholders, as on HEAD)
  OK   hooks             (258s) 1481 passed in 257.12s (0:04:17)
  OK   ci-examples       (10s) 36 passed in 5.87s
  OK   scar-forge
  OK   coordinator       (4s) 174 passed in 4.46s
  OK   framework         (157s) memory: 0 problem(s)
Everything configured passed, and that is ALL this run proves.
verify-full rc=0
```

### Observations (no action)

- **The unborn-branch fallback also tightens AH3.** On an unborn `main` under a live mandate, order or absence, `git merge feature/x` goes from old=0 to new=2 AH3, because `current_branch` now returns `main`. That is the safe direction, only under active autonomy, and the inactive rows are unchanged. The round-3 review noted it too.
- **An unreadable target is judged as the starting cwd.** For example, `cd` with no argument (to `$HOME`), `cd .. && git commit` out of the repo, or `git -C WT -C .. commit` from a `main` cwd → rc 2. Git would fail in a non-repo anyway. This is the docstring's stated safe-direction rule.

### Parked (re-test 2; declared limits or outside F-AC1's wording)

- First run's Q1 evasion forms that are still allowed: `git switch main && git commit` and `git checkout main; git commit` from a `feature/x` cwd → 0. `cherry-pick`, `revert`, `commit-tree` and `bash -c '…'` → 0. The `cd`/`-C` forms of Q1 are now refused.
- `cd -` and `pushd`/`popd` stacks are declared limits. `cd WT && cd - && git commit` from `main` → 2, but only by accident: `cd -` is read as `$HOME`. This matches reviewer R1/R2.
- Q2 (absence not pinned) is closed: the new `absence-main` rows are in the test file. Q3 (`--dry-run` refused) and Q4 (owner check through `commit-msg` only) are unchanged.

## Defects

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Medium | Inc. 1, F-AC1 allowed half. The guard refuses a commit that lands on a working branch when the hook's cwd is on `main`. This hits both `cd <worktree on wip/x> && git commit -m x` and `git -C <worktree on wip/x> commit -m x`: rc 2 `rule F-AC1`. Following the refusal's own advice ("or a worktree, and commit there") from a session whose cwd is the `main` checkout is therefore refused again. Repro: repo `a` on `main` with a live order, `git worktree add -b wip/x ../a-wt`, then feed `cd ../a-wt && git commit -m x` with cwd `a`. Fixing it means resolving the commit's target directory (`cd`/`-C`) before reading the branch, which also closes Parked Q1's `cd`/`-C` forms. | scripts/autonomy.py `protected_commit`; .claude/hooks/guard_bash.py `_apply_core` (`branch = autonomy.current_branch(cwd)`) | ai-engineer | `missed-ac` |
| Low | Inc. 1, F-AC1 refused half. Under live autonomy, an agent's `git commit` on an unborn `main` (no commits yet) is allowed and creates `main`. `autonomy.current_branch` uses `git rev-parse --abbrev-ref HEAD`, which exits 128 on an unborn branch, so it returns None and `protected_commit` returns None. Repro: `git init -b main`, write `scripts/autonomy.json` `{"project":"proj"}`, live `order-proj-…` in `APPROVAL_LOG`, feed `git commit -m x` → rc 0 (status prints the order as active). `git symbolic-ref --short HEAD` prints `main` and would serve as a fallback. | scripts/autonomy.py `current_branch` (line ~925) | ai-engineer | `missed-ac` |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

Both rows above are from the first increment-1 run (commit 17ce083). Both are closed in re-test 2. They stay here as the rework record.

## Approval history

- **2026-10-22 — drafted (increment 1, F1).** QA run, from the spec, the review, and the author's uncommitted 3-file diff in worktree agent-ab74ef54c3710742d, with every command run on scratch copies. FAIL: 2 defects (`missed-ac`), 3 of 4 rows PASS.
- **2026-10-22 — re-test 2 (increment 1, F1).** Re-ran the first run's repros and extra `cd`/`-C`/unborn probes on scratch copies of HEAD db71dda plus the reworked 3-file diff (review round 3 PASS). PASS: both defects closed, the reverse direction refused, A-AC8 unchanged, owner commit path unchanged. Full pytest and `scripts/verify-full.sh` rc=0.
- **2026-10-22 — increment 2 (Log).** Verified the author's uncommitted 8-file diff (worktree agent-a652078d3d8838f6b, review PASS) on scratch copies of HEAD 996c3e4 plus the 8 files. Tested end to end in throwaway repos, with and without a live order, against the old tree as a red-first reference. PASS: AM2-AC2, F-AC2, AM2-AC3 (a), AM2-AC8 (`log`, `verify-log`) and A-AC8, with no defects. Full pytest `2365 passed, 3 skipped` and `scripts/verify-full.sh` rc=0.
- **2026-10-22 — increment 3 (Registry and owner commands).** Verified the author's 12 uncommitted files (worktree agent-a302faca16121a04e, review PASS, plus the post-review control-character and verify-fast fixes) on scratch copies of HEAD 9e00765 plus the 12 files. A 64-case scratch harness drove the real wrappers and `commit-msg` in throwaway repos: 64 passed on new, and 56 failed on old. PASS: A-AC10, A-AC9, J-AC1, J-AC2, AM2-AC3 (b), AM2-AC7, A-AC7 (registry half), A-AC6 (c) and A-AC8, with no defects. Full pytest `2465 passed, 3 skipped` and `scripts/verify-full.sh` rc=0.
