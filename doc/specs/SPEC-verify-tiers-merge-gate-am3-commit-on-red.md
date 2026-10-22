# SPEC: Amendment 3 — pre-commit refuses a commit whose staged tree's newest gate record is RED, or which holds a placeholder CI gate 3 would fail on

Status: In Review
Owner: ba-sa
Upstream: doc/requirements/PRD-verify-tiers-merge-gate.md (Approved, registry key `prd-verify-tiers-merge-gate-2026-10-20`; R5, R10, R12) · doc/memory/gate-exit-code-before-commit.md (incident 1: e6b4daa committed while verify-full printed RED; incident 2: 7661338 committed docs with no gate run, CI gate 3 went red) · un-parked by Jarvis under doc/memory/jarvis-decides-self-improvement.md (backlog improvement checklist C2) · constraints doc/memory/ease-of-use-over-strictness.md, doc/memory/hostile-inputs-in-every-ac.md, doc/memory/smallest-useful-scope-first.md
Date: 2026-10-22

## Overview

`.githooks/pre-commit` gains one check. It hashes the tree that is about to be committed and looks
for gate records (`.verify/runs/*/record.json`, written by `scripts/verify_record.py`) taken on
exactly that tree. If the newest one is RED, the commit is refused. If there is no usable record,
the hook prints one warning line and lets the commit through. INCOMPLETE, GREEN and OK never block.
`git commit --no-verify` remains the declared escape, and CI remains the real gate.

It also gains a second check: **the placeholder scan.** The hook runs CI gate 3's scan
(`ci-examples/github-actions.yml`, step "ไม่มีตัวยึดหลงเหลือ") with the same pattern, roots and
exclusions, over the index that is about to be committed. On a hit, the commit is refused. The scan
takes about 0.03 s (F19). In a fresh template that has not been bootstrapped, the five placeholders
that `scripts/bootstrap.sh` fills are allowed, and every other one is refused. Both incidents' real
cause was exactly such a literal, and replaying either commit's tree through the scan finds it (F21).

This blocks incident 1's shape by machine **when the commit stages everything on disk** (the usual
`git add -A && git commit`, F4). With unstaged edits or untracked files, the record cannot match
the index (F5), so a RED run followed by a partial commit only warns (declared limit 3)
`[INFERRED]`: e6b4daa's working-tree state cannot be replayed, F17. For incident 2 (no gate run at
all), the record check only warns (D4). What blocks incident 2 is the placeholder scan, because its
cause was a placeholder literal (F21). Any other kind of red that is committed with no gate run still
gets only the warning.

**What this amendment changes.** It adds requirements AM3-R1 to AM3-R10 and the criteria AM3-AC1 to
AM3-AC21 below. Nothing in the approved spec, its design, or amendments 1 and 2 changes. In
particular, the record schema, the verdict words (PRD R12), and every tier script stay as they are.

**Markers.**
- `[MEASURED: cmd]` means I ran `cmd` on 2026-10-22 on branch `feat/top3-tiers-mechanisms-deny` at
  `96bebdb`, git 2.39.5, in this checkout, unless another place is named. The scratch repos named
  below were throwaway repos built in the session scratchpad, deleted afterwards.
- `[INFERRED]` means I read it but did not run it.

## Current behaviour (the facts the decisions rest on)

