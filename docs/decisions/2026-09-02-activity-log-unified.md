# Decision Log — Unified activity logging (spend + lounge visits)

**Date:** 2026-09-02
**Area:** Simulation Engine / schema / API / frontend
**Roadmap:** `docs/prd/product-roadmap-v1.md` → Phase 1 (lounge visit logging) **and** Phase 2 (spend logging), built together
**Scope of this entry:** the shared logging model, period-window arithmetic, the observed-activity calculator, migration 0008, the `/v1/activity` API, and the `/activity` surface.

## Context

Phase 1 was complete except lounge visit logging, and that item was deliberately blocked on a design decision the roadmap states outright:

> "A logging habit lands in Phase 1, ahead of the Phase 2 spend-logging work. Design them as **one pattern, not two** — same entry surface, same mental model — or users end up with two separate things to remember and do neither."

Three shipped surfaces were also carrying an explicit hole: Portfolio View states in its own API payload that cap utilisation and milestone progress "need Phase 2 spend data", and the lounge section could state an entitlement but never a count.

## Decisions

1. **Spend logging and lounge-visit logging were built as one feature, not sequenced.** They are not merely similar — they are *coupled*. A lounge spend gate ("₹60,000 in the preceding quarter") is evaluated **from the spend log**, so the lounge half is not fully implementable without the spend half. Sequencing them would have shipped a lounge counter that could not answer whether the visits were unlocked.

2. **No sixth module.** Backend Build Rule 1 forbids a new top-level package without a decision-log entry, and none was needed: this work *is* the Simulation Engine's stated vocabulary ("milestone tracking, redemption readiness"). Period arithmetic went to `simulation/periods.py`, the calculator to `simulation/observed.py`, persistence to `repositories/activity.py` (build rule 3: only `knowledge/` and `repositories/` touch the DB). `PeriodWindow` is a value type and lives in `domain/`, because the boundary test forbids `domain/` importing an engine.

3. **Two tables, one pattern.** The shared shape is `(user, card, date, note)`; the payloads have nothing in common (₹ and a category vs. a scope and a guest count). A single polymorphic table would be half-NULL columns guarded by per-kind CHECKs. The sharing therefore lives where it is load-bearing — the window arithmetic, the API resource family, and one entry surface where the card and date fields never move between modes.

4. **The honesty model is the design, and it is encoded in the type names.** A manual log is a **lower bound**: users forget entries, they never invent them. Consequences, carried end to end into the wire format and the UI copy:
   - logged spend can prove a milestone or a spend gate **REACHED**, and can never prove one missed — so `ObservedStatus` has `REACHED` and `NOT_PROVEN`, and **deliberately no `NOT_REACHED`**;
   - remaining headroom is an **upper** bound — the fields are `visits_logged_at_least` and `remaining_at_most`, never a plain `remaining` a client could render as fact.

   This is the roadmap's own accepted failure mode ("an unlogged visit makes the displayed count wrong in the user's favour") plus the mitigation it demands. A field named `remaining` would eventually print "you have 1 lounge visit left" to someone who has none.

5. **The spend gate reads the PRECEDING window, and that got its own function.** `previous_window()` exists so no call site re-derives the off-by-one-period. Regalia Gold's 3 domestic visits this quarter are unlocked by ₹60,000 spent *last* quarter; ₹2,00,000 spent this quarter does nothing for this quarter's visits, and the UI says so in those words.

6. **Period boundaries are always computed from the origin, never by stepping.** Stepping compounds the end-of-month clamp — 31 Jan → 28 Feb → 28 Mar walks the anchor day permanently earlier. Computing every boundary as `origin + k months` keeps 31 Jan / 30 Apr / 31 Jul, which is what an issuer means. Windows are half-open `[start, end)` so they tile with no gap or overlap: a visit on 1 April belongs to Q2 alone.

7. **A card-relative anchor with no date raises `AnchorDateRequired` — never a calendar fallback.** All four currently-seeded lounge cards use calendar anchors, so no card-open date is collected yet and none was added speculatively. When such a row appears, the entitlement is reported as `UncountableAllowance` with a reason in the user's terms rather than counted wrongly. This is the same posture migration 0007 took by making `reset_anchor` NOT NULL with no default.

8. **Caps and milestones carry `anchor_assumed: true`, stated in the UI.** The catalog states a cap's *period* but never what it resets against, and most Indian caps actually run on the statement cycle. We assume the calendar and say so on the row ("counted on the calendar month, which may differ from your statement cycle") rather than implying knowledge we do not have. Adding a real `cap_reset_anchor` to the catalog is a data question, not a code one — logged as follow-up.

9. **Logging is signed-in only.** Best Card and Portfolio View are anonymous because the wallet is whatever the client sends; a log is a personal record that has to survive a device. `card_id` references the *catalog*, not `user_cards`, so logging is not gated on a server-side wallet that does not exist yet — the wallet stays the per-device `lib/wallet.ts` for now.

