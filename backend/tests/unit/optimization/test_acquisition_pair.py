"""Guided-flow slice 8 — the acquisition pair (decision log 2026-07-13, D8–D9).

When the current wallet can't clear the goal, the package must expose exactly
two labeled acquisition routes: the **cheapest** (the goal-achieving acquiring
route with the lowest card fees — selected by FEE, not by the
`cheapest_viable` archetype label, because Stage 9's duplicate-prune can merge
the forced cheapest_viable plan into an identical `one_new_card` plan and lose
the label) and the **best value** (the top `one_new_card` candidate re-scored
under the versioned acquisition-weights profile: low fees → cost, reward
ecosystem → efficiency, transfer-partner quality → risk; ease-to-get out of
scope). Same-acquisition duplicates collapse to one combined-label entry. No
new engine — a selection over already-ranked strategies with a second weights
profile from the same versioned config.

Composite hand-computations use an explicit profile (cost 50 / efficiency 30 /
risk 20, Σ=100):  composite = Σ(weight × sub-score) / Σ weights, 2dp
ROUND_HALF_UP — identical machinery to the Stage-9 composite.
"""

from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.domain import (
    CandidateStrategy,
    RankedStrategy,
    ScoreBreakdown,
    SimulationOutcome,
    SpendCategory,
    StrategyArchetype,
)
from app.knowledge.seed_catalog import seed_id
from app.optimization.ranking import (
    AcquisitionWeights,
    load_ranking_weights,
    select_acquisition_pair,
    select_guided_routes,
)

INFINIA = seed_id("card", "hdfc-infinia")
DCB = seed_id("card", "hdfc-diners-black")
BURGUNDY = seed_id("card", "axis-magnus-burgundy")

# The explicit synthetic profile for hand-computed composites.
ACQ = AcquisitionWeights(
    goal_achievement=Decimal("0"),
    efficiency=Decimal("30"),
    cost=Decimal("50"),
    simplicity=Decimal("0"),
    portfolio_utilization=Decimal("0"),
    risk=Decimal("20"),
)


def _breakdown(*, efficiency: str, cost: str, risk: str) -> ScoreBreakdown:
    return ScoreBreakdown(
        goal_achievement=Decimal("50"),
        efficiency=Decimal(efficiency),
        cost=Decimal(cost),
        simplicity=Decimal("50"),
        portfolio_utilization=Decimal("0"),
        risk=Decimal(risk),
    )


def _ranked(
    strategy_id: str,
    *,
    rank: int,
    archetype: StrategyArchetype,
    acquire: tuple[UUID, ...],
    breakdown: ScoreBreakdown,
    misses: bool = False,
    fees: int = 10_000,
) -> RankedStrategy:
    cards = acquire or (INFINIA,)
    strategy = CandidateStrategy(
        strategy_id=strategy_id,
        archetype=archetype,
        cards_used=cards,
        cards_to_acquire=acquire,
        spend_allocation={SpendCategory.TRAVEL: cards[0]},
        transfer_plan=(),
        claimed_total_miles=50_000,
    )
    outcome = SimulationOutcome(
        strategy_id=strategy_id,
        ledger=(),
        months_to_goal=None if misses else 6,
        miles_at_target_date=50_000,
        total_fees_inr=fees,
        card_fees_inr=fees,
        buffer_achieved=not misses,
        misses_goal=misses,
    )
    return RankedStrategy(
        strategy=strategy,
        simulation=outcome,
        score=Decimal("50"),
        score_breakdown=breakdown,
        rank=rank,
        headline_differentiator="balanced",
    )


# ── select_acquisition_pair ───────────────────────────────────────────────


def test_best_value_is_top_acquisition_composite_not_top_rank() -> None:
    """Two achieving one_new_card routes: A ranks higher overall but B wins
    under the acquisition profile. Hand-computed (profile 30/50/20):
      A: eff 100, cost 0,  risk 80  → (30×100 + 50×0 + 20×80)/100  = 46.00
      B: eff 40,  cost 100, risk 100 → (30×40 + 50×100 + 20×100)/100 = 82.00
    B is best_value despite rank 2; the ₹10,000 route is cheapest by fee."""
    a = _ranked(
        "onc-a", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="0", risk="80"),
        fees=30_000,
    )
    b = _ranked(
        "onc-b", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(INFINIA,), breakdown=_breakdown(efficiency="40", cost="100", risk="100"),
        fees=12_500,
    )
    cheap = _ranked(
        "cv", rank=3, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="20", cost="100", risk="90"),
        fees=10_000,
    )
    pair = select_acquisition_pair((a, b, cheap), ACQ)
    assert [(p.strategy.strategy_id, p.acquisition_role) for p in pair] == [
        ("cv", "cheapest"),
        ("onc-b", "best_value"),
    ]


