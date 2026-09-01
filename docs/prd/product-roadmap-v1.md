# OptiMiles Product Roadmap v1 — Post-MVP Expansion

**Document Path:** `/docs/prd/product-roadmap-v1.md`
**Version:** v1.0
**Status:** Approved — **canonical roadmap** for everything after the MVP
**Created:** 2026-08-26
**Relationship to scope:** Extends [mvp-scope-v2.md](mvp-scope-v2.md). The MVP scope document remains canonical for *what the goal engine does*; this document is canonical for *what gets built next and in what order*. Where the two conflict — specifically the "Platform Features / mobile applications" and "AI Features / conversational copilots" exclusions — **this document wins**, per decision log [`2026-08-26-post-mvp-expansion-and-mobile-strategy.md`](../decisions/2026-08-26-post-mvp-expansion-and-mobile-strategy.md).

---

# Why This Document Exists

The MVP is built and demoed. Two signals arrived at once:

**1. User testing.** People shown the product liked how easily they got a clear answer to a travel goal. The goal engine lands. But the recurring feedback was *"this would be better as an app."*

**2. Competitive.** A competitor (**PointsFly**, launched 2026-08-16) shipped an India-focused, AI-branded credit-card rewards platform with a broad daily-use feature surface — unified portfolio view, automatic transaction tracking with instant points alerts, award search with rupee-per-point valuation, an AI consultant chat, a "best card to swipe" feature, geofenced store alerts, and — notably — a **"Dream Destination tracker"** they describe as patent pending.

The second signal matters more than it first appears. Goal orientation is **not** the uncontested differentiator we assumed; a competitor is marketing it directly. Our defensible edge is narrower and deeper than "we do goals":

> **Our moat is a deterministic, explainable optimization engine.** Not that we track a goal — that we can show the exact math from spend to route to transfer to redemption, and defend every number in it.

That moat is real but invisible in a feature list. This roadmap adds the surface area that gets users in the door and keeps them there, without diluting the engine that makes the product worth trusting.

---

# The Core Problem With MVP-As-Shipped

The MVP answers one question extremely well: *"How do I get to Singapore Airlines business class in 8 months?"*

A user asks that question **once**. Then they have an 8-month accumulation period during which the product gives them no reason to return. There is no daily habit, no weekly check-in, no notification worth receiving. The value is entirely front-loaded into a single session.

This is a retention hole, and it is why goal-only positioning will not carry the business.

## The Retention Thesis

The fix is not to bury goals under competitor features. It is to build the ladder that leads to them:

```
DAILY     Best Card for this Spend      →  the habit / acquisition hook
WEEKLY    Spend logging + real progress →  makes the goal tracker true, not projected
QUARTERLY Goal strategy + plan          →  the payoff that retains
```

Today we only have step 3 — we sell the payoff without the habit that earns it. Every item in Phase 1 below exists to build steps 1 and 2, using engines that are **already written and fixture-tested**.

**Goals remain primary.** The daily surface is the on-ramp to the goal engine, not a replacement for it. Any feature that cannot eventually route a user toward a goal is a candidate for rejection.

---

# Feature Triage — The Competitive Surface

Every PointsFly capability, assessed against what we already have and what it would actually cost us.

## BUILD — reuses engines already in the repo

| Feature | What it is for us | Reuses |
|---|---|---|
| **Best Card for this Spend** | User enters an amount + category (+ optional merchant). Returns a ranked list of *their* cards with earned points, rupee value, and the reasoning chain. | Valuation Engine (`valuation/opportunities.py`), catalog earn rules, caps/exclusions |
| **Portfolio View** | All the user's cards in one place: earn rates by category, transfer partners, active caps and their utilisation, milestone progress, annual-fee dates. | `knowledge/store.py`, existing `/cards` page |
| **Grounded Q&A ("Ask OptiMiles")** | Natural-language questions answered **strictly from our verified catalog**, with the deterministic numbers shown alongside the prose. | `ai_reasoning/`, catalog snapshot |
| **Lounge Access Intelligence** | Which of the user's cards get them into a lounge, under exactly what conditions — and what they must do to activate it. See the dedicated section below. | `knowledge/` (new catalog tables), Portfolio View |

