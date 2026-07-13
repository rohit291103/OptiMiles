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

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain import (
    CatalogSnapshot,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    RewardOpportunity,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TravelGoal,
    WalletCard,
)
from app.domain.opportunity import TransferPath
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.allocation import Assignment
from app.optimization.explain import allocation_detail, card_monthly_points
from app.valuation.opportunities import enumerate_opportunities

CARD = uuid4()
CURRENCY = uuid4()
PARTNER = uuid4()

TODAY = date(2026, 7, 4)
ATLAS = seed_id("card", "axis-atlas")
BURGUNDY = seed_id("card", "axis-magnus-burgundy")
TRAVELONE = seed_id("card", "hsbc-travelone")


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


# ── Runner-up cause attribution (real seed catalog, counterfactual-verified) ──
#
# When the runner-up rates HIGHER per ₹100 than the chosen card, the row must
# say WHY the plan still keeps the spend where it is — by actually running the
# counterfactual (swap the category to the runner-up, re-estimate the whole
# plan with the same claimed_estimate the generator uses) and attributing the
# verified difference. Fixture goldens hand-checked against the seed catalog:
#
#   transfer_cap — wallet {Atlas, TravelOne}, travel ₹1.5L + dining ₹30k /mo,
#     horizon 12 (cutoff month 10 ⇒ 11 earning months):
#     current (travel→TravelOne, dining→Atlas):
#       TravelOne 1.5L×4/₹100 ×11 = 66,000 RP →1:1→ 66,000 mi
#       Atlas dining 600/mo ×11 = 6,600 + Silver 2,500 = 9,100 EDGE →1:2→ 18,200
#       total 84,200
#     swapped (travel also →Atlas): 8,100 EDGE/mo ×11 = 89,100 earned, but the
#       EDGE→KrisFlyer link hard-caps at 30,000/yr → 60,000 mi. Δ = 24,200,
#       and the cap is exactly what binds.
#
#   milestone — wallet {Atlas, Burgundy}, travel ₹20k + dining ₹30k /mo:
#     Burgundy dining rates 4.8 mi/₹100 vs Atlas 4.0, but moving dining off
#     Atlas forfeits the ₹3L-annual Silver bonus (2,500 EDGE = 5,000 mi):
#     71,000 vs 68,640 → Δ = 2,360; no cap binds (Burgundy cap 2,00,000).
#
#   route_shape — wallet {Atlas, TravelOne}, everything on TravelOne:
#     dining→Atlas would GAIN (72,600 → 84,200, Δ = −11,600): the single-card
#     route declines the swap by design, and the row must say so rather than
#     pretend the chosen card wins.


def _real_context(
    snapshot: CatalogSnapshot,
    wallet_ids: tuple[UUID, ...],
    *,
    travel: int,
    dining: int,
) -> PlanningContext:
    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=12,
        num_passengers=2,
        confidence=0.95,
    )
    resolution = resolve_goal(intent, snapshot, today=TODAY)
    assert isinstance(resolution, GoalResolution)
    goal = TravelGoal(id=uuid4(), user_id=uuid4(), status="active", **resolution.model_dump())
    return PlanningContext(
        user_id=goal.user_id,
        goal=goal,
        requirement=estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot=snapshot,
        wallet=tuple(WalletCard(card_id=c, current_points_balance=0) for c in wallet_ids),
        spend_profile=SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=travel),
                SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=dining),
            )
        ),
        horizon_months=12,
    )


def _attributed_rows(
    context: PlanningContext,
    assignment_cards: dict[SpendCategory, UUID],
    *,
    single_card_route: bool = False,
) -> dict[SpendCategory, object]:
    opportunities = enumerate_opportunities(context)
    index = {(o.card_id, o.category_slug): o for o in opportunities.opportunities}
    assignment: Assignment = {
        category: index[(card_id, category)] for category, card_id in assignment_cards.items()
    }
    rows = allocation_detail(
        assignment,
        context.spend_profile,
        all_opportunities=opportunities.opportunities,
        available_card_ids=frozenset(w.card_id for w in context.wallet),
        context=context,
        single_card_route=single_card_route,
    )
    return {row.category_slug: row for row in rows}


