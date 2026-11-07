# Decision Log: Best Card answers every program, knows how you pay, and explains itself

**Date:** 2026-11-07
**Area:** Reward Knowledge (schema: `requires_portal`), Valuation (`best_card.py`), API (Best Card provenance, saved-goal `partner_id`), frontend (`best-card.tsx`)
**Follows:** user feedback that Best Card "feels too naive" (2026-11-07). The roadmap's original Best Card scope note already asked for this depth.

## Context

The user found Best Card too naive. Four concrete gaps:

1. **No answer until the user picked a transfer program.** The default view listed points across currencies and said, honestly, "these aren't the same unit". It was correct, and it did not help.
2. **Portal-only bonus rates were priced as if they applied everywhere.** Infinia and Diners Black earn 16.65/₹100 on travel only when booked on HDFC SmartBuy. Magnus Burgundy's 30.00 applies only on Axis Travel EDGE. A direct airline booking earns the base rate. The condition existed only inside the free-text `category_label`, so Best Card overstated direct bookings by about 5×.
3. **Explanation was thin.** There was no margin over the runner-up and no per-card reason. Once the 2026-11-06 zero-earn rows landed, a 0-point "winner" was named by card-name tiebreak.
4. **Monthly caps were assumed unused** even though the activity log now has spend. The user deferred this one.

The user chose items 1–3.

## Decisions

1. **`RewardCategoryRule.requires_portal`** (migration 0011) records the booking channel a bonus rate needs. NULL means the rate applies however you pay.
   - Seeded on exactly three rules: Infinia and Diners Black travel (HDFC SmartBuy) and Magnus Burgundy travel (Axis Travel EDGE).
   - Atlas is deliberately not gated: its travel rate also covers direct airline and hotel bookings. TravelOne's rate applies to any airline or aggregator MCC.
   - **CR-04** rejects a portal on a non-bonus rule, which would price a phantom direct alternative. It also rejects a blank name.
2. **Every option is priced two ways.** Through the portal (the best case, and the ranking basis) and booked direct, where the gated rule does not apply and the card earns its base rate, uncapped.
3. **`program_verdicts`: one answer per program the wallet reaches, each in that program's own unit.** This is how Best Card answers without being told a program. It still never compares across currencies and never invents a ₹-per-point value, so CLAUDE.md's *Never Assume the User's Goal* holds.
   - A verdict carries the winner, the runner-up and the lead in program units.
   - `tied` is set when the lead is 0. A tiebreak is not advice.
   - The winner is null when nobody earns there.
   - `direct_winner` appears only when the winner's rate needs a portal.
4. **A goal the user set may lead, but never select.** The saved-goals list now exposes `partner_id`. Best Card sorts that program first with a "Your goal" badge. That program was chosen by the user, which CLAUDE.md permits. It is never selected on their behalf.
5. **`no_card_earns`:** when nothing in the wallet earns on the spend, the page says so ("None of your cards earn rewards on fuel") instead of crowning a 0.
6. **Provenance is wired into Best Card**, following Portfolio's convention.
   - `unverified_ids` flags each option and pick: its rule (or the card row when the base rate applies), plus its link, currency and partner. The UI marks those figures with `*`.
   - The ETag includes the provenance tier digest.
   - **The policy question is still open.** Should Best Card *withhold* an unverified winner, as Portfolio does? On today's seeds that would withhold the flagship answer (Infinia's SmartBuy rate is still flagged). This change marks unverified winners and does not withhold them; the user needs to decide.
7. **The "why" lives in the payload.** Each option carries rate, label, portal, direct figure, ratio and cap, and the UI composes one reason line from those fields. No figure is generated outside the engine.

## Changes from review (backend-reviewer, 2026-11-07)

- **`no_card_earns` is decided on rates, not floored points**, across routable and unroutable cards. Two cases were wrong before: a wallet that simply couldn't reach the chosen program was told "none of your cards earn", and so was a ₹20 spend that rounds to 0. Tiny spends now get a separate `too_small` verdict state ("too small to earn a whole mile").
- **Direct-booking ties are marked** (`direct_tied`). When cards tie at the top, a direct alternative is owed if *any* of the tied cards needs a portal. Name order no longer decides whether the user is told.
- **The direct figure has its own provenance** (`direct_needs_verification`). It rests on the card row (base rate), not on the portal rule. The card row also counts whenever the base rate takes part in a figure, such as overflow past a cap. Options and picks share one convention: rule, card when the base rate is involved, link, currency and partner.
- **Fail-open guard.** A NULL `requires_portal` means "applies however you pay", so a migrated-but-not-reseeded DB would silently re-introduce the overstatement. Two guards now catch this:
  - `deps.warn_on_seed_version_drift` logs at startup when the DB snapshot's content version differs from the reviewed seeds'. After a reseed they are equal; this was checked live.
  - A test asserts that every `RewardCategoryRule` field is in both the snapshot SELECT and the catalog upsert.
