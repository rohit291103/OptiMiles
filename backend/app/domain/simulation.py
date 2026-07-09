"""Stage 8 output: the month-by-month receipt for a strategy's claim.

simulate(strategy, context) is a pure function — no DB access during
computation; persistence is the orchestrator's job afterward. Where the
simulation disagrees with the generator's claim, the simulation wins.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransferExecution(BaseModel):
    """A transfer as it lands in the ledger (fee paid, arrival delayed)."""

    model_config = ConfigDict(frozen=True)

    from_card_id: UUID
    to_partner_id: UUID
    points_sent: int = Field(gt=0)
    miles_received: int = Field(ge=0)
    fee_inr: int = Field(ge=0)
    arrival_month: int = Field(ge=0)


class MonthLedgerEntry(BaseModel):
    """One monthly tick: spend → earn (cap-aware) → milestones → transfers."""

    model_config = ConfigDict(frozen=True)

    month: int = Field(ge=0)
    points_by_card: dict[UUID, int] = Field(
        description="Running end-of-month point balance per card (decremented on transfer)"
    )
    points_earned_this_month: int = Field(
        default=0,
        ge=0,
        description="Points earned this month (base + category + milestone bonuses), "
        "the earn delta — NOT the balance; unaffected by transfers-out",
    )
    cap_utilization: dict[UUID, Decimal] = Field(
        default_factory=dict, description="card id → fraction of accelerated cap consumed"
    )
    milestones_triggered: tuple[UUID, ...] = ()
    transfers_executed: tuple[TransferExecution, ...] = ()
    cumulative_target_miles: int = Field(ge=0)


class SimulationOutcome(BaseModel):
    """Full projection for one candidate; persisted to simulation_results with lineage."""

    model_config = ConfigDict(frozen=True)

    strategy_id: str
    ledger: tuple[MonthLedgerEntry, ...]
    months_to_goal: int | None = Field(
        default=None, ge=0, description="None if the goal is never reached in the horizon"
    )
    miles_at_target_date: int = Field(ge=0)
    total_fees_inr: int = Field(ge=0)
    buffer_achieved: bool
    misses_goal: bool = Field(
        default=False, description="Passed the gate but missed in simulation — never ranks #1"
    )
