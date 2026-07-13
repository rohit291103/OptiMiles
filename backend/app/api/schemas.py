"""API v1 request/response bodies (build-plan §7).

Thin wrappers over the pipeline's typed inputs and outputs. Requests carry the
user-supplied wallet / spend profile / constraints; responses are the domain
`FinalRecommendation` or an honest early-exit discriminated union. The pipeline
owns all the reward logic — these types only shape the HTTP edge.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain import (
    ClarificationRequest,
    ConstraintSet,
    FinalRecommendation,
    ParsedGoalIntent,
    SpendCategory,
    SpendProfileItem,
    UnsupportedRoute,
    WalletCard,
)


class WalletCardInput(BaseModel):
    card_id: UUID
    current_points_balance: int = Field(ge=0, default=0)


class SpendItemInput(BaseModel):
    category_slug: str
    monthly_spend_inr: int = Field(gt=0)
    pinned_card_id: UUID | None = None


class ParseGoalRequest(BaseModel):
    """POST /goals/parse — free text → intent | clarification (client holds loop)."""

    text: str = Field(min_length=1)
    profile_city: str | None = None


class ParseGoalResponse(BaseModel):
    """Discriminated on `kind`: a resolved intent, or the clarification menu."""

    kind: Literal["intent", "clarification", "scope_refusal"]
    intent: ParsedGoalIntent | None = None
    clarification: ClarificationRequest | None = None
    message: str | None = None


class RecommendationRequest(BaseModel):
    """POST /goals/{...}/recommendation and /simulations shared input.

    Either `text` (run Stage 1) or `intent` (client-held loop, skip Stage 1).
    Wallet/spend/constraints are optional — omitted spend applies the flagged
    default template, an empty wallet is a valid (likely-infeasible) context.
    """

    text: str | None = None
    intent: ParsedGoalIntent | None = None
    profile_city: str | None = None
    wallet: tuple[WalletCardInput, ...] = ()
    spend_profile: tuple[SpendItemInput, ...] = ()
    constraints: ConstraintSet | None = None

    def wallet_cards(self) -> tuple[WalletCard, ...]:
        return tuple(
            WalletCard(card_id=c.card_id, current_points_balance=c.current_points_balance)
            for c in self.wallet
        )

    def spend_items(self) -> tuple[SpendProfileItem, ...]:
        return tuple(
            SpendProfileItem(
                category_slug=SpendCategory(item.category_slug),
                monthly_spend_inr=item.monthly_spend_inr,
                pinned_card_id=item.pinned_card_id,
            )
            for item in self.spend_profile
        )


class RecommendationResponse(BaseModel):
    """Discriminated on `kind`: a full package, or an honest early exit.

    The structured recommendation is the first part of the two-part response
    (D-5); narration rides inside it (template or LLM) so a single call is
    complete even with the LLM disabled.
    """

    kind: Literal["recommendation", "clarification", "unsupported_route", "scope_refusal"]
    recommendation: FinalRecommendation | None = None
    clarification: ClarificationRequest | None = None
    unsupported_route: UnsupportedRoute | None = None
    message: str | None = None
    persisted: bool | None = Field(
        default=None,
        description="For the authenticated save endpoint: True iff the lineage "
        "chain was actually written. None on anonymous/non-persisting calls so "
        "the UI can tell a real save from a best-effort one that failed.",
    )


class CardSummary(BaseModel):
    """GET /catalog/cards item — supported cards for pickers."""

    id: UUID
    bank: str
    card_name: str
    annual_fee_inr: int
    has_lounge_access: bool
    acquirable: bool


class CatalogCardsResponse(BaseModel):
    catalog_snapshot_version: str
    cards: tuple[CardSummary, ...]


class SavedGoalSummary(BaseModel):
    """GET /goals list item — one saved goal + its latest recommendation.

    Read straight from persisted rows (no recomputation), so it reflects exactly
    what was stored, including the snapshot version that produced it (D-2)."""

    goal_id: UUID
    goal_name: str
    goal_type: str
    destination_city: str | None
    cabin_class: str | None
    target_miles: int
    target_date: date | None
    status: str
    saved_at: datetime
    summary: str | None
    confidence_score: float | None
    catalog_snapshot_version: str | None


class SavedGoalsResponse(BaseModel):
    """The signed-in user's saved goals, newest first (empty list is valid)."""

    goals: tuple[SavedGoalSummary, ...]


class SavedLedgerEntry(BaseModel):
    """One month of the persisted accumulation ledger — exactly the fields the
    dashboard's progress chart needs, read from the stored JSONB."""

    month: int
    points_earned_this_month: int
    cumulative_target_miles: int


class SavedMilestone(BaseModel):
    milestone_id: UUID
    card_id: UUID
    expected_month: int
    bonus_points: int


class SavedTransferPlanItem(BaseModel):
    from_card_id: UUID
    to_partner_id: UUID
    points: int
    planned_month: int


