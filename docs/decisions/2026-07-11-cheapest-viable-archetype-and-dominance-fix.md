# Decision Log — Cheapest-Viable Archetype + Dominance-Pruning Fix

**Date:** 2026-07-11
**Area:** backend (Optimization Engine, Stages 7 & 9) / frontend

## Context

After the strategy-UX revamp shipped, the user tried it live and found the
underlying recommendations, not just the presentation, were the problem:
every acquiring option shown was Axis Magnus for Burgundy (₹30,000 fee), with
no mid-cost alternative — even though HDFC Diners Club Black Metal (₹10,000)
also clears the same goal. The user asked directly why the optimizer never
proposes a cheaper card, and asked to work on the ranking engine.

Diagnosis, done against the live API and the real seed catalog before
touching any code:

1. **`generate_candidates`'s four archetypes all optimize for miles, never
   cost.** `one_new_card` keeps only the best-3-by-claim acquisitions;
   `simplest_viable` picks the single wallet-eligible card with the
   *highest* claim among those that clear the goal. No archetype searches
   for "cheapest card that still works."
2. **`hill_climb` ignores its starting basin.** Because
   `candidate_opportunities` returns the *global* candidate pool regardless
   of which card a basin nominally "started" from, climbing from any
   card's solo assignment converges to whichever card has the best rate
   (Magnus/Infinia) — proven by instrumenting `hill_climb` directly:
   seeding it with HSBC, Regalia, or Amex Platinum Travel as the "test"
   card produced the *identical* Magnus-only allocation in every case, at
   miles=97,280 on the golden fixture. A cheap-card search cannot
   hill-climb; it must force the category onto the card being tested.
3. **Even once generated (`_solo_assignment`, no climb), BR-02's
   "≥5%-over-baseline" gate silently discards the cheap acquisition** when
   the wallet's own status quo is already strong. Hand-verified on the
   user's exact reported scenario (Infinia + Atlas wallet, the app's own
   default): status quo claims 59,565 miles; Diners Club Black Metal alone
   claims 51,282 (still ≥ the 45,000 target) but `51,282 ≤ 59,565 × 1.05`,
   so it fails BR-02 and never becomes a candidate.
4. **Even exempted from BR-02, ranking's dominance prune (`_prune` /
   `dominated_by`) discards it anyway** — a cheaper acquisition that earns
   fewer miles than a strictly-cheaper, no-new-card status quo is, by the
   classical multi-objective definition, dominated (worse-or-equal on every
   raw dimension, strictly worse on miles) and gets silently dropped before
   scoring, regardless of BR-02.

Both (3) and (4) are real product bugs, not correct behavior: "add one cheap
card" and "use what I have" are different trade-offs a cost-conscious user
weighs on cost vs. miles — not a strict downgrade the ranking engine should
auto-hide.

## Decisions

