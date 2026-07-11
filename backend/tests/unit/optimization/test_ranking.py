"""Stage 9 — ranking: prune → hard rules → config-weighted scoring.

Synthetic candidates over the real seed catalog's card/link ids (the risk
sub-score reads real transfer links). Weights come from the real versioned
config (config/ranking-weights-v1.yaml: 35/20/15/10/10/10, near-tie 2.0).

Reference hand computation (test_golden_score_breakdown): single achieving
candidate, horizon 8, months_to_goal 7, buffer achieved, fees 30,235,
2 cards / 1 acquisition / 2 transfers, all spend on the acquired card,
one transfer through the 10-day HDFC link:

  goal_achievement    (8−7)/8 × 90 + 10        = 21.25
  efficiency          only candidate           = 100
  cost                only candidate           = 100
  simplicity          100 − 15×1 − 25×1 − 5×1  = 55
  portfolio_util      0 / 70,000 wallet spend  = 0
  risk                100 − 10 (slow transfer) = 90
  composite (35×21.25 + 20×100 + 15×100 + 10×55 + 10×0 + 10×90)/100
            = 5,693.75/100 = 56.9375 → 56.94 (ROUND_HALF_UP, 2dp)
"""

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

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
    StrategyArchetype,
    TransferPlanItem,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.ranking import load_ranking_weights, rank, reconcile_claim

TODAY = date(2026, 7, 4)
WEIGHTS_PATH = Path("config/ranking-weights-v1.yaml")

INFINIA = seed_id("card", "hdfc-infinia")
BURGUNDY = seed_id("card", "axis-magnus-burgundy")
KRISFLYER = seed_id("partner", "krisflyer")


@pytest.fixture(scope="module")
def weights():  # type: ignore[no-untyped-def]
    return load_ranking_weights(WEIGHTS_PATH)


def _context(snapshot: CatalogSnapshot) -> PlanningContext:
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
    return PlanningContext(
        user_id=goal.user_id,
        goal=goal,
        requirement=estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot=snapshot,
        wallet=(WalletCard(card_id=INFINIA, current_points_balance=20_000),),
        spend_profile=SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=40_000),
                SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=30_000),
            )
        ),
        horizon_months=8,
    )


def _strategy(
    strategy_id: str,
    *,
    allocation: dict[SpendCategory, UUID],
    acquire: tuple[UUID, ...] = (),
    transfers: tuple[tuple[UUID, int], ...] = ((INFINIA, 73_613),),
    claimed: int = 90_000,
) -> CandidateStrategy:
    cards = tuple(sorted({*allocation.values(), *(c for c, _ in transfers)}, key=str))
    return CandidateStrategy(
        strategy_id=strategy_id,
        archetype=StrategyArchetype.STATUS_QUO_OPTIMIZED,
        cards_used=cards,
        cards_to_acquire=acquire,
        spend_allocation=allocation,
        transfer_plan=tuple(
            TransferPlanItem(
                from_card_id=card_id, to_partner_id=KRISFLYER, points=points, planned_month=6
            )
            for card_id, points in transfers
        ),
        claimed_total_miles=claimed,
    )


def _outcome(
    strategy_id: str,
    *,
    months: int | None,
    miles: int,
    fees: int = 0,
    buffer: bool = True,
    misses: bool = False,
) -> SimulationOutcome:
    return SimulationOutcome(
        strategy_id=strategy_id,
        ledger=(),
        months_to_goal=months,
        miles_at_target_date=miles,
        total_fees_inr=fees,
        buffer_achieved=buffer,
        misses_goal=misses,
    )


# The near-tie pair (module docstring math, plus):
#   X: months 5, miles 100,000, fees 30,235; travel→Burgundy dining→Infinia,
#      acquires Burgundy, 2 transfers → 43.75/100/0/55/42.85/90 → 54.10
#   Y: months 6, miles 95,000, fees 0; all on Infinia, 1 transfer
#      → 32.5/0/100/100/100/90 → 55.38.  Δ = 1.28 < 2.0 → co-recommended.
def _pair_x() -> tuple[CandidateStrategy, SimulationOutcome]:
    strategy = _strategy(
        "x",
        allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: INFINIA},
        acquire=(BURGUNDY,),
        transfers=((BURGUNDY, 96_600), (INFINIA, 26_993)),
        claimed=100_000,
    )
    return strategy, _outcome("x", months=5, miles=100_000, fees=30_235)


