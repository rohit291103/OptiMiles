# Decision Log — Strategy Output as a "Story"

**Date:** 2026-07-11
**Area:** backend (optimization / persistence / AI reasoning) + frontend

## Context

The user found the strategy output thin and unconvincing: a saved goal showed a single "Travel → one card" row, no per-category guidance, no points math, and a stilted template explanation. They wanted the output to read as a *story* — "what your current cards reach → what adding one card unlocks → the ceiling with two" — with per-category spend guidance ("travel here, groceries there"), followable points/miles math, and prose that invites exploration.

Investigation (verified against the live engine + DB, see also `docs/tracker.md`) established:
- The thin single-category row was **stale data** from a 2026-07-06 save, before the simulator sent 5 categories. Not a live bug.
- The engine **already produces** the tiered story (`recommended` + `alternatives`, each with score breakdown + simulation), and the anonymous `/simulations` response already returns all of it — but the **saved** goal persisted only the single winner, and both UIs rendered only that, thinly.
- The engine routes all categories to one card because that is genuinely miles-optimal (one strong card wins every category). **Forcing diversification would recommend a worse plan** — dishonest. So the story is told by surfacing *per-category earn rates* (why each card wins), not by fabricating splits.

## Decisions

1. **Per-category earn detail is a presentation reshape, not new reward math.** New frozen domain type `StrategyAllocationDetail` (`app/domain/strategy.py`) + `app/optimization/explain.py` join a strategy's `spend_allocation` to the Stage-5 `RewardOpportunity` values (earn rate, effective miles/₹100, notes). `rank()` gained an optional `opportunities` param; when supplied it attaches `allocation_details` to each `RankedStrategy`. Backward-compatible — omitted in focused unit tests, threaded in from `pipeline/run.py` in production.
2. **Per-category display points are illustrative; the card total is authoritative.** Each row's `monthly_points` is a per-category floor and is explicitly documented as not-summable. The honest per-card figure (exact cross-category Decimal sum, floored ONCE — matching `allocation.py`/`projector.py`'s "one floor per card-month") is computed by `card_monthly_points()` in the backend and mirrored in the frontend, which computes the card header total from `spend × rate` the same way rather than summing the floored rows. (backend-reviewer finding, fixed with a golden test.)
3. **Persist the whole story into existing JSONB — no migration.** `repositories/results.py` now writes `allocation_details`, `score_breakdown`, `headline_differentiator`, and a compact `strategy_options` tier list (recommended + alternatives: headline/miles/fees/cards, recommended flagged) inside the free-form `simulation_results.card_allocations` column. `SavedStrategy`/`SavedGoalDetail` + `detail_from_row` reconstruct them, defaulting empty for goals saved before the fields existed. Verified with a live-DB round-trip (rolled back).
4. **Narration tells the comparison.** `ai_reasoning/narration.py` now uses the previously-dead `alternatives` param: `NarrationPayload` carries the tier comparison, the template populates `comparison_notes` deterministically ("With your current cards: X miles for no fee; Adding Magnus: Y for ₹Z (recommended)"), and the LLM prompt gets the tier facts. All tier numbers are added to `allowed_numbers` so the echo-guard still rejects fabrications; every existing narration contract preserved. Free LLM stays in place (per user); LLM-path testing kept minimal.
5. **Shared frontend story components.** `components/strategy-story.tsx` (`StrategyTiers`, `SpendRoutingDetailed`, `CardsToAcquire`) take normalized props and are used by BOTH the live simulator (`strategy-detail.tsx`) and the saved-goal view (`saved-strategy.tsx`), so live and persisted render identically. Per-category rows group by card with an expandable notes disclosure; the tier list shows a miles bar + reaches/falls-short + fees per option.

## Not done (deferred)

- **Forcing multi-card diversification** — rejected: it would recommend fewer-miles plans. The engine already splits when a split is genuinely optimal (caps/milestones).
- **Paid LLM** — staying on the free OpenRouter model per user; narration is often the deterministic template, which now tells the full comparison story on its own.
- A domain-level uniqueness guard on `SpendProfile.items` categories (backend-reviewer optional) — not currently reachable; noted for later.

## Verification
- 279 backend tests (new goldens for per-category math, per-card one-floor, tier persistence, narration comparison), mypy strict + ruff clean.
- Live `/simulations` serves `allocation_details` + `alternatives` + `comparison_notes`; live-DB save→read round-trip reconstructs every story field (rolled back).
- Frontend tsc + eslint clean; frontend-reviewer real-browser pass **clean (no crit/important)** — verified the tier comparison, grouped per-category rows, and notes disclosure across 2-tier/3-tier/single-recommendation shapes at 1440px and 390px, zero horizontal overflow, disclosure keyboard-accessible, and independently confirmed the per-card one-floor total is correct. (Saved-goal `/goals/[id]` view shares the same verified primitives but couldn't be driven past Google OAuth — low risk by construction.)
