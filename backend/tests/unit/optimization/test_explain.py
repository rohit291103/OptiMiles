"""Stage 9 explanation helper — per-category earn detail behind a strategy.

`allocation_detail` reshapes a strategy's `spend_allocation` (category → card)
into per-category rows carrying the earn facts the UI needs to tell the story:
the card, monthly spend, the card's earn rate for that category, the effective
target-program miles per ₹100, the projected monthly points, and any valuation
notes (caps/exclusions). Every number traces to a `RewardOpportunity` the
Valuation Engine already computed — nothing here is recomputed reward math, it
is a pure reshape + one display projection.

Golden (hand-computed): Infinia SmartBuy travel at 5.0 pts/₹100 on ₹40,000/mo
routes 40000 × 5.0 / 100 = 2,000 points/month; dining at the same rate on
₹30,000 routes 1,500. effective_miles_per_100inr passes through unchanged from
the opportunity (the Valuation Engine's number, not re-derived here).
"""

from decimal import Decimal
from uuid import uuid4

from app.domain import (
    RewardOpportunity,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
)
from app.domain.opportunity import TransferPath
from app.optimization.allocation import Assignment
from app.optimization.explain import allocation_detail, card_monthly_points

CARD = uuid4()
CURRENCY = uuid4()
PARTNER = uuid4()


def _opportunity(
    category: SpendCategory,
    *,
    earn_rate: str,
    eff: str,
    notes: tuple[str, ...] = (),
) -> RewardOpportunity:
    return RewardOpportunity(
        card_id=CARD,
        in_wallet=False,
        category_slug=category,
        earn_rate=Decimal(earn_rate),
        transfer_path=TransferPath(
            currency_id=CURRENCY,
            partner_id=PARTNER,
            ratio_from=5,
            ratio_to=4,
            min_transfer_points=1000,
            max_transfer_points=None,
            transfer_fee_inr=0,
            processing_days_min=1,
            processing_days_max=7,
        ),
        effective_miles_per_100inr=Decimal(eff),
        valuation_notes=notes,
    )


def _spend() -> SpendProfile:
    return SpendProfile(
        items=(
            SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=40_000),
            SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=30_000),
        )
    )


def test_allocation_detail_carries_per_category_earn_facts() -> None:
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(
            SpendCategory.TRAVEL, earn_rate="5.0", eff="4.0"
        ),
        SpendCategory.DINING: _opportunity(
            SpendCategory.DINING, earn_rate="5.0", eff="4.0", notes=("Cap ₹1L/mo",)
        ),
    }
    rows = allocation_detail(assignment, _spend())

    # Deterministic order by category value (travel < dining alphabetically? no —
    # dining < travel), so the helper sorts by category value for stability.
    by_cat = {row.category_slug: row for row in rows}
    travel = by_cat[SpendCategory.TRAVEL]
    dining = by_cat[SpendCategory.DINING]

    assert travel.card_id == CARD
    assert travel.monthly_spend_inr == 40_000
    assert travel.earn_rate == Decimal("5.0")
    assert travel.effective_miles_per_100inr == Decimal("4.0")
    # 40000 × 5.0 / 100 = 2000, floored to int for display.
    assert travel.monthly_points == 2_000
    assert travel.notes == ()

    assert dining.monthly_points == 1_500  # 30000 × 5.0 / 100
    assert dining.notes == ("Cap ₹1L/mo",)


def test_allocation_detail_is_deterministically_ordered() -> None:
    """Rows come back in a stable category order regardless of dict order."""
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(SpendCategory.TRAVEL, earn_rate="5", eff="4"),
        SpendCategory.DINING: _opportunity(SpendCategory.DINING, earn_rate="3", eff="2"),
    }
    order_a = [r.category_slug for r in allocation_detail(assignment, _spend())]
    order_b = [
        r.category_slug
        for r in allocation_detail(dict(reversed(list(assignment.items()))), _spend())
    ]
    assert order_a == order_b


def test_allocation_detail_floors_fractional_points() -> None:
    """Display points floor (never overstate) — 33333 × 5 / 100 = 1666.65 → 1666."""
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(SpendCategory.TRAVEL, earn_rate="5", eff="4"),
    }
    spend = SpendProfile(
        items=(
            SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=33_333),
        )
    )
    rows = allocation_detail(assignment, spend)
    assert rows[0].monthly_points == 1_666


def test_allocation_detail_monthly_miles_golden() -> None:
    """The worked example the UI shows per row: floor(spend × effective miles
    per ₹100 / 100). 40,000 × 4.0 / 100 = 1,600; 30,000 × 4.0 / 100 = 1,200."""
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(SpendCategory.TRAVEL, earn_rate="5.0", eff="4.0"),
        SpendCategory.DINING: _opportunity(SpendCategory.DINING, earn_rate="5.0", eff="4.0"),
    }
    by_cat = {r.category_slug: r for r in allocation_detail(assignment, _spend())}
    assert by_cat[SpendCategory.TRAVEL].monthly_miles == 1_600
    assert by_cat[SpendCategory.DINING].monthly_miles == 1_200


