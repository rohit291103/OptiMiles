# Decision Log — Post-MVP Expansion, Feature Triage, and Mobile Strategy

**Date:** 2026-08-26
**Area:** product / scope / platform

## Context

The MVP is built and was demoed to users. Two signals arrived together.

**User testing.** Testers liked how easily the product produced a clear answer to a
travel goal — the goal engine lands. The recurring objection was form factor:
*"it would be most suitable in an app."* This is validation of the value and a
rejection of the surface, not the reverse.

**Competitive.** A competitor, **PointsFly**, launched 2026-08-16 positioning itself
as "India's first AI-native platform to get the BEST value from your credit cards."
Its announced surface: unified portfolio view (earn rates, transfer partners, offers),
automatic transaction tracking with instant points alerts, flight/hotel award search
with real rupee-per-point valuation, an AI consultant chat ("AIRA"), a best-card-for-
this-spend feature, geofenced store alerts, and a **"Dream Destination tracker"**
marketed as patent pending. Headline claim: "can save you ₹75,000+ a year."

Two things follow. First, **goal orientation is not the uncontested differentiator we
assumed** — a competitor is marketing a goal tracker directly, so "we are the goal-based
one" is a depth argument, not a category argument. Second, the user's own read was
correct on the business point: a product that only answers a once-per-8-months question
has no daily surface, no habit, and structurally no reason for a user to return during
the accumulation period they are supposedly being guided through.

## Decisions

1. **Goals remain primary; a daily-use layer is added beneath them.** The MVP sells the
   payoff without the habit that earns it. The ordering that fixes this is
   **Best Card (daily) → spend logging (weekly) → goal plan (the payoff that retains)**.
   Every added feature must eventually route a user toward a goal; anything that cannot
   is a rejection candidate.

2. **Our moat is restated explicitly:** a deterministic, explainable optimization engine —
   the ability to show and defend the exact math from spend to route to transfer to
   redemption. Not the existence of a goal tracker. This is invisible in a feature list,
   which is precisely why the daily surface is needed to get users close enough to see it.

3. **Feature triage against the competitive surface** (full rationale in the roadmap):
   - **Build** — Best Card for this Spend; Portfolio View; catalog-grounded Q&A. All three
     reuse engines already written and fixture-tested.
   - **Build cheaply, not their version** — spend tracking as **statement/CSV upload +
     manual log** rather than SMS/transaction parsing (their version needs Android SMS
     permissions, which iOS cannot do at all, or Account Aggregator integration — that is
     a mobile-infrastructure company). Award value as a **sweet-spot table + points-worth
     calculator** rather than live award search (seat-level availability scraping is the
     hardest data problem in the category and breaks constantly).
   - **Reject** — geofenced store alerts (native background location, real battery/privacy
     cost, weak actual value — nobody changes card at the mall entrance because of a push);
     automatic bank/AA integration (unchanged from MVP scope).

4. **Catalog-grounded Q&A is in scope, and this is not a reversal of the chatbot exclusion.**
   `mvp-scope-v2.md` excludes "conversational copilots" and root `CLAUDE.md` excludes
   "generic chatbot experiences." Those exclusions target **ungrounded chat** — an LLM
   improvising reward facts. A Q&A surface that retrieves from the verified catalog and
   renders deterministic numbers is the opposite failure mode and is our clearest
   demonstration of the moat. Hard constraint: **every factual claim must trace to a
   catalog row or engine output; no number is ever LLM-generated; "the catalog does not
   cover this" is a first-class answer.** This is the existing Stage 1 / Stage 10 boundary
   applied to a new surface, not a new architectural allowance.

5. **Web features first; app conversion later.** Phases 1–3 of the roadmap are entirely
   web, and **Phase 4 (mobile) does not begin until they have landed**. Wrapping a surface
   that is not yet worth opening daily solves nothing — the app is a distribution decision,
   and there must first be something worth distributing. The mobile-first responsive pass
   is web usability work (most users will reach these features on a phone browser regardless),
   not the start of the app project.

6. **Mobile: web-first, then wrap — one codebase throughout.** Sequence is
   mobile-first web → PWA (manifest, service worker, web push) → **iOS via Capacitor** →
   **Android via Trusted Web Activity**. A React Native or Flutter rewrite is explicitly
   rejected: months of work, permanently forks the frontend, and buys nothing the engines
   need. "Should be an app" from testers is read as *home screen icon, notifications,
   opens instantly* — not *rewrite it natively*.

