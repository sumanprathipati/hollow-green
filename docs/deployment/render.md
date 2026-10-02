# Render (backend API)

Use the `render.yaml` Blueprint in the repo root, then set dashboard values.
Do not put secrets in `render.yaml`.

## Dashboard values

- Repository/branch: this repository, `main` (or the reviewed commit).
- Root directory: `.` (repository root; the start command uses `--app-dir src`).
- Build command: `pip install uv && uv sync --locked`
- Start command: `uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port $PORT`
  (Render requires binding `0.0.0.0` and its `$PORT` variable.)
- Health check path: `/v1/health` (returns 200 with safe status fields only).
- Python version: `3.12.0` (already a safe default in `render.yaml`).

## Environment variables

Required (dashboard, after the Vercel domain is known):

- `ALLOWED_ORIGINS=https://<your-vercel-domain>` — the exact frontend origin,
  no trailing slash, no wildcard. Redeploy the backend after changing it.

Optional (dashboard only, never in code or `render.yaml`):

- `GITHUB_TOKEN` — fine-grained, read-only token limited to public metadata
  access where possible. Raises GitHub API rate limits. Leave unset for a
  fully unauthenticated demo (lower limits, fixture/cache fallback still work).
- `AI_REVIEW_PROVIDER=openai_compatible`, `AI_REVIEW_BASE_URL`,
  `AI_REVIEW_MODEL`, `AI_REVIEW_API_KEY` — only to enable the optional
  citation-backed AI review. Leave all four unset for the safe
  AI-unavailable state.
- Never set: `E2E_TEST_MODE`, `PUBLIC_DATA_FIXTURE_ONLY` (test-only; the app
  defaults both to off, and the test-provider hook is inert without them).

## Logs and rollback

- Logs: Render dashboard → service → Logs. Startup logs one safe summary
  line (`environment=..., GitHub token configured=..., ...`); values, headers,
  prompts, and model output are never logged.
- Rollback: dashboard → service → Deploys → pick a previous commit → Deploy.
  Read the logs first; never roll back blindly.
