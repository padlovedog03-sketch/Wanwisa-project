# QA Report: verify-tiers increment H — less rework

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-verify-tiers-merge-gate.md
Date: 2026-10-20

## Verdict: FAIL

H-AC1 through H-AC5 pass on everything this branch can check, and owner addition (a) `--only` passes. Owner addition (b) fails: when a `not done` result is written in backticks or bold, the lint counts it as met. Backticks are how the agent docs themselves spell it. Separately, an earlier met line for the same AC hides a later `not done`.

Scope: branch `worktree-agent-ab70397b64a74a9e4` at 17d482a (commits 2058694, f654f7c, 17d482a), plus two uncommitted QA test files. The invocation states that the human approved the implementation and the owner accepted additions (a) and (b) on 2026-10-20 ("รับทั้งสอง"). QA did not see that approval first-hand.

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| H-AC1 | Spec template heading; In Review spec without it fails, named; Approved/Done never retro-failed; this spec carries the section | PASS | test_doc_contracts.py — template heading, planted spec named, approved/draft not judged, prose mention flagged (all pass); QA pin heading-too-deep flagged; `grep -n '^## Affected tests / affected files' doc/specs/SPEC-verify-tiers-merge-gate.md` returns line 309 |
| H-AC2 | `--spec` names `self-check missing for AC2`, exits 1; all three lines exit 0; line with no result flagged | PASS | tests/coordinator/test_handback_lint.py (32 tests, 22 of them red against the pre-H script 9a97bc6, green now); QA pins for both arrows, letter case, no-arrow line, empty result that does not borrow the next line |
| H-AC3 | ai-engineer.md and frontend-engineer.md require the self-check block and the right tier | PASS | test_engineers_must_self_check_on_the_right_tier for both agents (anchor plus verify-handoff --status, verify-full and handback_lint --spec in the same paragraph) |
| H-AC4 | Template Defects table has `Rework cause`; vocabulary equals agent_time.REWORK_CAUSES; FAIL report on or after cut-off with none, two or unknown cause fails, named with row; earlier reports not judged | PASS, except one clause NOT VERIFIED | Column, planted none/two/unknown rows, cut-off and PASS-report exemptions all pass; QA pins for the copied template placeholder and for a report dated exactly on the cut-off. NOT VERIFIED: the comparison with `agent_time.REWORK_CAUSES` is SKIPPED (scripts/agent_time.py ships with increment J). A literal pin stands in for it and compares sets only |
| H-AC5 | qa.md and frontend-qa.md require one cause per defect | PASS | test_qa_agents_require_one_cause_per_defect for both agents |
| Owner (a) | `--only <prefix>` filter | PASS | test_handback_lint.py only-tests; QA pins: `--only AC-` selects AC-AC ids only, `--only ZZ-` exits 2 with matches no AC, `--only` without `--spec` exits 2 |
| Owner (b) | `not done` always reported as an open AC, never as met | FAIL | Plain `not done` in any letter case and with either arrow is open (pinned). A backticked or bold `not done` exits 0 as met, and a duplicate line can hide it. See Defects 1 and 2 |

Counts: 6 PASS (one with an unverified clause), 1 FAIL, out of 7 criteria (H-AC1–H-AC5 plus owner additions a and b).

## Test Run

```
$ python3 -m pytest tests/coordinator/test_regression_handback_lint_self_check.py tests/framework/test_regression_doc_contracts_h.py -q
FAILED tests/coordinator/test_regression_handback_lint_self_check.py::test_regression_a_decorated_not_done_is_an_open_ac_never_met[backticks]
FAILED tests/coordinator/test_regression_handback_lint_self_check.py::test_regression_a_decorated_not_done_is_an_open_ac_never_met[bold]
FAILED tests/coordinator/test_regression_handback_lint_self_check.py::test_regression_a_decorated_not_done_is_an_open_ac_never_met[ascii-arrow-backticks]
FAILED tests/coordinator/test_regression_handback_lint_self_check.py::test_regression_an_earlier_met_line_does_not_hide_a_later_not_done
4 failed, 12 passed in 0.52s
```

The final `scripts/verify-full.sh` output is pasted in the hand-back message. It is red on the `coordinator` step because of the four defect reproductions above, and it still reads EXIT GATE INCOMPLETE because the lint, format and tests steps are not configured in this repo.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| High | A `not done` result in backticks or bold is counted as met. The handback exits 0 with self-check lines present for all ACs. The agent docs write the phrase in backticks, so an engineer who copies them gets a false green. Repro: test_regression_a_decorated_not_done_is_an_open_ac_never_met | scripts/handback_lint.py:104 | ai-engineer | missed-ac |
| Med | Duplicate lines for one AC: the first line wins. A met line followed by a `not done` line for the same AC exits 0, so the open AC is reported as met. Repro: test_regression_an_earlier_met_line_does_not_hide_a_later_not_done | scripts/handback_lint.py:99 | ai-engineer | missed-ac |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

