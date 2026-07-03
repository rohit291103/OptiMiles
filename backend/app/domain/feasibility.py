"""Stage 6 outputs: the feasibility gate.

An impossible goal answered with a strategy list is a lie; answered with
"not as stated — but yes with one of these changes" it is the most
trust-building screen in the product.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdjustmentOption(BaseModel):
    """A concrete, computed change that makes an infeasible goal feasible."""

    model_config = ConfigDict(frozen=True)

    kind: str = Field(
        description="'extend_timeline' | 'add_card' | 'raise_spend' | 'downgrade_cabin'"
    )
    description: str
    extend_to_months: int | None = None
    add_card_id: UUID | None = None
    raise_category_slug: str | None = None
    raise_spend_by_inr: int | None = None
    downgrade_cabin_to: str | None = None
    resulting_best_case_miles: int = Field(ge=0)


class PortfolioAssessment(BaseModel):
    """v1.1: 'Current Portfolio Assessment / Reward Gap Analysis' payload sections."""

    model_config = ConfigDict(frozen=True)

    current_capability_miles: int = Field(
        ge=0, description="Best-case miles from the current wallet alone"
    )
    convertible_balances_by_program: dict[str, int] = Field(
        description="Existing balances converted at actual ratios, keyed by program name"
    )
    reward_gap_miles: int = Field(description="miles_required_total − current capability")
    strengths: tuple[str, ...] = ()


class FeasibilityVerdict(BaseModel):
    """Gate decision. Infeasible ⇒ Stages 7–9 skipped; adjustments become the answer."""

    model_config = ConfigDict(frozen=True)

    feasible: bool
    best_case_miles: int = Field(ge=0)
    gap_miles: int = Field(description="miles_required_total − best_case (≤0 when feasible)")
    tight: bool = Field(
        default=False, description="Feasible but gap < buffer — narrate as tight, not certain"
    )
    adjustment_options: tuple[AdjustmentOption, ...] = ()
    portfolio: PortfolioAssessment
