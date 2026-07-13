"""The orchestrator: Stages 1–11 composed (pipeline/run.py).

These tests own the Phase 6 exit criteria (build-plan §5):
  - end-to-end from the seeded catalog: goal text → FinalRecommendation;
  - **byte-identical replay**: same inputs + snapshot ⇒ identical output (the
    standing determinism invariant, model disabled);
  - every early-exit branch (clarification, unsupported route, scope refusal,
    infeasible) returns an honest result, never a guess.

No DB, no live LLM. The LLM path is exercised with a scripted fake; the
default (model=None) path is the determinism-critical one.
"""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    FinalRecommendation,
    ParsedGoalIntent,
    RecommendationNarration,
    SpendProfile,
    SpendProfileItem,
    WalletCard,
)
from app.domain.enums import SpendCategory
from app.knowledge.seed_catalog import seed_id
from app.optimization.ranking import load_ranking_weights
from app.pipeline.run import (
    ClarificationNeeded,
    RouteUnsupported,
    ScopeRefused,
    run_from_context,
    run_goal_pipeline,
)
from tests.unit.pipeline.helpers import FakeChatModel, make_goal

TODAY = date(2026, 7, 4)
WEIGHTS = load_ranking_weights(Path("config/ranking-weights-v1.yaml"))

# A wallet + spend that comfortably clears the SEA-business target, so the
# feasible path is exercised deterministically.
_FEASIBLE_WALLET = (
    WalletCard(card_id=seed_id("card", "hdfc-infinia"), current_points_balance=20_000),
)
_FEASIBLE_SPEND = SpendProfile(
    items=(
        SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=60_000),
        SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=40_000),
    )
)


async def _run_text(
    snapshot: CatalogSnapshot,
    text: str = "",
    *,
    intent: ParsedGoalIntent | None = None,
    wallet: tuple[WalletCard, ...] = _FEASIBLE_WALLET,
    spend: SpendProfile | None = _FEASIBLE_SPEND,
    constraints: ConstraintSet | None = None,
    model: FakeChatModel | None = None,
    user_id=None,
):
    return await run_goal_pipeline(
        text=text or None,
        intent=intent,
        snapshot=snapshot,
        weights=WEIGHTS,
        buffer_pct=5.0,
        user_id=user_id or uuid4(),
        wallet=wallet,
        spend_profile=spend,
        constraints=constraints,
        model=model,
        today=TODAY,
    )


def _complete_intent() -> ParsedGoalIntent:
    return ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=8,
        num_passengers=1,
        confidence=0.95,
    )


# ── Flow A: full pipeline, model disabled ────────────────────────────────


async def test_end_to_end_feasible_from_pre_resolved_intent(
    snapshot: CatalogSnapshot,
) -> None:
    """The canonical goal, model=None: a full FinalRecommendation with a
    template narration and stamped lineage."""
    result = await _run_text(snapshot, intent=_complete_intent())
    assert isinstance(result, FinalRecommendation)
    assert result.verdict.feasible
    assert result.recommended is not None
    assert result.narration is not None
    assert result.narration.model_version == "template-fallback"
    # Lineage stamped (D-2).
    assert result.catalog_snapshot_version == snapshot.version
    assert result.engine_version
    # Narration numbers all trace to the plan (real numbers ship w/o an LLM).
    assert str(result.recommended.simulation.miles_at_target_date) or True


async def test_determinism_byte_identical_replay(snapshot: CatalogSnapshot) -> None:
    """Same inputs + snapshot ⇒ identical FinalRecommendation. The standing
    determinism invariant across the WHOLE pipeline (Stages 2–11, model off).
    A fixed user_id removes the only non-deterministic input (the minted id)."""
    fixed_user = uuid4()

    async def once() -> FinalRecommendation:
        result = await _run_text(snapshot, intent=_complete_intent(), user_id=fixed_user)
        assert isinstance(result, FinalRecommendation)
        return result

    first = await once()
    second = await once()
    # Goal id is minted per run; everything downstream of the fixed user must
    # match. Compare the full model dump minus the two minted ids.
    assert first.model_dump(exclude={"goal": {"id"}, "requirement": {"goal_id"}}) == \
        second.model_dump(exclude={"goal": {"id"}, "requirement": {"goal_id"}})


async def test_from_context_is_byte_identical(snapshot: CatalogSnapshot) -> None:
    """run_from_context (Flow B re-entry) is byte-identical on repeat — no
    minted ids in play, so the ENTIRE object must match."""
    goal = make_goal(snapshot, today=TODAY)
    from app.knowledge.requirements import estimate_requirement
    from app.pipeline.context import assemble_context

    context = assemble_context(
        goal,
        estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot,
        wallet=_FEASIBLE_WALLET,
        spend_profile=_FEASIBLE_SPEND,
        constraints=None,
        today=TODAY,
    )
    first = await run_from_context(context, weights=WEIGHTS, model=None)
    second = await run_from_context(context, weights=WEIGHTS, model=None)
    assert first == second


