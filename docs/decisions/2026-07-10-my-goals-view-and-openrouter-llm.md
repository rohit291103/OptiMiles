# Decision Log — "My Goals" read view + OpenRouter LLM wiring

**Date:** 2026-07-10
**Area:** integration / API / frontend / AI Reasoning config (post-Phase-7 follow-up)

## Context

The 8-phase backend build plan is complete through Phase 7 (auth + persistence live end-to-end). Two gaps surfaced in use: (a) a signed-in user could *save* a goal but had **no post-login page** — OAuth dropped them back on the landing page, and nothing surfaced saved goals; (b) narration was still template-fallback because no LLM key was configured, and the user wanted to use a **free** model via OpenRouter.

## Decisions

1. **LLM routes through OpenRouter via a new `llm_base_url` setting, not a new provider.** OpenRouter is OpenAI-API-compatible, so rather than add an `"openrouter"` value to the `llm_provider` enum (and a third branch), `config.py` gained an optional `llm_base_url` field. `_pydanticai.py`'s existing `openai` branch passes `base_url` to `OpenAIProvider` only when it's non-empty (empty ⇒ real OpenAI, unchanged). This keeps the "provider behind one config setting" boundary (build rule 3) intact — OpenRouter is just openai + base_url + key + model — and the sole `pydantic_ai` import stays in the one sanctioned adapter. The module-boundary test still passes.

2. **Model choice: a general instruct model, not the content-safety classifier the user linked.** The user's original pick (`nvidia/nemotron-3.5-content-safety:free`) is a *guardrail* model — it returns safe/unsafe classifications, so it cannot do either of OptiMiles' two LLM jobs (Stage 1 intent extraction, Stage 10 narration). Chose `qwen/qwen3-next-80b-a3b-instruct:free` — a real 80B general instruct model with a 262K context, capable of structured JSON extraction and prose. `.env`/`.env.example` document the pattern.

3. **`GET /goals` is a read-only, user-scoped endpoint backed by a new reader repo.** `repositories/saved_goals.py` (`list_saved_goals`) mirrors the `results.py` writer's placement — only `knowledge/` and `repositories/` touch the DB. The query is parameterized (`WHERE g.user_id = :user_id`), and `user_id` is only ever the verified JWT `sub` from `require_user` — there is no path for a caller to supply an arbitrary id, so one user can never read another's goals (RLS is defense-in-depth behind this, D-4). Each goal is `LEFT JOIN LATERAL`-ed to its latest `recommendation_outputs` row (`ORDER BY created_at DESC, id DESC LIMIT 1` — the `id` tiebreak makes the pick deterministic even if two outputs ever share a timestamp), and a goal with no recommendation still lists (NULL fields) rather than being dropped.

4. **The `/goals` page is the post-login home; OAuth now lands there.** `app/goals/page.tsx` lists saved goals (destination · cabin · miles, the recommendation summary, saved date + snapshot version), with an empty state and a "start a new goal" affordance. The `/auth/callback` handler redirects to `/goals` instead of `/`, and the nav gains a "My goals" link for signed-in users. Read-only for now — opening a goal into the full `strategy-detail.tsx` is deferred (needs a `GET /goals/{id}` payload endpoint).

## Verification

- **Backend:** 245 tests green (was 240 — 4 new repo tests covering user-scoping/row-mapping/LEFT-JOIN-miss/empty + 1 endpoint-auth test), mypy strict + ruff clean. Live over HTTP: `GET /goals` → 401 without a token and with a bad token (fails closed); endpoint registered in OpenAPI; `/goals` page renders 200 with heading + loading state; frontend compiled with no errors.
- **LLM:** a live structured call reached OpenRouter, authenticated, and hit the Qwen model — proving the wiring — but returned repeated `429`s (the free tier is upstream-rate-limited: ~50 req/day + moment-to-moment provider throttling). Wiring correct; free tier unreliable.

## Review outcome

**backend-reviewer** — no critical or important findings. Confirmed user-scoping is correct by construction (parameterized bind + JWT-derived id), the LATERAL is the standard "latest per group" idiom, the reader is in the right module, and the `llm_base_url` change is correctly confined to `ai_reasoning/` and gated (default OpenAI behavior unchanged). Applied two optional-polish fixes it raised: (1) a code comment that wrongly described the `LEFT JOIN LATERAL` as "lateral-free" was corrected; (2) added `, ro.id DESC` as a secondary sort so the latest-recommendation pick is deterministic under a timestamp tie (determinism is a standing invariant).

## Not done / follow-ups

- **Open a saved goal → full StrategyDetail:** the list is read-only; a `GET /goals/{id}` returning the stored `simulation_results`/`recommendation_outputs` payload + a detail view is the next slice.
- **LLM reliability:** the free Qwen tier is rate-limited. Buying $10 of OpenRouter credits once raises the free-model daily cap from 50 → 1000 (credits stay unspent since `:free` models cost nothing), or point `LLM_MODEL` at a paid model.
- **Rotate the OpenRouter key** — it was pasted into chat this session and must be treated as exposed. (Also still: rotate the Supabase DB password; publish the Google consent screen before launch.)
- No automated real-DB round-trip test for the reader (same constraint as `results.py`: needs a real `auth.users`-backed user) — the unit tests cover query shape and mapping.
