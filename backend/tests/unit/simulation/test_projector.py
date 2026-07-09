"""Stage 8 — month-by-month timeline simulation over the real seed catalog.

The projector is the cap-truth layer: Stage 5's static blend estimates a rate,
the ledger here actually meters spend through caps, milestones and transfer
delays month by month. Every golden value below is hand-computed from seed
rows (seeds/catalog/*.yaml) — a failing test means either the projector or
the seeds changed, both of which must be deliberate.

Shared arithmetic facts used throughout (seed-traceable):

  Infinia   travel 16.65/₹100 (cap ₹150k/mo), default 3.33; link 1:1,
            min 1,000, fee 0, processing 7–10 days (arrival still +1 month)
  DCB       same rates/currency as Infinia; quarterly milestone ₹4L → 10,000
  Atlas     travel 5.00/₹100 (cap ₹200k/mo), default 2.00; link 1:2,
            min 500, fee ₹235, ANNUAL LINK CAP 30,000 EDGE; milestones
            ₹3L → 2,500 (+₹7.5L → 2,500, ₹15L → 5,000); welcome 2,500
  Magnus    Burgundy: default 6.00; link 5:4, min 500, fee ₹235
  Amex      Plat Travel default 2.00; annual milestones ₹1.9L → 15,000,
            ₹4L → 25,000
  Goal      Hyderabad→Singapore business × 2 pax = 45,000 × 2 = 90,000 miles
            (post-Nov-2025 Zone 6 saver); buffer 5% ⇒ 4,500
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain import (
    CandidateStrategy,
    CatalogSnapshot,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    SimulationOutcome,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TransferPlanItem,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.simulation.projector import simulate

TODAY = date(2026, 7, 4)
KRISFLYER = seed_id("partner", "krisflyer")


def _context(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int],
    wallet: tuple[tuple[str, int], ...] = (("hdfc-infinia", 20_000),),
    horizon_months: int = 8,
) -> PlanningContext:
    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=horizon_months,
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
        wallet=tuple(
            WalletCard(card_id=seed_id("card", slug), current_points_balance=balance)
            for slug, balance in wallet
        ),
        spend_profile=SpendProfile(
            items=tuple(
                SpendProfileItem(category_slug=cat, monthly_spend_inr=amount)
                for cat, amount in spend.items()
            )
        ),
        horizon_months=horizon_months,
    )


def _strategy(
    allocation: dict[SpendCategory, str],
    transfers: tuple[tuple[str, int, int], ...] = (),
    acquire: tuple[str, ...] = (),
    extra_cards: tuple[str, ...] = (),
) -> CandidateStrategy:
    """Build a status-quo strategy from slugs. transfers = (from_slug, points,
    planned_month), always into KrisFlyer."""
    used = tuple(
        dict.fromkeys(
            [seed_id("card", slug) for slug in allocation.values()]
            + [seed_id("card", slug) for slug, _, _ in transfers]
            + [seed_id("card", slug) for slug in extra_cards]
        )
    )
    return CandidateStrategy(
        strategy_id="status_quo_optimized-1",
        archetype="status_quo_optimized",
        cards_used=used,
        cards_to_acquire=tuple(seed_id("card", slug) for slug in acquire),
        spend_allocation={cat: seed_id("card", slug) for cat, slug in allocation.items()},
        transfer_plan=tuple(
            TransferPlanItem(
                from_card_id=seed_id("card", slug),
                to_partner_id=KRISFLYER,
                points=points,
                planned_month=month,
            )
            for slug, points, month in transfers
        ),
        claimed_total_miles=0,
    )


def _balance(outcome: SimulationOutcome, month: int, card_slug: str) -> int:
    return outcome.ledger[month].points_by_card[seed_id("card", card_slug)]


# ── The workhorse golden: Infinia status quo, one transfer, full horizon ──


def test_golden_infinia_end_to_end(snapshot: CatalogSnapshot) -> None:
    """Start 40,000 RP. Monthly earn: travel 400×16.65 = 6,660 + dining
    300×3.33 = 999 ⇒ 7,659/month exactly. Balance end of month m (pre-
    transfer): 40,000 + 7,659×(m+1). At month 6 that is 93,613; transfer
    92,000 (1:1, fee 0, 7–10 processing days ⇒ arrival month 7). Cumulative
    KrisFlyer at month 7 = 92,000 ≥ 90,000 required (45,000 × 2 pax, post-
    Nov-2025 chart) ⇒ goal at month 7, but 92,000 < 94,500 (required +
    4,500 buffer) ⇒ buffer_achieved False."""
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000},
        wallet=(("hdfc-infinia", 40_000),),
    )
    strategy = _strategy(
        {SpendCategory.TRAVEL: "hdfc-infinia", SpendCategory.DINING: "hdfc-infinia"},
        transfers=(("hdfc-infinia", 92_000, 6),),
    )
    outcome = simulate(strategy, context)

    assert len(outcome.ledger) == 8
    assert [entry.month for entry in outcome.ledger] == list(range(8))
    assert _balance(outcome, 0, "hdfc-infinia") == 47_659
    assert _balance(outcome, 5, "hdfc-infinia") == 85_954
    assert _balance(outcome, 6, "hdfc-infinia") == 1_613  # 93,613 − 92,000
    assert _balance(outcome, 7, "hdfc-infinia") == 9_272

    (execution,) = outcome.ledger[6].transfers_executed
    assert execution.points_sent == 92_000
    assert execution.miles_received == 92_000
    assert execution.fee_inr == 0
    assert execution.arrival_month == 7

    assert outcome.ledger[6].cumulative_target_miles == 0
    assert outcome.ledger[7].cumulative_target_miles == 92_000
    assert outcome.months_to_goal == 7
    assert outcome.miles_at_target_date == 92_000
    assert outcome.misses_goal is False
    assert outcome.buffer_achieved is False

    # points_earned_this_month is the earn delta, NOT the running balance: a
    # flat 7,659/month every month, unaffected by the month-6 transfer-out
    # (the balance drops, but earning doesn't). This is the honest monthly
    # accrual — the frontend charts its cumulative sum, so it must not inherit
    # the balance field's transfer-driven non-monotonicity.
    assert [e.points_earned_this_month for e in outcome.ledger] == [7_659] * 8
    assert outcome.total_fees_inr == 0
    assert outcome.strategy_id == "status_quo_optimized-1"


def test_golden_buffer_boundary(snapshot: CatalogSnapshot) -> None:
    """buffer_achieved flips exactly at required + buffer = 94,500 miles.
    (42,000 start + 7,659 × 7 = 95,613 available at month 6.)"""
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000},
        wallet=(("hdfc-infinia", 42_000),),
    )
    at_buffer = simulate(
        _strategy(
            {SpendCategory.TRAVEL: "hdfc-infinia", SpendCategory.DINING: "hdfc-infinia"},
            transfers=(("hdfc-infinia", 94_500, 6),),
        ),
        context,
    )
    assert at_buffer.miles_at_target_date == 94_500
    assert at_buffer.buffer_achieved is True

    one_under = simulate(
        _strategy(
            {SpendCategory.TRAVEL: "hdfc-infinia", SpendCategory.DINING: "hdfc-infinia"},
            transfers=(("hdfc-infinia", 94_499, 6),),
        ),
        context,
    )
    assert one_under.miles_at_target_date == 94_499
    assert one_under.buffer_achieved is False


def test_no_transfers_misses_goal_with_full_ledger(snapshot: CatalogSnapshot) -> None:
    """A strategy that never transfers earns points but no target miles: the
    full-horizon ledger is still returned (ranking needs the near-miss data),
    months_to_goal is None and misses_goal is True."""
    context = _context(snapshot, {SpendCategory.DINING: 30_000})
    outcome = simulate(_strategy({SpendCategory.DINING: "hdfc-infinia"}), context)
    assert len(outcome.ledger) == 8
    assert outcome.months_to_goal is None
    assert outcome.misses_goal is True
    assert outcome.miles_at_target_date == 0
    assert outcome.buffer_achieved is False


# ── Cap boundaries (the Stage 5 blend, now metered month by month) ──


def test_golden_cap_exactly_at_boundary(snapshot: CatalogSnapshot) -> None:
    """₹150,000 travel = exactly the Infinia SmartBuy cap: all spend earns
    16.65 ⇒ 1,500 × 16.65 = 24,975/month; cap_utilization exactly 1."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 150_000})
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)
    assert _balance(outcome, 0, "hdfc-infinia") == 20_000 + 24_975
    assert outcome.ledger[0].cap_utilization[seed_id("card", "hdfc-infinia")] == Decimal("1")


