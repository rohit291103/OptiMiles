"""Stage 7 output: complete, executable candidate strategies.

Generated from bounded archetypes (3–8 candidates), fully deterministic — no
LLM proposes, adjusts, or vetoes strategies. Partial strategies are invalid
outputs; validation failures discard a candidate, never patch it silently.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SpendCategory, StrategyArchetype


class TransferPlanItem(BaseModel):
    """One scheduled transfer, batched over min_transfer and timed for delays."""

    model_config = ConfigDict(frozen=True)

    from_card_id: UUID
    to_partner_id: UUID
    points: int = Field(gt=0)
    planned_month: int = Field(ge=0, description="Months from plan start (0 = this month)")


class ExpectedMilestone(BaseModel):
    model_config = ConfigDict(frozen=True)

    milestone_id: UUID
    card_id: UUID
    expected_month: int = Field(ge=0)
    bonus_points: int = Field(ge=0)


class CandidateStrategy(BaseModel):
    """A plan the user can act on: which cards, which spend where, when to transfer."""

    model_config = ConfigDict(frozen=True)

    strategy_id: str = Field(description="Deterministic id, e.g. 'status_quo_optimized-1'")
    archetype: StrategyArchetype
    cards_used: tuple[UUID, ...] = Field(min_length=1)
    cards_to_acquire: tuple[UUID, ...] = ()
    spend_allocation: dict[SpendCategory, UUID] = Field(
        description="category slug → card id routing"
    )
    transfer_plan: tuple[TransferPlanItem, ...]
    expected_milestones: tuple[ExpectedMilestone, ...] = ()
    claimed_total_miles: int = Field(
        ge=0, description="Generator estimate; simulation wins on disagreement"
    )
    assumptions: tuple[str, ...] = Field(
        default=(), description="Raw material for the explanation stage"
    )
