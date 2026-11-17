# Decision Log — Best Card answers from verified figures only

**Date:** 2026-11-17
**Area:** backend + frontend + product (Week 47 Session 2)

## Context

Root `CLAUDE.md` says no optimization recommendation may be built from unverified rows. Before this change, Best Card still ranked over the 25 seed rows flagged `needs_verification`. An unverified figure could win, and it was shown with a gold `*` and the footnote "treat that figure as indicative".

The weekly plan's recommended design was a softer version of the rule. The best *verified* card would be the answer, and a note such as "Infinia may earn more via SmartBuy (unverified)" would point at the higher unverified figure.

The user rejected that note. Their reasoning: if the product recommends from unverified data, there is no point to the product. Unverified data is removed from the answer, and the team checks sources and verifies rows on its own schedule. A row comes back into Best Card by being verified.

## Decisions

1. **An unverified figure is removed, not labelled.** When `unverified_ids` is supplied (the API always supplies it), `rank_cards_for_spend` builds a verified view before it prices anything (`_verified_view` in `backend/app/valuation/best_card.py`):
   - A card is left out entirely if its own earn on this purchase rests on a flagged row. That means the category rule, or the card row wherever the base rate takes part. This applies to the portal figure **or** the booked-direct figure: a card is in the answer only if every figure it would show is verified.
   - A transfer link is left out if its link, currency or partner row is flagged. The card keeps its verified points, but it cannot win, or be listed under, that program.
   - The rest of the function only ever sees the verified view, so an unverified figure cannot reach `ranked`, `unroutable`, `program_verdicts`, `destinations`, `partner_reach` or `overall_pick`.
2. **No "may earn more" note.** Nothing in the response or the page hints that an unverified card would have scored higher. The response carries `withheld`, a list of names only: the card, plus the program when only a transfer is unverified. The figure is never sent, so the page cannot show it or pick it.
3. **The page says what it did not compare.** A short "Not compared" note lists the withheld cards and transfers, without numbers, so a user's card doesn't silently vanish. This is the *Not covered: say so plainly* tier from `CLAUDE.md`.
4. **States that would become false claims are fixed:**
   - `no_card_earns` is never true while a card's earn is withheld, because we don't know what it earns. It is computed over every verified card's rate, including cards whose only withheld figure is their route to the chosen program.
   - A card whose route to the chosen program is withheld is not listed as `unroutable`. "Can't reach this program" would be false.
   - Page copy no longer says "the only card you've picked", "can't be transferred" or "none of these transfer" when the real reason is that something was withheld. When every picked card is withheld, the page says it can't answer yet.
5. **`None` still means not assessed.** Engine callers that pass no provenance withhold nothing. The API always passes it. The surviving options' `needs_verification` fields stay in the payload and are always `false` from `/v1/best-card`.
6. **A standing guard.** `test_with_the_real_seed_flags_every_figure_in_the_answer_is_verified` runs every card, every category and every target program against the real seed flags, and asserts that nothing in the result rests on a flagged row. If a future change lets an unverified row back in, this test fails.

### What the current seeds remove from Best Card (2026-11-17)

- **Magnus for Burgundy:** its earn is withheld in every category except fuel. The card row, the default rule and the Travel EDGE rule are all flagged. On fuel its earn is verified, but its route to KrisFlyer is withheld.
- **Platinum Charge:** its earn is withheld wherever its base rate applies. The card row is flagged *only* for `joining_fee_inr`; its earn rate was re-confirmed on 2026-11-06. See Not done.
- **TravelOne, travel only:** the travel rule (its cap) is flagged.
- **Atlas → KrisFlyer** and **every Regalia Gold transfer** (the `hdfc-rp-regalia` currency is flagged).

## Not done (deferred)

- **Provenance is per row, not per field.** A card row flagged for one fact, like Platinum Charge's joining fee, withholds the card's base-rate earn too. Two fixes, both open: settle the joining fee in the seed (the team verifies it, or records it as not stated), or split card-row provenance so the base rate has its own flag. Until then, the rule errs towards withholding.
- **Portfolio View** is unchanged. It already names no category leader when the top figure is unverified ("No verified leader"). It still shows unverified rates in its earn table with a `*` label, as information rather than recommendation. Two questions are open for the user:
  - Should the Portfolio leader become the best *verified* card, as in Best Card?
  - Should unverified rates be hidden from the table too?
- **Goal engine (Stages 5–9)** still optimises over flagged rows. That is Week 47 Session 3.