def test_golden_cap_one_hundred_over(snapshot: CatalogSnapshot) -> None:
    """₹150,100 travel: 1,500×16.65 = 24,975 accelerated + ₹100 overflow at
    base 3.33 = 3.33 ⇒ 24,978.33 floors to 24,978."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 150_100})
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)
    assert _balance(outcome, 0, "hdfc-infinia") == 20_000 + 24_978
    assert outcome.ledger[0].cap_utilization[seed_id("card", "hdfc-infinia")] == Decimal("1")


def test_golden_cap_one_hundred_under(snapshot: CatalogSnapshot) -> None:
    """₹149,900 travel: 1,499×16.65 = 24,958.35 floors to 24,958; utilization
    149,900/150,000 = 0.99933… quantizes (4dp ROUND_DOWN) to 0.9993."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 149_900})
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)
    assert _balance(outcome, 0, "hdfc-infinia") == 20_000 + 24_958
    assert outcome.ledger[0].cap_utilization[seed_id("card", "hdfc-infinia")] == Decimal("0.9993")


def test_cap_resets_monthly(snapshot: CatalogSnapshot) -> None:
    """The monthly cap meters each month independently: ₹200k travel earns the
    same blended 26,640 every month (1,500×16.65 + 500×3.33 = 24,975 + 1,665),
    not a degrading rate as cumulative spend grows."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 200_000})
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)
    for month in range(3):
        earned = _balance(outcome, month, "hdfc-infinia") - (
            20_000 if month == 0 else _balance(outcome, month - 1, "hdfc-infinia")
        )
        assert earned == 26_640, f"month {month}: {earned}"


# ── Milestones: quarterly reset, annual once, exact thresholds ──


def test_golden_dcb_quarterly_milestone_triggers_each_quarter(
    snapshot: CatalogSnapshot,
) -> None:
    """DCB ₹4L quarterly ⇒ 10,000 RP. ₹140k travel/month: cumulative in-quarter
    spend crosses 400,000 in month 2 (420k) and again in month 5. Earn
    1,400×16.65 = 23,310/month from a zero starting balance."""
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 140_000},
        wallet=(("hdfc-diners-black", 0),),
        horizon_months=6,
    )
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-diners-black"}), context)
    milestone = seed_id("milestone", "hdfc-diners-black:0")

    assert _balance(outcome, 1, "hdfc-diners-black") == 46_620
    assert outcome.ledger[2].milestones_triggered == (milestone,)
    assert _balance(outcome, 2, "hdfc-diners-black") == 69_930 + 10_000
    assert outcome.ledger[5].milestones_triggered == (milestone,)
    assert _balance(outcome, 5, "hdfc-diners-black") == 149_860 + 10_000
    assert not outcome.ledger[0].milestones_triggered
    assert not outcome.ledger[3].milestones_triggered


def test_golden_quarterly_milestone_exactly_at_threshold(snapshot: CatalogSnapshot) -> None:
    """₹200k/month on DCB (₹100k travel + ₹100k dining): cumulative hits
    400,000 EXACTLY in month 1 — ≥ threshold triggers, no off-by-one."""
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 100_000, SpendCategory.DINING: 100_000},
        wallet=(("hdfc-diners-black", 0),),
        horizon_months=3,
    )
    outcome = simulate(
        _strategy(
            {SpendCategory.TRAVEL: "hdfc-diners-black", SpendCategory.DINING: "hdfc-diners-black"}
        ),
        context,
    )
    assert outcome.ledger[1].milestones_triggered == (seed_id("milestone", "hdfc-diners-black:0"),)


def test_quarterly_milestone_one_rupee_under_never_triggers(snapshot: CatalogSnapshot) -> None:
    """₹133,333/month ⇒ quarter total 399,999 — one rupee short, every
    quarter, forever. The bonus must never fire."""
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 133_333},
        wallet=(("hdfc-diners-black", 0),),
        horizon_months=6,
    )
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-diners-black"}), context)
    assert all(not entry.milestones_triggered for entry in outcome.ledger)


def test_golden_amex_two_annual_tiers(snapshot: CatalogSnapshot) -> None:
    """Amex dining ₹100k/month at default 2.00 ⇒ 2,000/month. Tier 1 (₹1.9L ⇒
    15,000) crosses at month 1 (200k); tier 2 (₹4L ⇒ 25,000) exactly at month
    3. Each annual milestone fires ONCE in a ≤12-month horizon."""
    context = _context(
        snapshot,
        {SpendCategory.DINING: 100_000},
        wallet=(("amex-platinum-travel", 0),),
        horizon_months=6,
    )
    outcome = simulate(_strategy({SpendCategory.DINING: "amex-platinum-travel"}), context)
    tier1 = seed_id("milestone", "amex-platinum-travel:0")
    tier2 = seed_id("milestone", "amex-platinum-travel:1")

    assert outcome.ledger[1].milestones_triggered == (tier1,)
    assert _balance(outcome, 1, "amex-platinum-travel") == 4_000 + 15_000
    assert outcome.ledger[3].milestones_triggered == (tier2,)
    assert _balance(outcome, 3, "amex-platinum-travel") == 8_000 + 15_000 + 25_000
    assert not outcome.ledger[2].milestones_triggered
    assert not outcome.ledger[4].milestones_triggered  # annual: never re-fires
    assert not outcome.ledger[5].milestones_triggered


def test_golden_atlas_acquired_welcome_and_annual_milestone(
    snapshot: CatalogSnapshot,
) -> None:
    """Acquired Atlas: welcome 2,500 lands with the first spend month; the
    ₹3L annual milestone crosses exactly at month 2 (3 × ₹100k). Travel earns
    1,000 × 5.00 = 5,000/month. Joining fee ₹5,000 is the strategy's cost."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 100_000}, wallet=(), horizon_months=4)
    outcome = simulate(
        _strategy({SpendCategory.TRAVEL: "axis-atlas"}, acquire=("axis-atlas",)), context
    )
    welcome = seed_id("milestone", "axis-atlas:1")
    annual = seed_id("milestone", "axis-atlas:0")

    assert outcome.ledger[0].milestones_triggered == (welcome,)
    assert _balance(outcome, 0, "axis-atlas") == 5_000 + 2_500
    assert outcome.ledger[2].milestones_triggered == (annual,)
    assert _balance(outcome, 2, "axis-atlas") == 17_500 + 2_500
    assert outcome.total_fees_inr == 5_000


