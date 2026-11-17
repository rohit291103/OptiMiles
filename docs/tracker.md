# OptiMiles — Project Tracker

The current state of the project, not its history. This file is **overwritten in place** after any session that changes `backend/`, `frontend/` or `docs/`. Keep it lean:
- **Done** describes what exists now, one bullet per capability.
- The *why* lives in [`decisions/`](decisions/).
- The full history lives in git; the long pre-2026-11-16 version of this file is there too.

**This week's plan:** [`weekly-goals.md`](weekly-goals.md). Both files are maintained by the `tracker-sync` skill.

---

**Last updated:** 2026-11-17 — Week 47 Session 2: Best Card answers from verified figures only. Unverified rows are removed, not labelled. Seeds are still **ahead of the live DB**. Backend suite **797 passed**.

## Snapshot

**Post-MVP Expansion, broadened scope** (root `CLAUDE.md`, 2026-08-26). The MVP goal engine is built and user-tested. **Roadmap Phase 1 (Daily Surface) is complete** (2026-09-02). **Phase 2 has started:** manual spend and lounge logging are live; CSV upload, actual-vs-projected progress and alerts are not built. Phase 3 (Q&A) has not started.

The **broadened scope is not yet in the catalog**. It is still the MVP's 9 cards, 7 currencies, 4 transfer partners (KrisFlyer, Maharaja Club, Marriott Bonvoy, Accor) and 14 transfer links, with **25 rows flagged `needs_verification`** (down from 30 on 2026-11-16). The rule that no recommendation may be built from unverified rows is now enforced on **Best Card** (unverified figures are removed, not labelled) and on Portfolio View's category leader. The goal engine (Stages 5–9) is next, as this week's Session 3.

**Deployed:** frontend on Vercel (`opti-miles.vercel.app`), backend on Render (`optimiles-api.onrender.com`), Supabase Postgres at migration **0012**.

---

## What a user can do today

| Route | Signed in? | What it does |
|---|---|---|
| `/` and `/goals/new` | No / yes | Guided goal wizard: structured goal form (covered routes only), card picker, total spend, how-your-cards-earn step, optional spend split, feasibility check, add-a-card pair (cheapest / best value), best-effort plan when the goal can't be reached |
| `/best-card` | No | Card-first answer for an amount and category: every program the wallet reaches, portal vs direct rate, ties, "no card earns here". **Verified figures only**; a "Not compared" note names what was left out |
| `/cards` | Optional | Portfolio View (earn table, caps, milestones, transfers, lounge conditions; logged progress when signed in) plus the catalog |
| `/activity` | Yes | Log spends and lounge visits; cap use, milestone progress, fee-waiver progress with renewal month |
| `/goals`, `/goals/[id]` | Yes | Dashboard of saved goals; saved strategy detail; download; delete |
| `/login`, `/signup`, `/privacy`, `/terms` | No | Google + email sign-in via Supabase; legal pages for OAuth publishing |

---

## Backend

### Done
- **Five engines + 11-stage pipeline** (`pipeline/run.py`), deterministic and replayable from a versioned catalog snapshot. Standing tests guard determinism and module boundaries. Decision logs `2026-07-04-phase*` to `2026-07-05-phase6-*`.
- **LLM boundary:** only `ai_reasoning/` calls an LLM — intent extraction (Stage 1), narration (Stage 10) and the wizard's education text.
  - Every number in the output is checked against the input (number-echo validation), with a fixed-template fallback.
  - Each LLM step has a hard 10-second budget.
  - Provider: OpenRouter via `llm_base_url`.
- **Knowledge:** YAML seeds → `CatalogSnapshot` with a content-hash version; `validate_catalog()` reports every issue at once.
  - Catalog rules: `requires_portal`, over-cap earn (`base_rate` / `nothing`), zero-earn rows, fee waivers, lounge programs (4 of 9 cards covered), `acquirable` (Atlas and both Amex cards are `false`).
  - Covered routes are served at `GET /v1/catalog/routes`.
  - Issuer source documents (T&C, MITC, offer pages saved as PDF) are kept in `docs/TnC-docs/<Issuer>/`, and seed `source` fields cite them by path and page. HDFC is there now.
  - Award-chart rows carry **no taxes** until a sourced figure exists, so the API returns `taxes_fees_inr_estimate: null`.
