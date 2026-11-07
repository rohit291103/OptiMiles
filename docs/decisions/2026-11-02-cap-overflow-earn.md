# Decision Log — What spend above a cap earns (`over_cap_earn`), and closing both Amex cards to new applicants

**Date:** 2026-11-02 (finished 2026-11-03)
**Area:** Reward Knowledge (schema, seeds, validation) / Valuation / Simulation / Optimization / API / frontend copy
**Severity:** Critical (a calculation bug that overstated earnings), per `diagnosing-bugs`
**Follows:** the seed-verification pass of 2026-11-02 (gap 1, "Earning past a cap", and gap 4, "Amex has paused new applications")

## Context

Migration 0001 wrote one answer into the schema comment for `reward_categories.monthly_cap_inr`: "Beyond the cap, spend earns base_earn_rate". Every engine then priced overflow that way. That holds for some issuers. The Axis Atlas T&C says "Earn 2 EDGE Mile per INR 100 spent on cumulative transactions above Rs. 2,00,000 per month". It does not hold for SBI Cashback. SBI's revision notice (in force from 1 Apr 2026) says "The maximum Cashback that can be earned in a statement cycle will be capped at ₹4,000", split as online 5% up to ₹2,000 and offline (POS) 1% up to ₹2,000. Once a channel reaches its maximum, further spend in that channel earns nothing.

**Reproduction.** Best Card, SBI Cashback, ₹50,000 online, no target program:

| | Arithmetic | Points (₹ cashback) | Rate per ₹100 |
|---|---|---|---|
| Before | 40,000 × 5% + 10,000 × 1% = 2,000 + 100 | **2,100** | 4.20 |
| After | 40,000 × 5% + 10,000 × 0 = 2,000 + 0 | **2,000** | 4.00 |

The offline case was also wrong. The seed had no offline cap, so ₹2,50,000 offline paid ₹2,500. The correct figure is 2,00,000 × 1% = ₹2,000.

**Where overflow was calculated.** There were two implementations:

1. `valuation/transfer_math.blended_earn_rate`, used by Best Card (`best_card._effective_rate`) and Stage 5 (`valuation/opportunities.py`). Optimization (`allocation.py`, `explain.py`, `feasibility.py`) uses only the blended `RewardOpportunity.earn_rate` from Stage 5, so it inherited the bug and computes no overflow of its own.
2. `simulation/projector.py`, which had its own copy of the split (`min(S,cap)×rate + (S−cap)×base`).

Portfolio View and the activity log (`simulation/observed.py`) show and measure caps, but neither calculates overflow earnings.

## Decisions

1. **One field on the category rule: `over_cap_earn`, either `base_rate` or `nothing`.**
   - It is a fact about each capped rule, taken from the issuer's terms, so it belongs on the rule rather than in engine code.
   - The name follows the domain-modeling vocabulary ("reward cap"). `nothing` was chosen over `none` so it cannot be confused with null or Python `None`.
   - A two-value enum covers every issuer behaviour in the catalog today. A numeric "overflow rate" would invite people to make up a third number.

2. **One implementation.** `transfer_math.over_cap_rate`, `category_points_exact` and `blended_earn_rate(spend, rule, base_rate)` are the only overflow code in the codebase.
   - The projector now calls `category_points_exact`, and its private copy is deleted.
   - `blended_earn_rate` now takes the **rule** instead of loose rates, so a caller cannot price a cap without also passing what the overflow earns.
   - The projector and Stage 5 can no longer disagree about overflow.

3. **Never default it silently. Enforcement happens at three levels:**
   - **DB:** the CHECK `(over_cap_earn IS NULL) = (no cap)`, with no DEFAULT.
   - **`validate_catalog`:** **CR-01** rejects a capped rule that does not state the field. **CR-02** rejects an uncapped rule that does state it (usually a sign the cap was forgotten).
   - **Earn math:** `over_cap_rate` raises on a capped rule with `None` instead of assuming base, even when the spend is under the cap, because the row itself is broken.
   - Why fail rather than default: the defect *was* a default. A new capped row with no stated overflow is the exact situation that produced this bug.