- **Smaller changes:**
  - The Best Card ETag includes `ENGINE_VERSION`.
  - Sort keys end in `card_id`.
  - `partner_reach` is computed once.
  - `SavedGoalSummary.partner_id` is required.
  - The UI says "booking directly with the airline or hotel" (the model has no OTA channel).
  - A capped base-level rate is no longer called a "bonus".
  - `db-schema-v1.md` is amended for 0011.

## Changes from review (frontend-reviewer, 2026-11-07, driven in a real browser)

- **Ties kept the portal warning.** Tied verdicts dropped "Book via HDFC SmartBuy" and the `*`, which reintroduced the overstatement this change exists to fix. Ties now render the same detail lines as wins: a per-card portal note, the unverified mark, and the direct-booking alternative.
- **Program-scoped "nobody earns" no longer gives false advice.** It says "None of your cards that reach Marriott Bonvoy earn…" and points to cards without a route, which may still earn. It no longer says "any card is as good as another".
- **Navigation.** There is an "← All programs" control above the hero. Focus and scroll move to the result whenever the shown program changes, so keyboard users are no longer dropped at `<body>` and the page doesn't leave mobile users in the footer.
- **`ProgramChooser` copy.** The shared chooser no longer hard-codes "miles" for hotel programs. Best Card hides its wallet-wide "best route" line, which contradicted the hero's per-card ratio. The dropped space in the chip and badge accessible names is fixed.
- **Copy:**
  - The hotel "worth knowing" note is reworded.
  - The dangling "the answers above settle" note is fixed.
  - Footnote contrast now meets AA.
  - "caps assumed unused **before this purchase**".
  - "1 mile", not "1 miles".
  - "The only card that earns here" when the runner-up earns 0.
  - Singular copy for one-card wallets.
  - Section titles are headings.

## Redesign: card-first (user feedback, 2026-11-07)

The user found the program-first verdict list vague. "The only card that reaches it — reaches where?" The page answered "which program" when the user asked "which card". They also asked that, with no cards picked, the page show every card in order. The changes:

- **The engine now answers per card.**
  - `CardSpendOption.destinations` lists every program the card transfers to, with what this spend becomes there (portal and direct), the ratio and provenance.
  - `best_for` lists the programs where it is the top card, ties included.
  - `overall_pick` names the sole top card in every program where anyone earns, when there is one.
- **Points-mode order is by programs won**, then best placing anywhere, then name. Cards that transfer nowhere come last. This replaces the old order by raw points across currencies: in a wallet of TravelOne, Atlas and Regalia Gold it put Regalia first, though Regalia is the top card nowhere. `test_no_assumed_program` is rewritten to the new rule.
- **The UI leads with one plain answer.**
  - "Use Axis Atlas — it's the only card you've picked. ₹10,000 of everyday spend earns 200 EDGE Miles, at 2 per ₹100. Atlas can move these to one program only — KrisFlyer (Singapore Airlines) — where they become 400 miles (1:2)."
  - Or: "Use Infinia — whichever program you send the points to, it gives you the most", with the SmartBuy condition and what to use instead when booking directly.
  - Or: "It depends on where you'll use the points", with one line per program. Airlines come before hotels and the user's goal comes first. A "Not sure yet? TravelOne is best for 2 of 4" hint is shown when one card tops the most programs.
- **A numbered "Your cards, in order" list.** Each card states what it earns, any portal condition and cap, what its points become in each program (each figure `*`-marked if unverified), and what it is best for.
- **No cards picked → all 9 cards we cover** are compared, with a banner saying so. Cards closed to new applicants are labelled.

## Bug: stale cached responses crashed the redesigned page (2026-11-07)

**Symptom.** In the user's browser, Best Card showed "Uncaught TypeError: Cannot read properties of undefined (reading 'split')".

