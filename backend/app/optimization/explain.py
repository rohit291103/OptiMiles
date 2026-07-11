"""Stage 9 explanation helpers — reshaping engine output for the story UI.

Pure presentation reshapes over already-computed engine artifacts. Nothing
here does reward math: it joins a strategy's `spend_allocation` (from the
Assignment its archetype produced) to the Stage-5 `RewardOpportunity` values
the Valuation Engine priced, so the UI can show *why* each category routes
where it does — the earn rate, the effective miles per ₹100, and the projected
monthly points — without the frontend recomputing anything.

The per-category `monthly_points` on each row is an **illustrative** figure —
`floor(monthly_spend × earn_rate / 100)` for that one category. It is NOT
authoritative and must not be summed to get a card's monthly credit: the engine
(`allocation.py` `_card_monthly`, `projector.py`) floors ONCE per card-month
over the exact cross-category sum, so per-category floors can undershoot the
true card total by a point or two when several categories share a card. Use
`card_monthly_points()` for the honest per-card figure the UI displays.
"""

from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from app.domain import SpendProfile, StrategyAllocationDetail
from app.optimization.allocation import Assignment


def _floor(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_DOWN))


def allocation_detail(
    assignment: Assignment, spend_profile: SpendProfile
) -> tuple[StrategyAllocationDetail, ...]:
    """Per-category earn detail for a strategy's routing, ordered by category
    slug for determinism. One row per allocated category; a category with no
    opportunity in the assignment is simply absent (it earned nothing).

    Each row's `monthly_points` is the per-category illustrative floor (see
    module docstring): fine to show per row, wrong to sum. For a card's true
    monthly credit use `card_monthly_points`."""
    spend_by_category = {
        item.category_slug: item.monthly_spend_inr for item in spend_profile.items
    }
    rows: list[StrategyAllocationDetail] = []
    for category in sorted(assignment, key=lambda c: c.value):
        opportunity = assignment[category]
        monthly_spend = spend_by_category.get(category, 0)
        monthly_points = _floor(Decimal(monthly_spend) * opportunity.earn_rate / 100)
        rows.append(
            StrategyAllocationDetail(
                category_slug=category,
                card_id=opportunity.card_id,
                monthly_spend_inr=monthly_spend,
                earn_rate=opportunity.earn_rate,
                effective_miles_per_100inr=opportunity.effective_miles_per_100inr,
                monthly_points=monthly_points,
                notes=opportunity.valuation_notes,
            )
        )
    return tuple(rows)


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
