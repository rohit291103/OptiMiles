"""Logged activity — what the user tells us they actually did, and what that
proves about their caps, milestones and lounge allowances.

Roadmap Phase 1 (lounge visit logging) and Phase 2 (spend logging) are ONE
pattern by decision, not two: both are "I used this card on this date", both
are counted inside a `PeriodWindow`, and the lounge spend gate is evaluated
from the spend log — so they cannot be built independently anyway.

THE HONESTY MODEL, which every type here encodes.
A manual log is a LOWER BOUND on what happened. The user forgets entries; they
never invent them. So:

  * logged spend can prove a milestone or a spend gate was REACHED,
    but can never prove one was missed — hence `ObservedStatus.NOT_PROVEN`
    rather than a "not reached" that would read as a fact;
  * logged visits give "at least N used", which makes the remaining
    allowance an UPPER bound — `remaining_at_most`.

The field names carry the bound because a caller that reads `remaining` as
exact will eventually print "you have 2 lounge visits left" to someone who has
none, and the roadmap is explicit that a wrong count is worse than no count.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.catalog import FeeWaiver
from app.domain.enums import AllowancePeriod, LoungeScope, SpendCategory


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ObservedStatus(StrEnum):
    """What the log can prove about a threshold.

    There is deliberately no NOT_REACHED. Absence of a logged entry is absence
    of evidence, not evidence of absence, and the difference is the whole
    reason this feature can be trusted.
    """

    REACHED = "reached"
    NOT_PROVEN = "not_proven"


class PeriodWindow(_Frozen):
    """A half-open window `[start, end)` that a logged activity falls into.

    Half-open so consecutive windows tile with no gap and no overlap: a visit
    on 1 April belongs to Q2 alone. `end` is the first day of the NEXT window
    and is never itself contained. Built by `simulation/periods.py`; a value
    type here so the domain stays free of engine imports.
    """

    start: date
    end: date
    label: str = Field(description="How a cardholder would say it: 'Jul–Sep 2026'")

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end


# ── What the user logs ───────────────────────────────────────────────────


class SpendEntry(_Frozen):
    """One spend the user recorded against a card.

    `category_slug` is the canonical catalog vocabulary, chosen by the user —
    there is no merchant→category mapping (roadmap decision 2026-08-26: a wrong
    mapping produces a wrong recommendation, and maintaining one is a standing
    commitment we declined).
    """

    id: UUID
    card_id: UUID
    occurred_on: date
    amount_inr: int = Field(gt=0)
    category_slug: SpendCategory
    note: str | None = None


class LoungeVisit(_Frozen):
    """One lounge visit the user recorded.

    Logged against (card, scope), NOT against a specific entitlement row: a
    card can hold several tiers for the same scope and the cardholder has no
    reason to know which one they are on. Attribution to a tier is the
    calculator's job.
    """

    id: UUID
    card_id: UUID
    occurred_on: date
    scope: LoungeScope
    guest_count: int = Field(default=0, ge=0)
    airport_code: str | None = Field(
        default=None,
        description="Free IATA-style code (DEL, BOM). No FK — the airport "
        "directory is a separate data track and must not block this.",
    )
    note: str | None = None


# ── What the log proves ──────────────────────────────────────────────────


class CapUse(_Frozen):
    """Progress against one accelerated-earning cap, from logged spend only."""

    card_id: UUID
    category_slug: SpendCategory
    category_label: str
    period: AllowancePeriod
    window: PeriodWindow
    cap_inr: int = Field(gt=0)
    logged_spend_inr: int = Field(ge=0, description="A LOWER bound on real spend")
    remaining_inr_at_most: int = Field(ge=0)
    fraction_used_at_least: Decimal = Field(ge=0)
    anchor_assumed: bool = Field(
        default=True,
        description="The catalog states a cap's PERIOD but not what it resets "
        "against; a calendar reset is assumed and the UI must say so.",
    )


class MilestoneProgress(_Frozen):
    """Progress toward one spend milestone, from logged spend only."""

    card_id: UUID
    milestone_id: UUID
    description: str | None
    bonus_points: int = Field(ge=0)
    threshold_inr: int = Field(gt=0)
    window: PeriodWindow | None = Field(
        default=None, description="None for one-time milestones — nothing resets"
    )
    logged_spend_inr: int = Field(ge=0)
    remaining_inr_at_most: int = Field(ge=0)
    status: ObservedStatus
    anchor_assumed: bool = True


class SpendGateState(_Frozen):
    """Whether the spend condition on a lounge tier is provably unlocked.

    Measured over the PRECEDING window — Regalia Gold's 3 domestic visits this
    quarter are unlocked by ₹60,000 spent *last* quarter. The off-by-one-period
    is the condition cardholders most often get wrong.
    """

    threshold_inr: int = Field(gt=0)
    window: PeriodWindow
    logged_spend_inr: int = Field(ge=0)
    status: ObservedStatus


class LoungeAllowanceUse(_Frozen):
    """One lounge entitlement, with what the log proves about its use."""

    card_id: UUID
    program_id: UUID
    program_name: str
    scope: LoungeScope
    is_unlimited: bool = Field(
        description="Explicit so no caller has to interpret a null allowance — "
        "null means unlimited and 0 means none, opposite answers"
    )
    allowance: int | None = Field(default=None, ge=0)
    period: AllowancePeriod
    window: PeriodWindow | None = Field(
        default=None, description="None when nothing resets (unlimited entitlements)"
    )
    visits_logged_at_least: int = Field(ge=0)
    guest_visits_logged: int = Field(ge=0)
    remaining_at_most: int | None = Field(
        default=None, ge=0, description="None when unlimited; an UPPER bound otherwise"
    )
    guests_share_allowance: bool = False
    enrollment_required: bool = False
    enrollment_url: str | None = None
    gate: SpendGateState | None = None
    conditions: str | None = None


class UncountableAllowance(_Frozen):
    """An entitlement we decline to count, and the reason in the user's terms.

    Emitted instead of a number when the reset anchor needs a per-card date the
    product does not collect. Saying "we need your card open date to count this"
    is an acceptable answer; a guessed count is not.
    """

    card_id: UUID
    scope: LoungeScope
    reason: str


class CardRenewalMonth(_Frozen):
    """The month a user's annual fee is charged on one card — optional.

    A month, not a date, by decision (2026-11-02-fee-waiver-progress): the
    waiver window provable from a month alone sits inside the issuer's real
    window whatever the day, so the day buys at most one month of countable
    spend at the cost of something most users would have to look up.
    """

    card_id: UUID
    renewal_month: int = Field(ge=1, le=12)


class FeeWaiverCoverage(StrEnum):
    """Which of four answers a card's fee-waiver row is.

    TRACKED — a spend-based waiver, and the user told us their renewal month,
        so progress is counted.
    NEEDS_RENEWAL_MONTH — a spend-based waiver, but no renewal month: the terms
        are stated, the progress is not. We never assume a window.
    NO_WAIVER — the issuer publishes no spend-based waiver (a sourced answer).
    NOT_COVERED — we have not researched this card's waiver. NOT the same as
        NO_WAIVER, and the UI must not render it as one.
    """

    TRACKED = "tracked"
    NEEDS_RENEWAL_MONTH = "needs_renewal_month"
    NO_WAIVER = "no_waiver"
    NOT_COVERED = "not_covered"


class FeeWaiverCount(_Frozen):
    """What the log proves toward one card's waiver, over the counted window.

    The window is the 11 whole months between renewal months
    (`simulation/periods.renewal_window`) — inside the issuer's real window
    whatever day the fee falls on, so the count stays a lower bound. Spend in
    the renewal month itself is not counted.
    """

    renewal_label: str = Field(description="The renewal this counts toward: 'Mar 2027'")
    decides_fee_label: str = Field(
        description="The fee this window decides. The renewal at its end for most "
        "issuers; for a CURRENT_CARD_YEAR waiver (HSBC) the fee charged at its START, "
        "a year earlier — the copy must name this, not the renewal."
    )
    window: PeriodWindow
    logged_spend_inr: int = Field(
        ge=0, description="Eligible logged spend in the window — a LOWER bound"
    )
    remaining_inr_at_most: int = Field(
        ge=0,
        description="Whole rupees still needed, an UPPER bound. For a 'more than' "
        "threshold this includes the one rupee past the figure. 0 iff REACHED.",
    )
    status: ObservedStatus
    subject_to_exclusions: bool = Field(
        default=False,
        description="The issuer excludes spend our log cannot separate (rent, wallet "
        "loads, or an undefined 'eligible spend'), so a REACHED is reached on the "
        "log, subject to those — not proof — and 'at most' holds only for counted spend.",
    )
    note: str | None = Field(
        default=None, description="The exclusion caveat in the user's words, when it applies"
    )


class FeeWaiverProgress(_Frozen):
    """One wallet card's annual-fee waiver: the terms, and what the log proves."""

    card_id: UUID
    coverage: FeeWaiverCoverage
    waiver: FeeWaiver | None = Field(
        default=None, description="The catalog terms. None only when NOT_COVERED."
    )
    needs_verification: bool | None = Field(
        default=None,
        description="True = Listed tier, label it unverified. None = not assessed "
        "(never read it as verified).",
    )
    renewal_month: int | None = Field(
        default=None, ge=1, le=12, description="Echo of what the user told us, if anything"
    )
    reason: str | None = Field(
        default=None, description="Why there is no count, in the user's terms"
    )
    count: FeeWaiverCount | None = None

    @model_validator(mode="after")
    def _shape_matches_coverage(self) -> "FeeWaiverProgress":
        # A count without a renewal month, or a NOT_COVERED row with terms,
        # would be a claim the calculator could not have made.
        if (self.count is not None) != (self.coverage is FeeWaiverCoverage.TRACKED):
            raise ValueError("count is present iff coverage is TRACKED")
        if (self.waiver is None) != (self.coverage is FeeWaiverCoverage.NOT_COVERED):
            raise ValueError("waiver is absent iff coverage is NOT_COVERED")
        return self


class ObservedActivity(_Frozen):
    """Everything the log proves for one user's wallet, at one date."""

    as_of: date
    card_ids: tuple[UUID, ...]
    caps: tuple[CapUse, ...] = ()
    milestones: tuple[MilestoneProgress, ...] = ()
    lounge: tuple[LoungeAllowanceUse, ...] = ()
    uncountable: tuple[UncountableAllowance, ...] = ()
    fee_waivers: tuple[FeeWaiverProgress, ...] = Field(
        default=(), description="One per wallet card, in wallet order"
    )
    logged_spend_total_inr: int = Field(default=0, ge=0)
    logged_visit_total: int = Field(default=0, ge=0)
    earliest_entry_on: date | None = Field(
        default=None,
        description="How far back the log reaches. Nothing before this date is "
        "known, which is what makes every figure here a bound rather than a fact.",
    )
