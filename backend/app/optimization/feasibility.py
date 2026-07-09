"""Stage 6 — the feasibility gate (`assess_feasibility`).

An impossible goal answered with a strategy list is a lie; answered with
"not as stated — but yes with one of these changes" it is the most
trust-building screen in the product. The gate therefore does two things,
both fully deterministic:

1. **Bound check.** `best_case_miles` = the optimistic upper bound from
   `allocation.bound_miles` over the constraint-respecting card set (wallet
   + acquirable non-wallet cards, unless `no_new_cards`; cards above
   `max_annual_fees_inr` are excluded individually). Feasible ⇔
   best_case ≥ `miles_required_total` (buffer EXCLUDED — a goal that clears
   the requirement but not the buffer is feasible-but-`tight`, and narration
   must present it as tight, not certain).

2. **Inverse problems.** For infeasible goals, each adjustment option is a
   COMPUTED single change that makes the bound clear the requirement — never
   an invented suggestion, and only emitted when it actually works (a
   saturated transfer cap can make "extend the timeline" genuinely useless,
   so no such option appears):

   - extend_timeline: smallest horizon in (H, 36] whose bound clears.
   - add_card: best single acquirable addition — emitted only when
     `no_new_cards` excluded acquisitions from the base bound (otherwise
     they are already counted). Never proposes a non-acquirable card.
   - raise_spend: smallest ₹10,000/month increment (≤ ₹5L) on the
     best-rate profile category; rates are honestly RE-PRICED at the higher
     spend via Stage 5's own `enumerate_opportunities` (pure re-valuation —
     the sanctioned Optimization → Valuation call), so cap blending is
     respected rather than linearly extrapolated.
   - downgrade_cabin: highest cabin below the goal's whose locked-chart
     requirement the CURRENT bound already clears (the bound is unchanged;
     the target drops). Uses the same award-chart row shape Stage 3 locked.

Also emits the `PortfolioAssessment`: `current_capability_miles` is the same
bound restricted to the wallet alone (regardless of constraints), and
`convertible_balances_by_program` converts existing balances at actual
ratios into every linked program (floored per program).
"""

from decimal import Decimal
from uuid import UUID

from app.domain import (
    AdjustmentOption,
    CabinClass,
    FeasibilityVerdict,
    OpportunitySet,
    PlanningContext,
    PortfolioAssessment,
    SpendCategory,
    SpendProfile,
)
from app.optimization.allocation import (
    allowed_card_ids,
    bound_miles,
    candidate_opportunities,
    greedy_assignment,
)
from app.valuation.opportunities import enumerate_opportunities

_MAX_EXTENDED_HORIZON_MONTHS = 36
_RAISE_STEP_INR = 10_000
_MAX_RAISE_STEPS = 50  # ≤ ₹5,00,000/month extra — beyond that the answer is "no"

_CABIN_ORDER = (
    CabinClass.FIRST,
    CabinClass.BUSINESS,
    CabinClass.PREMIUM_ECONOMY,
    CabinClass.ECONOMY,
)


def assess_feasibility(
    opportunities: OpportunitySet, context: PlanningContext
) -> FeasibilityVerdict:
    required = context.requirement.miles_required_total
    buffer = context.requirement.buffer_miles
    wallet_ids = frozenset(w.card_id for w in context.wallet)

    allowed = allowed_card_ids(opportunities, wallet_ids, context.constraints)
    best_case = _bound(opportunities, context, context.horizon_months, allowed)
    feasible = best_case >= required

    portfolio = _portfolio_assessment(opportunities, context, wallet_ids)
    options: tuple[AdjustmentOption, ...] = ()
    if not feasible:
        options = _adjustment_options(
            opportunities, context, allowed, wallet_ids, required, best_case
        )

    return FeasibilityVerdict(
        feasible=feasible,
        best_case_miles=best_case,
        gap_miles=required - best_case,
        tight=feasible and best_case < required + buffer,
        adjustment_options=options,
        portfolio=portfolio,
    )


