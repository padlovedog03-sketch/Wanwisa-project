# Review: Delegated autonomy, increment B (always-human guards) under amendment am1

Status: In Review
Owner: reviewer
Upstream: doc/specs/SPEC-delegated-autonomy-am1-guards-catch-accidents.md
Author-run: 8cccea4
Reviewer-run: a4adf404e56f3fe84
Date: 2026-10-22

Verdict: PASS

Every criterion that am1 rewrote or added (B-AC2, B-AC4, B-AC6, B-AC7, B-AC10) holds at HEAD. Each was re-run in this review, the new tests were shown red against the pre-amendment `9976550`, and the exit gate `scripts/verify-full.sh` is green (rc=0).

## Read from

- Upstream: `doc/specs/SPEC-delegated-autonomy-am1-guards-catch-accidents.md` (Approved, key `spec-delegated-autonomy-am1-guards-catch-accidents-2026-10-20`), which amends `doc/specs/SPEC-delegated-autonomy.md` Part B.
- Change: squash `8cccea4` ("feat: always-human list and its guards (delegated-autonomy increment B)"), an ancestor of main-tree HEAD on `feat/top3-tiers-mechanisms-deny` (`git merge-base --is-ancestor 8cccea4 HEAD` → true). HEAD was `ef1f717` when the review started and `0fd71b6` at the final gate run. `git show --stat 0fd71b6` shows that commit touches only `doc/memory/` and `doc/qa/` files, so no increment-B file changed between the two. Code reviewed at HEAD: `scripts/autonomy.py`, `.claude/hooks/guard_bash.py`, `.claude/hooks/guard_autonomy_paths.py`, `.githooks/commit-msg`, `doc/framework/ADAPTERS.md`, and the B test files.
- Not read: the author's conversation. The commit message's claims were re-run here, not relayed.

## Criteria Review

