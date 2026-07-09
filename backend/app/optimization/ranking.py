"""Stage 9 — ranking & selection (`rank`), weights from versioned config.

Ranking scores SIMULATED outcomes, never generator estimates: `rank()` first
applies `reconcile_claim` (the claimed_total_miles reconciliation the
blueprint puts at the Stage 8/9 boundary — simulation wins, a >10% gap flags
a generator bug in logs), then prunes, then applies hard rules, then scores.

Pipeline (SRE workflow, optimization-engine-spec §3.2):

1. **Prune.** Exact duplicates (same allocation + acquisitions + transfer
   plan) merge, first-in wins. Dominated candidates — worse-or-equal on every
   raw dimension (months, miles, fees, complexity, wallet-spend share, risk
   penalties) and strictly worse on one — are dropped before scoring, so
   normalization never rewards a strategy for the company it keeps.
2. **Hard rules before weights.** `misses_goal` candidates rank below every
   achieving one regardless of score (they are kept for transparency, never
   recommended). User constraints were filtered at generation (BR-03).
3. **Score.** Six named sub-scores, 0–100 each (`ScoreBreakdown` — every
   ranking decision explainable, BR-04/AD-06). Formulas, with quantization
   2dp ROUND_DOWN unless stated:

     goal_achievement = (horizon − months_to_goal)/horizon × 90
                        + 10 if buffer_achieved     (0 if goal missed)
     efficiency       = min-max over candidates of miles_at_target_date
                        (all equal → 100)
     cost             = inverted min-max of total_fees_inr (all equal → 100)
     simplicity       = 100 − 15×(cards−1) − 25×acquisitions
                        − 5×(transfers−1), floor 0
     portfolio_util   = 100 × monthly spend routed to wallet cards / total
     risk             = 100 − 20 per transfer ≥ 90% of its link's annual cap
                        − 15 if milestone bonuses > 25% of transferred points
                        − 10 per transfer link slower than 7 days
                        − 10 if the buffer is missed, floor 0

     composite = Σ(weight × sub-score) / Σ weights,
                 quantized 0.01 ROUND_HALF_UP → `simulation_results.optimization_score`

   Efficiency/cost are relative to the candidate set (deterministic and
   honest — "best of what's on the table"), the rest absolute.
4. **Select.** Deterministic order: achieving before missing, then score
   desc, then lower complexity (BR-05 near-tie preference), then
   strategy_id. A top-2 score gap below the config threshold marks both
   `co_recommended` (honesty beats a manufactured winner). Each strategy
   gets a deterministic `headline_differentiator` for narration: fastest /
   no new cards / lowest fees / simplest / balanced.

Weights live in `config/ranking-weights-v1.yaml` (build rule 5), loaded via
`load_ranking_weights`. Preference-aware weight modulation (DP-07) arrives
with the preference-collecting UX — deterministic default weights until then.
The LLM never reorders, vetoes, or blesses any of this.
"""

import logging
from collections.abc import Sequence
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Self
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import (
    CandidateStrategy,
    CurrencyTransferLink,
    PlanningContext,
    RankedStrategy,
    ScoreBreakdown,
    SimulationOutcome,
)

logger = logging.getLogger(__name__)

_TWO_DP = Decimal("0.01")
_RECONCILE_LOG_GAP = Decimal("0.10")  # >10% claim/simulation gap = generator bug
_NEVER = 10**6  # months_to_goal for goal-missing candidates in dominance checks


class RankingWeights(BaseModel):
    """The versioned scoring policy (config, not code — build rule 5)."""

    model_config = ConfigDict(frozen=True)

    version: str
    goal_achievement: Decimal = Field(ge=0)
    efficiency: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)
    simplicity: Decimal = Field(ge=0)
    portfolio_utilization: Decimal = Field(ge=0)
    risk: Decimal = Field(ge=0)
    near_tie_threshold: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _weights_must_weigh(self) -> Self:
        if self.total() <= 0:
            raise ValueError("ranking weights must sum to a positive value")
        return self

    def total(self) -> Decimal:
        return (
            self.goal_achievement
            + self.efficiency
            + self.cost
            + self.simplicity
            + self.portfolio_utilization
            + self.risk
        )


def load_ranking_weights(path: Path) -> RankingWeights:
    raw = yaml.safe_load(path.read_text())
    return RankingWeights(
        version=str(raw["version"]),
        near_tie_threshold=raw["near_tie_threshold"],
        **raw["weights"],
    )


def reconcile_claim(strategy: CandidateStrategy, outcome: SimulationOutcome) -> CandidateStrategy:
    """Where the simulation disagrees with the generator's claim, the
    simulation wins: the strategy is re-labeled with the simulated total and
    the correction is recorded for narration. A large gap is a generator bug
    — flagged in logs, per the Stage 8 failure contract."""
    simulated = outcome.miles_at_target_date
    claimed = strategy.claimed_total_miles
    if claimed == simulated:
        return strategy
    if abs(claimed - simulated) > max(claimed, 1) * _RECONCILE_LOG_GAP:
        logger.warning(
            "strategy %s: generator claimed %s miles but simulation landed %s — "
            "possible generator bug",
            strategy.strategy_id,
            f"{claimed:,}",
            f"{simulated:,}",
        )
    note = (
        f"generator estimate of {claimed:,} miles corrected to the simulated "
        f"{simulated:,} (simulation wins on disagreement)"
    )
    return strategy.model_copy(
        update={
            "claimed_total_miles": simulated,
            "assumptions": (*strategy.assumptions, note),
        }
    )