### Note on Q&A vs. the "conversational copilot" exclusion

`mvp-scope-v2.md` excludes "conversational copilots" and root `CLAUDE.md` excludes "generic chatbot experiences." Those exclusions are about **ungrounded chat** — an LLM improvising reward facts. A Q&A surface that retrieves from our verified catalog and renders deterministic numbers is the *opposite* of that failure mode, and is arguably our strongest demonstration of the moat. It is in scope under one hard constraint:

> **Every factual claim in an answer must be traceable to a catalog row or an engine output.** No number is ever generated by the LLM. If the catalog cannot answer, the product says so. This is the existing Stage 1 / Stage 10 boundary applied to a new surface — it is not a new architectural allowance.

## BUILD CHEAPLY — deliberately not the competitor's version

| Feature | Their version | Our version | Why |
|---|---|---|---|
| **Spend tracking** | Automatic SMS/transaction parsing with instant alerts | **Statement/CSV upload + quick manual log** | Their version needs Android SMS permissions (**iOS cannot do this at all**) or Account Aggregator integration. That is a mobile-infrastructure company. Ours captures ~80% of the value — real progress instead of projected progress — at a small fraction of the cost, and works on every platform. |
| **Award value lookup** | Live flight/hotel award search with real ₹/point | **Sweet-spot redemption table + "what are my points worth" calculator** | Live award availability is the hardest data problem in this category: seat-level scraping, constant breakage, high ongoing maintenance. `knowledge/goal_resolution.py` and `knowledge/requirements.py` already do most of the static work. Revisit live search only if it becomes a proven conversion blocker. |

## Lounge Access Intelligence *(added 2026-08-26)*

**Not scope creep.** `mvp-scope-v2.md` → Supported Goal Types → *Lifestyle Rewards* already lists "airport lounge optimization, travel benefit planning" as in-ecosystem but unsurfaced, and Core Capability 6 (*Existing Portfolio Optimization*) explicitly covers **unused benefits**. This activates a documented-but-dormant capability rather than adding a new one.

### Why it earns a place in Phase 1

- **It is the single most-confused benefit in the Indian premium-card market.** Access depends on which program the card rides (Priority Pass, DreamFolks, Visa/Mastercard lounge programs), domestic vs. international, per-quarter visit caps, spend-gating that unlocks visits only after a threshold, guest policy, and — critically — whether the user has *enrolled at all*. Most cardholders do not know their own answer.
- **Same shape as Best Card:** an in-the-moment question ("I'm at Delhi T3 — which card gets me in?") with a deterministic, catalog-backed answer. It is daily-surface utility, not a content page.
- **Acquisition.** Lounge eligibility carries very high organic search volume in India. It is one of the few reward topics people search *before* they know they have a rewards problem.
- **It reinforces the ICP.** Lounge access is a premium-card concern, and premium cardholders are exactly the users in `mvp-scope-v2.md` → Primary User.
- **It has a natural goal on-ramp:** "you have 6 unused visits expiring this quarter" and "your Atlas lounge benefit unlocks at ₹X more spend" are both *unused-benefit* findings — Capability 6 made visible.

### Current state

The catalog models lounge access as a **single boolean**, `has_lounge_access`, on the card (`backend/app/domain/catalog.py`, `alembic/versions/0001_initial_schema.py`, surfaced through `api/catalog.py`). It carries no program, no conditions, no caps. Everything below is greenfield, and the boolean is replaced — not extended.

### Scope — decided 2026-08-26

**Card side.** Bounded to our 9 supported cards, a dataset we already own the review process for. Per card, model:

