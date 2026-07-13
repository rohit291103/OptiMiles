"""Shared allocation + accumulation math for Stages 6–7 (internal module).

Both the feasibility gate and every strategy archetype answer the same
question — "route each spend category to one card; how many target-program
miles result?" — so the math lives once, here. Two estimators share one
assignment:

**Assignment** (`greedy_assignment`): start from the per-category best
`effective_miles_per_100inr` (ties prefer in-wallet, then lowest card id),
then hill-climb on `bound_miles` accepting the best single-category reroute
until none improves. Because the bound is currency-cap- and milestone-aware,
this one loop IS both the blueprint's "cap-reroute" (Stage 7 failure
scenario) and its "milestone chasing greedy post-pass": a reroute past a
saturated 2L Burgundy cap or into a ₹4L DCB quarterly bonus is accepted
exactly when it increases honestly-countable miles. Deterministic: fixed
category/candidate iteration order, strict-improvement acceptance.

**Feasibility bound** (`bound_miles`) — deliberately OPTIMISTIC, never
understates (a false "infeasible" kills a goal; overstatement is later
truthed by Simulation):

    per card:   points = monthly_points × horizon + balance
                       + milestone bonuses (spend-gated, see below)
    per currency: miles += min(Σ card points, link annual cap) × ratio_to/ratio_from
    best_case  = int(Σ)                      # ONE floor, at the very end

  No whole-block flooring, no min-transfer gate, no transfer-timing haircut,
  no per-month earn flooring. The annual link cap IS applied (once per
  horizon, same ≤12-month deviation as the projector): a saturated Atlas
  30k-EM cap bounds reality no matter how much is earned.

**Claimed estimate** (`claimed_estimate`) — the generator's honest claim,
built to mirror the projector so reconciliation gaps stay small:

    cutoff m   = horizon − 1 − ceil(processing_days_max/30)   per link
                 (a transfer sent later would land at/after the horizon)
    per card:   points@m = balance + floor(monthly_points) × (m+1)
                         + milestone bonuses fired ≤ m
    per card:   send = min(points@m, link cap remaining); skip if below
                min_transfer; whole_block_transfer(send) → sent, miles
    claimed    = Σ miles          # block remainders honestly not counted

Milestone semantics mirror the projector's (module docstring there):
spend_bonus on cumulative routed INR — MONTHLY per month, QUARTERLY per
plan quarter (months 0–2, 3–5, …), ANNUAL/ONE_TIME once within the ≤12-month
horizon; expected fire month = first month cumulative spend ≥ threshold;
welcome_bonus for acquired cards only, month 0; anniversary/category
excluded. All arithmetic exact `Decimal`; every rounding is directional and
stated above.

One documented rounding-path difference from the projector: earning here
multiplies spend by Stage 5's already-4dp-quantized `effective_rate`, whereas
the projector applies the raw cap split (min(spend,cap)×rate + excess×base)
before its own floor. On a CAPPED category with non-round spend this can
differ by a fraction of a point per card-month — single-digit miles over a
horizon, far under `reconcile_claim`'s 10% flag and 0 on every seed-rate
fixture (integration test). It is not bit-for-bit parity; the projector wins
any real disagreement, by design.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain import (
    ConstraintSet,
    CurrencyTransferLink,
    ExpectedMilestone,
    MilestonePeriod,
    MilestoneType,
    OpportunitySet,
    PlanningContext,
    RewardMilestone,
    RewardOpportunity,
    SpendCategory,
    TransferPlanItem,
)
from app.valuation.transfer_math import whole_block_transfer

Assignment = dict[SpendCategory, RewardOpportunity]

_HILL_CLIMB_MAX_STEPS = 64  # safety guard; strict improvement terminates far earlier


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


@dataclass(frozen=True)
class MilestoneFire:
    """One expected milestone trigger: (milestone, 0-based month)."""

    milestone: RewardMilestone
    month: int


@dataclass(frozen=True)
class ClaimedEstimate:
    """What a candidate strategy honestly claims (simulation wins on dispute)."""

    total_miles: int
    transfer_plan: tuple[TransferPlanItem, ...]
    expected_milestones: tuple[ExpectedMilestone, ...]
    cap_bound_currencies: frozenset[UUID] = frozenset()
    """Currencies whose transfer-link annual cap actually CLAMPED this estimate
    (points available exceeded the cap remaining) — the engine-owned fact for
    attribution, as opposed to inferring it from the block-floored plan (which
    false-positives when a cap isn't a multiple of the ratio)."""


def candidate_opportunities(
    opportunities: OpportunitySet, allowed_card_ids: frozenset[UUID]
) -> dict[SpendCategory, tuple[RewardOpportunity, ...]]:
    """Per category, the allowed opportunities in deterministic preference
    order: best effective rate first; ties prefer in-wallet, then lowest id."""
    by_category: dict[SpendCategory, list[RewardOpportunity]] = {}
    for opportunity in opportunities.opportunities:
        if opportunity.card_id in allowed_card_ids:
            by_category.setdefault(opportunity.category_slug, []).append(opportunity)
    return {
        category: tuple(
            sorted(
                items,
                key=lambda o: (
                    -o.effective_miles_per_100inr,
                    0 if o.in_wallet else 1,
                    str(o.card_id),
                ),
            )
        )
        for category, items in by_category.items()
    }


def greedy_assignment(
    opportunities: OpportunitySet,
    context: PlanningContext,
    allowed_card_ids: frozenset[UUID],
    horizon_months: int,
) -> Assignment:
    """Best-rate initial pick + hill-climb on the cap/milestone-aware bound.

    Categories with no allowed opportunity are simply absent (the feasibility
    bound counts them as zero; strategy validation treats that as incomplete).
    """
    candidates = candidate_opportunities(opportunities, allowed_card_ids)
    start: Assignment = {
        category: options[0] for category, options in candidates.items() if options
    }
    return hill_climb(start, candidates, context, horizon_months)


def hill_climb(
    start: Assignment,
    candidates: dict[SpendCategory, tuple[RewardOpportunity, ...]],
    context: PlanningContext,
    horizon_months: int,
) -> Assignment:
    """Accept the best single-category reroute until none strictly improves
    the bound. Different starting basins yield the archetypes' explainably
    different local optima; identical convergences dedupe downstream."""
    assignment = dict(start)
    if not assignment:
        return assignment
    for _ in range(_HILL_CLIMB_MAX_STEPS):
        current = bound_miles(assignment, context, horizon_months)
        best_trial: Assignment | None = None
        best_value = current
        for category in sorted(assignment, key=lambda c: c.value):
            for alternative in candidates.get(category, ()):
                if alternative == assignment[category]:
                    continue
                trial = {**assignment, category: alternative}
                value = bound_miles(trial, context, horizon_months)
                if value > best_value:  # strict: ties keep the earlier, better-rate pick
                    best_value, best_trial = value, trial
        if best_trial is None:
            return assignment
        assignment = best_trial
    return assignment


def allowed_card_ids(
    opportunities: OpportunitySet,
    wallet_ids: frozenset[UUID],
    constraints: ConstraintSet,
) -> frozenset[UUID]:
    """Wallet + constraint-respecting acquirable cards (BR-03/BR-04: user
    constraints are hard filters, applied before any optimization).
    `max_annual_fees_inr` filters cards individually here; the aggregate
    check across multiple acquisitions happens at strategy validation."""
    allowed = set(wallet_ids)
    if not constraints.no_new_cards:
        for aggregate in opportunities.card_aggregates:
            if aggregate.in_wallet or not aggregate.acquirable:
                continue
            if (
                constraints.max_annual_fees_inr is not None
                and aggregate.annual_fee_inr > constraints.max_annual_fees_inr
            ):
                continue
            allowed.add(aggregate.card_id)
    return frozenset(allowed)


def milestone_fires(
    milestones: tuple[RewardMilestone, ...],
    monthly_spend_inr: int,
    horizon_months: int,
    *,
    acquired: bool,
) -> tuple[MilestoneFire, ...]:
    """Expected milestone triggers for one card given constant monthly routed
    spend. Mirrors the projector's period semantics (see module docstring)."""
    fires: list[MilestoneFire] = []
    for milestone in sorted(milestones, key=lambda m: str(m.id)):
        if milestone.milestone_type == MilestoneType.WELCOME_BONUS:
            if acquired and monthly_spend_inr > 0:
                fires.append(MilestoneFire(milestone, 0))
            continue
        if milestone.milestone_type != MilestoneType.SPEND_BONUS:
            continue  # anniversary/category excluded — same exclusion as the projector
        threshold = milestone.spend_threshold_inr
        if threshold is None or monthly_spend_inr <= 0:
            continue
        months_needed = _ceil_div(threshold, monthly_spend_inr)
        if milestone.period == MilestonePeriod.MONTHLY:
            if months_needed == 1:
                fires.extend(MilestoneFire(milestone, m) for m in range(horizon_months))
        elif milestone.period == MilestonePeriod.QUARTERLY:
            for quarter_start in range(0, horizon_months, 3):
                months_in_quarter = min(3, horizon_months - quarter_start)
                if months_needed <= months_in_quarter:
                    fires.append(MilestoneFire(milestone, quarter_start + months_needed - 1))
        else:  # ANNUAL / ONE_TIME: once within the ≤12-month horizon (documented deviation)
            if months_needed <= horizon_months:
                fires.append(MilestoneFire(milestone, months_needed - 1))
    return tuple(fires)


def _card_monthly(
    assignment: Assignment, context: PlanningContext
) -> tuple[dict[UUID, int], dict[UUID, Decimal]]:
    """Per card: routed monthly INR and exact monthly points (blended rates)."""
    spend_by_category = {
        item.category_slug: item.monthly_spend_inr for item in context.spend_profile.items
    }
    monthly_spend: dict[UUID, int] = {}
    monthly_points: dict[UUID, Decimal] = {}
    for category, opportunity in assignment.items():
        spend = spend_by_category[category]
        card_id = opportunity.card_id
        monthly_spend[card_id] = monthly_spend.get(card_id, 0) + spend
        monthly_points[card_id] = (
            monthly_points.get(card_id, Decimal(0)) + Decimal(spend) * opportunity.earn_rate / 100
        )
    return monthly_spend, monthly_points


def _target_links(context: PlanningContext) -> dict[UUID, CurrencyTransferLink]:
    target = context.requirement.target_program_id
    return {
        link.currency_id: link
        for link in context.snapshot.transfer_links
        if link.partner_id == target
    }


def bound_miles(assignment: Assignment, context: PlanningContext, horizon_months: int) -> int:
    """Optimistic full-horizon best case (formula in the module docstring).
    Counts idle wallet balances too — they are convertible regardless of
    where new spend routes."""
    snapshot = context.snapshot
    links = _target_links(context)
    cards_by_id = {card.id: card for card in snapshot.cards}
    wallet_balance = {w.card_id: w.current_points_balance for w in context.wallet}
    monthly_spend, monthly_points = _card_monthly(assignment, context)

    involved = sorted(set(monthly_spend) | set(wallet_balance), key=str)
    currency_points: dict[UUID, Decimal] = {}
    for card_id in involved:
        card = cards_by_id[card_id]
        link = links.get(card.reward_currency_id)
        if link is None:
            continue  # no path to the target program (e.g. SBI) — worth nothing here
        points = monthly_points.get(card_id, Decimal(0)) * horizon_months
        points += wallet_balance.get(card_id, 0)
        card_milestones = tuple(m for m in snapshot.milestones if m.card_id == card_id)
        for fire in milestone_fires(
            card_milestones,
            monthly_spend.get(card_id, 0),
            horizon_months,
            acquired=card_id not in wallet_balance,
        ):
            points += fire.milestone.bonus_points
        currency_points[card.reward_currency_id] = (
            currency_points.get(card.reward_currency_id, Decimal(0)) + points
        )

    total = Decimal(0)
    for currency_id in sorted(currency_points, key=str):
        link = links[currency_id]
        points = currency_points[currency_id]
        if link.max_transfer_points is not None:
            points = min(points, Decimal(link.max_transfer_points))
        total += points * link.ratio_to / link.ratio_from
    return int(total)  # floor — the single deliberate rounding of the bound


def claimed_estimate(
    assignment: Assignment,
    context: PlanningContext,
    *,
    include_idle_balances: bool = True,
) -> ClaimedEstimate:
    """Cutoff-aware, block-floored claim + the transfer plan that delivers it
    (formulas in the module docstring). `include_idle_balances=False` builds
    the fewest-actions variant for the simplest-viable archetype: wallet
    balances on cards outside the assignment stay untouched."""
    snapshot = context.snapshot
    links = _target_links(context)
    cards_by_id = {card.id: card for card in snapshot.cards}
    wallet_balance = {w.card_id: w.current_points_balance for w in context.wallet}
    monthly_spend, monthly_points = _card_monthly(assignment, context)

    involved = set(monthly_spend)
    if include_idle_balances:
        involved |= {card_id for card_id, balance in wallet_balance.items() if balance > 0}

    by_currency: dict[UUID, list[UUID]] = {}
    for card_id in sorted(involved, key=str):
        currency_id = cards_by_id[card_id].reward_currency_id
        if currency_id in links:
            by_currency.setdefault(currency_id, []).append(card_id)

    total_miles = 0
    plan: list[TransferPlanItem] = []
    expected: list[ExpectedMilestone] = []
    cap_bound: set[UUID] = set()
    for currency_id in sorted(by_currency, key=str):
        link = links[currency_id]
        cutoff = context.horizon_months - 1 - _ceil_div(link.processing_days_max, 30)
        if cutoff < 0:
            continue  # horizon too short for this link's processing window
        cap_remaining = link.max_transfer_points
        for card_id in by_currency[currency_id]:
            spend = monthly_spend.get(card_id, 0)
            fires = milestone_fires(
                tuple(m for m in snapshot.milestones if m.card_id == card_id),
                spend,
                context.horizon_months,
                acquired=card_id not in wallet_balance,
            )
            # Only fires at/before the transfer cutoff feed this plan's total —
            # later ones never reach the batch, so recording them would inflate
            # ranking's milestone-dependency risk numerator against points that
            # were never transferred.
            expected.extend(
                ExpectedMilestone(
                    milestone_id=fire.milestone.id,
                    card_id=card_id,
                    expected_month=fire.month,
                    bonus_points=fire.milestone.bonus_points,
                )
                for fire in fires
                if fire.month <= cutoff
            )
            points = wallet_balance.get(card_id, 0)
            points += int(monthly_points.get(card_id, Decimal(0))) * (cutoff + 1)
            points += sum(f.milestone.bonus_points for f in fires if f.month <= cutoff)
            send = points if cap_remaining is None else min(points, cap_remaining)
            if cap_remaining is not None and points > cap_remaining:
                cap_bound.add(currency_id)  # the cap, not the earn, limited this
            if send <= 0 or send < link.min_transfer_points:
                continue
            points_sent, miles = whole_block_transfer(send, link)
            if points_sent == 0:
                continue
            plan.append(
                TransferPlanItem(
                    from_card_id=card_id,
                    to_partner_id=link.partner_id,
                    points=points_sent,
                    planned_month=cutoff,
                )
            )
            if cap_remaining is not None:
                cap_remaining -= points_sent
            total_miles += miles

    return ClaimedEstimate(
        total_miles=total_miles,
        transfer_plan=tuple(plan),
        expected_milestones=tuple(expected),
        cap_bound_currencies=frozenset(cap_bound),
    )
