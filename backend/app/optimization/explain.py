"""Stage 9 explanation helpers — reshaping engine output for the story UI.

Pure presentation reshapes over already-computed engine artifacts. Nothing
here does reward math: it joins a strategy's `spend_allocation` (from the
Assignment its archetype produced) to the Stage-5 `RewardOpportunity` values
the Valuation Engine priced, so the UI can show *why* each category routes
where it does — the earn rate, the effective miles per ₹100, and the projected
monthly points — without the frontend recomputing anything.

The optional story inputs deepen the "why" without new math:

- `currency_names` / `category_labels` (resolved from the snapshot by the
  caller) name the card's points currency and the accelerated rule that
  priced a row — the "book via the travel portal to get this rate" fact.
- `all_opportunities` + `available_card_ids` power the runner-up comparison:
  for each category, the best OTHER card actually available in this plan
  (wallet + acquired) and its effective miles/₹100 — the deterministic answer
  to "why is my other card ignored?". Cards outside the plan never appear.
- `context` additionally powers **cause attribution** when the runner-up rates
  strictly HIGHER than the chosen card: the counterfactual (the category
  swapped to the runner-up) is re-estimated with the same `claimed_estimate`
  the generator uses, and the verified whole-plan difference is attributed —
  the runner-up's transfer-link cap binding (`transfer_cap`), a milestone
  bonus forfeited by the swap (`milestone`), a verified lower total
  (`fewer_total`), no difference (`equal_total`), or — only on the forced
  single-card routes (`single_card_route`) — the swap would actually GAIN and
  the route declines it by design (`route_shape`); a gaining swap on a
  hill-climbed route ships no cause at all. This is the one part of this
  module that runs engine math, and it runs the engine's own estimator —
  nothing is re-derived here.

The per-category `monthly_points` on each row is an **illustrative** figure —
`floor(monthly_spend × earn_rate / 100)` for that one category. It is NOT
authoritative and must not be summed to get a card's monthly credit: the engine
(`allocation.py` `_card_monthly`, `projector.py`) floors ONCE per card-month
over the exact cross-category sum, so per-category floors can undershoot the
true card total by a point or two when several categories share a card. Use
`card_monthly_points()` for the honest per-card figure the UI displays.
`monthly_miles` carries the same caveat in target-program miles.
"""

from collections.abc import Mapping, Sequence
from decimal import ROUND_DOWN, Decimal
from typing import Literal
from uuid import UUID

from app.domain import (
    PlanningContext,
    RewardOpportunity,
    SpendCategory,
    SpendProfile,
    StrategyAllocationDetail,
)
from app.optimization.allocation import Assignment, ClaimedEstimate, claimed_estimate

RunnerUpReason = Literal[
    "transfer_cap", "milestone", "fewer_total", "equal_total", "route_shape"
]


def _floor(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_DOWN))


def allocation_detail(
    assignment: Assignment,
    spend_profile: SpendProfile,
    *,
    all_opportunities: Sequence[RewardOpportunity] = (),
    available_card_ids: frozenset[UUID] = frozenset(),
    currency_names: Mapping[UUID, str] | None = None,
    category_labels: Mapping[tuple[UUID, SpendCategory], str] | None = None,
    context: PlanningContext | None = None,
    single_card_route: bool = False,
) -> tuple[StrategyAllocationDetail, ...]:
    """Per-category earn detail for a strategy's routing, ordered by category
    slug for determinism. One row per allocated category; a category with no
    opportunity in the assignment is simply absent (it earned nothing).

    Each row's `monthly_points`/`monthly_miles` is the per-category
    illustrative floor (see module docstring): fine to show per row, wrong to
    sum. For a card's true monthly credit use `card_monthly_points`.

    With `context`, a row whose runner-up rates strictly higher also carries
    the counterfactual-verified reason + whole-plan delta (module docstring).
    `single_card_route` marks the forced single-card archetypes
    (simplest/cheapest_viable): both counterfactual sides then match the
    generator's `include_idle_balances=False` basis (so the delta is measured
    against the strategy's own claim, not a different plan), and a swap that
    would GAIN is attributed `route_shape` — declining it IS those routes'
    design. On hill-climbed routes a gaining swap is a search artifact, not a
    design choice, so no cause is asserted (fields stay None)."""
    spend_by_category = {
        item.category_slug: item.monthly_spend_inr for item in spend_profile.items
    }
    # The current plan's estimate is shared by every row's counterfactual —
    # computed once, lazily (only when some row actually needs attribution).
    current_estimate: ClaimedEstimate | None = None
    rows: list[StrategyAllocationDetail] = []
    for category in sorted(assignment, key=lambda c: c.value):
        opportunity = assignment[category]
        monthly_spend = spend_by_category.get(category, 0)
        monthly_points = _floor(Decimal(monthly_spend) * opportunity.earn_rate / 100)
        monthly_miles = _floor(
            Decimal(monthly_spend) * opportunity.effective_miles_per_100inr / 100
        )
        runner_up = _runner_up(
            category, opportunity.card_id, all_opportunities, available_card_ids
        )
        reason: RunnerUpReason | None = None
        delta: int | None = None
        if (
            context is not None
            and runner_up is not None
            and runner_up.effective_miles_per_100inr
            > opportunity.effective_miles_per_100inr
        ):
            if current_estimate is None:
                current_estimate = claimed_estimate(
                    assignment, context, include_idle_balances=not single_card_route
                )
            reason, delta = _attribute_runner_up(
                assignment,
                category,
                runner_up,
                current_estimate,
                context,
                single_card_route=single_card_route,
            )
        rows.append(
            StrategyAllocationDetail(
                category_slug=category,
                card_id=opportunity.card_id,
                monthly_spend_inr=monthly_spend,
                earn_rate=opportunity.earn_rate,
                effective_miles_per_100inr=opportunity.effective_miles_per_100inr,
                monthly_points=monthly_points,
                monthly_miles=monthly_miles,
                notes=opportunity.valuation_notes,
                currency_name=(currency_names or {}).get(opportunity.card_id),
                transfer_ratio_from=opportunity.transfer_path.ratio_from,
                transfer_ratio_to=opportunity.transfer_path.ratio_to,
                category_label=(category_labels or {}).get(
                    (opportunity.card_id, category)
                ),
                runner_up_card_id=runner_up.card_id if runner_up else None,
                runner_up_miles_per_100inr=(
                    runner_up.effective_miles_per_100inr if runner_up else None
                ),
                runner_up_reason=reason,
                runner_up_plan_delta_miles=delta,
            )
        )
    return tuple(rows)


