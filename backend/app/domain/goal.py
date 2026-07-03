"""Stages 2–3 outputs: the validated goal and its numeric target.

Past TravelGoal, every value in the system is user-confirmed or catalog-derived
— the trust boundary is crossed exactly once (blueprint §4 invariant).
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AwardType, CabinClass, GoalStatus, GoalType


class TravelGoal(BaseModel):
    """Validated, persisted goal (user_goals row) with a snapshot-locked award chart."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    goal_name: str
    goal_type: GoalType = GoalType.FLIGHT
    partner_id: UUID
    award_chart_id: UUID = Field(description="Locked at creation — chart updates never move a goal")
    origin_city: str
    destination_city: str
    origin_region: str
    destination_region: str
    cabin_class: CabinClass
    award_type: AwardType = AwardType.SAVER
    num_passengers: int = Field(gt=0, default=1)
    target_date: date
    status: GoalStatus = GoalStatus.ACTIVE


class RewardRequirement(BaseModel):
    """What winning looks like: the fixed numeric target (blueprint Stage 3)."""

    model_config = ConfigDict(frozen=True)

    goal_id: UUID
    target_program_id: UUID
    target_program_name: str
    chart_miles_per_passenger: int = Field(gt=0)
    miles_required_total: int = Field(gt=0, description="chart miles × passengers")
    buffer_miles: int = Field(ge=0, description="Configurable safety buffer, surfaced in narration")
    taxes_fees_inr_estimate: int | None = None
    award_type: AwardType
    one_way: bool = True
    stale_chart: bool = Field(
        default=False,
        description="Chart row deactivated since goal creation; locked row still authoritative",
    )