def test_allocation_detail_monthly_miles_floors() -> None:
    """33,333 × 4.0 / 100 = 1,333.32 → 1,333 (never overstate)."""
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(SpendCategory.TRAVEL, earn_rate="5", eff="4"),
    }
    spend = SpendProfile(
        items=(SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=33_333),)
    )
    assert allocation_detail(assignment, spend)[0].monthly_miles == 1_333


def test_allocation_detail_carries_reward_system_story() -> None:
    """Each row explains the card's reward system: the currency it earns, the
    transfer ratio to the target program (from the opportunity's own transfer
    path — 5:4 in the fixture), and the catalog's label for an accelerated
    category (how to actually get the rate, e.g. a portal). A category priced
    at the default rate gets no label — the note already says it's default."""
    assignment: Assignment = {
        SpendCategory.TRAVEL: _opportunity(SpendCategory.TRAVEL, earn_rate="5.0", eff="4.0"),
        SpendCategory.DINING: _opportunity(SpendCategory.DINING, earn_rate="2.0", eff="1.6"),
    }
    rows = allocation_detail(
        assignment,
        _spend(),
        currency_names={CARD: "EDGE Miles"},
        category_labels={(CARD, SpendCategory.TRAVEL): "Flights & hotels via the travel portal"},
    )
    by_cat = {r.category_slug: r for r in rows}
    travel = by_cat[SpendCategory.TRAVEL]
    assert travel.currency_name == "EDGE Miles"
    assert travel.transfer_ratio_from == 5
    assert travel.transfer_ratio_to == 4
    assert travel.category_label == "Flights & hotels via the travel portal"
    dining = by_cat[SpendCategory.DINING]
    assert dining.currency_name == "EDGE Miles"
    assert dining.category_label is None


def test_allocation_detail_runner_up_is_best_other_available_card() -> None:
    """The 'why not my other card' answer: among the cards actually available
    in this plan (wallet + acquired), the best non-chosen card's effective
    miles/₹100 is recorded per category. A better card that is NOT available
    in the plan never appears — the comparison is against real options only."""
    other, unavailable = uuid4(), uuid4()
    chosen = _opportunity(SpendCategory.TRAVEL, earn_rate="5.0", eff="4.0")
    other_opp = _opportunity(SpendCategory.TRAVEL, earn_rate="2.0", eff="2.0").model_copy(
        update={"card_id": other}
    )
    stronger_but_unavailable = _opportunity(
        SpendCategory.TRAVEL, earn_rate="9.0", eff="9.0"
    ).model_copy(update={"card_id": unavailable})

    rows = allocation_detail(
        {SpendCategory.TRAVEL: chosen},
        SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=40_000),
            )
        ),
        all_opportunities=(chosen, other_opp, stronger_but_unavailable),
        available_card_ids=frozenset({CARD, other}),
    )
    assert rows[0].runner_up_card_id == other
    assert rows[0].runner_up_miles_per_100inr == Decimal("2.0")


def test_allocation_detail_runner_up_absent_without_another_card() -> None:
    """One-card wallet: nothing to compare against, fields stay None."""
    chosen = _opportunity(SpendCategory.TRAVEL, earn_rate="5.0", eff="4.0")
    rows = allocation_detail(
        {SpendCategory.TRAVEL: chosen},
        SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=40_000),
            )
        ),
        all_opportunities=(chosen,),
        available_card_ids=frozenset({CARD}),
    )
    assert rows[0].runner_up_card_id is None
    assert rows[0].runner_up_miles_per_100inr is None


def test_card_monthly_points_floors_once_per_card_not_per_category() -> None:
    """The engine's contract (allocation.py / projector.py): sum exact points
    across all categories on a card, then floor ONCE — not per category. Two
    ₹999 categories at rate 5 give 999×5/100 = 49.95 each: per-category flooring
    would sum 49+49=98, but the true card-month credit is floor(99.9) = 99."""
    same_card = uuid4()

    def opp(cat: SpendCategory) -> RewardOpportunity:
        o = _opportunity(cat, earn_rate="5", eff="4")
        return o.model_copy(update={"card_id": same_card})

    assignment: Assignment = {
        SpendCategory.TRAVEL: opp(SpendCategory.TRAVEL),
        SpendCategory.DINING: opp(SpendCategory.DINING),
    }
    spend = SpendProfile(
        items=(
            SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=999),
            SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=999),
        )
    )
    totals = card_monthly_points(assignment, spend)
    # One floor per card, over the exact sum — matches the projector.
    assert totals[same_card] == 99
