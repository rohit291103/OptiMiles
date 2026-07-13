# Decision Log — Infeasible Goals Ship a Best-Effort Plan

**Date:** 2026-07-12
**Area:** backend + frontend (pipeline Stages 6–11, narration, persistence, strategy UI)

## Context

When a goal wasn't reachable as stated (Stage 6's optimistic bound below the
requirement), the pipeline short-circuited Stages 7–9 entirely: no candidates,
no ranking, `recommended=None`, and the user got only the adjustment menu. The
user's feedback: *"if the goal is not reachable we should still give them a
plan, and also advise to increase the time or take a new card or increase
spending — but we need to give the plan."* A dead end with no plan reads as a
product failure, not honesty — nobody abandons a trip because a calculator
said no; they want to know how far they'd get and what would close the gap.

## Decisions

1. **Stages 7–9 always run** (`pipeline/run.py`). The feasibility verdict
   shapes narration and risks, not whether a plan exists. This is safe
   because the Stage-6 bound is a true upper bound: on an infeasible goal
   every candidate honestly misses the requirement, so ranking's existing
   `misses_goal` hard rule simply orders "least-bad first" and the top plan
   becomes the best-effort recommendation. Determinism invariant unchanged.
2. **`generate_candidates` no longer returns `()` on infeasible verdicts**
   (`optimization/strategies.py`). The two goal-clearing archetypes
   (simplest/cheapest_viable) naturally emit nothing when nothing clears the
   goal; the other archetypes produce honest short-fall plans. `()` still
   happens when nothing is allocatable at all (e.g. cashback-only wallet with
   acquisitions forbidden) — that path keeps the old menu-only response.
3. **Narration carries both stories** (`ai_reasoning/narration.py`). The
   payload builds adjustment notes whenever the verdict is infeasible (not
   only when `recommended is None`); the prompt and template gained an
   infeasible-with-plan branch: *"Not reachable as stated — the best route
   still earns X of the Y miles needed"* + the menu. `verdict.best_case_miles`
   is unconditionally echo-allowed. **The success-framed `comparison_notes`
   tier story is suppressed when infeasible** (backend-reviewer finding: it
   read as if the routes reached the goal), matching the prompt, which
   already omitted the comparison block on that path.
4. **Persistence needs no branching change** — `results.py` already keyed on
   `recommended is not None`, so best-effort plans persist the full FK chain;
   `recommendation_type='goal_feasibility'` still records infeasibility (the
   new legitimate combination: that type WITH a `simulation_results` row and
   a real confidence score). Additionally, **the Stage-6 adjustment menu now
   persists** (`adjustment_options` in the `card_allocations` JSONB, exposed
   on `SavedGoalDetail`) so a saved best-effort goal can render "what would
   close the gap" — without it, the saved view's hero promised changes it
   couldn't show (frontend-reviewer finding).
5. **Frontend renders honestly** (`strategy-story.tsx` + consumers).
   `VerdictHero` gained `bestEffort` ("…doesn't reach X in time — but the
   best route still gets you ~P" + gap line, with the "changes that would
   close the gap" clause gated on an `AdjustmentMenu` actually rendering);
   the adjustment menu became a shared `AdjustmentMenu` component rendered
   between hero and route tabs on live + saved views; the saved view derives
   feasibility from the persisted `recommendation_type` (strategy presence no
   longer implies feasibility). Two goal-missing-copy lies fixed per review:
   `tradeOff()` no longer calls extra miles "not needed to reach this goal"
   when the recommended tier itself misses (they shrink the gap), and the
   book step states the shortfall instead of promising a balance that won't
   arrive.
6. **Contract updates encoded as tests** (TDD, red-first): best-effort
   generation (`test_strategies`), end-to-end infeasible-with-plan
   (`test_run`), narration both-stories + comparison suppression
   (`test_narration`), full-lineage persistence with menu JSONB
   (`test_results`). The old `test_cheapest_viable_respects_no_new_cards_and_fee_cap`
   relied on infeasible⇒() vacuity; rewritten to assert the real invariants
   (fee cap respected, no fabricated goal-clearing claim). 305 backend tests,
   mypy strict, ruff, tsc, eslint clean; verified live (2-month SG business ×2
   pax: 27,659 of 90,000 miles + 3 adjustments + 2 route tabs; feasible path
   regression-checked byte-identical behavior).

## Not done (deferred)

- **Schema-doc addendum**: `db-schema-v1.md`'s `recommendation_type` comment
  doesn't anticipate `goal_feasibility` co-occurring with a result row; noted
  here rather than editing the versioned doc (no constraint is violated —
  verified against migration 0001).
- **Runner-up cause attribution** (why a higher-rate card lost a category —
  e.g. Atlas's 30k annual transfer cap) — separate tracker item.
- **Spend-model revamp** (total-spend-over-horizon input framing,
  reward-value-first education) — needs a grilling/PRD pass first; tracker
  "Next up".
