# Decision Log: Seed verification against issuer sources, and zero-earn categories

**Date:** 2026-11-06
**Area:** Reward Knowledge (seeds), with knock-on golden updates in Valuation, Simulation and Optimization tests
**Follows:** tracker "Next up" from 2026-11-03 (the unverified seed questions and the zero-earn categories)
**Severity:** One calculation defect in a row marked *verified* (TravelOne travel was uncapped). The other changes correct conservative or unsourced values.

## Context

37 seed rows still had `needs_verification: true`, and the tracker listed open seed questions: SmartBuy cap units, over-cap behaviour, the HSBC strict-vs-inclusive waiver, Amex milestone transferability, SBI income and lounge. A separate defect was also listed. Categories that earn nothing (fuel, utilities) fell through to the `default` row, so every card earned its base rate on them.

This pass checked each row against the issuer's own pages and PDFs. PDFs that WebFetch couldn't parse were extracted locally with `pypdf`. Where the issuer page could not be read, the row stayed flagged. Specifically: HDFC (`hdfcbank.com` and `offers.smartbuy` return 403 to automated fetches), Axis Travel EDGE (rendered client-side), and singaporeair.com (404). Getting around bot protection was considered and **not** done.

## What the issuer sources showed

| Row | Before | Issuer source says | Now |
|---|---|---|---|
| HSBC TravelOne travel 4 RP/₹100 | "uncapped", **verified** | Service guide caps it per calendar month: "50,000 reward points" twice and "15,000 accelerated reward points" once in the same paragraph. "Accelerated Reward Points i.e 4 RP". Above the cap: "the regular earn rate of 2 reward points" | `monthly_cap_inr: 375000` (15,000 ÷ 4 × ₹100, the stricter reading), `over_cap_earn: base_rate` (issuer). **Flagged** until HSBC resolves the 50k/15k conflict |
| HSBC TravelOne min income | ₹15,00,000 | "INR600,000 per year for salaried" / ₹12L self-employed | ₹6,00,000 |
| HSBC TravelOne milestone | none | "Net Eligible spend of ₹12,00,000 in an anniversary year … additional 10,000 reward points" (primary card only, limited-period offer) | added, verified |
| HSBC RP expiry | market knowledge | "The validity of reward points is 3 years for … TravelOne" | verified |
| HSBC → KrisFlyer / Bonvoy / Accor | min 1,000, 0–2 days, flagged | 1:1 in the partner table. "There is no minimum number of points required to redeem or transfer". "No handling charges for redemptions". "Instantly or within 1 working day" | min 0, 0–1 days, verified |
| HDFC Infinia / DCB SmartBuy cap | ₹1,50,000 **spend** | The cap is on **bonus points**: Infinia 15,000 and DCB Metal 10,000 per calendar month (secondary sources; HDFC unreachable). The old figure was the 1.5L-RP *redemption* ceiling | ₹1,12,500 / ₹75,000 (bonus cap ÷ 20 bonus RP per ₹150 at 5X × ₹150). Still flagged |
| DCB lounge rows | three review sites | hdfc.bank.in: "Unlimited lounge access to 1,300+ lounges in India and abroad for primary and add-on card members" | verified |
| Amex Platinum Travel card | min income was market knowledge | "personal annual income of Rs. 6 Lacs or above" | verified |
| Amex Platinum Charge default 2.50 | flagged; note said "fuel earns nothing" | MR T&C: 1 MR/₹40. Fuel **5 MR/₹100**, capped at 5,000 points a month. No MR on insurance or utilities. 3X overseas | verified; note corrected |
| SBI Cashback card | min income ₹4L (guess), lounge unverified | No income figure published anywhere. The 50-page T&C never mentions lounge access | `min_income_inr: null`, lounge false, verified |
| KrisFlyer Europe / US award rows | "Zone 6 → Europe/USA" | The suitesmile chart prices **Singapore**-origin routes only, so 108,500 and 117,000 are SIN-origin prices | values kept (no India-origin source found), source defect annotated, flagged |
| Axis Atlas / Burgundy → KrisFlyer | flagged | Burgundy T&C PDF confirms KrisFlyer ∈ Group A and the 2L/yr Group A cap. Ratios are secondary-only (1:2 and 5:4 survived the 2026-09-23 reshuffle per cardexpress) | still flagged, notes updated |
| LoungeOne programme | secondary | **Contradicted**: Axis's own Atlas page still cites DreamFolks and says app booking is suspended | still flagged, contradiction recorded |

Still flagged, and why: the HDFC fee-waiver window alignment, the Regalia Gold lounge guest rule, the HDFC Regalia-tier currency, Infinia/DCB SmartBuy (HDFC unreachable), the Burgundy earn table and Travel EDGE cap, the Amex ₹4L milestone's transferability (the MR T&C does not separate bonus points from other points; the product page names only the Platinum Travel Collection), the Platinum Charge joining fee (not stated on the page), the Platinum Travel lounge guest rule, all award-chart rows, and the network lounge programme rows. Flagged rows: **37 → 30** (the DCB international lounge row went back to flagged on review).

## Decisions