| # | Fact | Evidence |
|---|---|---|
| F1 | Today's hook runs four checks (approvals, scar status, memory lint, neutrality) and nothing reads `.verify`. A commit whose staged tree has a RED record goes through. | `[MEASURED: scratch repo built like tests/framework/test_pre_commit.py::_clone_template, plus a hand-planted .verify/runs/20261022T000000Z-1/record.json with verdict RED and tree.before = tree.after = $(git write-tree); git commit -qm "on red"` → `commit-on-RED rc=0`] |
| F2 | Inside pre-commit, git hands the hook the index it is about to commit through `GIT_INDEX_FILE`. A plain `git write-tree` in the hook returns exactly the tree that gets committed, for all three commit forms. | `[MEASURED: scratch repo whose pre-commit echoes $GIT_INDEX_FILE and $(git write-tree)]`: `git commit` → `IDX=.git/index`, tree equals `HEAD^{tree}` afterwards; `git commit -a` → `IDX=…/.git/index.lock`, equal; `git commit -- f` with another path staged → `IDX=…/.git/next-index-82494.lock`, equal (the other staged path was left out, as committed) |
| F3 | `verify_record.py`'s own git helper removes `GIT_INDEX_FILE`, `GIT_DIR` and `GIT_WORK_TREE` from the environment, and `tree-hash` hashes the **working tree** (every unignored file, staged or not, minus `.verify`) through a throwaway index. So `tree-hash` is the wrong tool inside the hook. With `g` staged and `commit -- f`, `tree-hash` printed `fc367812…` while the commit's tree was `166b786d…`. Under `commit -a` with no untracked files, the two happened to agree (`554cb69b…`). Stripping `GIT_INDEX_FILE` is worse: `git write-tree` then fails with `index.lock: File exists` under both `commit -a` and `commit -- f`. | `[MEASURED: sed -n 391,433p scripts/verify_record.py]` (`_git_env`, `tree_hash`) · `[MEASURED: scratch repo whose pre-commit prints $(git write-tree), $(verify_record.py tree-hash) and $(env -u GIT_INDEX_FILE git write-tree)]` |
| F4 | A record's `tree.after` equals the commit's tree when everything on disk is staged (the usual `git add -A && git commit`). Record `20261022T085214Z-48995` has `tree.before = tree.after = 71596809…`, and the next commit `96bebdb` has `HEAD^{tree} = 71596809…`. In the F1 scratch repo, after `git add -A`, `tree-hash` and `git write-tree` both printed `05faa81e…`. | `[MEASURED: python3 -c "…json.load(open('.verify/runs/20261022T085214Z-48995/record.json'))['tree']"; git rev-parse HEAD^{tree}]` |
| F5 | With unstaged edits or untracked unignored files, the working-tree hash and the index tree differ. This checkout had one unstaged file at measurement time: `tree-hash` printed `3a99ca88…` while `git write-tree` printed `71596809…`. | `[MEASURED: git status --porcelain; git write-tree; python3 -I scripts/verify_record.py tree-hash]` |
| F6 | **verify-full** always writes a record with a tree (GREEN, INCOMPLETE or RED; tier `full`). Here, all 19 records are tier `full`: 12 INCOMPLETE, 7 RED (every RED is the `ci-examples` step). This template's own verify-full is INCOMPLETE because three steps are `echo TODO`. | `[MEASURED: for each .verify/runs/*/record.json print tier, verdict, tree.after]` |
| F7 | verify-full takes 235–378 s per run here (19 runs). | `[MEASURED: ended_at − started_at over the same 19 records]` |
| F8 | **verify-fast** never binds a record to a tree: it calls `finalize --tier fast` with no `--tree-before/--tree-after`, so `tree` is all null. When its LINT/TEST are still TODO (as in this template), it exits 0 with `FAST VERIFY INCOMPLETE` before `finalize`, so it writes **no** `record.json` at all. | `[MEASURED: finalize --tier fast on a scratch run dir → tree {'before': None, 'after': None, 'head': None, 'dirty': None}, verdict OK]` · `[MEASURED: scripts/verify-fast.sh doc/specs/SPEC-verify-tiers-merge-gate.md → rc=0, FAST VERIFY INCOMPLETE; new run dir holds only junit/]` |
| F9 | **verify-handoff** writes a tree-bound record (tier `handoff`, verdict OK, RED or EMPTY) because it passes `--tree-before/--tree-after`. This repo is not opted in. | `[MEASURED: grep -n "tree-before" scripts/verify-handoff.sh → line 180]` · `[MEASURED: finalize --tier handoff on a scratch run dir with selection.json, one step and a 1-test JUnit file, --tree-before/--tree-after = $(git write-tree) → tier handoff, verdict OK, tree.before = tree.after = the write-tree hash]` · `[MEASURED: scripts/verify-handoff.sh --status → not opted in]` |
| F10 | Verdict words in records: full = GREEN, INCOMPLETE, RED; fast and handoff = OK, RED, EMPTY. | `[MEASURED: sed -n 655,665p and 898,906p scripts/verify_record.py]` |
| F11 | Run directories are named `YYYYmmddTHHMMSSZ-PID` (full), `…-PID-fast`, `…-PID-handoff`. Before my own verify-fast probe (F8), two of the 21 directories here had no `record.json` (an aborted full run with only `steps.tsv`, and a TODO fast run with only `junit/`). The probe added a third, of the second kind. The recorder keeps 20 runs per tier bucket. | `[MEASURED: ls .verify/runs; sed -n 530,540p scripts/verify_record.py]` |
| F12 | Records are small (largest here 1395 bytes). | `[MEASURED: ls -l .verify/runs/*/record.json \| awk '{print $5}' \| sort -n \| tail -2]` |
| F13 | Cost today: the whole hook takes 0.32 s wall; `git write-tree` takes 0.012 s. | `[MEASURED: time .githooks/pre-commit; time git write-tree]` |
| F14 | When the index names a missing object, `git write-tree` inside the hook exits 128, and `git commit` then fails by itself (`Error building trees`, rc=1) whatever the hook decides. | `[MEASURED: scratch repo; git update-index --add --cacheinfo 100644,1111…1111,ghost; git commit]` |
| F15 | `.verify/` is git-ignored here, and each linked worktree has its own `.verify/runs` (the hook `cd`s to `git rev-parse --show-toplevel`, which is the worktree). | `[MEASURED: git check-ignore -v .verify/runs/x → .gitignore:15:.verify/]` · `[MEASURED: ls .claude/worktrees/agent-a791a8aea9df4ae78/.verify → runs]` |
| F16 | `.githooks/**` is on the protected-path list, so under autonomy a commit touching the hook needs an `Owner-Approved:` trailer (checked in commit-msg). | `[MEASURED: sed -n 100,116p scripts/autonomy.py → ".githooks/**"]` |
| F18 | CI gate 3 is a `grep -rn` with the pattern `'<[A-Z_]\{3,\}>'` over the roots `.claude .agents doc scripts AGENTS.md README.md` (stderr discarded). It is followed by four `grep -v`: `'doc/framework/'`, `'doc/templates/'`, `'scripts/bootstrap.sh'` and `'^\.claude/worktrees/'`. A hit fails it. The Azure copy is byte-identical. `scripts/bootstrap.sh` runs the same pipeline for its leftover report. `tests/ci/test_ci_examples.py` pins the four exclusions in `_GATE_3_EXCLUSIONS` and checks them against both CI and bootstrap. The `grep -v` filters match the whole `path:line:content` line, so a content line that mentions `doc/framework/` is also skipped. | `[MEASURED: sed -n 115,133p ci-examples/github-actions.yml; grep -n "LEFT=" ci-examples/azure-pipelines.yml scripts/bootstrap.sh; sed -n 344,384p tests/ci/test_ci_examples.py]` |
| F19 | Scan cost here. The CI pipeline over the working tree takes 0.033 s and finds 18 lines. The same pattern, roots and exclusions over the **index** (`git grep --cached -n -G`) take 0.027 s and give the **identical** 18 lines. Grepping only the paths staged against HEAD takes 0.008 s. | `[MEASURED: time (grep -rn … \| grep -v …); time (git grep --cached -n -G … \| grep -v …); diff of the two sorted outputs → identical; time (git diff --cached --name-only -z HEAD \| xargs -0 git grep --cached …)]` |
| F20 | **This template is red on gate 3 by design.** All 18 hits here are the five tokens `scripts/bootstrap.sh` substitutes: PROJECT ×14, FRONTEND_REPO ×7, FRONTEND_REPO_PATH ×3, PACKAGE ×3, BACKEND_REPO_PATH ×2 (each in angle brackets; counts are per token occurrence). `tests/ci/test_ci_examples.py::test_gate_3_is_red_on_this_repos_own_current_state` pins it. `scripts/check_neutrality.py` already uses "AGENTS.md still carries the PROJECT placeholder" as its template-or-project signal (line 171). | `[MEASURED: grep -oE '<[A-Z_]{3,}>' over the 18 lines \| sort \| uniq -c]` · `[MEASURED: sed -n 14,16p and 21,28p scripts/bootstrap.sh]` (the five keys) · `[MEASURED: sed -n 167,175p scripts/check_neutrality.py]` |
| F21 | **Both incidents were placeholder literals that bootstrap does not fill.** Replaying each commit's tree through the index scan, and dropping the five bootstrap tokens, gives: 7661338 → three lines in `doc/qa/QA-bugfix-gate3-worktree.md` (lines 20 and 21) and `doc/qa/REVIEW-bugfix-gate3-worktree.md` (line 27); e6b4daa → `doc/specs/SPEC-jarvis-coordinator.md:58`. Today's hook commits such a file: a fixture-style repo committed `doc/qa/QA-x.md` holding a non-bootstrap placeholder with rc=0. | `[MEASURED: GIT_INDEX_FILE=scratch git read-tree <commit>; git grep --cached … \| grep -v … \| grep -vE the five]` · `[MEASURED: fixture-style scratch repo with core.hooksPath .githooks; git commit → rc=0]` |
| F22 | `tests/framework/test_pre_commit.py::_clone_template` writes `AGENTS.md` as a one-line title holding the PROJECT placeholder, and copies `.githooks .agents scripts doc/memory doc/scars doc/templates`. Built that way, its index scan finds 3 lines, all PROJECT, and **0** lines with any other token. So the fixtures pass only if template mode allows the five tokens. Without template mode, every one of its 9 tests would be refused. | `[MEASURED: scratch repo built from the same dirs and AGENTS.md; LC_ALL=C git grep --cached … → 3 hits, 0 after dropping the five; git show :AGENTS.md \| grep -c → 1]` |
| F23 | `git grep --cached` inside the hook reads the index git is committing. With a placeholder only in an unstaged edit, `git commit -a` showed the hit. A plain `git commit` with the placeholder only in an untracked file showed nothing. Exit codes: 0 means hits, 1 means none (also for a pathspec that matches nothing, such as a missing `README.md`), and 128 means an error. `git grep` quotes odd paths (`"doc/a\nb.md":1:…`). Without `-I` it prints `Binary file doc/x.bin matches`, while macOS `grep -rn` printed nothing for the binary. Tokens that match neither tool: a 2-letter token, lower case, a hyphen inside, a non-ASCII letter. | `[MEASURED: scratch repos; hook printing $(git grep --cached …); git grep exit codes for a missing pathspec and a bad regex]` |
| F17 | Incident 1's tree cannot be replayed against its own record: the records from 2026-10-20 before 13:58Z were pruned, and none holds e6b4daa's tree `c75e9bca…`. Incident 2's tree `b519ed97…` has no record either, which matches "no gate run". | `[MEASURED: git rev-parse e6b4daa^{tree} 7661338^{tree}; grep -l over .verify/runs/*/record.json → no match]` |