def test_cheapest_survives_archetype_dedupe_by_fee() -> None:
    """Stage 9's duplicate-prune can merge the forced cheapest_viable plan
    into an identical one_new_card plan (first-in wins) — the label vanishes
    but the fee doesn't. With only one_new_card candidates left, the lowest
    card fee is still offered as cheapest. Hand-computed composites:
      A: eff 100, cost 100, risk 100 → 100.00 (best_value, ₹30,000)
      B: eff 0,   cost 100, risk 50  → 60.00  (cheapest,   ₹10,000)"""
    a = _ranked(
        "onc-a", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="100", risk="100"),
        fees=30_000,
    )
    b = _ranked(
        "onc-b", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(DCB,), breakdown=_breakdown(efficiency="0", cost="100", risk="50"),
        fees=10_000,
    )
    pair = select_acquisition_pair((a, b), ACQ)
    assert [(p.strategy.strategy_id, p.acquisition_role) for p in pair] == [
        ("onc-b", "cheapest"),
        ("onc-a", "best_value"),
    ]


def test_ties_break_by_rank_deterministically() -> None:
    """Equal acquisition composites AND equal fees → the original Stage-9
    rank breaks both ties (first in ranked order wins), collapsing the pair
    onto the single rank-1 route."""
    same = _breakdown(efficiency="50", cost="50", risk="50")
    a = _ranked("onc-a", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
                acquire=(BURGUNDY,), breakdown=same)
    b = _ranked("onc-b", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
                acquire=(INFINIA,), breakdown=same)
    pair = select_acquisition_pair((a, b), ACQ)
    assert [(p.strategy.strategy_id, p.acquisition_role) for p in pair] == [
        ("onc-a", "cheapest_and_best_value"),
    ]


def test_same_acquisition_set_collapses_to_combined_label() -> None:
    """cheapest_viable and the one_new_card winner landing on the SAME card is
    one route to the user — deduped to the higher acquisition-composite plan,
    labeled as both. Hand-computed: cv 60.00 < onc 82.00 → onc's plan kept.
      cv:  eff 0,  cost 100, risk 50  → (0 + 5000 + 1000)/100  = 60.00
      onc: eff 40, cost 100, risk 100 → (1200 + 5000 + 2000)/100 = 82.00"""
    onc = _ranked(
        "onc", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(DCB,), breakdown=_breakdown(efficiency="40", cost="100", risk="100"),
    )
    cv = _ranked(
        "cv", rank=2, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="0", cost="100", risk="50"),
    )
    pair = select_acquisition_pair((onc, cv), ACQ)
    assert len(pair) == 1
    assert pair[0].strategy.strategy_id == "onc"
    assert pair[0].acquisition_role == "cheapest_and_best_value"


def test_same_set_collapse_keeps_higher_composite_of_distinct_plans() -> None:
    """The collapse comparison with genuinely different picks going in:
    cheapest (by fee: ₹9,000 < ₹10,000) is the cv plan, best_value (by
    composite) is the onc plan, both acquiring the SAME card. The kept plan
    must be the higher acquisition-composite one. Hand-computed:
      cv:  eff 0,  cost 100, risk 50  → (0 + 5000 + 1000)/100    = 60.00
      onc: eff 40, cost 100, risk 100 → (1200 + 5000 + 2000)/100 = 82.00
    onc wins despite cv being the cheaper plan — same card, same route to the
    user, and the better plan for it."""
    onc = _ranked(
        "onc", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(DCB,), breakdown=_breakdown(efficiency="40", cost="100", risk="100"),
        fees=10_000,
    )
    cv = _ranked(
        "cv", rank=2, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="0", cost="100", risk="50"),
        fees=9_000,
    )
    pair = select_acquisition_pair((onc, cv), ACQ)
    assert len(pair) == 1
    assert pair[0].strategy.strategy_id == "onc"
    assert pair[0].acquisition_role == "cheapest_and_best_value"


def test_goal_missing_acquisitions_are_never_offered() -> None:
    """The pair is a promise ('these clear your goal') — a goal-missing
    acquisition can't be in it, whatever its scores."""
    missing_cv = _ranked(
        "cv", rank=1, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="100", cost="100", risk="100"),
        misses=True,
    )
    missing_onc = _ranked(
        "onc", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="100", risk="100"),
        misses=True,
    )
    assert select_acquisition_pair((missing_cv, missing_onc), ACQ) == ()


