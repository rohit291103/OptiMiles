# Decision Log — Phase 6 Pipeline Orchestrator + API v1

**Date:** 2026-07-05
**Area:** backend (pipeline orchestration + API — build-plan Phase 6)

## Context

Build-plan Phase 6 composes the five already-built, fixture-tested engines (Phases 0–5) into one end-to-end pipeline and exposes the deliberately-small API v1 (build-plan §7). This is the phase the whole build has been converging on: it turns the manually-chained `tests/integration/test_optimization_pipeline.py` (Stages 5→9 wired by hand) into a single `pipeline/run.py` function that also handles Stages 1, 4, 10, 11, and it establishes the **standing byte-for-byte determinism test** (build rule 8) that must stay green from here on. `model_from_settings()` is finally called for real; with no key in `.env` the whole pipeline runs on the non-LLM paths (structured-form intent, template narration) — correct, just less eloquent.

## Decisions

1. **The orchestrator is a plain linear function, two entry points, no framework** (`pipeline/run.py`). `run_goal_pipeline` is Flow A (raw text or a pre-resolved intent → full recommendation); `run_from_context` is the Flow-B re-entry point (a ready `PlanningContext` → Stages 5–11), shared by the public simulator. This is the mechanical form of blueprint §0.2 "pipeline orchestration is deterministic code": the same stage order every request, no LLM and no LangGraph deciding what runs next (D-3, D-7 hold).

2. **Every gap is an explicit early-exit, never a guess.** The pipeline outcome is a discriminated union — `FinalRecommendation | ClarificationNeeded | RouteUnsupported | ScopeRefused`. Stage 1 incomplete/ambiguous → clarification; Stage 1 out-of-scope → scope refusal; Stage 2 uncharted route → `RouteUnsupported` (never an estimate); Stage 6 infeasible → a `FinalRecommendation` whose `recommended is None` and whose narration is the computed adjustment menu. The client holds the clarification-loop state (blueprint §8.4): pass an accumulated `intent` to skip Stage 1, so the server stays stateless.

3. **Stage 4 defaults are config-driven and flagged, never silent** (`pipeline/context.py`). A caller who supplies no spend profile gets `DEFAULT_SPEND_PROFILE` with `assumed=True`, surfaced in `FinalRecommendation.assumed_flags` as `"spend_profile"` so the UI can prompt "edit to refine" (blueprint Stage 4). An empty wallet is a *valid* context — Stage 6 declares infeasibility with the obvious fix, it is never an error. `horizon_months` rounds a partial final month UP and floors at 1 (a same-month or past target still gets one simulated tick); golden-value tested at the boundaries.

4. **Persistence is a repo seam OFF the deterministic path** (`repositories/results.py`), by design (per the user's Phase-6 scope decision: "in-memory pipeline first, DB writes behind a repo seam"). `pipeline/run.py` produces the `FinalRecommendation` with **no DB and no LLM required**, and the seam persists it afterward — which is exactly what lets the determinism test run without a database. The seam writes the full FK lineage chain in one transaction — `user_goals → spend_simulations → simulation_results → recommendation_outputs` — every result row stamped `catalog_snapshot_version + engine_version` (D-2).

5. **The byte-identical determinism invariant is now a standing test** (build rule 8). `run_from_context(model=None)` is byte-identical on repeat (whole-object equality); `run_goal_pipeline` is byte-identical modulo the one legitimately-random input, the minted goal id (the determinism test fixes `user_id` and excludes `{goal.id, requirement.goal_id}` from the compared dump). Reviewer independently confirmed no other nondeterminism leaks onto the pipeline path — every `set`/`dict` in the engines is either a membership test or explicitly sorted before becoming ordered output, and `today` is threaded as a parameter, never read mid-pipeline.

6. **API v1 is six endpoints, one goal→package code path** (`app/api/`). `/goals/parse` is Stage 1 alone (text → intent | clarification). `/goals/recommendation` and the public, anonymous `/simulations` both run the pipeline through the shared `_run_and_respond` helper, so the marketing-site simulator returns the same real engine numbers a signed-in run would (blueprint Stage 8: "one implementation, three consumers"). `/catalog/cards` is a snapshot read returning the `acquirable` flag (Atlas listed, not offered as a new card). `/health` now reports the real snapshot version, degrading to `null` (not a 500) if the DB is unreachable — liveness must not depend on the DB. The catalog snapshot is a process-cached read model (blueprint §3.2).

## Review outcome (backend-reviewer)

Reviewer confirmed the safety-critical properties held: determinism (no hidden nondeterminism on the pipeline path), boundary adherence (orchestrator is a dumb composer with zero reward logic; only `repositories/` writes; `model=None` works end-to-end), no LLM in the middle. Found and I fixed **three findings**:

- **Critical — FK-chain violation on persist.** The recommendation endpoint minted a random `user_id` per request; `user_goals.user_id` FKs `users → auth.users`, so *every* persisted request would violate the FK against real Postgres (caught only by the best-effort `except`). Fixed by **not persisting in this phase**: persistence requires a real authenticated user that only Supabase auth can mint, which arrives in Phase 7. The endpoint computes and returns without writing (`persist=False`); the seam is built, correct, and tested for when auth lands, with the precondition documented on `persist_recommendation`.
- **Important — `total_monthly_*` column semantics.** The seam stored the cumulative `miles_at_target_date` (and a hardcoded `0` points) into monthly-named columns. Fixed to store genuine per-month averages: average points-earned across the simulated ledger, and `miles_at_target_date ÷ months_to_goal` (falling back to the full horizon when the goal is missed) — no cumulative total masquerading as a rate.
- **Important — no test for the persistence seam.** Added `tests/unit/repositories/test_results.py`: a capturing fake `AsyncConnection` asserts the FK write order, closed CHECK-constraint values (`goal_type`/`status`/`cabin_class`/`recommendation_type`/sim status all in-set), the infeasible path skips the `simulation_results` row and writes `result_id=None` + `confidence=None`, and the score/confidence ranges. Plus a polish fix: `confidence_score` is now `.quantize()`d to the column's `NUMERIC(4,2)` so the stored value is exactly what ranking computed, not what Postgres rounds to.

**215/215 total green (was 185), mypy strict, ruff clean.**

## Deviations from the blueprint (flagged)

- **Two-part response (D-5 / blueprint §8.3) is deferred, not built.** Narration currently ships *inside* the single `FinalRecommendation` (structured + narration in one round trip), rather than as a streamed/polled second part. This is harmless and fast in the only mode currently live — `model=None` template fallback, no API key yet — because there is no slow LLM call to hide. The streaming lever becomes necessary only once a live LLM key lands and narration latency is measured against the 30s budget (Scope v2). Recorded here as an explicit deferral to revisit in the same change that first exercises a real key, not as silent drift.

## Not done (deferred)

- **Live persistence + a real DB round-trip test** — waits on auth (Phase 7). The seam and its unit tests are ready; wiring `persist=True` needs a `users`/`auth.users`-backed `user_id`.
- **Two-part streaming response (D-5)** — see deviation above; revisit when a live LLM key is added.
- **Multi-turn clarification accumulation** — the pipeline supports it structurally (resubmit an accumulated `intent` to skip Stage 1); the client holds the loop, so there is no server-side session store to build.
- **Stale-chart warning path** (Stage 3 `stale_chart`) — still `False` by construction; it only fires when two snapshot generations meet (a locked chart row deactivated in a newer snapshot), which needs the goal-editing/re-run flow that doesn't exist yet.
