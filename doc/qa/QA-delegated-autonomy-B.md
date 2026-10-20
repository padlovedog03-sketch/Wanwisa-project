# QA Report: Delegated autonomy, increment B (always-human list and its guards)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-delegated-autonomy.md
Date: 2026-10-20

Commit under test: `9670f32` on `worktree-agent-aa8662140b00eeca3`. Design reference: `doc/architecture/DESIGN-delegated-autonomy.md` §B.1–§B.4.
Provenance: the brief cites the owner's lean-gates ruling (`doc/memory/lean-gates-risk-based-qa.md`), which routes guard code to full QA with no owner pre-review. That file exists in the main tree but is **untracked** (`?? doc/memory/lean-gates-risk-based-qa.md`; `INDEX.md` modified, uncommitted), and it is absent from this worktree. QA could not confirm from committed records that the implementation needed no human approval. This is recorded, not ruled on.

Rework causes use the SPEC-verify-tiers H-AC4 list (`missed-ac`, `regression`, `spec-defect`, `test-gap`, `env-flaky`). `doc/templates/qa-report.md` does not carry that list yet.

## Verdict: FAIL

Four criteria fail (B-AC2, B-AC4, B-AC6, B-AC7). The worst finding: one ordinary command, `mv scripts/autonomy.json <elsewhere>` or `git rm scripts/autonomy.json`, is allowed under an active mandate. It flips `status` to `inactive`, which switches off every AH guard and the commit-time check. Separately, `nice scripts/approve.sh <slug> --by agent` passed the owner rule and wrote a real approval.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| B-AC1 | `items` prints AH1–AH5; project file can only add | PASS | `tests/framework/test_autonomy_items.py` B-AC1 block (green in the `framework` step). `python3 scripts/autonomy.py items` prints AH1–AH5 with class/field/command/path matchers, exit 0. `disable`, a top-level `AH<n>`, an empty `protected_branches` and an empty `extra.AH<n>.<kind>` all fail with `cannot remove framework item AH<n>`. |
| B-AC2 | `classify_command` names the item for each §B.2 row; `[]` for the allow cases | **FAIL** | Canonical forms of every row classify correctly, and all five allow cases return `[]` (sweep output below). Common spellings of §B.2 rows at command position are missed: `git --no-pager push origin main`, `git push --all origin`, `git push --mirror origin`, `curl -sd payload URL`, `curl -dfoo URL`, `rm -rf .`, `rm -rf *` (and `rm -rf store` with `store/data/**` declared). A move or delete *from* a protected path (`mv`, `git mv`, `git rm`) is missed too. Red tests: `test_regression_always_human_spellings_are_refused_under_a_mandate` (7 cases), `test_regression_rm_of_an_ancestor_of_a_data_glob_is_refused`. These are guard-level tests, which reach `command_matches` through `guard_bash.py`; there is no separate `classify_command` unit test for the misses. |
| B-AC3 | Planted attempt per item exits 2 under a mandate; red against today's guard | PASS | `tests/hooks/test_guard_always_human.py` B-AC3 block is green. The pre-change guard (`git show 9670f32^:.claude/hooks/guard_bash.py`) exits 0 on `git push origin main`, `curl -X POST …`, `rm -rf data/`, `git push origin --delete feature/x`, `python3 scripts/autonomy.py grant x`, `echo '{}' > scripts/autonomy.json`. The new guard exits 2 with `always-human item AH<n> — matched: …`. |
| B-AC4 | Owner-script rule, every project | **FAIL** | The literal list in the AC is refused (existing tests green). Eight command-position spellings pass with exit 0: `nice …`, `timeout 5 …`, `source …`, `. …`, `env -i …`, `/usr/bin/env python3 scripts/approve.py …`, `bash -o errexit …`, `… \| xargs scripts/approve.sh`. Carried through to a real write in a scratch repo with a temp `APPROVAL_LOG`: guard exit 0 → `approve exit=0` → `registry lines after: 1` → doc stamped `Status: Approved`. A symlink to the registry also passes. When `scripts/autonomy.py` cannot be imported, the guard exits 1, which is non-blocking. In a project without autonomy, both guards allow deleting or editing that file. Red tests: `test_regression_owner_command_behind_a_prefix_is_refused` (8), `test_regression_registry_write_through_a_symlink_is_refused`, `test_regression_owner_rule_holds_when_the_core_cannot_be_imported`. |
| B-AC5 | Owner's `!scripts/approve.sh --list` not intercepted | PENDING (live owner probe) | Needs the owner's `!` shell, which no agent has. Indirect evidence only: the guard exits 0 on `scripts/approve.sh --list`. `ADAPTERS.md` row 74 declares it unproven. |
| B-AC6 | Write/Edit to a protected path refused under autonomy, allowed outside | **FAIL** | The existing tests are green: exact names are refused, and the same edit is allowed outside autonomy (R6). On this macOS volume, which is case-insensitive (`(repo/"SCRIPTS/AUTONOMY.JSON").exists() → True`), these Writes exit 0: `SCRIPTS/autonomy.json`, `scripts/Autonomy.json`, `Doc/Mandates/M.md`, `.Claude/settings.json`. A Write through an in-repo symlink also exits 0 (`cfg.json → scripts/autonomy.json`, `mlink → doc/mandates`), and so does Bash `echo '{}' > cfg.json`. Red tests: `test_regression_case_variant_of_a_protected_path_is_refused` (3; skipped on a case-sensitive FS), `test_regression_write_through_a_file_symlink_is_refused`, `…directory_symlink…`. |
| B-AC7 | Protected path staged without an `Owner-Approved:` trailer is refused; passes with one | **FAIL** | Editing `scripts/autonomy.json` with no trailer is refused: `check-commit: always-human item AH5: scripts/autonomy.json is protected while autonomy is active (no Owner-Approved: <key> trailer)`. With a trailer it passes. But `git rm -f scripts/autonomy.json && git commit -m 'chore: tidy'` commits with exit 0 and no trailer. `is_active` reads the working tree after the deletion. Red test: `tests/framework/test_regression_commit_msg_autonomy.py`. The engineer moved the check from pre-commit to commit-msg, and that move is sound. Probe: a pre-commit hook printing `.git/COMMIT_EDITMSG` showed an empty message on the first commit and `FIRST message` on the second commit. |
| B-AC8 | Artifact classification fails closed | PASS (reading stated) | `test_autonomy_items.py` B-AC8 block is green. A spec with no `Decision-class:` gives AH-UNSURE. A `touches: none` field with an AH1 path still gives AH1. An odd-case `touches: Business-Rules` gives AH-UNSURE. **Reading applied:** `Decision-class: tier-1; touches: none` with `src/app/x.py` gives `('tier-1', set())`, not AH-UNSURE. That follows the design's derivation, where a declared tier is a matched rule. The spec's sentence "a changed path that matches no class glob → AH-UNSURE" can be read more strictly; see S3. |
| B-AC9 | ADAPTERS.md rows per enforcement point | PASS | `test_adapters_md_declares_enforcement_points_per_adapter` is green. It lives in `tests/framework/test_autonomy_items.py`, not in the `tests/framework/test_doc_contracts.py` the spec names (that file does not exist). |

