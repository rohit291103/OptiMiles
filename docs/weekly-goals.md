# OptiMiles — Weekly Goals

This file holds the plan for the current week: one goal, split into about four build sessions of roughly an hour each. It sits between two other docs:

- [`tracker.md`](tracker.md) is the current state of the whole project (what is built, what is next).
- [`decisions/`](decisions/) records *why* things were decided, and is never rewritten.
- This file says which slice of the tracker's "Next up" we are building this week, and what "done" looks like for each session.

**How it is maintained** (by the `tracker-sync` skill, alongside the tracker):

- **Start of a session:** read the current week and pick up the next unchecked session.
- **End of a session:** tick its *Done when* boxes, note anything that slipped under that session, and refresh the tracker as usual.
- **End of the week:** add one line to *Past weeks* (goal, outcome, what carried over), then replace the plan with next week's. The full detail of a finished week lives in git and the decision logs, not here.

---

## Week 47 · 16–22 Nov 2026 — "Verified by Default"

**Goal:** by the end of the week, nothing the product recommends is built from unverified data. Unverified figures are still shown, but they are labelled and never chosen as the answer. The catalog can also hold unverified "Listed" cards, so adding cards can start next week without weakening that rule.

**Why this is the goal:** root `CLAUDE.md` says no optimization recommendation may be built from unverified rows. Today only Portfolio View's category leader follows that rule. Best Card and the goal engine still optimise over the 30 flagged seed rows (status review, 2026-11-16).

**Why this order:** all 5 KrisFlyer award-chart rows are flagged, and 8 of the 9 cards have at least one flagged row. Switching the rule on first would stop every goal from working. So we verify first, then enforce, then open the Listed tier.

### Prep before Session 1 (you, about 20 min)

- [ ] Have these pages open in a normal browser (they block automated fetches): the KrisFlyer award chart, the HDFC SmartBuy T&C (Infinia / Diners Black), and Axis Travel EDGE (Magnus Burgundy earn table and the 5:4 ratio).
- [ ] Run the Gemini research prompt for Session 4: [`prompts/listed-card-research-prompt-v1.md`](prompts/listed-card-research-prompt-v1.md). Its output goes to `research/listed-card-candidates-v1.md`.

### Session 1 — Verify what the bots couldn't read · ◐ PARTLY DONE (ran 2026-11-16, 4 leftovers for the weekend)

**What we'll achieve:** the launch blockers are cleared, and the rows the goal engine depends on most are verified.

| Time | Activity |
|---|---|
| 10 min | **You:** publish the Google OAuth consent screen, set the Supabase Auth Site URL and the `https://opti-miles.vercel.app/**` redirect, and add the LLM key and `LLM_MODEL` to Render. **Claude:** check sign-in and the LLM-written summary on the live site. |
| 40 min | **Together:** you paste the relevant page text, and Claude updates the seed YAML with `source` + `verified_on`, then runs `validate_catalog()` and the tests. Order: the 5 KrisFlyer award-chart rows, then the Infinia/DCB SmartBuy caps, then Burgundy's earn table and 5:4 ratio. |
| 10 min | Reload the live DB (with your approval), then refresh the tracker. |

**Done when:**
- [ ] The KrisFlyer award-chart rows are verified or corrected. **Partly (2026-11-16):** the 3 India → Singapore rows are verified, and all 5 have their unsourced taxes removed. London and New York cannot be verified from the airline's calculator, which only prices nonstops, so they stay flagged.
- [ ] Flagged rows drop from 30 to about 18. **At 25.** About 20 once Axis is done. The ~18 target assumed London and New York would clear.
- [ ] A Google account that is not a test user can sign in on the live site. OAuth is published and Supabase URLs are set; the sign-in itself hasn't been tried yet.

**Ran 2026-11-16.** Also done: the HDFC SmartBuy rows were verified from HDFC's own PDFs, and three wrong numbers were fixed (points expiry, and fuel for Infinia and Diners Black). Decision log: `decisions/2026-11-16-issuer-verification-krisflyer-hdfc.md`.

