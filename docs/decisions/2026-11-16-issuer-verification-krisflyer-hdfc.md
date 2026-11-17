# Decision Log — Issuer verification pass: KrisFlyer chart and HDFC

**Date:** 2026-11-16
**Area:** backend (seed catalog)

## Context

Week 47's goal is "Verified by Default": nothing the product recommends may be built from unverified rows (root `CLAUDE.md`, *Scope: Breadth With Depth*). Session 1 had to verify the rows the bots could not read, because the issuer sites block automated fetches. Before this session 30 seed rows were flagged `needs_verification`, including all 5 KrisFlyer award-chart rows, which every goal depends on.

The user supplied the evidence by hand:
- screenshots of the singaporeair.com KrisFlyer miles calculator
- HDFC's own documents, saved as PDFs: the SmartBuy offer page, the MITC, and the Infinia Reward Points T&C

Three read-only agents extracted the HDFC documents in parallel, and every quote they relied on was checked against the source before any seed was edited.

**Result:** flagged rows went from 30 to 25. Backend suite: 787 passed.

## Decisions

1. **India → Singapore award rows are verified from the airline's own calculator** (Economy 19,000 / Business 45,000 / First 61,500 Saver, one-way).
   - Mumbai and Chennai gave identical figures on all four cabins, so the airline itself confirms that India is priced as a single zone.
   - That settles the secondary figures that kept these rows flagged (pointsmax: 46,000 / 17,500 / 13,000).

2. **India → London and India → New York stay flagged.**
   - The calculator prices only Singapore Airlines' own nonstops. Both routes connect in Singapore, so the calculator returns nothing for them.
   - The rows are annotated so that nobody fills the gap by adding BOM–SIN and SIN–LHR together. KrisFlyer prices a connecting trip by origin and destination zone, not leg by leg.
   - The source to look for is the full zone-to-zone award chart.

3. **Unsourced taxes are removed, not verified with the rows.**
   - All 5 award-chart rows carried a `taxes_fees_inr` figure (₹6,500–₹38,000) with no source.
   - That figure reached the API as `requirement.taxes_fees_inr_estimate`, and the narration step could have repeated it.
   - Verification is a single flag per row, so clearing the flag would have vouched for those invented numbers too. The field is now absent, and the API reports taxes as unknown (`null`).
   - Taxes come back only with a dated source, for example a singaporeair.com award search.
   - Tests: `test_unsourced_taxes_are_absent_not_estimated` covers the null case. `test_sourced_taxes_scale_with_passengers` keeps the per-passenger maths tested.

4. **The Infinia and Diners Black Metal SmartBuy rows are verified from HDFC's SmartBuy offer page** (offer 15282, Offer Details tab, p.2/p.4/p.5).
   - **Multipliers and caps:** flights 5X and hotels 10X. Infinia's monthly cap is 15,000 and Diners Black Metal's is 10,000. Each card's daily cap equals its monthly cap, so it never binds.
   - **What "NX" means:** the page's worked example ("Hotel: Rs 50000 → 14985" accelerated points = 333 blocks × 45) proves that "NX" is the *total* including base. The seed's 20-bonus-points-per-₹150 conversion is therefore correct.
   - **Above the cap:** what that spend earns is now sourced from the issuer: "*Users will continue to earn Base Reward Points … over and above the Accelerated Reward Points."
   - **Narrower label:** the rows now read "Flights & hotels via SmartBuy portal", because SmartBuy rail earns only 3X. The old "Travel" label overstated it.
   - **Time-limited offer:** the page states an offer window ending 30-11-2026. Category rules have no validity date, so the window lives in the notes and needs re-checking.

5. **Three numbers were wrong and are corrected:**
   - **`hdfc-rp-premium` expiry: 2 years → 3 years.** MITC p.23 names Infinia and Diners Black as the exception to HDFC's 2-year default.
   - **Diners Black Metal earns nothing on fuel.** MITC p.7. A zero-earn row was added.
   - **Infinia earns nothing on fuel.** Cl.2 of the Infinia-branded Reward Points T&C. A zero-earn row was added.
     - The MITC's p.7 list does not name Infinia, so HDFC's documents disagree on this point.
     - We follow the Infinia-specific document. If it turns out to be wrong, we under-promise rather than over-promise.
   - Before these fixes, both cards counted fuel spend at 3.33 points per ₹100.

6. **Issuer documents are kept under `docs/TnC-docs/<Issuer>/`** with the filenames they were downloaded under.
   - Seed `source` fields cite them by path and page.
   - When an issuer URL exists, the cap-overflow source is that URL alone; the guard test requires it.
   - This folder sits outside the six standard `/docs` subfolders. It holds source evidence, not a category of our own writing, so a docs audit should treat it as expected.

7. **How this session was scoped:** apply the rows Session 1 targeted, plus any number shown to be wrong. Everything else the documents revealed is parked, so verification does not turn into an unreviewed catalog expansion.

## Not done (deferred)

- **Axis Burgundy and Atlas (5 rows):** waiting on the Axis T&C. Carried to the weekend as the rest of Session 1.
- **The live database has not been reloaded,** so the seeds are ahead of it (`cat-10cfcc27cd0b`).
  - Run `seeds/load_to_db.py` *before* pushing the backend.
  - The API reads verification flags from the YAML at runtime by row id. A backend deployed ahead of the database would mark rows verified while the database still serves their old values.
- **Parked findings from the HDFC documents:**
  - Grocery, utility and telecom caps of 2,000 points per month, and the insurance cap: no categories or caps for these yet.
  - HDFC rounds points down per ₹150 (₹200 for Regalia Gold) block. Our smooth per-₹100 rate can overstate a single transaction by up to about 5 points. This is an engine-level issue.
  - Sourced ₹-per-point values: 1 point = ₹1 on SmartBuy flights and hotels for Infinia and Diners Black (₹0.50 for Regalia), up to 70% of the booking. Regalia Gold's cashback value is ₹0.15. These are inputs to next week's valuation work.
  - Turkish Miles&Smiles and Avianca LifeMiles at 2:1 from `hdfc-rp-premium`.
  - Regalia Gold Priority Pass guest charge (USD 27): now has an issuer source in the MITC. The lounge row could be cleared.
  - All three HDFC fee-waiver windows stay flagged. The MITC never defines the "year".
  - Infinia retention rule: from 1 Apr 2026 it needs ₹18L of spend in the financial year, or ₹50L relationship value. That is stricter than the ₹10L fee waiver, and no field exists for it.
  - The MITC contradicts itself on whether the Rs 2 lounge validation charge is reversed.
  - A Regalia Gold SmartBuy row: the page says "Regalia", never "Regalia Gold", so it is not added.
- **First Saver availability:** a secondary source says First isn't flown on some India–Singapore nonstops, for example Bengaluru. A priced chart row does not guarantee the cabin exists from every city.
- **Effect on Session 3:** London and New York are now the only goals built on unverified award-chart rows. When enforcement lands, decide whether those two routes are refused or labelled.
