# Decision Log — Guided Strategy-Flow Revamp (design locked, not yet built)

**Date:** 2026-07-13
**Area:** product / frontend / backend

## Context

The user replaced the parked "spend-model revamp" idea with a full guided flow:
goal → approx **total spend over the horizon** (e.g. ₹6,00,000 over 12 months) →
card + transfer-ecosystem **education** (e.g. Atlas & TravelOne both → KrisFlyer;
TravelOne 2 pts/₹100 base, 4 travel, 16/24 via HSBC portal, 1:1 to KrisFlyer) →
opt-in **category split** → full visible calculation with per-category reasoning →
**feasibility verdict at the end**, with extra-card strategies offered when the goal
isn't reachable on the current wallet. A grilling session (this doc) resolved every
open branch. **This is a design decision only — implementation needs its own pass
(PRD/issues), and none of it is built yet.**

## Decisions

1. **One wizard everywhere.** The guided flow becomes THE goal-entry experience —
   the public homepage and `/goals/new` embed the same component. No forked
   one-shot form to maintain; the education step doubles as the marketing demo.
2. **Spend input is total-over-horizon only.** The user enters one number for the
   whole timeline. The engine still runs a monthly ledger internally (monthly caps,
   milestone thresholds, and transfer arrival timing are inherently time-based), so
   the total is spread uniformly: `monthly = floor(total ÷ months)` — floor, so
   projections never overstate earnings. A footnote makes the assumption visible:
   "≈ ₹50,000/month — we assume even spending."
3. **The total→profile split happens server-side.** The simulate request gains a
   total-spend input; the backend derives the category profile (default template
   proportions scaled to the total) so the existing `assumed` flag stays honest.
   A client-side split would present assumed numbers as user-entered truth.
4. **New education endpoint.** Wallet card ids in → structured payload out (per
   card: reward currency, earn rules with category labels incl. portal-accelerated
   rates, transfer links with ratio/cap/fee, partners shared across the wallet).
   Pure catalog-snapshot read — instant, deterministic, no pipeline run. This is a
   read-shaping of Knowledge Engine data, not a sixth engine.
5. **Feasibility: silent early probe, verdict at the end.** Right after goal +
   total spend, the cheap Stage-6 bound check runs silently. Clearly hopeless →
   interrupt immediately with the adjustment menu (don't walk someone through
   education for an impossible goal). Otherwise stay quiet and deliver the
   confident verdict at the end, as designed.
6. **Declining the category split still yields a full strategy.** "Want a spending
   strategy?" answered No → the pipeline runs on the assumed template split with a
   visible caveat and a one-click way to refine. Nobody leaves with only education.
7. **Split UI: categories win, total live-updates.** The split step pre-fills each
   category from the template scaled to their total; edits are free; the shown
   total re-derives from the sum. No "must equal" validation errors — once the
   user engages with the split, the split is the truth.
8. **Feasible → hero + quiet upgrade tabs; infeasible → explicit extra-card ask.**
   When current cards clear the goal, that strategy is the confident hero and the
   already-built acquisition route tabs remain beneath it as optional upgrades.
   When they don't, the flow asks "want strategies with additional cards?" and
   reveals exactly two.
9. **The two extra-card strategies: cheapest + best-value.** (a) the lowest-fee
   card that alone clears the goal (existing `cheapest_viable` archetype); (b) the
   best overall acquisition route by composite score (existing ranked
   `one_new_card` winner). The user's selection criteria — low fees, reward
   ecosystem, transfer-partner quality (ease-to-get explicitly out of scope) —
   become a versioned acquisition-weights profile in the existing ranking config.
   Reward rules stay config, not code; no new selection engine.
10. **LLM framing is an enhancement, never blocking.** Every step renders complete
    from deterministic data immediately; LLM-phrased framing (education story,
    calculation narrative — with a purpose-built system prompt) lands on top when
    available, passing the existing number-echo validation with template fallback.
    A 429 or slow model can never stall a step. (Today's OpenRouter free tier 429s
    intermittently — this keeps the wizard fully usable without a paid key.)
11. **Wizard shape: conversational scroll.** One page; each completed step
    collapses to an editable summary line and the next step appears below,
    auto-scrolled into view. Editing an earlier step invalidates and re-runs
    everything after it. Client-held state only — nothing persists until Save.
12. **The "Open to adding a new card?" toggle is dropped.** The end-of-flow
    behavior (decisions 8–9) handles the preference contextually.