4. **Migration 0009 uses an explicit backfill, not a default.**
   - Every row that is capped today was loaded under 0001's documented semantics, so it is set to `'base_rate'`. This restates what the database already claimed.
   - SBI Cashback's online rule is then set to `'nothing'` (matched by bank, card_name and slug), so the live DB does not keep the known-wrong value until the next seed load.
   - The reviewed seeds overwrite the backfill on load.
   - The migration file is written but not applied.

5. **Seed values.**

   | Rule | `over_cap_earn` | Basis |
   |---|---|---|
   | sbi-cashback:online (cap ₹40,000) | `nothing` | Issuer revision PDF, quoted above |
   | sbi-cashback:default (**new** cap ₹2,00,000 = ₹2,000 ÷ 1%) | `nothing` | Issuer revision PDF, "1% Offline (POS at Merchant Outlets) ₹2,000" |
   | axis-atlas:travel (cap ₹2,00,000) | `base_rate` | Issuer T&C, quoted above |
   | hdfc-infinia:travel (cap ₹1,50,000) | `base_rate`, **needs_verification** | hdfcbank.com returned 403. Secondary sources say the SmartBuy cap limits only the bonus and base points keep accruing. |
   | hdfc-diners-black:travel (cap ₹1,50,000) | `base_rate`, **needs_verification** | Same as Infinia |
   | axis-magnus-burgundy:travel (cap ₹2,00,000) | `base_rate`, **needs_verification** | The Burgundy T&C PDF could not be text-extracted. Axis's accelerated-35 T&C says Travel EDGE 5X "will be calculated on Base EDGE Reward points". |

   - All three unverified rows were already `needs_verification: true` because their cap unit or value is in doubt.
   - Choosing `base_rate` for them is a judgment call: the sources available all describe these as bonus-on-top-of-base structures.
   - If a reviewer prefers to under-promise until HDFC/Axis terms are read, flip them to `nothing`. Only Infinia/DCB/Magnus over-cap goldens would change.

6. **Surfaces now say it.**
   - `over_cap_earn` is exposed on the Best Card option, Portfolio earn rules, education earn rules and `CapStructure`.
   - Stage 5's valuation note now names the overflow behaviour.
   - Frontend copy that said "blended down to the base rate" or "more spend here earns the base rate" now follows the field. The activity-log "used up" line is neutral, because `CapUse` does not carry the field yet.

7. **Amex Platinum Travel and Platinum Charge are `acquirable: false`** (user decision).
   - Both issuer pages, re-checked 2026-11-03, say: "We are temporarily pausing the acceptance of new card applications in India as we make planned updates to our technology platforms for domestic card issuing operations."
   - Existing holders keep full support, and a test pins that an in-wallet Platinum Travel is still allocated spend.
   - The Stage 7 test uses the ₹5,000-fee-cap, empty-wallet fixture, where Platinum Travel used to be an acquisition candidate. With `acquirable: true` it still is, which was checked to make sure the test is not vacuous.
   - Flip back when Amex reopens applications.

## Fix round (2026-11-03, after backend review — no critical findings)

8. **Best Card rounded twice past a cap. Fixed.**
   - Before: `points_earned` was floor(amount/100 × the 4dp ROUND_DOWN blended rate).
   - After: it is **floor(`category_points_exact`)**, one floor of the exact cap split. The blended rate is display only.
   - Goldens:
     - SBI online ₹50,001: exact (40,000×5 + 10,001×0)/100 = 2,000.00 ⇒ **2,000**. The old path gave 500.01 × 3.9999 = 1,999.96 ⇒ 1,999.
     - Atlas travel ₹2,00,001: (200,000×5 + 1×2)/100 = 10,000.02 ⇒ **10,000** points and 20,000 miles at 1:2. The old path gave 2,000.01 × 4.9999 = 9,999.85 ⇒ 9,999 points and 19,998 miles.
   - **Stage 5 (`opportunities.py`)** computes no points, so it has no double floor. It emits the 4dp blended `earn_rate` and `miles_per_100` of that rate, which are ranking inputs.
   - **Optimization does round twice, and that is documented.** `allocation.py` (`_card_monthly`) and `explain.card_monthly_points` multiply spend by that already-quantized rate before their own floor. The `allocation.py` module docstring documents this: under a point per capped card-month, far below `reconcile_claim`'s 10% flag. The projector does the exact split once and wins any disagreement. This is a known, bounded difference, not parity.