**Left over, for the weekend (finish before Session 2):**
1. Axis Burgundy + Atlas (5 rows): put the Axis T&C PDFs in `TnC-docs/Axis/`.
2. Render: `LLM_API_KEY` + `LLM_MODEL=openai/gpt-4o-mini`. Then Claude checks that `model_version` is no longer `template-fallback`.
3. Sign in once with a Google account that is not a test user.
4. Reload the live DB (`seeds/load_to_db.py`) **before** pushing the backend, then commit.

### Session 2 — Never pick an unverified winner (Best Card and Portfolio) · ✅ DONE (2026-11-17)

**What we'll achieve:** the rule holds on the daily-use pages.

| Time | Activity |
|---|---|
| 10 min | Lock the decision. **Recommended:** an unverified figure stays visible with a label but is never the answer. The answer is the best *verified* card, plus a note such as "Infinia may earn more via SmartBuy (unverified)". |
| 35 min | Test-first change to `valuation/best_card.py`: the overall pick, the per-program winners and ties all skip unverified rows. Align Portfolio View's wording (it already withholds the category leader). |
| 15 min | UI wording, a quick `backend-reviewer` and `frontend-reviewer` pass, and a decision log entry. |

**Done when:**
- [x] A test proves an unverified row can never be Best Card's answer. (`test_best_card_verified_only.py`, including a property test over the real seed flags.)
- [x] ~~The page says why a card with a higher but unverified figure wasn't picked.~~ **Changed by the user:** there is no "may earn more" hint. The page names what it left out ("Not compared"), with no figures.

**Ran 2026-11-17.** The user locked a stricter version of the rule: unverified figures are removed, not labelled, and the team verifies rows on its own schedule. Portfolio was not changed: it already names no leader when the top figure is unverified. Two Portfolio questions are open (see the tracker). Decision log: `decisions/2026-11-17-best-card-verified-only.md`.

### Session 3 — Apply the rule in the goal engine

**What we'll achieve:** goal strategies are built only from verified data, and they say what was left out.

| Time | Activity |
|---|---|
| 15 min | Make the unverified flag reach the engine's input data (the snapshot / `PlanningContext`). Today only the API layer reads it, through `load_unverified_ids()`. |
| 30 min | Test-first: Stage 5 skips unverified earn rules and transfer links; unverified award-chart rows are refused or clearly labelled; the strategy output lists what was "not used: unverified". |
| 15 min | Keep the same-input-same-output (determinism) test passing, run `backend-reviewer`, and write a decision log entry. |

**Done when:**
- [ ] A test shows an unverified rate left out of a strategy and named in its output.
- [ ] The determinism test still passes.

**Risk:** if Session 1 doesn't clear the KrisFlyer award-chart rows, enforcing the rule here would stop every goal. The fallback is to label chart-based numbers "unverified" for now rather than refuse. Decide this at the start of the session.
*Update after Session 1:* Singapore is cleared. Only **London and New York** goals still rest on unverified chart rows, so the decision now covers just those two routes.

### Session 4 — Open the Listed tier

**What we'll achieve:** the catalog can hold cards that appear in browse but are never recommended.

| Time | Activity |
|---|---|
| 15 min | Settle the words (Verified / Listed / Not covered) and where the tier is stored, using the `domain-modeling` skill. |
| 30 min | Test-first: Listed cards load into the catalog, and no engine path can use them (enforced by a `validate_catalog()` check and a test). `/cards` browse shows them as "Unverified — not used for recommendations". |
| 15 min | Seed 1–2 Listed cards from the Gemini research brief, then update the tracker and the docs. |

**Done when:**
- [ ] A Listed card appears in `/cards` browse with its label.
- [ ] A test proves no engine path can recommend a Listed card.

### Not this week

These are candidates for next week's goal: sourced ₹-per-point values, new transfer partners for the currencies we already have, and statement/CSV upload with actual-vs-projected progress (roadmap Phase 2).

---

## Past weeks

| Week | Goal | Outcome | Carried over |
|---|---|---|---|
| — | — | — | — |
