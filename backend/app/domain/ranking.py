"""Stage 9 output: transparent, explainable ordering.

Weights live in versioned config, not code. Hard rules before weights:
misses_goal candidates rank below all achieving ones. The LLM never reorders,
vetoes, or blesses the ranking.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.simulation import SimulationOutcome
from app.domain.strategy import CandidateStrategy


class ScoreBreakdown(BaseModel):
    """Named sub-scores (0–100 each) behind the composite — never a black box."""

    model_config = ConfigDict(frozen=True)

    goal_achievement: Decimal = Field(ge=0, le=100)
    efficiency: Decimal = Field(ge=0, le=100)
    cost: Decimal = Field(ge=0, le=100)
    simplicity: Decimal = Field(ge=0, le=100)
    portfolio_utilization: Decimal = Field(
        ge=0, le=100, description="Scoring teeth behind 'Maximize Existing Cards First' (v1.1)"
    )
    risk: Decimal = Field(ge=0, le=100)


class RankedStrategy(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: CandidateStrategy
    simulation: SimulationOutcome
    score: Decimal = Field(
        ge=0, le=100, description="Maps to simulation_results.optimization_score"
    )
    score_breakdown: ScoreBreakdown
    rank: int = Field(ge=1)
    headline_differentiator: str = Field(
        description="'fastest' / 'no new cards' / 'lowest fees' — deterministic input for narration"
    )
    co_recommended: bool = Field(
        default=False, description="Near-tie at the top presented honestly as a co-recommendation"
    )
