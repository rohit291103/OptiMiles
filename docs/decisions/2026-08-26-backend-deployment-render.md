# Decision Log — Backend Deployment (Render, free tier)

**Date:** 2026-08-26
**Area:** infrastructure / deployment

## Context

Only the frontend was deployed (Vercel). The backend had **no deployment
configuration in the repo at all** — no Dockerfile, no `render.yaml`, no
`fly.toml`, nothing — so the live site had no API to call. With Phase 1 features
now landing (Best Card shipped this session), the backend needs a home.

## Decisions

1. **The backend runs as a long-running instance, not serverless.** `app/api/deps.py`
   caches the catalog snapshot in module-level process memory and the pipeline runs
   to a 30-second budget (Scope v2). A serverless function rebuilds that cache on
   every cold start. **This rules out Vercel Functions** despite the frontend
   already living there — co-location is not worth losing the process cache.

2. **Render, free web service, Singapore region.** Native Python runtime reads
   `uv.lock` directly, deploys from GitHub on push, and Singapore is Render's
   closest region to Indian users. Blueprint committed at repo-root `render.yaml`
   so the config is reviewable rather than dashboard-only state.

3. **Free tier chosen knowingly, over the paid recommendation.** The constraint is
   real: **free services spin down after ~15 minutes idle and a Python cold start
   runs 50s+, exceeding the 30s pipeline budget** — the first visitor after a quiet
   period would time out.
   - **Mitigation:** `.github/workflows/render-keepalive.yml` pings `/health` every
     10 minutes, keeping the instance *and* its cached snapshot warm. Free tier
     grants 750 instance-hours/month against a ~730-hour month, so one always-warm
     service fits — **but only one**.
   - **Honest limit, recorded:** GitHub scheduled workflows are best-effort and get
     delayed or dropped under load. This *reduces* cold starts, it does not
     eliminate them. **If cold starts bite real users, the fix is the paid tier,
     not a tighter cron.**

4. **No Docker.** Render's native Python runtime is sufficient; a Dockerfile would
   be more control and more maintenance for no current gain. Revisit only if the
   runtime stops being enough (or if Fly.io becomes the target).

5. **`/health` stays DB-independent** — it already returns `status: ok` with a null
   snapshot version when the database is unreachable. This is what makes Render's
   health check pass during first setup before `DATABASE_URL` is correct, and it is
   what makes the keepalive ping safe.

6. **Secrets stay out of the repo.** `render.yaml` marks `DATABASE_URL`,
   `CORS_ALLOW_ORIGINS`, `SUPABASE_URL`, and `LLM_API_KEY` as `sync: false`; they
   are set in the Render dashboard. `CORS_ALLOW_ORIGINS` is never `*` — the API is
   CORS-scoped on purpose.

7. **No staging environment, no CDN, no queues.** One environment until there is a
   reason for two; `/catalog/cards` and `/best-card` already ETag on the snapshot
   version; the pipeline is sync single-request by Backend Build Rule 7.

## Consequences

- New: repo-root `render.yaml`, `.github/workflows/render-keepalive.yml`,
  `backend/.python-version` (3.13), and the runbook
  [`docs/architecture/deployment-v1.md`](../architecture/deployment-v1.md).
- **Verified locally:** the app imports, `uvicorn app.main:app` boots, `/health`
  returns 200, and `/v1/best-card` is registered in the OpenAPI paths. The Render
  deploy itself is **not** done — it needs the user's Render account.
- **A likely live bug surfaced while investigating:** `frontend/.env.local` has
  `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. That file never reaches Vercel,
  but if the Vercel environment variable was never set, **the deployed frontend has
  been calling `localhost` all along** — meaning the live Goal Simulator silently
  fails for every visitor. Must be checked as part of this deploy.
- `NEXT_PUBLIC_*` values are inlined at build time, so setting the Vercel variable
  requires a **redeploy** to take effect.
- Ordering dependency to respect: backend CORS needs the frontend origin, and the
  frontend needs the backend URL. Deploy backend with the known Vercel production
  URL first, then set the frontend variable and redeploy.
- Pre-existing blockers, unchanged by this decision: the Google OAuth consent screen
  is still in "Testing" (only added test users can sign in), OpenRouter's free tier
  429s into template narration, and `db-keepalive.yml` still needs its
  `DATABASE_URL` repo secret.
