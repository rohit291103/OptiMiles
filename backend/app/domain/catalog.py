"""Catalog snapshot types — the versioned, immutable read model of catalog tables.

Mirrors db-schema-v1 §3.1 with the v1.1 amendment (backend-build-plan-v1 §3):
reward currencies are first-class and transfer links belong to currencies, not
cards (D-1). Produced solely by the Knowledge Engine; consumed read-only by
Valuation / Optimization / Simulation via PlanningContext.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AwardType,
    CabinClass,
    MilestonePeriod,
    MilestoneType,
    PartnerType,
    SpendCategory,
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class RewardCurrency(_Frozen):
    """A bank's points currency (e.g. HDFC Reward Points) — shared across cards."""

    id: UUID
    currency_name: str
    issuer: str
    expiry_rules: str | None = None


class TransferPartner(_Frozen):
    """A loyalty program points can be transferred into (e.g. KrisFlyer)."""

    id: UUID
    partner_name: str
    program_name: str
    partner_type: PartnerType
    iata_code: str | None = None
    alliance: str | None = None


class CurrencyTransferLink(_Frozen):
    """Transfer relationship: reward currency → partner program (v1.1, D-1).

    Card eligibility for a transfer is derived: card → currency → link.
    """

    id: UUID
    currency_id: UUID
    partner_id: UUID
    ratio_from: int = Field(gt=0, description="Currency points consumed per unit")
    ratio_to: int = Field(gt=0, description="Partner miles credited per unit")
    min_transfer_points: int = Field(ge=0)
    max_transfer_points: int | None = Field(default=None, description="None = uncapped")
    transfer_fee_inr: int = Field(ge=0, default=0)
    processing_days_min: int = Field(ge=0)
    processing_days_max: int = Field(ge=0)
    notes: str | None = None


class Card(_Frozen):
    """A credit card product in the supported catalog."""

    id: UUID
    bank: str
    card_name: str
    card_network: str
    reward_currency_id: UUID
    annual_fee_inr: int = Field(ge=0)
    joining_fee_inr: int = Field(ge=0)
    base_earn_rate: Decimal = Field(ge=0, description="Points per ₹100 on uncategorized spend")
    min_income_inr: int | None = None
    has_lounge_access: bool = False
    acquirable: bool = Field(
        default=True,
        description="False when the card is closed to new applicants (e.g. Atlas, "
        "discontinued 2026) — existing holders keep it, but Stage 7 must never "
        "recommend acquiring it",
    )


class RewardCategoryRule(_Frozen):
    """Accelerated earn rate for one (card, category) pair, with caps."""

    id: UUID
    card_id: UUID
    category_slug: SpendCategory
    category_label: str
    earn_rate: Decimal = Field(ge=0, description="Points per ₹100 in this category")
    monthly_cap_inr: int | None = None
    quarterly_cap_inr: int | None = None
    annual_cap_inr: int | None = None
    notes: str | None = None


class RewardMilestone(_Frozen):
    """Bonus points on crossing a spend threshold (or welcome/anniversary)."""

    id: UUID
    card_id: UUID
    milestone_type: MilestoneType
    spend_threshold_inr: int | None = None
    bonus_points: int = Field(ge=0)
    period: MilestonePeriod
    description: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class AwardChartEntry(_Frozen):
    """Redemption cost for one (partner, route-region, cabin, award type)."""

    id: UUID
    partner_id: UUID
    origin_region: str
    destination_region: str
    cabin_class: CabinClass
    award_type: AwardType
    miles_required: int = Field(gt=0)
    taxes_fees_inr: int | None = None
    notes: str | None = None
    effective_date: date


class CatalogSnapshot(_Frozen):
    """One request = one snapshot. Only active rows; never mixes catalog states.

    version = a SHA-256 content hash over the snapshot's domain objects
    (`cat-<hex>`, computed by `knowledge/versioning.py`) — identical content
    yields an identical version whether loaded from YAML seeds or the DB
    (D-2); persisted alongside every result so runs are byte-replayable.
    """

    version: str
    currencies: tuple[RewardCurrency, ...]
    partners: tuple[TransferPartner, ...]
    transfer_links: tuple[CurrencyTransferLink, ...]
    cards: tuple[Card, ...]
    category_rules: tuple[RewardCategoryRule, ...]
    milestones: tuple[RewardMilestone, ...]
    award_charts: tuple[AwardChartEntry, ...]