def test_runner_up_reason_transfer_cap_golden(snapshot: CatalogSnapshot) -> None:
    """The user-reported Atlas confusion: Atlas travel rates 10 mi/₹100 vs
    TravelOne's 4, yet travel routes to TravelOne — because moving it would
    strand points behind the 30,000 EDGE/yr transfer cap. The row must name
    the cap and carry the verified whole-plan delta (84,200 − 60,000)."""
    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: ATLAS},
    )
    travel = rows[SpendCategory.TRAVEL]
    assert travel.runner_up_card_id == ATLAS
    assert travel.runner_up_miles_per_100inr == Decimal("10.0000")
    assert travel.runner_up_reason == "transfer_cap"
    assert travel.runner_up_plan_delta_miles == 24_200


def test_runner_up_reason_milestone_golden(snapshot: CatalogSnapshot) -> None:
    """Burgundy dining rates 4.8 mi/₹100 vs Atlas's 4.0, but moving dining off
    Atlas forfeits the ₹3L-annual Silver bonus — milestone-keeping is the
    verified cause (71,000 − 68,640 = 2,360), not the transfer cap."""
    context = _real_context(snapshot, (ATLAS, BURGUNDY), travel=20_000, dining=30_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: ATLAS},
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == BURGUNDY
    assert dining.runner_up_reason == "milestone"
    assert dining.runner_up_plan_delta_miles == 2_360


def test_runner_up_reason_route_shape_when_swap_would_gain(
    snapshot: CatalogSnapshot,
) -> None:
    """A forced single-card route (simplest/cheapest archetypes) can decline a
    swap that would earn MORE overall — the row must own that trade-off
    (negative delta) instead of implying the chosen card wins the category."""
    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: TRAVELONE},
        single_card_route=True,
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == ATLAS
    assert dining.runner_up_reason == "route_shape"
    assert dining.runner_up_plan_delta_miles == -11_600


def test_gaining_swap_on_hill_climbed_route_asserts_no_cause(
    snapshot: CatalogSnapshot,
) -> None:
    """Reviewer finding: on a hill-climbed route a swap that would GAIN is a
    search artifact (the climb optimizes an optimistic bound; this verifier
    is stricter), NOT a design choice — asserting 'route_shape' would be a
    lie, so the row ships no cause (falls back to the neutral sentence)."""
    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: TRAVELONE},
        # Same all-on-one-card assignment, NOT marked as a forced route.
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == ATLAS  # comparison still ships
    assert dining.runner_up_reason is None
    assert dining.runner_up_plan_delta_miles is None


def test_runner_up_reason_fewer_total_golden(snapshot: CatalogSnapshot) -> None:
    """No cap binds and no milestone is lost, but the swap still verifiably
    loses: dining ₹1,000/mo on TravelOne pools with travel and transfers;
    moved to Atlas it earns 20 EDGE/mo × 11 = 220, below the link's 500-point
    minimum — stranded. 66,220 − 66,000 = 220."""
    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=1_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: TRAVELONE},
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == ATLAS  # rates 4.0 vs TravelOne's 2.0
    assert dining.runner_up_reason == "fewer_total"
    assert dining.runner_up_plan_delta_miles == 220


def test_runner_up_reason_equal_total(snapshot: CatalogSnapshot) -> None:
    """₹10/mo dining floors to zero points on both Atlas (chosen, 4.0) and
    Burgundy (runner-up, 4.8) — the swap changes nothing: 66,000 = 66,000."""
    context = _real_context(snapshot, (ATLAS, BURGUNDY, TRAVELONE), travel=150_000, dining=10)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: ATLAS},
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == BURGUNDY
    assert dining.runner_up_reason == "equal_total"
    assert dining.runner_up_plan_delta_miles == 0


