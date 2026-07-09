"""Stage 8 — Timeline Simulation: the month-by-month receipt for a strategy.

`simulate(strategy, context)` is a pure function — no DB, no clock, no
randomness; same inputs ⇒ byte-identical `SimulationOutcome` (BR-10). It is
the cap-truth layer: Stage 5's static blend *estimates* a rate, the ledger
here actually meters spend through caps, milestone thresholds and transfer
processing delays. Where the result disagrees with the generator's claim,
the simulation wins.

Simulation model (spec SIM-001 §5–6; all arithmetic exact, rounding
directional and conservative):

- **Months are 0-based**, ledger covers 0 … horizon_months−1 (matches
  `TransferPlanItem.planned_month`, where 0 = this month). The full horizon
  is always simulated — goal achievement is recorded at its first month
  (BR-08), but the ledger continues so Ranking sees complete buffer/fee data
  for near-miss and post-goal months.
- **Within a month:** spend → earn (cap-aware) → milestones → transfers →
  goal progress. Milestone bonuses are therefore transferable in the month
  they land; transferred points leave before next month's earn.

Earning (per card, per month):

    for each profile category routed here:
        rule = (card, category) else (card, default)   # validated present
        exact += min(S, cap)/100 × rule.rate + max(S−cap, 0)/100 × base
    credit = floor(exact)        # ONE floor per card-month, not per category

  Only monthly caps are metered in v1 (the only period the seed catalog
  uses); a rule carrying a quarterly/annual spend cap raises rather than
  silently overstating earnings. `cap_utilization[card] = min(S, cap)/cap`
  (4dp ROUND_DOWN), the max across the card's capped rules that month.

Milestones (catalog truth, never `strategy.expected_milestones`):

- `spend_bonus` qualifies on cumulative INR spend on the card: ANNUAL /
  ONE_TIME periods measure since month 0 and fire at most once in the ≤12-
  month MVP horizon (same single-application deviation as the annual
  transfer cap, decision log 2026-07-04); QUARTERLY measures within each
  plan quarter (months 0–2, 3–5, …) and re-fires each quarter; MONTHLY
  measures within the month. Thresholds are ≥ (exactly-at triggers).
- `welcome_bonus` fires for **acquired cards only**, in the card's first
  month with positive spend — effectively month 0 whenever the card gets any
  allocation, since spend is fixed for the whole horizon (BR-02); the
  spend check is loop-invariant, the `fired_once` gate does the work.
- `anniversary_bonus` / `category_bonus` are excluded from v1 simulation
  (no anniversary dates in context; spec §11 "invalid milestone → exclude").
- Milestone **validity windows (BR-05/BR-06) are NOT evaluated here** — the
  projector has no calendar anchor. `validate_catalog()` rejects any seed
  row carrying `valid_from`/`valid_until` until this engine enforces them,
  so no such milestone can reach a snapshot (Unknown Over Incorrect).

Transfers (plan order within a month; ratio conversion delegated to
valuation.transfer_math.whole_block_transfer — it lives in exactly one
place; only the cumulative annual-cap bookkeeping is simulation state):

    allowed = min(planned, balance, annual link cap remaining)
    skip (no fee, no event) if allowed < min_transfer_points
    points_sent, miles = whole_block_transfer(allowed, link)
        # remainder STAYS on the card — flooring never destroys points
    arrival_month = planned + ceil(processing_days_max / 30)

  Transfers initiate at month end (after that month's earn), so any nonzero
  processing window is conservative: 1–30 days ⇒ next month. The link's
  `max_transfer_points` is a per-calendar-year cap applied once across the
  horizon (exact for ≤12-month horizons). Miles arriving at or beyond the
  horizon are recorded on the execution but never reach
  `cumulative_target_miles` — a transfer landing after the target date is
  precisely the failure this engine exists to catch.

Aggregates: `months_to_goal` = first month with cumulative target-program
miles ≥ `miles_required_total` (buffer excluded; `buffer_achieved` compares
the target-date balance against required + buffer separately);
`total_fees_inr` = joining fees of acquired cards + transfer fees paid
(wallet cards' annual fees are sunk costs of the status quo, not of this
strategy — Ranking's cost dimension prices card fees from the strategy).
"""

from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from app.domain import (
    CandidateStrategy,
    CurrencyTransferLink,
    MilestonePeriod,
    MilestoneType,
    MonthLedgerEntry,
    PlanningContext,
    RewardCategoryRule,
    RewardMilestone,
    SimulationOutcome,
    SpendCategory,
    TransferExecution,
)
from app.valuation.transfer_math import whole_block_transfer

_FOUR_DP = Decimal("0.0001")
_HUNDRED = Decimal(100)


