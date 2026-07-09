"""Stages 5→6→7→8→9 chained on the real seed catalog (no DB, no LLM).

Unit tests verify each engine's arithmetic in isolation; this test verifies
the engines AGREE when chained — specifically the Phase 4 exit criterion
(build-plan §5, tracker): the generator's `claimed_total_miles` must
reconcile with what the Phase 3 projector actually simulates. `allocation.
claimed_estimate` is built to MIRROR the projector (same transfer cutoff,
whole-block flooring, milestone periods); this test proves the mirror holds
on realistic data, so `ranking.reconcile_claim` never has to make a large
correction and the >10% generator-bug warning never fires in practice.

If this test ever shows a widening gap, the two engines have drifted — fix
the generator to match the projector (simulation is the source of truth),
not the other way round.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.feasibility import assess_feasibility
from app.optimization.ranking import load_ranking_weights, rank
from app.optimization.strategies import generate_candidates
from app.simulation.projector import simulate
from app.valuation.opportunities import enumerate_opportunities

TODAY = date(2026, 7, 4)
from pathlib import Path  # noqa: E402

WEIGHTS = load_ranking_weights(Path("config/ranking-weights-v1.yaml"))


def _context(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int],
    wallet: dict[str, int],
    horizon_months: int = 8,
    constraints: ConstraintSet | None = None,
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
            for slug, balance in wallet.items()
        ),
        spend_profile=SpendProfile(
            items=tuple(
                SpendProfileItem(category_slug=cat, monthly_spend_inr=amount)
                for cat, amount in spend.items()
            )
        ),
        horizon_months=horizon_months,
        constraints=constraints or ConstraintSet(),
    )


# Realistic goal/spend/wallet fixtures spanning the archetypes: wallet-only,
# one-new-card, a cap-saturating case, and a milestone-diversion case.
_FIXTURES = [
    ({SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000}, {"hdfc-infinia": 20_000}, None),
    (
        {SpendCategory.TRAVEL: 100_000, SpendCategory.DINING: 30_000},
        {"hdfc-infinia": 20_000, "axis-magnus-burgundy": 0},
        ConstraintSet(no_new_cards=True),
    ),
    (
        {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 140_000},
        {"hdfc-diners-black": 0, "axis-magnus-burgundy": 0},
        ConstraintSet(no_new_cards=True),
    ),
    ({SpendCategory.TRAVEL: 60_000, SpendCategory.DINING: 40_000}, {"hsbc-travelone": 5_000}, None),
]


@pytest.mark.parametrize("spend, wallet, constraints", _FIXTURES)
def test_claim_reconciles_with_simulation(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int],
    wallet: dict[str, int],
    constraints: ConstraintSet | None,
) -> None:
    """The generator's pre-reconciliation claim must land within a tight
    tolerance of the projector's simulated miles for EVERY generated
    candidate — the two engines genuinely agree, not just in the hand-checked
    unit fixtures. Tolerance is 2% or 200 miles, whichever is larger (absorbs
    the documented blended-rate vs cap-split rounding difference on capped
    categories; a real drift would blow past it)."""
    context = _context(snapshot, spend, wallet, constraints=constraints)
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    candidates = generate_candidates(opportunities, verdict, context)
    assert candidates, "expected at least one candidate for a feasible fixture"

    for candidate in candidates:
        outcome = simulate(candidate, context)
        claimed = candidate.claimed_total_miles
        simulated = outcome.miles_at_target_date
        tolerance = max(200, int(Decimal(claimed) * Decimal("0.02")))
        assert abs(claimed - simulated) <= tolerance, (
            f"{candidate.strategy_id}: claim {claimed:,} vs simulation "
            f"{simulated:,} exceeds tolerance {tolerance:,} — generator and "
            f"projector have drifted"
        )


@pytest.mark.parametrize("spend, wallet, constraints", _FIXTURES)
def test_rank_after_simulation_is_well_formed(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int],
    wallet: dict[str, int],
    constraints: ConstraintSet | None,
) -> None:
    """The full chain produces a coherent ranked list: reconciled claims,
    sequential ranks, exactly one #1, and every score in range."""
    context = _context(snapshot, spend, wallet, constraints=constraints)
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    candidates = generate_candidates(opportunities, verdict, context)
    pairs = tuple((candidate, simulate(candidate, context)) for candidate in candidates)

    ranked = rank(pairs, context, WEIGHTS)
    assert ranked
    assert [entry.rank for entry in ranked] == list(range(1, len(ranked) + 1))
    assert ranked[0].rank == 1
    for entry in ranked:
        # reconcile_claim ran: the ranked strategy carries simulated truth.
        assert entry.strategy.claimed_total_miles == entry.simulation.miles_at_target_date
        assert Decimal(0) <= entry.score <= Decimal(100)


def test_full_chain_is_deterministic(snapshot: CatalogSnapshot) -> None:
    """Same goal + context + snapshot ⇒ byte-identical ranked output across
    the whole Stage 5–9 chain (the standing determinism invariant)."""
    spend = {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000}
    wallet = {"hdfc-infinia": 20_000}

    def run() -> tuple:
        context = _context(snapshot, spend, wallet)
        opportunities = enumerate_opportunities(context)
        verdict = assess_feasibility(opportunities, context)
        candidates = generate_candidates(opportunities, verdict, context)
        pairs = tuple((c, simulate(c, context)) for c in candidates)
        return rank(pairs, context, WEIGHTS)

    assert run() == run()


def test_atlas_never_acquired_across_chain(snapshot: CatalogSnapshot) -> None:
    """The Phase 4 requirement holds through the full chain: no ranked
    strategy acquires the discontinued Atlas, even when its 1:2 KrisFlyer
    ratio would tempt the generator."""
    atlas: UUID = seed_id("card", "axis-atlas")
    context = _context(
        snapshot,
        {SpendCategory.TRAVEL: 120_000, SpendCategory.DINING: 20_000},
        {"hdfc-regalia-gold": 0},
    )
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    candidates = generate_candidates(opportunities, verdict, context)
    pairs = tuple((c, simulate(c, context)) for c in candidates)
    for entry in rank(pairs, context, WEIGHTS):
        assert atlas not in entry.strategy.cards_to_acquire
    for option in verdict.adjustment_options:
        assert option.add_card_id != atlas