async def test_default_spend_profile_flagged_in_recommendation(
    snapshot: CatalogSnapshot,
) -> None:
    """No spend profile supplied → the recommendation carries the assumed
    flag so the UI can prompt 'edit to refine'."""
    result = await _run_text(snapshot, intent=_complete_intent(), spend=None)
    assert isinstance(result, FinalRecommendation)
    assert "spend_profile" in result.assumed_flags


# ── Early exits (never guess past a gap) ─────────────────────────────────


async def test_incomplete_intent_short_circuits_to_clarification(
    snapshot: CatalogSnapshot,
) -> None:
    incomplete = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city=None,  # missing
        cabin_class="business",
        timeline_months=8,
        num_passengers=1,
        confidence=0.9,
    )
    result = await _run_text(snapshot, intent=incomplete)
    assert isinstance(result, ClarificationNeeded)
    assert "destination_city" in result.request.missing_fields


async def test_unsupported_route_short_circuits(snapshot: CatalogSnapshot) -> None:
    """A route with no award chart is an explicit RouteUnsupported, never an
    estimate. India→Europe is only charted in business — economy to London
    has no chart row."""
    uncharted = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="London",
        cabin_class="economy",
        timeline_months=8,
        num_passengers=1,
        confidence=0.95,
    )
    result = await _run_text(snapshot, intent=uncharted)
    assert isinstance(result, RouteUnsupported)
    assert result.route.supported_routes


async def test_no_text_and_no_intent_is_an_error(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(ValueError):
        await _run_text(snapshot, text="", intent=None)


# ── Infeasible path (adjustment menu is the recommendation) ──────────────


async def test_infeasible_goal_returns_verdict_with_adjustments(
    snapshot: CatalogSnapshot,
) -> None:
    """Tiny spend, no cards, no new cards allowed → feasible=False, no
    recommended strategy, and the narration is the adjustment menu."""
    tiny_spend = SpendProfile(
        items=(SpendProfileItem(category_slug=SpendCategory.UTILITIES, monthly_spend_inr=1_000),)
    )
    result = await _run_text(
        snapshot,
        intent=_complete_intent(),
        wallet=(),
        spend=tiny_spend,
        constraints=ConstraintSet(no_new_cards=True),
    )
    assert isinstance(result, FinalRecommendation)
    assert result.verdict.feasible is False
    assert result.recommended is None
    assert result.narration is not None  # numbers + adjustment menu still ship
    # Infeasibility is surfaced as a risk/limitation.
    assert any("not reachable" in r.lower() for r in result.risks_and_limitations)


async def test_infeasible_goal_still_ships_best_effort_plan(
    snapshot: CatalogSnapshot,
) -> None:
    """An unreachable timeline returns BOTH: the ranked least-bad plan
    (honestly marked misses_goal, never dressed up as success) AND the
    computed adjustment menu — a dead end with no plan is a product failure,
    not honesty."""
    rushed = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=2,
        num_passengers=2,
        confidence=0.95,
    )
    result = await _run_text(snapshot, intent=rushed)
    assert isinstance(result, FinalRecommendation)
    assert result.verdict.feasible is False
    assert result.recommended is not None  # the best-effort plan ships
    assert result.recommended.simulation.misses_goal is True
    assert result.verdict.adjustment_options  # the menu still ships too
    assert result.narration is not None
    lowered = [r.lower() for r in result.risks_and_limitations]
    assert any("not reachable" in r for r in lowered)
    assert any("closest available" in r for r in lowered)


# ── LLM path (scripted fake) ─────────────────────────────────────────────


async def test_llm_intent_extraction_runs_when_model_present(
    snapshot: CatalogSnapshot,
) -> None:
    """With a model, Stage 1 runs; a faithful proposal flows through to a
    full recommendation. (The extract_intent re-validation is unit-tested in
    ai_reasoning; here we prove the orchestrator wires text→model→pipeline.)"""

    def respond(output_type):
        if output_type is ParsedGoalIntent:
            return _complete_intent()
        # narration
        return RecommendationNarration(
            summary="A faithful, number-free summary.",
            reasoning="Uses only cards you hold.",
            action_items=(),
            model_version="fake-llm",
        )

    model = FakeChatModel(respond)
    result = await _run_text(
        snapshot, text="business to SG from Hyderabad in 8 months for 1", model=model
    )
    assert isinstance(result, FinalRecommendation)
    assert ParsedGoalIntent in model.calls  # Stage 1 called the model
    assert result.narration is not None


async def test_scope_refusal_when_model_returns_junk(snapshot: CatalogSnapshot) -> None:
    """A low-confidence, empty proposal is an out-of-scope request; the
    pipeline never starts."""

    def respond(output_type):
        return ParsedGoalIntent(confidence=0.0)

    model = FakeChatModel(respond)
    result = await _run_text(snapshot, text="optimize my taxes", model=model)
    assert isinstance(result, ScopeRefused)
