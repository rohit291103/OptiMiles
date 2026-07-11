# Decision Log — Dashboard Polish + Saved-Goal Delete

**Date:** 2026-07-10
**Area:** frontend / backend

## Context

The user walked through the revamped dashboard (same-day: `2026-07-10-dashboard-revamp-and-goal-detail.md`) and gave feedback: the top-bar and sidebar text read too small, the focus-goal hero should sit *below* the stat tiles, the stat numbers deserved more visual weight, the goal grid should fit 2–3 per row, and each goal card needed an action menu (download / delete / etc.). Deleting a saved goal had no backend support at all — the API surface was create + read only.

## Decisions

1. **`DELETE /goals/{goal_id}` deletes the whole persisted lineage, not just the goal row.** Migration `0001`'s FKs pointing at `user_goals` are `ON DELETE SET NULL` from `spend_simulations`/`recommendation_outputs` but **`NO ACTION` from `simulation_results.goal_id`** — so a bare goal delete would either strand lineage rows with NULL goal ids or be rejected outright. `delete_goal_lineage` (in `repositories/results.py`, which stays the sole writer of user-result tables) deletes child-first in one transaction: `recommendation_outputs` → `simulation_results` → `spend_simulations` → `user_goals`.
2. **`simulation_results` gets its own explicit DELETE rather than trusting the cascade from `spend_simulations`.** The cascade only covers it when a result's `goal_id` matches its parent simulation's — an unenforced invariant of `persist_recommendation` that a future writer could silently break (backend-reviewer finding, applied). We deleted defensively instead of amending the migration, because the schema is live on Supabase with real rows.
3. **Every DELETE statement is scoped to the caller.** `simulation_results` has no `user_id` column, so its statement scopes through goal ownership (`USING user_goals ... AND g.user_id = :user_id`). Unknown id and someone else's goal are the same 404, matching the read endpoints. Verified against the live DB inside a rolled-back transaction: full lineage clears with no FK errors, a foreign user's delete touches nothing, rollback restored all rows.
4. **Dashboard layout reordered: stat tiles above the focus-goal hero,** with larger tabular-nums values and unit suffixes ("goals" / "miles"). The "All goals" grid now shows **all** goals (it previously hid the focus goal, making the "Saved goals" count disagree with the visible cards) at 1/2/3 columns (base/sm/xl).
5. **Per-goal three-dot menu** on each grid card: View strategy, Download strategy (exports the stored `GET /goals/{id}` payload as JSON — a client-side re-serialization, no new endpoint), and Delete with a two-step in-menu confirm (no native `window.confirm`, which clashes with the dark theme). Cards use a stretched-link pattern so the whole card navigates while the menu sits above it at `z-10`.
6. **App-shell typography scaled up** per user feedback: top-bar title in the heading serif at `text-lg sm:text-xl`, "+ New goal" at default button size, sidebar `w-64` with `text-[15px]` nav and 18px icons.
7. **Mobile overflow fix (frontend-reviewer finding, applied):** the goal grid needed an explicit base `grid-cols-1` — without it the implicit column auto-sizes to content width (928px on a 390px viewport), breaking `truncate` and pushing the new menu off-canvas. This bug predated the session but was fixed here.

## Not done (deferred)

- **No automated real-DB test for the delete** — same standing gap as `persist_recommendation`; the live-DB check was manual (rollback-protected script). Covered by the existing "automated real-DB round-trip test" tracker item.
- **Badge/menu a11y association on goal cards** (reviewer optional, low confidence): the status badge isn't tied to the card via `aria-describedby`. Consciously skipped as polish.
- The migration-level fix (making `simulation_results.goal_id` `ON DELETE CASCADE`) was deliberately not taken — defensive delete chosen over touching a live schema.