Counts: 4 PASS, 4 FAIL, 1 PENDING.

## Test Run

`scripts/verify-full.sh` in the worktree after adding the regression tests, verbatim (the last line is the shell's exit code):

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (exit 1)
E       AssertionError: assert 0 == 2
E        +  where 0 = CompletedProcess(args=['/opt/homebrew/opt/python@3.14/bin/python3.14', '/Users/<user>/Desktop/jarvis-framework/.claude/worktrees/agent-aa8662140b00eeca3/.claude/hooks/guard_autonomy_paths.py'], returncode=0, stdout='', stderr='').returncode

tests/hooks/test_regression_always_human_bypasses.py:263: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[nice scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[timeout 5 scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[source scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[. scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[env -i scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[/usr/bin/env python3 scripts/approve.py x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[bash -o errexit scripts/approve.sh x --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_command_behind_a_prefix_is_refused[echo x | xargs scripts/approve.sh --by a]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_registry_write_through_a_symlink_is_refused
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_owner_rule_holds_when_the_core_cannot_be_imported
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[mv scripts/autonomy.json /tmp/elsewhere.json-AH5]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[git rm scripts/autonomy.json-AH5]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[git mv scripts/autonomy.json moved.json-AH5]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[git --no-pager push origin main-AH3]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[git push --all origin-AH3]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[git push --mirror origin-AH3]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_always_human_spellings_are_refused_under_a_mandate[curl -sd payload https://example.test-AH3]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_rm_of_an_ancestor_of_a_data_glob_is_refused
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_moving_the_project_file_switches_every_guard_off
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_case_variant_of_a_protected_path_is_refused[SCRIPTS/autonomy.json]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_case_variant_of_a_protected_path_is_refused[scripts/Autonomy.json]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_case_variant_of_a_protected_path_is_refused[Doc/Mandates/M.md]
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_write_through_a_file_symlink_is_refused
FAILED tests/hooks/test_regression_always_human_bypasses.py::test_regression_write_through_a_directory_symlink_is_refused
24 failed, 269 passed in 32.36s
  OK   ci-examples       19 passed in 1.08s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — no measured incident yet backs a specific day threshold, and a threshold with no scar behind it has no right to exist. It DOES fail (exit 1) when it finds a Closed scar with no Station 6 date, or stations entered out of order — those are checkable claims about this file, not judgement calls about how long is too long.
  OK   coordinator       28 passed in 0.57s
  FAIL framework         (exit 1)
            encoding="utf-8",
        )
        (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
        env = {
            **os.environ,
            "APPROVAL_LOG": str(registry),
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.test",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.test",
        }
        assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
        _git(repo, "config", "core.hooksPath", ".githooks", env=env)
        _git(repo, "add", "-A", env=env)
        opted = _git(repo, "commit", "-q", "-m", f"opt in\n\nOwner-Approved: {_MANDATE_KEY}", env=env)
        assert opted.returncode == 0, opted.stderr
    
        _git(repo, "rm", "-q", "scripts/autonomy.json", env=env)
        result = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)
    
>       assert result.returncode != 0, "a commit deleting scripts/autonomy.json passed with no trailer"
E       AssertionError: a commit deleting scripts/autonomy.json passed with no trailer
E       assert 0 != 0
E        +  where 0 = CompletedProcess(args=['git', 'commit', '-q', '-m', 'chore: tidy'], returncode=0, stdout='', stderr='').returncode

tests/framework/test_regression_commit_msg_autonomy.py:74: AssertionError
=========================== short test summary info ============================
FAILED tests/framework/test_bootstrapped_project.py::test_framework_suite_is_green_after_bootstrap
FAILED tests/framework/test_regression_commit_msg_autonomy.py::test_regression_deleting_the_project_file_needs_an_owner_trailer
2 failed, 120 passed in 29.41s
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
EXIT=1
```

Baseline before QA tests (same worktree, same commit): `hooks 269 passed`, `framework` OK, gate exit 0 with the three TODO steps. All 269 pre-existing hook tests stay green. `test_bootstrapped_project` fails only because it runs the copied framework suite, which now contains the red commit-msg regression test (its inner output: `FAILED tests/framework/test_regression_commit_msg_autonomy.py … 1 failed, 120 passed, 1 skipped`).

Command sweep for B-AC2 (`classify_command`, design §B.2 rows): every canonical row → expected item (29/29). Allow cases → `[]` (5/5). `git merge` while on `main` and `git rebase` while on `release` → `['AH3']`.

## Defects (if FAIL)

| Severity | Description | Where | Rework cause | Suggested owner |
|---|---|---|---|---|
| High | **Off switch.** Under an active mandate, `mv scripts/autonomy.json X`, `git mv …` and `git rm …` are allowed. `status()` then returns `inactive` because the file is gone, and every AH rule goes off: `git push origin main` 2 → 0, and the path guard on `.claude/settings.json` gives 0. A committed `git rm` passes commit-msg with no trailer. A move or delete *from* a protected path is not treated as a write, and "active" is derived from the very file being protected. | `scripts/autonomy.py:426-445` (`_write_targets`: mv/cp give only the destination, `git rm/mv` not seen); `:737-739` (`status`); `:781` (`check_commit` → `is_active` on the working tree) | missed-ac | ai-engineer |
| High | **Owner rule bypassed by a prefix.** `nice`, `timeout`, `source`/`.`, `env -i`, `/usr/bin/env`, `bash -o <opt>` and `xargs` leave the owner script unseen. Proven end to end with `nice`: guard exit 0, real registry line, doc stamped `Approved`. Wrapper stripping matches the raw token (so `/usr/bin/env` is missed) and does not skip wrapper options (`env -i`, `sudo -u x`). | `scripts/autonomy.py:330` (`_TRANSPARENT_WRAPPERS`), `:331` (`_INTERPRETERS`), `:379-382`, `:414-423` (`_effective`: `-o errexit` value taken as the script) | missed-ac | ai-engineer |
| High | **Owner rule fails open when the core cannot be imported.** With `scripts/autonomy.py` missing or broken, `guard_bash.py` exits 1 (traceback), which is non-blocking, so `scripts/approve.sh x --by a` runs. In a project without autonomy, both guards allow `rm scripts/autonomy.py` and an Edit of it. B-AC4 says "every project". | `.claude/hooks/guard_bash.py:306-308` (bare `import autonomy`) | missed-ac | ai-engineer |
| High | **Path guard misses case variants and symlinks.** On macOS's default case-insensitive volume, `SCRIPTS/autonomy.json` and `Doc/Mandates/M.md` reach protected files with exit 0. A symlink created by an allowed `ln -s` exposes a protected file or directory under an unprotected name. This affects both the Write guard and the Bash redirect rule. | `scripts/autonomy.py:299` (`fnmatchcase`), `:306-319` (`repo_relative` resolves symlinks only as a fallback) | missed-ac | ai-engineer |
| Medium | **§B.2 spellings missed:** `git --no-pager push origin main` (only `-C`/`-c` are skipped); `git push --all/--mirror origin` (pushes or overwrites protected branches); `curl -sd …`, `curl -dfoo` (combined or attached short flags); `rm -rf .`, `rm -rf *`, `rm -rf store` with `store/data/**` declared (an ancestor of a data glob). | `scripts/autonomy.py:490-513`, `:530-532`, `:596-602` | missed-ac | ai-engineer |
| Medium | **Registry writes the owner rule misses:** a symlink to the registry (`echo >> reglink`), `cd ~/.jarvis/approvals && echo >> registry.jsonl`, `"${APPROVAL_LOG:-x}"`, `dd of=…`. The candidate path is never resolved. | `scripts/autonomy.py:448-462` (`_is_registry_target`) | missed-ac | ai-engineer |
| High (owner ruling) | **S1. A trailer the agent can supply itself.** `Owner-Approved: <mandate key>` satisfies the commit check for any protected path (probe F: exit 0). `python3 scripts/autonomy.py status` prints that key to the agent. This is literal compliance with "resolves to an owner registry entry", so it is not counted as a FAIL. The owner should decide whether the key must be fresh, kind `approval`, and/or name the changed artifact. | spec B-AC7 wording; `scripts/autonomy.py:797-800` | spec-defect | owner → ba-sa |
| Low | **S2.** B-AC7 names `.githooks/pre-commit`, which cannot see the message being committed (measured). The spec should say `commit-msg`, along with design §B.4 and the adapter ข row. | `doc/specs/SPEC-delegated-autonomy.md:98` | spec-defect | ba-sa |
| Low | **S3.** B-AC8 says "a changed path that matches no class glob → AH-UNSURE". The design's derivation lets a declared tier satisfy "a rule matched". The spec should state which reading holds. | `doc/specs/SPEC-delegated-autonomy.md:99` | spec-defect | ba-sa |
| Low | **S4.** B-AC9 names `tests/framework/test_doc_contracts.py`, which does not exist. The test is in `test_autonomy_items.py`. | spec row B-AC9 | spec-defect | ba-sa |

## Edge Cases Probed

- Allowed as required: `grep -rn "approve.sh" doc/`, `cat` of the registry, `less <registry>`, `echo "run scripts/approve.sh …"`, `git log --grep approve.sh`, a heredoc that only mentions the command, `python3 -m pytest`, `scripts/approve.sh --list`, `scripts/approve.sh x --dry-run`, `python3 scripts/autonomy.py status|items` under a mandate. All gave exit 0.
- Owner rule held for: `sudo …`, `python3 -u …`, `bash -e …`, `bash -x -- …`, `../scripts/approve.sh` from a subdirectory, quoted or escaped names (`"scripts/approve.sh"`, `appr''ove.sh`, `s\cripts/…`), `~`, `$HOME`, `"$HOME/…"`, the absolute registry path, `$APPROVAL_LOG`, `${APPROVAL_LOG}`, `>>~/…` with no space, `cp` into the registry dir, `rm`/`sed -i ''` on the registry, and `cat >> registry <<EOF`.
- `scripts/approve.sh y --by a --list` and `… -n` pass, correctly: approve.py lists or dry-runs and writes nothing. The future owner wrappers (`delegate.sh` …) must honour the same flags, or this exemption becomes a hole.
- Declared limits, noted and not failed: `bash -c '…'`, `bash <<EOF … EOF`, `bash <<< '…'`, `echo … | bash`, `python3 -m approve`, a symlinked copy of approve.sh run under a new name, and `sudo -u x` (needs a password headless).
- `#`: `echo hi # ; scripts/approve.sh …` is blocked although a shell would treat the rest as a comment. That errs on the safe side. Under autonomy, `echo "DROP TABLE is bad"` is blocked as AH3 SQL (false positive; Low).
- R6: with no `autonomy.json`, only the owner rule fires. AH3 and AH5 commands and protected-path Writes all exit 0 (existing tests plus probes).
- ConfigError: a `disable` key does not weaken anything; `git push origin main` is still refused. A malformed project file gives `status` = `unknown … treated as active`, and the path guard still refuses `.claude/hooks/x.py`.
- Deviation noted: the design says matching runs over `guard_bash._executable_segments`. The engineer wrote a separate shlex splitter in `autonomy.py`, so A1' and the AH rules can disagree on one command. No harmful case was found beyond those listed.
- Adapter paths via `extra_protected`: `check_neutrality.py` passes inside the gate's `framework` step. I did not re-probe whether moving them into the core would fail it.
- Latency: guard_bash takes 42 ms (`ls -la`) and 52 ms (`git status`) per call, against 22 ms for the pre-change guard, averaged over 20 runs. This is consistent with the engineer's 35–60 ms claim.
- Stated gap confirmed and not failed: a bare `git push` while on `main` is not caught.

## Re-test 1

Commit under test: `7309362` (fix) on top of `03bc2ab` (QA pins), branch `worktree-agent-aa8662140b00eeca3`. Coordinator rulings applied as given (made under the owner's delegation; the owner may reverse them): fail closed for owner-only commands when the core cannot load; S1 trailer rule; activation anchored in the owner registry. Coordinator-accepted deviations were not counted as failures: `scripts/autonomy.py` editable while inactive, the opt-in carve-out, and the changed trailer in `test_pre_commit.py`.

### Verdict: FAIL

All 25 round-1 pins are green, and every round-1 bypass I re-ran is closed. B-AC2, B-AC4, B-AC6 and B-AC7 still fail on new routes. The worst finding: `scripts/` comes first on the core's import path, and its other files are not protected. One file the agent may write, `scripts/shlex.py` (`raise ImportError`), turns off every active-scope guard. After that, `git push origin main` exits 0, and a Write to `.claude/settings.json` exits 1, which does not block. A `scripts/argparse.py` shim lets a mandate edit through commit-msg with no trailer. Separately, `git -c alias.ok='!scripts/approve.sh' ok <slug> --by agent` passed the owner rule. I ran it end to end: it wrote a registry line and stamped the document `Approved`.

### Criteria Results (re-test 1)

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| B-AC1 | `items`; project file can only add | PASS | `tests/framework/test_autonomy_items.py` is green in the `framework` step. |
| B-AC2 | `classify_command` per §B.2 row | **FAIL** | The round-1 spellings now classify (pins green). Five new spellings push to `main` under a mandate with exit 0: `arch -arm64 git push origin main`, `caffeinate -i git push …`, `script -q /dev/null git push …`, `git -c alias.p=push p origin main` and `git push --repo=origin main`. Writes to protected paths through git: `git checkout <ref> -- .claude/settings.json`, `git checkout <ref> -- doc/mandates` and `git restore --source=<ref> doc/mandates/…` exit 0. Rewinding the tree switches the guards off: `git checkout <pre-opt-in>`, `git reset --hard <pre-opt-in>`, and `git stash -u` of an uncommitted opt-in each leave `status` = `inactive` while the mandate is live, and then `git push origin main` exits 0. Red: `test_regression_push_to_a_protected_branch_is_refused` (5), `…restoring_a_protected_path_from_another_ref_is_refused` (3), `…rewinding_past_the_opt_in_keeps_guards_on` (2), `…stashing_an_uncommitted_opt_in_keeps_guards_on`. |
| B-AC3 | Planted attempt per item exits 2 | PASS | The `test_guard_always_human.py` B-AC3 block is green. |
| B-AC4 | Owner-script rule, every project | **FAIL** | The literal list holds, and all 8 round-1 prefixes, the symlink and the missing-core cases are green. New routes: `git` and `awk` are on `_READERS`, yet each can run a file. `git -c alias.ok='!scripts/approve.sh' ok qa-probe --by agent` was carried end to end in a scratch clone with a temp `APPROVAL_LOG`: guard exit 0, `approve exit=0`, `registry lines: 1`, and the doc read `Status: Approved` / `Approval: spec-qa-probe-2026-10-20`. `git bisect run scripts/approve.sh …` and `awk 'BEGIN{system(ARGV[1])}' scripts/approve.sh` also exit 0. Registry writes: a symlink made **in the same command** is not resolved yet when the guard runs (`ln -s <registry> r && echo x >> r`, plus the directory form), and `cd $HOME/.jarvis/approvals && echo x >> registry.jsonl` gets through (`cd` does not expand variables). All exit 0. False positives in every project: `find . -name approve.sh`, `ruff check scripts/approve.py`, `scripts/approve.sh --help`, `nl`/`sort`/`bash -n`/`python3 -m py_compile` on an owner script. All exit 2. Red: `test_regression_owner_script_run_through_a_reader_is_refused` (3), `…registry_write_is_refused` (3), `…reading_an_owner_script_stays_allowed` (3). |
| B-AC5 | Owner's `!scripts/approve.sh --list` | PENDING (live owner probe) | Unchanged. The guard exits 0 on `scripts/approve.sh --list`. |
| B-AC6 | Write/Edit to a protected path refused under autonomy | **FAIL** | The round-1 case and symlink pins are green. A guard installed in the project, with an agent-written `scripts/shlex.py` raising ImportError, makes `guard_autonomy_paths.py` exit **1** (traceback, non-blocking) on a Write to `.claude/settings.json` under a mandate. The control without the shadow exits 2. The same shadow takes guard_bash into owner-only fallback, so `git push origin main` exits 0. Both a Write and `echo … > scripts/shlex.py` are allowed under the mandate, because `scripts/*.py` is not protected. Probe: `argparse`, `shlex`, `dataclasses` and `datetime` shadow the core (`fnmatch`, `typing`, `glob` and `pathlib` are preloaded and do not). Red: `test_regression_shadow_module_in_scripts_keeps_the_path_guard_on`, `…keeps_ah3_on`. |
| B-AC7 | Protected path at commit needs an owner trailer | **FAIL** | The round-1 pin (`git rm` of the project file) and the S1 cases are green. New route: commit `scripts/argparse.py` (a shim whose `parse_args` returns `command="status"`) together with an edit of `doc/mandates/MANDATE-proj-first.md`, with no trailer. Result: exit 0, and the hook printed `mandate mandate-proj-first-2026-10-20`. `python3 scripts/autonomy.py` puts `scripts/` first on `sys.path`. Red: `tests/framework/test_regression_commit_msg_autonomy.py::test_regression_a_shadow_module_cannot_switch_the_commit_check_off`. |
| B-AC8 | Artifact classification fails closed | PASS (reading stated in round 1) | Green. Not re-probed. |
| B-AC9 | ADAPTERS.md rows | PASS | Green. |

Counts: 4 PASS, 4 FAIL, 1 PENDING.

### Test Run (re-test 1)

Baseline, `scripts/verify-full.sh` at `7309362` before adding the re-test tests: `hooks 339 passed`, `ci-examples 19 passed`, `coordinator 28 passed`, `framework` OK, `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, `EXIT=0`. This matches the engineer's report.

After adding the tests: `scripts/verify-full.sh` in the worktree. The summary lines are copied verbatim; the gate itself truncates each failing step to its last traceback, and that traceback is omitted here. The user name is redacted.

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  FAIL hooks             (exit 1)
E       AssertionError: 'git push --repo=origin main' pushes to main under a mandate and passed
E       assert 0 == 2
tests/hooks/test_regression_autonomy_rework_bypasses.py:289: AssertionError
=========================== short test summary info ============================
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_shadow_module_in_scripts_keeps_ah3_on
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_shadow_module_in_scripts_keeps_the_path_guard_on
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_rewinding_past_the_opt_in_keeps_guards_on[checkout-pre-opt-in]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_rewinding_past_the_opt_in_keeps_guards_on[reset-hard-pre-opt-in]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_stashing_an_uncommitted_opt_in_keeps_guards_on
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_restoring_a_protected_path_from_another_ref_is_refused[git checkout pre-opt-in -- .claude/settings.json]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_restoring_a_protected_path_from_another_ref_is_refused[git checkout pre-opt-in -- doc/mandates]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_restoring_a_protected_path_from_another_ref_is_refused[git restore --source=pre-opt-in doc/mandates/MANDATE-proj-first.md]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_owner_script_run_through_a_reader_is_refused[git -c alias.ok='!scripts/approve.sh' ok spec-x --by agent]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_owner_script_run_through_a_reader_is_refused[git bisect run scripts/approve.sh spec-x --by agent]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_owner_script_run_through_a_reader_is_refused[awk 'BEGIN{system(ARGV[1])}' scripts/approve.sh]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_registry_write_is_refused[file-link-same-command]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_registry_write_is_refused[dir-link-same-command]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_registry_write_is_refused[cd-through-HOME]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_reading_an_owner_script_stays_allowed[find . -name approve.sh]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_reading_an_owner_script_stays_allowed[ruff check scripts/approve.py]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_reading_an_owner_script_stays_allowed[scripts/approve.sh --help]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_push_to_a_protected_branch_is_refused[arch -arm64 git push origin main]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_push_to_a_protected_branch_is_refused[caffeinate -i git push origin main]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_push_to_a_protected_branch_is_refused[script -q /dev/null git push origin main]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_push_to_a_protected_branch_is_refused[git -c alias.p=push p origin main]
FAILED tests/hooks/test_regression_autonomy_rework_bypasses.py::test_regression_push_to_a_protected_branch_is_refused[git push --repo=origin main]
22 failed, 339 passed in 27.55s
  OK   ci-examples       19 passed in 0.50s
  OK   scar-forge        LIMIT (stated limit): this reports staleness, it never gates on it — […]
  OK   coordinator       28 passed in 0.45s
  FAIL framework         (exit 1)
>       assert result.returncode != 0, "a mandate edit with no trailer passed commit-msg behind scripts/argparse.py"
E       AssertionError: a mandate edit with no trailer passed commit-msg behind scripts/argparse.py
E       assert 0 != 0
E        +  where 0 = CompletedProcess(args=['git', 'commit', '-q', '-m', 'chore: tidy'], returncode=0, stdout='', stderr='mandate mandate-proj-first-2026-10-20\n').returncode
tests/framework/test_regression_commit_msg_autonomy.py:141: AssertionError
=========================== short test summary info ============================
FAILED tests/framework/test_bootstrapped_project.py::test_framework_suite_is_green_after_bootstrap
FAILED tests/framework/test_regression_commit_msg_autonomy.py::test_regression_a_shadow_module_cannot_switch_the_commit_check_off
2 failed, 129 passed in 30.07s
EXIT GATE RED (exit 1).
Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,
or hardcode an expected value to make it pass.
EXIT=1
```

All 339 pre-existing hook tests stay green, and so do the 129 other framework tests. As in round 1, `test_bootstrapped_project` fails only because it runs the copied framework suite, which now contains the new red commit-msg test.

### Defects (re-test 1), by severity

| Severity | Description | Where | Rework cause | Suggested owner |
|---|---|---|---|---|
| Critical | **Off switch by shadowing a stdlib module.** Both guards and the commit-msg CLI insert `scripts/` at the head of `sys.path`, and `scripts/<name>.py` is not protected. Writing `scripts/shlex.py` (or `argparse`, `dataclasses`, `datetime`) is allowed under a mandate. After that, the core fails to import: guard_bash keeps only the owner fallback (AH3 and AH5 path writes off), and `guard_autonomy_paths.py` exits 1 (non-blocking). A `scripts/argparse.py` shim makes `check-commit` exit 0, so a mandate edit commits with no trailer. Suggested direction, not prescribed: import the core by file path with `-I`/`-P` semantics (no `scripts/` on `sys.path`), and fail closed (exit 2) on any core failure while a project file, a committed one or a mandate folder exists. | `.claude/hooks/guard_bash.py:307-308`, `.claude/hooks/guard_autonomy_paths.py:27-29`, `scripts/autonomy.py:51` and its CLI entry (via `.githooks/commit-msg`) | missed-ac | ai-engineer |
| High | **Owner script run through a "reader".** `_READERS` exempts `git` and `awk`, but both can run a file: `git -c alias.x='!scripts/approve.sh' x …` and `git bisect run scripts/approve.sh …` run it with the agent's arguments, and so does `awk 'BEGIN{system(ARGV[1])}' scripts/approve.sh`. Proven end to end with the git alias: a real registry line was written and the doc was stamped `Approved`. The module's own rule says "add a program here only if it cannot execute a file". | `scripts/autonomy.py:396-405` (`_READERS`), `:593-605` (`_owner_script`) | missed-ac | ai-engineer |
| High | **Off switch by rewinding the tree, and git writes to protected paths.** `git checkout <pre-opt-in commit>` and `git reset --hard <pre-opt-in>` (both allowed on a clean tree), and `git stash -u` while the opt-in is uncommitted, leave no project file, no `HEAD:scripts/autonomy.json` and no `doc/mandates`. `_authority` then returns `inactive` without reading the registry, although the mandate is live. `git checkout <ref> -- <protected>` and `git restore --source=<ref> <protected>` overwrite `.claude/settings.json` or a mandate document with exit 0. Activation still depends on the working tree; it is not anchored in the registry alone. | `scripts/autonomy.py:902-923` (`_authority` early `inactive`), `:538-572` (`_write_targets`: no `checkout`/`restore`/`reset`/`stash`) | missed-ac | ai-engineer |
| High | **Registry write through a symlink made in the same command.** `ln -s <registry> r && echo x >> r` and `ln -s <registry dir> rd && echo x >> rd/registry.jsonl` both exit 0 in every project. The link does not exist yet when the guard resolves `r`, and `ln`'s source is never checked as a registry target. The same pattern reaches protected paths under a mandate (`ln -s scripts/autonomy.json c && echo '{}' > c` gives exit 0). | `scripts/autonomy.py:574-590` (`_is_registry_target`), `:553-562` (`ln` source ignored) | missed-ac | ai-engineer |
| Medium | **AH3 push to a protected branch behind an unlisted wrapper or alias.** `arch -arm64 …`, `caffeinate -i …`, `script -q /dev/null …`, `git -c alias.p=push p origin main` and `git push --repo=origin main` all exit 0 under a mandate. The owner rule now searches the whole argv; the AH3 git rules still need `git` at command position, and the subcommand must be literally `push`. | `scripts/autonomy.py:370-391` (`_WRAPPERS`), `:624-643` (`_git_matches`: `positional[1:]` assumes the remote is positional) | missed-ac | ai-engineer |
| Medium | **`cd` through a variable.** `cd $HOME/.jarvis/approvals && echo x >> registry.jsonl` and `cd "$HOME/.jarvis" && echo x >> approvals/registry.jsonl` exit 0. `cd` expands `~` but not variables, while targets do expand them. | `scripts/autonomy.py:711-714` | missed-ac | ai-engineer |
| Low | **Reading tools that name an owner script are refused in every project.** `find . -name approve.sh`, `ruff check scripts/approve.py`, `python3 -m py_compile scripts/approve.py`, `nl`/`sort`/`bash -n scripts/approve.sh` and `scripts/approve.sh --help` all exit 2. Before increment B they were allowed. This is normal lint and search work; a guard with this many false positives tends to get switched off. | `scripts/autonomy.py:396-405`, `:74` (`READ_ONLY_FLAGS` lacks `--help`/`-h`) | regression | ai-engineer |
| Medium (ruling) | **The opt-in carve-out admits any new protected file.** On the commit that first adds `scripts/autonomy.json`, the mandate key that `status` prints clears every added path. That includes a new `doc/orders/ORDER-self.md`, a new `doc/mandates/MANDATE-wide.md`, a not-yet-existing owner wrapper `scripts/release.sh` and a new `.githooks/post-checkout` (probe: exit 0, all in one commit). This matches the accepted wording ("clears only the paths that commit adds"), so it has no red pin. The coordinator or owner should decide whether it should clear only `scripts/autonomy.json`. | `scripts/autonomy.py:989-999`, `:1033-1046` | spec-defect | coordinator → owner |
| Medium (ruling) | **A project can claim another project's mandate.** In a project with no mandate, the agent may write `scripts/autonomy.json` with `"project": "proj"` (allowed while inactive, an accepted deviation). `status` then reports `mandate mandate-proj-first-…` for that project. Increment B only adds guards, so this is harmless today. Once increment C's approve-under exists, it would let an agent put an undelegated project under someone else's mandate. The spec does not say what binds a mandate to a repository. | `scripts/autonomy.py:937-941` (`ours` by slug prefix) | spec-defect | ba-sa |
| Low (ruling) | **Writers outside the enumerated list.** `perl -pi`, `truncate`, `unlink`, `rsync`, `find … -delete`, `patch` and `chmod 000` reach protected paths under a mandate, and `rsync`/`truncate`/`unlink`/`perl -pi` reach the registry in every project. All exit 0. Design §B.2 enumerates only redirect, tee, `sed -i`, cp, mv and rm, so the spec should say whether that list is exhaustive. | design §B.2 AH5 row; `scripts/autonomy.py:538-572` | spec-defect | ba-sa |

### Edge cases probed (re-test 1)

- Round-1 bypasses re-run: every one is now refused, both through the pins (green) and as hand probes. `cd <regdir> && echo >> registry.jsonl`, `pushd`, a chained `cd a && cd b`, `cp /dev/null <registry>`, `tee -a`, `mv x <registry>` and `rm <registry>` are all blocked.
- Fallback mode: a core that **raises when called** is handled. `_apply_core` wraps import and run, so the owner rule holds. A core **replaced by an always-inactive stub** would switch off everything except that fallback. An agent cannot write `scripts/autonomy.py` under a mandate by Write, redirect or cp. It can by `git checkout <ref> -- scripts/autonomy.py` (High row above), and indirectly by shadowing (Critical row).
- `doc/mandates/` alone activating, machine-wide: an empty `doc/mandates/` in an unrelated repo with no project file makes `status` = `mandate mandate-proj-…` (another project's mandate), and a Write to `.claude/settings.json` there is refused. That is the safe direction, so it is not a defect. It does contradict R6 for any repo that ships a `doc/mandates/` folder before opting in. I found no way to abuse it toward *less* guarding.
- `APPROVAL_LOG=<empty file> git commit …`: the guard allows it (exit 0), and commit-msg then reads an empty registry. `inactive` follows, and a mandate edit commits with no trailer. This is the same class as `git commit --no-verify`, which the guard also allows. The hook says it "skips this hook, not CI". I recorded it, not failed it, because the commit-time check claims only tamper-evidence and CI is the backstop.
- Datetime shim at commit time (`date.today()` → 9999): `status` still printed the mandate, so `datetime` is resolved before `scripts/` takes effect in the CLI path. Not a route.
- SQL false positives under a mandate: `git commit -m 'feat: drop the DELETE FROM path'` and `echo 'DROP TABLE is bad'` are blocked (AH3). Low, carried from round 1.
- `git stash` (without `-u`) and `git rm -r --cached .`: stash is allowed (HEAD keeps the project file). `git rm -r --cached .` is blocked as a write to protected `.`, which is correct.
- Not probed: Windows or case-sensitive volumes; the `-I`/`-P` interpreter behaviour of the hook runner.

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** qa, against SPEC-delegated-autonomy (Approved, key spec-delegated-autonomy-2026-10-20) at commit 9670f32. Adds 25 red-first regression tests (24 in hooks, 1 in framework) in `tests/hooks/test_regression_always_human_bypasses.py` and `tests/framework/test_regression_commit_msg_autonomy.py`.
- **2026-10-20 — re-test 1.** qa, against 7309362. FAIL on B-AC2, B-AC4, B-AC6 and B-AC7; B-AC5 still pending the owner's live probe. Adds 22 red-first regression tests in `tests/hooks/test_regression_autonomy_rework_bypasses.py` and 1 in `tests/framework/test_regression_commit_msg_autonomy.py`.

## B-AC5 live owner probe (coordinator, 2026-10-20)

After the B merge (8cccea4) the owner ran, from their own `!` shell prefix:
`APPROVAL_LOG=/tmp/jarvis-probe.jsonl scripts/approve.sh zz-nomatch --by <owner>`
Output: `ปฏิเสธทั้งชุด — ยังไม่ได้เขียนอะไรเลย: zz-nomatch: ไม่มีเอกสารที่ git track และชื่อไฟล์ตรงกับ slug นี้`
— approve.py's own refusal, no `BLOCKED … owner-only`. The owner-only rule does not fire on the
owner's `!` commands. Same session, an agent-issued `scripts/approve.sh x --by a` → guard exit 2.

B-AC5: **PASS**.