def test_welcome_bonus_not_awarded_to_wallet_card(snapshot: CatalogSnapshot) -> None:
    """The same Atlas in the wallet (not acquired) never re-earns its welcome
    bonus — only the ₹3L annual milestone fires."""
    context = _context(
        snapshot, {SpendCategory.TRAVEL: 100_000}, wallet=(("axis-atlas", 0),), horizon_months=4
    )
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "axis-atlas"}), context)
    welcome = seed_id("milestone", "axis-atlas:1")
    assert all(welcome not in entry.milestones_triggered for entry in outcome.ledger)
    assert _balance(outcome, 0, "axis-atlas") == 5_000


# ── Transfer mechanics: annual link cap, whole blocks, thresholds, delays ──


def test_golden_atlas_annual_link_cap_across_transfers(snapshot: CatalogSnapshot) -> None:
    """The Atlas→KrisFlyer link caps at 30,000 EDGE/year (1:2). First transfer
    of 25,000 converts fully (50,000 miles); the second is squeezed to the
    5,000 remaining under the cap (10,000 miles) regardless of balance."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 100_000}, wallet=(("axis-atlas", 30_000),))
    outcome = simulate(
        _strategy(
            {SpendCategory.TRAVEL: "axis-atlas"},
            transfers=(("axis-atlas", 25_000, 2), ("axis-atlas", 25_000, 5)),
        ),
        context,
    )
    (first,) = outcome.ledger[2].transfers_executed
    assert first.points_sent == 25_000
    assert first.miles_received == 50_000
    assert first.arrival_month == 3  # 3 processing days ⇒ next month

    (second,) = outcome.ledger[5].transfers_executed
    assert second.points_sent == 5_000
    assert second.miles_received == 10_000
    assert second.arrival_month == 6

    assert outcome.ledger[3].cumulative_target_miles == 50_000
    assert outcome.ledger[6].cumulative_target_miles == 60_000


def test_golden_magnus_whole_block_transfer_leaves_remainder(
    snapshot: CatalogSnapshot,
) -> None:
    """Magnus Burgundy 5:4 sends whole blocks only: of 12,347 planned points,
    2,469 blocks × 5 = 12,345 leave the card (⇒ 2,469 × 4 = 9,876 miles) and
    the 2-point remainder STAYS on the balance — flooring must never destroy
    points. Fee ₹235 per Axis transfer."""
    context = _context(
        snapshot, {SpendCategory.DINING: 30_000}, wallet=(("axis-magnus-burgundy", 12_347),)
    )
    outcome = simulate(
        _strategy(
            {SpendCategory.DINING: "axis-magnus-burgundy"},
            transfers=(("axis-magnus-burgundy", 12_347, 0),),
        ),
        context,
    )
    (execution,) = outcome.ledger[0].transfers_executed
    assert execution.points_sent == 12_345
    assert execution.miles_received == 9_876
    assert execution.fee_inr == 235
    # 12,347 start + 1,800 earned (300 × 6.00) − 12,345 sent = 1,802
    assert _balance(outcome, 0, "axis-magnus-burgundy") == 1_802
    assert outcome.total_fees_inr == 235


def test_transfer_below_min_threshold_is_skipped(snapshot: CatalogSnapshot) -> None:
    """900 < Infinia link min 1,000: no execution, no fee, balance intact."""
    context = _context(snapshot, {SpendCategory.DINING: 30_000})
    outcome = simulate(
        _strategy({SpendCategory.DINING: "hdfc-infinia"}, transfers=(("hdfc-infinia", 900, 0),)),
        context,
    )
    assert outcome.ledger[0].transfers_executed == ()
    assert _balance(outcome, 0, "hdfc-infinia") == 20_999
    assert outcome.total_fees_inr == 0


def test_transfer_limited_by_available_balance(snapshot: CatalogSnapshot) -> None:
    """Planned 60,000 with only 3 points on the card (0 start + ₹100 dining ⇒
    floor(3.33) = 3): 3 < min 1,000 ⇒ skipped, not partially forced."""
    context = _context(snapshot, {SpendCategory.DINING: 100}, wallet=(("hdfc-infinia", 0),))
    outcome = simulate(
        _strategy({SpendCategory.DINING: "hdfc-infinia"}, transfers=(("hdfc-infinia", 60_000, 0),)),
        context,
    )
    assert outcome.ledger[0].transfers_executed == ()
    assert _balance(outcome, 0, "hdfc-infinia") == 3


def test_transfer_with_no_link_is_skipped(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback has no KrisFlyer link by design: a (buggy) plan trying to
    transfer from it is ignored and the simulation continues (spec §11)."""
    context = _context(
        snapshot,
        {SpendCategory.DINING: 30_000},
        wallet=(("hdfc-infinia", 20_000), ("sbi-cashback", 5_000)),
    )
    outcome = simulate(
        _strategy(
            {SpendCategory.DINING: "hdfc-infinia"},
            transfers=(("sbi-cashback", 5_000, 0),),
            extra_cards=("sbi-cashback",),
        ),
        context,
    )
    assert outcome.ledger[0].transfers_executed == ()
    assert _balance(outcome, 0, "sbi-cashback") == 5_000


