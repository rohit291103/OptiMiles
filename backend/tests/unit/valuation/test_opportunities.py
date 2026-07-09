"""Stage 5 — opportunity enumeration over the real seed catalog.

The search space contract: one opportunity per (eligible card × profile
category), priced at the blended cap-aware rate for routing that WHOLE
category's spend to that card — the granularity at which Stage 7 allocates.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain import (
    CatalogSnapshot,
    GoalResolution,
    OpportunitySet,
    ParsedGoalIntent,
    PlanningContext,
    RewardOpportunity,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.valuation.opportunities import enumerate_opportunities

TODAY = date(2026, 7, 4)


def _context(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int] | None = None,
    wallet_slugs: tuple[str, ...] = ("hdfc-infinia",),
) -> PlanningContext:
    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=8,
        num_passengers=2,
        confidence=0.95,
    )
    resolution = resolve_goal(intent, snapshot, today=TODAY)
    assert isinstance(resolution, GoalResolution)
    goal = TravelGoal(id=uuid4(), user_id=uuid4(), status="active", **resolution.model_dump())
    spend = (
        spend if spend is not None else {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000}
    )
    return PlanningContext(
        user_id=goal.user_id,
        goal=goal,
        requirement=estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot=snapshot,
        wallet=tuple(
            WalletCard(card_id=seed_id("card", slug), current_points_balance=20_000)
            for slug in wallet_slugs
        ),
        spend_profile=SpendProfile(
            items=tuple(
                SpendProfileItem(category_slug=cat, monthly_spend_inr=amount)
                for cat, amount in spend.items()
            )
        ),
        horizon_months=8,
    )


def _find(
    opportunities: OpportunitySet, card_slug: str, category: SpendCategory
) -> RewardOpportunity:
    card_id = seed_id("card", card_slug)
    return next(
        o
        for o in opportunities.opportunities
        if o.card_id == card_id and o.category_slug == category
    )


def test_sbi_cashback_yields_zero_opportunities(snapshot: CatalogSnapshot) -> None:
    """Phase 2 exit criterion (build plan §5): no transfer link ⇒ no path to
    KrisFlyer ⇒ SBI never appears in the search space."""
    result = enumerate_opportunities(_context(snapshot))
    sbi = seed_id("card", "sbi-cashback")
    assert not any(o.card_id == sbi for o in result.opportunities)
    assert not any(a.card_id == sbi for a in result.card_aggregates)


def test_every_eligible_card_covers_every_profile_category(snapshot: CatalogSnapshot) -> None:
    """8 eligible cards (9 minus SBI) × 2 profile categories = 16 cells: the
    complete allocation search space, no gaps."""
    result = enumerate_opportunities(_context(snapshot))
    assert len(result.opportunities) == 16
    assert len(result.card_aggregates) == 8


def test_golden_infinia_travel_within_cap(snapshot: CatalogSnapshot) -> None:
    """₹40k travel ≤ ₹150k cap → full SmartBuy rate: 16.65 × 1:1 = 16.65."""
    opp = _find(enumerate_opportunities(_context(snapshot)), "hdfc-infinia", SpendCategory.TRAVEL)
    assert opp.effective_miles_per_100inr == Decimal("16.65")
    assert opp.in_wallet is True


def test_golden_infinia_travel_beyond_cap_blends(snapshot: CatalogSnapshot) -> None:
    """₹200k travel vs ₹150k cap → blended 13.32 pts/₹100 × 1:1 = 13.32,
    with a valuation note naming the cap (explainability raw material)."""
    context = _context(snapshot, spend={SpendCategory.TRAVEL: 200_000})
    opp = _find(enumerate_opportunities(context), "hdfc-infinia", SpendCategory.TRAVEL)
    assert opp.effective_miles_per_100inr == Decimal("13.32")
    assert any("cap" in note.lower() for note in opp.valuation_notes)


def test_golden_atlas_travel_rate(snapshot: CatalogSnapshot) -> None:
    """Atlas travel 5 EM/₹100 × 1:2 = 10 miles/₹100 (no longer the best rate —
    Burgundy's Travel EDGE 24.00 is) — and the annual transfer cap must be
    surfaced as a note, not hidden."""
    opp = _find(enumerate_opportunities(_context(snapshot)), "axis-atlas", SpendCategory.TRAVEL)
    assert opp.effective_miles_per_100inr == Decimal("10.00")
    assert opp.in_wallet is False
    assert opp.transfer_path.max_transfer_points == 30_000


def test_golden_dining_falls_back_to_default_rate(snapshot: CatalogSnapshot) -> None:
    """No card accelerates dining in the seeds: Infinia dining earns the
    default 3.33 × 1:1 = 3.33, flagged as default-rate in notes."""
    opp = _find(enumerate_opportunities(_context(snapshot)), "hdfc-infinia", SpendCategory.DINING)
    assert opp.effective_miles_per_100inr == Decimal("3.33")
    assert any("default" in note.lower() for note in opp.valuation_notes)


def test_golden_amex_and_magnus_defaults(snapshot: CatalogSnapshot) -> None:
    result = enumerate_opportunities(_context(snapshot))
    amex = _find(result, "amex-platinum-travel", SpendCategory.DINING)
    assert amex.effective_miles_per_100inr == Decimal("1")  # 2.00 × 1/2
    charge = _find(result, "amex-platinum-charge", SpendCategory.DINING)
    assert charge.effective_miles_per_100inr == Decimal("1.25")  # 2.50 × 1/2
    magnus = _find(result, "axis-magnus-burgundy", SpendCategory.DINING)
    assert magnus.effective_miles_per_100inr == Decimal("4.8")  # 6.00 × 4/5 (Burgundy 5:4)


def test_golden_magnus_burgundy_travel_is_best_rate(snapshot: CatalogSnapshot) -> None:
    """Travel EDGE 30/₹100 through the Burgundy 5:4 link = 24.00 miles/₹100 —
    the new best travel rate in the catalog (₹40k ≤ ₹2L monthly cap)."""
    opp = _find(
        enumerate_opportunities(_context(snapshot)), "axis-magnus-burgundy", SpendCategory.TRAVEL
    )
    assert opp.effective_miles_per_100inr == Decimal("24.00")
    assert opp.transfer_path.max_transfer_points == 200_000


def test_aggregates_carry_fees_and_welcome_bonus(snapshot: CatalogSnapshot) -> None:
    result = enumerate_opportunities(_context(snapshot))
    atlas = next(a for a in result.card_aggregates if a.card_id == seed_id("card", "axis-atlas"))
    assert atlas.annual_fee_inr == 5_000
    assert atlas.welcome_bonus_points == 2_500  # welcome_bonus milestone
    assert atlas.in_wallet is False
    infinia = next(
        a for a in result.card_aggregates if a.card_id == seed_id("card", "hdfc-infinia")
    )
    assert infinia.in_wallet is True
    assert infinia.welcome_bonus_points == 0


def test_aggregates_carry_acquirable_flag(snapshot: CatalogSnapshot) -> None:
    """Stage 7's one-new-card archetype reads acquirability from the aggregates:
    discontinued Atlas must arrive flagged non-acquirable."""
    result = enumerate_opportunities(_context(snapshot))
    atlas = next(a for a in result.card_aggregates if a.card_id == seed_id("card", "axis-atlas"))
    assert atlas.acquirable is False
    burgundy = next(
        a for a in result.card_aggregates if a.card_id == seed_id("card", "axis-magnus-burgundy")
    )
    assert burgundy.acquirable is True


def test_deterministic_output_order(snapshot: CatalogSnapshot) -> None:
    """Same context ⇒ identical OpportunitySet, including order — the
    byte-replayability invariant applies to intermediate artifacts too."""
    a = enumerate_opportunities(_context(snapshot))
    b = enumerate_opportunities(_context(snapshot))
    assert [o.card_id for o in a.opportunities] == [o.card_id for o in b.opportunities]
    assert a.opportunities == b.opportunities


def test_golden_remaining_cards_all_pinned(snapshot: CatalogSnapshot) -> None:
    """Exit criterion is EVERY (card, category, KrisFlyer) path hand-computed —
    DCB, Regalia Gold and HSBC TravelOne were previously only counted, not
    asserted (reviewer finding, 2026-07-04).

    Hand-computed:
      DCB travel        16.65 pts/₹100 × 1:1           = 16.65
      DCB dining        3.33 (default) × 1:1           = 3.33
      Regalia default   2.67 × 1:2 value (2:1 link)    = 1.3350
      HSBC travel       4.00 × 1:1                     = 4.00
      HSBC dining       2.00 (default) × 1:1           = 2.00
    """
    result = enumerate_opportunities(_context(snapshot))
    expectations = [
        ("hdfc-diners-black", SpendCategory.TRAVEL, Decimal("16.65")),
        ("hdfc-diners-black", SpendCategory.DINING, Decimal("3.33")),
        ("hdfc-regalia-gold", SpendCategory.DINING, Decimal("1.3350")),
        ("hsbc-travelone", SpendCategory.TRAVEL, Decimal("4.00")),
        ("hsbc-travelone", SpendCategory.DINING, Decimal("2.00")),
    ]
    for slug, category, expected in expectations:
        actual = _find(result, slug, category).effective_miles_per_100inr
        assert actual == expected, f"{slug}/{category.value}: {actual} != {expected}"


def test_golden_dcb_shares_infinia_currency_blend(snapshot: CatalogSnapshot) -> None:
    """DCB rides the same hdfc-rp-premium currency as Infinia: ₹200k travel
    against its ₹150k cap must blend to the identical 13.32 — a
    currency-sharing regression canary (D-1)."""
    context = _context(snapshot, spend={SpendCategory.TRAVEL: 200_000})
    opp = _find(enumerate_opportunities(context), "hdfc-diners-black", SpendCategory.TRAVEL)
    assert opp.effective_miles_per_100inr == Decimal("13.32")
