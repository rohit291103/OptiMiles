"""Shared kernel: Pydantic models for every pipeline object.

Rules (backend-build-plan-v1 §4, system-execution-flow-v1 §3):
- This package imports NOTHING from the rest of `app` — pure data types only.
- No I/O, no DB, no LLM, no engine logic. Engines consume and produce these.
- All models are frozen: objects only gain structure moving downstream;
  a stage never mutates its input.
"""

from app.domain.catalog import (
    AwardChartEntry,
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    RewardCategoryRule,
    RewardCurrency,
    RewardMilestone,
    TransferPartner,
)
from app.domain.context import (
    ConstraintSet,
    PlanningContext,
    SpendProfile,
    SpendProfileItem,
    WalletCard,
)
from app.domain.enums import (
    AwardType,
    CabinClass,
    GoalStatus,
    GoalType,
    MilestonePeriod,
    MilestoneType,
    PartnerType,
    SimulationStatus,
    SpendCategory,
    StrategyArchetype,
)
from app.domain.feasibility import AdjustmentOption, FeasibilityVerdict, PortfolioAssessment
from app.domain.goal import RewardRequirement, TravelGoal
from app.domain.intent import ClarificationRequest, ParsedGoalIntent
from app.domain.narration import ActionItem, RecommendationNarration
from app.domain.opportunity import (
    CapStructure,
    CardAggregates,
    OpportunitySet,
    RewardOpportunity,
    TransferPath,
)
from app.domain.ranking import RankedStrategy, ScoreBreakdown
from app.domain.recommendation import FinalRecommendation
from app.domain.resolution import GoalResolution, UnsupportedRoute
from app.domain.simulation import MonthLedgerEntry, SimulationOutcome, TransferExecution
from app.domain.strategy import CandidateStrategy, ExpectedMilestone, TransferPlanItem

__all__ = [
    "ActionItem",
    "AdjustmentOption",
    "AwardChartEntry",
    "AwardType",
    "CabinClass",
    "CandidateStrategy",
    "CapStructure",
    "Card",
    "CardAggregates",
    "CatalogSnapshot",
    "ClarificationRequest",
    "ConstraintSet",
    "CurrencyTransferLink",
    "ExpectedMilestone",
    "FeasibilityVerdict",
    "FinalRecommendation",
    "GoalResolution",
    "GoalStatus",
    "GoalType",
    "MilestonePeriod",
    "MilestoneType",
    "MonthLedgerEntry",
    "OpportunitySet",
    "ParsedGoalIntent",
    "PartnerType",
    "PlanningContext",
    "PortfolioAssessment",
    "RankedStrategy",
    "RecommendationNarration",
    "RewardCategoryRule",
    "RewardCurrency",
    "RewardMilestone",
    "RewardOpportunity",
    "RewardRequirement",
    "ScoreBreakdown",
    "SimulationOutcome",
    "SimulationStatus",
    "SpendCategory",
    "SpendProfile",
    "SpendProfileItem",
    "StrategyArchetype",
    "TransferExecution",
    "TransferPartner",
    "TransferPath",
    "TransferPlanItem",
    "TravelGoal",
    "UnsupportedRoute",
    "WalletCard",
]
