"""Goal endpoints (build-plan §7): parse, and the full recommendation run.

`/goals/parse` is Stage 1 alone — free text → intent | clarification, with the
client holding the loop state (blueprint §8.4: server stays stateless). The
recommendation run composes the whole pipeline and persists the lineage chain.

The public simulator (`/simulations`) shares the pipeline via the same
`_run_and_respond` helper, so there is one code path from goal to package.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai_reasoning.intent import ScopeRefusal, extract_intent
from app.ai_reasoning.model import ChatModel
from app.api.auth import require_user
from app.api.deps import get_config, get_engine, get_model, get_snapshot, get_weights
from app.api.schemas import (
    ParseGoalRequest,
    ParseGoalResponse,
    RecommendationRequest,
    RecommendationResponse,
    SavedActionItem,
    SavedGoalDetail,
    SavedGoalsResponse,
    SavedGoalSummary,
    SavedLedgerEntry,
    SavedMilestone,
    SavedStrategy,
    SavedTransferPlanItem,
)
from app.config import Settings
from app.domain import (
    CatalogSnapshot,
    ClarificationRequest,
    FinalRecommendation,
    SpendProfile,
)
from app.optimization.ranking import RankingWeights
from app.pipeline.run import (
    ClarificationNeeded,
    RouteUnsupported,
    ScopeRefused,
    run_goal_pipeline,
)
from app.repositories.results import persist_recommendation
from app.repositories.saved_goals import (
    SavedGoalDetailRow,
    get_saved_goal,
    list_saved_goals,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=SavedGoalsResponse)
async def my_goals(user_id: UUID = Depends(require_user)) -> SavedGoalsResponse:
    """The signed-in user's saved goals, newest first — the "My Goals" view.

    Read-only, scoped to the verified `auth.users` id from the access token
    (the query never spans users; RLS is the second line of defence, D-4). Each
    goal carries its latest recommendation summary and the snapshot version it
    was computed against, straight from persisted rows — no recomputation, so
    the list matches exactly what was saved."""
    async with get_engine().connect() as conn:
        rows = await list_saved_goals(conn, user_id=user_id)
    return SavedGoalsResponse(
        goals=tuple(
            SavedGoalSummary(
                goal_id=row.goal_id,
                goal_name=row.goal_name,
                goal_type=row.goal_type,
                destination_city=row.destination_city,
                cabin_class=row.cabin_class,
                target_miles=row.target_miles,
                target_date=row.target_date,
                status=row.status,
                saved_at=row.created_at,
                summary=row.summary,
                confidence_score=row.confidence_score,
                catalog_snapshot_version=row.catalog_snapshot_version,
            )
            for row in rows
        )
    )


@router.get("/{goal_id}", response_model=SavedGoalDetail)
async def goal_detail(
    goal_id: UUID,
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> SavedGoalDetail:
    """One saved goal's full stored recommendation — the dashboard detail view.

    Reconstructed from the persisted lineage chain (D-2), never recomputed: the
    numbers shown are exactly what the engine produced at save time, against the
    snapshot version named in the response. Only the id → display-name maps use
    the current snapshot (labels, not values). Scoped to the verified caller; an
    unknown id and someone else's goal are the same 404 on purpose."""
    async with get_engine().connect() as conn:
        row = await get_saved_goal(conn, user_id=user_id, goal_id=goal_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Goal not found")
    detail = detail_from_row(row)
    if detail.strategy is not None:
        card_names, partner_names = display_names(detail.strategy, snapshot)
        detail = detail.model_copy(
            update={"card_names": card_names, "partner_names": partner_names}
        )
    return detail


def display_names(
    strategy: SavedStrategy, snapshot: CatalogSnapshot
) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve the card/partner ids a saved strategy references to display
    names from the current snapshot. Purely cosmetic — retired ids are omitted
    (the client falls back to a generic label), never guessed."""
    card_ids = {
        *strategy.cards_used,
        *strategy.cards_to_acquire,
        *strategy.spend_allocation.values(),
        *(str(m.card_id) for m in strategy.milestones),
        *(str(t.from_card_id) for t in strategy.transfer_plan),
    }
    partner_ids = {str(t.to_partner_id) for t in strategy.transfer_plan}
    card_names = {
        str(card.id): card.card_name
        for card in snapshot.cards
        if str(card.id) in card_ids
    }
    partner_names = {
        str(partner.id): partner.program_name
        for partner in snapshot.partners
        if str(partner.id) in partner_ids
    }
    return card_names, partner_names


def detail_from_row(row: SavedGoalDetailRow) -> SavedGoalDetail:
    """Persisted lineage row → response. Pure reshaping of stored JSONB into
    typed fields (plus a priority sort for action items); no engine calls."""
    strategy: SavedStrategy | None = None
    if row.card_allocations is not None:
        allocations = row.card_allocations
        strategy = SavedStrategy(
            spend_allocation=allocations.get("spend_allocation", {}),
            cards_used=tuple(allocations.get("cards_used", [])),
            cards_to_acquire=tuple(allocations.get("cards_to_acquire", [])),
            ledger=tuple(
                SavedLedgerEntry(
                    month=entry["month"],
                    points_earned_this_month=entry.get("points_earned_this_month", 0),
                    cumulative_target_miles=entry.get("cumulative_target_miles", 0),
                )
                for entry in allocations.get("ledger", [])
            ),
            months_to_goal=row.months_to_goal,
            optimization_score=row.optimization_score,
            milestones=tuple(
                SavedMilestone(**m) for m in (row.milestone_projections or [])
            ),
            transfer_plan=tuple(
                SavedTransferPlanItem(**t) for t in (row.transfer_recommendation or [])
            ),
        )

    action_items = tuple(
        sorted(
            (SavedActionItem(**item) for item in (row.action_items or [])),
            key=lambda item: item.priority,
        )
    )

    return SavedGoalDetail(
        goal_id=row.goal_id,
        goal_name=row.goal_name,
        goal_type=row.goal_type,
        origin_city=row.origin_city,
        destination_city=row.destination_city,
        cabin_class=row.cabin_class,
        num_passengers=row.num_passengers,
        target_miles=row.target_miles,
        target_date=row.target_date,
        status=row.status,
        saved_at=row.created_at,
        recommendation_type=row.recommendation_type,
        summary=row.summary,
        reasoning=row.reasoning,
        action_items=action_items,
        confidence_score=row.confidence_score,
        catalog_snapshot_version=row.catalog_snapshot_version,
        engine_version=row.engine_version,
        strategy=strategy,
    )


@router.post("/parse", response_model=ParseGoalResponse)
async def parse_goal(
    request: ParseGoalRequest,
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    model: ChatModel | None = Depends(get_model),
) -> ParseGoalResponse:
    proposal = await extract_intent(
        request.text, snapshot, model=model, profile_city=request.profile_city
    )
    if isinstance(proposal, ClarificationRequest):
        return ParseGoalResponse(kind="clarification", clarification=proposal)
    if isinstance(proposal, ScopeRefusal):
        return ParseGoalResponse(kind="scope_refusal", message=proposal.message)
    return ParseGoalResponse(kind="intent", intent=proposal)


@router.post("/recommendation", response_model=RecommendationResponse)
async def recommend(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    weights: RankingWeights = Depends(get_weights),
    model: ChatModel | None = Depends(get_model),
    settings: Settings = Depends(get_config),
) -> RecommendationResponse:
    """Full run → structured Recommendation Package (Stages 1–11), anonymous.

    Not persisted: with no authenticated user there is no real `auth.users` id
    to attribute the write to (inventing one would violate the `user_goals`
    FK). Signed-in callers use `POST /goals/recommendation/save`, which persists
    the lineage chain under their verified id.
    """
    return await _run_and_respond(
        request, snapshot, weights, model, settings, user_id=uuid4(), persist=False
    )


@router.post("/recommendation/save", response_model=RecommendationResponse)
async def recommend_and_save(
    request: RecommendationRequest,
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    weights: RankingWeights = Depends(get_weights),
    model: ChatModel | None = Depends(get_model),
    settings: Settings = Depends(get_config),
) -> RecommendationResponse:
    """Authenticated full run that persists the lineage chain under the caller's
    real `auth.users` id (verified from the Supabase access token).

    Same pipeline and response as the anonymous endpoint; the only difference is
    a real `user_id` and `persist=True`, which satisfies the
    `persist_recommendation` precondition (a `users → auth.users`-backed id).
    """
    return await _run_and_respond(
        request, snapshot, weights, model, settings, user_id=user_id, persist=True
    )


async def _run_and_respond(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot,
    weights: RankingWeights,
    model: ChatModel | None,
    settings: Settings,
    *,
    user_id: UUID,
    persist: bool,
) -> RecommendationResponse:
    """Run the pipeline and map its outcome union to the HTTP response. Shared
    by the recommendation and simulation endpoints."""
    spend = (
        SpendProfile(items=request.spend_items()) if request.spend_profile else None
    )
    outcome = await run_goal_pipeline(
        text=request.text,
        intent=request.intent,
        snapshot=snapshot,
        weights=weights,
        buffer_pct=settings.requirement_buffer_pct,
        user_id=user_id,
        wallet=request.wallet_cards(),
        spend_profile=spend,
        constraints=request.constraints,
        profile_city=request.profile_city,
        model=model,
    )

    if isinstance(outcome, ClarificationNeeded):
        return RecommendationResponse(kind="clarification", clarification=outcome.request)
    if isinstance(outcome, RouteUnsupported):
        return RecommendationResponse(kind="unsupported_route", unsupported_route=outcome.route)
    if isinstance(outcome, ScopeRefused):
        return RecommendationResponse(kind="scope_refusal", message=outcome.refusal.message)

    # A full recommendation (feasible or infeasible-with-adjustments).
    persisted = await _persist(outcome, user_id) if persist else None
    return RecommendationResponse(
        kind="recommendation", recommendation=outcome, persisted=persisted
    )


async def _persist(recommendation: FinalRecommendation, user_id: UUID) -> bool:
    """Best-effort lineage persistence (blueprint Stage 11: the response beats
    bookkeeping). Returns True iff the write landed. A failure is logged and
    reported (as `persisted=False`) so the UI never claims a save that didn't
    happen — but it never turns the recommendation itself into an error."""
    import logging

    try:
        async with get_engine().begin() as conn:
            await persist_recommendation(conn, recommendation, user_id=user_id)
        return True
    except Exception:  # pragma: no cover - exercised in the DB-integration test
        logging.getLogger(__name__).warning("recommendation persistence failed", exc_info=True)
        return False
