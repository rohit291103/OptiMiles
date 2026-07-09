# Decision Log — Phase 3: Simulation Engine semantic contract

**Date:** 2026-07-04
**Area:** backend

## Context

Build-plan Phase 3 delivered `app/simulation/projector.py` — `simulate(strategy, context) → SimulationOutcome`, the Stage 8 month-by-month ledger — test-first against `simulation-engine-spec-v1.md` (SIM-001) and system-execution-flow-v1.md Stage 8. The spec leaves several timing/rounding semantics open, and a few of its business rules cannot be honestly implemented with the MVP's inputs. Each choice below is documented in the module docstring; this entry records the *why* and the review outcome. The math contract from Phase 2 (exact arithmetic, directional conservative rounding, hand-computed goldens) carries over unchanged.

## Decisions

1. **Months are 0-based and the full horizon is always simulated.** Ledger covers months 0…`horizon_months`−1, matching `TransferPlanItem.planned_month` ("0 = this month"). SIM-001 BR-08 says "stop immediately when the goal becomes achievable"; we record `months_to_goal` at the first achieving month but keep simulating to the horizon, because Ranking (Stage 9) needs complete buffer/fee/near-miss data — the same reasoning as the spec's own repo note on `misses_goal`. Narration can render 1-based months for humans.

2. **Within-month order: spend → cap-aware earn → milestones → transfers → goal progress.** Milestone bonuses are therefore transferable in the month they land; transferred points leave before next month's earn. Transfers initiate at month end, so arrival is `planned_month + ceil(processing_days_max / 30)` — any nonzero processing window conservatively spills into the next month (max days, ceiling division: under-promise arrival, never overstate). Miles arriving at/after the horizon are recorded on the `TransferExecution` but never reach `cumulative_target_miles` — a transfer landing after the target date is exactly the failure this engine exists to catch, and it is golden-tested both ways.

3. **Earning floors once per card-month, not per category.** Per routed category: `min(S, cap)/100 × rule_rate + max(S−cap, 0)/100 × base_rate`, summed exactly (Decimal) across the card's categories, floored once to an int at credit. Monthly caps meter each month independently (they reset) — this is the "cap-truth layer" that corrects Stage 5's static blend, which the Phase 2 reviewer asked Phase 3 to confirm. **Confirmed by the Phase 3 reviewer:** the projector reads raw `snapshot.category_rules` (never Valuation's derived opportunity output), so there is no double-counting between the static blend and the metered ledger.

4. **Only monthly spend caps are metered in v1.** No seed row uses `quarterly_cap_inr`/`annual_cap_inr`; a rule carrying one raises `ValueError` rather than silently overstating earnings (Unknown Over Incorrect). Both branches of the guard are pinned by tests.

5. **Milestones come from catalog truth, never `strategy.expected_milestones`** (the simulation is the receipt; where it disagrees with the generator, it wins). Thresholds are ≥ (exactly-at triggers — boundary-tested at ₹400,000 exactly and one rupee under). Periods: QUARTERLY measures within plan quarters (months 0–2, 3–5, …) and re-fires each quarter; ANNUAL/ONE_TIME measure cumulative-since-month-0 and fire at most once in the ≤12-month MVP horizon (the same single-application deviation as the annual transfer cap, Phase 2 decision item 2); MONTHLY measures within the month. Welcome bonuses fire for **acquired cards only**, with the card's first spend; wallet cards never re-earn them. Wallet cards' pre-plan spend toward thresholds is not modeled (counter starts at 0 — delays bonuses, conservative).

6. **Transfers send whole ratio blocks; the remainder stays on the card.** Ratio conversion is delegated to `valuation.transfer_math` — a new `whole_block_transfer(points, link) → (points_sent, miles)` helper exposes the points side of the same floor `points_to_miles` already computed, so flooring never destroys balance points and the conversion formula still lives in exactly one place. This helper exists because the Phase 3 reviewer rejected the projector's initial inline reimplementation as an avoidable duplication of "the one sanctioned intra-stage exception" — the fix moved the math into `transfer_math` rather than documenting the duplication. The only transfer state kept in the projector is the cumulative annual-link-cap bookkeeping across a plan's transfers (correctly not a stateless-math concern; applied once per horizon, exact for ≤12 months, same as Phase 2 item 2).

7. **BR-05/BR-06 (milestone validity windows) are not evaluated by the v1 projector — and `validate_catalog()` now rejects any seed row carrying `valid_from`/`valid_until`.** The projector has no calendar anchor (inputs are relative months), so it cannot check validity honestly. The reviewer flagged that a future expired-promo seed row would silently influence every projection; the guard makes that impossible at snapshot-load/CI time instead. Implementing BR-05/06 later requires giving the simulation a plan-start date — remove the guard in the same change.

8. **`total_fees_inr` = joining fees of acquired cards + transfer fees paid.** Wallet cards' annual fees are sunk costs of the status quo, not of the strategy under evaluation; Ranking's cost dimension prices card fees from the strategy itself. `buffer_achieved` compares target-date miles against required + buffer; `months_to_goal` compares against the raw requirement (buffer excluded) — the buffer is a safety margin, not a moving goalpost.

9. **Anniversary/category bonuses excluded from v1** (no anniversary dates in context; SIM-001 §11 "invalid milestone → exclude"). A `spend_bonus` row with a missing threshold is likewise excluded silently, per the same table — pinned by test.

## Review outcome

`backend-reviewer` independently recomputed all 24 golden values from seed rows — every one matched. Its two substantive findings (transfer-math duplication → decision 6; BR-05/06 gap → decision 7) and two coverage gaps (threshold-`None` exclusion, quarterly-cap guard branch) were fixed in-phase. Two mutation checks (breaking arrival delay and earn flooring) confirmed the goldens bite: 3 and 12 test failures respectively. Suite at phase close: 103/103, mypy strict, ruff clean.

## Not done (deferred)

- **`claimed_total_miles` reconciliation** (Stage 8 failure table: flag a large generator-claim vs simulated-total gap as a generator-bug signal in logs). Deliberately deferred to Phase 4/pipeline — the comparison needs Stage 7's generator to exist so both sides mean something. Tracked in the tracker's Next up.
- **BR-05/BR-06 enforcement** (needs a calendar anchor in the simulation inputs) — guarded against instead, per decision 7.
- **Variable monthly spend** (SIM-001 §14 future extension) — BR-02 fixed-spend assumption baked in; the welcome-bonus spend check is loop-invariant under it (noted in the docstring so a future variable-spend change re-derives it).
