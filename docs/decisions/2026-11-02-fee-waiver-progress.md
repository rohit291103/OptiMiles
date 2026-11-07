# Decision Log — Annual-fee waiver progress (from an optional renewal month)

**Date:** 2026-11-02
**Area:** Knowledge Engine (catalog) / Simulation Engine (`observed.py`) / schema / API / `/activity`
**Builds on:** `2026-09-02-activity-log-unified.md` (the honesty model) and `2026-11-02-portfolio-progress-composition.md` (Listed-tier labelling)
**User decision being implemented:** track fee-waiver progress **only** when the user has given an optional per-card **renewal month**. Otherwise say "tell us your renewal month to track this" and never assume a window.

## Context

Portfolio View had deferred the "fee calendar" because it "needs a card-open date we don't collect". Fee waivers are where that gap costs real money: a ₹2,500–₹30,000 fee depends on whether last year's spend crossed a threshold, and the activity log already holds the spend. What was missing was (a) the waiver terms in the catalog, and (b) when the user's card year starts.

## Decisions

1. **Collect a renewal MONTH, not a date.** Every published waiver window ends at the renewal. These are the issuer's 12 months before it (HDFC), the card anniversary year (HSBC, Axis), and the 365 days before the fee billing date (SBI). Without the day, each edge is uncertain by up to a month. So we count only the part of the window that is certain **whatever the day**: the **11 whole months between renewal months**, `[1st of the month after last year's renewal month, 1st of this renewal month)`. That window is a subset of the real window for both the 12-month and the 365-day shapes. `test_renewal_window.py` proves this for every as-of date from 2024 to 2028, every renewal month, and every possible renewal day. Counting a subset keeps the log a lower bound. Adding the day would only gain one month of countable spend, and most users would have to look it up. The rule is less personal data with the same honesty. The cost is stated in the UI: spend in the renewal month itself is not counted.

2. **Which renewal is the target.** The target is the next renewal. During the renewal month itself, the target is this month's renewal: its window has fully elapsed, and it answers "did I qualify for the fee posting now?". The target moves to the next renewal once that month ends.

3. **Waivers are their own catalog row (`FeeWaiver`, table `card_fee_waivers`), not columns on `Card`.** A waiver is sourced and verified separately from the card's fee and earn rate. `load_unverified_ids` flags never inherit, so the waiver needs its own id (`seed_id("fee_waiver", card_slug)`). One row per card at most (FW-02 plus a partial unique index).

4. **Three answers, modelled as three.**
   - `kind: spend_based` comes with its terms.
   - `kind: none` is a **sourced** "the issuer lists no waiver".
   - **No row** means "not covered yet".

   `none` is never a default. The CHECK constraints and FW-03 make a row carry its terms only when it is spend-based. On the wire this becomes `FeeWaiverCoverage`: `tracked`, `needs_renewal_month`, `no_waiver` or `not_covered`. The UI renders `not_covered` as "We have not checked this card's annual-fee waiver yet. That is not the same as saying it has none."

5. **The comparison type is a field (`threshold_comparison: at_least | more_than`), because the sources differ.** HDFC says "Spend Rs. X", SBI says "Rs.2 Lakh or more", and Axis says "Waived on eligible spends of INR 30,00,000". All three are met **at** the figure. HSBC says "exceeds ₹800,000", which is **strict**. Logged amounts are whole rupees, so a strict threshold needs `threshold + 1`. As a result, `remaining_inr_at_most` is ₹1 at exactly ₹8,00,000 and the status is `NOT_PROVEN`. Invariant: `REACHED` holds exactly when `remaining_inr_at_most == 0`.

6. **The window shape records which fee is waived, not just the period.**
   - `preceding_card_year`: the waiver applies to the fee at the end of the window (HDFC, Magnus).
   - `current_card_year`: the fee charged at the start of the window is reversed (HSBC).
   - `days_365_before_fee_date`: SBI.

   The counting window is the same for all three. The copy differs: for HSBC the UI says "the card year ending at your Jun 2027 renewal", not "your Jun 2027 renewal".

7. **Issuer exclusions our vocabulary can express are applied structurally.** For Magnus Burgundy, Axis excludes rent, wallet, utilities, government, EMI, cash, insurance, gold and fuel. `utilities` and `fuel` are categories we log, so `excluded_categories: [utilities, fuel]` removes them from the count; a golden test pins this. The test case logs ₹32L in total, which would have printed a false "waived", against ₹25L of eligible spend. The exclusions we cannot express go in `unmodelled_exclusions` (see 11). **Correction (fix round):** an earlier version of this entry said "excluding more spend can only lower the count, so the lower bound holds". That is true only for **modelled** exclusions. Logged spend is a lower bound on what the user *spent*, not on what the issuer *counts*. Rent logged under "other" on a Magnus card inflates the count and can produce a false REACHED. Decision 11 handles that case.

8. **A renewal benefit is not a waiver.** On Amex Platinum, spending ₹20L earns vouchers "on … payment of renewal fee". That makes the card `kind: none`, and `conditions` explains the voucher benefit.

9. **Renewal months are user data in `card_renewal_months (user_id, card_id, renewal_month SMALLINT 1–12)`.** The table has PK `(user, card)`, owner-only RLS and an `updated_at` trigger. `card_id` references the catalog, with ON DELETE RESTRICT (same posture as 0008). It lives in migration **0010**, `down_revision = "0009"`, together with the catalog table. A month can be set for any catalog card, including uncovered ones, because it is a fact about the user's card.

10. **No sixth module.** Window arithmetic is `periods.renewal_window` / `month_label`. The calculator lives in `observed.observe()`, which gains `renewal_months=` and `unverified_ids=` keyword arguments. Persistence is in `repositories/activity.py`. `needs_verification` is `bool | None`, and `None` means "not assessed", the same convention as `PartnerReach`. The API always passes the tier.

11. **Exclusions we cannot log are named, and they qualify the answer (fix round).** `FeeWaiver.unmodelled_exclusions` lists, in the user's words, what the issuer excludes that our categories cannot separate. It is also used when the issuer's "eligible spend" is not defined anywhere we could reach, which is not the same as "nothing is excluded". `has_unmodelled_exclusions` is derived from it (a pydantic computed field, not a column). When it is set, `FeeWaiverCount.subject_to_exclusions` is true and `note` carries the caveat:
    - REACHED reads "Reached on your log — subject to the issuer's exclusions listed: …";
    - NOT_PROVEN warns "if any of your logged spend is one of those, you need more than shown", because "at most" also holds only for spend the issuer counts.

    The summary `caveat` gains a sentence saying waiver counts may include spend the issuer excludes. Status stays REACHED / NOT_PROVEN, and the UI never prints "your log alone proves it" while the flag is set.

12. **HSBC (`current_card_year`) during the renewal month: kept as is, now explained.** HSBC reverses the fee charged at the **start** of a card year when spend **in** that year exceeds ₹8L. In the renewal month, the year that has just closed is the one being settled: its reversal decides the fee charged a year earlier. The year now beginning has no spend in it yet, and it becomes the target once the month ends. This was judged correct.

    What was wrong was the copy, which named "your Nov 2026 renewal". `FeeWaiverCount.decides_fee_label` now names the fee the window decides:
    - the end-of-window renewal for most issuers;
    - for `current_card_year`, the fee charged at the start of the window, one year earlier.

    The UI reads "the waiver for your Nov 2025 fee (the card year ending at your Nov 2026 renewal)". The HSBC `conditions` says the same thing. A golden test covers both 2 Nov 2026 (window Dec 2025–Oct 2026, decides Nov 2025, REACHED on ₹9L) and 1 Dec 2026 (window Dec 2026–Oct 2027, decides Nov 2026, at most ₹8,00,001).

13. **0010's "none is bare" CHECK now covers every term column**: `threshold_inr`, `threshold_comparison` and `window_kind` must be NULL, both waive flags false, and both exclusion arrays empty. It now mirrors FW-03 exactly. `unmodelled_exclusions TEXT[] NOT NULL` has no default.

## Seeded values (re-opened at the issuer on 2026-11-02; quotes on each YAML row)

| Card | Kind | Threshold | Comparison | Window | Fees | Excluded (structural) | Unmodelled exclusions | Tier |
|---|---|---|---|---|---|---|---|---|
| HDFC Infinia Metal | spend_based | ₹10,00,000 | at_least | preceding_card_year | renewal | — | Cash on Call, balance transfers, cash withdrawals | **unverified** |
| HDFC Diners Club Black Metal | spend_based | ₹8,00,000 | at_least | preceding_card_year | renewal | — | same | **unverified** |
| HDFC Regalia Gold | spend_based | ₹4,00,000 | at_least | preceding_card_year | renewal | — | same | **unverified** |
| HSBC TravelOne | spend_based | ₹8,00,000 | **more_than** | current_card_year | renewal **and first year** | — | "eligible spend" undefined | **unverified** |
| Axis Magnus for Burgundy | spend_based | ₹30,00,000 | at_least | preceding_card_year | renewal | utilities, fuel | rent, wallet loads, government payments, EMI conversions, cash withdrawals, insurance, gold, reversals/fees | verified |
| SBI Cashback | spend_based | ₹2,00,000 | at_least | days_365_before_fee_date | renewal only | — | "eligible spends" undefined | **unverified** |
| Axis Atlas | none | — | — | — | — | — | — | verified |
| Amex Platinum Charge | none | — | — | — | — | — | — | verified |
| Amex Platinum Travel | *(no row: not covered)* | | | | | | | |

Sources:
- **HDFC:** fee-waiver page ("Pricing MID for Oct 2026"); MITC (updated 29 Oct 2026), fee table plus the footnote "* Exclude transactions - Cash on Call, Balance Transfer, Cash Withdrawal"; the Regalia Gold fees page ("within 12 billing cycles of your anniversary year").
- **HSBC:** TravelOne service guide ("exceeds ₹800,000") and the KFS ("₹800,000 or more").
- **Axis:** MITC, plus the SoSC "Annual Fee Waiver" row, which shows "-" for Atlas. The MITC's "5,000 5,000 Nil" for Atlas is the add-on fee column, not a waiver statement.
- **SBI:** MITC, plus Cashback T&C §13.2.
- **Amex:** issuer card pages.

**Tiers, re-assessed in the fix round:**
- **HDFC ×3 are flagged.** The thresholds and exclusions are sourced, but HDFC states the window as "12 billing cycles of your anniversary year". How those cycles line up with the renewal is not stated, so the month-only subset proof (decision 1) is not established for HDFC.
- **HSBC is flagged.** Its two documents disagree on strict vs. inclusive. The stricter reading is seeded, because it can only make REACHED harder to prove. "Eligible spend" is also undefined.
- **SBI is flagged.** "Eligible spends" is not defined in the MITC or the T&C. Third-party lists (fuel, rent, wallet, EMI) were deliberately **not** modelled, because they are not issuer sources.

## Not verified / open

- **Eligible-spend definitions for HSBC and SBI remain unknown.** They are carried as unmodelled exclusions, so every REACHED on those cards is "subject to exclusions", and the rows are flagged.
- **HDFC billing-cycle alignment** (see Tiers above).
- **SBI's 365-day clause sits in the T&C's card-upgrade section**, while the MITC says "preceding year". Both shapes give the same month-only window, so the count is unaffected.
- **Renewal month vs. fee-statement month.** The UI asks for "the month the annual fee is charged". If an issuer's anniversary month and the month the fee is billed differ, and the user enters the later one, the window could include one month past the true renewal. This is documented but not guarded.
- **The HSBC rule counts add-on card spend.** The UI tells users to log add-on spend against the primary card.
- **Not applied to the live DB.** Migration 0010 exists as a file only, and the seeds have not been loaded.

## What shipped

**Backend**
- `domain/enums.py`: `FeeWaiverKind`, `ThresholdComparison`, `FeeWaiverWindow`
- `domain/catalog.py`: `FeeWaiver`, plus `CatalogSnapshot.fee_waivers`
- `domain/activity.py`: `CardRenewalMonth`, `FeeWaiverCoverage`, `FeeWaiverCount`, `FeeWaiverProgress`, plus `ObservedActivity.fee_waivers`
- `knowledge/seed_catalog.py`: hydration, the provenance index, and `PROVENANCE_COLLECTIONS`
- `knowledge/store.py`, `repositories/catalog_admin.py`: the DB read and sync paths
- `knowledge/validation.py`: FW-01 to FW-03
- `simulation/periods.py`: `renewal_window`, `month_label`
- `simulation/observed.py`: one fee-waiver row per wallet card
- `repositories/activity.py`: set, list, fetch and clear for renewal months
- `api/activity.py`: `GET /v1/activity/renewal-months`, `PUT` and `DELETE /v1/activity/renewal-months/{card_id}`; the summary now carries `fee_waivers`
- `alembic/versions/0010_fee_waivers_renewal_months.py`

**Frontend**
- `lib/api.ts`: types, plus `setRenewalMonth` / `clearRenewalMonth`
- `components/app/activity-log.tsx`: the "Annual-fee waivers" section, with a per-card renewal-month select, lower-bound copy and an Unverified pill
- Fix round changes to `activity-log.tsx`:
  - The month pick is now optimistic. It is shown and the select stays disabled until the next summary load completes, success or failure; this is tracked by a `loads` counter on the parent. A failed save rolls back, and overlapping saves are blocked.
  - The spinner is `role="status"` with an sr-only "Saving…".
  - `aria-describedby` links the select to its hint and error.
  - The select is at least 44px tall at every breakpoint (`h-12 sm:h-11`).
  - The whole-months note appears once per section.
  - A `more_than` threshold shows "(spend must exceed ₹X)".
  - The unmodelled exclusions are listed on each card, and the server `note` is rendered.
- `/activity` page copy

**Tests:** 86 new tests (after the fix round):
- 10 window tests, one of them exhaustive
- 39 catalog and validation tests
- 20 calculator goldens, hand-computed from the real seeds
- 7 repository tests
- 10 endpoint tests

The backend suite has **727 passed**, with mypy strict and ruff clean; tsc, eslint and `next build` are also clean.

A headless Chromium run against the production build with a mocked API passed **53/53** checks, at 390×844 and 1440×900. It covered:
- all four coverage states;
- strict-threshold copy;
- the "subject to exclusions" REACHED;
- the select holding its optimistic value and staying disabled while the refetch was held for 2.5 s;
- the sr-only "Saving…";
- rollback on a mocked 500;
- `aria-describedby` on the hint and the error;
- selects at least 44px tall at both widths;
- the whole-months note appearing exactly once.

It found no overflow, no text under 12px and no tap targets under 44px. The only console error was the deliberate 500.