def rank(
    pairs: Sequence[tuple[CandidateStrategy, SimulationOutcome]],
    context: PlanningContext,
    weights: RankingWeights,
) -> tuple[RankedStrategy, ...]:
    reconciled = [(reconcile_claim(strategy, outcome), outcome) for strategy, outcome in pairs]
    survivors = _prune(reconciled, context)
    if not survivors:
        return ()

    raws = [_raw_dimensions(strategy, outcome, context) for strategy, outcome in survivors]
    breakdowns = [
        _breakdown(raw, raws, outcome, context)
        for raw, (_, outcome) in zip(raws, survivors, strict=True)
    ]
    scored = [
        (strategy, outcome, breakdown, _composite(breakdown, weights), raw)
        for (strategy, outcome), breakdown, raw in zip(survivors, breakdowns, raws, strict=True)
    ]
    scored.sort(
        key=lambda entry: (
            1 if _misses(entry[1]) else 0,  # hard rule: achieving above missing
            -entry[3],
            entry[4].complexity_units,  # BR-05: ties prefer the simpler plan
            entry[0].strategy_id,
        )
    )

    achieving = [entry for entry in scored if not _misses(entry[1])]
    co_recommended: set[str] = set()
    if len(achieving) >= 2 and achieving[0][3] - achieving[1][3] < weights.near_tie_threshold:
        co_recommended = {achieving[0][0].strategy_id, achieving[1][0].strategy_id}

    headlines = _headlines(scored, context)
    return tuple(
        RankedStrategy(
            strategy=strategy,
            simulation=outcome,
            score=score,
            score_breakdown=breakdown,
            rank=position,
            headline_differentiator=headlines[strategy.strategy_id],
            co_recommended=strategy.strategy_id in co_recommended,
        )
        for position, (strategy, outcome, breakdown, score, _) in enumerate(scored, start=1)
    )


# ── Raw dimensions (pruning + tie-breaking currency) ──────────────────────


class _RawDimensions(BaseModel):
    model_config = ConfigDict(frozen=True)

    months: int  # _NEVER when the goal is missed
    miles: int
    fees: int
    complexity_units: int
    wallet_spend_share: Decimal  # 0–1
    risk_penalty: int

    def dominated_by(self, other: "_RawDimensions") -> bool:
        no_worse = (
            other.months <= self.months
            and other.miles >= self.miles
            and other.fees <= self.fees
            and other.complexity_units <= self.complexity_units
            and other.wallet_spend_share >= self.wallet_spend_share
            and other.risk_penalty <= self.risk_penalty
        )
        return no_worse and other != self


def _misses(outcome: SimulationOutcome) -> bool:
    return outcome.misses_goal or outcome.months_to_goal is None


def _raw_dimensions(
    strategy: CandidateStrategy, outcome: SimulationOutcome, context: PlanningContext
) -> _RawDimensions:
    return _RawDimensions(
        months=_NEVER if _misses(outcome) else outcome.months_to_goal or 0,
        miles=outcome.miles_at_target_date,
        fees=outcome.total_fees_inr,
        complexity_units=_complexity_units(strategy),
        wallet_spend_share=_wallet_spend_share(strategy, context),
        risk_penalty=_risk_penalty(strategy, outcome, context),
    )