def test_transfer_at_final_month_arrives_after_target_date(
    snapshot: CatalogSnapshot,
) -> None:
    """100,000 points transferred in the LAST month (processing 7–10 days ⇒
    arrival month 2 = past the horizon): the miles never count toward the
    goal. The same transfer a month earlier achieves it — timing is the
    entire failure mode this engine exists to catch."""
    context = _context(
        snapshot,
        {SpendCategory.DINING: 30_000},
        wallet=(("hdfc-infinia", 100_000),),
        horizon_months=2,
    )
    late = simulate(
        _strategy(
            {SpendCategory.DINING: "hdfc-infinia"}, transfers=(("hdfc-infinia", 100_000, 1),)
        ),
        context,
    )
    (execution,) = late.ledger[1].transfers_executed
    assert execution.arrival_month == 2  # recorded, but beyond the ledger
    assert late.miles_at_target_date == 0
    assert late.misses_goal is True

    early = simulate(
        _strategy(
            {SpendCategory.DINING: "hdfc-infinia"}, transfers=(("hdfc-infinia", 100_000, 0),)
        ),
        context,
    )
    assert early.ledger[1].cumulative_target_miles == 100_000
    assert early.months_to_goal == 1
    assert early.misses_goal is False
    assert early.buffer_achieved is True  # 100,000 ≥ 94,500