- **Program** the access rides on (Priority Pass / DreamFolks / Visa / Mastercard / issuer-direct)
- **Domestic vs. international** entitlements, counted separately — they almost always differ
- **Visit caps** and their period (per quarter is the Indian norm), plus guest-visit rules
- **Spend gating** — visits unlocked only after a spend threshold in the period. This is the condition most users get wrong, and we can compute it, because we already track their spend for goals
- **Enrollment requirement** — whether the user must activate a membership before the benefit exists at all
- **Devaluation-sensitive fields** flagged for re-verification (see risk below)

**Airport / lounge directory — WE OWN IT.** *(Decided 2026-08-26 against the narrower recommendation; rationale: it is the strongest defensible data moat available to us and the best organic-search surface in the product.)* Airport → terminal → lounge → accepted programs, maintained in-house.

This is a **data program, not a feature**, and it is sized accordingly:

- It is one to two orders of magnitude larger than the entire card catalog, and every row carries `source` + `verified_on` + line-by-line review like any other seed row.
- **It runs as a parallel track and must never block the card side.** Best Card, Portfolio View, and card-side lounge conditions ship on their own timeline. The directory lands incrementally underneath them.
- **Ship by coverage, never by completion.** The product states which airports are covered and which are not. Partial coverage presented as complete is the same trust failure as a stale condition. "We don't cover Kochi yet" is an acceptable answer; a wrong lounge list is not.
- **Collection uses the stack we already have** — Playwright + BeautifulSoup against the programs' own lounge finders and airport sites, with human verification before any row is seeded. Research support is Gemini's documented role in the collaboration model.
- **Coverage order follows our users:** the metros our ICP actually flies from first (DEL, BOM, BLR, HYD, MAA, CCU), then the next tier, then international airports where KrisFlyer/Maharaja routes land.

### Visit tracking — in Phase 1

*(Decided 2026-08-26 against the recommendation to ship entitlement-only.)* Users log lounge visits manually, so the product can show **"3 of 8 used · 5 expiring in 6 weeks"** rather than only stating the entitlement. This is the stronger notification hook and the more useful answer.

Two things this pulls forward, both to be planned rather than discovered:

1. **A logging habit lands in Phase 1**, ahead of the Phase 2 spend-logging work. Design them as **one pattern, not two** — same entry surface, same mental model — or users end up with two separate things to remember and do neither.
2. **Reset periods are not uniform and are the hard part.** Issuers variously reset on the calendar quarter, the card anniversary, or the statement cycle. The quarter anchor must be modeled per card, not assumed. This is the most likely source of a wrong count, and a wrong count is worse than no count.

**Honest failure mode, accepted:** an unlogged visit makes the displayed count wrong in the user's favour, which is exactly the direction that sends someone to a desk to be turned away. Mitigation: always show the entitlement alongside the count, and treat logged visits as *"at least this many used"* rather than as authoritative.

### On "links to book"

Worth stating precisely, because the mental model is usually wrong: **most Indian lounge access is not booked.** The cardholder presents the card or a program membership at the desk. What is genuinely actionable, and therefore what we link to:

- **Activate** — issuer enrollment pages for Priority Pass / DreamFolks memberships that must be claimed before they exist
- **Check** — the program's own lounge-finder for a given airport (the correct place to send someone, rather than mirroring their directory)
- **Book** — only where booking is real: some paid-access and reserved lounges

Framing this as *activate / check / find* rather than *book* is not pedantry — it is the difference between a feature that matches reality and one that promises a button that does not exist.

### The real risk: data maintenance

This is the reason to scope it tightly rather than the reason to skip it.

Indian card lounge benefits have been **repeatedly devalued** — quarterly caps introduced where there were none, spend-gating added to previously unconditional benefits, programs switched between vendors. A lounge table is materially more perishable than earn rates or transfer ratios. Two consequences:

1. **Every lounge row carries `source` + `verified_on` like every other seed row, and re-verification cadence is treated as higher than the rest of the catalog.** A stale lounge condition is worse than no lounge feature — it sends a user to a desk to be turned away, which is exactly the trust failure the whole product is built to avoid.
2. **Under-promise on ambiguity.** Same policy as earn rates (`cards.yaml` seeding policy): where a condition is unclear, seed the *more restrictive* reading and flag `needs_verification: true`.

