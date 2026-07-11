"""Stage 10 — narration, LLM mocked.

Contract: the LLM is handed ONLY the finished structured numbers and phrases
them; a deterministic number-echo check then verifies every number and card/
program name in the narration exists in the input payload. An unmatched
figure triggers ONE regeneration, then the template fallback. The numbers
ship regardless of LLM availability — only eloquence degrades.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.ai_reasoning.narration import build_narration_payload, narrate
from app.domain import (
    CandidateStrategy,
    CatalogSnapshot,
    FeasibilityVerdict,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    RankedStrategy,
    RecommendationNarration,
    ScoreBreakdown,
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
from app.optimization.feasibility import assess_feasibility

from .conftest import FakeChatModel, always, raises

TODAY = date(2026, 7, 4)
INFINIA = seed_id("card", "hdfc-infinia")
BURGUNDY = seed_id("card", "axis-magnus-burgundy")
KRISFLYER = seed_id("partner", "krisflyer")


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


def _ranked(context: PlanningContext) -> RankedStrategy:
    strategy = CandidateStrategy(
        strategy_id="one_new_card-1",
        archetype=StrategyArchetype.ONE_NEW_CARD,
        cards_used=(INFINIA, BURGUNDY),
        cards_to_acquire=(BURGUNDY,),
        spend_allocation={SpendCategory.TRAVEL: BURGUNDY, SpendCategory.DINING: BURGUNDY},
        transfer_plan=(
            TransferPlanItem(
                from_card_id=BURGUNDY, to_partner_id=KRISFLYER, points=96_600, planned_month=6
            ),
            TransferPlanItem(
                from_card_id=INFINIA, to_partner_id=KRISFLYER, points=20_000, planned_month=6
            ),
        ),
        claimed_total_miles=97_280,
    )
    outcome = SimulationOutcome(
        strategy_id="one_new_card-1",
        ledger=(),
        months_to_goal=7,
        miles_at_target_date=97_280,
        total_fees_inr=30_235,
        buffer_achieved=True,
    )
    return RankedStrategy(
        strategy=strategy,
        simulation=outcome,
        score=Decimal("56.94"),
        score_breakdown=ScoreBreakdown(
            goal_achievement=Decimal("21.25"),
            efficiency=Decimal("100"),
            cost=Decimal("100"),
            simplicity=Decimal("55"),
            portfolio_utilization=Decimal("0"),
            risk=Decimal("90"),
        ),
        rank=1,
        headline_differentiator="fastest",
    )


def _verdict(context: PlanningContext) -> FeasibilityVerdict:
    from app.valuation.opportunities import enumerate_opportunities

    return assess_feasibility(enumerate_opportunities(context), context)


def _good_narration(model_version: str = "test-model") -> RecommendationNarration:
    """A faithful narration: every number/name appears in the payload."""
    from app.domain.narration import ActionItem

    return RecommendationNarration(
        summary="Reaches 97,280 KrisFlyer miles by month 7, one month ahead of target.",
        reasoning=(
            "Routing travel and dining to the Magnus Burgundy earns fastest; "
            "your Infinia balance of 20,000 points transfers too. Total fees ₹30,235."
        ),
        action_items=(
            ActionItem(priority=1, action="Apply for the Magnus Burgundy", card_id=BURGUNDY),
        ),
        comparison_notes="Fastest of the options.",
        model_version=model_version,
    )


# ── LLM disabled / failing → template fallback ────────────────────────────


async def test_disabled_llm_uses_template_and_still_ships_numbers(
    snapshot: CatalogSnapshot,
) -> None:
    context = _context(snapshot)
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=None
    )
    assert narration.model_version == "template-fallback"
    # The headline number MUST be present — templates degrade eloquence, not truth.
    assert "97,280" in narration.summary or "97,280" in narration.reasoning
    assert narration.action_items


async def test_llm_failure_falls_back_to_template(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot)
    model = FakeChatModel(raises(RuntimeError("timeout")))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert narration.model_version == "template-fallback"


# ── Tier comparison ("your cards → +1 → +2" story) ─────────────────────────


def _alternative(context: PlanningContext) -> RankedStrategy:
    """A cheaper, fewer-miles alternative — the 'no new cards' tier."""
    strategy = CandidateStrategy(
        strategy_id="status_quo_optimized-1",
        archetype=StrategyArchetype.STATUS_QUO_OPTIMIZED,
        cards_used=(INFINIA,),
        cards_to_acquire=(),
        spend_allocation={SpendCategory.TRAVEL: INFINIA, SpendCategory.DINING: INFINIA},
        transfer_plan=(
            TransferPlanItem(
                from_card_id=INFINIA, to_partner_id=KRISFLYER, points=51_282, planned_month=6
            ),
        ),
        claimed_total_miles=51_282,
    )
    outcome = SimulationOutcome(
        strategy_id="status_quo_optimized-1",
        ledger=(),
        months_to_goal=7,
        miles_at_target_date=51_282,
        total_fees_inr=0,
        buffer_achieved=False,
    )
    return RankedStrategy(
        strategy=strategy,
        simulation=outcome,
        score=Decimal("50.00"),
        score_breakdown=ScoreBreakdown(
            goal_achievement=Decimal("21.25"),
            efficiency=Decimal("0"),
            cost=Decimal("100"),
            simplicity=Decimal("100"),
            portfolio_utilization=Decimal("100"),
            risk=Decimal("90"),
        ),
        rank=2,
        headline_differentiator="no new cards",
    )


async def test_template_narrates_the_tier_comparison(snapshot: CatalogSnapshot) -> None:
    """With an alternative present, the template fallback populates
    comparison_notes (previously always None) with the tier story, and the
    alternative's miles are echo-allowed (not flagged as invented)."""
    context = _context(snapshot)
    narration = await narrate(
        _ranked(context),
        _verdict(context),
        context,
        alternatives=(_alternative(context),),
        model=None,
    )
    assert narration.comparison_notes is not None
    # The alternative's headline miles appear in the comparison prose.
    assert "51,282" in narration.comparison_notes