def _pair_y() -> tuple[CandidateStrategy, SimulationOutcome]:
    strategy = _strategy(
        "y",
        allocation={SpendCategory.TRAVEL: INFINIA, SpendCategory.DINING: INFINIA},
        transfers=((INFINIA, 95_000),),
        claimed=95_000,
    )
    return strategy, _outcome("y", months=6, miles=95_000, fees=0)


# ── Config ────────────────────────────────────────────────────────────────


def test_weights_config_loads(weights) -> None:  # type: ignore[no-untyped-def]
    assert weights.version == "1"
    total = (
        weights.goal_achievement
        + weights.efficiency
        + weights.cost
        + weights.simplicity
        + weights.portfolio_utilization
        + weights.risk
    )
    assert total == Decimal("100")
    assert weights.near_tie_threshold == Decimal("2.0")


# ── Scoring ───────────────────────────────────────────────────────────────


def test_golden_score_breakdown(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """Full hand-computed composite for one candidate (module docstring)."""
    strategy = _strategy(
        "solo",
        allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: BURGUNDY},
        acquire=(BURGUNDY,),
        transfers=((BURGUNDY, 96_600), (INFINIA, 20_000)),
        claimed=97_280,
    )
    outcome = _outcome("solo", months=7, miles=97_280, fees=30_235)
    (ranked,) = rank(((strategy, outcome),), _context(snapshot), weights)
    breakdown = ranked.score_breakdown
    assert breakdown.goal_achievement == Decimal("21.25")
    assert breakdown.efficiency == Decimal("100")
    assert breakdown.cost == Decimal("100")
    assert breakdown.simplicity == Decimal("55")
    assert breakdown.portfolio_utilization == Decimal("0")
    assert breakdown.risk == Decimal("90")
    assert ranked.score == Decimal("56.94")
    assert ranked.rank == 1
    assert ranked.co_recommended is False


