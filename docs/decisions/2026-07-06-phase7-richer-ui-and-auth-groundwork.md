# Decision Log — Phase 7 (Integration): Richer Recommendation UI + Auth Groundwork

**Date:** 2026-07-06
**Area:** integration (frontend recommendation detail + Supabase auth groundwork — build-plan Phase 7, continued)

## Context

Follows the same-day simulator live-integration ([2026-07-06-phase7-simulator-live-integration.md](2026-07-06-phase7-simulator-live-integration.md)). Two threads: (1) surface the explainable *detail* the pipeline already returns but the simulator was only summarizing, and (2) build the Supabase-auth groundwork so signed-in goal persistence (`persist=True`) is ready the moment the user rotates the Supabase password and adds keys. The user asked for both; the auth live round-trip is intentionally left unverifiable this session (no keys yet), built to "ready + unit-tested."

## Decisions

1. **The richer recommendation UI renders only deterministic engine artifacts** (`components/strategy-detail.tsx`): the 6-part score breakdown as labeled bars (the "never a black box" promise made visible), the month-by-month accumulation curve, the spend-allocation routing (category → card, ids resolved to names via the catalog map the simulator already fetches), and the narration's action items. Nothing here is LLM-originated; the score sub-scores, ledger, and allocation are all Stage 8/9 outputs.

2. **A backend simulation-field was added rather than reverse-engineering the chart on the frontend** (`MonthLedgerEntry.points_earned_this_month`). The month-by-month chart needs a true per-month *earn* series. The obvious frontend shortcut — summing `points_by_card` — is **wrong**: `points_by_card` is the running end-of-month *balance*, which a transfer-out decrements, so it's non-monotonic and re-summing it double-counts. The correct, un-derivable-on-the-frontend quantity is the earn delta (base + category + milestone bonuses, before the transfer decrement), so it was added at the source in `projector.py` and TDD'd with a hand-computed golden (flat 7,659/month across the Infinia archetype, unchanged through the transfer month). The frontend charts a single cumulative sum of that clean field. This is the "have the backend expose a genuine field rather than reverse-engineer a non-monotonic one on the frontend" call the reviewer explicitly recommended.

3. **Auth is Supabase Auth + a JWT verified by FastAPI** (user's chosen approach). The frontend's Supabase session mints an HS256 access token; FastAPI verifies it against the project JWT secret (`api/auth.py`, `require_user`) and extracts the caller's real `auth.users` id — exactly the `persist_recommendation` precondition. This matches the existing schema (`users.id → auth.users(id)`) and D-4 (service-role backend, RLS as defense-in-depth): the seam *identifies* the caller, it does not authorize row access.

4. **Auth fails closed.** With no `supabase_jwt_secret` configured, every authenticated request is rejected (401), never passed through — a misconfigured deploy is locked, not open. `jwt.decode` is pinned to `algorithms=["HS256"]` (no `alg:none` / algorithm-confusion bypass), audience and expiry enforced. Unit-tested against a known secret with real sign/verify (15 cases: the valid path plus every rejection — bad signature, wrong audience, expiry, non-UUID/missing sub, no-secret, malformed header).

5. **The persisting endpoint is separate and authenticated** (`POST /goals/recommendation/save`, `Depends(require_user)`, `persist=True`). The anonymous `/goals/recommendation` and public `/simulations` stay `persist=False`. Same pipeline, same response — the only difference is a real `user_id` and a write. Best-effort persistence now **fails fast** (`connect_args={"timeout": 5}` on the engine) so an unreachable DB can't block the response for asyncpg's ~60s default.

6. **The frontend auth degrades gracefully when unconfigured.** `lib/supabase.ts` exports a `supabase` client that is `null` without keys; `AuthForm` shows "Authentication isn't configured yet" on submit rather than crashing. Real `signUp`/`signInWithPassword`/`signInWithOAuth` (Google/Apple), email-confirmation notice, error/notice display (`role="alert"`/`role="status"`), `router.push("/")` on success. The anon key is `NEXT_PUBLIC_` — correct: it is designed to be public; RLS + the server-side JWT secret enforce access.

## Verification

- **Chart-bug fix verified live**: after the field change, the cumulative series from `/simulations` is a clean monotonic climb (`[7,326 … 58,608]`, flat +7,326/month) — previously the buggy double-cumulative `[7,326 … 161,172]` with a false transfer-month plateau.
- **Backend**: 236 tests (was 219 — +15 auth, +1 projector golden, +save-endpoint cases), mypy strict + ruff clean. The projector golden pins the new field's exact values.
- **Auth save endpoint**: 401 without a token; 200 with a valid known-secret token (persistence best-effort, swallowed with no DB).
- **Frontend**: `tsc` + eslint clean; `/login` and the homepage compile and render.
- Live signed-in DB round-trip: **not verified — blocked on the user rotating the Supabase password + adding keys** (built to ready + unit-tested, per the session scope).

## Review outcome

**frontend-reviewer (richer UI)** — drove a real browser (desktop + mobile, both no-overflow, no console errors) and caught a **real correctness bug**: the month-by-month chart summed `points_by_card`, which is the running *balance* (decremented on transfer), and re-cumulated it — double-counting and inheriting the transfer's non-monotonic dip as a false plateau. Verified live: rendered `[7,326 … 161,172]` vs the correct `[7,326 … 58,608]`. Fixed at the source per decision 2 (the `points_earned_this_month` field), not patched on the frontend.

**backend-reviewer (auth)** — verified against the installed PyJWT that `algorithms=["HS256"]` blocks `alg:none`/algorithm-confusion, audience + expiry are enforced, the 5s connect timeout is the right asyncpg knob, and fail-closed is real. Found one **defense-in-depth gap**: `jwt.decode` didn't *require* `exp`, so a validly-signed token omitting `exp` would be treated as never-expiring (narrow — only whoever controls signing could mint one). Fixed with `options={"require": ["exp", "aud", "sub"]}` plus three new tests (exp-omitted rejected, `alg:none` rejected, wrong-algorithm HS512 rejected) and a ≥32-byte test secret. 239 backend tests, mypy strict + ruff clean.

**frontend-reviewer (auth)** — no critical/important findings; null-guard ordering, FormData usage, the finally-block, accessibility (`role="alert"`/`role="status"`), `useRouter` from `next/navigation`, and **no service-role secret client-side** all verified. Applied its one substantive polish: the signup "Full name" was collected but never sent — now passed as `options.data.full_name`. Left as documented follow-ups: OAuth-button double-click guard, `emailRedirectTo` (needs live Supabase config).

## Not done (deferred)

- **Live auth + persistence round-trip** — needs the Supabase password rotation + keys in env (user-gated). The whole path is built and unit-tested.
- **A "Save this goal" button** wiring the simulator's result to `simulateAndSave()` — the call exists in the API client; surfacing it in the UI (with a signed-in check / login prompt) is the natural next step.
- **Logged-in state in the nav** (show the user / a sign-out control) — the session exists; reflecting it in `SiteNav` is follow-up.
- **Fire-and-forget background persistence** — persistence is currently awaited (fail-fast bounded at 5s); moving it off the response path is a later optimization, adjacent to the D-5 two-part-response work.
- **Degenerate single-candidate score bars** (e.g. `efficiency: 0` when only one candidate exists, a min-max-over-candidates artifact from `ranking.py`) — a product/backend polish the reviewer flagged as out of this diff's scope.