13. **Empty wallet skips standalone education.** A one-liner ("no cards yet —
    we'll introduce the right ones with your strategy") replaces the step, and the
    recommended acquisition's card/ecosystem education renders as the first
    section of the strategy output instead. Same content, right moment.

## Not done (deferred)

- **All implementation.** This session shipped only the design + a separate
  goal-page UI polish pass (tracker). Next step: break this into vertical-slice
  issues (`to-issues`) or a PRD; backend pieces (total-spend request field,
  education endpoint, acquisition-weights profile) are TDD-mandatory.
- **Lumpy/non-uniform spend schedules** (wedding month, festival season): the
  even-spread assumption is surfaced but not modeled. Revisit only on real demand.
- **Ease-of-getting-the-card scoring** — explicitly out of scope per the user.
- **Streaming narration (D-5)** stays deferred; decision 10 works with the
  existing single-response narration.

## Implementation slices — guided strategy-flow revamp

Vertical slices, dependency-ordered, each one sitting of focused work and
demoable on its own. Backend calculation/API slices are TDD-mandatory (`tdd`
skill). References: decisions numbered above; current state per `docs/tracker.md`.

1. [ ] **Simulate accepts a total-spend budget** (decisions 2–3) — depends on: none
   - Backend only: request gains `total_spend_inr` (mutually exclusive with
     `spend_profile`); server scales the default template to the total,
     `monthly = floor(total ÷ horizon_months)`, profile flagged `assumed`.
     Deterministic goldens incl. non-divisible totals.
   - Touches: `backend/app/api/schemas.py`, `backend/app/pipeline/context.py`,
     `backend/app/api/goals.py`, unit tests.
   - Demo: curl `/simulations` with only a total → full recommendation, assumed flags set.

2. [ ] **Education endpoint returns the wallet's reward story** (decision 4) — depends on: none
   - Backend only: wallet card ids → per-card currency, earn rules with category
     labels (portal-accelerated rates included), transfer links (ratio/cap/fee),
     partners shared across the wallet. Pure catalog-snapshot read (Knowledge
     Engine data reshape — no pipeline run, no LLM, no sixth engine).
   - Touches: `backend/app/api/` (new route), read-shaping helper +
     `knowledge/store.py` consumers, unit tests against the seed catalog.
   - Demo: curl with Atlas+TravelOne ids → both cards' chains to KrisFlyer with rates.

3. [ ] **Fast feasibility probe endpoint** (decision 5) — depends on: slice 1
   - Backend only: goal intent + wallet + total → Stage 2–6 only (resolution →
     requirement → context → opportunities → bound check), returning the verdict +
     adjustment menu. No candidates, no simulation, no narration — sub-second.
   - Touches: `backend/app/api/` (new route reusing pipeline stages),
     `pipeline/run.py` (early-exit composition), tests.
   - Demo: hopeless goal returns `feasible: false` + menu in <1s.

4. [ ] **Wizard shell: goal → cards → total-spend, conversational scroll** (decisions 1, 2, 11, 12) — depends on: slice 1
   - Frontend: step framework (completed steps collapse to editable summary
     lines; editing invalidates downstream; auto-scroll to active step), steps 1–2
     built from the existing goal sentence + bank-grouped picker + a new
     total-spend input with the "≈ ₹X/month — we assume even spending" footnote;
     old per-category inputs and the new-card toggle removed; final step runs the
     existing pipeline via slice 1 and renders the existing `StrategyDetail`.
   - Touches: `frontend/src/components/goal-simulator.tsx` (likely split into
     `goal-wizard.tsx` + step components), `frontend/src/lib/api.ts`.
   - Demo: full journey minus education/split — total in, strategy out.

5. [ ] **Hopeless goals get stopped early** (decision 5) — depends on: slices 3, 4
   - Frontend: silent probe fires after the total-spend step; clearly-infeasible →
     inline interrupt with the shared `AdjustmentMenu` and editable steps;
     otherwise invisible.
   - Touches: wizard step flow, `frontend/src/lib/api.ts`.
   - Demo: 2-month ×2-pax business on ₹1L stops before education; sane goal flows on.

6. [ ] **Education step in the wizard** (decisions 4, 10, 13) — depends on: slices 2, 4
   - Frontend: renders the education payload as the cards → partners → reward
     system story (deterministic template text first); empty wallet skips with the
     one-liner and defers education into the strategy output.
   - Touches: new `education-step` component, wizard flow, `api.ts`.
   - Demo: Atlas+TravelOne shows both chains to KrisFlyer; empty wallet skips.

7. [ ] **Opt-in category split step** (decisions 6, 7) — depends on: slice 4
   - Frontend: "Want a spending strategy?" → Yes: categories-win split UI
     (pre-filled from the template scaled to their total; edits free; total
     live-updates). No: run on the assumed split, render the strategy with the
     visible caveat + one-click refine that reopens this step.
   - Touches: new `split-step` component, wizard flow.
   - Demo: both paths produce a full strategy; the No path shows the caveat.

8. [ ] **Acquisition pair for infeasible goals: cheapest + best-value** (decisions 8, 9) — depends on: none (parallel)
   - Backend: versioned acquisition-weights profile in the ranking config
     (fees/ecosystem/transfer-quality); infeasible responses expose exactly two
     acquisition strategies — `cheapest_viable` + the top-composite
     `one_new_card` — deduped and labeled. Goldens over the seed catalog.
   - Touches: `backend/config/ranking-weights-v1.yaml` (or v2),
     `backend/app/optimization/ranking.py`, `pipeline/run.py`, tests.
   - Demo: infeasible run returns the two labeled acquisition routes.

9. [ ] **End-of-flow verdict: confident hero, contextual extra-card ask** (decisions 8, 9) — depends on: slices 7, 8
   - Frontend: feasible → current-cards hero with the existing route tabs demoted
     to quiet "upgrade" options; infeasible → best-effort verdict + explicit
     "want strategies with additional cards?" reveal of the two routes.
   - Touches: `strategy-detail.tsx`, `strategy-story.tsx`, wizard final step.
   - Demo: both verdict paths live against the real engine.

10. [ ] **Wizard ships everywhere + LLM framing on top** (decisions 1, 10) — depends on: slices 4–9
    - Homepage embed swapped to the wizard; dead one-shot code removed; education
      + calculation framing narrated by the LLM (purpose-built system prompt,
      number-echo validated, template fallback, never blocking); full
      frontend-reviewer + backend-reviewer pass; saved-goal flow re-verified.
    - Touches: `frontend/src/app/page.tsx`, `backend/app/ai_reasoning/narration.py`
      (education prompt), cleanup across both trees.
    - Demo: marketing page and /goals/new run the identical wizard end-to-end.
