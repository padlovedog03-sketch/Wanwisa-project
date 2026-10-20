# QA Report: Synthetic alpha

Status: Done
Owner: qa
Upstream: doc/specs/SPEC-synthetic-alpha.md
Date: 2026-10-10

## Verdict: FAIL

Synthetic fixture for the meter's rework report.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| High | AC2 not implemented | app/a.py:1 | ai-engineer | missed-ac |
| Low | no negative case for the parser | tests/test_a.py | ai-engineer | `test-gap` |
