# Decision Log — Logged progress in Portfolio View, and the "Unverified" label

**Date:** 2026-11-02
**Area:** Valuation Engine (portfolio read) / Knowledge (seed provenance) / API / frontend
**Follows:** `2026-09-02-activity-log-unified.md` → "Next: wire the summary into Portfolio View"; `2026-08-26-portfolio-view-and-shared-wallet.md` decision 3

## Context

`/cards` showed caps and milestone thresholds as targets only, with `spend_data_available: false` and a "targets, not progress" line. The activity log now has the data (`GET /v1/activity/summary`, `simulation/observed.py`). Separately, nothing in the product could label Listed-tier rows. `needs_verification` was dropped by the seed loader and never reached the DB or the snapshot, so the tiered-coverage rule ("the UI must say it is unverified") could not be met on any surface.

## Decisions

1. **The frontend puts the two responses together. The backend does not embed progress in `/v1/portfolio`.**
   - `/v1/portfolio` stays anonymous, ETag'd and a pure function of the catalog. Embedding the log would make it auth-dependent, date-dependent and uncacheable, and would couple two endpoints that answer different questions.
   - Both engines stay pure (build rule 3). `build_portfolio` reads no log, and `observe()` gains no pricing. The page joins **caps on (card_id, category_slug)**, which is unique per card by seed id, and **milestones on `milestone_id`**. `milestone_id` was added to `PortfolioMilestone` for this join, because two milestones can share a threshold.
   - The honesty model stays where it was built. The UI renders the summary's own bound-named fields (`remaining_inr_at_most`, `ObservedStatus`) and its caveat, so this work adds no new bound logic.

2. **Progress renders only for a signed-in user who has logged something.** With no session, a failed summary, or an empty log, the page keeps the "targets, not progress" line. A page full of "₹0 of ₹1,50,000" rows for someone who never opened the log would be noise, not a lower bound worth showing.

3. **The copy follows the lower-bound model.**
   - A milestone reads "your log shows ₹X in 2026 — past the ₹T threshold" or "₹Y more to log before we can confirm it". It never reads "missed" or "not reached".
   - Cap headroom is "at most".
   - Every calendar-window row says it "may differ from your statement cycle".
   - Percentages are floored from the integer rupee amounts, not taken from the rounded `fraction_used_at_least`. That way an "at least" figure can never round up.

4. **Provenance reaches the read surface through a YAML index. There is no DB column.** `knowledge/seed_catalog.load_unverified_ids()` returns the deterministic ids of every row flagged `needs_verification: true`, using the same keys as `load_seed_snapshot`. Drift guards check that every flagged id is a real snapshot row and that every flag line is counted. This follows the seeds README ("provenance stays in the reviewed YAML") and needs no migration.
   - The API reads it once per process through `deps.get_unverified_ids` (setting `seed_dir`). If the directory is missing, the call raises rather than returning an empty set, because an empty set would label every row verified.
   - `build_portfolio(..., unverified_ids=...)` is **required, not defaulted**, for the same reason.
   - The portfolio ETag now includes a digest of the tier. A row can be verified without any of its values changing, and the old tag would then serve the stale label as a 304.

5. **Flags do not inherit.** A card-level flag covers the panel header's facts: the card row or its currency. A lounge tier is flagged if its own row or its programme's row is flagged. A category-table cell follows the row its rate came from: the category rule, or the card row when the cell falls back to the base rate.

## Review round (same day)

`backend-reviewer` and `frontend-reviewer` were run on the work above. Their findings, and what was done about each:

6. **Derived figures inherit every upstream flag.** A miles figure is rate × the target link's ratio, and the link belongs to a currency. So `miles_per_100` on earn rules and category cells, and `bonus_miles` on milestones, are unverified whenever the rate's row, the target link or its currency is unverified. This only applies when a programme is chosen, because without one there is no derived figure.
   - A transfer link is unverified if its own row or its partner's row is.
   - `PartnerReach.needs_verification` is true if the partner or any contributing link is unverified.
   - Best Card has no provenance index wired yet. It passes `unverified_ids=None` and gets `null`, meaning "not assessed". That is deliberately not `false`.

7. **"Which card wins" is never decided by an unverified row.** If the would-be winner is unverified, `leader_card_id` is `null` and `leader_withheld_unverified` is true, and the table says "No verified leader".
   - **A verified runner-up is not promoted in its place.** This is stricter than "exclude flagged rows and rank the rest". That alternative would highlight a smaller number next to a larger one and call it the winner.
   - A verified winner still leads over an unverified runner-up, because its lead does not depend on the runner-up's number being right.
   - On today's seeds, a KrisFlyer-priced Infinia + Atlas + Regalia wallet gets no verified leader in either category. Atlas's KrisFlyer link is flagged, and so is Infinia's SmartBuy travel rule.

8. **Provenance fails closed and is guarded against drift.**
   - A non-boolean `needs_verification` (for example a quoted `"true"`) is a load error.
   - A guard test fails if `CatalogSnapshot` gains a row collection that `PROVENANCE_COLLECTIONS` does not cover.
   - The count test parses the YAML at every depth.
   - At first snapshot load the API logs a warning for any flagged id the DB snapshot does not contain.
   - The tier digest used in the ETag is cached. **Changing a flag in the YAML takes effect only after a process restart.**

9. **Frontend fixes.**
   - "Used up this cap" is hedged when the reset anchor is assumed, and "At least 0% used" is dropped.
   - The summary is keyed on the live session identity and cleared when it changes. On a shared device, one person's progress is never shown to the next.
   - New states for signed out, session expired (401) and other errors; the error state has a retry button and a link to the log.
   - The decorative asterisks are `aria-hidden`, and the new pill text stays at 12px or larger.
   - The page uses its own lower-bound caveat. The activity API's caveat mentions lounge visits, which this page does not count.

## Follow-ups (not done here)

- `/activity` and Best Card do not yet show the Unverified label. `observe()` could take the same `unverified_ids`, and Best Card could wire the index the same way `/v1/portfolio` does.
- Lounge visits used are not yet attached to Portfolio View's lounge rows. `LoungeAllowanceUse` and `PortfolioLoungeAccess` share no row id, so the join would need one.
- `CapUse.fraction_used_at_least` is quantized with Decimal's default ROUND_HALF_EVEN, so it can round *up* (0.995 → 1.00). The UI no longer depends on it, but the field name promises a floor.
- `PortfolioCard.reaches_target` depends on a link existing, and carries no flag of its own. The link row itself is labelled.