## Requirements of this amendment

| # | Requirement | Source |
|---|---|---|
| AM3-R1 | The hook identifies "the staged tree" as the output of `git write-tree` run inside the hook with git's own environment untouched (F2), never `verify_record.py tree-hash` (F3). | PRD R5; F2, F3 |
| AM3-R2 | A record counts for the staged tree only when it is tier `full` or `handoff`, and its `tree.before` and `tree.after` are both equal to the staged tree. Fast records never count (F8). A run whose tree changed mid-run counts for neither tree. | PRD R5; F8, F9 |
| AM3-R3 | Among the records that count, the newest decides. If it is RED, the commit is refused, and the refusal names the record. | memory gate-exit-code-before-commit (incident 1) |
| AM3-R4 | Any other verdict never blocks. GREEN, INCOMPLETE and OK pass, and the hook prints the verdict word exactly as recorded. It never prints GREEN for a run that was not GREEN. | PRD R12; F6 |
| AM3-R5 | No usable record for the staged tree (none at all, only stale, only fast, only EMPTY, only unreadable) never blocks. It prints one `WARN` line naming the command that would produce a record. | doc/memory/ease-of-use-over-strictness.md; F7 |
| AM3-R6 | When the check itself cannot run (write-tree fails, or the lookup exits with anything other than 0 or 1), the commit is refused, and `--no-verify` is named as the escape. The lookup never prints a traceback. A missing recorder warns instead (a project without the verify tiers). | hostile-inputs memory ("never crashes, never reports green") |
| AM3-R7 | `--no-verify` still skips the hook, and the declared limits below are written into `doc/framework/ADAPTERS.md`, next to the existing pre-commit row. | PRD R13 ("tamper-evident, not tamper-proof"); ease-of-use ruling item 2 |
| AM3-R8 | The hook runs CI gate 3's placeholder scan, with the same pattern, roots and four exclusions, over the index being committed (F23), and refuses on any hit. It prints each hit line, and how many there were. | memory gate-exit-code-before-commit (both incidents, F21); coordinator REWORK 2026-10-22 |
| AM3-R9 | **Template mode.** When the index's `AGENTS.md` contains the PROJECT placeholder, hits whose only tokens are the five that `scripts/bootstrap.sh` substitutes are allowed. A line that also holds any other token is still a hit. Outside template mode, every token is a hit, exactly as in CI. | F20, F22; AM3-AC13 must stay green |
| AM3-R10 | A drift test keeps the hook's pattern, roots and exclusions equal to CI gate 3, and its allowed tokens equal to bootstrap's substitution keys. If the scan itself cannot run (`git grep` exits with anything other than 0 or 1), the commit is refused. | hostile-inputs memory; F18 |

## Acceptance Criteria

AM3-AC1 to AM3-AC13 live in one new file, **`tests/framework/test_pre_commit_verify_record.py`**.
AM3-AC14 to AM3-AC19 and AM3-AC21 live in a second new file,
**`tests/framework/test_pre_commit_placeholders.py`**. AM3-AC20 is one new test in
`tests/ci/test_ci_examples.py`. In both new files, each test
commits for real through `.githooks/pre-commit` in a throwaway repo, built the way
`tests/framework/test_pre_commit.py::_clone_template` builds one, with `.verify/` git-ignored. Its environment drops every `VERIFY_*` variable, the same way that
helper pops `MEMORY_DIR` and the others. verify-full exports `VERIFY_TEST_STEPS`, the budget
variables, `VERIFY_RUN_DIR` and `VERIFY_JUNIT_DIR` while `tests/framework/` runs inside it, and they
would change AM3-AC12's real `finalize` output (scope-discipline rule 5, "leaked environment
settings"). It
plants records as JSON files (no gate is run). A helper `_record(repo, name, tier, verdict, before,
after, ended_at)` writes one. "Refused" means the commit returns non-zero **and** `HEAD` is
unchanged. "Passes" means return code 0 and a new `HEAD`.

**RED-FIRST.** Before the hook changes, the engineer runs the new file against today's hook and
pastes the result. Every criterion asserts either a refusal or a line the hook does not print
today (`FAIL verify record`, `verify record:`, `WARN`, `FAIL placeholder scan`), so every test
must fail then, except AM3-AC10 (the `--no-verify` pin), AM3-AC13 (the existing file), the
pass-only rows of AM3-AC15, AC16, AC17 and AC18, and AM3-AC20 (which reads files and fails today
only because the hook holds no scan). Those pass before and after, and they guard against
over-blocking. AM3-AC14 and AM3-AC21 fail today because the commit goes through (F21).
The refusal cases fail today because the commit goes through (F1). The pass-with-a-line cases
guard against over-blocking: a version that refused them would fail them.

