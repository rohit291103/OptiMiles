"""Catalog snapshot types — the versioned, immutable read model of catalog tables.

Mirrors db-schema-v1 §3.1 with the v1.1 amendment (backend-build-plan-v1 §3):
reward currencies are first-class and transfer links belong to currencies, not
cards (D-1). Produced solely by the Knowledge Engine; consumed read-only by
Valuation / Optimization / Simulation via PlanningContext.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import (
    AllowancePeriod,
    AwardType,
    CabinClass,
    FeeWaiverKind,
    FeeWaiverWindow,
    LoungeScope,
    MilestonePeriod,
    MilestoneType,
    OverCapEarn,
    PartnerType,
    ResetAnchor,
    SpendCategory,
    ThresholdComparison,
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
    over_cap_earn: OverCapEarn | None = Field(
        default=None,
        description="What spend above the cap earns (base_rate | nothing). Required "
        "on every capped rule and absent on uncapped ones — validate_catalog "
        "CR-01/CR-02 enforce it; the earn math raises rather than assume",
    )
    requires_portal: str | None = Field(
        default=None,
        description="The booking channel this BONUS rate needs (e.g. 'HDFC SmartBuy'); "
        "the same purchase booked directly earns the card's base rate. None = the rate "
        "applies however you pay. Only on accelerated rules — validate_catalog CR-04",
    )
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


class LoungeProgram(_Frozen):
    """A network airport lounge access rides on.

    The programme is not the lounge and not the airport — it is the thing that
    decides whether a given lounge will let this card in. Indian cards ride on
    Priority Pass, DreamFolks, LoungeOne, the Visa/Mastercard lounge
    programmes, or the issuer's own arrangement.
    """

    id: UUID
    program_name: str
    operator: str | None = None
    notes: str | None = None


class LoungeAccess(_Frozen):
    """One card's entitlement, in one programme, for one scope.

    A card typically has SEVERAL of these — Regalia Gold has a domestic row
    (3 visits a quarter, gated on last quarter's spend) and an international
    row (6 a year, ungated). Tiered cards get one row per tier, distinguished
    by `spend_gate_inr`.

    VOCABULARY, deliberately not "cap": a reward cap is a ₹-spend ceiling on
    accelerated earning (`RewardCategoryRule`). A lounge limit counts visits.
    Same English word, unrelated concepts — so this is an *allowance*.

    `visits_per_period = None` means unlimited, never zero. Zero is a real and
    different answer: Infinia grants no complimentary GUEST visits (they are
    chargeable), which is not the same as an unlimited guest entitlement.
    """

    id: UUID
    card_id: UUID
    program_id: UUID
    scope: LoungeScope

    visits_per_period: int | None = Field(
        default=None, ge=0, description="None = unlimited; 0 = none granted"
    )
    period: AllowancePeriod
    reset_anchor: ResetAnchor

    guest_visits_per_period: int | None = Field(default=None, ge=0)
    guests_share_allowance: bool = Field(
        default=False,
        description="True when a guest visit consumes the cardholder's own allowance",
    )

    spend_gate_inr: int | None = Field(
        default=None,
        ge=0,
        description="Visits unlock only after this spend in `spend_gate_period`",
    )
    spend_gate_period: AllowancePeriod | None = None

    enrollment_required: bool = Field(
        default=False,
        description="The benefit does not exist until the holder activates it",
    )
    enrollment_url: str | None = None

    conditions: str | None = Field(
        default=None,
        description="Anything the structured fields cannot carry — per-visit "
        "charges, add-on-holder rules, foreign-currency guest fees",
    )


class FeeWaiver(_Frozen):
    """What one card's issuer publishes about waiving its annual fee on spend.

    At most one per card. Its own row, not columns on `Card`, so it carries
    its own provenance: a waiver is sourced and verified separately from the
    card's fee and earn rate, and a flagged waiver must not flag the card (or
    the reverse) — see `load_unverified_ids`.

    THREE ANSWERS, NOT TWO. `kind=SPEND_BASED` with terms; `kind=NONE`, a
    sourced statement that the issuer lists no waiver (Axis Atlas); and no row
    at all, "not covered yet" (Amex Platinum Travel). `NONE` is never a
    default for a card we have not researched.

    A renewal BENEFIT is not a waiver. Amex Platinum's ₹20L-spend vouchers
    are paid only after the renewal fee is paid, so that card is `NONE`.

    Field consistency (terms present iff SPEND_BASED) is FW-03 in
    `validate_catalog`, so a bad row is reported with every other issue
    rather than failing at construction.
    """

    id: UUID
    card_id: UUID
    kind: FeeWaiverKind
    threshold_inr: int | None = Field(default=None, gt=0)
    threshold_comparison: ThresholdComparison | None = None
    window_kind: FeeWaiverWindow | None = None
    waives_renewal_fee: bool = False
    waives_joining_fee: bool = Field(
        default=False, description="True only where the issuer says the first-year fee too"
    )
    excluded_categories: tuple[SpendCategory, ...] = Field(
        default=(),
        description="Logged categories the issuer names as NOT counting toward the "
        "threshold. Only categories our vocabulary can express; the rest are in "
        "`unmodelled_exclusions`.",
    )
    unmodelled_exclusions: tuple[str, ...] = Field(
        default=(),
        description="What the issuer excludes that our logging vocabulary cannot "
        "separate (rent, wallet loads, …), in the user's words — or a statement "
        "that the issuer's 'eligible spend' is undefined. Never empty just because "
        "nothing was checked.",
    )
    conditions: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_unmodelled_exclusions(self) -> bool:
        """True when logged spend may include spend the issuer does not count.

        Then a REACHED is "reached on your log — subject to the issuer's
        exclusions", not proof: the log is a lower bound on what the user
        SPENT, not on what the issuer COUNTS.
        """
        return bool(self.unmodelled_exclusions)


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
    # Coverage is deliberately partial (CLAUDE.md → tiered coverage): a card
    # with no rows here is "not covered yet", which the read surface states
    # rather than reporting as "no lounge access".
    lounge_programs: tuple[LoungeProgram, ...] = ()
    lounge_access: tuple[LoungeAccess, ...] = ()
    # Also partial by design: a card with no row here is "not covered yet",
    # which is a different answer from a `FeeWaiverKind.NONE` row.
    fee_waivers: tuple[FeeWaiver, ...] = ()
