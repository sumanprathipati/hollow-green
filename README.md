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
GET /v1/demo-releases -> DemoReleaseMeta[] (development/demo only)
GET /v1/demo-releases/{release_id} -> ReleaseLog fixture (development/demo only)
```

Response contains `score.{reserve_level, recovery_load, deductions, buffers}`, `follow_ups[]`, `rollback_summary`, `tolerance`.

Demo fixtures are currently served read-only from `tests/fixtures` for local development. They should move to a dedicated `demo-data/` folder later.

## Local dashboard

Two terminals, repo root for backend, `frontend/` for the dashboard. Synthetic data only.

Terminal 1 — backend:

```sh
uv sync
uv run uvicorn api.main:app --app-dir src --reload --port 8000
```

Expected: `http://127.0.0.1:8000/v1/health` returns `{"status": "ok"}`. API docs at `http://127.0.0.1:8000/docs`.

Terminal 2 — frontend:

```sh
cd frontend
npm install
npm run dev -- --port 3000
```

Expected: primary dashboard at `http://localhost:3000`. `http://127.0.0.1:3000` is also allowed by backend CORS. Set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` to override the default backend address.

## Tests

Synthetic data only. Every scoring rule has a match and non-match test.

Backend:

```sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Frontend (`frontend/`):

```sh
npm run lint
npm run typecheck
npm run test
npm run build
```
