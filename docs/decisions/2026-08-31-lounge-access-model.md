# Decision Log — Lounge Access Intelligence: the model

**Date:** 2026-08-31
**Area:** Reward Knowledge Engine / schema / seed data
**Roadmap:** `docs/prd/product-roadmap-v1.md` → Phase 1, Lounge Access Intelligence (card side)
**Scope of this entry:** the data model, migration and validation rules, plus the first seeded rows. The read surface and UI are the next slice; visit logging is the one after.

## Context

`has_lounge_access` — a single boolean on the card — was the entire lounge model. It carries no programme, no counts, no conditions, and it is the most-confused benefit in the Indian premium-card market: access depends on which network the card rides, domestic vs international, per-quarter allowances, spend gates, guest policy, and whether the holder has enrolled at all.

## Decisions

1. **Domestic and international are separate rows, never one combined count.** They almost never match on an Indian card — Regalia Gold gives 3 domestic visits a quarter *behind a spend gate* and 6 international a year *with no gate*. A single number could only ever be wrong.

2. **`reset_anchor` is a required, explicitly-seeded field with no default** (the user's decision, 2026-08-26). Issuers reset variously on the calendar quarter, the card anniversary and the statement cycle. A silent calendar-quarter assumption is the likeliest source of a wrong visit count, and a wrong count is worse than no count — it sends someone to a lounge desk to be turned away. **Enforced twice**: a DB CHECK constraint and validation rule LA-04.

3. **"Allowance", never "cap".** `RewardCategoryRule` already uses *cap* for a ₹-spend ceiling on accelerated earning. A lounge limit counts visits. Same English word, unrelated concepts — so the lounge fields are `visits_per_period` / `guest_visits_per_period`, and `AllowancePeriod` is its own enum rather than a reuse of `MilestonePeriod` (which needs `ONE_TIME` and lacks `STATEMENT_CYCLE`; sharing one enum would let nonsense combinations typecheck).

4. **NULL means unlimited; 0 means none.** Both are real answers and they are not interchangeable. Infinia uses both in the same card: unlimited cardholder access, and *zero* complimentary guest visits (guests pay USD 27 + GST).

5. **Tiered entitlements are one row per tier, distinguished by `spend_gate_inr`.** The uniqueness index is `(card, programme, scope, COALESCE(spend_gate_inr, -1))` so an Atlas-style Silver/Gold/Platinum ladder is expressible, while a true duplicate — which would double-count somebody's entitlement — is rejected (LA-05).

6. **`cards.has_lounge_access` STAYS for now**, against the roadmap's "replaces the boolean" wording. Coverage is partial (2 of 9 cards), and dropping the boolean today would convert *"we have not researched this card yet"* into the false claim *"this card has no lounge access"* — the exact trust failure the feature exists to prevent. It becomes the coarse fallback, and a later migration drops it once coverage is complete.

7. **Provenance stays in the YAML seeds, not the DB.** The first draft of the migration had `source` / `verified_on` / `needs_verification` columns; that contradicts the established pattern (`repositories/catalog_admin.py`: "the seeds are the audited artifact"). Removed. Lounge rows carry the heaviest provenance in the repo and it belongs where a human reviews it.

8. **Only two cards were seeded, deliberately.** See below — this is the substantive decision of the session.

## The coverage decision

A research pass found the published data too conflicting to seed honestly:

- **Axis Atlas** — three mutually exclusive figures across sources (8/12/18 by tier; a flat 18+12; Platinum as 12+6), plus a reported mid-2026 vendor switch (DreamFolks → Priority Pass international, LoungeOne domestic).
- **HSBC TravelOne** — searches return HSBC's **UK and Singapore** products, not the Indian card.
- **HDFC Diners Club Black Metal** — the mid-2026 HDFC revision is documented for Diners Club Privilege and BizPower; whether it touched Diners Club Black is unconfirmed. It shares Infinia's reward tier, which makes assuming Infinia's terms tempting and wrong.

Seeded instead:

- **Infinia** — verified from HDFC's own T&C PDF (effective 2026-07-02): unlimited domestic via the issuer-direct programme (₹2 per visit for Visa cardholders), unlimited international via Priority Pass for holders presenting their own Priority Pass card, zero complimentary guest visits.
- **Regalia Gold** — listed, `needs_verification: true`, from a specific secondary source: 3 domestic visits per calendar quarter unlocked by ₹60,000 spend in the *preceding* quarter, and 6 international a year via Priority Pass with no gate. **This is the case most cardholders get wrong** — the visits are not granted, they are earned by last quarter's spend.

The remaining seven are **not covered**, which the tiered-coverage rule makes an acceptable answer. `docs/research/lounge-access-research-brief-v1.md` records exactly what is needed and which conflicts to resolve first.

> The judgement here: a lounge feature covering two cards honestly is worth more than one covering nine cards where seven are guesses. Guessed lounge conditions are the single most expensive kind of wrong this product can be, because the user finds out at the airport.

## What shipped

- `domain/enums.py` — `LoungeScope`, `AllowancePeriod`, `ResetAnchor`
- `domain/catalog.py` — `LoungeProgram`, `LoungeAccess`, both on `CatalogSnapshot` (defaulting to empty, so partial coverage is the normal case)
- `alembic/versions/0007_lounge_access.py` — `lounge_programs`, `card_lounge_access`, with CHECK constraints mirroring LA-03/LA-04, the tier-aware unique index, an `updated_at` trigger, and RLS read policies matching migration 0003. **Applied to the live database.**
- `knowledge/validation.py` — LA-01…LA-05
- `knowledge/seed_catalog.py`, `knowledge/store.py`, `repositories/catalog_admin.py` — load, read and sync paths
- `seeds/catalog/lounge_programs.yaml` (6 programmes) and per-card `lounge_access` blocks
- `tests/unit/knowledge/test_lounge_validation.py` (10 tests). Suite **493 passed**, mypy strict + ruff clean.

**Verified against the live DB:** migration applied (alembic at 0007), seeds synced (6 programmes, 4 access rows), and the DB snapshot's content version is byte-identical to the seed snapshot's (`cat-bc9b17e80925`) — the D-2 guarantee holding across a schema change.

## Next

1. **Read surface + UI** — "which of my cards gets me in, on what condition, and what must I activate", in Portfolio View. Must state coverage honestly: detailed conditions where we have them, the coarse boolean where we do not, "not covered yet" where we have neither.
2. **Coverage** — work the research brief.
3. **Visit logging** — needs per-user persistence; design it as *one pattern* with Phase 2 spend logging rather than two things to remember.
4. **Drop `has_lounge_access`** once coverage is complete.


---

# Slice 2 — read surface, UI, and coverage 2 → 4 (same day)

## Coverage

Two more cards reached the *listed* tier on further research:

- **HDFC Diners Club Black Metal** — unlimited domestic and unlimited international (Diners Club network), three independent secondary sources agreeing.
- **Amex Platinum Travel** — from Amex India's own pages. Amex states **two** limits, 8 a year *and* 2 a quarter. They are arithmetically consistent, but **the quarterly limit is what binds on any real trip** — you cannot spend all eight in one quarter — so that is what is seeded, with the annual total in the user-facing conditions. Seeding "8 per year" would over-promise a traveller planning a single trip.
  - Its international row is seeded as **zero complimentary visits**: Priority Pass *membership* is free, which is not the same as free visits, and the per-visit charge is unconfirmed. Conservative reading, flagged, and the note says to raise it if visits turn out to be included — never to lower a promise already shown.

Atlas, Magnus, TravelOne and Platinum Charge remain uncovered; their conflicts are unchanged and recorded in the brief.

## The read surface

`PortfolioCard` gains `lounge_coverage` — a **tri-state**, and it is the whole point:

- `detailed` — real conditions held
- `not_detailed` — the card **has** lounge access, we have not researched it
- `none` — the card has no lounge access

Collapsing the middle state into `none` would be a false claim about a benefit the cardholder is paying for. It is the same failure class as a stale condition, just quieter, and with partial coverage it would have hit five of nine cards.

Also on the payload: `is_unlimited` is explicit rather than leaving callers to interpret a null, because on this surface `null` means unlimited and `0` means none — opposite answers. A UI treating the null as "no data" would tell an Infinia holder they have no lounge access.

## The UI

A dedicated **"Lounge access"** section in Portfolio View, per card, answering the in-the-moment question:

- Domestic and international stated separately, domestic first
- **The spend gate gets the loudest treatment on the page** — a gold callout reading *"Only if you spent ₹60,000 or more in the previous quarter — these visits are earned, not automatic."* This is the condition most cardholders get wrong and the single most useful thing the feature says.
- "You must activate this first — it doesn't exist until you do" wherever enrollment is required
- Guests, reset anchor, and the issuer's own conditions text
- Uncovered cards render *"conditions not covered yet"* with an explicit "we'd rather say nothing than guess the number", plus a wallet-level count
- Cards with no lounge access are simply absent from the section

**One defect caught in the live pass:** the seeded `conditions` strings were leaking reviewer-facing language into user copy ("Seeded conservatively as zero…", "this is the row to re-check first"). `conditions` is user-facing; reviewer notes now live in YAML comments, where the seed reviewer sees them and the cardholder does not.

Verified live at 1440×900 and 390×844 against the real database: all four states render correctly, SBI Cashback is correctly absent, no page overflow, no console errors. Suite **500 passed**; DB and seed snapshots byte-identical at `cat-c25780ce44db`.