| # | Maps to | Given / When / Then |
|---|---|---|
| AM3-AC1 | R1, R2, R3 | Given everything is staged and a `full` record with verdict `RED` and before = after = `git write-tree`, when `git commit` runs, then it is refused, and the output contains `FAIL verify record` and the record's relative path. |
| AM3-AC2 | R4 | Given the same, but verdict `INCOMPLETE`, then it passes, the output contains `INCOMPLETE`, and the output does not contain `GREEN`. Same for `GREEN` (output contains `GREEN`), and for a `handoff` record with `OK` (output contains `OK`, not `GREEN`). |
| AM3-AC3 | R5 | Given a matching `handoff` record with verdict `EMPTY`, then it passes with a `WARN` line, and the output does not contain `verify record:`. |
| AM3-AC4 | R3 | (a) Given a matching RED record and a later matching GREEN record, then it passes. (b) Given a matching GREEN record and a later matching RED record, then it is refused. In both cases the directory names sort the **opposite** way to `ended_at`, which proves that `ended_at` orders them. (c) Given two matching records with the same `ended_at`, the directory name breaks the tie (the later name wins). |
| AM3-AC5 | R2, R5 | Each of these passes with exactly one `WARN no gate record for the staged tree` line, which names `scripts/verify-full.sh`: (a) a RED `full` record for a **different** tree (stale); (b) no `.verify` directory at all; (c) `.verify/runs` empty, or holding only directories without `record.json` (F11); (d) a RED `fast` record with all-null `tree` (F8); (e) a RED `full` record whose `tree.after` equals the staged tree but whose `tree.before` differs (the tree changed mid-run). |
| AM3-AC6 | R1 | Hostile commit forms (the hook must use git's index, not `.git/index`). (a) Given `f` edited and **not** staged, and a RED record on the working tree, when `git commit -a` runs, then it is refused. (b) Given `f` and `g` edited, a RED record on the working tree, when `git commit -- f` runs (the commit tree leaves out `g`), then it passes with `WARN`. (c) Given the same edits, and a RED record whose tree equals the `commit -- f` tree, then `git commit -- f` is refused. A version that calls `tree-hash` fails (b) or (c) (F3). A version that removes `GIT_INDEX_FILE` makes `write-tree` fail (F3), so it refuses (b) and fails it. |
| AM3-AC7 | R1, R2 | Given a linked worktree (`git worktree add`) whose own `.verify/runs` is empty, and a matching RED record in the **main** checkout's `.verify/runs`, when the worktree commits that tree, then it passes with `WARN`. A run in another checkout never counts (F15). |
| AM3-AC8 | R2, R5, R6 | Hostile records. None of these may print a traceback, or a `verify record:` pass line. Each one (except the RED-match rows) passes with a `WARN` line that names the bad record's path, escaped so that a newline or control character in a directory name prints as `\n`/`\xNN`. The record is: malformed JSON; truncated JSON; an empty file; a JSON array; `tree` given as a number; `tree.after` given as a list; `verdict` missing; `verdict` given as `red` or `RED ` or `Red` (never treated as RED or as a pass; it is unreadable); non-UTF-8 bytes; a file over 1 MiB (not read beyond the cap); `record.json` as a symlink to a RED record; a run directory that is a symlink; `record.json` that is a directory. **RED-match rows:** (i) a matching readable RED record plus a **newer** unreadable record → still refused (an unreadable run never cancels a RED); (ii) a matching readable GREEN record plus a newer unreadable record → passes with `WARN` and does **not** print `GREEN` (it never falls back silently to the older pass). |
| AM3-AC9 | R6 | (a) Given `scripts/verify_record.py` replaced in the throwaway repo by one that exits 3, when committing, then it is refused with `FAIL verify record — the check could not run (exit 3)` and the output names `--no-verify`. (b) Given `scripts/verify_record.py` deleted, then it passes with `WARN … recorder missing`. (c) Given an index that names a missing object (F14), then the commit fails, and the hook's output contains `staged tree could not be hashed`. |
| AM3-AC10 | R7 | Given a matching RED record, when `git commit --no-verify` runs, then it passes. This pins the declared escape, so that a later change cannot quietly remove it or start claiming it is closed. |
| AM3-AC11 | R3 | Given a matching RED record and also a failing memory-lint plant, then the output shows **both** `FAIL scripts/memory_lint.py` and `FAIL verify record`. The new check adds to the hook's existing `fail` flag and never short-circuits the other four checks. |
| AM3-AC12 | R2, R4 | Real recorder output, not a hand-written record. Given everything is staged, and a record produced in the throwaway repo by the real recorder (`verify_record.py finalize --tier full --run-dir .verify/runs/D --tree-before $(git write-tree) --tree-after $(git write-tree)` over a `steps.tsv` holding one TODO step, the same shape as this template's own INCOMPLETE runs, F6), when committing, then it passes and prints `INCOMPLETE`. A second record made the same way over a step with exit 1 (verdict RED) gets the commit refused. This test never runs `verify-full.sh` itself. That would take minutes, and running it inside verify-full's own `framework` step would recurse. |
| AM3-AC13 | R5, R9 | Unchanged files must stay green: `python3 -m pytest tests/framework/test_pre_commit.py -q` passes with no edit to that file. Its fixtures have no `.verify`, so they hit AM3-AC5(b). Their placeholder hits are PROJECT only, and their `AGENTS.md` puts them in template mode (F22). |
| AM3-AC14 | R8 | **Project mode** (the staged `AGENTS.md` has no PROJECT placeholder). Given a staged `doc/qa/QA-x.md` whose line 1 holds an upper-case angle-bracket token of 3 or more letters (the test builds it as `"<" + "ABC_DEF" + ">"` so that its own source does not trip gate 3), when committing, then it is refused, and the output contains `FAIL placeholder scan` and `doc/qa/QA-x.md:1:`. The same file in **template mode** is also refused (it is not one of the five). |
| AM3-AC15 | R8 | Exclusions and roots are equal to CI's. In project mode, these pass: the token placed in `doc/framework/x.md`, in `doc/templates/x.md`, or in `scripts/bootstrap.sh`; a `doc/x.md` line whose content also says `doc/framework/` (the content quirk, F18); a force-added (`git add -f`) `.claude/worktrees/a/x.md`; and files outside the roots (`src/x.py`, `tests/x.py`, `ci-examples/x.yml`). These are refused: `doc/worktrees-notes.md`, `.claude/worktreesX/x.md`, `doc/.claude/worktrees/x.md`, `README.md`, `AGENTS.md`. |
| AM3-AC16 | R9 | Template mode. (a) A staged `.claude/agents/x.md` holding the PROJECT and PACKAGE tokens passes, and so does each of the other three bootstrap tokens. (b) A line holding the PROJECT token **and** a non-bootstrap token is refused. (c) In project mode, `scripts/x.py` holding the PROJECT token is refused. (d) Hostile: `AGENTS.md` has the PROJECT placeholder in the working tree, but the staged version does not, so the run is project mode (the index decides) and case (c) is refused. `AGENTS.md` absent from the index is project mode. A PROJECT token in some other file does not switch on template mode. (e) A near-miss of a bootstrap token, such as `PROJECTS` or `FRONTEND_REPO_PATHS` in angle brackets, is refused in template mode. |
| AM3-AC17 | R8 | The scan reads what is committed, never the working tree (F23). (a) A token only in an untracked file → passes. (b) A token only in an unstaged edit, with plain `git commit` → passes. (c) The same edit with `git commit -a` → refused. (d) A staged deletion of the only file holding a token → passes. (e) `git commit -- f`, where the token is staged in `g` but not in `f` → passes. |
| AM3-AC18 | R8, R10 | Hostile shapes. None prints a traceback. These pass: the 2-letter token, the lower-case token, the hyphenated token, the non-ASCII-letter token (F23), and a binary file holding the token (`-I`, matching CI's discarded binary message, limit 10). A file named with a newline under `doc/` that holds a token is refused, and the output shows git's quoted path on one line. More than 20 hit lines print the first 20, then `… and N more` with the true N. |
| AM3-AC19 | R10 | Given a `PATH` shim named `git` that delegates to the real git except for `grep`, which exits 2, when committing, then it is refused with `FAIL placeholder scan — the scan could not run (git grep exit 2)`. |
| AM3-AC20 | R10 | Drift, in `tests/ci/test_ci_examples.py`. The pre-commit file holds the CI pattern string `'<[A-Z_]\{3,\}>'`, the CI roots string, and each `grep -v` needle from `_GATE_3_EXCLUSIONS`. Its `grep -v '` count equals `len(_GATE_3_EXCLUSIONS)`. Its allowed-token set equals the keys of bootstrap's `subs` table (parsed from `scripts/bootstrap.sh`). Hostile: the comparison helper, run on a planted copy of the hook text with one extra exclusion, one missing exclusion, or a sixth allowed token, names the difference. |
| AM3-AC21 | R8 | Real incidents as regression pins. In a fixture-style repo (template mode), staging the exact content of `git show 7661338:doc/qa/QA-bugfix-gate3-worktree.md`, or of `git show e6b4daa:doc/specs/SPEC-jarvis-coordinator.md`, is refused and names that file. If the commit objects are unreachable (a shallow clone), the test skips and says why. It never passes vacuously. |

## Functional Behavior

**Hook (`.githooks/pre-commit`)**, appended after the existing four-check loop, before the
`blocked` summary line `[INFERRED]` (the pseudocode follows the current file's style):

```
if [ ! -f scripts/verify_record.py ]; then
  echo "pre-commit: WARN verify record not checked — recorder missing (scripts/verify_record.py)"
elif ! staged=$(git write-tree 2>/dev/null); then          # GIT_INDEX_FILE left as git set it (F2)
  echo "pre-commit: FAIL verify record — staged tree could not be hashed"; fail=1
else
  out=$(python3 -I scripts/verify_record.py commit-check --tree "$staged" 2>&1); rc=$?
  case $rc in
    0) [ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/pre-commit: /' ;;
    1) printf '%s\n' "$out" | sed 's/^/pre-commit: /'; fail=1 ;;
    *) echo "pre-commit: FAIL verify record — the check could not run (exit $rc)"; fail=1 ;;
  esac
fi
```

The existing summary line (`blocked — … --no-verify skips this hook, not CI …`) already names the
escape, and it prints whenever `fail=1`.

**Placeholder scan**, appended after the record check. It runs whether or not the recorder exists.
The PROJECT placeholder is written below as `$mark`, because this spec lives under `doc/`, which
gate 3 scans. The hook may spell it literally: `.githooks/` is not a gate-3 root.

```
# CI gate 3 (ci-examples/github-actions.yml "ไม่มีตัวยึดหลงเหลือ") over the index being committed.
# Keep the pattern, roots and grep -v list equal to it: tests/ci/test_ci_examples.py checks.
hits=$(LC_ALL=C git grep --cached -I -n -G '<[A-Z_]\{3,\}>' -- .claude .agents doc scripts AGENTS.md README.md); grc=$?
if [ "$grc" -gt 1 ]; then
  echo "pre-commit: FAIL placeholder scan — the scan could not run (git grep exit $grc)"; fail=1
else
  hits=$(printf '%s\n' "$hits" | grep -v 'doc/framework/' | grep -v 'doc/templates/' \
         | grep -v 'scripts/bootstrap.sh' | grep -v '^\.claude/worktrees/' || true)
  if git show :AGENTS.md 2>/dev/null | grep -qF "$mark"; then        # template mode (R9)
    hits=$(printf '%s\n' "$hits" | sed -E 's/<(PROJECT|PACKAGE|BACKEND_REPO_PATH|FRONTEND_REPO_PATH|FRONTEND_REPO)>//g' ...)
    # keep the ORIGINAL line for every line that still matches after the five are removed
  fi
  [ -n "$hits" ] && { echo "pre-commit: FAIL placeholder scan — N line(s) CI gate 3 would fail on:"; first 20 lines indented; "… and N more"; fail=1; }
fi
```

The engineer chooses how to keep the original lines (an `awk` over the line, or a paired loop), but
must not print a stripped line. `-I` and `LC_ALL=C` are deliberate: limits 10 and 11.

**Lookup (`verify_record.py commit-check --tree HASH [--runs DIR]`)**, where `--runs` defaults to
`.verify/runs` relative to the cwd. The hook has already `cd`'d to the top level.

1. If `--runs` is missing or not a real directory (a symlink counts as missing), print the
   no-record WARN line and exit 0.
2. For each direct child `D` of runs, sorted by name: skip `D` if it is a symlink or not a
   directory. If `D/record.json` does not exist, skip it silently (F11: aborted or TODO runs). If it
   exists but is a symlink, not a regular file, over 1 MiB, not UTF-8, not a JSON object, or has
   no string `verdict` in {GREEN, INCOMPLETE, RED, OK, EMPTY}, or no `tree` object with string-or-null
   `before`/`after`, or no `ended_at` string, then mark it **unreadable** and remember its name.
3. A readable record **matches** when `tier` ∈ {full, handoff} and `tree.before == tree.after ==
   HASH`.
4. Order the matches by `(ended_at, directory name)`. The last one is the newest match.
5. Decide:
   - newest match is RED → print `FAIL verify record — the newest gate run for the staged tree is RED (.verify/runs/D/record.json)` and exit 1;
   - otherwise, if any unreadable record's name sorts after the newest match's name (or there is no
     match), print `WARN unreadable gate record ignored: …` for each one, using the same escaping;
   - newest match is GREEN, INCOMPLETE or OK and nothing unreadable is newer → print
     `verify record: <its verdict> for the staged tree (.verify/runs/D/record.json)`, with the verdict
     verbatim, and exit 0;
   - no match, or the newest match is EMPTY, or an unreadable record is newer than a non-RED match
     → print `WARN no gate record for the staged tree — run scripts/verify-full.sh (scripts/verify-handoff.sh when opted in) before committing; CI runs the gate regardless`
     and exit 0.
6. Any unexpected exception → print one line `commit-check: internal error: <exception class>` to
   stderr and exit 2. The hook turns that into a refusal (AM3-AC9a). No traceback, and no record
   content in the output (AGENTS.md §8: names and counts only).

Escaping reuses the recorder's existing `_escape` (`[MEASURED: sed -n 723,729p scripts/verify_record.py]`
defines it) so the output style matches the handoff tier.

## Technical Design

- **Files to create/modify** (one owner, this amendment. `scripts/verify_record.py` was owned by
  increment A+C, which is merged (c8c73e1), so the merge order is: A+C first (done), then this):
  - `.githooks/pre-commit`: modify (the block above). It is a protected path (F16), so under
    autonomy its commit needs `Owner-Approved:`.
  - `scripts/verify_record.py`: add `commit-check` (a parser entry in `main()`, plus one function
    of about 60 lines). Add one line to the module docstring's subcommand list. No existing function
    changes.
  - `tests/framework/test_pre_commit_verify_record.py`: new.
  - `tests/framework/test_pre_commit_placeholders.py`: new (AM3-AC14 to AC19, AC21).
  - `tests/ci/test_ci_examples.py`: one new test (AM3-AC20). It reuses `_gh_step`,
    `_GATE_3_EXCLUSIONS` and `_BOOTSTRAP`, and nothing else changes. Owner: this amendment. The
    file's earlier owner, the gate-3 worktree bugfix, is merged, so the merge order is that fix, then this.
  - `doc/framework/ADAPTERS.md`: the C1 row (line 68) and the adapter-file line (63) add "the
    newest gate record for the staged tree is not RED" and "no placeholder CI gate 3 would fail on"
    to the list of pre-commit checks, plus the declared limits below.
  - `doc/memory/gate-exit-code-before-commit.md`: set `mechanism:` to the hook, its two test files,
    and the limit "missing record warns only; placeholder literals block".
  - `doc/tasks/backlog.md`: the C2 row and the parked row (line 82) → done. This is the coordinator's
    file, so it is listed for the coordinator, not the engineer.
- **Interface:** `python3 -I scripts/verify_record.py commit-check --tree HASH [--runs DIR]`, where HASH is whatever `git write-tree` printed. The lookup does not check its length or alphabet (a SHA-256 repository prints 64 hex characters, and a length check would refuse every commit there). It only compares it for equality.
  Exit 0 means pass (it may print WARN or `verify record:` lines), exit 1 means refuse, and any other
  exit means the check failed. Stdlib only, Python 3.9+, matching the file's header.
- **Data:** read-only over the existing `record.json` schema 1. No new fields. No writes.
  The hook never runs a gate.
- **Cost:** one `git write-tree` (0.012 s, F13), plus reading at most about 60 small files (three
  buckets of 20, F11, F12) `[INFERRED]` well under 0.1 s. The engineer measures the hook
  before and after (`time .githooks/pre-commit`) and reports both numbers.
- **Placeholder scan cost:** 0.027 s over the index here (F19).
- **verify-fast routing needs no change:** `tests/framework/test_pre_commit_placeholders.py` matches the
  existing `tests/framework/test_pre_commit*` route. A touch to `ci-examples` or `scripts/bootstrap.sh`
  runs `tests/ci/`, where AM3-AC20 lives. But a touch to `.githooks` alone does not run `tests/ci/`
  (limit 12). Beyond that, a touch to `.githooks` or `tests/framework/test_pre_commit*`
  already runs `tests/framework/` and `tests/hooks/`, and a touch to `scripts/verify*` already runs
  the verify-tier suites `[MEASURED: grep -n "githooks\|test_pre_commit\|scripts/verify" scripts/verify-fast.sh]`.

## Declared limits

These go into ADAPTERS.md, under the ease-of-use ruling: they are written down, not chased.

1. **A missing record warns and does not block.** Incident 2 (a commit with no gate run) still goes
   through. The difference now is that a `WARN no gate record` line sits in the commit output.
   CI gate 3 caught incident 2 on the branch, and it remains the control.
2. **Any edit after a RED run, and then a commit without re-running, only warns.** That RED was
   for another tree. Under PRD R5 it is not evidence about this tree, either way.
3. **Partial staging.** When unstaged edits or untracked files exist, the working-tree record cannot
   match the index (F5). The commit warns, even right after a gate run. The fix is to stage
   everything, or to re-run the gate after staging.
4. **Records are agent-writable files.** A hand-written GREEN record, or a deleted RED one, passes.
   That counts as deliberate fraud (scope-discipline rule 5). The merge gate's runner record and CI
   are the controls.
5. **`--no-verify`** skips this check together with the other four. CI is the gate nobody can skip.
6. **Newest is by `ended_at` to the second, then by directory name.** Two runs that end in the same
   second are ordered by name (timestamp, then PID). The PID is not monotonic.
7. **Records in another checkout or worktree never count** (F15), even for an identical tree.
8. **Template mode trusts one line.** A bootstrapped project whose `AGENTS.md` again contains the
   PROJECT placeholder (quoted in prose, say) gets the five tokens allowed. CI gate 3 still fails it.
   It is the same signal `check_neutrality.py` uses, with the same weakness (F20).
9. **The scan sees the commit, not CI's checkout of the branch.** A placeholder already committed
   with `--no-verify` blocks every later commit until it is fixed. That is deliberate: CI is red on
   it anyway.
10. **Binary files are skipped (`-I`).** `[INFERRED]` GNU grep 3.5 and later print "binary file
    matches" to stderr, which gate 3 discards, so CI on such a runner ignores binaries too. macOS
    `grep -rn` printed nothing for one (F23).
11. **`LC_ALL=C`.** CI runs in the runner's locale. A runner whose locale makes `[A-Z]` match lower
    case would be stricter than the hook. `[INFERRED]`; not measured on a CI runner.
12. **Drift is caught by `tests/ci/` (AM3-AC20).** verify-fast runs that suite for a touch to
    `ci-examples` or bootstrap, but not for a touch to `.githooks` alone. verify-full and CI always
    run it.
13. **Quoted paths.** `git grep` quotes odd file names (F23). A quoted `.claude/worktrees/…` path
    would escape the anchored exclusion. Such files are git-ignored here (`.gitignore:14`) and need
    `git add -f`.

## Decisions (ADR-style)

- **D1. "Staged tree" = `git write-tree` inside the hook, with git's environment untouched.**
  Context: the record hashes the working tree through a throwaway index, and its git helper strips
  `GIT_INDEX_FILE` (F3). Inside pre-commit, git points `GIT_INDEX_FILE` at the index it will commit
  (F2). Decision: the hook computes the hash and passes it with `--tree`. The lookup never hashes
  anything itself. Consequences: correct for `commit`, `commit -a` and `commit -- path` (F2). It
  costs 0.012 s (F13). AM3-AC6 pins it.
- **D2. Match means `tier ∈ {full, handoff}` and `before == after == staged`, with no time-based
  staleness.** Context: PRD R5, "no result counts as evidence for a tree other than the one it ran
  on". Fast records carry no tree (F8). Decision: a stale record and a missing record are the same
  case. Consequences: one rule instead of two. A change during the run disqualifies the record.
- **D3. Only an exact-match RED blocks.** Context: incident 1 committed on the very tree the gate had
  just judged RED. Decision: refuse on it. Consequences: incident 1's shape is blocked by machine.
  The edit-after-RED variant only warns (limit 2). I considered and rejected "a RED on the current
  `HEAD` blocks every commit until a non-RED run", because it uses a record about another tree
  as evidence (against R5), and it wedges docs commits after any red run.
- **D4. A missing record warns. It does not block.** Context: blocking would cost one 235–378 s
  verify-full run per commit, docs commits included (F7). No cheap tier writes a tree-bound record
  today: fast has no tree (F8), and in this template it writes no record at all, while handoff is
  opt-in (F9). The other ways to make it cheap all change `verify-fast.sh` and `verify_record.py`'s
  finalize, which is more scope (smallest-useful-scope ruling). Blocking would also turn every
  existing commit test red, because their fixtures have no `.verify` (9 tests in
  `tests/framework/test_pre_commit.py`), and it would wedge every fresh clone's first commit.
  Decision: warn, and name the command. Consequences: incident 2 is visible but not prevented,
  and that is stated as limit 1. If a third "no gate run" incident occurs, the next step is a
  cheap, tree-bound fast record (parked, below), not a block on full runs.
- **D5. INCOMPLETE, GREEN and OK pass. EMPTY warns.** Context: PRD R12 keeps the meanings, and the
  template's own gate is INCOMPLETE (F6). EMPTY means nothing was verified (F10). Decision: as
  stated, and the verdict is printed verbatim. Consequences: the hook never says GREEN for
  INCOMPLETE (AM3-AC2).
- **D6. Bad evidence warns, and a broken check refuses.** Context: the hostile-inputs ruling says
  never crash, never leak, never report green. The ease ruling says don't wedge people on accidents.
  Decision: an unreadable or odd record is ignored with a named WARN. It never cancels a RED, and
  never lets an older pass speak for a newer unknown run (AM3-AC8 i/ii). A lookup crash or a
  write-tree failure refuses (AM3-AC9). Consequences: a bug in the gate is loud. Ordinary
  corruption is only a warning.
- **D7. Put the lookup in `verify_record.py` as `commit-check`, not in a new script.** Context: that
  file owns the record schema and `_escape`. Decision: add the subcommand there. Consequences:
  one owner of the schema. The verify-tier suites re-run on every touch (already routed).
- **D8. Do not change any tier script.** Fast stays tree-less. Consequences: zero risk to the
  merged A+C increment. D4's limit stays.
- **D9. Scan the whole index, limited to gate 3's roots.** Context: three scopes were measured (F19):
  the working tree (0.033 s, CI's exact command), the whole index (0.027 s), and the staged-vs-HEAD
  paths only (0.008 s). Decision: the whole index. It is what the commit will contain, so it is what
  CI sees when it checks the commit out, and it gave the identical 18 lines here. Rejected: the
  working tree, because it blocks on untracked or unstaged files that are not being committed (F23).
  Also rejected: changed paths only. The 0.02 s it saves buys a commit that passes the hook while CI
  is red on a placeholder already in the tree (limit 9 is the honest version of that). Consequences:
  correct for `-a` and `-- path` (AM3-AC17), at about 0.03 s.
- **D10. Template mode via the index's `AGENTS.md`.** Context: the template is red on gate 3 by
  design (F20), and the existing pre-commit fixtures commit PROJECT tokens (F22). Decision: when the
  staged `AGENTS.md` holds the PROJECT placeholder, allow only bootstrap's five tokens. The check is
  per line, not per file. Consequences: a fresh clone commits freely before bootstrap. Both incidents
  are still refused, because neither was one of the five (F21). After bootstrap, the hook equals CI
  exactly. Rejected: "skip the scan in template mode", because it would have let both incidents
  through in this very repo.
- **D11. A scan hit refuses, unlike a missing record.** Context: the ease-of-use ruling asks for
  low cost and no wedging on accidents. Decision: refuse, because the check costs about 0.03 s, the
  fix is local and obvious (the hit line is printed), and a hit is a certain CI failure, not a
  maybe. Consequences: the coordinator's REWORK decision is implemented. `--no-verify` remains the
  escape.
- **D12. The drift test lives in `tests/ci/test_ci_examples.py`.** Context: gate 3's exclusion
  list and its bootstrap pin already live there (F18). Decision: add one test beside them that reads
  the hook text. Consequences: one list (`_GATE_3_EXCLUSIONS`) governs CI, bootstrap and the hook.
  A `.githooks`-only touch does not trigger it in verify-fast (limit 12).

## Affected tests / affected files

| File | Why it is affected | Expected change |
|---|---|---|
| `.githooks/pre-commit` | gains the check | modify |
| `scripts/verify_record.py` | gains `commit-check` | add a subcommand; existing functions unchanged |
| `tests/framework/test_pre_commit_verify_record.py` | AM3-AC1 to AC13 | new |
| `tests/framework/test_pre_commit_placeholders.py` | AM3-AC14 to AC19, AC21 | new |
| `tests/framework/test_pre_commit.py` (9 tests) | copies all of `.githooks/` and `scripts/` into a throwaway repo and commits through pre-commit. It has no `.verify` and no exact-output assertions (it uses only `in` and return codes). Its PROJECT tokens pass only in template mode (F22). | unchanged, must stay green (AM3-AC13) |
| `tests/ci/test_ci_examples.py` (gate-3 tests, lines 330–560) | owns `_GATE_3_EXCLUSIONS` and pins CI against bootstrap; `test_gate_3_is_red_on_this_repos_own_current_state` pins F20 | one new test (AM3-AC20); the existing tests stay unchanged and green |
| `scripts/bootstrap.sh`, `ci-examples/github-actions.yml`, `ci-examples/azure-pipelines.yml` | the sources the drift test compares against | unchanged |
| `tests/framework/test_bootstrapped_project.py` | runs bootstrap; does not install the hooks (absent from the `core.hooksPath` search) | unaffected |
| `tests/hooks/test_verify_tiers.py`, `test_verify_scripts.py`, `test_verify_handoff.py`, `test_verify_merge.py`, `test_regression_verify_tiers_qa.py` | import or run `verify_record.py` | unchanged, must stay green; none enumerates the subcommands (only `tree-hash` is called by name, at test_verify_tiers.py:1419) |
| `tests/ci/test_ci_examples.py` (verify-merge tests) | runs and copies `verify_record.py` (lines 614, 648) | unchanged, must stay green |
| `tests/framework/test_commit_msg_owner_trailer.py`, `test_check_fix_has_test.py`, `test_regression_commit_msg_autonomy.py`, `tests/hooks/test_autonomy_stdlib_shadowing.py` | install `.githooks/commit-msg` only (they copy that single file) | unaffected; listed because they appear in the search |
| `tests/hooks/test_guard_autonomy_paths.py` | lists `.githooks/pre-commit` as a protected path | unaffected (the path is unchanged) |
| `doc/framework/ADAPTERS.md` | declares the pre-commit checks and their limits | modify lines 63 and 68 |
| `doc/memory/gate-exit-code-before-commit.md` | `mechanism: none` today | set `mechanism:` |
| `doc/tasks/backlog.md` | C2 row (line 112) and parked row (line 82) | coordinator marks it done |
| `ci-examples/*.yml` | do not reference the hook; gate 3 is the source copied | unaffected |

How this list was built:
- `grep -rln "core.hooksPath\|\.githooks" tests/ ci-examples/` gave 6 test files. For each one, I
  grepped `copytree\|\.githooks` to see whether it installs pre-commit or only commit-msg.
- `grep -rln "verify_record\|\.verify/" tests/` gave 6 files.
- `grep -rn "pre-commit\|githooks" ci-examples/ tests/ci/` gave no hits.
- `grep -rln "pre-commit\|githooks" scripts/ doc/framework/ AGENTS.md .agents/` gave `AGENTS.md:156`
  (the "enable once per clone" line, unchanged) and ADAPTERS.md 63, 64, 68, 98 (63 and 68 change).
- `grep -n "add_subparsers\|subcommand\|tree-hash\|--help" tests/hooks/test_verify_*.py tests/ci/test_ci_examples.py`.
- For the placeholder scan: `grep -n "LEFT=\|grep -rn\|grep -v" ci-examples/*.yml scripts/bootstrap.sh`,
  and `grep -n "def test.*gate_3\|_GATE_3_EXCLUSIONS\|worktrees" tests/ci/test_ci_examples.py`. The
  fixture's content was measured by building it (F22).

## Traceability

- PRD R5 → AM3-R1, R2 → AM3-AC1, AC4, AC5, AC6, AC7
- PRD R12 → AM3-R4 → AM3-AC2, AC12
- PRD R13 (tamper-evident wording) → AM3-R7 → AM3-AC10 and the declared limits
- memory gate-exit-code-before-commit, incident 1 → AM3-R3 → AM3-AC1, AC4, AC11
- memory gate-exit-code-before-commit, incident 2 → AM3-R5 → AM3-AC3, AC5 (warn, by D4)
- memory hostile-inputs → AM3-R6 → AM3-AC8, AC9
- memory ease-of-use → AM3-R5, R7 → AM3-AC5, AC10, AC13
- memory gate-exit-code-before-commit, both incidents' cause (F21) → AM3-R8 → AM3-AC14, AC15, AC17, AC18, AC21
- template clones and existing fixtures → AM3-R9 → AM3-AC13, AC16
- drift and scan failure → AM3-R10 → AM3-AC18, AC19, AC20

That is 10 requirements mapped to 21 criteria. Every requirement has at least one criterion. Each
criterion's test file is named above the AC table.

## Parked

- **A cheap tree-bound fast record**, so that a docs-only commit could earn a record in seconds:
  verify-fast would pass `--tree-*`, and the hook would accept a fast `OK` for paths it covered.
  Trigger: a third "no gate run" incident. Displaced by D4, D8.
- **A hint in the WARN line.** When nothing matches, but the newest full or handoff record on the
  current `HEAD` is RED, the hook could add "the last gate run here was RED, for a different tree". It
  would inform, not gate, which keeps it within R5. Parked to keep this amendment to one rule. Trigger:
  a partial-staging commit on RED (limit 3) reaching CI.

## Approval history

- **2026-10-22 — drafted.** ba-sa, at Jarvis's request (un-parking checklist C2). The draft is based
  on the measurements above, taken at `96bebdb`.
- **2026-10-22 — REWORK 1 (Jarvis).** D3 and D4 kept. The parked idea "run CI gate 3's placeholder
  scan at commit time" is un-parked into this amendment: AM3-R8 to R10, AM3-AC14 to AC21, F18 to
  F23, D9 to D12, and limits 8 to 13.
