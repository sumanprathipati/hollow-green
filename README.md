# Hollow Green

Finds releases that passed but quietly spent their recovery capacity. Green on the dashboard, hollow underneath.

Phase 1 is a deterministic, explainable analysis engine for synthetic deployment-event logs. No LLM, UI, database, authentication, or cloud deployment.

## Concepts

- **Recovery load**: capacity a successful release consumed and did not restore.
- **Buffers**: retry budget, time remaining, rollback availability, health-check status, manual-intervention count.
- **Reserve Level**: 0–100, the only numeric primary score. Starts at 100, subtracts fixed points per rule.
- **Recovery Load label**: derived from Reserve Level — `low` (80–100), `medium` (50–79), `high` (25–49), `critical` (0–24).
- **Release classes**: `clean_success`, `recovered_success`, `fragile_success`, `rollback`, `failed`.
- **RecoveryFollowUp**: each recovery action yields an item with `follow_up_id`, `kind`, `event_ids`, `severity`, `required_action`, `status` (`open` in Phase 1).

## Scoring

Every deduction lists `rule_id` + `event_ids`. Examples: first successful automated retry 6, repeats 12 (cap 60), budget exhausted +15, manual override 20, bypass 25, time-low 15 / critical +10, rollback missing 25 / stale 10, health degraded 20 / failed 40. Clean verified automatic rollback costs 0 points. Window extensions never raise Reserve above the original-window result.

See `docs/phase1-plan.md` for the exact formulas.

## API

```text
GET /v1/health -> {status: "ok"}
GET /v1/version -> {schema_version: "1.0", app: "hollow-green"}
POST /v1/releases:analyze -> ReleaseReport
```

Response contains `score.{reserve_level, recovery_load, deductions, buffers}`, `follow_ups[]`, `rollback_summary`, `tolerance`.

## Tests

Synthetic data only. Every scoring rule has a match and non-match test.

```sh
python -m pytest
ruff check .
ruff format --check .
mypy src
```