- **Valuation:**
  - `transfer_math.py` holds the shared maths (whole-block transfers, caps, blended earn).
  - `opportunities.py` is Stage 5.
  - `best_card.py`: card-first, with `program_verdicts`, `destinations` / `best_for` / `overall_pick`, portal vs direct, and the `too_small` / `no_card_earns` states.
    - **Verified only:** `_verified_view` drops cards whose earn rests on a flagged row, and transfer links whose link, currency or partner is flagged, before anything is priced.
    - `withheld` lists names only, never figures.
    - A property test over the real seed flags guards it. Decision log `2026-11-17-best-card-verified-only.md`.
  - `portfolio.py`: the target program is optional; the category leader is withheld when it is unverified.
- **Simulation:**
  - `projector.py` builds the month-by-month ledger (caps, milestones, transfers).
  - `periods.py` and `observed.py` read the activity log. Results are lower bounds (`ObservedStatus` has no `NOT_REACHED`).
  - Fee-waiver progress against a user-set renewal month.
- **Optimization:**
  - 5 strategy archetypes, a greedy start plus hill-climb, and Stage 6 feasibility with an adjustment menu.
  - Ranking uses the `ranking-weights-v2.yaml` profile (acquisition pair: cheapest and best value) and keeps at most 3 routes.
  - Runner-up cause attribution; unreachable goals get a best-effort plan.
- **API (`/v1`):**
  - `goals`: parse, recommendation, save, list, detail, delete
  - `simulations`: run and probe, both rate-limited
  - `catalog`: cards, routes, education, education/story
  - `best-card`, `portfolio`
  - `activity`: spend, lounge visits, renewal months, summary
  - `/health` (GET + HEAD) at the root
  - ETags include a payload digest.
- **Auth and persistence:** Supabase HS256 JWT (fails closed). Owner-only RLS on every user table; catalog tables are public read-only. Saved goals write the full chain with `catalog_snapshot_version` + `engine_version`. Security audit 2026-11-07, hardening in migration 0012.
- **Ops:** CI (`backend-ci.yml`); keepalive jobs for Supabase and Render.

### Things to know before touching the backend
- **Supabase connection:**
  - Use the transaction pooler (`…pooler.supabase.com:6543`), not the direct host, which is IPv6-only and times out.
  - It needs `statement_cache_size=0` + `NullPool` + `pool_pre_ping`, in both `deps.py` and `alembic/env.py`.
- **Migrations:** SQL goes through the `_execute()` splitter, so never put `;` inside a SQL string literal.
- **Payload changes:** if you change a payload's shape, keep `deps.payload_digest` in its ETag, or browsers get a 304 onto the old body.
- **Local ports:** the frontend runs on `:3000` and the backend on `:8001`. Port `:8000` belongs to another project; leave it alone.
- **Snapshot loading:** the snapshot loads once and is cached. If the pooler refuses the first request, the process serves errors until it restarts (a retry is in Next up).
- **IDE:** point the Python interpreter at `backend/.venv/bin/python`; the root `.venv` is empty.

### In progress
- **Week 47 Session 1 leftovers (weekend), detailed in [`weekly-goals.md`](weekly-goals.md):**
  - Axis Burgundy + Atlas verification (5 rows)
  - Render LLM key + model
  - a sign-in with a Google account that isn't a test user
  - reload the live DB
- ⚠️ **Seeds are ahead of the live DB** (`cat-10cfcc27cd0b` vs live `cat-51ef71e52796`) and are not committed. Run `seeds/load_to_db.py` **before** pushing the backend. The API reads verification flags from the YAML at runtime, so a backend deployed first would mark rows verified while the DB still serves their old values.

### Next up
- **Week 47 — enforce the verified tier:** Stages 5–9 (Session 3), then the Listed tier (Session 4). Best Card is done. Details in `weekly-goals.md`.
- **Deploy order for Best Card: backend before frontend.** The new page fails closed (shows an error) against a backend without `withheld`, rather than showing unlabelled unverified figures. And per Session 1, reload the live DB before pushing the backend.
- **Platinum Charge is withheld from Best Card wherever its base rate applies.** Its card row is flagged only for `joining_fee_inr`, but row-level provenance withholds the base rate too. Two fixes, either one works: verify the joining fee (or record it as not stated), or give the base rate its own flag.
- **Portfolio, two open questions for the user:**
  - Should the category leader become the best *verified* card, as in Best Card? Today it shows "No verified leader".
  - Should unverified rates be hidden from the earn table, instead of labelled `*`?
