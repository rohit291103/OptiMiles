# Decision Log — Catalog expansion (Burgundy, Amex Plat Charge, hotel programs) + first web-verification pass

**Date:** 2026-07-04
**Area:** product / backend (seed data)

## Context

Before starting build-plan Phase 4, the user redefined the supported catalog: keep the KrisFlyer core, swap standard Axis Magnus for **Magnus for Burgundy**, add **Amex Platinum Charge**, and add **Marriott Bonvoy + Accor ALL** as hotel transfer programs (transfer capability only — hotel *goals* remain out of scope). The user confirmed via Q&A: Marriott is a program only (no co-brand card), Burgundy *replaces* standard Magnus, and Regalia Gold / HSBC TravelOne / SBI Cashback stay. This amends mvp-scope-v2's card list; the engines needed zero changes — the catalog is config (build plan rule 5), and Stages 5/8 pick the new rows up automatically.

At the same time, the standing "verify `needs_verification: true` rows" debt was attacked with a live web pass (2026-07-04), since the original seeds mixed the Gemini research doc with unverified model knowledge.

## Decisions

1. **Catalog is now 9 cards, 4 partners, 14 transfer links.** Cards: Infinia, Diners Black, Regalia Gold, HSBC TravelOne, Atlas, **Magnus for Burgundy** (new slug `axis-magnus-burgundy`; the `axis-magnus` slug is gone), Amex Platinum Travel, **Amex Platinum Charge** (new), SBI Cashback (negative case, untouched). Partners: KrisFlyer, Maharaja Club, **Marriott Bonvoy**, **Accor ALL** (both `partner_type: hotel`, no award-chart rows by design — hotel redemptions are not chart-priced flights).

2. **No currency split was needed for Burgundy.** Because Burgundy *replaces* standard Magnus, the existing `axis-edge-rewards` currency simply carries Burgundy's entitlement: **5:4 to Group A** (double standard's 5:2), 2,00,000 EDGE RP/calendar-year Group A cap. Had both variants coexisted, D-1 would have forced a currency split (the HDFC-tier pattern); the replace decision avoided that.

3. **Award chart corrected to the post-1-Nov-2025 Saver chart (Zone 6 = India)** — the old values were db-schema-v1 *examples* and materially wrong: SEA business 35,000 → **45,000**; SEA economy 16,000 → **19,000**; SEA first 47,500 → **61,500**; Europe business 67,500 → **108,500**; North America business 84,500 → **117,000** (east coast; NYC is the MVP route — west is 112,500, the higher figure is seeded deliberately). Source: suitesmile.com chart dump (2026-03-28); the official singaporeair.com PDF was not fetchable, and pointsmax.in quotes 46,000 for DEL→SIN business vs the zone table's 45,000 — **all five rows stay `needs_verification: true`** until checked against the live chart.

4. **Seed corrections from the web pass** (previously wrong or unverified, now sourced):
   - **HDFC premium → Maharaja Club is 2:1, not the seeded 1:1** (pointsmath HDFC table, 2026-06-21) — a real ratio bug caught before it ever reached a user.
   - **HDFC → KrisFlyer processing is ~7 working days** (seeded 1–5); seeded as 7–10. Arrival math in the projector is unaffected (`ceil(10/30)` is still +1 month).
   - **Axis transfers carry a ₹199+GST (~₹235) per-transfer fee** — first non-zero fee rows in the catalog; still flagged for exact-amount verification.
   - **Axis removed Marriott Bonvoy, Accor and Qatar on 2026-04-02** (the April devaluation) — deliberately *no* Axis→hotel links.
   - **Atlas is discontinued for new applicants (2026)** — noted on the card; Stage 7's one-new-card archetype must not recommend acquiring it. The schema has no `acquirable` flag yet — **tracked as a Phase 4 requirement**.
   - **Atlas full milestone ladder seeded**: Silver ₹3L → 2,500 (was already there), + Gold ₹7.5L → 2,500, + Platinum ₹15L → 5,000 (annual, cumulative thresholds; paisabazaar/cardinsider 2026).
   - **Verified clean** (flags flipped to false): HSBC TravelOne rates (4/₹100 travel+forex, 2/₹100 base, uncapped) and fee ₹4,999; Amex Plat Travel 1 MR/₹50; Amex→KrisFlyer 2:1 with 1,000-MR increments; Regalia→KrisFlyer 2:1; Atlas welcome/Silver milestones.

5. **New transfer links** (all with sources): Marriott Bonvoy ← HDFC premium 2:1, HDFC Regalia 100:33, HSBC 1:1, Amex MR 1:1. Accor ALL ← HDFC premium 2:1 (devalued from 1:1 in HDFC's revamp), HDFC Regalia 2:1, HSBC 1:1. No Amex→Accor (not an MR India partner). All ratios pass `validate_catalog()`'s 1:4…5:1 sanity bounds (Regalia→Bonvoy 100:33 ≈ 3:1 is the worst in the catalog).

6. **Amex Platinum Charge shares the `amex-mr` currency** with Platinum Travel — same MR program, same transfer entitlements, so D-1 needs no second Amex currency. Card: ₹66,000 fee, 1 MR/₹40 = 2.50/₹100 default (fuel's 5 MR/₹100 not seeded — conservative), welcome benefit is hotel vouchers (not points, so no milestone row), `min_income` null (invitation/relationship-based).

7. **Magnus Burgundy's above-threshold tier is deliberately not modeled**: it earns *more* (35/₹200) beyond ₹1.5L/month, but the schema models accelerated-up-to-cap, not accelerated-above-threshold. The flat 12/₹200 base is seeded (under-promise), with the Travel EDGE 5X (30/₹100, ₹2L/month cap) as its travel category. Same conservative policy the standard-Magnus seed used.

8. **Tests updated deliberately, not mechanically** — every changed golden re-hand-computed: requirement 45,000 × 2 = 90,000 + 4,500 buffer; Burgundy dining 6.00 × 4/5 = 4.8 and travel 30.00 × 4/5 = **24.00 miles/₹100, the new best travel rate** (new golden); whole-block transfer 12,347 → 12,345 sent → 9,876 miles at 5:4 (fee ₹235 asserted); search space 16 opportunities / 8 aggregates. 104/104 green, mypy strict, ruff clean.

## Not done (deferred)

- **The live Supabase catalog was NOT reloaded.** Build plan §6 requires line-by-line human review of seed changes; the user must review this diff, then run `seeds/load_to_db.py` (the content-hash version will change, correctly).
- **Official KrisFlyer chart verification** — the singaporeair.com PDF was unreachable; the 45,000-vs-46,000 discrepancy between secondary sources is unresolved. All chart rows stay flagged.
- **Maharaja Club expansion** (HSBC 1:1 and Regalia 100:33 links exist in the wild) — still deliberately sparse.
- **`acquirable` card flag** — needed by Phase 4 so the one-new-card archetype skips discontinued Atlas.
- **mvp-scope-v2.md text edit** — the PRD still lists the old 8 cards; this entry is the authoritative amendment until the PRD gets its v2.1 pass.