**Root cause.** The ETags for Best Card, Portfolio and the catalog were built only from data: snapshot version, provenance digest, query and the static `ENGINE_VERSION`. The redesign added response fields without changing any of those. The browser revalidated, got 304, and handed the new UI the pre-redesign body, which had no `partner_name`. The backend reviewer had flagged this risk; adding `ENGINE_VERSION` was not enough, because nothing bumps it for changes like this.

**Reproduction.** A pre-redesign ETag returned 304. Feeding the page a payload stripped of the new fields reproduced the exact error.

**Fix.** `deps.payload_digest(model, *modules)` is a sha256 of the response model's JSON schema plus the source of the modules that compute it. It is deterministic across workers and is now part of the ETag on `/v1/best-card`, `/v1/portfolio`, `/v1/catalog/cards` and `/v1/catalog/routes`. Any change to a payload's shape or logic now invalidates cached copies.

**Regression tests.** `tests/unit/api/test_etag_payload_digest.py` checks four things:
- the digest varies with shape and with code
- the digest is deterministic
- the pre-fix ETag now gets 200
- all four ETags carry their digest

**Verified live.** The user's old ETag gets a 200 with the new fields, and the new ETag still gets a 304.

## Card-first review round (frontend-reviewer, 48+ wallets driven, 2026-11-07)

**Engine.** A tied card was pushed down the order by its name-tiebreak position. Diners and Infinia tied for "Best for Maharaja" yet were numbered #1 and #5. Two fixes:
- Placing is now competition-style from the figures: the number of cards that earn strictly more.
- A new `order_position` field gives dense, shared numbers (1, 1, 2).

Both are pinned by tests.

**UI.** All twelve important findings were fixed:
- A glued word ("Atlas— it's") is gone.
- The "booking directly?" box no longer names the pick as its own alternative.
- "It depends" is no longer shown when ties are identical everywhere: the answer is now **grouped by card** ("Either Diners or Infinia: …").
- The old result keeps the labels it was computed for while a new one loads, and it dims.
- On mobile the picker collapses to a summary and the spacing is tightened, so "Use X" sits on the first screen at 390×844.
- Nothing is said twice: the answer panel covers the picked card(s) and the list shows "Your other cards".
- The chooser is hidden where it was redundant or a dead end, uses friendly program names and no "via N cards".
- A ₹20 spend shows one "too small" message, not a winner at 0.
- Answer rows carry the bank name and the "not open to new applicants" label.
- The portal condition sits in the headline ("Use HDFC Infinia Metal — booked through HDFC SmartBuy").
- Copy:
  - rates carry units ("2 EDGE Miles per ₹100", "1% back")
  - programs are named in their own units ("KrisFlyer miles", "Accor points")
  - cashback is shown as rupees
  - "Sending points to …"
  - the intro is rewritten
  - no "any card is as good as another" overclaim
- Accessibility: a short `aria-live` status replaces the live region that wrapped the whole result. The answer is the `h2`. Program buttons say they open the full working.

## Not done / known gaps

- **Deferred UI polish from review:** verdict order is alphabetical (consider ordering by reach or grouping repeated winners), there is no pressed/pending state on drill-in, the live region wraps the whole result, and a raw 422 shows on absurd amounts.
- **Logged-spend cap utilisation and milestone proximity.** The user deferred this. The data exists (`simulation/observed.py`).
- **Stages 5–9 still price travel at the portal rate.** The goal engine assumes the user books through the portal. That is now a known, documented assumption rather than a hidden one, but it is not yet surfaced or modelled in strategies.
- **The HDFC SmartBuy multipliers themselves are still flagged**, because HDFC is unreachable to automated fetches (see 2026-11-06).

## Verification

- Backend:
  - 21 verdict and portal tests, hand-computed from the seeds (e.g. KrisFlyer on ₹10,000 travel: Infinia 1,665 via SmartBuy, Atlas 1,000, lead 665; booked direct, Atlas wins at 1,000 against Infinia's 333)
  - 2 CR-04 tests, 1 seed golden, plus saved-goal `partner_id` mapping
  - Suite 742 → 768 after review fixes. mypy strict and ruff are clean.
- Live DB: migration 0011 applied and seeds reloaded (user-approved 2026-11-07). The live endpoint returns the same figures as the goldens.
- Frontend: tsc and eslint are clean. Driven headless at 1440×900 and 390×844 for:
  - points view
  - priced view
  - tie
  - nobody earns

  No horizontal overflow and no console errors. A JSX-dropped space ("fuelspend") was found this way and fixed.
