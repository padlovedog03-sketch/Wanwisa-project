# Review: verify-tiers increment D — merge gate (final confirmation after REWORK 2)

Status: Draft
Owner: reviewer
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Author-run: a251af236e29ab259
Reviewer-run: ac882ab23a015b907
Date: 2026-10-20

Verdict: PASS

## Verdict: PASS

At head 1ee6f19 the two accident-class false GREENs from the last round are closed: R6 (shadowed import) now gives `MERGE GATE RED` and R11 (`--check` of a record made with the candidate's own gate code) now gives `MERGE GATE NOT RUN`. All eight D criteria still pass, and the exit gate passes every configured step. R7 (a test step rewrites the recorder) is still GREEN, but under the owner's threat model (scope-discipline rule 5, doc/memory/stay-on-the-definition.md, commit be0fa18) it is deliberately written fraud. The engineer declared it as a LIMIT in the `verify-merge.sh` header, so it is under Parked, not rework.

## 1ee6f19 confirmation (delta 97bde08..1ee6f19)

This is a confirmation pass, not a new hunt. I read the delta diff (`git diff 97bde08..1ee6f19`), scope-discipline rule 5 and doc/memory/stay-on-the-definition.md. I ran everything below in this run, at worktree `.claude/worktrees/agent-a251af236e29ab259`, HEAD `1ee6f19`, with `git status --short` empty before and after.

### Repros re-run

`python3 -m pytest -q -s -p no:cacheprovider /private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D2-a251-hostile/test_rev_d2.py` gave `1 failed, 8 passed`. Output: `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D2-a251-hostile/run-1ee6f19.out`.

| Repro | Last round (97bde08) | Now (1ee6f19) | Result |
|---|---|---|---|
| R6, `scripts/fnmatch.py` shadows the recorder's import | GREEN | `MERGE GATE RED — tree c2d579ba… — runner r1` | Closed |
| R11, `--check` of the record from the candidate's own forged `verify-full.sh` | GREEN | `MERGE GATE NOT RUN — record is for tree 45ddecb2…, judged tree 2e6e911f…` | Closed |
| R7, a test step rewrites the injected recorder mid-run | GREEN | `MERGE GATE GREEN — tree bf0b084c… — runner r1` (the one failing case) | Deliberate fraud. Declared LIMIT, see Parked |
| R1, R6-control, R9 | RED | RED | Unchanged |
| R2, R3 (base ref is trusted) | GREEN | GREEN | Declared LIMIT, unchanged |
| R4 (bad base refs) | NOT RUN | NOT RUN, exit 3 | Unchanged |

Mutation check. In a `git archive` copy (`/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D3-a251-mut`), I removed `-I` from `verify-full.sh` and from the judge heredoc in `verify-merge.sh`. Then `python3 -m pytest -q -p no:cacheprovider tests/hooks/test_verify_merge.py -k shadowing` gave `2 failed`. The engineer's two new shadow tests catch the fix being reverted. (`-k` was used here only to target the mutation, not as a gate run.)

### The engineer's four deviations, judged

1. **`--check` binds to the judged tree** (the candidate's tree with the base's gate code in it, hashed in a scratch index). Accepted. The honest path stays GREEN: `test_check_of_a_runner_record_made_with_the_base_gate_code_is_green` passes. The forged own-gate-code record is refused (R11 above). Its only failure mode is that the base moves between the CI run and the `--check`, and that fails closed (NOT RUN). See Parked.
2. **`--check` with no base ref gives NOT RUN.** Accepted. It fails closed, and it is pinned by `test_check_without_a_base_ref_is_not_run`.
3. **`-I` on the judge heredoc** (`python3 -I -`). Accepted. The judge imports only `json` and `sys`, so isolated mode costs an honest run nothing. It is pinned by `test_a_candidate_module_shadowing_the_judges_import_is_not_green` (red without `-I`, as shown above).
4. **Stale-path test tweak** (`tests/ci/test_ci_examples.py`). The doc-path check strips `;` and maps `scripts/verify.conf` to `scripts/verify.conf.example`. Accepted. `verify.conf` is a per-project file made from the committed example (SETUP §6), so the tweak opens no route to a false GREEN. The gate-2 command assertions now check the last line of the step (`./scripts/verify-full.sh`). The new `test_gate_2_takes_the_gate_code_from_the_base_branch[github|azure-pr|azure-push]` runs the real YAML script body against a clone and asserts `BASE GATE` and the `note:` line.

### Criteria (re-run at 1ee6f19)

| # | Criterion | Verdict | Evidence (command run in this run) |
|---|---|---|---|
| D-AC1 | GREEN in a fresh worktree, bound to tree and runner | PASS | `python3 -m pytest tests/hooks/test_verify_merge.py tests/framework/test_doc_contracts.py tests/ci -q -p no:cacheprovider` → `132 passed, 1 skipped` |
| D-AC2 | exactly one banner; RED 1 / NOT RUN 3 | PASS | Same run. Every repro above printed exactly one banner. R4 exit 3 and R6 RED both match. |
| D-AC3 | `--check` refuses another tree and a record with no runner | PASS | Same run (with the new judged-tree binding). R11 → NOT RUN. |
| D-AC4 | local fallback is labelled weaker | PASS | Same run |
| D-AC5 | dirty caller tree: HEAD judged, caller untouched | PASS | Same run. `git status --short` in the worktree was empty after all runs. |
| D-AC6 | every requiring line carries the opt-in qualifier | PASS | `tests/framework/test_doc_contracts.py` in the same run. The reworded SETUP §6 items 4 and 6 keep the qualifier. |
| D-AC7 | QA verdict rests on its own run | PASS | Same run |
| D-AC8 | conf example, SETUP §6, CI runner id, ci tests, neutrality 0 | PASS | `tests/ci` in the same run. `python3 scripts/check_neutrality.py` → `neutrality: 0 provider name(s) in layers 0-1, 0 project leak(s)` |

Exit gate, `scripts/verify-full.sh` in the worktree, exit 0 (output: `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D2-a251-hostile/verify-full-1ee6f19.out`): hooks `858 passed`, ci-examples `22 passed`, coordinator `111 passed`, framework OK, scar-forge OK, then `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`. INCOMPLETE is this template repo's normal state, because those three steps are TODO placeholders. Every configured step passed.

### Defects (accident class)

None.

### Parked (proposed LIMIT lines, no rework)

- **R7, deliberate fraud.** Committed test code that rewrites the recorder mid-run, or writes a fake JUnit with matching counts, still gives GREEN. It is already declared in the `verify-merge.sh` header ("the candidate's own test code … runs with the gate's privileges … The control is reviewing the candidate's test diff"). This matches rule 5. The same goes for the conftest/JUnit residual and the pytest `addopts` filter carried over from the last round, when committed on purpose.
- **Base moves between the CI run and `--check`.** `--check` hashes the judged tree against the base ref as it is at check time. If the base's gate code changed in between, or a PR targets a branch other than `main` and `VERIFY_MERGE_BASE_REF` is not set, an honest record gives NOT RUN. This fails closed. SETUP §6 item 6 already covers the non-`main` target. Proposed LIMIT: "--check must use the base the runner used."
- **`verify-handoff.sh` still calls the recorder without `-I`** (stated in the engineer's commit message; that file belongs to increment B and is not in this change). A shadowed import there would affect the handoff tier, not the merge gate. Route it to increment B.
- **Carried over and unchanged:** the quiet fallback to local `main` when there is no `origin/main`; `python3` missing gives exit 127 with no banner (fails closed); the merge order (B lands first).

## Outside files

None edited. This run wrote only this review file, plus scratch files under `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D2-a251-hostile/` and `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D3-a251-mut/`.

## Round 2 record (97bde08), superseded by the confirmation above

The old High is closed for the case it named: a committed forged `verify-full.sh` on a branch with a clean base now goes RED and prints the `note:` line. All eight D criteria pass again. The verdict is still FAIL, because three other routes give `MERGE GATE GREEN` from a run that executed no test, and the declared limits cover none of them:

1. The candidate shadows a module that the base's recorder imports (`scripts/fnmatch.py`).
2. The documented runner path, a CI run of the candidate's own `verify-full.sh` followed by `--check`, is still open.
3. A test step rewrites the injected recorder in the middle of the run.

### Read from

- Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md (D-AC1 to D-AC8). Also read: doc/memory/ease-of-use-over-strictness.md, doc/framework/SETUP.md §5 and §6, ci-examples/*.yml, scripts/verify.conf.example.
- Change: the rework commits b3c5133, 214e914 and 97bde08 on top of 7a47d5e, on branch worktree-agent-a251af236e29ab259, in worktree `.claude/worktrees/agent-a251af236e29ab259`.
- Not read: the author's conversation. I checked the engineer's stated residual (the base ref is trusted) by reproducing it as R2 and R3.

### Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| D-AC1 | GREEN in a fresh worktree, bound to tree and runner | PASS | `python3 -m pytest -q tests/hooks/test_verify_merge.py tests/framework/test_doc_contracts.py tests/ci/test_ci_examples.py tests/framework/test_neutrality.py` → `138 passed, 1 skipped`. `test_green_runs_in_a_fresh_worktree_and_binds_tree_and_runner` is included. |
| D-AC2 | exactly one banner; RED 1 / NOT RUN 3 | PASS | Same run. On the real worktree, `bash scripts/verify-merge.sh HEAD` printed `note: this candidate changes the gate code — judged with main's copy`, then `conf: none committed in main; environment only`, then `MERGE GATE NOT RUN — no runner and no local fallback configured`, and exited 3. That is one banner. Afterwards `git worktree list` showed no `merge-gate-*` entry and `git status --short` was empty. |
| D-AC3 | `--check` refuses another tree and a record with no runner (RED-FIRST) | PASS | In a `git archive` copy, I changed the reworked line 123 to `if False and before != judged:`. `test_check_refuses_a_record_for_another_tree` then failed: `1 failed, 56 passed`. The planted case has teeth on the new line. |
| D-AC4 | local fallback is labelled weaker | PASS | `test_local_fallback_without_a_runner_id_is_labelled_weaker` is in the 138 passed. |
| D-AC5 | dirty caller tree: HEAD judged, caller untouched | PASS | The dirty-tree and dirty-conf tests are in the 138 passed. `git status --short` in the author worktree was empty after all my runs. |
| D-AC6 | every requiring line carries the opt-in qualifier (RED-FIRST) | PASS | `tests/framework/test_doc_contracts.py` is in the 138 passed. The rework only touched SETUP §6, and the reworded lines there keep the qualifier. |
| D-AC7 | QA verdict rests on its own run | PASS | `test_qa_verdict_rests_on_its_own_run_never_an_earlier_record[*]` is in the 138 passed. The rework did not change it. |
| D-AC8 | conf example, SETUP §6, CI runner id, ci tests, neutrality 0 | PASS | `python3 scripts/check_neutrality.py` → `0 provider name(s) in layers 0-1`. In the exit gate, ci-examples gave `19 passed`. |

The rework's own tests are red-first. In a copy of HEAD with `scripts/verify-merge.sh` set back to 7a47d5e's version, `tests/hooks/test_verify_merge.py` gave `11 failed, 46 passed`. The 11 failures are exactly the new tests (`test_forged_candidate_verify_full`, `_recorder`, `_conf`, `test_no_base_ref_is_not_run[*]`, and so on).

Exit gate, run in the author worktree in this review: `scripts/verify-full.sh` → hooks `853 passed`, ci-examples `19 passed`, coordinator `111 passed`, framework OK, scar-forge OK, and the final line `EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests`, exit 0. INCOMPLETE is this template repo's normal state, because lint, format and tests are TODO placeholders. Every configured step passed.

### The old High: closed for the route it named

The old scratch file (`…/scratchpad/hostile/test_hostile_merge.py`) is gone. The scratchpad is shared, and another session removed it. I re-created its forgery byte for byte as R1 in the new scratch file (path under Hostile inputs). Results:

- **R1.** On branch `cand`, base `main` clean: the forged `verify-full.sh`, plus a suite that runs nothing → `note: this candidate changes the gate code — judged with main's copy; review the gate diff`, then `MERGE GATE RED — tree fff6f06d… — runner r1`, exit 1. Closed.
- **R1b.** The forged `verify-full.sh` with the suite intact → the base's `verify-full.sh` runs the real stub suite (`3 passed`), the note line is printed, and the merge record holds no `forged` path. Correct.

### The engineer's declared residual (base ref is trusted): acceptable as declared

- **R2.** The forgery committed on local `main` itself, default base → `MERGE GATE GREEN`.
- **R3.** `VERIFY_MERGE_BASE_REF=HEAD` → `MERGE GATE GREEN`.

Both match the header's LIMIT ("A base the agent can write … makes base == candidate"). SETUP §6 step 1 says that the base branch must be locked (section 5) because the merge gate trusts it. SETUP §5 tells the user how to lock it (GitHub branch rules, or Azure Branch policies) and says plainly that "ถ้ายังไม่ล็อกสาขา ด่านทั้งหมดยังข้ามได้ด้วยการ push ตรง".

In my opinion this limit is acceptable under doc/memory/ease-of-use-over-strictness.md. Forging it requires writing to the base itself, which a protected branch refuses. That is the same trust root as every other CI gate in this framework, not a hole the gate opens. One sharp edge is under Parked: when `origin/main` is absent, the gate falls back quietly to local `main`.

### Defects

| Severity | Description | Where | Back to |
|---|---|---|---|
| High | **False GREEN through a shadowed import of the base's recorder (R6).** The candidate commits `scripts/fnmatch.py` and nothing in the three gate files. The base's `verify-full.sh` runs `python3 scripts/verify_record.py …`, so `scripts/` is `sys.path[0]` and the candidate's `fnmatch.py` loads before the stdlib one. Its forged `finalize` writes `{"tier":"full","tree":{"before":<--tree-before>,"after":same},"runner":{"id":$VERIFY_RUNNER_ID,"kind":"runner"},"verdict":"GREEN","count_check":"ok"}` and prints `VERDICT=GREEN`; every other subcommand gets the real module. The suite runs nothing (`OK tests (0s) ran nothing`). Result: `MERGE GATE GREEN — tree 4a7ddfb4… — runner r1`, exit 0, and **no `note:` line**, because the note covers only the three files. Control R6-control (same do-nothing suite, no shadow) → `MERGE GATE RED`. This is the case the ease-of-use ruling names as not declarable ("the guard importing agent-writable code"). The claim in the header and in verify.conf.example, "a candidate cannot judge itself with gate code it wrote", is false while it is open. Repro: `test_R6_shadowed_import`. | `scripts/verify-full.sh:110,119,169,170` (`python3 scripts/verify_record.py …` with the script dir on `sys.path`); `scripts/verify-merge.sh:191` (only three files replaced) | ai-engineer. A fix within the ruling: run the recorder isolated, e.g. `python3 -I scripts/verify_record.py` (the recorder has no sibling imports, checked with `grep '^import\|^from'`: stdlib only). Pin it with a shadow test like R6. Since `verify-full.sh` is taken from the base, the fix protects candidates once it is merged. |
| High | **The documented runner path still has the original High (R11).** SETUP §6 step 4 marks `runner` as **แนะนำ** ("recommended"). Step 6 and both CI examples (`ci-examples/github-actions.yml:94-97`, `azure-pipelines.yml:74-78`) run `./scripts/verify-full.sh` from the candidate's own checkout, with `VERIFY_RUNNER_ID` set, and say the record is re-checked with `scripts/verify-merge.sh --check <record> <ref>`. `--check` runs no base code. With the forged `verify-full.sh` committed on a branch, running it with `VERIFY_RUNNER_ID=ci-7` and then `--check .verify/runs/forged/record.json HEAD` → `MERGE GATE GREEN — tree fff6f06d… — runner ci-7`, exit 0. The `--check` LIMIT in verify.conf.example ("a record is a file … take it from the runner's own artifacts") does not cover this. The runner's own artifact is the forged one, because the runner ran the candidate's gate code. The coordinator's ruling closed the main-run mode only. Repro: `test_R11_check_of_candidates_own_record`. | `scripts/verify-merge.sh:164-165` (`--check` judges any record); `ci-examples/*.yml` gate 2; `doc/framework/SETUP.md` §6 steps 4 and 6 | coordinator / ba-sa first, to decide what the runner runs. Options I saw, not prescribed: (a) the CI examples run `scripts/verify-merge.sh HEAD` from a checkout of the base, so the gate code comes from the base; (b) `--check` refuses, or labels as weaker, a record whose run did not use the base's gate code (for example, the merge record carries `gate_code.base_commit` and `--check` requires it); (c) state the limit in SETUP §6 and in the examples. Under the ease-of-use ruling, (c) alone would declare away a false green, which that ruling does not allow. |
| High | **A test step rewrites the injected recorder in the worktree mid-run (R7).** The candidate's test command (here `tools/stub_junit.py`) inserts the forged `finalize` into `$wt/scripts/verify_record.py` and exits 0 without running anything. `verify-full`'s TREE_AFTER and `finalize` then run the rewritten recorder. The rewritten recorder writes `after = before` although a tracked file changed. The outer judge trusts the record's `tree.after` and never re-checks the worktree itself. Result: `MERGE GATE GREEN — tree 04900fbb… — runner r1`, exit 0, with no note line. Repro: `test_R7_step_rewrites_recorder`. The real-world equivalent is any committed `conftest.py` or test module. Re-hashing the tree after the run is **not** enough on its own, because the forged recorder can restore its own file before it exits. The verdict has to come from code the candidate never had a chance to touch, for example `finalize` re-run after `verify-full.sh` exits, from a copy taken fresh from the base's git objects outside `$wt`. | `scripts/verify-merge.sh:251-271` (the recorder lives inside `$wt` while candidate code runs there; `judge` trusts `tree.after`) | ba-sa / owner. How far the gate defends against candidate code running as the same user is a design decision. At minimum, the header must stop claiming what it does not prove. The residual that cannot be closed is under Parked. |

### Hostile inputs tried

Scratch file: `/private/tmp/claude-502/-Users-pongsakorn-ni-Desktop-jarvis-framework/6d826cce-9bfa-45c0-81a3-52b532c353c2/scratchpad/rev-D2-a251-hostile/test_rev_d2.py`. Run from the author worktree with `python3 -m pytest -q -s -p no:cacheprovider <file>` → `3 failed, 6 passed`. The 3 failures are the defects above. Output: `…/rev-D2-a251-hostile/run.out`.

- R1, the old forgery on a branch with a clean base → RED plus the note line. Closed.
- R2, the forgery on local `main`, and R3, `VERIFY_MERGE_BASE_REF=HEAD` → GREEN. This is the declared LIMIT.
- R4, `VERIFY_MERGE_BASE_REF` set to `nope`, `" main"` or `"main\n"` → each `MERGE GATE NOT RUN — no base ref to take the gate code from`, exit 3. Empty `VERIFY_MERGE_BASE_REF=""` → uses the default (`main`).
- R5, no `main` and no `origin/main` (branch renamed to `master`) → NOT RUN, exit 3.
- R6, shadowed `scripts/fnmatch.py` → **GREEN** (Defect 1). Its control → RED.
- R7, a step that rewrites the recorder → **GREEN** (Defect 3).
- R9, the candidate turns `scripts/` into a symlink to a directory holding a forged `verify-full.sh` → RED.
- R10, the candidate deletes all three gate files → restored from the base, and the real suite runs.
- R11, `--check` of the record from the candidate's own `verify-full` → **GREEN** (Defect 2).
- The pytest config route (`pytest.ini`, `pyproject.toml` or `setup.cfg` `addopts`): `grep -n 'pytest.ini\|pyproject\|addopts\|setup.cfg' scripts/verify_record.py` finds only `PYTEST_ADDOPTS` (line 112). The ini files are not scanned. I did not reproduce it. See Parked.

### Parked

- **Inherent residual (declare it, not a FAIL by itself).** A candidate's test harness (`conftest.py`, a JUnit plugin) can write a passing JUnit report whose count agrees with a collect step it also controls. Any gate that runs the candidate's suite has this property, and only diff review controls it. Once Defects 1 to 3 are settled, the header should carry one LIMIT line for it.
- **Pytest config `addopts` (predates D; false-green class, route via coordinator).** `addopts = -k …` in a committed `pytest.ini` or `pyproject.toml` would filter both collection and the run, so executed == collected still holds. The ban scan reads `PYTEST_ADDOPTS` only. This is inferred from the grep, not reproduced. It belongs to the bans increment, not to D.
- **Quiet fallback to local `main`.** With no `origin/main` (no remote, or a shallow CI fetch), the default base quietly becomes local `main`, which is the agent-writable case. It shows only in the `conf: … committed in main` line and in the merge record's `gate_code.base_ref`. Suggest a `note:` line when the base ref is a local branch.
- **Weak pin.** With the `before != judged` check disabled, only the `--check` test failed. No main-run test bites on the binding against the injected tree. It is hard to break in practice, because verify-full hashes the same worktree.
- **Carried over from the first review, still open:** the merge order (B's `verify-handoff.sh` must land first), and `python3` missing → exit 127 with no banner.
- **Shared scratchpad.** Another session deleted the brief's repro file `…/scratchpad/hostile/test_hostile_merge.py` and my first copy (`hostile2`, `mut2`). Reviewers should use uniquely named scratch directories.

## Approval history

- **2026-10-20 — drafted (first review).** FAIL on one High: the candidate's own `verify-full.sh` forged GREEN.
- **2026-10-20 — re-review after REWORK (b3c5133, 214e914, 97bde08).** Independent reviewer, working from the spec, the rework diff and commands re-run in the author's worktree and in scratch copies. The old High is closed for its route. The verdict is FAIL on three new false-GREEN routes. The declared trusted-base LIMIT is judged acceptable.
- **2026-10-20 — final confirmation at 1ee6f19.** Independent reviewer. R6 and R11 re-run and closed (RED and NOT RUN). R7 parked as deliberate fraud per scope-discipline rule 5 and the engineer's header LIMIT. The four deviations are accepted. D-AC1 to D-AC8 PASS. The exit gate passes every configured step. Verdict PASS.