def test_transfer_fee_charged_per_execution(snapshot: CatalogSnapshot) -> None:
    """Seed links are all fee-free, so fee accounting is exercised through a
    snapshot with the Infinia link's fee set to ₹500: one transfer ⇒ fee on
    the execution record and in total_fees_inr."""
    fee_links = tuple(
        link.model_copy(update={"transfer_fee_inr": 500})
        if link.currency_id == seed_id("currency", "hdfc-rp-premium")
        and link.partner_id == KRISFLYER
        else link
        for link in snapshot.transfer_links
    )
    fee_snapshot = snapshot.model_copy(update={"transfer_links": fee_links})
    context = _context(fee_snapshot, {SpendCategory.DINING: 30_000})
    outcome = simulate(
        _strategy({SpendCategory.DINING: "hdfc-infinia"}, transfers=(("hdfc-infinia", 10_000, 0),)),
        context,
    )
    (execution,) = outcome.ledger[0].transfers_executed
    assert execution.fee_inr == 500
    assert outcome.total_fees_inr == 500


# ── Contract guards ──


def test_determinism_byte_identical(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot, {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000})
    strategy = _strategy(
        {SpendCategory.TRAVEL: "hdfc-infinia", SpendCategory.DINING: "hdfc-infinia"},
        transfers=(("hdfc-infinia", 72_000, 6),),
    )
    a = simulate(strategy, context)
    b = simulate(strategy, context)
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()


