# Decision Log — Phase 7: Live Auth + Persistence (Google OAuth → saved goals)

**Date:** 2026-07-06
**Area:** integration / auth / database (build-plan Phase 7, second half)

## Context

Phase 7's first half made the anonymous simulator live. This half closed the loop end-to-end: a user logs in with Google, and a saved goal persists to the live Supabase DB under their real identity — the thing the Phase-6 persistence seam was built and waiting for. It was done against the live database, so several latent Supabase/pooler realities surfaced and were fixed as first-class code (see the companion log `2026-07-06-db-pooler-fix-and-catalog-rls.md` for the pooler/RLS specifics).

## Decisions

1. **Supabase Auth + FastAPI JWT verification** (the user's chosen approach). The browser client (`@supabase/supabase-js`, explicit **PKCE** flow) holds the session and sends the access token; `api/auth.py`'s `require_user` verifies it (HS256, fails closed with no secret, `alg:none`/confusion blocked, `exp`/`aud`/`sub` required) and yields the real `auth.users` UUID. This matches the schema (`users.id → auth.users`) and D-4 (service-role backend, RLS as defense-in-depth). Google is the only OAuth provider enabled (Apple removed from the UI — it needs a paid Apple Developer account; not worth it for MVP).

2. **A dedicated `/auth/callback` route completes the OAuth return.** The original code redirected OAuth straight to `/`, leaving the `?code=` unexchanged and the user logged-out — the "came back to homepage" bug. The callback page exchanges the code (via `detectSessionInUrl`, with an explicit `exchangeCodeForSession` fallback) and surfaces any provider `?error=` instead of failing silently. `redirectTo` points at it; Supabase's redirect allowlist covers `http://localhost:3000/**`.

3. **The nav is session-aware** (`use-auth.ts` → `SiteNav`). `useAuth()` subscribes via `onAuthStateChange` so login/logout reflect live (email + Sign out vs Log in / Get started) without a reload. This was the actual reason a *successful* login "looked like nothing happened" — the DB had the user, but the UI had no way to show it.

4. **Only `POST /goals/recommendation/save` persists** (`Depends(require_user)`, `persist=True`). The anonymous `/recommendation` and public `/simulations` stay `persist=False`. The "Save this goal" button re-runs the pipeline server-side under the token rather than persisting the already-shown result — safe because the pipeline is deterministic (same inputs + snapshot ⇒ identical output, the standing invariant), so the saved row matches what's on screen.

5. **`auth.users` → `public.users` sync trigger** (migration `0004`). Every user-scoped table FKs `public.users`, but Supabase Auth only writes `auth.users` — nothing bridged them, so the first save FK-violated against an empty `public.users`. Fixed with the standard Supabase pattern: an `AFTER INSERT` trigger on `auth.users` (`SECURITY DEFINER`, `search_path=public`, `ON CONFLICT DO NOTHING`) mirroring the identity into `public.users`, plus a backfill for the existing user. Future signups auto-sync.

## Verification (against the live DB)

Proven end-to-end with the real authenticated user (`rohitg291103@gmail.com`, Google):
- Login: `auth.users` row created (provider=google); the `0004` trigger + backfill populated `public.users`.
- Nav reflects the session (email + Sign out).
- A save wrote the **full lineage chain** — `user_goals → spend_simulations → simulation_results → recommendation_outputs`, every row stamped `catalog_snapshot_version=cat-b63f738db960` (D-2). Row counts incremented as expected on repeat saves.
- 239 backend tests green, mypy strict + ruff clean; frontend tsc + eslint clean.

## Review outcome

**backend-reviewer** — caught one **ship-blocking bug my local test missed**: CORS `allow_headers` didn't include `Authorization`, so the browser preflight would reject the signed-in `simulateAndSave` cross-origin POST (my `urllib` test bypassed CORS, so it passed while the real Save button would fail). Fixed — added `Authorization` to `allow_headers`, verified over real HTTP (`access-control-allow-headers` now lists it), and added a regression test (`test_cors_preflight_allows_authorization_header`) that OPTIONS-preflights the save endpoint. Also applied the suggested defense-in-depth: `REVOKE EXECUTE ON FUNCTION public.handle_new_auth_user() FROM PUBLIC` (in `0004` for fresh deploys **and** on the live DB, since `0004` already ran; verified no PUBLIC grant remains). Confirmed sound (no change): NullPool+pre_ping is coherent (pre_ping is near-redundant but harmless under NullPool); `_persist`'s broad `except` can't leak into the response; the `0004` trigger is injection-free with correct `SECURITY DEFINER`+`search_path` pinning. **240 backend tests green** (was 239), mypy strict + ruff clean.

**frontend-reviewer** — drove a real browser (desktop + mobile, no overflow/console errors; all three `/auth/callback` branches terminate cleanly with no redirect loop). Found one **important correctness gap**: the Save button showed "Saved ✓" on any 200, but persistence is best-effort — a failed write returned 200 and the UI lied. Fixed on both sides: `/goals/recommendation/save` now returns `persisted: bool` (True iff the lineage chain actually wrote), and `handleSave` only claims "Saved" when `persisted === true`, else "Couldn't save" (verified live: real DB → `persisted: true`; no-DB test → `persisted: false`, asserted). Applied both polish items too: the Save/nav auth UI now waits on `useAuth().loading` so a returning user doesn't flash the logged-out prompt; and a token-null save shows a distinct "session expired — log in again" message instead of a misleading "try again". **240 backend tests green, mypy + ruff clean; frontend tsc + eslint clean.**

## Not done / follow-ups

- **Snapshot-load resilience:** the catalog snapshot loads once and caches; a transient cold-pooler refusal at first request leaves the process serving `null`/500 until restart. Add a retry so a single refusal doesn't poison the process. (Non-blocking; the DB is reliably up on retry.)
- **Real-DB round-trip *test*:** persistence is proven manually against the live DB, but there's no automated integration test (it needs a real `auth.users`-backed user). The unit tests (capturing fake connection) still cover the seam's shape.
- **OAuth polish:** Google consent screen is in "Testing" mode (only added test users can log in) — publish before launch (non-sensitive `email`+`profile` scopes ⇒ no Google review). Signup "Full name" now flows to `options.data.full_name`; `emailRedirectTo` not set (fine for OAuth).
- **Password rotation:** the DB password transited chat during debugging; rotate when convenient (user deferred).