Detail on defect 1. The check is `found[ac][1].lower().startswith("not done")`, so it misses any result that begins with markup. All of these were measured as exit 0 (met), each with both arrows: `` `not done` ``, `**not done**`, `_not done_`, `(not done)`, `✗ not done`, `not-done`, `not  done` (two spaces), `notdone`. The tests pin only backticks and bold, the two spellings the docs lead an agent to write. The fix should strip leading markdown markup before comparing. Whether hyphen and spacing variants also count is for the engineer to state. `TODO`, `pending`, `skipped` and `FAIL` also exit 0. That is the documented presence-only limit, not part of this defect.

Detail on defect 2. `found.setdefault(...)` keeps the first line for each AC. With `not done` first and a met line second, the lint reports it as open, which is correct. In the opposite order it reports met. One fix is to treat any `not done` line as open, or to flag duplicate lines.

## Edge Cases Probed

The engineer's deviation, the AC-id pattern `(?:[A-Z][A-Z0-9]*-)?AC\d+`, is **correct and misreads nothing in the current corpus**. Measured over every `doc/**/*.md`:
  - doc/specs/SPEC-verify-tiers-merge-gate.md gives the same 83 ids under the old pattern (2058694: `[A-Z]*-?AC\d+`), the new one and a loose first-column count.
  - SPEC-delegated-autonomy.md gives 64 under all three.
  - SPEC-verify-tiers-merge-gate-am1-size-class.md gives 0 old and 10 new (J2-AC1 to J2-AC10). Under the old pattern that spec had no readable ACs and would exit 2. The 11th loose cell is a prose cell, not an id.
  - Pinned by test_regression_a_digit_carrying_prefix_is_read_from_the_spec, which is red on a mutant that restores the old pattern.

Latent silent-drop forms. No current spec uses them, so they are not blocking. A first-column id in bold (`**H-AC3**`) or with three segments (`FE-H-AC2`) is not read at all. When other ids are present, that AC is dropped from the required list without a message.

Prefix boundaries in `--only`, measured:
  - `AC` selects AC1 and AC-AC2.
  - `AC-` selects AC-AC only.
  - `H-AC1` also selects H-AC10.
  - `J` selects J2-AC1.
  - An empty `--only ""` selects every AC.

  All of this is literal starts-with, as documented. These only ever make the check stricter and never falsely green. Observation only.

Not done variants: plain `not done` in lower, title or upper case, with `→` or `->`, is open (pinned). With no arrow (`H-AC1: not done`), the AC is reported missing rather than met (pinned).

Empty result borrowing the next line (the fe59b02 class): a result of only spaces and a tab, followed by an indented `1 passed`, is flagged as having no result (pinned).

Plain `-` mode without `--spec`: output and exit codes match the pre-H script 9a97bc6 on four inputs (clean, empty field, bold or list fields, nothing at all). A handback with no Self-check block stays clean (pinned). Two argument-level differences:
  - `--spec` given as the only argument now exits 2 as a usage error. The old script treated it as a filename and exited 1.
  - A missing `--spec` file raises a traceback with exit 1, the same code as "problems found". This is a Low usability gap. Neither is a defect against an AC.

Spec at In Review with the heading only mentioned in prose: flagged (existing test). An h3 heading is flagged (pinned). Two further forms, neither blocking:
  - A heading inside a fenced code block passes the check. This is contrived.
  - A bold `**Status:** In Review`, or a lowercase `In review`, is not judged. The repo's status grammar is itself inconsistent: approve.py accepts only a plain `Status: `, while verify_approvals.py also accepts `**Status**:`.

QA report with a bold verdict (`## Verdict: **FAIL**` or `**Verdict:** FAIL`), `Verdict: Fail`, or `- Verdict: FAIL`: not judged. A report with no `Date:`, a bold `**Date:**`, `Date: 21 Oct 2026` or the template's `Date: YYYY-MM-DD`: not judged. **Neither contradicts H-AC4 as written.** Its Given requires `Verdict: FAIL` and a `Date:` on or after the cut-off, and these reports fall outside that. Both are fail-open paths, though: a FAIL report escapes the rework-cause gate by bolding one word or deleting one line the template carries. They are recorded for the owner to decide (failing closed on an undated FAIL report would be a spec change). They are not on the engineer's defect list.

A pipe inside a Defects description cell (even `\|`) shifts the columns and fails the row with the owner name read as the cause. This fails closed (false red, never false green). The template could warn about it. This report keeps every cell free of pipes for that reason.

A report that copies the template's placeholder cause unedited is named (pinned). A report dated exactly on the cut-off is judged (pinned).

Teeth: every passing QA pin was shown red against a targeted mutant held in scratch, never by editing `scripts/`:
  - case-insensitivity removed;
  - ASCII arrow dropped;
  - arrow made optional;
  - empty-result check removed;
  - `--only` usage errors removed;
  - plain mode forced to self-check;
  - old AC-id pattern restored;
  - placeholder accepted as a cause;
  - cut-off comparison changed to `<=`;
  - heading check loosened to any level.

The four defect reproductions are red on the current code.

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **2026-10-20 — drafted.** qa, from SPEC-verify-tiers-merge-gate.md H-AC1–H-AC5 and the owner-accepted additions (a) and (b), against branch commit 17d482a.
