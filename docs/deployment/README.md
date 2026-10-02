# Deployment

Order matters. Backend first, then frontend, then tighten CORS.

1. Verify CI is green on `main` (see CI badge in README; a real GitHub
   Actions run must be confirmed in the GitHub UI).
2. Deploy the backend to Render (see `render.md`; `render.yaml` holds safe
   defaults, dashboard values below).
3. Copy the Render HTTPS backend URL, e.g. `https://hollow-green-api.onrender.com`.
4. Deploy the frontend to Vercel (see `vercel.md`) with
   `NEXT_PUBLIC_API_BASE_URL=https://<render-backend-domain>`.
5. Copy the exact Vercel origin, e.g. `https://hollow-green.vercel.app`.
6. Set Render `ALLOWED_ORIGINS` to the exact Vercel origin and redeploy the
   backend if the origin changed.
7. Run the validation checklist (`validation-checklist.md`).

## Rollback

- Vercel: open the project dashboard, pick a prior production deployment, and
  promote/redeploy it.
- Render: open the service dashboard, pick a previous Git commit, and deploy it.
- Never use a rollback as a substitute for reviewing logs. Read the logs
  first, then decide.
