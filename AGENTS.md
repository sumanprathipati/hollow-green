# Hollow Green

## Product
Hollow Green finds releases that passed but quietly spent their recovery
capacity. Green on the dashboard, hollow underneath.

## Core concepts
- Recovery debt: hidden capacity a successful release consumed and did not restore.
- Buffers: retry budget, time remaining, rollback availability,
  health-check status, manual-intervention count.
- Reserve Level: percent of recovery capacity remaining after a release.
- Release classes: clean success, recovered success, fragile success,
  rollback, failed.
- Debt items: each recovery action creates a debt with a required
  repayment action.

## Technical stack
- Python 3.12
- FastAPI
- Pydantic v2
- Pytest

## Rules
- Use synthetic data only. Never use real company, customer, or employer data.
- Scoring is deterministic and explainable. Every score must link back to
  specific events.
- Do not add an LLM in Phase 1.
- Do not add a UI, database, authentication, or cloud deployment in Phase 1.
- Every scoring rule needs one test where it matches and one where it does not.
- Never put API keys or secrets in code, tests, logs, or commits.
- Run format, lint, type check, and tests before saying a task is done.

## Workflow
1. Plan first. List files to change, tests to add, and risks.
2. Wait for my approval before implementing.
3. Make small, reviewable changes and commit often.
4. After implementing, report: changed files, test results, failures,
   and known limitations.

## Definition of done
- All tests pass.
- New behavior has tests.
- README is updated if user-facing behavior changed.
- Changes are explained in plain language.