7. **iOS first, deliberately, on ICP grounds — against raw market share.** India is roughly
   95% Android. We are choosing iOS anyway because our primary user (₹50,000–₹2,00,000/month,
   premium travel cards — Infinia, Amex Platinum, Magnus) skews heavily to iPhone. Shipping
   to the platform our actual paying users hold beats shipping to the platform the median
   Indian holds. **This is recorded explicitly so it is not later mistaken for an oversight** —
   anyone reading "we chose the 5% platform first" without the ICP rationale will read it
   as a mistake.

8. **The iOS-first choice front-loads real costs, accepted knowingly:**
   - **App Store Guideline 4.2 (Minimum Functionality)** rejects repackaged websites. A
     Capacitor shell with no native capability will be bounced; Android's TWA path has no
     equivalent barrier. We take the hard approval problem first.
   - **iOS PWA install is a dead end** — no install prompt, manual Share → Add to Home
     Screen, web push only after that. On iOS the PWA does not substitute for the App
     Store; on Android it is a one-tap banner.
   - **iOS cannot read SMS**, so automatic transaction tracking is permanently unavailable
     there. Decision 3's choice of upload-and-manual-log is what keeps this from mattering.

9. **Native capabilities are chosen in Phase 1, not at submission.** To clear Guideline 4.2
   the app must do something a website cannot. Pick two or three from: push notifications
   for milestone/cap alerts (strongest — it is the Phase 2 feature users would install for),
   biometric lock on the portfolio, a goal-progress home screen widget, offline card list.
   The web app is architected so these bolt on cleanly.