| # | Criterion (as amended by am1) | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| B-AC2 | `classify_command` returns AH3 for the design table, for the round-1 pins and for the canonical command behind the 14 listed wrappers. It returns `[]` for the five allow cases. | PASS | `python3 scratchpad/cls.py`, which imports `scripts/autonomy.py`: `{env,exec,nohup,time,sudo,doas,command,builtin,nice,timeout 5,stdbuf -oL,xargs,source,.} git push origin main` → `['AH3']` each. `git push origin HEAD:main`, `+main` and `-f origin main` → `['AH3']`. The allow cases `git push origin feature/x`, `grep -rn 'git push origin main' doc/`, `curl -s https://example.test/x`, a heredoc that mentions the push, and `python3 -m pytest` → `[]`. The 24 round-1 pins are in `python3 -m pytest tests/hooks/test_autonomy_stdlib_shadowing.py tests/hooks/test_regression_always_human_bypasses.py -q -p no:cacheprovider` → `39 passed`. |
| B-AC4 | `owner-only command` (exit 2) in every project for the 11 approved invocations, for owner scripts in a non-reader argv, and when the core cannot be imported. `--list` stays allowed. | PASS | Guard probe `scratchpad/probe.py` (the `guard_bash.py` hook fed a Bash payload in a throwaway repo, plain and with a live mandate, `APPROVAL_LOG` set to a temp file): all 11 approved invocations → `2` in both projects. `env`, `timeout 5` and `xargs` before `scripts/approve.sh` → `2`. `scripts//approve.sh` and `./scripts/./approve.sh` → `2`. `scripts/approve.sh --list` → `0`. The shadowing guarantee rests on the committed tests, which copy the hooks and the core into the test repo next to the planted module. `python3 -m pytest tests/hooks/test_autonomy_stdlib_shadowing.py <the two shadow pins in test_regression_autonomy_rework_bypasses.py> tests/framework/test_regression_commit_msg_autonomy.py -q -p no:cacheprovider` → `19 passed`. The first shadowing test is a no-shadow control. (My own `scratchpad/shadow.py` probe did not test shadowing: the hooks load the core from their own repo, `guard_autonomy_paths.py:43`, so a module planted in a separate temp repo was never on their import path. I do not count it as evidence.) |
| B-AC6 | With autonomy active, a shell write to a protected path through a redirect, `tee`, `sed -i`, `cp`, `mv` or `rm` is refused naming AH5. Both guards keep working when a `scripts/` stdlib shadow raises on import. | PASS | Probe, live mandate: `echo x > .claude/settings.json`, `>>`, `echo x>.claude/…`, `./.claude/…`, `.CLAUDE/…`, `sed -i '' s/a/b/ scripts/autonomy.json`, `cp x doc/mandates/M.md`, `tee doc/mandates/M.md`, `mv doc/mandates/M.md /tmp/x`, `rm doc/mandates/M.md` and `rm -f scripts/autonomy.json` → `2` each. The same commands in a plain project → `0` (R6). Shadowing: `test_autonomy_stdlib_shadowing.py` collects 15 tests (`--collect-only`), including AH3 and the path guard under `dataclasses` and `datetime` shadows. The two `shlex` shadow pins cover AH3 and the path guard. All are in the `19 passed` run under B-AC4. |
| B-AC7 | The check runs in `.githooks/commit-msg` under `python3 -I`. The opt-in carve-out clears only `scripts/autonomy.json` and the trailer entry's own `artifact` (AM1-ADR-3). An `argparse.py` shim does not switch it off. | PASS | `grep -n "python3 -I" .githooks/commit-msg` → line 17, `python3 -I scripts/autonomy.py check-commit --message-file "$1"`. The AM1-ADR-3 cases `test_the_opt_in_clears_the_project_file_and_its_own_mandate_document` and `test_the_opt_in_does_not_clear_another_protected_path_it_adds[ORDER-self, MANDATE-wide, release.sh, post-checkout]` are green at HEAD (333-pass run below). The four refusal cases are **red at `9976550`** (red-first run below). The `test_regression_deleting_the_project_file_needs_an_owner_trailer` fixture is now split into an install commit and an opt-in commit, as the spec asked (lines 52-56), and its assertion is unchanged. `test_regression_a_shadow_module_cannot_switch_the_commit_check_off` (an `argparse.py` shim) is green. |
| B-AC10 | Read-only uses that name an owner script are allowed in plain and active projects. The hostile neighbours stay refused. | PASS | Probe, both projects: all 9 allowed commands → `0`. All 8 hostile neighbours, plus `-okdir`, `-delete`, `bash -x scripts/approve.sh x`, `python3 -m pdb scripts/approve.py x` and `py_compile …; python3 scripts/approve.py x` → `2` with `owner-only command`. **Red-first:** I copied HEAD's test files into `git archive 9976550` and ran `python3 -m pytest tests/hooks/test_guard_always_human.py tests/framework/test_commit_msg_owner_trailer.py tests/hooks/test_regression_autonomy_rework_bypasses.py tests/framework/test_doc_contract_always_human_limits.py -q -p no:cacheprovider` → `26 failed, 70 passed`. The failures are the 18 B-AC10 cases (9 commands × 2 projects), the 3 kept rework pins, the 4 AM1-ADR-3 cases and the doc contract. |
| am1: retired pins | The 17 pins are deleted, the 3 B-AC10 pins and the 2 shadow pins are kept, and the docstring points at am1. | PASS | `pytest tests/hooks/test_regression_autonomy_rework_bypasses.py --collect-only -q` → exactly 5: two `shadow_module` pins and three `reading_an_owner_script_stays_allowed` pins. The docstring (lines 1-17) names the amendment and its §Declared limits. |
| am1: ADAPTERS.md | The limits paragraph is replaced with the spec's Thai text. | PASS | I diffed spec lines 183-196 against `doc/framework/ADAPTERS.md` lines 102-115. The only difference is one trailing blank line. `grep -c "ข้อจำกัดที่พูดตรง" doc/framework/ADAPTERS.md` → `0`, so the old paragraph is gone. The doc contract test is green at HEAD and red at `9976550`. |
| Suites | The spec's "must stay green" list, plus the tests the brief names | PASS | `python3 -m pytest tests/hooks -q -p no:cacheprovider` (unfiltered) → `1303 passed in 236.24s`. The B files plus the rework files, the doc contract and `test_neutrality.py` → `333 passed in 72.83s`. |

### Exit gate

First run: `scripts/verify-full.sh` → `EXIT GATE RED (exit 1)`. The only failing step was `FAIL ci-examples`, with two tests failing:
- `test_gate_3_is_green_after_bootstrap_runs`
- `test_gate_3_ignores_an_agent_worktree_under_dot_claude`

Both were tripped by a review file another agent had left untracked, `doc/qa/REVIEW-verify-tiers-G-polling.md`. No increment-B file was named. Commit `0fd71b6` then fixed that file.

Second run, at `0fd71b6`, with only this review untracked: `scripts/verify-full.sh` → `rc=0`. Each step:
- `OK hooks`: `1303 passed`
- `OK ci-examples`: `30 passed`
- `OK coordinator`: `155 passed`
- `OK framework`
- `OK scar-forge`

