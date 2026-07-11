# Decision Log — Post-Login Card Catalog: Real Card Art

**Date:** 2026-07-11
**Area:** frontend

## Context

User asked why "SBI" shows up in the post-login supported-card catalog
(`/cards`) and asked for the same card images the landing page uses.

Two separate things were conflated in the question:

1. **SBI Cashback is a deliberate, correct catalog entry** — it's seeded in
   `backend/seeds/catalog/cards.yaml` as an intentional negative case: a
   cashback card with no transferable reward currency, so the Valuation
   Engine can be proven to correctly emit zero KrisFlyer opportunities for
   it (`app/valuation/opportunities.py`). It belongs in the catalog; it is
   not a seeding mistake.
2. **The `/cards` page renders every card with the same generic `CreditCard`
   lucide icon** — no card, SBI or otherwise, had real art. That's the
   actual gap the user was reacting to: SBI "looks out of place" only
   because nothing on that page looks like a real card, unlike the landing
   page's `SupportedCards` section, which shows real card art for its
   (curated, 5-card) example wallet via `next/image` from
   `frontend/public/cards/`.

`CardSummary` (the `GET /catalog/cards` response type) carries no
image/slug field, so there was no existing hook to attach art to.

## Decisions

1. **`frontend/src/app/(app)/cards/page.tsx`**: added a `CARD_IMAGES` lookup
   keyed by `"${bank}|${card_name}"` (the same real filenames the landing
   page's hardcoded `CARDS` array already uses), and updated `CardTile` to
   render the mapped image via `next/image` when present, falling back to
   the original `CreditCard` icon otherwise. This is intentionally the same
   graceful-degradation shape as the landing page's icon tiles, not a new
   pattern.
2. **Did not source new card art.** Only 5 of the catalog's 9 cards have an
   image asset in `frontend/public/cards/` (Infinia, Diners Club Black,
   Regalia Gold, HSBC TravelOne, Amex Platinum Travel). Axis Atlas, Axis
   Magnus for Burgundy, Amex Platinum Charge, and SBI Cashback still render
   the fallback icon. Generating or fabricating bank card art isn't
   something to do speculatively — real card art should come from the same
   verified-source discipline the seed data itself requires.
3. **Did not remove SBI Cashback from the catalog or hide it from `/cards`.**
   It's correct, tested, documented behavior — hiding it would undermine the
   "engine correctly excludes non-transferable cards" guarantee it exists to
   demonstrate.

tsc --noEmit and eslint clean on the changed file. Verified `/cards` compiles
and serves 200 against the live dev server.

## Not done (deferred)

- **Sourcing card art for Atlas, Magnus for Burgundy, Platinum Charge, and
  SBI Cashback** — needs real, rights-clear card images added to
  `frontend/public/cards/` the same way the existing five were sourced.
  Left as a follow-up; the fallback icon is a correct, non-broken interim
  state, not a bug.
