# Hollow Green

Finds releases that passed but quietly spent their recovery capacity. Green on the dashboard, hollow underneath.

Phase 1 is a deterministic, explainable analysis engine for synthetic deployment-event logs. No LLM, UI, database, authentication, or cloud deployment.

Stage 6 adds an optional public-data path: verifiable public GitHub evidence assessed with its own honest vocabulary (no deployment approval). Demo fixtures stay available under Demo mode with the unchanged deterministic engine.

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
GET /v1/public-repos -> allowlisted public GitHub repositories
GET /v1/public-repos/{owner}/{repo}/assessment -> PublicDataAssessment (?candidate=, ?refresh=, ?fixture=)
```

Response contains `score.{reserve_level, recovery_load, deductions, buffers}`, `follow_ups[]`, `rollback_summary`, `tolerance`.

Demo fixtures are currently served read-only from `tests/fixtures` for local development. They should move to a dedicated `demo-data/` folder later.

## Local dashboard

Two terminals, repo root for backend, `frontend/` for the dashboard.

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

The dashboard has two modes: Demo scenarios (synthetic fixtures) and Public GitHub evidence (verifiable public repository data).

## Public GitHub evidence

Public repository evidence only — deployment readiness cannot be determined.

Public mode uses its own honest vocabulary and never reuses Demo deployment
outcomes (`PROCEED`, `PROCEED WITH CAUTION`, `HOLD / INVESTIGATE`,
`ROLLBACK VERIFIED`, or `clean_success` / `recovered_success` /
`fragile_success` / `failed`). Each assessment returns:

- `change_risk_level`: `low` / `moderate` / `elevated` / `unknown` — computed
  only from observable public data (change/release recency, recent commit
  count, PR state, open-issue count, source-record availability).
- `evidence_completeness`: `sufficient` / `limited` / `insufficient` — missing
  operational signals reduce completeness; they are never treated as negative
  release-health events.
- `deployment_readiness`: always `not_assessable_from_public_data`.
- `public_recommendation`: `LOWER CHANGE RISK — REVIEW REQUIRED` /
  `MODERATE CHANGE RISK — REVIEW EVIDENCE` / `ELEVATED CHANGE RISK — INVESTIGATE` /
  `INSUFFICIENT EVIDENCE — DO NOT INFER READINESS`.

No scoring-engine window, retry-budget, Reserve Level, or classification is
used for public assessments. The dashboard hero states the limitation
prominently, shows an evidence-completeness card with unavailable signals, and
keeps raw external JSON in the labeled audit view only.

Setup:

```sh
cp .env.example .env
# Optional: add a GitHub token to raise rate limits (backend-only, never committed).
# GITHUB_TOKEN=
# PUBLIC_REPOS=octocat/Hello-World
uv run uvicorn api.main:app --app-dir src --reload --port 8000
```

Supported repositories: small allowlist in `PUBLIC_REPOS` (comma-separated `owner/name`). Default: `octocat/Hello-World` (tiny, stable, public). Requests for anything outside the allowlist return 404.

Rate limits: unauthenticated GitHub REST calls are heavily limited (typically 60/hour per IP). Setting server-side `GITHUB_TOKEN` raises limits. On 429 the API returns a rate-limit error; the dashboard shows a rate-limit state with retry. Successful assessments are cached in memory for 5 minutes; errors fall back to cached or saved-fixture data when available, labeled via `served_from` (`live`, `cache`, or `fixture`).

Data provenance: every assessment includes `data_source: "public-github"`, `retrieved_at`, `source_urls` (GitHub API + web URLs), `served_from`, `limitations`, and `unavailable_signals`. The frontend shows repository, candidate, retrieved timestamp, source links, and the public-data disclaimer, and keeps raw external JSON in the labeled Audit view only.

Privacy/security boundaries: public data only. No employer, customer, private, credentialed, or scraped data. `GITHUB_TOKEN` is backend-only (see `.env.example` placeholders); it is never sent to the frontend and never appears in API responses. No LLM scoring and no duplicate scoring logic in the frontend; Demo scores come from the existing Python engine, and public assessments are computed only from observable public data.

Architecture:

```text
GitHub REST (public only) ---> api/github_client.py (timeouts, token server-side,
                               rate-limit handling, source URLs, TTL cache + saved fixture)
                               |
                               v
                 hollow_green/public_data.py (typed evidence schemas +
                   compute_public_result from observable signals only;
                   internal ReleaseLog mapper retained isolated + unused by route)
                               |
                               v
                 api/public_data.py (assessment: public_result + evidence + limitations)
                               |
                               v
                 Next.js command center (Demo scenarios | Public GitHub evidence)
```

Demo path (unchanged): fixtures -> POST /v1/releases:analyze -> hollow_green/analyze.py.

## Evidence-grounded change review (optional AI assistance)

Public GitHub evidence mode can show an "AI-assisted evidence review" card that
explains the deterministic assessment in plain language. It is explanatory
assistance only: the deterministic `public_result` is the source of truth, and
no score, threshold, risk level, or recommendation is decided or altered by the
model. Demo mode never renders this card.

```text
Browser
  -> Next.js command center
  -> FastAPI public evidence assessment
  -> normalized/capped EvidenceBundle
  -> backend-only AI provider adapter
  -> strict Pydantic/citation/safety validator
  -> structured cited explanation returned to UI
```

Rules enforced in code and tests:

- The model receives only the normalized, capped evidence bundle for the
  selected repository (repository/candidate metadata, at most 5 commits, 5 pull
  requests, 5 issues, unavailable-signal and limitation records). No tokens,
  headers, raw API payloads, README text, source code, cookies, file paths, or
  free-text input are ever sent.
- Every factual bullet carries `[En]` citations that must exist in the bundle;
  sources render as clickable links built from bundle URLs only. The model may
  not emit URLs, Markdown links, or HTML.
- Output is capped (4 sections, 4 bullets each, 350 words) and scanned for
  forbidden deployment/demo vocabulary and unsupported facts, dates, counts, or
  references. Failures return `blocked` without the rejected text.
- Provider keys live only in server environment (`AI_REVIEW_PROVIDER`,
  `AI_REVIEW_BASE_URL`, `AI_REVIEW_MODEL`, `AI_REVIEW_API_KEY`, documented in
  `.env.example`); never `NEXT_PUBLIC_`, never in responses, logs, or the
  browser. Timeouts are 10s connect / 20s read, no streaming, bounded sizes.
- Without configuration the endpoint returns HTTP 200 `unavailable` with setup
  guidance; the deterministic view keeps working. Provider outages map to safe
  502/429 responses without leaking details.

Endpoint: `POST /v1/public-data/assessments/{owner}/{repo}/{candidate}/evidence-review`
with body `{"regenerate": false}` (extra fields rejected) and the existing
`refresh` / `fixture` query semantics, including `stale_cache` fallback.

Real signals (observed from public GitHub): repository metadata (name, URL, default branch, stars, open-issue count), release/tag candidates (name, date, URL), recent commits (sha, date, message, URL), recent pull requests (number, title, state, URL), open-issue sample (number, title, URL), retrieval timestamp and source URLs.

Unavailable signals (always listed, never inferred): health, rollback, CI, retry consumption, manual interventions, production telemetry. Missing signals lower evidence completeness; the public result never contains a deployment approval.

## Tests

Synthetic data only, plus sanitized recorded GitHub fixtures and mocked HTTP (tests never call GitHub). Every scoring rule has a match and non-match test.

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
