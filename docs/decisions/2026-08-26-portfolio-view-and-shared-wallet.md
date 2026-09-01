# Decision Log — Portfolio View + the shared wallet

**Date:** 2026-08-26
**Area:** backend (Valuation Engine) / frontend / product
**Roadmap:** `docs/prd/product-roadmap-v1.md` → Phase 1 (Daily Surface), item 2

## Context

Best Card shipped earlier the same day. The next Phase 1 item is **Portfolio
View** — "expand `/cards` from catalog browsing into the user's own portfolio:
caps, milestone progress, transfer partners, fee calendar."

`/cards` was a read-only grid of card art for all 9 supported cards. Nothing in
the product knew which cards a given user actually holds: the goal wizard asked
every time (pre-selecting Infinia + Atlas as a guess), and Best Card asked
again. The same person could get three answers computed over three different
wallets in one session.

## Decisions

1. **Portfolio View lives in the Valuation Engine, not Knowledge.** The reshape
   of catalog rows into per-card facts is Knowledge-shaped, but what makes this
   a *portfolio* rather than a card list is that every earn rate, every
   milestone bonus and every transfer ceiling is **priced in miles toward a
   target program**, and cards are compared in that unit. That is
   transfer-value estimation — Valuation's job. New file
   `backend/app/valuation/portfolio.py`; **no sixth engine** (build rule 1).

   `knowledge/education.py` stays as-is: it is the wizard's *narration-shaped*
   read of the same catalog, and the module-boundary test forbids Valuation
   from importing Knowledge anyway.

2. **Same central invariant as Best Card: comparison is by MILES, never by
   points.** HDFC RP, EDGE Miles and MR are different units and the catalog
   carries no ₹-per-point valuation (inventing one would violate the seed
   policy). A card with no link to the target program is priced `null` —
   never zero, never ranked. **Where no wallet card reaches the target, the
   category leader is `null`**: we decline to rank the incommensurable rather
   than guessing. The golden test that proves this matters is the same shape as
   Best Card's — Regalia Gold earns 2.67 pts/₹100 against TravelOne's 2.00 but
   only 1.335 KrisFlyer miles against TravelOne's 2.00, because its tier
   transfers 2:1 against 1:1.

3. **Phase 1 shows targets, not progress — and says so.** Cap *utilisation* and
   milestone *progress* need observed spend, which is Phase 2. The endpoint
   returns `spend_data_available: false` plus a `caveat` string, so the honesty
   ships with the numbers rather than depending on the UI to remember it.
   Annual-fee **dates** are dropped from scope for the same reason: they need
   the user's card-open date, which the catalog does not and should not hold.
   Fee *amounts* and a wallet total do ship.

4. **Three rollups earn their place beyond a per-card dump:**
   - **"Which card wins, by category"** — every category any wallet card
     accelerates, compared across the whole wallet in miles/₹100. Cards with no
     rule for a category still appear **at their base rate** (the same fallback
     Best Card applies), because "is my travel card actually better here?" is
     the question the table exists to answer.
   - **Transfer ceilings in miles** — `annual_ceiling_miles` converts a link's
     yearly points cap into the target program (Atlas: 30,000 EDGE Miles/year =
     **60,000 KrisFlyer miles**). That number bounds a single-card strategy and
     is buried in T&Cs nobody reads. It uses **whole-block** conversion
     (`points_to_miles`), not marginal — see the review section below.
   - **"Where your points can go"** — partners reachable from the wallet, with
     the best door into each (`best_miles_per_1000_points`).

5. **`marginal_miles` promoted into `valuation/transfer_math.py`.** Best Card
   had it as a private helper; pricing a milestone bonus needs the same
   arithmetic. Ratio conversion lives in exactly one module (blueprint §3.1),
   so it moved rather than being copied. `points_to_miles` (whole-block) still
   models an actual send; `marginal_miles` prices a purchase or a bonus.

6. **One wallet, stored in `localStorage`** (`frontend/src/lib/wallet.ts`),
   shared by Portfolio View, Best Card and the goal wizard.
   - **Why not a DB table:** Best Card is signed-out by design, so the wallet
     must work with no account at all; the wallet is a list of catalog card ids
     (no balances, no statements, nothing sensitive); and a server-side wallet
     needs a schema change plus a migration story for signed-out users. Phase 2
     (spend logging) is when a per-user row starts earning its keep. Until then
     this is the small honest version — **per-device, and the UI says so.**
   - Reads go through `useSyncExternalStore`, so every mounted surface —
     including other browser tabs — re-renders together.