9. **Migration 0009 backfill now also fixes SBI's offline rule.** The predicate is now `category_slug IN ('online', 'default')`, still limited to SBI Cashback and to rows capped at migration time. On a pre-0009 DB the `default` row is uncapped (its cap arrives with the seed load), so that half matches nothing today. It keeps any capped SBI rule off the base-rate backfill.

10. **Overflow provenance is machine-checked.**
    - Every capped rule now carries **`over_cap_earn_source`**: an issuer https URL, or text starting `secondary:`. It is a seed meta key, stripped by the loader, so it never reaches the snapshot or its hash.
    - `test_unsourced_overflow_keeps_its_rule_unverified` parses the YAML. Any capped rule whose source is not an issuer domain (allowlist: sbicard.com, axis.bank.in, axisbank.com, hdfcbank.com, hsbc.co.in, americanexpress.com; https only; exact host or subdomain) must be `needs_verification: true`.
    - Infinia travel, DCB travel and Magnus Travel EDGE are `secondary:`, and **each of those rows was already `needs_verification: true`**. The `false` values near them belong to other rows: the default rules, the card headers and the fee-waiver blocks.
    - **No flag changed in this round, so Portfolio leader selection is unchanged.** These three rows were already Listed tier. On the travel category, Portfolio already withholds the leader (`leader_withheld_unverified`) when the would-be winner is one of them, and does not promote a verified runner-up.

11. **CR-03: only monthly caps are allowed.** `category_points_exact` honours only `monthly_cap_inr`, so a quarterly or annual cap would have earned uncapped in Best Card and Stage 5. This was the smaller correct option:
    - `validate_catalog` **CR-03** rejects any rule with a quarterly or annual cap, whether alone or next to a monthly one. No seed has one.
    - `category_points_exact` also raises on one, as a second guard.
    - The projector already refused them. Support should arrive together with an engine that actually meters the period.

## Not done / follow-ups

- **`CapUse.over_cap_earn`** (activity log, `simulation/observed.py`). The fee-waiver agent owns that file this round. Once it lands, the "cap used up" copy can say "earns nothing" or "earns the base rate" exactly.
- **Quarterly and annual caps** are refused everywhere (CR-03 and the earn maths). Supporting them means metering the period in Best Card, Stage 5 and the projector together.
- **Zero-earn MCC exclusions** (fuel, rent, wallet and so on fall through to `default` on every card). These are a separate overstatement (seed-verification gap 2), not fixed here.
- **SBI's statement cycle** is still metered as a calendar month.

## Verification

- Red first: the import failed, and then 160 tests failed until the seeds stated the field, which shows the engine refuses an unstated overflow.
- Final run: pytest **689 passed**. 17 of them are new for this work: transfer_math +4 (its 5-test blended section was rewritten as 9 tests against the rule-based signature), best_card +4, projector +1, opportunities +1, validation +3, seed_catalog +1 (overflow golden, plus the Atlas acquirable test generalised to the 3 closed cards), strategies +2 and portfolio +1. The other new tests in the count belong to the concurrent fee-waiver agent.
- `mypy app` is clean (strict). `ruff check` is clean for this work; the 3 remaining E501s are in the fee-waiver agent's in-progress activity files. Frontend `tsc` and `eslint` are clean.
- No existing golden value changed: no seeded card's overflow behaviour moved from base, and SBI is not in any goal fixture because it has no transfer links.
