# Decision Log — Scope broadening + never assume the user's program

**Date:** 2026-08-26 (third sitting)
**Area:** product scope / frontend / backend API
**Supersedes:** the "MVP Philosophy", "Initial MVP Scope" and card-count exclusions in root `CLAUDE.md`
**Relationship to the roadmap:** `docs/prd/product-roadmap-v1.md` still governs *what gets built and in what order*. This document governs *how wide the product reaches*, and wins where the two disagree on coverage.

## Context — two things happened together

**1. A real defect, found by the user.** Best Card showed:

> Axis Atlas — Earns **200 EDGE Miles** on ₹10,000 — **about 400 KrisFlyer miles**

on a page where the user had never mentioned Singapore Airlines, never set a goal, and was never offered a choice. The same assumption ran through Portfolio View. The user's words: *"stop this everywhere KrisFlyer miles, I see even why in the image you are talking about KrisFlyer if nobody asked or mentioned."*

**2. The MVP is declared over.** The goal is no longer one airline. The product must be **valuable, informative and comprehensive** across the Indian rewards ecosystem, and must compete with PointsFly on coverage.

These are the same problem at two scales. The KrisFlyer default was not a coding slip — it was `CLAUDE.md` telling the code that KrisFlyer is primary, and the code faithfully repeating it to a user who had said nothing of the kind.

## How the defect actually happened, traced

1. `CLAUDE.md` → *Primary MVP Goal*: "Singapore Airlines business-class optimization"; *Initial Focus Areas*: "KrisFlyer transfer ecosystem".
2. Best Card's design problem: points across issuers are genuinely incommensurable (HDFC RP, EDGE Miles, MR are different units) and the catalog carries **no ₹-per-point valuation** — inventing one would violate the seed policy. Ranking needs a common unit; a transfer program is the only honest one available. So the feature was made goal-relative, **defaulting to the program the scope document named primary**.
3. Portfolio View copied that default.
4. `GET /v1/best-card` and `GET /v1/portfolio` both already accepted `target_program_id` — **the frontend simply never sent it**, so the backend fell back to KrisFlyer and the UI printed the program name in bold as if it were the user's plan.

The engineering reasoning (step 2) was sound and stands. The failure was steps 3–4: an *internal* choice of unit was rendered as an *external* claim about the user's goal, with no way to change it.

## Decisions

1. **The MVP frame is retired.** Scope is now the Indian rewards ecosystem: broad card coverage, every meaningful transfer ecosystem, and informational depth sufficient to answer a rewards question that has no goal attached. `CLAUDE.md`'s "Build Narrow and Deep" section is replaced by **Scope: Breadth With Depth**.

2. **Breadth is governed by tiered coverage, not by a card count.** Breadth and line-by-line seed review do not scale together, and pretending otherwise is how a rewards product ends up confidently wrong. Three tiers, stated to the user, never a silent quality gradient:
   - **Verified** — full review bar, `source` + `verified_on`. **The only tier optimization output may be built from.**
   - **Listed** — broader coverage from published sources, `needs_verification: true`, usable for informational surfaces with the UI saying so.
   - **Not covered** — said plainly. "We don't cover that card yet" is an acceptable answer; a guess is not.

3. **Never assume the user's target program.** Surfaces default to what the catalog states directly — points earned, earn rates, caps, benefits. A target program is **chosen by the user** or inherited from a goal they actually set. Where none is chosen, the product says the cards are not comparable and offers the choice. A program name appears in the UI only when the user put it there.

4. **The Best Card flow becomes three steps, per the user's own description:**
   1. **Points first** — what each card earns for this spend, in its own currency, with the earn rate and the maths. **No single winner is crowned here**, because across currencies there is no honest winner yet.
   2. **Ask** — "want to see what these are worth if you transfer?"
   3. **User picks the partner** — only partners actually reachable from their wallet are offered — and *then* the ranking, the winner, and the runner-up reasoning appear, in the unit they chose.

   Portfolio View follows the same shape: points and earn rates by default, with a partner selector that switches the comparison into miles.

5. **"Best available partner" is NOT offered.** It sounds obvious and it is not computable: 333 KrisFlyer miles vs 166 Marriott Bonvoy points are no more comparable than the source currencies were. Offering it would smuggle back the exact assumption we are removing.