def _bound(
    opportunities: OpportunitySet,
    context: PlanningContext,
    horizon_months: int,
    allowed: frozenset[UUID],
) -> int:
    assignment = greedy_assignment(opportunities, context, allowed, horizon_months)
    return bound_miles(assignment, context, horizon_months)


def _portfolio_assessment(
    opportunities: OpportunitySet, context: PlanningContext, wallet_ids: frozenset[UUID]
) -> PortfolioAssessment:
    capability = _bound(opportunities, context, context.horizon_months, wallet_ids)
    convertible = _convertible_balances(context)
    program = context.requirement.target_program_name

    strengths: list[str] = []
    linked_currencies = {
        link.currency_id
        for link in context.snapshot.transfer_links
        if link.partner_id == context.requirement.target_program_id
    }
    cards_by_id = {card.id: card for card in context.snapshot.cards}
    reaching = sum(
        1 for card_id in wallet_ids if cards_by_id[card_id].reward_currency_id in linked_currencies
    )
    if reaching:
        strengths.append(
            f"{reaching} of your {len(wallet_ids)} card(s) can already transfer into {program}"
        )
    if convertible.get(program, 0) > 0:
        strengths.append(
            f"existing balances are already worth {convertible[program]:,} {program} miles"
        )

    return PortfolioAssessment(
        current_capability_miles=capability,
        convertible_balances_by_program=convertible,
        reward_gap_miles=context.requirement.miles_required_total - capability,
        strengths=tuple(strengths),
    )


def _convertible_balances(context: PlanningContext) -> dict[str, int]:
    """Existing wallet balances converted at actual ratios, per program.
    Exact Decimal accumulation, floored once per program."""
    cards_by_id = {card.id: card for card in context.snapshot.cards}
    programs_by_id = {partner.id: partner.program_name for partner in context.snapshot.partners}
    totals: dict[str, Decimal] = {}
    for wallet_card in context.wallet:
        if wallet_card.current_points_balance <= 0:
            continue
        currency_id = cards_by_id[wallet_card.card_id].reward_currency_id
        for link in context.snapshot.transfer_links:
            if link.currency_id != currency_id:
                continue
            program = programs_by_id[link.partner_id]
            miles = Decimal(wallet_card.current_points_balance) * link.ratio_to / link.ratio_from
            totals[program] = totals.get(program, Decimal(0)) + miles
    return {program: int(miles) for program, miles in sorted(totals.items())}


def _adjustment_options(
    opportunities: OpportunitySet,
    context: PlanningContext,
    allowed: frozenset[UUID],
    wallet_ids: frozenset[UUID],
    required: int,
    best_case: int,
) -> tuple[AdjustmentOption, ...]:
    options: list[AdjustmentOption] = []

    extend = _extend_timeline_option(opportunities, context, allowed, required)
    if extend is not None:
        options.append(extend)

    if context.constraints.no_new_cards:
        add = _add_card_option(opportunities, context, wallet_ids, required)
        if add is not None:
            options.append(add)

    raise_option = _raise_spend_option(context, allowed, required)
    if raise_option is not None:
        options.append(raise_option)

    downgrade = _downgrade_cabin_option(context, best_case)
    if downgrade is not None:
        options.append(downgrade)

    return tuple(options)


def _extend_timeline_option(
    opportunities: OpportunitySet,
    context: PlanningContext,
    allowed: frozenset[UUID],
    required: int,
) -> AdjustmentOption | None:
    for horizon in range(context.horizon_months + 1, _MAX_EXTENDED_HORIZON_MONTHS + 1):
        resulting = _bound(opportunities, context, horizon, allowed)
        if resulting >= required:
            return AdjustmentOption(
                kind="extend_timeline",
                description=(
                    f"extend the timeline from {context.horizon_months} to {horizon} months"
                ),
                extend_to_months=horizon,
                resulting_best_case_miles=resulting,
            )
    return None


