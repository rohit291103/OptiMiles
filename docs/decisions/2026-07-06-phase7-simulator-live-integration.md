# Decision Log — Phase 7 (Integration): Live Goal Simulator

**Date:** 2026-07-06
**Area:** integration (frontend Goal Simulator → backend `POST /simulations` — build-plan Phase 7, first half)

## Context

Build-plan Phase 7 wires the landing-page Goal Simulator to the real backend, replacing the static mock (`goal-simulator.tsx` hardcoded destinations/miles). Phase 6 left the pipeline and the anonymous `POST /simulations` endpoint built and green; this session connects the browser to it. Phase 7's second half — Supabase auth → a real `user_id` → `persist=True` and the real-DB round-trip — is deferred to its own session (scope decision this session), because it is a much larger lift and the only part gated on the still-pending Supabase password rotation. The simulator needs neither auth nor an LLM key: it sends a *structured intent* (destination/cabin/timeline chosen from menus), so it skips Stage 1 entirely and runs on the deterministic core + template-fallback narration.

## Decisions

1. **The simulator posts a structured `intent`, not free text.** The menus already produce machine-checkable fields, so the request carries `intent` (skipping the LLM Stage 1) rather than `text`. Consequence: the public simulator is fully functional with **no LLM key** — the only degraded surface is narration eloquence (template fallback), never a number. Free-text goal entry stays a signed-in / later-session feature via `/goals/parse`.

2. **CORS is enabled on the API, config-driven, no wildcard, no credentials.** `POST /simulations` is a browser call from the Next site (a cross-origin request), so `CORSMiddleware` allows the configured origins (`cors_allow_origins`, comma-separated env, default `localhost:3000` + `127.0.0.1:3000`), methods `GET`/`POST`, header `Content-Type`. No `allow_credentials` — nothing cookie-bound crosses the boundary; the simulator is anonymous. Production origins are appended via the `CORS_ALLOW_ORIGINS` env var. The origin list is a `str` field split by a `cors_origins` property rather than a `tuple[str, ...]` field, because pydantic-settings JSON-decodes complex-typed env vars (a comma string would raise).

3. **The frontend talks to the backend through one typed client** (`src/lib/api.ts`), base URL from `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`, documented in `.env.example`). It mirrors only the response fields the simulator renders — the backend `FinalRecommendation` is richer — and models the response as the same discriminated union the API returns (`recommendation | clarification | unsupported_route | scope_refusal`), so every branch is handled explicitly, including infeasible-with-adjustments and uncharted-route.

4. **The single spend figure is spread across a representative category mix, not sent as one `default` bucket.** The engine earns *per category* — accelerated categories are the whole point — and uncategorized `default` spend earns the low base rate. Sending the simulator's one monthly-spend number as a lone `default` line made the flagship demo (Infinia, ₹1L, 8 months, Singapore business) read **infeasible** (38,400 < 45,000 miles) — technically honest but a poor first impression *and* an understatement of real categorized earning. Spreading it over a premium-traveler mix (`SPEND_MIX`, travel/dining/online/groceries/utilities, sums to 1 — mirroring the backend's own `DEFAULT_SPEND_PROFILE` philosophy) makes the same demo read **feasible, 7 months to goal, 84,480 best-case** — truthful and compelling. A signed-in user edits their real per-category profile.

5. **The wallet picker is populated from the live catalog, acquirable-only.** `fetchCards()` hits `GET /catalog/cards`; the picker shows acquirable cards (so the discontinued Atlas isn't offered as a new card) and pre-selects the flagship pair. If the catalog fetch fails the simulator degrades to no picker and still runs (empty wallet is a valid, likely-infeasible context).

## Verification

Booted the real app over HTTP (uvicorn) with the seed snapshot (no DB needed — the simulate path uses the process-cached snapshot, not persistence) and exercised the exact browser path:
- **CORS preflight** (`OPTIONS /simulations`, Origin `localhost:3000`) → 200 with `access-control-allow-origin: http://localhost:3000`, `allow-methods: GET, POST`.
- **Live `POST /simulations`** (flagship demo) → `kind: recommendation`, feasible, 45,000 required / 84,480 best-case / 7 months to goal, `narration.model_version: template-fallback`.
- Infeasible path (empty wallet, `no_new_cards`) → `feasible: false` with the adjustment menu rendered.

Backend: 218/218 tests, mypy strict + ruff clean (added a CORS endpoint test + a config-parsing test). Frontend: `tsc --noEmit` clean, eslint clean on both changed files.

## Review outcome

**backend-reviewer** — no critical/important findings. CORS is safe (no wildcard, `allow_credentials` left at its `False` default, methods/headers scoped to what `/simulations` needs); the `str`-field + `cors_origins`-property seam is sound. Acted on two cheap follow-ups: added a documented `CORS_ALLOW_ORIGINS=` line to `backend/.env.example`, and a negative test (`test_cors_rejects_unconfigured_origin`) proving a foreign origin gets no allow-origin header — i.e. the allow-list actually restricts, not just permits. Flagged for the *later* auth session (not now): if `allow_credentials` is ever flipped on, it must never ship alongside a wildcard origin.

**frontend-reviewer** — no critical/important defects; the request/response contract lines up with the backend field-for-field, city names match `CITY_TO_REGION` case-insensitively, numeric coercion floors invalid input, and the `useEffect` cleanup guard is correct. Applied all three concrete fixes: `text-red-400` → the `text-destructive` design token; `aria-pressed` on the cabin-class pills (they were the one single-choice control missing state semantics, inconsistent with the wallet pills below them); and `aria-live="polite"` on the results container for screen-reader announcement parity with the error `role="alert"`. Also hardened the `scope_refusal` branch: typed `message` as `string | null` to match the backend's `str | None` and render a fallback string rather than `undefined`. Noted (not bugs): the `clarification` branch is currently unreachable from this caller since the structured intent always supplies every field `resolve_goal` checks — a reasonable defensive branch kept for the free-text path later.

## Not done (deferred — Phase 7 second half)

- **Auth + live persistence** (`persist=True`, real-DB round-trip test) — waits on Supabase auth wiring and the DB password rotation. The persistence seam (`repositories/results.py`) remains built and unit-tested from Phase 6.
- **Free-text goal entry** via `/goals/parse` in the UI — needs a live LLM key to be worth surfacing; the structured simulator covers the marketing path.
- **Auth forms** (`/login`, `/signup`) still submit to a `setTimeout` stub — real auth route is the same deferred second half.
- **`verify`-style full browser pass** (desktop + mobile) of the live simulator interacting with a running backend — the end-to-end HTTP path is verified programmatically here; a human/Playwright visual pass of the rendered result states is the remaining confirmation.
