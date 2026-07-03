"""Stage 4 output: PlanningContext — everything the deterministic core may know.

Frozen by construction. Flow B (simulation replay) never mutates a context; it
builds a new one. Same goal + same context + same snapshot version ⇒
byte-identical results (the standing determinism test).
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog import CatalogSnapshot
from app.domain.enums import SpendCategory
from app.domain.goal import RewardRequirement, TravelGoal


class WalletCard(BaseModel):
    """A card the user holds, with starting balance (user_cards row)."""

    model_config = ConfigDict(frozen=True)

    card_id: UUID
    current_points_balance: int = Field(ge=0)
    monthly_spend_limit_inr: int | None = None
    is_primary: bool = False


class SpendProfileItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    category_slug: SpendCategory
    monthly_spend_inr: int = Field(gt=0)
    pinned_card_id: UUID | None = Field(
        default=None, description="User pin from simulation_line_items.assigned_card_id"
    )


class SpendProfile(BaseModel):
    """Monthly spend by category — user-declared, or a default template."""

    model_config = ConfigDict(frozen=True)

    items: tuple[SpendProfileItem, ...]
    assumed: bool = Field(
        default=False,
        description="True when a default template was applied — narration must say so",
    )


class ConstraintSet(BaseModel):
    """Hard user constraints. Filter before scoring; preferences only tilt weights."""

    model_config = ConfigDict(frozen=True)

    no_new_cards: bool = False
    max_annual_fees_inr: int | None = None


class PlanningContext(BaseModel):
    """Immutable input to Stages 5–9. The only user-data read in the core (Stage 4)."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    goal: TravelGoal
    requirement: RewardRequirement
    snapshot: CatalogSnapshot
    wallet: tuple[WalletCard, ...]
    spend_profile: SpendProfile
    horizon_months: int = Field(gt=0, description="Months until goal.target_date")
    constraints: ConstraintSet = ConstraintSet()