1. **Where the issuer contradicts itself, seed the stricter reading and flag the row.** This is the same precedent as the TravelOne fee waiver. The conservative value can only under-promise, and the flag stops it being stated as fact.
2. **A points-denominated cap is converted to a spend cap at the seeded rate.** The schema has only ₹-spend caps. Converting at the seeded (conservative) multiplier is exact for that multiplier, and it never overstates a higher real multiplier. Proof for SmartBuy hotels (real 10X, seeded 5X): below ₹1,12,500 the seeded row earns less than the real 10X. Above it, both land on base rate plus the same 15,000 bonus RP. No new schema column was added.
3. **Zero-earn categories are seed rows with `earn_rate: "0.00"`, not engine code.** The schema already allowed `earn_rate ≥ 0`, and `fuel` and `utilities` are canonical categories. Rows were added only where the issuer's own text excludes the category from *earning*:
   - TravelOne: fuel, utilities
   - SBI Cashback: fuel, utilities
   - Amex Platinum Travel: fuel, utilities
   - Amex Platinum Charge: utilities
   - Magnus Burgundy: fuel

   **Not added:**
   - HDFC: no issuer earn-exclusion text was reached.
   - Atlas: its exclusion list sits in a note, not in quoted issuer text.
   - Burgundy utilities: the Axis exclusion we hold is worded for the *fee-waiver threshold*, which is a different rule.
   - Platinum Charge fuel: it earns *more* (5/₹100) up to a cap, and the issuer doesn't say what happens past that cap. CR-01 forbids a capped row without `over_cap_earn`, so fuel stays on the 2.50 default. That under-states up to ₹2L of fuel a month.

   Insurance, rent, wallets, tax and similar exclusions have no category in our vocabulary. They still fall to `default`, and each card's notes list them.
4. **Unpublished numbers become null, not a guess.** SBI's income bar is `null`, matching Amex Platinum Charge.
5. **The provenance classifier recognises the new issuer domains** (`hdfc.bank.in` and `hsbc.bank.in`; both issuers' old domains now 301 there).

6. **"Nobody earns here" is its own state, not a winner.** This came out of the backend review. Once zero-earn rows existed, Portfolio View named a category leader at **0 miles** by card-name tiebreak, for example TravelOne for fuel beside a Cashback card that has no route. `CategoryLeader` gained `no_card_earns`. When the best routed card earns 0, no leader is named, and the UI says "None of your cards earn here". The UI shows the same note client-side when every row's rate is 0, so it also works with no programme chosen. This is checked before verification, so it is never mislabelled "No verified leader".
   - Zero-row labels are neutral ("Fuel", not "Fuel (earns no points)"). Portfolio can name a category from any card's rule, and an "earns nothing" heading above another card's winning base rate would contradict it.
   - A zero cell renders as a dimmer "0". It has a hover title and a screen-reader note ("excluded by the issuer"), plus its own footnote, so it can't be read as the no-route dash or as a base rate.
   - The no-route footnote is now derived from the cells, so it shows exactly when a dash is on screen. The old leader-field proxy, flagged by frontend-reviewer, could hide it.
7. **The TravelOne ₹12L milestone counts all sales spend.** HSBC's milestone T&C §8 defines eligible transactions as "all types of sales transactions (including … bill payments … insurance payments)". So fuel and utilities count toward the threshold even though they earn no points. The projector's all-spend accumulation therefore matches, and the row stays verified. The offer has no published end date, so re-check it each pass.
8. **Kept flagged on review:** the DCB *international* lounge row. The issuer confirms unlimited access abroad, but naming the Diners Club programme as the provider is an inference.

**Deferred from review:** Best Card still ranks all-zero results (e.g. fuel on TravelOne + Cashback) by tiebreak. The result shows 0 points honestly, but the framing reads as a pick. It needs a "no card earns on this" state on `BestCardResult` and the page, mirroring decision 6.

## Consequences

- **Engine outputs move.** Infinia travel blends to 10.8225 pts/₹100 at ₹2L (was 13.32). DCB to 8.3250. TravelOne plans that reach ₹12L/year gain 10,000 RP. The Atlas-vs-TravelOne runner-up delta goes from 24,200 to 34,200: removing the new milestone gives back exactly 24,200, which was checked. Every changed golden was recomputed by hand, with the working in its docstring.
- **Portfolio View names TravelOne as a leader** now that its route is verified, and it gains Fuel and Utilities rows when a wallet card has them.
- **Live DB is stale until reseeded.** As before, the seeds must be reloaded, after migrations 0009 and 0010.
- Suite 727 → 734:
  - zero-earn Best Card test
  - verified-leader endpoint test
  - TravelOne milestone parametrize case
  - two `no_card_earns` portfolio tests
  - TravelOne cap-boundary test

  mypy strict, ruff check, tsc and eslint are clean.
- **Small frontend change:** `no_card_earns` in `lib/api.ts` and the Portfolio category table. Reviewed by frontend-reviewer.

## Sources (issuer)

- HSBC: https://www.hsbc.bank.in/credit-cards/products/travelone/ · /rewards/ · https://www.hsbc.bank.in/credit-cards/how-to-redeem-credit-card-reward-points/ · service guide https://www.hsbc.co.in/content/dam/hsbc/in/documents/aw-travel-one-sevice-guide-11-12-2025.pdf · milestone T&C https://www.hsbc.bank.in/content/dam/hsbc/in/documents/milestone-benefits-2-tnc.pdf
- HDFC: https://www.hdfc.bank.in/credit-cards/diners-club-black-metal-edition-credit-card · https://www.hdfc.bank.in/credit-cards/regalia-gold-credit-card
- Amex: https://www.americanexpress.com/in/credit-cards/platinum-travel-credit-card/ · https://www.americanexpress.com/in/charge-cards/platinum-card/ · MR T&C https://www.americanexpress.com/content/dam/amex/in/benefits/membership-rewards-terms.pdf
- SBI: https://www.sbicard.com/sbi-card-en/assets/docs/pdf/ekit-tncs/cashback-tnc-ekit.pdf
- Axis: https://www.axis.bank.in/docs/default-source/default-document-library/credit-cards/magnus-for-burgundy-terms-and-conditions.pdf · https://www.axis.bank.in/cards/credit-card/axis-bank-atlas-credit-card/privileges

Secondary sources used for still-flagged rows are cited inline in each YAML row.
