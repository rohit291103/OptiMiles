"""Stage 2 result types: either a fully resolved goal draft, or an explicit,
honest rejection. An unsupported route is NEVER estimated (blueprint Stage 2).
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AwardType, CabinClass, GoalType


class GoalResolution(BaseModel):
    """A validated goal draft — every field confirmed against the catalog.

    This is TravelGoal minus persistence identity (id/user_id/status); the
    orchestrator persists it as a user_goals row and gets a TravelGoal back.
    """

    model_config = ConfigDict(frozen=True)

    goal_name: str
    goal_type: GoalType = GoalType.FLIGHT
    partner_id: UUID
    award_chart_id: UUID
    origin_city: str
    destination_city: str
    origin_region: str
    destination_region: str
    cabin_class: CabinClass
    award_type: AwardType = AwardType.SAVER
    num_passengers: int = Field(gt=0)
    target_date: date


class UnsupportedRoute(BaseModel):
    """Explicit rejection with the supported alternatives — never an estimate."""

    model_config = ConfigDict(frozen=True)

    origin_region: str | None
    destination_region: str | None
    cabin_class: CabinClass | None
    reason: str
    supported_routes: tuple[str, ...] = Field(
        description="Human-readable '<origin region> → <destination region> (<cabins>)' entries"
    )
