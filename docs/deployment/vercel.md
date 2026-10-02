# Vercel (frontend dashboard)

No `vercel.json` is used on purpose: prefer Vercel project settings with
framework auto-detection so there is exactly one place to change these values.

## Project settings

- Root Directory: `frontend`
- Framework Preset: `Next.js` (auto-detected)
- Install Command: `npm ci` (only if not automatically inferred)
- Build Command: `npm run build`
- Output: Next.js default (no override)
- Node version: `22.x` (matches CI)

## Environment variables

- `NEXT_PUBLIC_API_BASE_URL=https://<render-backend-domain>` — the exact
  Render backend HTTPS origin, no trailing slash.
- This is a **build-time** variable: Next.js embeds `NEXT_PUBLIC_*` values
  into the browser bundle. Changing it requires a new Vercel deployment.
  It must never contain a secret.
- Do NOT add: `E2E_TEST_MODE`, `PUBLIC_DATA_FIXTURE_ONLY`, `test_provider`,
  `GITHUB_TOKEN`, or any `AI_REVIEW_*` key to Vercel. The frontend needs none
  of them; provider and GitHub secrets stay backend-only.

## Rollback

Vercel dashboard → project → Deployments → pick a prior production
deployment → Promote to Production (or Redeploy). Read the build/runtime logs
first; never roll back blindly.
