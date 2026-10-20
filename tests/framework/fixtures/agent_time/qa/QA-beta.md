# QA Report: Synthetic beta

Status: Done
Owner: qa
Upstream: doc/specs/SPEC-synthetic-beta.md
Date: 2026-10-19

## Verdict: FAIL

Synthetic fixture for the meter's rework report.

## Defects (if FAIL)

| Severity | Description | Where | Suggested owner | Rework cause |
|---|---|---|---|---|
| Med | AC4 output line missing | app/b.py:9 | ai-engineer | missed-ac |
| Med | two causes given, which the vocabulary forbids | app/b.py:20 | ai-engineer | missed-ac, test-gap |