- **Unverified seed questions:**
  - KrisFlyer India → London / New York Saver prices. The airline's calculator has none, because these routes connect in Singapore; never add up the legs. Needs the full zone-to-zone chart.
  - Burgundy earn table, Travel EDGE cap and the 5:4 ratio; Atlas 1:2 ratio and its cap
  - HDFC fee-waiver window: the MITC never defines the "year", so all 3 stay flagged
  - Re-check the SmartBuy offer page after 30-11-2026, the end of its offer window
- **Parked from the HDFC documents** (detail in decision log `2026-11-16-issuer-verification-krisflyer-hdfc.md`):
  - grocery, utility and telecom caps of 2,000 points a month; insurance cap
  - HDFC rounds down per ₹150 block, so a smooth rate can overstate one transaction by up to about 5 points (engine-level)
  - Turkish Airlines and Avianca as 2:1 partners
  - Regalia Gold Priority Pass guest rule now issuer-sourced, so that row could be cleared
  - Infinia ₹18L retention rule
  - First Saver availability by Indian city
  - TravelOne travel cap (HSBC's own guide says both 50,000 and 15,000)
  - HSBC and SBI "eligible spend" definitions for fee waivers
  - Amex ₹4L milestone transferability
  - Regalia Gold and Platinum Travel lounge guest rules
- **Breadth (next week candidates):**
  - sourced ₹-per-point values (none in the catalog yet). HDFC's documents give some: 1 point = ₹1 on SmartBuy flights and hotels for Infinia and Diners Black (₹0.50 for Regalia); Regalia Gold cashback ₹0.15.
  - transfer partners for the currencies we already have
  - new issuers, by ecosystem priority
- **Phase 2:**
  - statement/CSV upload (adds `spend_entries.source`; a full statement makes the log complete rather than a lower bound)
  - actual-vs-projected progress
  - milestone and cap alerts, modelled as events so they can be pushed later
  - re-plan when actual spending drifts from the plan
- **Best Card follow-ups:**
  - cap use and milestone proximity from logged spend
  - Stages 5–9 still price travel at the portal rate
- **Catalog modelling:**
  - an effective-from date (Amex Platinum Travel's lounge gate rises to ₹1,00,000 on 2027-01-01; change the seed by hand until then)
  - a `cap_reset_anchor` per cap
  - categories for rent / wallet / insurance / tax (a vocabulary decision)
  - BR-05/06 milestone validity windows (need a plan-start date)
- **Robustness:**
  - retry the snapshot load on a cold pooler
  - a real-DB round-trip test for saving
  - `CapUse` small fixes: it can round up, its ids depend on YAML order, and it should carry `over_cap_earn`
- **Deferred:**
  - two-part streaming response (D-5)
  - preference-aware ranking weights (DP-07)
  - more Maharaja Club links (HSBC 1:1, Regalia 100:33)

---

## Frontend

### Done
- **Marketing site** (`app/page.tsx`): edge-to-edge, dark/gold, Framer Motion v12; the goal wizard is the second section.
- **Goal wizard** (`goal-wizard.tsx` + `components/wizard/`): the only goal-entry surface, on both the homepage and `/goals/new`.
- **Strategy output** (`strategy-story.tsx`): verdict first, plan tabs that swap the whole plan, per-card earn maths table, transfer and book steps, earn chart, why-this-route, fine print. Shared by live results and saved goals.
- **Best Card** (`best-card.tsx`): card-first answer; programs listed only with 2+; drill-in per card.
  - Shows no unverified figures and no `*` marks.
  - A `NotCompared` note names withheld cards and transfers, without figures.
  - A `NothingVerified` panel covers the case where every picked card is withheld.
  - Copy no longer calls a withheld transfer "can't be transferred".
- **Portfolio View** (`app/portfolio-view.tsx`) and the **activity log** (`app/activity-log.tsx`).
- **Signed-in app shell** (`app/app-shell.tsx`): sidebar, top bar, mobile drawer, auth gate. Includes the dashboard and saved-goal detail.
- **Shared per-device wallet** (`lib/wallet.ts`), used by the wizard, Best Card and Portfolio.
- **Shared UI:** `card-picker`, `confirm-dialog`, `plane-loader`.
- **Storybook, design-sync and mobile-first pass:** Storybook 10 with a design-sync export (`src/lib-entry.ts`); the mobile-first pass was done 2026-09-01.

### Things to know before touching the frontend
- `lucide-react` is pinned to v1.21, which has **no brand or logo icons**. Importing one crashes the dev server.
- The hero's pin-and-release reads raw `scrollY` in pixels. Don't reintroduce `useScroll({target})`; it was buggy.
- `offset-path` (the plane loader) only animates in Chromium; Safari shows it static, which is acceptable.
- The base `grid-cols-1` on the dashboard grid is load-bearing; without it, narrow screens overflow.

### In progress
- Nothing active.

### Next up
- **Click through the signed-in pages behind real Google OAuth** (dashboard, saved-goal detail, wizard save, `/activity`). So far they have been checked only with injected sessions or by reading the code.
- **Saved goals, part 2:** persist the alternatives' full plans, so saved goals get the same tab swap as live results.
- **Goal form:** return trips (engine work: `one_way` is hard-coded), and free-text entry (parked until the LLM is reliable).
- **Portfolio:** show lounge visits used on the lounge rows, and a fee calendar.
- **PWA manifest:** Phase 4 only, after Phases 1–3.
- **Docs fix:** the `2026-06-21` decision log still says "no animation library", which the 2026-06-26 adoption of Framer Motion contradicts.

---

## Docs / Product

### Done
- `/docs` tree (`prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`), plus `TnC-docs/` for issuer source PDFs. The decision log runs to `2026-11-16-issuer-verification-krisflyer-hdfc.md`.
- **Canonical docs:**
  - scope: `CLAUDE.md` *Scope: Breadth With Depth*
  - roadmap: `prd/product-roadmap-v1.md`
  - goal engine: `prd/mvp-scope-v2.md`
  - backend entry point: `architecture/backend-build-plan-v1.md`
- **Weekly planning:** [`weekly-goals.md`](weekly-goals.md); Gemini prompt `prompts/listed-card-research-prompt-v1.md`.

### Next up
- Mirror the roadmap, the scope-broadening decision and the weekly plan into Notion.
- (Optional) Merge the two Strategy Ranking Engine drafts, and fold build-plan §3 into a `db-schema-v2.md`.

---

## Launch checklist (on the user)

- [x] **Publish the Google OAuth consent screen.** Done 2026-11-16, per the user. Still to do: one sign-in with a Google account that isn't a test user.
- [x] **Supabase Auth URL config:** Site URL plus a `https://opti-miles.vercel.app/**` redirect. Done 2026-11-16, per the user.
- [ ] **Render:** add `LLM_API_KEY` and `LLM_MODEL=openai/gpt-4o-mini`.
  - `LLM_MODEL` is required: if it's empty, the code falls back to `gpt-4o-mini` without the `openai/` prefix, and OpenRouter rejects that name.
  - Free `:free` models are capped at about 50 requests a day (about 1,000 with $10 of credits), across the whole site. They often miss the 10-second budget, so most visitors would still see the template.
  - Until then, summaries use the fixed template (live check 2026-11-16: `model_version: template-fallback`).
- [ ] (Optional) HSTS header, leaked-password protection, hide the public `/docs`.

---

## Last session notes

2026-11-17, Week 47 Session 2: Best Card answers from verified figures only. Nothing deployed or committed yet; Session 1's seed changes are still uncommitted too.
- **User decision:** an unverified figure is **removed** from the answer, not labelled. There is no "may earn more (unverified)" note. The team verifies rows on its own schedule, and a row comes back into Best Card by being verified.
- **Backend:** `best_card.py` builds a verified view before pricing (`_verified_view`). The response's new `withheld` field names what was left out, without figures. `no_card_earns` is never claimed while a card is withheld, and a withheld route is not reported as unroutable. New tests include a property test over the real seed flags that does not rely on the engine's own helpers; the old "marked unverified" tests were rewritten.
- **Frontend:** removed the `*` marks and their footnote. Added the "Not compared" note and the "can't answer yet" state. Answers are qualified as the best of the cards we could compare, and copy that would now be false was fixed.
- **Effect with today's seeds:**
  - Magnus for Burgundy and Platinum Charge are withheld in most categories (Platinum Charge only because of its joining-fee flag).
  - TravelOne is withheld on travel.
  - Atlas → KrisFlyer and every Regalia Gold transfer are withheld.
- **Decision log:** `decisions/2026-11-17-best-card-verified-only.md`.
