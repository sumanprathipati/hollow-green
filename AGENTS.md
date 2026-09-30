# Hollow Green

## Product
Hollow Green finds releases that passed but quietly spent their recovery
capacity. Green on the dashboard, hollow underneath.

## Core concepts
- Recovery load: hidden capacity a successful release consumed and did not restore.
- Buffers: retry budget, time remaining, rollback availability,
  health-check status, manual-intervention count.
- Reserve Level: percent of recovery capacity remaining after a release.
  It is the only numeric primary score (0-100).
- Recovery Load: derived label from Reserve Level: low (80-100),
  medium (50-79), high (25-49), critical (0-24).
  No second numeric score field.
- Release classes: clean success, recovered success, fragile success,
  rollback, failed.
- RecoveryFollowUp: each recovery action creates a follow-up with
  follow_up_id, kind, event_ids, severity, required_action,
  status (open | completed | verified).

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
- Each ReleaseLog must contain exactly one terminal event
  (deploy_succeeded, deploy_failed, or deploy_rolled_back).
  Zero or more than one terminal event must return 422.
- event_id values must be unique inside a ReleaseLog.
  Duplicates must return 422.
- No financial "debt" language in code, tests, README, or API.
  Use RecoveryFollowUp, follow_up_id, required_action, status.
- Never put API keys or secrets in code, tests, logs, or commits.
- Phase 1 pins: rel-fragile-003 asserts Reserve Level exactly 23
  and Recovery Load exactly critical (42 retry + 20 manual + 15 time.low).
- API validation tests must cover zero, one, and multiple terminal-event cases.
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