### Business note

Lounge content is the most natural home in the product for card-application affiliate links, since the query "which card gets me lounge access" is genuinely adjacent to acquiring one. Flagged as a monetization surface to consider; **no decision taken here**, and any such link must never influence ranking output — the engine's independence is the product.

---

## REJECT

| Feature | Why not |
|---|---|
| **Geofenced store alerts** | Requires a native app with background location permission. Zero fit with a web-first architecture, meaningful battery/privacy cost, and weak real-world value — users do not change card at the mall entrance because of a push notification. This is a demo feature. |
| **Automatic bank/transaction integration** | Same conclusion as the MVP scope reached: bank integrations stay out. Account Aggregator onboarding is a regulatory and engineering project of its own, and it is not what makes our recommendations good. |

---

# Phased Plan

Phases are ordered by **dependency and business impact**, not by effort.

> **Sequencing decision (2026-08-26):** build the usable web features first; the app conversion comes later. Phases 1–3 are entirely web. **Phase 4 does not start until Phases 1–3 have landed** — there is no point wrapping a surface that is not yet worth opening daily. The mobile-first pass inside Phase 1 is web work that makes the existing surfaces usable on a phone; it is not the beginning of the app project.

## Phase 1 — Daily Surface (the habit)

**Goal:** give a user a reason to open OptiMiles in a moment of actual spending.

- **Best Card for this Spend**
  - **Input: amount + category only** *(decided 2026-08-26)*. Categories come from the existing catalog earn-rule vocabulary. **No merchant→category mapping** — it is a standing data-maintenance commitment and a wrong mapping produces a wrong recommendation. Revisit only if category selection proves to be real friction.
  - Output: ranked cards with points earned, rupee value, and the "why" — including *why not* the runner-up (we already do runner-up cause attribution, see decision `2026-07-13-runner-up-cause-attribution.md`)
  - Must respect: category caps and their current utilisation, exclusions, milestone proximity
  - **Goal linkage:** when the user has an active goal, show how this spend moves them toward it. This is the on-ramp.
  - **Signed-out with a real card picker** *(decided 2026-08-26)* — anyone can select their own cards and get a genuinely true answer, reusing the bank-grouped picker already built for the goal wizard. Not a fixed demo wallet: the acquisition argument only works if the answer is actually theirs. The account then sells itself on saving the wallet and carrying it into a goal.
- **Portfolio View** — expand `/cards` from catalog browsing into the user's own portfolio: caps, milestone progress, transfer partners, fee calendar
- **Lounge Access Intelligence** — see the dedicated section above. Replaces the `has_lounge_access` boolean with real conditions; surfaces "which of my cards gets me in, under what conditions, and what must I activate," plus **manual visit logging** ("3 of 8 used"). Needs a schema change and a seed pass over the 9 cards. The **airport/lounge directory runs as a parallel data track** and must not block this.
- **Mobile-first pass on the existing surfaces** — the goal wizard and dashboard were built desktop-first (138 breakpoint usages across 58 components, but the layouts assume a wide viewport). Most users will hit these features on a phone browser long before any app exists, so this is usability work that pays off immediately — and it happens to be the prerequisite for Phase 4. Not cosmetic polish.

## Phase 2 — Real Progress (the loop)

**Goal:** turn the goal tracker from a projection into a record.

- **Spend logging** — quick manual entry, plus **statement/CSV upload** with a mapping step
- **Actual vs. projected progress** on the goal detail page — the Simulation Engine already projects; this adds the observed series alongside it
- **Milestone and cap alerts** — "you are ₹18,000 from the Atlas milestone", "your 5% cap resets in 4 days". These are the notifications that justify an app, and they come from data we already model
- **Re-plan on drift** — when actual accumulation diverges from plan, offer a re-run rather than silently showing a stale strategy

## Phase 3 — Ask OptiMiles (the moat, made visible)

