"""POST /simulations (+ /probe) — the public goal-entry endpoints (build-plan §7).

Anonymous, no persistence: they serve the marketing-site Goal Simulator and the
guided wizard, running the same pipeline as `/goals/recommendation` but never
writing a row. `/simulations` reuses the shared `recommend.run_and_respond` so
there is exactly one goal→package code path — the simulator sees the same real
engine numbers a signed-in run would (blueprint Stage 8: "one implementation,
three consumers"). `/simulations/probe` is the wizard's silent early
feasibility check (guided-flow decision 5): Stages 1–6 only, sub-second.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.ai_reasoning.model import ChatModel
from app.api.deps import get_config, get_model, get_snapshot, get_weights
from app.api.ratelimit import RateLimiter, limit_dependency
from app.api.recommend import run_and_respond
from app.api.schemas import (
    ProbeResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.config import Settings
from app.domain import CatalogSnapshot, SpendProfile
from app.optimization.ranking import RankingWeights
from app.pipeline.run import (
    ClarificationNeeded,
    RouteUnsupported,
    ScopeRefused,
    run_feasibility_probe,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])

# Anonymous + expensive ⇒ per-IP brakes (fixed window, in-process — build
# rule 7, one sync process). The full run is seconds of CPU + an optional
# LLM call; the probe is a sub-second Stage 1–6 check fired once per wizard
# pass, so it gets a looser budget.
simulate_limiter = RateLimiter(max_requests=10, window_seconds=60)
probe_limiter = RateLimiter(max_requests=30, window_seconds=60)
simulate_limit = limit_dependency(simulate_limiter)
probe_limit = limit_dependency(probe_limiter)


@router.post("", response_model=RecommendationResponse)
async def simulate_goal(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    weights: RankingWeights = Depends(get_weights),
    model: ChatModel | None = Depends(get_model),
    settings: Settings = Depends(get_config),
    _: None = Depends(simulate_limit),
) -> RecommendationResponse:
    return await run_and_respond(
        request, snapshot, weights, model, settings, user_id=uuid4(), persist=False
    )


@router.post("/probe", response_model=ProbeResponse)
async def probe_feasibility(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    model: ChatModel | None = Depends(get_model),
    settings: Settings = Depends(get_config),
    _: None = Depends(probe_limit),
) -> ProbeResponse:
    """The wizard's silent early feasibility check — Stages 1–6 only.

    Same request shape as `/simulations` (intent + wallet + total or split),
    but no candidates, simulation, or narration: just the Stage-6 bound-check
    verdict with its adjustment menu, fast enough to run invisibly right after
    the total-spend step."""
    spend = (
        SpendProfile(items=request.spend_items()) if request.spend_profile else None
    )
    outcome = await run_feasibility_probe(
        text=request.text,
        intent=request.intent,
        snapshot=snapshot,
        buffer_pct=settings.requirement_buffer_pct,
        user_id=uuid4(),
        wallet=request.wallet_cards(),
        spend_profile=spend,
        total_spend_inr=request.total_spend_inr,
        constraints=request.constraints,
        profile_city=request.profile_city,
        model=model,
    )
    if isinstance(outcome, ClarificationNeeded):
        return ProbeResponse(kind="clarification", clarification=outcome.request)
    if isinstance(outcome, RouteUnsupported):
        return ProbeResponse(kind="unsupported_route", unsupported_route=outcome.route)
    if isinstance(outcome, ScopeRefused):
        return ProbeResponse(kind="scope_refusal", message=outcome.refusal.message)
    return ProbeResponse(
        kind="feasibility",
        verdict=outcome.verdict,
        miles_required_total=outcome.miles_required_total,
        horizon_months=outcome.horizon_months,
        catalog_snapshot_version=outcome.catalog_snapshot_version,
    )