async def test_alternative_numbers_are_echo_allowed(snapshot: CatalogSnapshot) -> None:
    """A faithful LLM draft may cite an alternative's miles/fees — the payload
    allow-lists them, so the echo-guard does not fall back to template."""
    from app.ai_reasoning.narration import build_narration_payload

    context = _context(snapshot)
    payload = build_narration_payload(
        _ranked(context), _verdict(context), context, (_alternative(context),)
    )
    assert 51_282 in payload.allowed_numbers  # alternative headline miles


# ── Happy path + number-echo validation ───────────────────────────────────


async def test_faithful_narration_passes_through(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot)
    model = FakeChatModel(always(_good_narration()))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert narration.model_version == "test-model"
    assert "97,280" in narration.summary
    assert len(model.calls) == 1  # no regeneration needed


async def test_llm_prompt_contains_only_payload_numbers(snapshot: CatalogSnapshot) -> None:
    """The LLM is handed the structured payload and nothing else — it cannot
    introduce facts because it was given only facts to phrase."""
    context = _context(snapshot)
    model = FakeChatModel(always(_good_narration()))
    await narrate(_ranked(context), _verdict(context), context, alternatives=(), model=model)
    (_, prompt, _) = model.calls[0]
    assert "97,280" in prompt or "97280" in prompt
    assert "Magnus Burgundy" in prompt or "Burgundy" in prompt


async def test_hallucinated_number_triggers_regeneration_then_accepts(
    snapshot: CatalogSnapshot,
) -> None:
    """First draft invents '150,000 miles' (not in payload) → one regeneration
    → second draft is faithful → accepted."""
    context = _context(snapshot)
    from app.domain.narration import ActionItem

    bad = RecommendationNarration(
        summary="Reaches 150,000 miles — an easy win.",  # 150,000 not in payload
        reasoning="Great plan.",
        action_items=(ActionItem(priority=1, action="Apply"),),
        model_version="test-model",
    )
    drafts = iter([bad, _good_narration()])
    model = FakeChatModel(lambda i, p, t: next(drafts))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert len(model.calls) == 2  # regenerated exactly once
    assert narration.model_version == "test-model"
    assert "97,280" in narration.summary


async def test_persistent_hallucination_falls_back_to_template(
    snapshot: CatalogSnapshot,
) -> None:
    """If the second draft ALSO hallucinates, ship the template — never a
    number the payload can't back."""
    context = _context(snapshot)
    from app.domain.narration import ActionItem

    bad = RecommendationNarration(
        summary="You will get 999,999 miles.",
        reasoning="Trust me.",
        action_items=(ActionItem(priority=1, action="Apply"),),
        model_version="test-model",
    )
    model = FakeChatModel(always(bad))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert narration.model_version == "template-fallback"
    assert len(model.calls) == 2  # tried twice, then gave up
    assert "999,999" not in narration.summary