def test_unallocated_profile_category_fails_loudly(snapshot: CatalogSnapshot) -> None:
    """Stage 7 guarantees complete allocations; a partial strategy reaching
    the projector is a generator bug and must raise, not under-simulate."""
    context = _context(snapshot, {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000})
    partial = _strategy({SpendCategory.TRAVEL: "hdfc-infinia"})
    with pytest.raises(ValueError, match="dining"):
        simulate(partial, context)


def test_allocation_to_unused_card_fails_loudly(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot, {SpendCategory.DINING: 30_000})
    strategy = _strategy({SpendCategory.DINING: "hdfc-infinia"})
    broken = strategy.model_copy(update={"cards_used": (seed_id("card", "axis-atlas"),)})
    with pytest.raises(ValueError, match="not in cards_used"):
        simulate(broken, context)


def test_unsupported_rule_cap_period_fails_loudly(snapshot: CatalogSnapshot) -> None:
    """v1 meters monthly caps only. A rule carrying a quarterly/annual spend
    cap must raise rather than silently overstate earnings (Unknown Over
    Incorrect)."""
    rules = tuple(
        rule.model_copy(update={"annual_cap_inr": 1_000_000})
        if rule.id == seed_id("category", "hdfc-infinia:travel")
        else rule
        for rule in snapshot.category_rules
    )
    capped_snapshot = snapshot.model_copy(update={"category_rules": rules})
    context = _context(capped_snapshot, {SpendCategory.TRAVEL: 40_000})
    with pytest.raises(ValueError, match="annual"):
        simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)


def test_unsupported_quarterly_rule_cap_fails_loudly(snapshot: CatalogSnapshot) -> None:
    """The other half of the cap guard: quarterly_cap_inr alone must also
    raise (reviewer finding, 2026-07-04 — only the annual branch was pinned)."""
    rules = tuple(
        rule.model_copy(update={"quarterly_cap_inr": 500_000})
        if rule.id == seed_id("category", "hdfc-infinia:travel")
        else rule
        for rule in snapshot.category_rules
    )
    context = _context(
        snapshot.model_copy(update={"category_rules": rules}), {SpendCategory.TRAVEL: 40_000}
    )
    with pytest.raises(ValueError, match="quarterly"):
        simulate(_strategy({SpendCategory.TRAVEL: "hdfc-infinia"}), context)


def test_spend_bonus_without_threshold_is_excluded(snapshot: CatalogSnapshot) -> None:
    """SIM-001 §11 'invalid milestone → exclude': a spend_bonus row missing
    its threshold is skipped silently — no trigger, no crash, no bonus."""
    milestones = tuple(
        m.model_copy(update={"spend_threshold_inr": None})
        if m.id == seed_id("milestone", "hdfc-diners-black:0")
        else m
        for m in snapshot.milestones
    )
    context = _context(
        snapshot.model_copy(update={"milestones": milestones}),
        {SpendCategory.TRAVEL: 140_000},
        wallet=(("hdfc-diners-black", 0),),
        horizon_months=6,
    )
    outcome = simulate(_strategy({SpendCategory.TRAVEL: "hdfc-diners-black"}), context)
    assert all(not entry.milestones_triggered for entry in outcome.ledger)
    assert _balance(outcome, 2, "hdfc-diners-black") == 69_930  # no +10,000