**Goal:** answer arbitrary reward questions with numbers we can defend.

- Catalog-grounded Q&A over cards, transfer partners, ratios, caps, and the user's own portfolio
- Every answer renders the underlying numbers and their source, not just prose
- Explicit "the catalog does not cover this" path — refusing to guess is the product's brand
- Reuses the existing intent-extraction and narration boundary; no new LLM authority

## Phase 4 — Mobile (the form factor)

**Goal:** deliver the thing user testing actually asked for.

**Entry condition:** Phases 1–3 shipped and in use on web. Do not start earlier.

**Sequence — web-first, then wrap. One codebase throughout.**

1. **Mobile-first web** *(Phase 1 dependency, listed above)*
2. **PWA layer** — `manifest.json`, service worker, web push. There is no manifest in `frontend/public/` today. Near-free on Android; useful everywhere
3. **iOS app via Capacitor** — App Store first, per the ICP argument below
4. **Android app via Trusted Web Activity** — near-free once the PWA exists

### Why iOS first

India is roughly 95% Android by raw market share, which argues for Android first. We are choosing iOS first anyway, deliberately:

> **Our ICP is not the mass market.** Infinia, Amex Platinum, and Magnus holders — users spending ₹50,000–₹2,00,000/month on premium travel cards, per `mvp-scope-v2.md` → Primary User — skew heavily toward iPhone. Shipping to the platform our actual paying users hold beats shipping to the platform the median Indian holds.

This is a real trade and it costs us something. Recording it here so the choice is not mistaken later for an oversight.

### Known costs of the iOS-first choice

- **App Store Guideline 4.2 (Minimum Functionality).** Apple rejects apps that are repackaged websites. A Capacitor/WKWebView shell with no native capability *will* be bounced. Android's Play review has no equivalent barrier — a TWA wrap ships in days. **We front-load the hard approval problem.**
- **iOS PWA install is a dead end.** No install prompt; users must manually tap Share → Add to Home Screen, and web push only functions afterward. On iOS the PWA is not a substitute for the App Store. On Android it is a one-tap banner.
- **iOS cannot read SMS.** If automatic transaction tracking ever becomes the retention feature, iOS is permanently blocked from it. Our Phase 2 choice of upload-and-manual-log is what keeps this from being fatal — another reason not to build the competitor's version.

### Mitigation — decide native capabilities in Phase 1, not at submission

To clear Guideline 4.2, the app must do something a website does not. Choose **two or three** of the following during Phase 1 and architect the web app so they bolt on cleanly:

- Push notifications for milestone/cap alerts *(strongest candidate — it is the Phase 2 feature users would install for)*
- Face ID / biometric lock on the portfolio view
- Home screen widget showing goal progress
- Offline access to the card list and portfolio

**Do not** discover this requirement at submission time.

### Explicitly not doing

A React Native or Flutter rewrite. It is months of work, it forks the frontend permanently, and it buys nothing our engines need. Capacitor keeps one codebase; if native depth is ever genuinely required, Capacitor is the incremental path to it.

---

# What Stays Out of Scope

Carried forward from `mvp-scope-v2.md`, still excluded, now with the competitive context:

- **Automated transfer execution** — we recommend transfers; we never execute them
- **Bank / Account Aggregator integrations** — see triage above
- **Live award availability search** — deferred, not rejected; revisit only on evidence
- **Geofenced store alerts** — rejected
- **Autonomous agents, memory-heavy personalization, autonomous financial advice** — unchanged
- **Community, referrals, enterprise accounts, social features** — unchanged
- **Cashback optimization as a primary mode** — we remain a premium-travel product

---

# Guardrails Carried Into Every Phase

These are not negotiable and apply to all new surfaces:

