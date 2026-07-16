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
   normalization never rewards a strategy for the company it keeps. EXCEPTION:
   a GOAL-ACHIEVING candidate that acquires a card is never pruned for losing
   to a cheaper/faster no-new-card candidate — "add one card" and "use what
   you have" are different trade-offs a user weighs on cost vs. miles, not a
   strict downgrade (dominance among acquiring candidates is still enforced,
   so a worse acquisition can't hide behind a better one; a goal-MISSING
   acquisition gets no such protection — the hard rule below already keeps
   it out of the recommendation).
2. **Hard rules before weights.** `misses_goal` candidates rank below every
   achieving one regardless of score — never recommended over an achieving
   plan. On an infeasible goal every candidate misses by construction (the
   Stage-6 bound is a true upper bound), so the least-bad one ranks first
   and becomes the best-effort recommendation, presented alongside the
   adjustment menu. User constraints were filtered at generation (BR-03).
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
    OpportunitySet,
    PlanningContext,
    RankedStrategy,
    RewardOpportunity,
    ScoreBreakdown,
    SimulationOutcome,
    SpendCategory,
    StrategyAllocationDetail,
    StrategyArchetype,
)
from app.optimization.explain import allocation_detail

logger = logging.getLogger(__name__)

_TWO_DP = Decimal("0.01")
_RECONCILE_LOG_GAP = Decimal("0.10")  # >10% claim/simulation gap = generator bug
_NEVER = 10**6  # months_to_goal for goal-missing candidates in dominance checks


class AcquisitionWeights(BaseModel):
    """A profile over the six Stage-9 sub-scores (config, not code).

    Used as the guided flow's acquisition-selection criteria (decision 9,
    2026-07-13): the user's stated priorities map onto existing sub-scores —
    low fees → cost, reward-ecosystem strength → efficiency, transfer-partner
    quality → risk (cap headroom + processing speed are exactly what the risk
    penalty measures). Ease-to-get is explicitly out of scope. No new scoring
    machinery: the composite formula is Stage 9's, only the weights differ."""

    model_config = ConfigDict(frozen=True)

    goal_achievement: Decimal = Field(ge=0)
    efficiency: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)
    simplicity: Decimal = Field(ge=0)
    portfolio_utilization: Decimal = Field(ge=0)
    risk: Decimal = Field(ge=0)

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


class RankingWeights(AcquisitionWeights):
    """The versioned scoring policy (config, not code — build rule 5).

    `acquisition` is the optional second profile the guided flow scores
    extra-card routes with (v2 config); None on configs that predate it."""

    version: str
    near_tie_threshold: Decimal = Field(ge=0)
    acquisition: AcquisitionWeights | None = None


def load_ranking_weights(path: Path) -> RankingWeights:
    raw = yaml.safe_load(path.read_text())
    acquisition_raw = raw.get("acquisition_weights")
    return RankingWeights(
        version=str(raw["version"]),
        near_tie_threshold=raw["near_tie_threshold"],
        acquisition=(
            AcquisitionWeights(**acquisition_raw) if acquisition_raw is not None else None
        ),
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
    *,
    opportunities: OpportunitySet | None = None,
) -> tuple[RankedStrategy, ...]:
    """Rank the simulated candidates. When `opportunities` (the Stage-5 priced
    search space) is supplied, each RankedStrategy also carries the per-category
    earn story (`allocation_details`) for its routing — a presentation reshape,
    never re-priced. Omitted (e.g. in focused unit tests) ⇒ no detail attached,
    ranking is otherwise identical."""
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
    opportunity_index = _opportunity_index(opportunities)
    story = _story_inputs(opportunities, context)
    return tuple(
        RankedStrategy(
            strategy=strategy,
            simulation=outcome,
            score=score,
            score_breakdown=breakdown,
            rank=position,
            headline_differentiator=headlines[strategy.strategy_id],
            co_recommended=strategy.strategy_id in co_recommended,
            allocation_details=_details_for(strategy, opportunity_index, context, story),
        )
        for position, (strategy, outcome, breakdown, score, _) in enumerate(scored, start=1)
    )