def simulate(strategy: CandidateStrategy, context: PlanningContext) -> SimulationOutcome:
    snapshot = context.snapshot
    all_cards = set(strategy.cards_used) | set(strategy.cards_to_acquire)

    # ── Validate the strategy is complete before projecting it (Stage 7's
    # BR guarantees this; a violation here is a generator bug, fail loudly).
    spend_by_card: dict[UUID, list[tuple[SpendCategory, int]]] = {c: [] for c in all_cards}
    for item in context.spend_profile.items:
        card_id = strategy.spend_allocation.get(item.category_slug)
        if card_id is None:
            raise ValueError(
                f"strategy {strategy.strategy_id!r} allocates no card for profile "
                f"category '{item.category_slug.value}' — partial strategies are invalid"
            )
        if card_id not in all_cards:
            raise ValueError(
                f"strategy {strategy.strategy_id!r} routes '{item.category_slug.value}' "
                f"to card {card_id}, which is not in cards_used/cards_to_acquire"
            )
        spend_by_card[card_id].append((item.category_slug, item.monthly_spend_inr))

    cards_by_id = {c.id: c for c in snapshot.cards}
    rules_by_card: dict[UUID, dict[SpendCategory, RewardCategoryRule]] = {}
    for category_rule in snapshot.category_rules:
        rules_by_card.setdefault(category_rule.card_id, {})[category_rule.category_slug] = (
            category_rule
        )
    links_by_route: dict[tuple[UUID, UUID], CurrencyTransferLink] = {
        (link.currency_id, link.partner_id): link for link in snapshot.transfer_links
    }
    milestones_by_card: dict[UUID, list[RewardMilestone]] = {}
    for milestone in snapshot.milestones:
        if milestone.card_id in all_cards:
            milestones_by_card.setdefault(milestone.card_id, []).append(milestone)
    transfers_by_month: dict[int, list[int]] = {}
    for index, planned in enumerate(strategy.transfer_plan):
        transfers_by_month.setdefault(planned.planned_month, []).append(index)

    # ── Mutable simulation state.
    starting = {w.card_id: w.current_points_balance for w in context.wallet}
    balances: dict[UUID, int] = {c: starting.get(c, 0) for c in all_cards}
    cumulative_spend: dict[UUID, int] = dict.fromkeys(all_cards, 0)
    quarter_spend: dict[UUID, int] = dict.fromkeys(all_cards, 0)
    fired_once: set[UUID] = set()  # annual/one_time spend bonuses + welcome bonuses
    link_points_sent: dict[UUID, int] = {}  # link id → cumulative (annual cap, applied once)
    pending_arrivals: dict[int, int] = {}  # arrival month → target-program miles
    total_fees = sum(cards_by_id[c].joining_fee_inr for c in strategy.cards_to_acquire)
    cumulative_target_miles = 0
    ledger: list[MonthLedgerEntry] = []
    months_to_goal: int | None = None

    for month in range(context.horizon_months):
        if month % 3 == 0:
            quarter_spend = dict.fromkeys(all_cards, 0)

        # 1. Spend → earn (cap-aware; one floor per card-month).
        cap_utilization: dict[UUID, Decimal] = {}
        month_spend_by_card: dict[UUID, int] = dict.fromkeys(all_cards, 0)
        # Earn delta for this month (base + category + milestone bonuses),
        # tracked independently of `balances` so a transfer-out doesn't reduce
        # it — this is the honest monthly accrual the frontend charts.
        month_earned = 0
        for card_id, routed in spend_by_card.items():
            if not routed:
                continue
            card = cards_by_id[card_id]
            card_rules = rules_by_card.get(card_id, {})
            exact = Decimal(0)
            worst_utilization: Decimal | None = None
            month_spend = 0
            for category, spend_inr in routed:
                rule = card_rules.get(category) or card_rules.get(SpendCategory.DEFAULT)
                if rule is None:
                    raise ValueError(
                        f"card {card.card_name!r} has no rule for '{category.value}' and "
                        "no default rule — catalog integrity failure"
                    )
                if rule.quarterly_cap_inr is not None or rule.annual_cap_inr is not None:
                    raise ValueError(
                        f"rule {rule.id} carries a quarterly/annual spend cap; v1 "
                        "projector meters monthly caps only and must not silently "
                        "overstate earnings"
                    )
                cap = rule.monthly_cap_inr
                if cap is None or spend_inr <= cap:
                    exact += Decimal(spend_inr) * rule.earn_rate / _HUNDRED
                else:
                    exact += Decimal(cap) * rule.earn_rate / _HUNDRED
                    exact += Decimal(spend_inr - cap) * card.base_earn_rate / _HUNDRED
                if cap is not None:
                    used = (Decimal(min(spend_inr, cap)) / Decimal(cap)).quantize(
                        _FOUR_DP, rounding=ROUND_DOWN
                    )
                    if worst_utilization is None or used > worst_utilization:
                        worst_utilization = used
                month_spend += spend_inr
            earned = int(exact)  # floor: exact is ≥ 0
            balances[card_id] += earned
            month_earned += earned
            month_spend_by_card[card_id] = month_spend
            cumulative_spend[card_id] += month_spend
            quarter_spend[card_id] += month_spend
            if worst_utilization is not None:
                cap_utilization[card_id] = worst_utilization

        # 2. Milestones (catalog truth; thresholds are ≥, bonuses credit now).
        triggered: list[UUID] = []
        for card_id, milestones in milestones_by_card.items():
            for milestone in milestones:
                if milestone.milestone_type == MilestoneType.WELCOME_BONUS:
                    if (
                        card_id in strategy.cards_to_acquire
                        and milestone.id not in fired_once
                        and any(s > 0 for _, s in spend_by_card[card_id])
                    ):
                        fired_once.add(milestone.id)
                        triggered.append(milestone.id)
                        balances[card_id] += milestone.bonus_points
                        month_earned += milestone.bonus_points
                elif milestone.milestone_type == MilestoneType.SPEND_BONUS:
                    threshold = milestone.spend_threshold_inr
                    if threshold is None:
                        continue  # spec §11: invalid milestone → exclude
                    month_spend = month_spend_by_card[card_id]
                    if milestone.period == MilestonePeriod.QUARTERLY:
                        # Fires once per plan quarter: the month in-quarter
                        # spend first reaches the threshold (spend is fixed
                        # monthly per BR-02, so "first reaches" = "crossed
                        # this month").
                        crossed = (
                            quarter_spend[card_id] >= threshold
                            and quarter_spend[card_id] - month_spend < threshold
                        )
                    elif milestone.period == MilestonePeriod.MONTHLY:
                        crossed = month_spend >= threshold
                    else:  # ANNUAL / ONE_TIME: once, on cumulative plan spend
                        crossed = (
                            milestone.id not in fired_once
                            and cumulative_spend[card_id] >= threshold
                        )
                        if crossed:
                            fired_once.add(milestone.id)
                    if crossed:
                        triggered.append(milestone.id)
                        balances[card_id] += milestone.bonus_points
                        month_earned += milestone.bonus_points
                # anniversary_bonus / category_bonus: excluded in v1 (docstring)

        # 3. Scheduled transfers (plan order; whole blocks; remainder stays).
        executions: list[TransferExecution] = []
        for index in transfers_by_month.get(month, ()):
            planned = strategy.transfer_plan[index]
            card = cards_by_id[planned.from_card_id]
            link = links_by_route.get((card.reward_currency_id, planned.to_partner_id))
            if link is None:
                continue  # spec §11: missing transfer rule → ignore, continue
            allowed = min(planned.points, balances[planned.from_card_id])
            if link.max_transfer_points is not None:
                # The link cap is annual; cumulative bookkeeping across the
                # plan's transfers lives here, not in stateless transfer_math.
                remaining = link.max_transfer_points - link_points_sent.get(link.id, 0)
                allowed = min(allowed, remaining)
            if allowed < link.min_transfer_points or allowed <= 0:
                continue
            points_sent, miles = whole_block_transfer(allowed, link)
            if points_sent == 0:
                continue
            balances[planned.from_card_id] -= points_sent
            link_points_sent[link.id] = link_points_sent.get(link.id, 0) + points_sent
            total_fees += link.transfer_fee_inr
            # Initiated at month end ⇒ any processing days spill forward.
            arrival = month + -(-link.processing_days_max // 30)
            executions.append(
                TransferExecution(
                    from_card_id=planned.from_card_id,
                    to_partner_id=planned.to_partner_id,
                    points_sent=points_sent,
                    miles_received=miles,
                    fee_inr=link.transfer_fee_inr,
                    arrival_month=arrival,
                )
            )
            if planned.to_partner_id == context.requirement.target_program_id:
                pending_arrivals[arrival] = pending_arrivals.get(arrival, 0) + miles

        # 4. Goal progress: credit arrivals due this month.
        cumulative_target_miles += pending_arrivals.pop(month, 0)
        if months_to_goal is None and (
            cumulative_target_miles >= context.requirement.miles_required_total
        ):
            months_to_goal = month

        ledger.append(
            MonthLedgerEntry(
                month=month,
                points_by_card=dict(sorted(balances.items(), key=lambda kv: str(kv[0]))),
                points_earned_this_month=month_earned,
                cap_utilization=cap_utilization,
                milestones_triggered=tuple(triggered),
                transfers_executed=tuple(executions),
                cumulative_target_miles=cumulative_target_miles,
            )
        )

    requirement = context.requirement
    return SimulationOutcome(
        strategy_id=strategy.strategy_id,
        ledger=tuple(ledger),
        months_to_goal=months_to_goal,
        miles_at_target_date=cumulative_target_miles,
        total_fees_inr=total_fees,
        buffer_achieved=(
            cumulative_target_miles >= requirement.miles_required_total + requirement.buffer_miles
        ),
        misses_goal=months_to_goal is None,
    )
