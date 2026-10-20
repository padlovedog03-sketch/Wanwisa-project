# QA Report: <Feature Name>

Status: Draft
Owner: qa
Upstream: doc/specs/SPEC-<feature-slug>.md
Date: YYYY-MM-DD

## Verdict: PASS | FAIL

<One sentence summary. FAIL if any criterion fails.>

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AC1 | <short name> | PASS/FAIL | tests/test_x.py::test_y — output summary |

## Test Run

```
<final pytest command + summary line, e.g. "12 passed in 0.34s">
```

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| High/Med/Low | <what breaks, how to reproduce> | src/<PACKAGE>/x.py:42 | ai-engineer | <one cause from the line below> |

Rework causes (exactly one per defect): `missed-ac` · `regression` · `spec-defect` · `test-gap` · `env-flaky`

<`missed-ac`: an acceptance criterion was not met. `regression`: something that
worked before is broken. `spec-defect`: the code does what the spec says and the
spec is wrong. `test-gap`: the behaviour is wrong and no test caught it.
`env-flaky`: the failure comes from the environment or a non-deterministic test,
not from the change. If two seem to fit, pick the one the fix will address. A
FAIL report dated on or after 2026-10-20 with a missing, doubled or unknown cause
fails `tests/framework/test_doc_contracts.py`.>

## Edge Cases Probed

- <case> → <result>

## Approval history

<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it, because an approval
     with no record of what wording it replaced is an approval nobody can audit
     later. Dates and amendment history belong here — never decorated onto the
     canonical `Status:` line, whose grammar is machine-checked. -->

- **YYYY-MM-DD — drafted.** <who, and what this first version was based on.>
