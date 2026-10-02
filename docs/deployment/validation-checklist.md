# Manual post-deployment verification checklist

Perform these against the real deployed URLs. Do not hammer the service:
a handful of refresh/review calls is enough to observe a controlled 429.

## Backend (`https://<render-url>`)

- [ ] `GET /v1/health` returns 200 with only `status`, `environment`,
  `public_data`, `ai_review` (no versions, paths, traces, or secrets).
- [ ] `GET /docs` loads the FastAPI docs (note: this is `/docs`, there is no
  root `/health`; health lives at `/v1/health`).
- [ ] From a disallowed Origin, API responses carry no
  `access-control-allow-origin` echo; from the exact Vercel origin they do.
- [ ] Public assessment loads (fixture/cache behavior as appropriate).
- [ ] A few rapid refresh/review calls produce a safe HTTP 429 with a
  `Retry-After` header and no internal details.
- [ ] With no AI provider configured, the review endpoint returns the
  `unavailable` state (HTTP 200 + setup guidance), not an error.

## Frontend (exact Vercel HTTPS URL)

- [ ] Demo mode analyzes all five fixtures with the expected recommendations.
- [ ] Public GitHub mode shows the hero sentence
  "Public repository evidence only — deployment readiness cannot be
  determined." with unchanged Stage 6.1 vocabulary.
- [ ] AI review with no key shows the safe unavailable state.
- [ ] DevTools Network shows no secret value, E2E flag, fake-provider
  selection, raw prompt, or rejected model output in any response.
- [ ] Lighthouse/axe quick check passes; mobile layout has no horizontal scroll.

## Security

- [ ] No `.env` file, test-only env var, GitHub token, or AI key is committed
  or present in the Vercel client environment.
- [ ] Production backend has `E2E_TEST_MODE` and `PUBLIC_DATA_FIXTURE_ONLY`
  unset (defaults off).
- [ ] CORS allows only local dev origins plus the exact deployed origin.
- [ ] Health/docs expose no implementation internals.
