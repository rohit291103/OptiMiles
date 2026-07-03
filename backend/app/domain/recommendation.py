"""Stage 11 output: the Recommendation Package (blueprint v1.1 §2 Stage 11).

Every field maps to a deterministic pipeline artifact; none is LLM-originated.
Reconstructable from persisted lineage (goal → simulation → result →
recommendation, plus catalog_snapshot_version + engine_version).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.feasibility import FeasibilityVerdict
from app.domain.goal import RewardRequirement, TravelGoal
from app.domain.narration import RecommendationNarration
from app.domain.ranking import RankedStrategy


class FinalRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    goal: TravelGoal
    requirement: RewardRequirement
    verdict: FeasibilityVerdict
    recommended: RankedStrategy | None = Field(
        default=None, description="None on the infeasible path — adjustments are the answer"
    )
    alternatives: tuple[RankedStrategy, ...] = ()
    narration: RecommendationNarration | None = Field(
        default=None, description="Second part of the two-part response (D-5); may lag structure"
    )
    risks_and_limitations: tuple[str, ...] = ()
    assumed_flags: tuple[str, ...] = Field(
        default=(), description="UI hints: 'based on default spend profile — edit to refine'"
    )
    catalog_snapshot_version: str
    engine_version: str
