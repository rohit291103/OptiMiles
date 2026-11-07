"""Shared kernel: Pydantic models for every pipeline object.

Rules (backend-build-plan-v1 §4, system-execution-flow-v1 §3):
- This package imports NOTHING from the rest of `app` — pure data types only.
- No I/O, no DB, no LLM, no engine logic. Engines consume and produce these.
- All models are frozen: objects only gain structure moving downstream;
  a stage never mutates its input.
"""

from app.domain.activity import (
    CapUse,
    LoungeAllowanceUse,
    LoungeVisit,
    MilestoneProgress,
    ObservedActivity,
    ObservedStatus,
    PeriodWindow,
    SpendEntry,
    SpendGateState,
    UncountableAllowance,
)
from app.domain.catalog import (
    AwardChartEntry,
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    FeeWaiver,
    LoungeAccess,
    LoungeProgram,
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
    AllowancePeriod,
    AwardType,
    CabinClass,
    FeeWaiverKind,
    FeeWaiverWindow,
    GoalStatus,
    GoalType,
    LoungeScope,
    MilestonePeriod,
    MilestoneType,
    OverCapEarn,
    PartnerType,
    ResetAnchor,
    SimulationStatus,
    SpendCategory,
    StrategyArchetype,
    ThresholdComparison,
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
from app.domain.strategy import (
    CandidateStrategy,
    ExpectedMilestone,
    StrategyAllocationDetail,
    TransferPlanItem,
)

__all__ = [
    "ActionItem",
    "AdjustmentOption",
    "AllowancePeriod",
    "AwardChartEntry",
    "AwardType",
    "CabinClass",
    "CandidateStrategy",
    "CapStructure",
    "CapUse",
    "Card",
    "CardAggregates",
    "CatalogSnapshot",
    "ClarificationRequest",
    "ConstraintSet",
    "CurrencyTransferLink",
    "ExpectedMilestone",
    "FeasibilityVerdict",
    "FeeWaiver",
    "FeeWaiverKind",
    "FeeWaiverWindow",
    "FinalRecommendation",
    "GoalResolution",
    "GoalStatus",
    "GoalType",
    "LoungeAccess",
    "LoungeAllowanceUse",
    "LoungeProgram",
    "LoungeScope",
    "LoungeVisit",
    "MilestonePeriod",
    "MilestoneProgress",
    "MilestoneType",
    "MonthLedgerEntry",
    "ObservedActivity",
    "ObservedStatus",
    "OpportunitySet",
    "OverCapEarn",
    "ParsedGoalIntent",
    "PartnerType",
    "PeriodWindow",
    "PlanningContext",
    "PortfolioAssessment",
    "RankedStrategy",
    "RecommendationNarration",
    "ResetAnchor",
    "RewardCategoryRule",
    "RewardCurrency",
    "RewardMilestone",
    "RewardOpportunity",
    "RewardRequirement",
    "ScoreBreakdown",
    "SimulationOutcome",
    "SimulationStatus",
    "SpendCategory",
    "SpendEntry",
    "SpendGateState",
    "SpendProfile",
    "SpendProfileItem",
    "StrategyAllocationDetail",
    "StrategyArchetype",
    "ThresholdComparison",
    "TransferExecution",
    "TransferPartner",
    "TransferPath",
    "TransferPlanItem",
    "TravelGoal",
    "UncountableAllowance",
    "UnsupportedRoute",
    "WalletCard",
]