def test_single_sided_pair_when_only_one_archetype_exists() -> None:
    cheap = _ranked(
        "cv", rank=1, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="20", cost="100", risk="90"),
    )
    pair = select_acquisition_pair((cheap,), ACQ)
    assert [(p.strategy.strategy_id, p.acquisition_role) for p in pair] == [
        ("cv", "cheapest"),
    ]


# ── select_guided_routes ──────────────────────────────────────────────────


def _wallet_only(strategy_id: str, *, rank: int, misses: bool) -> RankedStrategy:
    return _ranked(
        strategy_id, rank=rank, archetype=StrategyArchetype.STATUS_QUO_OPTIMIZED,
        acquire=(), breakdown=_breakdown(efficiency="50", cost="100", risk="100"),
        misses=misses, fees=0,
    )


def test_guided_routes_stand_down_when_wallet_clears() -> None:
    """Decision 8's feasible path: current cards clear the goal → standard
    presentation (hero + quiet upgrade tabs), no pair reshaping."""
    wallet_win = _wallet_only("sq", rank=1, misses=False)
    onc = _ranked(
        "onc", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="0", risk="80"),
    )
    assert select_guided_routes((wallet_win, onc), ACQ) is None


def test_guided_routes_pair_plus_wallet_best_effort() -> None:
    """Wallet misses, acquisitions clear → the labeled pair (original rank
    order) plus the wallet best-effort route last, for the verdict hero."""
    onc = _ranked(
        "onc", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="0", risk="80"),
        fees=30_000,
    )
    cv = _ranked(
        "cv", rank=2, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="20", cost="100", risk="90"),
        fees=10_000,
    )
    best_effort = _wallet_only("sq", rank=3, misses=True)
    routes = select_guided_routes((onc, cv, best_effort), ACQ)
    assert routes is not None
    assert [r.strategy.strategy_id for r in routes] == ["onc", "cv", "sq"]
    assert [r.acquisition_role for r in routes] == ["best_value", "cheapest", None]


def test_guided_routes_pair_only_when_no_wallet_route_exists() -> None:
    """Empty wallet: nothing non-acquiring was generable — the pair stands
    alone (education folds into the strategy output, decision 13)."""
    onc = _ranked(
        "onc", rank=1, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="100", cost="0", risk="80"),
        fees=30_000,
    )
    cv = _ranked(
        "cv", rank=2, archetype=StrategyArchetype.CHEAPEST_VIABLE,
        acquire=(DCB,), breakdown=_breakdown(efficiency="20", cost="100", risk="90"),
        fees=10_000,
    )
    routes = select_guided_routes((onc, cv), ACQ)
    assert routes is not None
    assert [r.acquisition_role for r in routes] == ["best_value", "cheapest"]


def test_guided_routes_stand_down_without_an_achieving_acquisition() -> None:
    """Truly infeasible (nothing clears, even acquiring) → None: the existing
    best-effort + adjustment-menu path stays the answer."""
    best_effort = _wallet_only("sq", rank=1, misses=True)
    missing_onc = _ranked(
        "onc", rank=2, archetype=StrategyArchetype.ONE_NEW_CARD,
        acquire=(BURGUNDY,), breakdown=_breakdown(efficiency="50", cost="50", risk="50"),
        misses=True,
    )
    assert select_guided_routes((best_effort, missing_onc), ACQ) is None


# ── Config (v2 adds the acquisition profile; v1 has none) ─────────────────


def test_v2_config_carries_acquisition_profile() -> None:
    weights = load_ranking_weights(Path("config/ranking-weights-v2.yaml"))
    assert weights.version == "2"
    assert weights.acquisition is not None
    # The user's criteria map: low fees → cost, ecosystem → efficiency,
    # transfer-partner quality → risk. All six present, positive total.
    assert weights.acquisition.cost > 0
    assert weights.acquisition.efficiency > 0
    assert weights.acquisition.risk > 0
    assert weights.acquisition.total() > 0
    # Base ranking weights unchanged from v1 (the profile is additive).
    v1 = load_ranking_weights(Path("config/ranking-weights-v1.yaml"))
    for field in (
        "goal_achievement", "efficiency", "cost", "simplicity",
        "portfolio_utilization", "risk", "near_tie_threshold",
    ):
        assert getattr(weights, field) == getattr(v1, field)


def test_v1_config_has_no_acquisition_profile() -> None:
    weights = load_ranking_weights(Path("config/ranking-weights-v1.yaml"))
    assert weights.acquisition is None
