"""API v1 request/response bodies (build-plan §7).

Thin wrappers over the pipeline's typed inputs and outputs. Requests carry the
user-supplied wallet / spend profile / constraints; responses are the domain
`FinalRecommendation` or an honest early-exit discriminated union. The pipeline
owns all the reward logic — these types only shape the HTTP edge.
"""

from datetime import date, datetime
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