1. **No LLM ever produces a reward number.** Stage 1 (intent) and Stage 10 (narration) remain the only LLM touchpoints. "Best Card" and "Ask OptiMiles" are deterministic engines with optional narration on top.
2. **Only `knowledge/` and `repositories/` touch the database; only `ai_reasoning/` touches an LLM.**
3. **The five engines remain the module boundary.** Best Card lives in Valuation + Optimization. No sixth engine without a decision-log entry.
4. **Reward rules stay config, not code.** New surfaces read the same catalog with the same `source` + `verified_on` discipline.
5. **Determinism stays a test.** Same inputs + snapshot version ⇒ byte-identical results, end to end.
6. **Lineage persists.** `catalog_snapshot_version` + `engine_version` on every stored result, including new surfaces.

---

# Success Criteria

The MVP's success criteria (`mvp-scope-v2.md` → Success Criteria) still hold. This roadmap adds:

| Phase | The product succeeds when a user can… |
|---|---|
| 1 | Decide which card to use for a real purchase in under 10 seconds, and understand why — and know, before reaching the airport, which of their cards gets them into a lounge and on what condition |
| 2 | See their actual accumulated rewards against their plan, and be told when to act |
| 3 | Ask a reward question in their own words and get an answer with visible, sourced math |
| 4 | Do all of the above from their phone home screen, and receive a notification worth receiving |

**The retention question this roadmap exists to answer:** does a user who set a goal open OptiMiles again within 7 days? Today, structurally, they have no reason to.

---

# Open Questions

Carried into Phase 1 planning; none are blockers for starting the mobile-first pass.

1. **What did testers mean by "app"?** Specifically: what would they do in an app that they would not do on web — receive notifications, log a spend, check a card at the counter? This determines whether push is the actual ask or just the available vocabulary.
2. **Which devices were testers on?** If they were iPhone users, that independently reinforces the iOS-first call. If Android, the ICP argument is carrying the decision alone.
3. **Which two or three native capabilities clear Guideline 4.2?** Must be settled before Phase 4 begins, and ideally shapes Phase 1 architecture.
**All open questions were resolved on 2026-08-26**, asked and answered directly. Recorded here as the standing answers.

| Question | Decision |
|---|---|
| Best Card input | **Amount + category only.** No merchant→category mapping — a standing maintenance commitment where a wrong mapping yields a wrong recommendation. Revisit only if category selection proves to be real friction. |
| Best Card signed-out | **Full card picker, signed-out** — reuse the goal wizard's bank-grouped picker, not a fixed demo wallet. The acquisition argument only holds if the answer is genuinely the user's. |
| Lounge airport side | **We own the full directory**, run as a parallel data track. |
| Lounge visit tracking | **Yes — manual visit logging in Phase 1.** |
| Lounge coverage bar | **Partial but labelled.** Publish what is verified and say so explicitly ("DEL T3: 4 lounges verified, list may be incomplete"). Ships in months rather than quarters, coverage grows continuously, and the product never claims completeness it does not have. |
| Lounge reset anchor | **Explicit per-card field** — anchor type (calendar quarter / card anniversary / statement cycle) is seeded and sourced per card, like any other catalog row. More work up front, and the only version that is actually correct. No silent calendar-quarter default. |
| Tester devices | **Mostly iPhone** — this independently confirms the iOS-first call; it no longer rests on the ICP argument alone. |
| Native capabilities for Guideline 4.2 | **Push notifications + biometric lock + offline card & lounge access.** Home screen widget dropped as the most native-specific work for the least return. |

### Consequences for Phase 1 architecture

The three chosen native capabilities are what the web app must be built to accommodate — decided now, not at submission:

- **Push notifications** — the notification-worthy events (milestone hit, cap reset, lounge visits expiring) must be modeled as *events* in Phases 1–2, not computed only at page render, or there is nothing to push.
- **Biometric lock** — the portfolio view needs a clean lock/unlock boundary; keep it a route-level concern rather than scattering it through components.
- **Offline card & lounge access** — the user's wallet and their lounge conditions must be independently cacheable. This is the one that matters most in practice: **the lounge feature gets used at an airport, which is exactly where signal is worst.** Design those payloads to be small and self-contained from the start.
