# Review: Gate 3 skips agent worktrees under .claude/worktrees/

Status: In Review
Owner: reviewer
Upstream: NO_SPEC_BUGFIX — doc/tasks/backlog.md item B1
Author-run: afbef35185650415b, ac4c5000b7ebc15d9, abe0851416b28a4ac
Reviewer-run: ab890f306d7777f69
Date: 2026-10-22

Verdict: PASS

The round-2 gap is closed. Mutant m7 (`'^\.claude/worktrees'`, trailing slash dropped) now turns 2 tests red: the new `.claude/worktreesX/x.md` and `.claude/worktrees.md` cases. Every plausible widening, removal or un-anchoring of the filter tried in this review is caught. All four criteria pass.

## Read from

- Upstream: the bug reproduction in the brief (B1). A placeholder fixture under the untracked `.claude/worktrees/` turns CI gate 3 ("ไม่มีตัวยึดหลงเหลือ") red in both ci-examples.
- Change: the uncommitted diff in worktree `.claude/worktrees/agent-afbef35185650415b` against HEAD 018f11b. `git diff --stat` shows 3 files, `98 insertions(+), 2 deletions(-)`: `ci-examples/azure-pipelines.yml` (2), `ci-examples/github-actions.yml` (3: the filter plus a comment) and `tests/ci/test_ci_examples.py` (+95).
- Not read: the author's conversation. Every result below was re-run in this review.

Mutation method: each mutant is an rsync copy of the worktree in the reviewer scratchpad (`r3/m*`), with `.git`, `worktrees` and `__pycache__` excluded. In each copy the shipped ` | grep -v '^\.claude/worktrees/'` is rewritten in both YAML files (only in the Azure file for m5), with an assert that the original text was present. The author's files were never edited. Each copy then ran `python3 -m pytest tests/ci/test_ci_examples.py -q -p no:cacheprovider`. Note: the first mutation pass in this review ran under zsh, which does not word-split the file list, so no mutant was applied (every run showed 30 passed and a FileNotFoundError). That pass is discarded, and every mutant was re-run from a bash script.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| AC1 | Worktree placeholders under top-level `.claude/worktrees/` no longer fail gate 3, in both examples, and the two scripts stay identical | PASS | The brief's verify command gives `30 passed in 3.25s`. `test_gate_3_ignores_an_agent_worktree_under_dot_claude` runs the shipped gate with a fixture at `.claude/worktrees/agent-x/doc/f.md` and passes. m1 (filter removed, which is the pre-fix behaviour) turns it red. m5 (filter removed from the Azure file only) gives `FAILED ...::test_gate_3_scripts_are_byte_identical_between_the_two_files`, `1 failed, 29 passed`. |
| AC2 | Placeholders in every other path still fail | PASS | The parametrized `test_gate_3_still_scans_real_paths_next_to_a_worktree` asserts exit 1 and the exact `<rel>:1:leftover <ABC_DEF>` line for `.claude/agents/x.md`, `doc/x.md`, `doc/worktrees-notes.md`, `doc/.claude/worktrees/x.md`, `.claude/worktreesX/x.md` and `.claude/worktrees.md`. A content-line test covers a `doc/x.md` line that mentions `.claude/worktrees/`. All are green at baseline (30 passed). |
| AC3 | No other gate loosened, and the tests go red if the filter is removed, widened or un-anchored | PASS | `git diff -U0 ci-examples` shows only the gate-3 pipe in both files plus one comment line. Mutants: m1 (removed) gives `8 failed, 22 passed`. m2 (`'worktrees'`) gives `5 failed`. m3 (`'^\.claude/'`) gives `3 failed`. m4 (`'.claude/worktrees/'`, anchor dropped) gives `2 failed`. m5 (Azure only) gives `1 failed`. m6 (`'\.claude/worktrees/'`) gives `2 failed`. **m7 (`'^\.claude/worktrees'`, slash dropped) gives `2 failed` ([.claude/worktreesX/x.md], [.claude/worktrees.md]), so the round-2 gap is closed.** m8 (`'^\.claude/worktree'`) gives `2 failed`. m9 (`'^.claude/worktrees/'`, dot unescaped) gives `30 passed`. That is an equivalent mutant, not a gap: gate 3 only scans `.claude .agents doc scripts AGENTS.md README.md`, so no grep output line can start with any character other than `.` followed by `claude/worktrees/`. m9 cannot skip anything the shipped filter scans. |
| AC4 | The tests run the shipped gate text | PASS | `_run_gate_3` calls `_extract_gate_3_script`, which takes the step's `run` text from the YAML. Mutants m1 to m8 edited only the YAML, and each turned tests red. The Azure copy is tied to it by the byte-identical test (m5). |