def select_route_options(
    ranked: tuple[RankedStrategy, ...], *, max_options: int = 3
) -> tuple[RankedStrategy, ...]:
    """The ≤3 genuinely different routes the package presents (Stage 9's
    'Select', applied to presentation): several archetypes converging on the
    same acquisition set are ONE route to the user — keep the best-ranked plan
    per distinct set of cards-to-acquire, in rank order, capped at
    `max_options`. Ranking order already puts the recommended plan first and
    goal-achieving plans above goal-missing ones, so the survivors are the
    recommended route plus the strongest distinct alternatives. Each survivor
    keeps its ORIGINAL `rank` (1, 3, 4 after a collapse, say) — the field
    records Stage-9 position, not display order; consumers iterate the tuple
    positionally."""
    selected: list[RankedStrategy] = []
    seen_sets: set[frozenset[UUID]] = set()
    for option in ranked:
        acquisition_set = frozenset(option.strategy.cards_to_acquire)
        if acquisition_set in seen_sets:
            continue
        seen_sets.add(acquisition_set)
        selected.append(option)
        if len(selected) == max_options:
            break
    return tuple(selected)


def select_acquisition_pair(
    ranked: tuple[RankedStrategy, ...] | Sequence[RankedStrategy],
    acquisition: AcquisitionWeights,
) -> tuple[RankedStrategy, ...]:
    """The guided flow's two extra-card offerings (decision 9, 2026-07-13).

    Over already-ranked strategies, pick:
      - **cheapest** — the goal-achieving acquiring route with the lowest
        card (joining) fees, ties to the better rank. Selected by fee, not by
        the `cheapest_viable` archetype label: the archetype exists to make
        sure this candidate is *generated*, but Stage 9's duplicate-prune can
        merge its forced plan into an identical `one_new_card` plan (first-in
        wins), so the label is an unreliable witness — the fee is the fact.
      - **best_value** — the goal-achieving `one_new_card` candidate with the
        highest composite under the acquisition-weights profile (Stage 9's
        composite formula, different weights); ties break by original rank.

    Goal-missing candidates are never offered — the pair is a promise that
    these routes clear the goal. If both picks land on the same acquisition
    set they collapse to one route (the higher acquisition-composite plan,
    ties to the better rank) labeled `cheapest_and_best_value`. Each returned
    strategy is a copy carrying its `acquisition_role`; cheapest first."""
    achieving = [entry for entry in ranked if not _misses(entry.simulation)]

    cheapest = min(
        (e for e in achieving if e.strategy.cards_to_acquire),
        key=lambda e: (e.simulation.card_fees_inr, e.rank),
        default=None,
    )
    best_value: RankedStrategy | None = None
    best_composite: Decimal | None = None
    for entry in achieving:  # ranked order ⇒ strict > keeps the better rank on ties
        if entry.strategy.archetype != StrategyArchetype.ONE_NEW_CARD:
            continue
        if not entry.strategy.cards_to_acquire:
            continue
        composite = _composite(entry.score_breakdown, acquisition)
        if best_composite is None or composite > best_composite:
            best_value, best_composite = entry, composite

    if cheapest is None and best_value is None:
        return ()
    if cheapest is None:
        assert best_value is not None
        return (best_value.model_copy(update={"acquisition_role": "best_value"}),)
    if best_value is None:
        return (cheapest.model_copy(update={"acquisition_role": "cheapest"}),)

    same_set = frozenset(cheapest.strategy.cards_to_acquire) == frozenset(
        best_value.strategy.cards_to_acquire
    )
    if same_set:
        cheapest_composite = _composite(cheapest.score_breakdown, acquisition)
        assert best_composite is not None
        keep = (
            best_value
            if best_composite > cheapest_composite
            or (best_composite == cheapest_composite and best_value.rank < cheapest.rank)
            else cheapest
        )
        return (keep.model_copy(update={"acquisition_role": "cheapest_and_best_value"}),)
    return (
        cheapest.model_copy(update={"acquisition_role": "cheapest"}),
        best_value.model_copy(update={"acquisition_role": "best_value"}),
    )


def select_guided_routes(
    ranked: tuple[RankedStrategy, ...],
    acquisition: AcquisitionWeights,
) -> tuple[RankedStrategy, ...] | None:
    """Guided-flow presentation (decisions 8–9): when the current wallet
    can't clear the goal but an acquisition can, present the labeled pair (in
    original rank order) plus the best wallet-only route last (the honest
    best-effort the verdict hero shows). Returns None whenever the reshaping
    doesn't apply — the wallet clears the goal (standard hero + quiet upgrade
    tabs), or nothing acquiring achieves it (the existing best-effort +
    adjustment-menu path) — so callers fall back to `select_route_options`."""
    wallet_clears = any(
        not _misses(entry.simulation) and not entry.strategy.cards_to_acquire
        for entry in ranked
    )
    if wallet_clears:
        return None
    pair = select_acquisition_pair(ranked, acquisition)
    if not pair:
        return None
    routes = list(sorted(pair, key=lambda entry: entry.rank))
    best_effort = next(
        (entry for entry in ranked if not entry.strategy.cards_to_acquire), None
    )
    if best_effort is not None:
        routes.append(best_effort)
    return tuple(routes)