10. **Lounge Access Intelligence is added to Phase 1** (user request, same session). This is
    **not scope creep**: `mvp-scope-v2.md` already lists "airport lounge optimization" under
    Lifestyle Rewards, and Core Capability 6 (Existing Portfolio Optimization) explicitly
    covers *unused benefits*. It activates a dormant documented capability.
    - **Why Phase 1:** lounge access is the most-confused benefit in the Indian premium-card
      market (program, domestic vs. international, quarterly visit caps, spend-gating,
      guest rules, enrollment). It has the same in-the-moment shape as Best Card, very high
      organic search volume in India (acquisition), and it reinforces the ICP.
    - **Current state:** a single boolean, `has_lounge_access`, on the card. No program, no
      conditions, no caps. **The boolean is replaced, not extended.**
    - **Card side** — build now, bounded to our 9 cards, whose review process we already own.
    - **Airport/lounge directory — WE OWN IT.** Decided against the narrower recommendation
      (link out to the programs' own finders). Rationale: it is the strongest defensible data
      moat available to us and the best organic-search surface in the product. **Consequence,
      accepted:** it is a *data program, not a feature* — one to two orders of magnitude larger
      than the whole card catalog, changing constantly, every row needing `source` +
      `verified_on` + line-by-line review. Therefore: it **runs as a parallel track and must
      never block the card side**; it **ships by coverage, never by completion** (the product
      states which airports are covered — partial coverage presented as complete is the same
      trust failure as a stale condition); collection uses Playwright + BeautifulSoup, already
      in the stack, with human verification before seeding, and research is Gemini's documented
      role; coverage order follows our ICP's metros (DEL, BOM, BLR, HYD, MAA, CCU) first.
    - **Manual visit logging ships in Phase 1.** Decided against the entitlement-only
      recommendation, so the product can show "3 of 8 used · 5 expiring in 6 weeks" rather than
      only stating entitlement. **Two consequences to plan rather than discover:** (a) a logging
      habit now lands in Phase 1, ahead of Phase 2 spend logging — design them as **one pattern,
      not two**, or users get two things to remember and do neither; (b) **reset anchors are not
      uniform** (calendar quarter vs. card anniversary vs. statement cycle) and must be modeled
      per card. **Accepted failure mode:** an unlogged visit makes the count wrong *in the user's
      favour* — the direction that gets someone turned away at a desk. Mitigation: always show
      entitlement alongside the count, and treat logged visits as "at least this many used.".
    - **"Links to book" is reframed as activate / check / find.** Most Indian lounge access
      is not booked — the cardholder presents the card at the desk. What is actionable is
      enrollment links, the programs' own lounge finders, and genuine booking only where it
      exists. Promising a button that does not exist is a trust failure.
    - **Data perishability is the headline risk, and the reason for the tight scope.** Indian
      lounge benefits have been repeatedly devalued (caps introduced, spend-gating added,
      vendors switched). A stale lounge condition sends a user to a desk to be turned away —
      worse than having no lounge feature. Re-verification cadence is higher than the rest of
      the catalog, and ambiguity is seeded to the **more restrictive** reading with
      `needs_verification: true`, matching the `cards.yaml` earn-rate policy.
    - **Monetization flagged, not decided:** lounge content is the natural home for
      card-application affiliate links. Any such link must never influence ranking output.

11. **All existing engineering guardrails carry into every new surface unchanged:** no LLM
   ever produces a reward number; only `knowledge/`/`repositories/` touch the DB and only
   `ai_reasoning/` touches an LLM; the five engines remain the module boundary (Best Card
   lives in Valuation + Optimization, it is not a sixth engine); reward rules stay config;
   determinism stays a standing test; lineage columns persist on new stored results.

## Consequences

- **New canonical roadmap:** [`docs/prd/product-roadmap-v1.md`](../prd/product-roadmap-v1.md),
  with four phases — Daily Surface, Real Progress, Ask OptiMiles, Mobile.
- **`mvp-scope-v2.md` is amended, not superseded.** It remains canonical for what the goal
  engine does. Its "Platform Features / mobile applications" and "AI Features /
  conversational copilots" exclusions are overridden by decisions 4–7; a status banner on
  that document points here.
- **Root `CLAUDE.md` updated** — the MVP Exclusions list and Current Development Phase now
  reflect the post-MVP expansion.
- **The mobile-first web pass is reclassified** from cosmetic polish to a Phase 4
  prerequisite. The goal wizard and dashboard were built desktop-first.
- **`frontend/public/` has no `manifest.json`** — the PWA layer is greenfield.
- **A schema change is required for lounge** — `has_lounge_access` (boolean, in
  `0001_initial_schema.py`, `domain/catalog.py`, `api/schemas.py`, `api/catalog.py`) is
  replaced by real lounge-benefit modeling plus a seed pass over all 9 cards. First catalog
  schema change since v1.1; it needs its own migration and a decision-log note if the shape
  turns out non-obvious.
- Live award availability search moves from "out of scope" to **deferred pending evidence**,
  revisited only if it proves to be a conversion blocker.

## Open Questions

Carried into Phase 1 planning; none block starting the mobile-first pass.

1. What did testers mean by "app" — specifically, what would they do there that they would
   not do on web (notifications? logging a spend? checking a card at the counter)? This
   determines whether push is the real ask or just the available vocabulary.
2. Which devices were testers on? iPhone users would independently reinforce decision 7;
   Android users mean the ICP argument is carrying it alone.
3. Which two or three native capabilities clear Guideline 4.2? Must be settled before
   Phase 4, and ideally shapes Phase 1 architecture.
**None remain open.** Every question raised in this session was asked and answered the same
day; see below.

## Resolved Same Session (asked directly, 2026-08-26)

- **Best Card input: amount + category only.** No merchant→category mapping — a standing
  data-maintenance commitment where a wrong mapping yields a wrong recommendation. Revisit
  only if category selection proves to be real friction.
- **Best Card signed-out: full card picker**, reusing the bank-grouped picker already built
  for the goal wizard — not a fixed demo wallet. The acquisition argument only holds if the
  answer is genuinely the user's own.
- **Lounge airport directory: owned in-house** (see decision 10).
- **Lounge visit tracking: manual logging in Phase 1** (see decision 10).
- **Lounge coverage bar: partial but labelled.** Publish what is verified and say so
  ("DEL T3: 4 lounges verified, list may be incomplete"). Months rather than quarters to first
  launch, continuous coverage growth, and no claim of completeness we cannot back.
- **Lounge reset anchor: explicit per-card seeded field** (calendar quarter / card anniversary /
  statement cycle), sourced like any other catalog row. **No silent calendar-quarter default** —
  that would be quietly wrong for anniversary-based cards, which is the exact failure mode
  decision 10 committed to avoiding.
- **Tester devices: mostly iPhone.** This independently confirms decision 7 — iOS-first no
  longer rests on the ICP argument alone.
- **Native capabilities for Guideline 4.2: push notifications + biometric lock + offline card
  & lounge access.** Home screen widget dropped (most native-specific work, least return).
  **Phase 1 architectural consequence:** notification-worthy events (milestone hit, cap reset,
  lounge visits expiring) must be modeled as *events* during Phases 1–2 rather than computed at
  render, or there is nothing to push; the portfolio needs a route-level lock boundary; and the
  wallet + lounge payloads must be small and independently cacheable — **the lounge feature is
  used at airports, where signal is worst.**
