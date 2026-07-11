"""Stage 7 output: complete, executable candidate strategies.

Generated from bounded archetypes (3–8 candidates), fully deterministic — no
LLM proposes, adjusts, or vetoes strategies. Partial strategies are invalid
outputs; validation failures discard a candidate, never patch it silently.
"""

from decimal import Decimal
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


class StrategyAllocationDetail(BaseModel):
    """One category's earn story: where it routes and why that card wins it.

    A presentation reshape of a strategy's `spend_allocation` joined to the
    Stage-5 `RewardOpportunity` for that (card, category) — every number here
    is a Valuation Engine output, not recomputed reward math. `monthly_points`
    is the one display projection: `floor(monthly_spend × earn_rate / 100)`,
    floored so the UI never overstates the earn rate it shows."""

    model_config = ConfigDict(frozen=True)

    category_slug: SpendCategory
    card_id: UUID
    monthly_spend_inr: int = Field(ge=0)
    earn_rate: Decimal = Field(ge=0, description="Points per ₹100 in this category")
    effective_miles_per_100inr: Decimal = Field(
        ge=0, description="Target-program miles per ₹100 after ratio/caps/fees (Stage 5)"
    )
    monthly_points: int = Field(
        ge=0, description="floor(monthly_spend × earn_rate / 100) — display projection"
    )
    notes: tuple[str, ...] = Field(
        default=(), description="Valuation notes for this path (caps/exclusions)"
    )


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