10. **A visit is logged against `(card, scope)`, never against an entitlement tier.** A cardholder has no reason to know which tier admitted them; attribution is the calculator's job. Where a card holds several tiers for one scope, the same visits appear against each — the tiers are alternatives, not additive allowances.

11. **Visits are accepted for cards with no seeded lounge entitlement.** Coverage is deliberately partial (4 of 9). Refusing to record something the user says happened because our catalog is incomplete would be backwards; it simply is not counted against an allowance we do not have.

12. **No `source` column on `spend_entries` yet.** Statement/CSV import is named in the same roadmap phase, but it changes *behaviour*, not just provenance: an imported statement makes the log **complete** for its period rather than a lower bound, which is the entire honesty model above. That belongs in the slice that ships the importer.

13. **Future-dated entries are rejected at the API edge (422).** A log records what happened, not what is planned; a future entry would count toward a window it has not happened in and silently inflate a milestone. Enforced in the endpoint rather than as a CHECK, because a CHECK cannot call `NOW()`.

## What shipped

**Backend**
- `domain/activity.py` — `PeriodWindow`, `SpendEntry`, `LoungeVisit`, `CapUse`, `MilestoneProgress`, `SpendGateState`, `LoungeAllowanceUse`, `UncountableAllowance`, `ObservedActivity`, `ObservedStatus`
- `simulation/periods.py` — `current_window` / `previous_window` / `AnchorDateRequired`
- `simulation/observed.py` — `observe()`, a pure function of (snapshot, entries, wallet, date)
- `alembic/versions/0008_activity_log.py` — `spend_entries`, `lounge_visits`, owner-only RLS, `updated_at` triggers, one index per access pattern. **Applied to the live database.**
- `repositories/activity.py` — the only module touching those tables; every query user-scoped
- `api/activity.py` — `POST/GET/DELETE /v1/activity/spend` and `/lounge-visits`, plus `GET /v1/activity/summary`, all auth-required

**Frontend**
- `lib/api.ts` — the activity client and types
- `components/app/activity-log.tsx` — one form with two modes, plus lounge / caps / milestones / log sections
- `app/(app)/activity/page.tsx`, nav entry in `app-shell.tsx`

**Tests:** 84 in `tests/unit/simulation` (25 period goldens hand-computed from the calendar, 32 calculator goldens hand-computed from the real seed catalog), 22 endpoint, 6 repository. Suite **500 → 584 passed**, mypy strict + ruff + tsc + eslint + next build all clean.

## Verification

Driven live against the real database and a real `auth.users` row, at 390×844 and 1440×900:

- Log ₹75,000 travel on Infinia → cap moves ₹0 → **₹75,000 of ₹1,50,000 · Sep 2026**, headroom "at most ₹75,000 left"
- Log a domestic visit on Regalia (+2 guests, typed "bom") → **"At least 1 used in Jul–Sep 2026 · at most 2 left"**, "2 guest visits logged — these do not come out of your own allowance", airport stored as **BOM**
- Spend gate renders **"Needs ₹60,000 spent in Apr–Jun 2026 — the quarter before this one"** as of a date in Q3
- Delete removes the row; future-dated entry 422s; unknown card 404s; every route 401s without a token
- **0 horizontal overflow, 0 sub-12px text, 0 sub-44px tap targets, 0 console errors**
- Catalog snapshot version **unchanged at `cat-c25780ce44db`** across the schema change — D-2 still holding

Test data was removed from the live database afterwards.

## Also fixed

The signed-in shell's mobile hamburger was **36×36** — the only route to navigation on a phone inside the app. The 2026-09-01 mobile pass fixed `site-nav.tsx`'s equivalent but could not drive these pages (they sit behind Google OAuth), and explicitly flagged that gap. Now `size-12 sm:size-9`, with the drawer's close button given the same treatment. Mobile tap targets on `/activity` went 1 → 0.

## A note on the verification itself

Roughly an hour went into chasing a "the UI is one write behind" defect that did not exist. The activity summary round-trips in ~2.5s against the remote Supabase pooler; fixed `waitForTimeout(2500/3000)` calls in the Playwright harness were racing it, and repeated runs against shared database state made the off-by-one look systematic. Two false conclusions were drawn and reversed before instrumenting the component directly showed fresh data arriving and being applied correctly.

**The lesson worth keeping:** when verifying against a *remote* database, assert on the expected outcome (`waitForFunction`) and reset state between runs. A fixed timeout that is "obviously long enough" locally is a coin flip at 2.5s round trips, and it fabricates a very convincing bug.

## Next

- Wire the summary into Portfolio View so `/cards` shows real utilisation instead of its `spend_data_available: false` caveat
- Statement/CSV upload (Phase 2), which introduces the `source` column and the "complete for this period" behaviour
- Actual-vs-projected progress on the goal detail page, and milestone/cap alerts — both now have their data source
- Seed a real `cap_reset_anchor` so `anchor_assumed` can go false where the issuer's reset is known
