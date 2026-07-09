"""Stage 5 output: the priced search space.

Each RewardOpportunity answers: "if ₹100 goes to (card, category), how many
target-program miles eventually come out, after ratios, caps, fees, delays?"
Every number in a final recommendation traces back to a named opportunity —
the unit of explainability.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SpendCategory


class CapStructure(BaseModel):
    """Earn caps on an accelerated rate; spend past a cap earns at base rate."""

    model_config = ConfigDict(frozen=True)

    monthly_cap_inr: int | None = None
    quarterly_cap_inr: int | None = None
    annual_cap_inr: int | None = None


class TransferPath(BaseModel):
    """The currency → program leg of an opportunity (direct only in MVP)."""

    model_config = ConfigDict(frozen=True)

    currency_id: UUID
    partner_id: UUID
    ratio_from: int = Field(gt=0)
    ratio_to: int = Field(gt=0)
    min_transfer_points: int = Field(ge=0)
    max_transfer_points: int | None = None
    transfer_fee_inr: int = Field(ge=0)
    processing_days_min: int = Field(ge=0)
    processing_days_max: int = Field(ge=0)


class RewardOpportunity(BaseModel):
    """One individually-sensible earn path: (card, category) → target program."""

    model_config = ConfigDict(frozen=True)

    card_id: UUID
    in_wallet: bool
    category_slug: SpendCategory
    earn_rate: Decimal = Field(ge=0, description="Points per ₹100 before transfer")
    cap_structure: CapStructure = CapStructure()
    transfer_path: TransferPath
    effective_miles_per_100inr: Decimal = Field(
        ge=0, description="Target-program miles per ₹100, after ratio/caps/amortized fees"
    )
    valuation_notes: tuple[str, ...] = Field(
        default=(),
        description="Cap applies / exclusion / ratio worse than headline — for narration",
    )


class CardAggregates(BaseModel):
    """Per-card facts strategies need beyond per-category paths."""

    model_config = ConfigDict(frozen=True)

    card_id: UUID
    in_wallet: bool
    acquirable: bool = Field(
        default=True, description="False = closed to new applicants; never recommend acquiring"
    )
    annual_fee_inr: int = Field(ge=0)
    joining_fee_inr: int = Field(ge=0)
    welcome_bonus_points: int = Field(ge=0, default=0)
    milestone_ids: tuple[UUID, ...] = ()


class OpportunitySet(BaseModel):
    """The full priced search space for one PlanningContext. Ephemeral."""

    model_config = ConfigDict(frozen=True)

    opportunities: tuple[RewardOpportunity, ...]
    card_aggregates: tuple[CardAggregates, ...]
