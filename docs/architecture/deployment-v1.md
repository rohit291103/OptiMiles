# OptiMiles Deployment v1

**Document Path:** `/docs/architecture/deployment-v1.md`
**Version:** v1.0
**Status:** Runbook — current as of 2026-08-26
**Decision:** [`2026-08-26-backend-deployment-render.md`](../decisions/2026-08-26-backend-deployment-render.md)

---

# Topology

| Piece | Where | Notes |
|---|---|---|
| **Frontend** (Next.js) | Vercel | Already deployed |
| **Backend** (FastAPI) | **Render** — free web service, Singapore region | New; blueprint at repo-root `render.yaml` |
| **Database + Auth** | Supabase (free) | Transaction-mode pooler, port 6543 |
| **LLM** | OpenRouter | Optional — empty key degrades gracefully |

## Why the backend is a long-running instance, not serverless

`app/api/deps.py` caches the catalog snapshot in module-level process memory, and the pipeline runs to a 30-second budget (Scope v2). A serverless function rebuilds that cache on every cold start, so a process that stays up is a requirement, not a preference. This is why Vercel Functions — despite the frontend already living there — are the wrong home for this API.

---

# Free-tier reality check

The free Render plan was chosen deliberately. Its constraint is real and worth stating plainly:

> **Free web services spin down after ~15 minutes with no traffic, and a Python cold start runs 50s+ — longer than the 30-second pipeline budget.** The first visitor after a quiet period would time out.

Mitigation: `.github/workflows/render-keepalive.yml` pings `/health` every 10 minutes, keeping both the instance and its cached snapshot warm. Free tier grants **750 instance-hours/month** against a ~730-hour month, so exactly one always-warm service fits — **but only one**.

**Honest limit:** GitHub's scheduled workflows are best-effort and get delayed or dropped under load. The keepalive *reduces* cold starts; it does not eliminate them. If cold starts still bite users, the fix is the paid tier, not a tighter cron.

`/health` is deliberately DB-independent — it returns `status: ok` with a null snapshot version when the database is unreachable. So Render's health check passes even before `DATABASE_URL` is correct, which is what you want during first setup.

---

# First deploy

## 1. Commit the deploy config

`render.yaml`, `.github/workflows/render-keepalive.yml`, and `backend/.python-version` must be on `main` before Render can read the blueprint.

## 2. Create the Render service

Render dashboard → **New → Blueprint** → point at `github.com/rohit291103/OptiMiles`. The blueprint sets runtime, region, build/start commands, health check, and plan. Render will prompt for the four secrets marked `sync: false`.

Build and start commands, for reference:

```
build:  pip install uv && uv sync --frozen --no-dev
start:  uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 3. Set backend environment variables

In Render → Environment:

| Variable | Value | Consequence if wrong |
|---|---|---|
| `DATABASE_URL` | Supabase **transaction pooler** URL — user `postgres.<ref>`, port **6543** | The direct host is IPv6-only and unreachable. Wrong ⇒ every catalog read fails |
| `CORS_ALLOW_ORIGINS` | The Vercel origin(s), comma-separated | **Wrong ⇒ every browser call fails preflight.** Never `*` |
| `SUPABASE_URL` | `https://<ref>.supabase.co` | Enables JWKS token verification. Unset ⇒ auth fails closed, `/goals` rejects everything |
| `LLM_API_KEY` | OpenRouter key | Optional. Empty ⇒ LLM disabled; pipeline stays **correct**, losing only free-text intent and narration eloquence |

## 4. Point the frontend at the backend

Vercel → Project → Settings → Environment Variables:

```
NEXT_PUBLIC_API_BASE_URL = https://optimiles-api.onrender.com
```

**Then redeploy** — `NEXT_PUBLIC_*` values are inlined at build time, so changing the variable alone does nothing until a new build runs.

> **Check this first.** `frontend/.env.local` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. That file is local-only and never reaches Vercel, but if the Vercel variable was never set, the deployed frontend is currently calling `localhost` — which would mean the live simulator has been silently broken for every visitor.

## 5. Resolve the ordering dependency

The frontend needs the backend URL, and the backend's CORS needs the frontend URL. Do it in this order:

1. Deploy the backend with `CORS_ALLOW_ORIGINS` set to the **known** Vercel production URL
2. Set `NEXT_PUBLIC_API_BASE_URL` on Vercel, redeploy
3. If you use Vercel preview deployments, each gets its own generated hostname — add them to `CORS_ALLOW_ORIGINS` or previews will fail preflight while production works

## 6. Set the keepalive variable

GitHub → Settings → Secrets and variables → Actions → **Variables** → `API_BASE_URL` = the Render URL. It is a *variable*, not a secret — the workflow skips cleanly if unset.

While there, confirm the `DATABASE_URL` **secret** exists for `db-keepalive.yml`, which stops the free Supabase project pausing after ~7 days idle.

---

# Verification checklist

Run these against the deployed backend, in order:

```bash
API=https://optimiles-api.onrender.com

# 1. Liveness. catalog_snapshot_version must be non-null — null means the DB
#    is unreachable and only the DB-independent parts of the app work.
curl -s $API/health

# 2. Catalog read (proves DATABASE_URL + pooler settings are right)
curl -s $API/v1/catalog/cards | head -c 400

# 3. Best Card end-to-end (no auth, no LLM — the cleanest full-stack probe)
curl -s "$API/v1/best-card?amount_inr=10000&category=default&card_ids=<uuid>"

# 4. CORS preflight from the real frontend origin
curl -s -i -X OPTIONS "$API/v1/catalog/cards" \
  -H "Origin: https://<your-vercel-domain>" \
  -H "Access-Control-Request-Method: GET" | grep -i access-control
```

Then in a browser: load the deployed site, open devtools, and confirm the Goal Simulator and `/best-card` complete without CORS or network errors.

---

# Known blockers, unrelated to hosting

- **Google OAuth consent screen is still in "Testing"** — only explicitly added test users can sign in. Publishing is required before real users can log in. Scopes are non-sensitive, so no Google review is needed.
- **OpenRouter free tier rate-limits (429s)** — narration falls back to templates. Correctness is unaffected; only prose quality is. A small paid balance resolves it.
- **Supabase free tier pauses after ~7 days idle** — `db-keepalive.yml` handles this once its `DATABASE_URL` secret is set.

---

# What is deliberately not here

- **No Docker.** Render's native Python runtime reads `uv.lock` directly. A Dockerfile would be more control and more maintenance for no current gain.
- **No staging environment.** One environment until there is a reason for two.
- **No CDN or caching layer in front of the API.** `/catalog/cards` and `/best-card` already return ETags keyed on the catalog snapshot version; that is enough at this scale.
- **No queues, workers, or background jobs** — the pipeline is a sync single-request design (Backend Build Rule 7).