class SavedAllocationDetail(BaseModel):
    """One category's persisted earn story (results.py card_allocations JSONB):
    where it routes, the rate, and the projected monthly points — the 'why' the
    saved-goal view shows, matching the live simulator's per-category rows."""

    category_slug: str
    card_id: str
    monthly_spend_inr: int
    earn_rate: Decimal
    effective_miles_per_100inr: Decimal
    monthly_points: int
    monthly_miles: int = 0
    notes: tuple[str, ...] = ()
    # Reward-system story fields (None/absent on goals saved before they
    # were persisted) — mirrors StrategyAllocationDetail's enrichment.
    currency_name: str | None = None
    transfer_ratio_from: int | None = None
    transfer_ratio_to: int | None = None
    category_label: str | None = None
    runner_up_card_id: str | None = None
    runner_up_miles_per_100inr: Decimal | None = None
    # Counterfactual-verified cause attribution (2026-07-13; absent on older
    # saves): why the higher-rated runner-up still lost this category, plus
    # the whole-plan miles delta of the swap. Deliberately `str`, not the
    # domain Literal — stored JSONB may carry values from any engine version,
    # and an unknown reason must deserialize (the UI falls back generically).
    runner_up_reason: str | None = None
    runner_up_plan_delta_miles: int | None = None


class SavedScoreBreakdown(BaseModel):
    """The 6-part composite behind a saved recommendation (now persisted)."""

    goal_achievement: Decimal
    efficiency: Decimal
    cost: Decimal
    simplicity: Decimal
    portfolio_utilization: Decimal
    risk: Decimal


class SavedStrategyOption(BaseModel):
    """One tier of the 'your cards → +1 → +2' comparison, persisted compactly
    (no full simulation) so the saved view can render the story, not just the
    single winner. `is_recommended` marks the chosen tier."""

    strategy_id: str
    archetype: str
    headline_differentiator: str
    miles_at_target_date: int
    months_to_goal: int | None = None
    total_fees_inr: int
    # Fee split (absent on older saves — clients fall back to the total).
    card_fees_inr: int | None = None
    transfer_fees_inr: int | None = None
    cards_used: tuple[str, ...] = ()
    cards_to_acquire: tuple[str, ...] = ()
    score: Decimal | None = None
    is_recommended: bool = False
    co_recommended: bool = False


class SavedStrategy(BaseModel):
    """The recommended strategy as persisted (results.py's JSONB payloads,
    reconstructed — never recomputed). Card/partner ids are strings exactly as
    stored; the client resolves names via the catalog it already fetches."""

    spend_allocation: dict[str, str]
    cards_used: tuple[str, ...]
    cards_to_acquire: tuple[str, ...]
    ledger: tuple[SavedLedgerEntry, ...]
    months_to_goal: int | None
    optimization_score: Decimal | None
    milestones: tuple[SavedMilestone, ...]
    transfer_plan: tuple[SavedTransferPlanItem, ...]
    # Story fields (empty on goals saved before they were persisted).
    allocation_details: tuple[SavedAllocationDetail, ...] = ()
    score_breakdown: SavedScoreBreakdown | None = None
    headline_differentiator: str | None = None


class SavedActionItem(BaseModel):
    priority: int
    action: str
    impact: str | None = None
    card_id: UUID | None = None


class SavedAdjustmentOption(BaseModel):
    """One persisted Stage-6 adjustment ("what would close the gap") — stored
    with best-effort infeasible saves; empty on feasible and older saves."""

    kind: str
    description: str


class SavedGoalDetail(BaseModel):
    """GET /goals/{id} — one saved goal's full stored recommendation.

    Everything here is a persisted engine artifact (D-2 lineage): re-opening a
    goal shows what was computed at save time, against the snapshot named here.
    `strategy` is None only when nothing was allocatable (no simulation_results
    row; infeasible goals normally persist a best-effort plan and
    `recommendation_type` records the infeasibility) — the summary/reasoning
    then carry the adjustment story."""

    goal_id: UUID
    goal_name: str
    goal_type: str
    origin_city: str | None
    destination_city: str | None
    cabin_class: str | None
    num_passengers: int | None
    target_miles: int
    target_date: date | None
    status: str
    saved_at: datetime
    recommendation_type: str | None
    summary: str | None
    reasoning: str | None
    action_items: tuple[SavedActionItem, ...]
    confidence_score: float | None
    catalog_snapshot_version: str | None
    engine_version: str | None
    strategy: SavedStrategy | None
    # The 'your cards → +1 → +2' comparison tiers (empty on older saves and on
    # the infeasible path). Lives on the detail, not the strategy, because it
    # spans strategies.
    strategy_options: tuple[SavedStrategyOption, ...] = ()
    # The Stage-6 adjustment menu for best-effort infeasible saves (empty when
    # feasible or on older saves). Detail-scoped like strategy_options: it
    # belongs to the verdict, not any one strategy.
    adjustment_options: tuple[SavedAdjustmentOption, ...] = ()
    # Cosmetic id → display-name maps resolved from the *current* snapshot so
    # the client can label cards/partners without extra calls. Ids no longer in
    # the catalog are simply absent (client falls back to a generic label).
    card_names: dict[str, str] = {}
    partner_names: dict[str, str] = {}