def test_single_card_route_counterfactual_uses_fewest_actions_basis(
    snapshot: CatalogSnapshot,
) -> None:
    """Reviewer finding: simplest/cheapest_viable claims are generated with
    include_idle_balances=False, so their counterfactual must use the same
    basis — otherwise the delta is measured against a plan the user was never
    shown. Wallet holds an idle 5,000-EDGE Atlas balance outside the
    all-on-TravelOne assignment:

      fewest-actions basis (idle excluded from the current side): current
        66,000 + 6,600 = 72,600; swap dining→Atlas brings Atlas INTO the
        assignment, so its balance counts on the swapped side either way —
        (6,600 + 2,500 Silver + 5,000 balance) EDGE ×2 = 28,200 + 66,000
        travel = 94,200. Δ = 72,600 − 94,200 = −21,600.
      (The default basis would say −11,600 — a number inconsistent with the
      route's own claimed total.)"""
    context = _real_context(
        snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000
    ).model_copy(
        update={
            "wallet": (
                WalletCard(card_id=ATLAS, current_points_balance=5_000),
                WalletCard(card_id=TRAVELONE, current_points_balance=0),
            )
        }
    )
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: TRAVELONE},
        single_card_route=True,
    )
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_reason == "route_shape"
    assert dining.runner_up_plan_delta_miles == -21_600


def test_claimed_estimate_marks_cap_bound_currencies(snapshot: CatalogSnapshot) -> None:
    """The engine-owned attribution fact: the EDGE→KrisFlyer cap (30,000/yr)
    actually clamps the all-on-Atlas plan (89,100 EDGE earned > cap), so the
    currency is marked; the tiny-dining strand case (220 EDGE, under the
    500-point minimum — the cap never engages) is NOT marked."""
    from app.optimization.allocation import claimed_estimate

    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000)
    opportunities = enumerate_opportunities(context)
    index = {(o.card_id, o.category_slug): o for o in opportunities.opportunities}
    edge_currency = index[(ATLAS, SpendCategory.TRAVEL)].transfer_path.currency_id

    capped = claimed_estimate(
        {
            SpendCategory.TRAVEL: index[(ATLAS, SpendCategory.TRAVEL)],
            SpendCategory.DINING: index[(ATLAS, SpendCategory.DINING)],
        },
        context,
    )
    assert edge_currency in capped.cap_bound_currencies

    strand_context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=1_000)
    strand_index = {
        (o.card_id, o.category_slug): o
        for o in enumerate_opportunities(strand_context).opportunities
    }
    stranded = claimed_estimate(
        {
            SpendCategory.TRAVEL: strand_index[(TRAVELONE, SpendCategory.TRAVEL)],
            SpendCategory.DINING: strand_index[(ATLAS, SpendCategory.DINING)],
        },
        strand_context,
    )
    assert stranded.cap_bound_currencies == frozenset()


def test_runner_up_reason_absent_when_chosen_rates_higher_or_no_context(
    snapshot: CatalogSnapshot,
) -> None:
    """Attribution only fires when the runner-up genuinely rates higher AND a
    context was provided: a lower-rated runner-up needs no excuse, and the
    context-less call (older callers, synthetic tests) stays back-compatible."""
    context = _real_context(snapshot, (ATLAS, TRAVELONE), travel=150_000, dining=30_000)
    rows = _attributed_rows(
        context,
        {SpendCategory.TRAVEL: TRAVELONE, SpendCategory.DINING: ATLAS},
    )
    # Dining's runner-up (TravelOne, 2.0) rates BELOW Atlas (4.0) — no reason.
    dining = rows[SpendCategory.DINING]
    assert dining.runner_up_card_id == TRAVELONE
    assert dining.runner_up_reason is None
    assert dining.runner_up_plan_delta_miles is None

    # Same assignment without a context: comparison ships, attribution doesn't.
    opportunities = enumerate_opportunities(context)
    index = {(o.card_id, o.category_slug): o for o in opportunities.opportunities}
    rows_no_ctx = allocation_detail(
        {
            SpendCategory.TRAVEL: index[(TRAVELONE, SpendCategory.TRAVEL)],
            SpendCategory.DINING: index[(ATLAS, SpendCategory.DINING)],
        },
        context.spend_profile,
        all_opportunities=opportunities.opportunities,
        available_card_ids=frozenset({ATLAS, TRAVELONE}),
    )
    travel_no_ctx = next(r for r in rows_no_ctx if r.category_slug == SpendCategory.TRAVEL)
    assert travel_no_ctx.runner_up_card_id == ATLAS
    assert travel_no_ctx.runner_up_reason is None


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