The gate also printed `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. That is the template's stated limit, not a B issue. The run record is `.verify/runs/20261022T075639Z-87289/record.json`.

## Defects (if FAIL)

None.

## Hostile inputs tried

- `scripts/approve.sh --by a -- spec-x --help`, the same with `-h`, and the same with `-n` → `0` in both projects. Here is why, from the code:
  - The read-only-flag check in `_owner_script` (`scripts/autonomy.py:644`) finds a flag anywhere after the script word, even past a `--`.
  - After `--`, argparse treats those words as slugs (`approve.py:287`, `nargs="*"`).
  - `find_documents` matches each slug as a case-insensitive substring of tracked filenames (`approve.py:175-179`).
  - `approve.py` validates the whole batch first, and it writes nothing if any slug matches no document or a document that cannot be approved (`approve.py:320-342`).

  So `--help` almost certainly aborts, because no filename contains it. A forged approval is possible only through `-h` or `-n`, and only when every tracked document whose filename contains that substring is itself approvable. `-n` was already in `READ_ONLY_FLAGS` at `9976550` (`git show 9976550:scripts/autonomy.py` → line 91, `{"--list", "--dry-run", "-n"}`), so that route predates am1. am1 widened it with `-h` and `--help`.

  I could not run this end to end. `guard_bash.py` refused my own scratch run of `approve.sh` with `owner-only command`, as it should, and I did not route around it. This finding is `[INFERRED]` from the code. It is a deliberate spelling, so it is Parked.
- `SCRIPTS/APPROVE.SH x --by a` → `0`. On a case-insensitive volume this runs the owner script. This is a shell spelling, so it is Parked.
- `bash scripts/approve.sh -n x` → `0`. Here `-n` reaches `approve.py` as `--dry-run`, so nothing is written and the result is correct.
- `bash -n -c '…approve.sh…'` → `0`. `bash -n` executes nothing, so this is correct.
- `sort -o out scripts/approve.sh` → `0`. It reads the script and writes elsewhere, so this is correct.
- `nl scripts/approve.sh | sh` → `0`. A pipe into a shell is a limit the approved design already declares (§B.4).
- I checked that `--help` and `-n` do not leak into always-human items. With a live mandate, `git push origin main --help`, `scripts/deploy.sh prod --help`, `scripts/deploy.sh prod -n`, `cloudctl buy --help` and `rm -rf data --help` → `2` each. `READ_ONLY_FLAGS` applies only inside `_owner_script`.
- I checked whitespace and path variants: leading or doubled spaces, `scripts//`, `./scripts/./`, and `.CLAUDE/settings.json` (case-folded) → refused.

## Parked (outside the threat model or outside the ACs; not FAIL)

- **Proposed LIMIT line for ADAPTERS.md (owner decision):** a read-only flag after `--` (`scripts/approve.sh --by a -- <slug> -n|-h`). The guard lets it through, and `approve.py` reads those words as slugs. It writes only if every document whose filename contains that substring is approvable. The am1 rationale "Why `--help` is safe anywhere in the argv" does not hold past `--`. The `-n` route predates am1; `-h` and `--help` are new with am1. There are two options:
  - (a) declare it as a new D-L line;
  - (b) a one-line fix: stop the `READ_ONLY_FLAGS` search at a `--` token.

  Changing the declared-limits list is the owner's decision.
- **Proposed LIMIT line:** owner-script names with different case (`SCRIPTS/APPROVE.SH`) on case-insensitive volumes. The registry-path check already case-folds, but the owner-script basename check does not.
- **Stale record:** `doc/qa/QA-delegated-autonomy-B.md` still says `Verdict: FAIL` (lines 13 and 150) and never mentions am1. The spec's file table gives qa the job of adding the "re-test 2" note. That belongs to the QA step that follows this review, not to the author.
- **File placement (Low):** the spec put the doc-contract case in the shared `tests/framework/test_doc_contracts.py`. It landed as its own file, `tests/framework/test_doc_contract_always_human_limits.py`. It covers the same ten limit classes and the read-only line. The spec's merge-order note for the shared file no longer applies.

## Approval history

- **2026-10-22 — drafted.** Written by the reviewer (run `a998e45d25322f524`) from the am1 spec, squash `8cccea4` at main-tree HEAD `ef1f717` then `0fd71b6`, and the commands above. The author's conversation was not read.
