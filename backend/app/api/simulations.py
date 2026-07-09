"""POST /simulations — the public landing-page simulator (build-plan §7).

Anonymous, no persistence: it serves the marketing-site Goal Simulator, so it
runs the same pipeline as `/goals/recommendation` but never writes a row. It
reuses the shared `_run_and_respond` helper so there is exactly one goal→package
code path — the simulator sees the same real engine numbers a signed-in run
would (blueprint Stage 8: "one implementation, three consumers").
"""

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.ai_reasoning.model import ChatModel
from app.api.deps import get_config, get_model, get_snapshot, get_weights
from app.api.goals import _run_and_respond
from app.api.schemas import RecommendationRequest, RecommendationResponse
from app.config import Settings
from app.domain import CatalogSnapshot
from app.optimization.ranking import RankingWeights

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=RecommendationResponse)
async def simulate_goal(
    request: RecommendationRequest,
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    weights: RankingWeights = Depends(get_weights),
    model: ChatModel | None = Depends(get_model),
    settings: Settings = Depends(get_config),
) -> RecommendationResponse:
    return await _run_and_respond(
        request, snapshot, weights, model, settings, user_id=uuid4(), persist=False
    )
