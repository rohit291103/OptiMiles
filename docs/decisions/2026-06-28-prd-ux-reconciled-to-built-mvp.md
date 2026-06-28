# Decision Log — PRD & UX reconciled to the built MVP

**Date:** 2026-06-28
**Area:** product

## Context

After the landing page reached its current state (product-first edge-to-edge
redesign, static 5-card wallet, live-mock Goal Simulator), the user asked
whether what we built still matches what the PRD and UX docs envisioned — i.e.
"does `mvp_scope` match what we've actually built." A read-through found the
core vision intact ("Google Maps for Indian credit card rewards," goal-driven,
explainability-first, dark/premium) but several concrete details in
`docs/prd/mvp_scope_1.md` and `docs/ux/landing-page-v1.md` had gone stale
relative to the built product. This pass reconciles the docs to reality, with
two scope calls confirmed by the user.

## Decisions

1. **Card universe trimmed to 8 in the PRD.** The PRD's "15–20 card" universe
   (which included Amex MRCC, Amex Gold Charge, Axis Select, IDFC First Wealth,
   Yes Marquee, AU Zenith+, Air India SBI, Vistara IDFC/SBI) was replaced with
   the committed **8-card MVP set** — HDFC Infinia, HDFC Diners Black, HDFC
   Regalia Gold, HSBC TravelOne, Axis Atlas, Axis Magnus, Amex Platinum Travel,
   SBI Cashback — matching root `CLAUDE.md` → "Initial Supported Cards." The
   broader list is preserved as an explicit **"Deferred (post-MVP candidates)"**
   note so the ecosystem research isn't lost. Rationale: keep reward modeling
   and manual validation tractable; "narrow and deep" over breadth-too-early.

2. **All three goal categories kept in MVP scope, with flight-only the surfaced
   one.** Flight Redemption, Hotel Stay, and Lounge/Lifestyle goals all remain
   in MVP scope per the user's call. The PRD now marks **Flight Redemption as
   the category currently surfaced in the product** (the live simulator) and
   Hotel/Lounge as planned-but-not-yet-built (in scope and schema, not yet in
   the UI). This avoids narrowing the product's stated ambition while being
   honest about what's actually demonstrable today.

3. **Canonical simulator routes fixed to the built product.** The simulator
   wires India→Singapore, →London, →New York. An earlier PRD draft listed Dubai
   instead of New York. The **built product is now the source of truth**: PRD
   route list and the UX doc's "known constraints" both updated to Singapore /
   London / New York; Dubai recorded as a candidate route, not yet wired.

4. **Supported-cards UX description corrected.** `docs/ux/landing-page-v1.md`
   still described a "roadmap roster by tier" with Active vs **Coming soon**
   badges and (in earlier drafts) an autoplay/drag carousel. Reality is a
   **static responsive grid of 5 all-Active cards** (`object-contain`,
   `1.586:1`, labels below), framed as "the cards you already carry" — a
   deliberate illustrative subset of the 8-card MVP, not a tiered roadmap. The
   UX doc was rewritten to match. (See
   `2026-06-21-supported-cards-photos-and-scope.md` for the original UI change.)

## Not done (deferred)

- No code changes — this pass is documentation-only; the product was already in
  its intended state.
- Did not expand Hotel/Lounge goals in the UI; they stay in-scope-but-unsurfaced
  per decision 2.
- Did not add Axis Atlas / Axis Magnus / SBI Cashback to the visual wallet; the
  5-card UI subset stands (decision documented in
  `2026-06-21-supported-cards-photos-and-scope.md`).
- Post-MVP candidate cards (decision 1) are parked, not modeled.
