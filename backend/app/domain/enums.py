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
