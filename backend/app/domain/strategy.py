"""Stage 7 output: complete, executable candidate strategies.

Generated from bounded archetypes (3–8 candidates), fully deterministic — no
LLM proposes, adjusts, or vetoes strategies. Partial strategies are invalid
outputs; validation failures discard a candidate, never patch it silently.
"""

from decimal import Decimal
from typing import Literal
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
    monthly_miles: int = Field(
        default=0,
        ge=0,
        description="floor(monthly_spend × effective_miles_per_100inr / 100) — the "
        "worked example in target-program miles; display projection, same "
        "not-summable caveat as monthly_points",
    )
    notes: tuple[str, ...] = Field(
        default=(), description="Valuation notes for this path (caps/exclusions)"
    )
    # ── Reward-system story (optional enrichment; None on older artifacts) ──
    currency_name: str | None = Field(
        default=None, description="The points currency this card earns (e.g. 'EDGE Miles')"
    )
    transfer_ratio_from: int | None = Field(
        default=None, description="Currency points consumed per transfer block (Stage-5 path)"
    )
    transfer_ratio_to: int | None = Field(
        default=None, description="Target-program miles credited per transfer block"
    )
    category_label: str | None = Field(
        default=None,
        description="The catalog's label for the accelerated rule that priced this "
        "row (how to actually get the rate, e.g. a portal); None when the "
        "default rate applied",
    )
    runner_up_card_id: UUID | None = Field(
        default=None,
        description="Best OTHER card available in this plan for the category — "
        "the 'why not my other card' comparison; None when there is none",
    )
    runner_up_miles_per_100inr: Decimal | None = Field(
        default=None, description="That runner-up's effective miles per ₹100 (Stage-5 value)"
    )
    runner_up_reason: Literal[
        "transfer_cap", "milestone", "fewer_total", "equal_total", "route_shape"
    ] | None = Field(
        default=None,
        description="Why a HIGHER-rated runner-up still lost this category, verified "
        "by re-estimating the whole plan with the category swapped: 'transfer_cap' "
        "(the runner-up's transfer link cap would strand points), 'milestone' (the "
        "swap forfeits a milestone bonus), 'fewer_total' (the swap verifiably lowers "
        "the plan total), 'equal_total' (no difference), 'route_shape' (the swap "
        "would gain but the route declines it by design — set ONLY for the forced "
        "single-card archetypes; a gaining swap on a hill-climbed route is a "
        "search artifact and ships no cause). None when the chosen card simply "
        "rates higher/equal, no runner-up exists, or no context was available "
        "for the counterfactual.",
    )
    runner_up_plan_delta_miles: int | None = Field(
        default=None,
        description="Engine-verified whole-plan miles LOST by moving this category "
        "to the runner-up (current total − swapped total; negative when the swap "
        "would gain — the 'route_shape' case). Set exactly when runner_up_reason is.",
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
