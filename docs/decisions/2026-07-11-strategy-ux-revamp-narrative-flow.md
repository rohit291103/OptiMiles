# Decision Log — Strategy Output + Goal Entry UX Revamp ("route plan" narrative)

**Date:** 2026-07-11
**Area:** frontend / product

## Context

A cold read of the strategy output (screenshot walkthrough) showed the screen
actively damaged trust instead of building it. Concretely:

- **"Why this strategy scores 51"** rendered the ranking engine's raw
  six-dimension sub-scores as if they were grades. The recommended plan showed
  "Efficiency 0" and "Goal achievement 21" directly under "Projected progress
  100% / Achievable" — a self-contradiction to anyone who doesn't know the
  sub-scores are *relative comparisons within the candidate set* (efficiency 0
  = fewest miles of the set, risk 90 = safe).
- Three unexplained mile numbers (45,000 required / 84,480 "best-case" /
  51,282 reached) with no stated relationship; "best-case" silently referred
  to the +2-cards tier.
- "Best route: no new cards" (a raw `headline_differentiator` slug) followed
  immediately by "Adding Magnus for Burgundy: 73,920 miles for ₹30,235" with
  no sentence saying when you'd want that — the app appeared to argue with
  itself.
- The per-category spend split rendered **only for the recommended tier**,
  even though `rank()` attaches `allocation_details` to every
  `RankedStrategy` — the alternatives' plans existed in the response and were
  thrown away by the UI.
- The earn-rate "why" (SmartBuy 16.65×, caps, exclusions) was hidden behind
  chevron disclosures; "Time to goal: 7 months" sat next to "Points earned
  over 8 months" (achievement month vs. horizon, never explained); internal
  lineage ("snapshot cat-b63f") shipped as user-facing footer copy; "no annual
  fee" was false-adjacent (Infinia has a fee — it means no *new* fees).
- Goal entry collected one monthly-spend number and secretly split it via a
  hard-coded `SPEND_MIX`, so users never saw or controlled what the engine
  actually earned on.

The product-model decision: the promise is "Google Maps for rewards," and
Google Maps says "Fastest route, 7 min, avoids tolls" then gives turn-by-turn
directions — it does not show its scoring internals as the primary UI.

## Decisions

1. **The result is a narrative in fixed order: verdict → routes → plan steps
   → chart → why.** Rebuilt `strategy-story.tsx` as the shared system
   (`VerdictHero`, `StrategyPlanTabs`, `PlanSteps`, `EarnChart`,
   `WhyThisRoute`, `NextSteps`, `FinePrint`), consumed by both the live
   simulator (`strategy-detail.tsx`) and the saved-goal view
   (`saved-strategy.tsx`). Every number remains a deterministic engine
   artifact; the only frontend arithmetic is presentation (differences,
   percentages, the established one-floor-per-card-month card total).
2. **Verdict first, in English.** `VerdictHero` opens with "You'll have
   ~51,282 KrisFlyer miles by month 7 — a month ahead of your deadline,"
   plus target/fees context and the narration summary. Infeasible goals get
   the same hero ("Not as stated") followed by the adjustment menu.
3. **Route options are selectable tab-cards; picking one swaps the entire
   plan** (spend split, transfers, chart, why). This fixes "only the
   recommended tier's split is visible" using data the API already returned.
   A non-recommended selection gets a one-sentence trade-off ("earns 22,638
   more miles… but costs ₹30,235 more") derived from engine numbers.
4. **The plan is numbered steps** — get the card (when applicable) → route
   your monthly spend (per-card groups, valuation notes now inline instead of
   chevron-hidden, milestone bonuses listed) → transfer to the program
   (months + processing-delay note) → book (chart miles per seat, buffer
   *tracked on top of* the target — the response's `miles_required_total`
   does NOT include `buffer_miles`; earlier copy claiming otherwise was
   corrected against a live response).
5. **Raw scores are demoted, not deleted.** `WhyThisRoute` states 2–3
   plain-language reasons derived from engine facts; the six bars live behind
   a "How OptiMiles scored this route" disclosure that spells out the
   semantics (comparisons within the candidate set, not grades; risk =
   higher-is-safer).
6. **Chart tells its timeline honestly:** titled "Points earned, month by
   month" with "Goal reached in month 7 of your 8-month window" and a dashed
   goal-month marker (clamped so the pill can't spill past the card edge).
7. **Goal entry is the sentence.** "I want to fly [business] to [Singapore]
   from [Hyderabad] within [8] months, for [1 passenger]" as inline controls,
   followed by "your situation": full-catalog wallet picker, **per-category
   monthly spend inputs** (travel/dining/online/groceries/utilities — the
   hidden `SPEND_MIX` split is gone; empty profile falls back to the engine's
   flagged default template), and an "Open to adding a new card?" preference.
8. **The new-card preference is applied client-side only** (default-selects
   the no-new-cards route tab when one exists). It does not touch ranking —
   wiring it into ranking weights is DP-07, deferred until the preference has
   a persistence story.
9. **Wallet picker lists the full catalog, not `acquirable` cards.**
   `acquirable` gates what the engine may propose as a *new* card; it never
   meant "can be held" (Atlas is closed to new applicants but holdable).
   Found by frontend-reviewer: Atlas was impossible to declare as an owned
   card.
10. **Lineage is fine print.** Footer copy is now human-first ("computed
    deterministically, never estimated by AI") with catalog/engine versions
    in small type; "no annual fee" copy became "₹0 new fees."
11. **Saved goals degrade gracefully.** Only the recommended tier is
    persisted in full; alternative tabs render a compact panel that says so
    and points at re-running the simulator. Older saves without
    `strategy_options` synthesize a single tier from the stored strategy
    (`miles` from the ledger's final `cumulative_target_miles`, which the
    projector defines as `miles_at_target_date`). Horizon is derived from
    ledger length (the ledger always runs the full window).
12. **API client typed two more persisted-domain fields** —
    `CandidateStrategy.transfer_plan` + `expected_milestones` — verified
    present in the live `/simulations` response before use.

frontend-reviewer drove the result in a real browser (1440×900 + 390×844;
default wallet, empty wallet, 5-tier long-horizon, and infeasible runs): zero
console errors, no horizontal overflow; its three findings (mobile spend-row
truncation, goal-pill overflow, the `acquirable` picker bug) were applied.
tsc + eslint clean.

## Not done (deferred)

- **Free-text goal entry** (`/goals/parse` Stage 1): wired but the OpenRouter
  free tier rate-limits; a free-text box that 429s is worse than the sentence
  form. Flip to free-text-primary once a paid key lands.
- **Persisting alternatives' full plans** (allocation details + ledgers per
  tier) so saved goals get the full tab-swap: backend `results.py` extension,
  noted in the tracker as the saved-detail-parity follow-up.
- **DP-07 preference-aware ranking** (the "open to new cards" answer should
  eventually modulate ranking weights server-side).
- **HSBC TravelOne hotel-portal earn rate (claimed 6× on hotels)**: not in
  the seed catalog (only 4× flights/OTA/forex is verified) and there is no
  "hotels" spend category; adding it is a seed change requiring web
  verification + line-by-line human review per build rule 5.
- **Backend latency**: reviewer measured `POST /simulations` at ~59.5s live
  (tracker already flags 36–44s vs. the 30s budget) — pre-existing, not a
  frontend defect, but it makes users sit on the loader.
