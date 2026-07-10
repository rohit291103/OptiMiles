"""Goal endpoints (build-plan §7): parse, and the full recommendation run.

`/goals/parse` is Stage 1 alone — free text → intent | clarification, with the
client holding the loop state (blueprint §8.4: server stays stateless). The
recommendation run composes the whole pipeline and persists the lineage chain.

The public simulator (`/simulations`) shares the pipeline via the same
`_run_and_respond` helper, so there is one code path from goal to package.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from app.ai_reasoning.intent import ScopeRefusal, extract_intent
from app.ai_reasoning.model import ChatModel
from app.api.auth import require_user
from app.api.deps import get_config, get_engine, get_model, get_snapshot, get_weights
from app.api.schemas import (
    ParseGoalRequest,
    ParseGoalResponse,
    RecommendationRequest,
    RecommendationResponse,
    SavedGoalsResponse,
    SavedGoalSummary,
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
from app.repositories.saved_goals import list_saved_goals

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