1. **New `CHEAPEST_VIABLE` archetype** (`StrategyArchetype.CHEAPEST_VIABLE`,
   `app/optimization/strategies.py`): iterates every acquirable card not
   already in the wallet, sorted by `(annual_fee_inr, card_id)` ascending,
   forces every profile category onto that one card (**no hill-climb** —
   climbing would walk straight back to Magnus, defeating the point), keeps
   the first (cheapest) whose claim clears `miles_required_total`. This is
   basin #5, alongside the existing four; `_MAX_CANDIDATES=8` headroom was
   confirmed sufficient (backend-reviewer checked the worst-case draft
   count doesn't exceed the bound).
2. **`CHEAPEST_VIABLE` is exempt from BR-02** (the "≥5%-over-baseline" gate
   in `_build_validated`) — its justification is "cheapest card that still
   clears the goal," not "beats the status quo by a margin." Every other
   acquiring archetype keeps the BR-02 gate unchanged.
3. **Ranking's dominance prune exempts GOAL-ACHIEVING acquiring candidates
   from domination by non-acquiring candidates** (`_RawDimensions.acquires`
   + the `dominated_by` short-circuit in `app/optimization/ranking.py`).
   Scoped narrowly: (a) only protects candidates that reach the goal in
   simulation (`months != _NEVER`) — a goal-missing acquisition gets no
   exemption, since the achieving-before-missing hard rule already excludes
   it from recommendation and exempting it would just add dead weight to
   the candidate set; (b) only protects against non-acquiring dominators —
   two acquiring candidates (e.g. two different Magnus plans) still prune
   normally, so a genuinely worse acquisition can't hide behind a better
   one.
4. **Frontend needed zero changes** to render the new tier — `strategy-story.tsx`'s
   `StrategyPlanTabs` already builds tabs generically from
   `[recommended, ...alternatives]` with no hardcoded count. Verified live
   by frontend-reviewer: the exact reported scenario now renders 4 distinct
   route tabs (status quo ₹0 / 235 fee, two Magnus variants at ₹30,235 and
   ₹30,470, Diners Club at ₹10,000), correct trade-off sentence, correct
   per-tab plan swap, zero console errors, at both 1440×900 and 390×844.
5. **Tab-label disambiguation added** (`strategy-story.tsx`'s `tierLabel`):
   two tiers can legitimately converge on the same card from different
   archetypes (e.g. `concentrated` and `one_new_card` both landing on
   Magnus with slightly different miles/fees) — this was flagged by
   frontend-reviewer as a legibility risk ("looks like a duplicate bug"
   even though the underlying numbers differ). `tierLabel` now appends the
   engine's own `headline_differentiator` (e.g. "balanced," "lowest fees")
   in parentheses ONLY when another visible tier shares the same
   card-acquisition label. `PlanTier` gained a `headline: string` field,
   threaded from `RankedStrategy.headline_differentiator` (live) and
   `SavedStrategyOption.headline_differentiator` (saved goals).
6. **backend-reviewer ran an independent pass** on both the archetype and
   the dominance exemption: no critical/important findings against
   correctness, determinism, or module boundaries (no LLM involvement, no
   new top-level module, reward math stays in `allocation.py`). Two
   optional-polish notes applied: (a) the dominance exemption was
   originally unscoped to goal-achieving candidates — tightened per decision
   #3 above, with a new test (`test_goal_missing_acquisition_gets_no_dominance_exemption`)
   pinning the boundary; (b) a fee-tie-break test gap was flagged (no two
   currently-acquirable seed cards share a fee, so the tie-break on card id
   in the sort key is currently unexercised by real data) — accepted as a
   documented, low-value-to-test edge case rather than forcing synthetic
   catalog injection this codebase has no existing pattern for.

Verified live end-to-end on the user's exact reported scenario
(Hyderabad→Singapore business, 8mo, Infinia+Atlas wallet, the app's default
spend split): the response now shows **status quo (₹0, 59,565mi, recommended)
→ Diners Club Black Metal (₹10,000, 51,282mi) → Magnus for Burgundy
(₹30,235–30,470, 73,920–76,120mi)** — a genuine free/cheap/premium spread
instead of only free-or-₹30k.

286 backend tests (up from 283), mypy strict + ruff clean. Frontend tsc +
eslint clean.

## Not done (deferred)

- **Backend latency**: frontend-reviewer measured `POST /simulations` at
  40–46s live during this verification pass (worse than the previously
  flagged 36–44s, and the narration LLM call is retrying on attempt 1 every
  request per the backend log) — pre-existing, not caused by this change,
  but now blocking manual QA with default Playwright timeouts. Tracker
  already carries this; escalating again given it's getting worse, not
  better.
- **Fee-tie-break test**: no acquirable seed card currently ties another on
  `annual_fee_inr`, so the deterministic tie-break (`str(card_id)` as the
  secondary sort key) has no real-data test. Revisit if the catalog changes
  to introduce a genuine tie.
- **DP-07 preference-aware ranking weights** would let a user's "prefer
  cheap cards" signal (already collected client-side in the goal-entry
  revamp) actually reweight `cost` vs `efficiency` server-side, rather than
  just picking a default tab — still deferred pending the
  preference-persistence story, unchanged from the prior session's
  decision log.
