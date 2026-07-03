# Decision Log — Phase 2: Valuation Engine mathematical contract

**Date:** 2026-07-04
**Area:** backend

## Context

Build-plan Phase 2 (Valuation Engine) implemented test-first: `transfer_math.py`
(pure arithmetic, the shared calculation vocabulary for Optimization and
Simulation per blueprint §3.1) and `opportunities.py` (Stage 5 enumeration).
The user explicitly required the engines to be "engineered with proper logic
and mathematics" — this entry records the mathematical contract and its two
deliberate deviations from the blueprint's wording. Per build-plan watchout #1,
the full spec lives as module docstrings + 26 hand-computed tests, not a
standalone doc.

## Decisions

1. **Exact arithmetic only.** `int` for points/miles/INR, `Decimal` for rates;
   floats never touch reward math. Enforced by usage and mypy strict.
2. **Rounding is directional — always the conservative side, chosen per
   formula and documented in the docstring:**
   - Transfers floor to whole ratio blocks: `miles = floor(points/ratio_from) × ratio_to`
     (you cannot transfer a fraction of a block; flooring never overstates).
   - Rates quantize to 4dp ROUND_DOWN (under-promise miles per ₹100).
   - The Stage 3 requirement buffer ceils UP (never understate what's needed).
3. **Cap economics are blended, not headline:** an opportunity is priced at
   `blended_earn_rate = (cap×acc + (spend−cap)×base) / spend` for the profile's
   whole-category monthly spend — the decision-relevant number at Stage 7's
   allocation granularity (one card per category). Golden: ₹200k into
   Infinia's ₹150k travel cap = 13.32 pts/₹100, not 16.65. Quarterly/annual
   caps ride along in `cap_structure` for the Simulation Engine's monthly
   ledger; only the monthly cap participates in the static blend.
4. **Deviation (documented): flat transfer fees are NOT folded into
   `effective_miles_per_100inr`** despite the blueprint's "amortized fees"
   phrasing. Folding an INR fee into a miles-rate requires a miles→INR
   valuation the MVP catalog cannot ground (no cash-price data). Fees stay
   explicit on `transfer_path`, get summed into `total_fees_inr` by
   Simulation, and are scored in Ranking's cost dimension. A fee > 0 always
   emits a valuation note.
5. **Deviation (documented): annual transfer caps applied once, not
   per-year** — `transferable_points` treats `max_transfer_points` as a
   single-application cap, which is exact for MVP horizons ≤ 12 months and
   conservative for longer ones. Multi-year horizons must re-apply per
   calendar year (flagged in the docstring).
6. **Enumeration contract:** one opportunity per (eligible card ×
   spend-profile category); eligibility strictly card → currency → active
   link (D-1), which makes "SBI Cashback yields zero KrisFlyer opportunities"
   true by construction and pinned by test. Categories a card doesn't
   accelerate fall back to its `default` rule with an explanatory
   valuation note. Output order is deterministic (cards by id, categories in
   profile order) — byte-replayability extends to intermediate artifacts.

7. **Phase-exit reviewer round (all findings fixed same-day):** the reviewer
   independently recomputed all 24 golden values — every one matched. One
   Important find: `.normalize()` after `.quantize()` turned round-number
   rates into scientific notation (`Decimal("10.0000").normalize()` →
   `1E+1`), which would have serialized the literal string "1E+1" into JSONB
   and API payloads; invisible to tests because Decimal equality is
   value-based. Fixed by keeping the fixed 4dp form (display formatting is
   the caller's job) + a str()-based regression test. Also closed the
   coverage gap: DCB / Regalia Gold / HSBC TravelOne now carry pinned golden
   assertions (previously only counted), incl. a DCB-blends-like-Infinia
   currency-sharing canary (D-1). 73 tests total.

## Not done (deferred)

- Redemption-value estimation (₹ value per mile) — needs cash-price data the
  catalog doesn't have; without it, fee amortization and "efficiency vs cash"
  comparisons stay out of the rate math.
- Welcome-bonus timing/eligibility nuance (first-spend conditions) — Stage 7/8
  concern; aggregates currently expose the total only.
- Multi-hop transfer paths (currency → program → program) — MVP is direct
  links only, per blueprint Stage 5.
