# Review: <Feature Name>

Status: Draft
Owner: reviewer
Upstream: doc/specs/SPEC-<feature-slug>.md
Author-run: <id>
Reviewer-run: <id>
Date: YYYY-MM-DD

<!-- Save as doc/qa/REVIEW-<feature-slug>.md (NO_SPEC_BUGFIX work: doc/qa/REVIEW-bugfix-<id>.md).
     The QA spawn gate reads three lines: `Verdict:` must be exactly PASS, and
     `Reviewer-run:` must be filled and differ from `Author-run:` (compared without
     case, spaces or invisible characters). Any FAIL verdict line keeps QA blocked. -->

## Verdict: PASS | FAIL

<One sentence. FAIL if any criterion in scope fails review.>

## Read from

- Upstream: <spec path, or the bugfix reproduction>
- Change: <commit or diff range>
- Not read: the author's conversation. Claims in the handback were re-run, not relayed.

## Criteria Review

| # | Criterion | Verdict | Evidence (command run in this review) |
|---|---|---|---|
| AC1 | <short name> | PASS/FAIL | <command> → <result> |

## Defects (if FAIL)

| Severity | Description | Where | Back to |
|---|---|---|---|
| High/Med/Low | <what breaks, how to reproduce> | <path:line> | <author agent> |

## Hostile inputs tried

- <input> → <result>

## Approval history

- **YYYY-MM-DD — drafted.** <who, and what this review was based on.>