6. **Rupee value / "max return" is deferred, not refused.** The user asked for value and return, and it is the right ask — but it needs a **₹-per-point valuation per currency**, which the catalog deliberately does not have. Seeding sourced valuations (with `source` + `verified_on`, at the transfer-ratio review bar) is now a standing priority. **Inventing a valuation to unblock a UI is forbidden** — it would be the one number in the product with nothing behind it, in the surface users trust most.

## Consequences

- `target_program_id` becomes genuinely optional end to end: engines and endpoints must return a coherent points-only answer when no program is chosen, rather than substituting a default.
- With no target chosen, Portfolio View's category comparison has **no leader** — that is correct, and the UI must say why rather than showing a blank.
- Coverage note that shapes the partner chooser: the catalog holds four partners (KrisFlyer, Maharaja Club, Marriott Bonvoy, Accor ALL) and they are **not evenly reachable** — both Axis currencies reach only KrisFlyer, and Maharaja Club is reachable only from HDFC's Infinia/Diners tier. The chooser must therefore offer only what the user's own wallet can reach, or it will present dead ends.
- Expanding partner coverage is now a first-class catalog priority, because a partner chooser is only as good as the list behind it.

---

# What shipped (same session)

**Backend**

- `app/valuation/wallet.py` (new) — the shared vocabulary both priced surfaces
  needed: `UnknownCard`, `resolve_wallet()`, `partner_reach()`,
  `resolve_target()`. Extracting it removed a would-be import cycle
  (`portfolio` already imported `UnknownCard` from `best_card`) and put the
  "which programmes can this wallet actually reach" logic in one place, since
  it is now what both choosers are built from.
- `valuation/best_card.py` — `target_program_id` is optional. With none:
  `ranking_basis="points"`, every miles figure `None`, nothing in
  `unroutable` (there is no route being asked about), and `partner_reach`
  filled in. With one: unchanged miles ranking. The `ranking_basis` field
  exists so a client cannot mistake the points listing for a ranking.
- `valuation/portfolio.py` — same shape. With no programme: `reaches_target`
  is `None` (not `False`, which would read as "no route" — a claim nobody
  asked us to make), `cards_reaching_target` is `None`, and **no category has
  a leader**.
- `api/best_card.py`, `api/portfolio.py` — the `_DEFAULT_PROGRAM = "KrisFlyer"`
  constant and its `_default_program_id()` helper are **deleted**. This is the
  actual site of the bug.
- Tests: `tests/unit/valuation/test_no_assumed_program.py` (17) pins the whole
  contract, including that an Axis-only wallet is offered **only** KrisFlyer
  and a cashback-only wallet is offered nothing at all. The two endpoint tests
  that asserted the old KrisFlyer default were rewritten to assert its
  absence. Suite **483 passed**, mypy strict + ruff clean.

**Frontend**

- `components/ui/program-chooser.tsx` (new) — shared by both surfaces. Offers
  only reachable programmes; renders an honest empty state for a wallet with
  no transfer links at all; no "whichever is best" option, per decision 5.
- `best-card.tsx` — split into `PointsFirst` and `Priced`. Step 1 lists what
  each card earns in its own currency with the rate and cap, states plainly
  that the units are not comparable, and **crowns nobody**; the winner, the
  maths and the runner-up callout appear only after a programme is chosen.
- `portfolio-view.tsx` — the comparison table shows points per ₹100 with no
  gold leader until a programme is picked, and its heading changes from "What
  each card earns" to "Which card wins" at that moment. The two summary tiles
  that assumed a target now answer the question that is well-posed without one
  ("programmes reachable", "transferable cards").

Verified in a real browser at 1440×900 and 390×844: with nothing chosen,
"KrisFlyer" appears **only as one of four options**, never as an assertion; an
Axis-only wallet is offered only KrisFlyer; a cashback-only wallet is told
there is no transfer question to ask; choosing Marriott Bonvoy reprices the
whole wallet and names a leader. No console errors, no page overflow.

**Not shipped, and named as such:** the rupee-value / "max return" column, per
decision 6 — it is blocked on sourced ₹-per-point valuations, not on UI work.