def _add_card_option(
    opportunities: OpportunitySet,
    context: PlanningContext,
    wallet_ids: frozenset[UUID],
    required: int,
) -> AdjustmentOption | None:
    """Best single acquirable addition (only meaningful when no_new_cards
    excluded acquisitions from the base bound). The fee constraint still
    applies — this option relaxes exactly one thing."""
    max_fee = context.constraints.max_annual_fees_inr
    best: tuple[int, str, UUID] | None = None
    for aggregate in opportunities.card_aggregates:
        if aggregate.in_wallet or not aggregate.acquirable:
            continue
        if max_fee is not None and aggregate.annual_fee_inr > max_fee:
            continue
        resulting = _bound(
            opportunities,
            context,
            context.horizon_months,
            wallet_ids | {aggregate.card_id},
        )
        key = (resulting, str(aggregate.card_id))
        if resulting >= required and (best is None or key > (best[0], best[1])):
            best = (resulting, str(aggregate.card_id), aggregate.card_id)
    if best is None:
        return None
    resulting, _, card_id = best
    card = next(c for c in context.snapshot.cards if c.id == card_id)
    return AdjustmentOption(
        kind="add_card",
        description=f"add {card.card_name} ({card.bank})",
        add_card_id=card_id,
        resulting_best_case_miles=resulting,
    )


def _raise_spend_option(
    context: PlanningContext, allowed: frozenset[UUID], required: int
) -> AdjustmentOption | None:
    """Smallest ₹10k/month increment on the best-rate category that clears the
    requirement, honestly re-priced per step via Stage 5 (pure re-valuation)."""
    category = _best_rate_category(context, allowed)
    if category is None:
        return None
    for step in range(1, _MAX_RAISE_STEPS + 1):
        extra = step * _RAISE_STEP_INR
        raised_context = _with_raised_spend(context, category, extra)
        raised_opportunities = enumerate_opportunities(raised_context)
        resulting = _bound(raised_opportunities, raised_context, context.horizon_months, allowed)
        if resulting >= required:
            return AdjustmentOption(
                kind="raise_spend",
                description=f"raise monthly {category.value} spend by ₹{extra:,}",
                raise_category_slug=category.value,
                raise_spend_by_inr=extra,
                resulting_best_case_miles=resulting,
            )
    return None


def _best_rate_category(context: PlanningContext, allowed: frozenset[UUID]) -> SpendCategory | None:
    """The profile category whose best allowed opportunity converts spend
    fastest — computed from a fresh enumeration to stay consistent with the
    re-priced steps. Ties keep profile order."""
    candidates = candidate_opportunities(enumerate_opportunities(context), allowed)
    best: tuple[Decimal, SpendCategory] | None = None
    for item in context.spend_profile.items:
        options = candidates.get(item.category_slug)
        if not options:
            continue
        rate = options[0].effective_miles_per_100inr
        if best is None or rate > best[0]:
            best = (rate, item.category_slug)
    return best[1] if best else None


def _with_raised_spend(
    context: PlanningContext, category: SpendCategory, extra_inr: int
) -> PlanningContext:
    items = tuple(
        item.model_copy(update={"monthly_spend_inr": item.monthly_spend_inr + extra_inr})
        if item.category_slug == category
        else item
        for item in context.spend_profile.items
    )
    return context.model_copy(
        update={"spend_profile": SpendProfile(items=items, assumed=context.spend_profile.assumed)}
    )


def _downgrade_cabin_option(context: PlanningContext, best_case: int) -> AdjustmentOption | None:
    """The bound stays put; the requirement drops. Highest cabin below the
    goal's with a locked-chart row the current bound clears."""
    goal = context.goal
    lower_cabins = _CABIN_ORDER[_CABIN_ORDER.index(goal.cabin_class) + 1 :]
    for cabin in lower_cabins:
        entry = next(
            (
                e
                for e in context.snapshot.award_charts
                if e.partner_id == goal.partner_id
                and e.origin_region == goal.origin_region
                and e.destination_region == goal.destination_region
                and e.cabin_class == cabin
                and e.award_type == goal.award_type
            ),
            None,
        )
        if entry is None:
            continue
        new_required = entry.miles_required * goal.num_passengers
        if best_case >= new_required:
            return AdjustmentOption(
                kind="downgrade_cabin",
                description=f"switch from {goal.cabin_class.value} to {cabin.value}",
                downgrade_cabin_to=cabin.value,
                resulting_best_case_miles=best_case,
            )
    return None