def _prune(
    pairs: Sequence[tuple[CandidateStrategy, SimulationOutcome]], context: PlanningContext
) -> list[tuple[CandidateStrategy, SimulationOutcome]]:
    unique: list[tuple[CandidateStrategy, SimulationOutcome]] = []
    seen: set[object] = set()
    for strategy, outcome in pairs:
        fingerprint = (
            tuple(sorted((c.value, str(card)) for c, card in strategy.spend_allocation.items())),
            strategy.cards_to_acquire,
            strategy.transfer_plan,
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append((strategy, outcome))

    raws = [_raw_dimensions(strategy, outcome, context) for strategy, outcome in unique]
    return [
        pair
        for pair, raw in zip(unique, raws, strict=True)
        if not any(raw.dominated_by(other) for other in raws)
    ]


def _complexity_units(strategy: CandidateStrategy) -> int:
    return (
        15 * (len(strategy.cards_used) - 1)
        + 25 * len(strategy.cards_to_acquire)
        + 5 * max(0, len(strategy.transfer_plan) - 1)
    )


def _wallet_spend_share(strategy: CandidateStrategy, context: PlanningContext) -> Decimal:
    wallet_ids = {w.card_id for w in context.wallet}
    total = 0
    on_wallet = 0
    for item in context.spend_profile.items:
        total += item.monthly_spend_inr
        if strategy.spend_allocation.get(item.category_slug) in wallet_ids:
            on_wallet += item.monthly_spend_inr
    return Decimal(on_wallet) / Decimal(total) if total else Decimal(0)


def _risk_penalty(
    strategy: CandidateStrategy, outcome: SimulationOutcome, context: PlanningContext
) -> int:
    links = _links_by_route(context)
    cards_by_id = {card.id: card for card in context.snapshot.cards}
    penalty = 0
    for transfer in strategy.transfer_plan:
        currency_id = cards_by_id[transfer.from_card_id].reward_currency_id
        link = links.get((currency_id, transfer.to_partner_id))
        if link is None:
            continue
        if link.max_transfer_points is not None and Decimal(transfer.points) >= Decimal(
            link.max_transfer_points
        ) * Decimal("0.9"):
            penalty += 20  # a plan living at a hard cap has no room for error
        if link.processing_days_max > 7:
            penalty += 10  # slow links put the arrival month at risk
    transferred = sum(item.points for item in strategy.transfer_plan)
    bonuses = sum(milestone.bonus_points for milestone in strategy.expected_milestones)
    if transferred and Decimal(bonuses) > Decimal(transferred) * Decimal("0.25"):
        penalty += 15  # heavy dependence on milestone triggers
    if not outcome.buffer_achieved:
        penalty += 10
    return penalty


def _links_by_route(
    context: PlanningContext,
) -> dict[tuple[UUID, UUID], CurrencyTransferLink]:
    return {(link.currency_id, link.partner_id): link for link in context.snapshot.transfer_links}


# ── Sub-scores and composite ──────────────────────────────────────────────


def _breakdown(
    raw: _RawDimensions,
    all_raws: Sequence[_RawDimensions],
    outcome: SimulationOutcome,
    context: PlanningContext,
) -> ScoreBreakdown:
    horizon = context.horizon_months
    if _misses(outcome):
        goal = Decimal(0)
    else:
        months = outcome.months_to_goal or 0
        goal = Decimal(horizon - months) / Decimal(horizon) * 90
        if outcome.buffer_achieved:
            goal += 10

    return ScoreBreakdown(
        goal_achievement=_down(goal),
        efficiency=_down(_min_max(raw.miles, [r.miles for r in all_raws], higher_is_better=True)),
        cost=_down(_min_max(raw.fees, [r.fees for r in all_raws], higher_is_better=False)),
        simplicity=Decimal(max(0, 100 - raw.complexity_units)),
        portfolio_utilization=_down(raw.wallet_spend_share * 100),
        risk=Decimal(max(0, 100 - raw.risk_penalty)),
    )


def _min_max(value: int, values: Sequence[int], *, higher_is_better: bool) -> Decimal:
    low, high = min(values), max(values)
    if low == high:
        return Decimal(100)
    position = Decimal(value - low) / Decimal(high - low) * 100
    return position if higher_is_better else Decimal(100) - position


def _down(value: Decimal) -> Decimal:
    return value.quantize(_TWO_DP, rounding=ROUND_DOWN)


def _composite(breakdown: ScoreBreakdown, weights: RankingWeights) -> Decimal:
    weighted = (
        weights.goal_achievement * breakdown.goal_achievement
        + weights.efficiency * breakdown.efficiency
        + weights.cost * breakdown.cost
        + weights.simplicity * breakdown.simplicity
        + weights.portfolio_utilization * breakdown.portfolio_utilization
        + weights.risk * breakdown.risk
    )
    return (weighted / weights.total()).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


# ── Headline differentiators (deterministic narration input) ──────────────


def _headlines(
    scored: Sequence[tuple[CandidateStrategy, SimulationOutcome, ScoreBreakdown, Decimal, object]],
    context: PlanningContext,
) -> dict[str, str]:
    del context
    achieving_months = [
        outcome.months_to_goal
        for _, outcome, *_ in scored
        if not _misses(outcome) and outcome.months_to_goal is not None
    ]
    fees = [outcome.total_fees_inr for _, outcome, *_ in scored]
    complexities = [_complexity_units(strategy) for strategy, *_ in scored]
    anyone_acquires = any(strategy.cards_to_acquire for strategy, *_ in scored)

    fastest_months = min(achieving_months, default=None)
    headlines: dict[str, str] = {}
    for strategy, outcome, *_ in scored:
        if (
            not _misses(outcome)
            and outcome.months_to_goal is not None
            and outcome.months_to_goal == fastest_months
            and achieving_months.count(outcome.months_to_goal) == 1
        ):
            label = "fastest"
        elif not strategy.cards_to_acquire and anyone_acquires:
            label = "no new cards"
        elif outcome.total_fees_inr == min(fees) and fees.count(outcome.total_fees_inr) == 1:
            label = "lowest fees"
        elif (
            _complexity_units(strategy) == min(complexities)
            and complexities.count(_complexity_units(strategy)) == 1
        ):
            label = "simplest"
        else:
            label = "balanced"
        headlines[strategy.strategy_id] = label
    return headlines