def _opportunity_index(
    opportunities: OpportunitySet | None,
) -> dict[tuple[UUID, SpendCategory], RewardOpportunity]:
    """(card_id, category) → priced opportunity, for reattaching per-category
    earn detail to a ranked strategy's routing. Empty when no set was given."""
    if opportunities is None:
        return {}
    return {
        (o.card_id, o.category_slug): o for o in opportunities.opportunities
    }


class _StoryInputs(BaseModel):
    """Snapshot-derived naming for the allocation story — resolved once per
    rank() call, purely cosmetic (labels, not values)."""

    model_config = ConfigDict(frozen=True)

    all_opportunities: tuple[RewardOpportunity, ...]
    currency_names: dict[UUID, str]
    category_labels: dict[tuple[UUID, SpendCategory], str]


def _story_inputs(
    opportunities: OpportunitySet | None, context: PlanningContext
) -> _StoryInputs:
    if opportunities is None:
        return _StoryInputs(all_opportunities=(), currency_names={}, category_labels={})
    snapshot = context.snapshot
    currency_by_id = {currency.id: currency.currency_name for currency in snapshot.currencies}
    return _StoryInputs(
        all_opportunities=opportunities.opportunities,
        currency_names={
            card.id: currency_by_id[card.reward_currency_id]
            for card in snapshot.cards
            if card.reward_currency_id in currency_by_id
        },
        category_labels={
            (rule.card_id, rule.category_slug): rule.category_label
            for rule in snapshot.category_rules
            if rule.category_slug != SpendCategory.DEFAULT
        },
    )


def _details_for(
    strategy: CandidateStrategy,
    opportunity_index: dict[tuple[UUID, SpendCategory], RewardOpportunity],
    context: PlanningContext,
    story: _StoryInputs,
) -> tuple[StrategyAllocationDetail, ...]:
    """Rebuild the strategy's Assignment (category → priced opportunity) from
    its spend_allocation, then reshape to per-category detail. A category whose
    (card, category) path isn't in the index is skipped — the detail is a
    best-effort story overlay, never a source of truth. The runner-up
    comparison is scoped to the plan's own cards: wallet + this strategy's
    acquisitions."""
    if not opportunity_index:
        return ()
    assignment = {
        category: opportunity_index[(card_id, category)]
        for category, card_id in strategy.spend_allocation.items()
        if (card_id, category) in opportunity_index
    }
    if not assignment:
        return ()
    available = frozenset(
        {w.card_id for w in context.wallet} | set(strategy.cards_to_acquire)
    )
    return allocation_detail(
        assignment,
        context.spend_profile,
        all_opportunities=story.all_opportunities,
        available_card_ids=available,
        currency_names=story.currency_names,
        category_labels=story.category_labels,
        # Enables runner-up cause attribution (counterfactual re-estimate) —
        # the deterministic "why did the higher-rate card lose this category".
        # The forced single-card archetypes are marked so the counterfactual
        # uses their own include_idle_balances=False basis and a declined
        # gaining swap is owned as route_shape.
        context=context,
        single_card_route=strategy.archetype
        in (StrategyArchetype.SIMPLEST_VIABLE, StrategyArchetype.CHEAPEST_VIABLE),
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
    acquires: bool = Field(
        default=False,
        description="True iff this candidate adds a card — see dominated_by",
    )

    def dominated_by(self, other: "_RawDimensions") -> bool:
        # An acquiring candidate that STILL REACHES THE GOAL is never pruned
        # for losing to a cheaper, no-new-card option — "add one cheap card"
        # and "use what you have" are different choices a user weighs on
        # cost vs. miles, not a strict downgrade. Scoped to goal-achieving
        # acquisitions only (months != _NEVER): a goal-missing acquisition
        # gets no special protection and is pruned/ranked normally — the
        # achieving-before-missing hard rule in rank() already keeps it out
        # of the recommendation regardless, so exempting it here would only
        # add dead weight to the candidate set. Dominance among acquiring
        # candidates (Magnus vs. a worse Magnus plan, say) is unaffected —
        # an acquisition can't hide a genuinely dominated sibling.
        if self.acquires and self.months != _NEVER and not other.acquires:
            return False
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
        acquires=bool(strategy.cards_to_acquire),
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


def _composite(breakdown: ScoreBreakdown, weights: AcquisitionWeights) -> Decimal:
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
