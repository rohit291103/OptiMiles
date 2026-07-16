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
    spend_profile_from_total,
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


# ── Total-spend → assumed profile (guided-flow decision log 2026-07-13, D2–D3) ──
#
# Template weights: travel 25k / dining 20k / online 20k / groceries 15k /
# utilities 10k — weight sum 90k. Every division floors (projections must
# never overstate earnings):
#     monthly_budget    = floor(total ÷ horizon_months)
#     category_amount_i = floor(monthly_budget × weight_i ÷ 90_000)


def test_total_divisible_scales_template_exactly() -> None:
    """₹90,000 over 1 month divides the template weights exactly — no floor
    loss. Hand-computed: 25,000 / 20,000 / 20,000 / 15,000 / 10,000."""
    profile = spend_profile_from_total(90_000, horizon_months=1)
    assert profile.assumed is True
    assert [(i.category_slug, i.monthly_spend_inr) for i in profile.items] == [
        (SpendCategory.TRAVEL, 25_000),
        (SpendCategory.DINING, 20_000),
        (SpendCategory.ONLINE, 20_000),
        (SpendCategory.GROCERIES, 15_000),
        (SpendCategory.UTILITIES, 10_000),
    ]


def test_total_600k_over_12_months_floors_each_category() -> None:
    """The design doc's canonical example: ₹6,00,000 over 12 months.

    monthly = floor(600000/12) = 50,000. Hand-computed category floors:
      travel    floor(50000×25000/90000) = floor(13888.88…) = 13,888
      dining    floor(50000×20000/90000) = floor(11111.11…) = 11,111
      online    = 11,111
      groceries floor(50000×15000/90000) = floor(8333.33…)  =  8,333
      utilities floor(50000×10000/90000) = floor(5555.55…)  =  5,555
    Sum 49,998 ≤ 50,000 — floor loss never overstates."""
    profile = spend_profile_from_total(600_000, horizon_months=12)
    amounts = {i.category_slug: i.monthly_spend_inr for i in profile.items}
    assert amounts == {
        SpendCategory.TRAVEL: 13_888,
        SpendCategory.DINING: 11_111,
        SpendCategory.ONLINE: 11_111,
        SpendCategory.GROCERIES: 8_333,
        SpendCategory.UTILITIES: 5_555,
    }
    assert sum(amounts.values()) <= 600_000 // 12
    assert profile.assumed is True


def test_total_non_divisible_by_horizon_floors_monthly_first() -> None:
    """Non-divisible total: ₹1,00,000 over 7 months.

    monthly = floor(100000/7) = 14,285 (never 14,286). Category floors:
      travel    floor(14285×25000/90000) = floor(3968.05…) = 3,968
      dining    floor(14285×20000/90000) = floor(3174.44…) = 3,174
      online    = 3,174
      groceries floor(14285×15000/90000) = floor(2380.83…) = 2,380
      utilities floor(14285×10000/90000) = floor(1587.22…) = 1,587"""
    profile = spend_profile_from_total(100_000, horizon_months=7)
    amounts = {i.category_slug: i.monthly_spend_inr for i in profile.items}
    assert amounts == {
        SpendCategory.TRAVEL: 3_968,
        SpendCategory.DINING: 3_174,
        SpendCategory.ONLINE: 3_174,
        SpendCategory.GROCERIES: 2_380,
        SpendCategory.UTILITIES: 1_587,
    }


def test_tiny_total_drops_zero_floor_categories() -> None:
    """₹96 over 12 months → monthly 8. utilities floors to 0
    (8×10000/90000 = 0.88…) and must be DROPPED, not emitted as an invalid
    zero-spend item: travel 2, dining 1, online 1, groceries 1."""
    profile = spend_profile_from_total(96, horizon_months=12)
    amounts = {i.category_slug: i.monthly_spend_inr for i in profile.items}
    assert amounts == {
        SpendCategory.TRAVEL: 2,
        SpendCategory.DINING: 1,
        SpendCategory.ONLINE: 1,
        SpendCategory.GROCERIES: 1,
    }
    assert SpendCategory.UTILITIES not in amounts


def test_total_below_horizon_yields_empty_profile() -> None:
    """₹5 over 12 months → monthly floor 0 → no fundable category. An empty
    (still assumed) profile is the honest output; Stage 5 then enumerates
    nothing and Stage 6 declares infeasibility — never a fabricated spend."""
    profile = spend_profile_from_total(5, horizon_months=12)
    assert profile.items == ()
    assert profile.assumed is True


def test_derivation_guards_reject_non_positive_inputs() -> None:
    """Defensive guards (unreachable via the API, which validates gt=0 and
    floors the horizon at 1) still fail loud for direct callers."""
    with pytest.raises(ValueError, match="total_spend_inr"):
        spend_profile_from_total(0, horizon_months=12)
    with pytest.raises(ValueError, match="horizon_months"):
        spend_profile_from_total(600_000, horizon_months=0)


def test_assemble_derives_profile_from_total(snapshot: CatalogSnapshot) -> None:
    """Total-only callers get the template scaled to their budget over the
    goal's own derived horizon, flagged assumed."""
    goal = make_goal(snapshot, today=TODAY, timeline_months=8)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)

    context = assemble_context(
        goal,
        requirement,
        snapshot,
        wallet=(),
        spend_profile=None,
        total_spend_inr=600_000,
        constraints=None,
        today=TODAY,
    )
    assert context.horizon_months == 8
    # monthly = floor(600000/8) = 75,000 → same derivation as the direct call.
    assert context.spend_profile == spend_profile_from_total(600_000, horizon_months=8)
    assert context.spend_profile.assumed is True


def test_assemble_rejects_profile_and_total_together(
    snapshot: CatalogSnapshot,
) -> None:
    """A caller supplying both a category split and a total is a contract
    violation — fail loud, never silently prefer one."""
    goal = make_goal(snapshot, today=TODAY, timeline_months=8)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)
    caller_profile = SpendProfile(
        items=(SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=50_000),),
    )
    with pytest.raises(ValueError, match="total_spend_inr"):
        assemble_context(
            goal,
            requirement,
            snapshot,
            wallet=(),
            spend_profile=caller_profile,
            total_spend_inr=600_000,
            constraints=None,
            today=TODAY,
        )


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