Exit gate: `scripts/verify-full.sh` ran in the worktree and exited 0 (`rc=0`). Below, the scar-forge line is shortened and the final `record:` path line is left out. Everything else is quoted as printed:

```
EXIT GATE — full verify
  TODO lint              not configured — this step verified NOTHING
  TODO format            not configured — this step verified NOTHING
  TODO tests             not configured — this step verified NOTHING
  OK   hooks             (175s) 1303 passed in 174.51s (0:02:54)
  OK   ci-examples       (4s) 30 passed in 3.30s
  OK   scar-forge        (0s) LIMIT (stated limit): ...
  OK   coordinator       (4s) 155 passed in 3.38s
  OK   framework         (44s) memory: 0 problem(s) in .../agent-afbef35185650415b/doc/memory
counts: not configured — executed == collected NOT checked
EXIT GATE INCOMPLETE — 3 step(s) not configured: lint format tests
Everything configured passed, and that is ALL this run proves.
Fill those steps in scripts/verify-full.sh before treating this output as a gate.
```

## Defects (if FAIL)

None.

## Hostile inputs tried

- `.claude/worktrees/agent-x/doc/f.md` → skipped. This is the intended skip.
- `doc/.claude/worktrees/x.md` (nested under another root) → red, and pinned (m4 and m6 caught).
- `.claude/worktreesX/x.md`, `.claude/worktrees.md` (look-alike prefixes) → red, and now pinned (m7 and m8 caught).
- `doc/worktrees-notes.md` (name contains `worktrees`) → red, and pinned (m2 caught).
- `.claude/agents/x.md` (a sibling under `.claude/`) → red, and pinned (m3 caught).
- A content line that mentions `.claude/worktrees/` next to a placeholder → red, and pinned.
- An unescaped dot (m9) → survives, but it is an equivalent mutant for the scanned roots (see AC3).
- The case variant `.claude/Worktrees/` was checked in round 2: it is reported on a case-sensitive filesystem. It was not re-run in this round.

## Parked

- `test_gate_3_exclusions_match_bootstraps_own_leftover_check` still says "identical three exclusions". The CI gate now has four, while `scripts/bootstrap.sh` keeps three. The drift is the harmless direction, and both the file and the problem are outside the diff and the four criteria, so this is backlog material. (Carried over from rounds 1 and 2.)
- Proposed LIMIT line: the escaped dot in `'^\.claude/worktrees/'` is not pinned by a test, because no scanned path can tell it apart. It would only matter if a new scan root were added whose name differs from `.claude` only in its first character.

## Review history

- **2026-10-22, round 1 (author run afbef35185650415b).** Result: FAIL on AC3. The tests did not pin the `^` anchor: mutant m4 (`grep -v '.claude/worktrees/'`) left all 26 tests green. AC1, AC2 and AC4 passed. Defect returned, Medium: add `doc/.claude/worktrees/x.md` and a content-line case.
- **2026-10-22, round 2 (REWORK, author run ac4c5000b7ebc15d9).** Both requested cases were added, and m4 and m6 were caught. Mutant m7 (`'^\.claude/worktrees'`, trailing slash dropped) left all 28 tests green, so the filter could widen silently to `.claude/worktreesX/x.md` and `.claude/worktrees.md`. Result: FAIL on AC3, defect Low: pin the trailing slash.
- **2026-10-22, round 3 (REWORK, author run abe0851416b28a4ac).** Both look-alike cases were added. m7 is now caught (2 failed). Result: PASS (see Verdict above).