def _attribute_runner_up(
    assignment: Assignment,
    category: SpendCategory,
    runner_up: RewardOpportunity,
    current: ClaimedEstimate,
    context: PlanningContext,
    *,
    single_card_route: bool,
) -> tuple[RunnerUpReason | None, int | None]:
    """Why does a higher-rated runner-up still lose this category? Run the
    actual counterfactual — the same `claimed_estimate` the generator uses,
    with just this category swapped — and attribute the verified difference.
    Priority when the swap loses miles: the runner-up's transfer cap binding
    beats a forfeited milestone beats the generic verified total (a capped
    swap usually also reshuffles milestones; the cap is the actionable
    fact). The milestone check is presence-of-loss, not magnitude — a lost
    bonus is named even when rate effects contribute part of the delta;
    acceptable while few seeded cards carry milestones, revisit if the
    catalog grows stacked milestone ladders."""
    swapped = claimed_estimate(
        {**assignment, category: runner_up},
        context,
        include_idle_balances=not single_card_route,
    )
    delta = current.total_miles - swapped.total_miles
    if delta < 0:
        # The swap would GAIN. For the forced single-card archetypes that is
        # a design choice the row should own; on hill-climbed routes it is a
        # search artifact (the climb optimizes an optimistic bound, this
        # verifier is stricter) — asserting "declined by design" would be a
        # lie, so no cause ships.
        return ("route_shape", delta) if single_card_route else (None, None)
    if delta == 0:
        return "equal_total", 0
    if runner_up.transfer_path.currency_id in swapped.cap_bound_currencies:
        # Engine-owned fact from the counterfactual itself: the runner-up's
        # link cap actually clamped, so the cap — not the earn rate — is what
        # limits the swapped plan.
        return "transfer_cap", delta
    lost_milestones = {m.milestone_id for m in current.expected_milestones} - {
        m.milestone_id for m in swapped.expected_milestones
    }
    if lost_milestones:
        return "milestone", delta
    return "fewer_total", delta


def _runner_up(
    category: SpendCategory,
    chosen_card_id: UUID,
    all_opportunities: Sequence[RewardOpportunity],
    available_card_ids: frozenset[UUID],
) -> RewardOpportunity | None:
    """The best non-chosen opportunity for this category among the plan's own
    cards. Deterministic: highest effective miles/₹100, ties broken by card id.
    None when the plan has no other card with a priced path here."""
    candidates = [
        o
        for o in all_opportunities
        if o.category_slug == category
        and o.card_id != chosen_card_id
        and o.card_id in available_card_ids
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda o: (o.effective_miles_per_100inr, str(o.card_id)))


def card_monthly_points(
    assignment: Assignment, spend_profile: SpendProfile
) -> dict[UUID, int]:
    """Honest per-card monthly points: exact Decimal sum across all categories
    routed to a card, floored ONCE (the engine's contract — matches
    `allocation.py` `_card_monthly` and the projector's per-card-month floor).
    This, not the sum of per-category `monthly_points` rows, is the figure the
    UI shows as a card's monthly earn."""
    spend_by_category = {
        item.category_slug: item.monthly_spend_inr for item in spend_profile.items
    }
    exact_by_card: dict[UUID, Decimal] = {}
    for category, opportunity in assignment.items():
        spend = spend_by_category.get(category, 0)
        exact_by_card[opportunity.card_id] = (
            exact_by_card.get(opportunity.card_id, Decimal(0))
            + Decimal(spend) * opportunity.earn_rate / 100
        )
    return {card_id: _floor(total) for card_id, total in exact_by_card.items()}
