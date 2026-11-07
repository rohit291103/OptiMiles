"""Canonical vocabulary enums. Values match DB CHECK constraints and seed slugs."""

from enum import StrEnum


class SpendCategory(StrEnum):
    """Canonical category slugs (db-schema-v1 §3.1) — the shared key between
    reward_categories, simulation line items, and spend profiles."""

    TRAVEL = "travel"
    DINING = "dining"
    INTERNATIONAL = "international"
    FUEL = "fuel"
    GROCERIES = "groceries"
    UTILITIES = "utilities"
    ONLINE = "online"
    DEFAULT = "default"


class OverCapEarn(StrEnum):
    """What spend ABOVE a category rule's reward cap earns (migration 0009).

    Stated per capped rule from the issuer's terms — never assumed. Before
    2026-11-02 the schema hard-wired BASE_RATE for every cap, which overstated
    cards like SBI Cashback that pay nothing once the cap is reached.
    """

    BASE_RATE = "base_rate"  # the card's base_earn_rate (e.g. Axis Atlas travel)
    NOTHING = "nothing"  # zero (e.g. SBI Cashback past ₹2,000 cashback/cycle)


class CabinClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class AwardType(StrEnum):
    SAVER = "saver"
    ADVANTAGE = "advantage"


class PartnerType(StrEnum):
    AIRLINE = "airline"
    HOTEL = "hotel"


class MilestoneType(StrEnum):
    SPEND_BONUS = "spend_bonus"
    WELCOME_BONUS = "welcome_bonus"
    ANNIVERSARY_BONUS = "anniversary_bonus"
    CATEGORY_BONUS = "category_bonus"


class LoungeScope(StrEnum):
    """Domestic and international entitlements are ALWAYS counted separately.

    They almost never match on an Indian card — Regalia Gold gives 3 domestic
    visits a quarter behind a spend gate and 6 international a year with no
    gate — so one combined number could only ever be wrong.
    """

    DOMESTIC = "domestic"
    INTERNATIONAL = "international"


class AllowancePeriod(StrEnum):
    """The window a lounge visit allowance (or its spend gate) is counted over.

    Deliberately NOT `MilestonePeriod`, despite the overlap: a milestone
    period bounds an accrual of points and needs ONE_TIME; an allowance period
    bounds a count of visits and needs STATEMENT_CYCLE. Sharing one enum would
    let a nonsense combination typecheck.
    """

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"
    STATEMENT_CYCLE = "statement_cycle"
    LIFETIME = "lifetime"


class ResetAnchor(StrEnum):
    """What an allowance period is measured against.

    Seeded explicitly per card, never defaulted (roadmap decision 2026-08-26).
    Issuers variously reset on the calendar quarter, the card anniversary, or
    the statement cycle, and assuming the calendar quarter would produce a
    confidently wrong visit count — worse than no count at all, because it
    sends someone to a lounge desk to be turned away.
    """

    CALENDAR_QUARTER = "calendar_quarter"
    CALENDAR_YEAR = "calendar_year"
    CARD_ANNIVERSARY = "card_anniversary"
    STATEMENT_CYCLE = "statement_cycle"
    NOT_APPLICABLE = "not_applicable"


class MilestonePeriod(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


class GoalType(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    CUSTOM = "custom"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class SimulationStatus(StrEnum):
    DRAFT = "draft"
    COMPUTING = "computing"
    COMPLETED = "completed"
    STALE = "stale"


class StrategyArchetype(StrEnum):
    """Bounded candidate-generation archetypes (blueprint Stage 7)."""

    STATUS_QUO_OPTIMIZED = "status_quo_optimized"
    ONE_NEW_CARD = "one_new_card"
    CONCENTRATED = "concentrated"
    SIMPLEST_VIABLE = "simplest_viable"
    CHEAPEST_VIABLE = "cheapest_viable"


class FeeWaiverKind(StrEnum):
    """What a card's issuer publishes about waiving the annual fee on spend.

    `NONE` is a sourced ANSWER ("the issuer's fee schedule lists no waiver"),
    not a gap. A card we have not researched has no fee-waiver row at all —
    "not covered yet" — and the two must never be conflated: telling someone
    "there is no waiver" when we simply have not looked is an invented fact.
    """

    SPEND_BASED = "spend_based"
    NONE = "none"


class ThresholdComparison(StrEnum):
    """Whether reaching the threshold exactly is enough.

    Issuers word this differently and it decides the answer at the boundary:
    HDFC "Spend Rs. 4,00,000" and SBI "Rs.2 Lakh or more" are met AT the
    figure; HSBC's "exceeds ₹800,000" is not.
    """

    AT_LEAST = "at_least"
    MORE_THAN = "more_than"


class FeeWaiverWindow(StrEnum):
    """Which spend the issuer measures, relative to which fee.

    PRECEDING_CARD_YEAR — the 12 months / card anniversary year before a
        renewal; meeting it waives THAT renewal's fee (HDFC, Axis Magnus).
    CURRENT_CARD_YEAR — spend during the card year a fee was charged for;
        meeting it reverses THAT year's fee (HSBC TravelOne).
    DAYS_365_BEFORE_FEE_DATE — the 365 days before the annual-fee billing
        date (SBI Cashback).

    All three end at a renewal, which is what lets one month-only window
    (`simulation/periods.renewal_window`) stay inside each of them.
    """

    PRECEDING_CARD_YEAR = "preceding_card_year"
    CURRENT_CARD_YEAR = "current_card_year"
    DAYS_365_BEFORE_FEE_DATE = "days_365_before_fee_date"
