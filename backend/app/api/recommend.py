"""The shared goal→package HTTP path (build-plan §7).

`run_and_respond` is the ONE code path from a `RecommendationRequest` to the
discriminated HTTP response, shared by `/v1/goals/recommendation[/save]` and
the public `/v1/simulations` — the simulator sees the same real engine
numbers a signed-in run would (blueprint Stage 8: "one implementation, three
consumers"). It lives in its own module so neither router imports the other's
internals.

Persistence stays best-effort at the request level (blueprint Stage 11: the
response beats bookkeeping): a failed write is logged and reported honestly
via `persisted=False`, never turned into an error response.
"""

import logging
from uuid import UUID

from app.ai_reasoning.model import ChatModel
from app.api.deps import get_engine
from app.api.schemas import RecommendationRequest, RecommendationResponse
from app.config import Settings
from app.domain import CatalogSnapshot, FinalRecommendation, SpendProfile
from app.optimization.ranking import RankingWeights
from app.pipeline.run import (
    ClarificationNeeded,
    RouteUnsupported,
    ScopeRefused,
    run_goal_pipeline,
)
from app.repositories.results import persist_recommendation

_log = logging.getLogger(__name__)


async def run_and_respond(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot,
    weights: RankingWeights,
    model: ChatModel | None,
    settings: Settings,
    *,
    user_id: UUID,
    persist: bool,
) -> RecommendationResponse:
    """Run the pipeline and map its outcome union to the HTTP response."""
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
        total_spend_inr=request.total_spend_inr,
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
    if not persist:
        return RecommendationResponse(kind="recommendation", recommendation=outcome)
    saved_ids = await _persist(outcome, user_id)
    return RecommendationResponse(
        kind="recommendation",
        recommendation=outcome,
        persisted=saved_ids is not None,
        saved_goal_id=saved_ids["goal_id"] if saved_ids else None,
    )


async def _persist(
    recommendation: FinalRecommendation, user_id: UUID
) -> dict[str, UUID] | None:
    """Best-effort lineage persistence (blueprint Stage 11: the response beats
    bookkeeping). Returns the minted lineage ids iff the write landed, else
    None. A failure is logged and reported (as `persisted=False`) so the UI
    never claims a save that didn't happen — but it never turns the
    recommendation itself into an error."""
    try:
        async with get_engine().begin() as conn:
            return await persist_recommendation(conn, recommendation, user_id=user_id)
    except Exception:  # pragma: no cover - exercised in the DB-integration test
        _log.warning("recommendation persistence failed", exc_info=True)
        return None