def test_misses_goal_never_ranks_first(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """Hard rules before weights: a candidate that misses in simulation ranks
    below every achieving one, even with more miles and zero fees."""
    achieving = _pair_x()
    missing_strategy = _strategy(
        "miss",
        allocation={SpendCategory.TRAVEL: INFINIA, SpendCategory.DINING: INFINIA},
        transfers=((INFINIA, 120_000),),
        claimed=120_000,
    )
    missing = (missing_strategy, _outcome("miss", months=None, miles=120_000, misses=True))
    ranked = rank((missing, achieving), _context(snapshot), weights)
    assert [r.strategy.strategy_id for r in ranked] == ["x", "miss"]
    assert ranked[1].rank == 2


def test_golden_near_tie_co_recommendation(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """55.38 vs 54.10: Δ = 1.28 < 2.0 → both co-recommended, honest about it."""
    ranked = rank((_pair_x(), _pair_y()), _context(snapshot), weights)
    assert [r.strategy.strategy_id for r in ranked] == ["y", "x"]
    assert ranked[0].score == Decimal("55.38")
    assert ranked[1].score == Decimal("54.10")
    assert ranked[0].co_recommended is True
    assert ranked[1].co_recommended is True


def test_headline_differentiators(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """Deterministic narration input: X is uniquely fastest; Y acquires
    nothing while another candidate does."""
    ranked = rank((_pair_x(), _pair_y()), _context(snapshot), weights)
    by_id = {r.strategy.strategy_id: r.headline_differentiator for r in ranked}
    assert by_id == {"x": "fastest", "y": "no new cards"}


# ── Per-category allocation detail (the story) ─────────────────────────────


def test_allocation_details_absent_without_opportunities(
    snapshot: CatalogSnapshot, weights
) -> None:  # type: ignore[no-untyped-def]
    """Backward-compatible: rank() without an OpportunitySet still ranks, and
    each RankedStrategy simply carries no allocation detail."""
    (ranked,) = rank((_pair_y(),), _context(snapshot), weights)
    assert ranked.allocation_details == ()


def test_allocation_details_attached_from_opportunities(
    snapshot: CatalogSnapshot, weights
) -> None:  # type: ignore[no-untyped-def]
    """Given the real OpportunitySet, each ranked strategy gains per-category
    earn detail resolved from the priced opportunities for its routing."""
    from app.valuation.opportunities import enumerate_opportunities

    context = _context(snapshot)
    opportunities = enumerate_opportunities(context)
    # Route both categories through Infinia (a wallet card with priced paths).
    pair = _pair_y()
    (ranked,) = rank((pair,), context, weights, opportunities=opportunities)

    details = {d.category_slug: d for d in ranked.allocation_details}
    assert set(details) == {SpendCategory.TRAVEL, SpendCategory.DINING}
    travel = details[SpendCategory.TRAVEL]
    assert travel.card_id == INFINIA
    assert travel.monthly_spend_inr == 40_000  # from _context spend profile
    # The rate is a real priced value (positive); the exact per-category math is
    # golden-tested in test_explain.py, so here we only assert the detail was
    # resolved from the actual opportunity, not fabricated.
    assert travel.earn_rate > 0
    assert travel.effective_miles_per_100inr > 0


# ── Pruning ───────────────────────────────────────────────────────────────


def test_dominated_strategy_is_pruned(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """Z is a different plan (different transfer batch) with identical
    complexity/risk/fees but slower and fewer miles → dominated → never
    scored."""
    x_strategy, x_outcome = _pair_x()
    z_strategy = _strategy(
        "z",
        allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: INFINIA},
        acquire=(BURGUNDY,),
        transfers=((BURGUNDY, 96_000), (INFINIA, 26_993)),
        claimed=90_000,
    )
    z_outcome = _outcome("z", months=7, miles=90_000, fees=30_235)
    ranked = rank(((z_strategy, z_outcome), (x_strategy, x_outcome)), _context(snapshot), weights)
    assert [r.strategy.strategy_id for r in ranked] == ["x"]


def test_acquiring_candidate_survives_domination_by_a_cheaper_no_new_card_option(
    snapshot: CatalogSnapshot, weights
) -> None:  # type: ignore[no-untyped-def]
    """The bug this exemption exists to fix: a status-quo (no new card) plan
    with more miles AND lower fees than an acquiring plan would classically
    dominate it — but "add one cheap card" is a different trade-off a
    cost-conscious user weighs against "use what I have," not a strict
    downgrade of it. W (acquiring, fewer miles, higher fees than Y) must
    still reach scoring alongside Y."""
    y_strategy, y_outcome = _pair_y()  # no acquisition: months 6, miles 95,000, fees 0
    w_strategy = _strategy(
        "w",
        allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: BURGUNDY},
        acquire=(BURGUNDY,),
        transfers=((BURGUNDY, 51_282),),
        claimed=51_282,
    )
    w_outcome = _outcome("w", months=7, miles=51_282, fees=10_000)  # worse on every dimension
    ranked = rank(((w_strategy, w_outcome), (y_strategy, y_outcome)), _context(snapshot), weights)
    assert {r.strategy.strategy_id for r in ranked} == {"w", "y"}


def test_goal_missing_acquisition_gets_no_dominance_exemption(
    snapshot: CatalogSnapshot, weights
) -> None:  # type: ignore[no-untyped-def]
    """The exemption is scoped to GOAL-ACHIEVING acquisitions only: a
    candidate that acquires a card but still misses the goal in simulation
    is pruned normally when dominated — the achieving-before-missing hard
    rule already excludes it from recommendation, so exempting it here
    would only add dead weight, not a real user-facing option.

    Both strategies use Infinia only (no acquisition, no risk penalty from a
    Burgundy transfer) so risk_penalty ties at 0 and "missing" is dominated
    on every OTHER dimension cleanly — isolating the months/misses boundary
    instead of an incidental risk-penalty difference."""
    dominating_strategy, dominating_outcome = _pair_y()  # months 6, miles 95,000, fees 0
    missing_strategy = _strategy(
        "missing",
        allocation={SpendCategory.TRAVEL: INFINIA, SpendCategory.DINING: INFINIA},
        acquire=(INFINIA,),  # synthetic: forces acquires=True without Burgundy's risk penalty
        transfers=((INFINIA, 30_000),),
        claimed=30_000,
    )
    missing_outcome = _outcome("missing", months=None, miles=30_000, fees=10_000, misses=True)
    ranked = rank(
        ((missing_strategy, missing_outcome), (dominating_strategy, dominating_outcome)),
        _context(snapshot),
        weights,
    )
    assert [r.strategy.strategy_id for r in ranked] == ["y"]


def test_acquiring_candidate_still_dominated_by_a_better_acquiring_candidate(
    snapshot: CatalogSnapshot, weights
) -> None:  # type: ignore[no-untyped-def]
    """The exemption is scoped to acquiring-vs-non-acquiring only: two
    acquiring candidates still prune normally (this is the pre-existing
    test_dominated_strategy_is_pruned fixture, re-asserted here to pin the
    boundary explicitly)."""
    x_strategy, x_outcome = _pair_x()  # acquires Burgundy: months 5, miles 100,000, fees 30,235
    z_strategy = _strategy(
        "z",
        allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: INFINIA},
        acquire=(BURGUNDY,),
        transfers=((BURGUNDY, 96_000), (INFINIA, 26_993)),
        claimed=90_000,
    )
    z_outcome = _outcome("z", months=7, miles=90_000, fees=30_235)  # worse on every dimension
    ranked = rank(((z_strategy, z_outcome), (x_strategy, x_outcome)), _context(snapshot), weights)
    assert [r.strategy.strategy_id for r in ranked] == ["x"]


def test_duplicate_strategies_are_merged(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """Same allocation + acquisitions + transfer plan = the same plan."""
    strategy, outcome = _pair_y()
    twin = strategy.model_copy(update={"strategy_id": "y2"})
    ranked = rank(
        ((strategy, outcome), (twin, _outcome("y2", months=6, miles=95_000))),
        _context(snapshot),
        weights,
    )
    assert len(ranked) == 1
    assert ranked[0].strategy.strategy_id == "y"


# ── claimed_total_miles reconciliation (deferred from Phase 3) ────────────


def test_reconcile_relabels_claim_with_simulated_truth(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Where simulation disagrees with the generator, the simulation wins:
    the claim is re-labeled and a >10% gap flags a generator bug in logs."""
    strategy, _ = _pair_x()
    outcome = _outcome("x", months=6, miles=80_000, fees=30_235)
    with caplog.at_level(logging.WARNING, logger="app.optimization.ranking"):
        reconciled = reconcile_claim(strategy, outcome)
    assert reconciled.claimed_total_miles == 80_000
    assert any("100,000" in note and "80,000" in note for note in reconciled.assumptions)
    assert any("generator" in record.message.lower() for record in caplog.records)


def test_reconcile_is_a_noop_when_claims_agree(caplog: pytest.LogCaptureFixture) -> None:
    strategy, outcome = _pair_x()
    with caplog.at_level(logging.WARNING, logger="app.optimization.ranking"):
        assert reconcile_claim(strategy, outcome) is strategy
    assert not caplog.records


def test_rank_applies_reconciliation(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    """rank() itself must surface simulated numbers on the ranked strategy."""
    strategy, _ = _pair_x()
    outcome = _outcome("x", months=6, miles=80_000, fees=30_235)
    (ranked,) = rank(((strategy, outcome),), _context(snapshot), weights)
    assert ranked.strategy.claimed_total_miles == 80_000


# ── Contract guarantees ───────────────────────────────────────────────────


def test_empty_input_ranks_nothing(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    assert rank((), _context(snapshot), weights) == ()


def test_ranks_are_sequential_and_breakdowns_present(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    ranked = rank((_pair_x(), _pair_y()), _context(snapshot), weights)
    assert [r.rank for r in ranked] == [1, 2]
    for entry in ranked:
        for field in (
            "goal_achievement",
            "efficiency",
            "cost",
            "simplicity",
            "portfolio_utilization",
            "risk",
        ):
            value = getattr(entry.score_breakdown, field)
            assert Decimal(0) <= value <= Decimal(100)


def test_determinism(snapshot: CatalogSnapshot, weights) -> None:  # type: ignore[no-untyped-def]
    context = _context(snapshot)
    assert rank((_pair_x(), _pair_y()), context, weights) == rank(
        (_pair_x(), _pair_y()), context, weights
    )