7. **Who may write the wallet, deliberately split:**
   - The **goal wizard writes it** — its step asks the ownership question
     directly ("cards you already hold"), so the answer *is* the wallet. It
     also now **pre-selects the saved wallet** instead of guessing Infinia +
     Atlas, filtered against the live catalog so a stale id can never be
     posted.
   - **Best Card does not auto-write.** Its picker is a what-if ("what if I
     had…"), so it pre-fills from the wallet and offers an explicit **"Save
     these as my cards"** button that appears only when the selection actually
     differs. Silently overwriting someone's portfolio because they compared a
     card they don't own is the wrong default.

8. **`/cards` leads with the portfolio, keeps the catalog below.** The card-art
   grid is still the browse-and-add surface; it is now the second section of
   the page rather than the whole page.

9. **A stale wallet fails loudly.** An id no longer in the catalog is a 404
   from the endpoint (not a silent drop — a confident ranking over a wallet the
   user didn't ask about is worse than an error), and the UI opens the card
   picker on that error so the user can actually fix it.

## What shipped

**Backend**
- `app/valuation/portfolio.py` — `build_portfolio(snapshot, *, card_ids,
  target_program_id) -> WalletPortfolio`. Pure function of the snapshot: no DB,
  no clock, no LLM.
- `app/valuation/transfer_math.py` — `marginal_miles()` promoted from
  `best_card.py`'s private helper.
- `app/api/portfolio.py` — `GET /v1/portfolio`, anonymous, ETag'd on snapshot
  version + query hash, `UnknownCard` → 404, `ValueError` → 422 (mirrors
  `/v1/best-card`).
- Tests: `tests/unit/valuation/test_portfolio.py` (32, golden values hand-
  computed from the seed catalog) + `tests/unit/api/test_portfolio_endpoint.py`
  (10). Full suite **461 passed**; mypy strict + ruff clean.

**Frontend**
- `src/lib/wallet.ts` — the shared wallet store.
- `src/components/app/portfolio-view.tsx` — summary tiles, the category
  comparison table (internal `overflow-x-auto`), per-card panels (earn rates /
  milestones / transfers out), partner reach, the API's caveat line.
- `src/app/(app)/cards/page.tsx` — portfolio first, catalog second.
- `src/components/best-card.tsx` — wallet pre-fill + explicit save.
- `src/components/goal-wizard.tsx` — wallet pre-fill + persist on toggle.
- tsc + eslint + `next build` clean. Verified in a real headless browser at
  1440×900 and 390×844: no horizontal overflow, no console errors, correct
  golden numbers on screen, and the Best Card save flow exercised end to end.

## Consequences / follow-ups

- **The wallet is per-device.** A user on a phone and a laptop has two wallets.
  Acceptable for Phase 1; Phase 2's per-user persistence is where this gets
  fixed, and the store's single-module shape is what makes that a swap rather
  than a rewrite.
- **Lounge access is still a boolean** in the card panels (`has_lounge_access`)
  — the Lounge Access Intelligence item replaces it wholesale, and Portfolio
  View is where its real conditions will land.
- **Milestone tiers render as independent rows.** Atlas's Silver/Gold/Platinum
  thresholds are cumulative in reality; the catalog models them as separate
  rows and the UI shows them that way. Correct per the seed data, but worth
  revisiting when milestone progress lands in Phase 2.
- **Fee calendar deferred**, per decision 3 — needs a card-open date the
  product does not collect yet.


---

# Review pass (same session)

Both reviewers were run after the feature was built. Findings and what was done
with them.

## `backend-reviewer`

1. **`annual_ceiling_miles` was overstating — fixed.** It priced the yearly
   transfer cap with `marginal_miles`, but that cap bounds a **real send**, and
   a send floors to whole ratio blocks. At 3:2 a 5-point cap clears one block —
   2 miles, not the 3 marginal pricing claims. Now `points_to_miles`, matching
   what `simulation/projector.py` and `optimization/allocation.py` already do
   after applying the same cap.

   The sharp part of this finding: **both capped links in the current catalog
   cap on an exact multiple of `ratio_from`**, so the two functions agree today
   and the original golden test passed either way. Convenient seed data was
   hiding a real overstatement on a number this document calls "the number that
   actually bounds a single-card strategy". There is now a test that builds
   links which do *not* divide evenly.

   **The general lesson, worth carrying:** a golden test drawn only from current
   seed values cannot distinguish two formulas that happen to agree on that
   data. Where two plausible formulas exist, pin the case that separates them,
   even if it needs a synthetic row.

2. **`CategoryLeader.category_label` depended on wallet order — fixed.** It took
   "the first accelerated row", so the same wallet listed in a different order
   could render a different label for the same category. It now comes from the
   card with the strongest claim (accelerated first, then rate, then card name),
   and a card with no rule for a category can no longer lend it a fallback name.

3. **ETag used Python's `hash()` — fixed in both `/v1/portfolio` and
   `/v1/best-card`.** `str` hashing is salted per process, so every worker and
   every restart minted a different ETag for the same query: never a false 304,
   but never a cache hit either. Now a sha256 digest. Pre-existing in Best Card;
   fixed there too since this endpoint copied it.

4. Coverage gaps closed: `bonus_miles is None` when the card cannot reach the
   target program (Atlas priced against Marriott, which Axis lost in the
   Apr-2026 devaluation), catalog pass-through fields, and a 21-card wallet →
   422.

**Not changed, deliberately:** `PortfolioResponse` subclassing the engine's
`WalletPortfolio` (flagged as a watch-item, not a defect — Best Card already
returns the bare engine type, and forking their shapes buys nothing today), and
the `knowledge/education.py` ↔ `valuation/portfolio.py` resemblance (the
reviewer agreed the split is correct; cross-referencing comments were added to
both files so the next reader does not "fix" it).

Backend after the pass: **467 tests**, mypy strict + ruff clean.

## `frontend-reviewer`

Driven live at 1440×900 and 390×844 with a **full 9-card wallet** — the case the
first pass had not tried.

1. **The category table lost its row labels on horizontal scroll — fixed.**
   Scrolling right to reach the 6th–9th card scrolled the category name away
   with it, leaving bare numbers. The row header is now `sticky left-0` on an
   opaque background. This was undermining the one table this document calls the
   page's actionable payoff.

2. **Nothing indicated the table scrolled — fixed.** On a phone a 9-card wallet
   showed about a quarter of the table inside a plain bordered box that read as
   complete. Added a right-edge fade that hides once scrolled to the end, plus a
   "scroll sideways to compare all N cards" line, both shown only when the table
   actually overflows.

3. **A stale wallet was an unrecoverable trap — fixed, and this contradicted
   decision 9 as written.** The picker only renders cards that exist in the
   catalog, so a phantom id could never be deselected: the 404 banner opened the
   picker, but the offending card was not in it, and every subsequent request
   404'd forever. Now unknown ids are separated from the wallet before pricing:
   the rest of the wallet is priced normally, an explicit notice names how many
   cards dropped out, and a **"Remove it/them"** button prunes them. A **"Clear
   my wallet"** affordance was added to the editor as the blunt escape hatch.
   The engine still fails loudly on an unknown id — this only stops the UI from
   being a dead end.

4. **Ad-hoc red replaced with the `destructive` token** in Portfolio View and
   Best Card. The parent page (`cards/page.tsx`) was already using the token, so
   one page was rendering two different error treatments.

5. **The Phase-1 caveat was easy to miss — fixed.** It existed only as fine
   print below (for a 9-card wallet) roughly 11,000px of page. A short version
   now sits directly under the summary tiles, where the numbers are first read;
   the full sentence still closes the page.

6. Polish taken: `quarterly_cap_inr` / `annual_cap_inr` were fetched but never
   rendered — latent, since no seed row sets them today, but a quarterly-capped
   card would have had its cap silently disappear. All three periods now render.

**Noted, not done:** the reviewer's suggestion that wallets larger than ~5 cards
might be better served by a "your card vs. the best card" comparison than a full
N-column grid, and that the always-expanded per-card panels read as a reference
appendix at 9 cards. Both are real design questions rather than defects; the
typical wallet is 2–4 cards, and the sticky column plus scroll affordance makes
the 9-card case workable. **Revisit if real wallets turn out to be large** —
the mobile-first pass later in Phase 1 is the natural place.

All fixes re-verified in a real browser at both viewports: sticky column holds,
fade appears and clears correctly, stale-wallet recovery works end to end, clear
wallet returns the empty state, no page overflow, no console errors.
