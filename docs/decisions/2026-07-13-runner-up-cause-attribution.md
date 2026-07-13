# Decision Log — Runner-Up Cause Attribution (Counterfactual-Verified)

**Date:** 2026-07-13
**Area:** backend (Optimization Engine, Stage-9 explanation) + frontend (strategy story)

## Context

The per-category runner-up comparison shipped 2026-07-12 deliberately refused
to name a cause when the runner-up rated HIGHER than the chosen card ("caps,
milestone bonuses and the route's own goal all shape the split"), because the
row carried no attribution. Users read that as "the engine can't differentiate"
— the exact complaint behind the Atlas-vs-TravelOne travel confusion, where
the engine knows Atlas earns 10 mi/₹100 vs TravelOne's 4 but routes travel to
TravelOne because Atlas's 30,000 EDGE/yr KrisFlyer transfer cap would strand
the extra points.

## Decisions

1. **Attribution is verified, never hypothesized.** When a runner-up rates
   strictly higher, `optimization/explain.py` runs the actual counterfactual —
   `claimed_estimate` (the generator's own estimator) with just that category
   swapped to the runner-up — and attributes the whole-plan difference.
   `StrategyAllocationDetail` gains `runner_up_reason`
   (`transfer_cap | milestone | fewer_total | equal_total | route_shape`) and
   `runner_up_plan_delta_miles` (current − swapped; engine-verified).
2. **Cap detection is an engine-owned fact, not reverse-engineered.**
   `ClaimedEstimate` gains `cap_bound_currencies` — set exactly where the
   annual link cap clamps (`points > cap_remaining`) inside `claimed_estimate`.
   (The first draft inferred cap-binding from the block-floored transfer plan
   — backend-reviewer showed that false-positives whenever a cap isn't a
   multiple of its ratio; the flag eliminates the class of bug.)
3. **The counterfactual uses the strategy's own basis.** `ranking._details_for`
   marks the forced single-card archetypes (simplest/cheapest_viable), and both
   counterfactual sides then run `include_idle_balances=False` — the same
   basis as those strategies' claims, so the delta is consistent with the
   number the user sees (reviewer finding; a wallet's idle balance otherwise
   skews the delta, hand-verified −11,600 vs −21,600 on the test fixture).
4. **`route_shape` only where declining is genuinely by design.** A gaining
   swap on a forced single-card route is owned as `route_shape` (negative
   delta). On a hill-climbed route a gaining swap is a search artifact (the
   climb optimizes the optimistic bound; the verifier is stricter) — asserting
   "declined by design" would lie, so no cause ships and the UI falls back to
   the neutral sentence (reviewer finding).
5. **Priority when the swap loses: cap > milestone > generic.** A capped swap
   usually also reshuffles milestones; the cap is the actionable fact. The
   milestone check is presence-of-loss, not magnitude — documented limitation,
   revisit if the catalog grows stacked milestone ladders.
6. **Golden tests over the real seed catalog** (hand-derivations in
   `test_explain.py`'s comment block): transfer_cap 84,200−60,000=24,200
   (Atlas/TravelOne); milestone 71,000−68,640=2,360 (Atlas Silver lost to
   Burgundy dining); route_shape −11,600; fewer_total 220 (min-transfer
   stranding — no cap, no milestone); equal_total (both floor to zero);
   idle-balance basis −21,600; hill-climbed-gaining-swap → None; cap-flag
   set/unset. 314 backend tests, mypy strict, ruff, tsc, eslint clean.
7. **UI sentence states the cause** (`strategy-story.tsx` `runnerUpSentence`):
   transfer_cap → "its yearly transfer allowance is already fully used… would
   strand the extra points and end N miles lower overall"; milestone /
   fewer_total / equal_total / route_shape each get a verified-number sentence;
   null reason (older saves) keeps the old cause-neutral fallback. Persisted
   via the existing `card_allocations` JSONB (`SavedAllocationDetail` widened
   with `str`-typed reason for forward-compat). frontend-reviewer drove all
   three live sentence variants (transfer_cap 52,000 on the user's exact
   Atlas+TravelOne scenario; milestone 41,583; route_shape 43,000) at both
   viewports; its null-delta dangling-clause finding fixed.

## Not done (deferred)

- **Milestone magnitude decomposition** (reason names the loss even when rate
  effects contribute part of the delta) — documented in-code, acceptable at
  current catalog size.
- **Cap boundary micro-tests** (earned exactly at cap / one block under) —
  the engine flag is set at the clamp site, structurally immune to the
  flooring bug; goldens cover clamped and never-engaged.
- **Multi-card-per-currency fixture** (two cards sharing a currency in one
  counterfactual) — supported by construction (per-currency cap pool), not
  separately fixtured.
- ~~Frontend-reviewer's out-of-diff observation: React duplicate-key warning
  on recurring milestones~~ — fixed in the same pass (`key` now
  `id + expectedMonth`).
