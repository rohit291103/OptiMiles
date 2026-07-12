# Decision Log — Three Distinct Routes, Card/Transfer Fee Split, and the Per-Category Earn Story

**Date:** 2026-07-12
**Area:** backend + frontend (Stages 8/9/11, narration, saved-goal API, strategy-story UI)

## Context

The user reviewed the revamped strategy UI on a real saved goal (Atlas + TravelOne wallet, Singapore business, 18 months) and reported five problems:

1. **Six route tabs** — archetype variants of the same acquisition (two "Add Diners Club Black Metal", three Magnus tiers) rendered as separate routes; "3 is enough."
2. **"Card no longer listed"** on every alternative tab — `display_names()` in `api/goals.py` only mapped ids referenced by the *recommended* strategy, so alternatives' acquisitions (Magnus etc.) always fell back to the generic label.
3. **"₹235 fees" confusion** — `total_fees_inr` folded the Axis ₹235-per-transfer program fee into the headline ("₹10,235 in fees"; "Your current cards · ₹235 fees"), and the per-category rows repeated the same cap/fee notes four times. The user's read: card fees are the price of a route; taxes/transfer micro-fees "are not our job" to headline.
4. **The spend split looked arbitrary** — everything routed to Atlas with no visible math, so TravelOne appeared "ignored" even though Atlas (2 EDGE/₹100 × 1:2 = 4 miles/₹100) genuinely beats TravelOne's default (2 RP/₹100 × 1:1 = 2 miles/₹100) on every non-travel category. The optimizer was right; the UI never showed why.
5. **No "how to earn on travel" guidance** — TravelOne's 4 RP/₹100 travel rate and DCB's 16.65 SmartBuy-portal rate were in the catalog but the UI never said how to get an accelerated rate or showed a worked example ("4 RP per ₹100 → ₹10,000 → 400 RP").

## Decisions

1. **`select_route_options()` (new, `optimization/ranking.py`) caps the package at 3 genuinely different routes.** Keep the best-ranked plan per distinct acquisition set (frozenset of `cards_to_acquire`), in rank order, max 3. Wired in `pipeline/run.py` so narration and Stage-11 assembly both see the same capped selection — `FinalRecommendation.alternatives` is now ≤ 2 everywhere (live response, persistence, narration tiers). Rationale: two archetypes converging on "add DCB" are one *route* to the user; presenting them separately reads as duplication, not honesty. The full ranked set still exists inside Stage 9 for scoring; selection is presentation policy, deterministic, and tested (dedupe, cap, order-preservation, set-identity ignoring tuple order).

2. **Fees split into `card_fees_inr` + `transfer_fees_inr` on `SimulationOutcome`** (projector computes both; `total_fees_inr` = their sum and still feeds Ranking's cost dimension, so scoring behavior is unchanged). Everything user-facing headlines **card fees only**: VerdictHero, route tabs, trade-off sentences, narration payload/template/prompt ("New-card fees ₹30,000"; the totals are no longer echo-allowed numbers). Transfer program fees surface exactly once, as a footnote in the transfer step ("the bank charges … ₹470 across this plan, billed at transfer time — not part of the card fees"). The Stage-5 valuation note was reworded to match ("billed at transfer time — not a card fee"). Persisted `strategy_options` carry both fields; older saves without them fall back to the stored total client-side.

3. **`StrategyAllocationDetail` enriched into a full reward-system story** (all fields optional → older saved artifacts still deserialize): `monthly_miles` (floor(spend × effective miles/₹100 ÷ 100) — the worked example), `currency_name`, `transfer_ratio_from/to` (from the opportunity's own transfer path), `category_label` (the catalog rule's label — how to actually get an accelerated rate, e.g. "Travel via SmartBuy portal"), and `runner_up_card_id` + `runner_up_miles_per_100inr` — the best OTHER card *available in this plan* (wallet ∪ acquisitions) for that category. Built in `optimization/explain.py` as a pure reshape of Stage-5 opportunities (no recomputation; ratios and rates pass through), threaded from `rank()` via `_story_inputs`. The runner-up is the deterministic answer to "why is TravelOne ignored?": the UI now prints, per category, "TravelOne would net 4 miles/₹100 here vs 16.65 on this card."

4. **`display_names()` (api/goals.py) now maps every id the detail references** — recommended strategy AND each `strategy_options` tier's `cards_used`/`cards_to_acquire`, plus runner-up card ids. This kills the "Card no longer listed" fallback on alternative tabs (regression-tested with a Magnus alternative).

5. **Frontend SpendStep redesigned for consistent structure** (`strategy-story.tsx`): per-card header gains a reward-system subline ("Earns EDGE Miles · transfers to KrisFlyer at 1:2"); each row shows the rate chain ("2 pts per ₹100 → 4 miles/₹100"), a worked example ("₹20,000 × 2/₹100 = 400 pts → ~800 KrisFlyer miles a month"), a gold "To get this rate: …" line when a portal/accelerated rule applies, and the runner-up sentence. **Notes are hoisted**: notes identical across a card's rows render once in a card footer; when every row of a multi-category card earns the default rate, the per-row notes collapse to one sentence. VerdictHero shows the narration summary only on the infeasible path — when feasible it duplicated the deterministic headline in a different voice (the "inconsistent explanation" the user flagged).

## Not done (deferred)

- **Forcing spend onto TravelOne (or any "equal weightage" split)** — deliberately not done, same reasoning as the 2026-07-11 entry: the split is miles-optimal; the fix is showing the math (runner-up comparison), not weakening the optimizer. If the user still wants a preference-weighted split, that's DP-07 territory.
- **Folding transfer fees into effective rates** — still the documented Stage-5 deviation (no groundable miles→INR valuation); the split keeps them visible without laundering them into a rate.
- **Persisting alternatives' full plans for saved goals** (tab-swap parity) — unchanged; alternatives still persist compactly.
- **/simulations latency (40–46s)** — still open from 2026-07-11; untouched here.

## Verification

TDD throughout (new goldens: fee split 5,000/235/5,235; monthly_miles 1,600/1,333; runner-up scoping incl. a stronger-but-unavailable card never appearing). 299 backend tests, mypy strict, ruff, tsc, eslint all green. Live pipeline run on the reported scenario now presents exactly: DCB ₹10,000 card fees / 1,42,515 mi → current cards ₹0 / 78,000 mi → Magnus ₹30,000 / 1,82,720 mi, with the SmartBuy label and runner-up comparisons attached.
