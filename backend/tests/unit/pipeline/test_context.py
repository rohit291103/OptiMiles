"""Stage 4 assembly + horizon math (pipeline/context.py).

The default-spend template and horizon rounding are the two places Stage 4
originates a value, so they get golden-value coverage: a default profile is
always flagged assumed, and the horizon rounds UP a partial final month and
floors at 1.
"""

from datetime import date
from uuid import uuid4

import pytest

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    SpendProfile,
    SpendProfileItem,
    WalletCard,
)
from app.domain.enums import SpendCategory
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.pipeline.context import (
    assemble_context,
    default_spend_profile,
    horizon_months,
)
from tests.unit.pipeline.helpers import make_goal

TODAY = date(2026, 7, 4)


@pytest.mark.parametrize(
    "target, expected",
    [
        (date(2026, 7, 4), 1),  # same day → floored at 1, never 0
        (date(2026, 7, 3), 1),  # already past → still one tick
        (date(2026, 8, 4), 1),  # exactly one month, same day → not rounded up
        (date(2026, 8, 5), 2),  # one month + partial → rounds UP
        (date(2027, 3, 4), 8),  # the canonical "8 months" goal
        (date(2027, 3, 20), 9),  # 8 months + partial → 9
    ],
)
def test_horizon_rounds_up_partial_month_and_floors_at_one(
    target: date, expected: int
) -> None:
    assert horizon_months(target, TODAY) == expected


def test_default_spend_profile_is_flagged_assumed() -> None:
    profile = default_spend_profile()
    assert profile.assumed is True
    assert profile.items  # non-empty template
    # Every template category is a real canonical slug.
    for item in profile.items:
        assert isinstance(item.category_slug, SpendCategory)
        assert item.monthly_spend_inr > 0


def test_assemble_applies_default_profile_when_none_given(
    snapshot: CatalogSnapshot,
) -> None:
    goal = make_goal(snapshot, today=TODAY, timeline_months=8)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)

    context = assemble_context(
        goal,
        requirement,
        snapshot,
        wallet=(),
        spend_profile=None,
        constraints=None,
        today=TODAY,
    )
    assert context.spend_profile.assumed is True
    assert context.horizon_months == 8
    assert context.wallet == ()  # empty wallet is a valid context, not an error
    assert context.constraints == ConstraintSet()


def test_assemble_keeps_caller_profile_unflagged(snapshot: CatalogSnapshot) -> None:
    goal = make_goal(snapshot, today=TODAY, timeline_months=8)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)
    caller_profile = SpendProfile(
        items=(SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=50_000),),
        assumed=False,
    )
    wallet = (WalletCard(card_id=uuid4(), current_points_balance=1_000),)

    context = assemble_context(
        goal,
        requirement,
        snapshot,
        wallet=wallet,
        spend_profile=caller_profile,
        constraints=ConstraintSet(no_new_cards=True),
        today=TODAY,
    )
    assert context.spend_profile is caller_profile
    assert context.spend_profile.assumed is False
    assert context.constraints.no_new_cards is True


def test_resolution_and_context_agree_on_target_date(snapshot: CatalogSnapshot) -> None:
    """The horizon derived from the resolved target_date matches the intent's
    stated timeline — resolution and Stage-4 assembly don't drift."""
    from app.domain import GoalResolution, ParsedGoalIntent

    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=8,
        num_passengers=1,
        confidence=0.95,
    )
    resolution = resolve_goal(intent, snapshot, today=TODAY)
    assert isinstance(resolution, GoalResolution)
    assert horizon_months(resolution.target_date, TODAY) == 8