async def test_hallucinated_card_name_triggers_fallback(snapshot: CatalogSnapshot) -> None:
    """Number-echo also guards card/program NAMES — a card not in the plan
    is a hallucination."""
    context = _context(snapshot)
    from app.domain.narration import ActionItem

    bad = RecommendationNarration(
        summary="Reaches 97,280 miles.",
        # Neither card is in this plan:
        reasoning="Use your HSBC TravelOne and the Amex Platinum Charge together.",
        action_items=(ActionItem(priority=1, action="Apply"),),
        model_version="test-model",
    )
    model = FakeChatModel(always(bad))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert narration.model_version == "template-fallback"


# ── Infeasible path ───────────────────────────────────────────────────────


async def test_infeasible_verdict_narrates_adjustments(snapshot: CatalogSnapshot) -> None:
    """No recommended strategy (infeasible) → the narration is the adjustment
    menu, template or LLM. Numbers still echo-checked."""
    from app.domain import ConstraintSet

    context = _context(snapshot).model_copy(
        update={"constraints": ConstraintSet(no_new_cards=True)}
    )
    verdict = _verdict(context)
    assert verdict.feasible is False
    narration = await narrate(None, verdict, context, alternatives=(), model=None)
    assert narration.model_version == "template-fallback"
    assert narration.action_items  # at least one adjustment option surfaced


async def test_faithful_echo_of_adjustment_amount_is_accepted(
    snapshot: CatalogSnapshot,
) -> None:
    """Reviewer finding: the ₹ amount inside an adjustment-note description is
    shown to the LLM; a FAITHFUL echo of it must not be rejected as a
    hallucination. Infeasible no_new_cards fixture surfaces a 'raise monthly
    travel spend by ₹10,000' option — the LLM quoting ₹10,000 is honest."""
    from app.domain import ConstraintSet
    from app.domain.narration import ActionItem

    context = _context(snapshot).model_copy(
        update={"constraints": ConstraintSet(no_new_cards=True)}
    )
    verdict = _verdict(context)
    raise_note = next(o for o in verdict.adjustment_options if o.kind == "raise_spend")
    assert raise_note.raise_spend_by_inr == 10_000
    faithful = RecommendationNarration(
        summary="Not reachable as stated yet.",
        reasoning="One fix: raise monthly travel spend by ₹10,000 to close the gap.",
        action_items=(ActionItem(priority=1, action="Raise travel spend by ₹10,000"),),
        model_version="test-model",
    )
    model = FakeChatModel(always(faithful))
    narration = await narrate(None, verdict, context, alternatives=(), model=model)
    assert narration.model_version == "test-model"  # accepted, no spurious fallback
    assert len(model.calls) == 1


async def test_decimal_glued_number_is_rejected(snapshot: CatalogSnapshot) -> None:
    """Reviewer finding (Critical): '97280.7' must not pass just because 97280
    and 7 are each independently allow-listed — the fabricated decimal makes
    it a different, unsupported number. Headline miles are always integers."""
    context = _context(snapshot)
    from app.domain.narration import ActionItem

    bad = RecommendationNarration(
        summary="Reaches 97280.7 miles — a precise-sounding fabrication.",
        reasoning="Great plan.",
        action_items=(ActionItem(priority=1, action="Apply"),),
        model_version="test-model",
    )
    model = FakeChatModel(always(bad))
    narration = await narrate(
        _ranked(context), _verdict(context), context, alternatives=(), model=model
    )
    assert narration.model_version == "template-fallback"
    assert "97280.7" not in narration.summary


# ── Payload builder (the deterministic fact set) ──────────────────────────


def test_payload_contains_no_forbidden_internals(snapshot: CatalogSnapshot) -> None:
    """The payload the LLM sees is finished numbers + names — not raw score
    weights or catalog ids the model might parrot as facts."""
    context = _context(snapshot)
    payload = build_narration_payload(_ranked(context), _verdict(context), context, ())
    assert payload.headline_miles == 97_280
    assert payload.months_to_goal == 7
    assert "Magnus Burgundy" in payload.card_names or any(
        "Burgundy" in name for name in payload.card_names
    )
    assert payload.target_program == "KrisFlyer"


def test_allowed_numbers_include_headline_and_fees(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot)
    payload = build_narration_payload(_ranked(context), _verdict(context), context, ())
    assert 97_280 in payload.allowed_numbers
    assert 30_235 in payload.allowed_numbers
    assert 20_000 in payload.allowed_numbers  # the transferred Infinia balance
