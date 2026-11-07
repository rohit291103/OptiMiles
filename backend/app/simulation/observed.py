"""What a manual activity log proves about caps, milestones and lounge visits.

A pure function of (catalog snapshot, logged entries, wallet, date). No DB, no
clock, no LLM — the repository fetches the rows, this decides what they mean,
and the API renders it. Same shape as `valuation/portfolio.py`.

WHY EVERY FIGURE IS A BOUND. Users forget to log; they do not invent entries.
So logged spend is a LOWER bound on real spend and logged visits a LOWER bound
on real visits. Two consequences run through the whole module:

  * a threshold can be proven REACHED, never proven missed — hence
    `ObservedStatus.NOT_PROVEN` and no NOT_REACHED anywhere;
  * remaining headroom is an UPPER bound — "at most 1 lounge visit left".

The roadmap accepts this failure mode explicitly ("an unlogged visit makes the
displayed count wrong in the user's favour") and requires the mitigation this
module implements: always carry the entitlement alongside the count, and treat
logged visits as "at least this many used".

WHAT THE CATALOG DOES NOT TELL US. Category caps and milestones carry a period
but no reset anchor — most Indian caps actually run on the statement cycle. We
assume the calendar and flag it (`anchor_assumed`) rather than implying we
know. Lounge rows DO carry `reset_anchor` (migration 0007 makes it NOT NULL
with no default), so they are counted against the issuer's real reset; where
that anchor needs a per-card date we do not collect, the entitlement is
reported as `UncountableAllowance` instead of being guessed.

ANNUAL-FEE WAIVERS follow the same rule from the other direction: the window
is the 12 months ending at the card's renewal, which we know only if the user
told us their renewal MONTH. Without it the waiver's terms are stated and no
progress is computed — never a calendar-year fallback. With it, the counted
window is the part of the issuer's window that is certain whatever the day
(`periods.renewal_window`), so the count is still a lower bound.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.activity import (
    CapUse,
    FeeWaiverCount,
    FeeWaiverCoverage,
    FeeWaiverProgress,
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
    CatalogSnapshot,
    FeeWaiver,
    LoungeAccess,
    RewardCategoryRule,
    RewardMilestone,
)
from app.domain.enums import (
    AllowancePeriod,
    FeeWaiverKind,
    FeeWaiverWindow,
    MilestonePeriod,
    ResetAnchor,
    ThresholdComparison,
)
from app.simulation.periods import (
    AnchorDateRequired,
    current_window,
    month_label,
    previous_window,
    renewal_window,
)

# A milestone period is a different enum from an allowance period by design
# (see `domain/enums.py`): one bounds an accrual and needs ONE_TIME, the other
# bounds a count of visits and needs STATEMENT_CYCLE. Mapping across is
# therefore explicit rather than a cast.
_MILESTONE_TO_ALLOWANCE: dict[MilestonePeriod, AllowancePeriod] = {
    MilestonePeriod.MONTHLY: AllowancePeriod.MONTHLY,
    MilestonePeriod.QUARTERLY: AllowancePeriod.QUARTERLY,
    MilestonePeriod.ANNUAL: AllowancePeriod.ANNUAL,
    MilestonePeriod.ONE_TIME: AllowancePeriod.LIFETIME,
}

# Which anchor a calendar-assumed period is measured against. Quarterly caps
# read as calendar quarters, everything else as the calendar year's grid.
_ASSUMED_ANCHOR: dict[AllowancePeriod, ResetAnchor] = {
    AllowancePeriod.MONTHLY: ResetAnchor.CALENDAR_YEAR,
    AllowancePeriod.QUARTERLY: ResetAnchor.CALENDAR_QUARTER,
    AllowancePeriod.HALF_YEARLY: ResetAnchor.CALENDAR_YEAR,
    AllowancePeriod.ANNUAL: ResetAnchor.CALENDAR_YEAR,
    AllowancePeriod.LIFETIME: ResetAnchor.NOT_APPLICABLE,
}


def _status(observed: int, threshold: int) -> ObservedStatus:
    """REACHED only when the log alone proves it. Never NOT_REACHED."""
    return ObservedStatus.REACHED if observed >= threshold else ObservedStatus.NOT_PROVEN


def _sum_spend(entries: Iterable[SpendEntry], window: PeriodWindow | None) -> int:
    """Total logged spend inside `window`; the whole log when nothing resets."""
    return sum(e.amount_inr for e in entries if window is None or window.contains(e.occurred_on))


def _declared_caps(rule: RewardCategoryRule) -> list[tuple[AllowancePeriod, int]]:
    """Every cap the rule actually declares, in ascending period length.

    A rule may carry more than one (a monthly cap AND an annual one); each gets
    its own row rather than the code picking a "primary" and hiding the other.
    """
    declared = [
        (AllowancePeriod.MONTHLY, rule.monthly_cap_inr),
        (AllowancePeriod.QUARTERLY, rule.quarterly_cap_inr),
        (AllowancePeriod.ANNUAL, rule.annual_cap_inr),
    ]
    return [(period, cap) for period, cap in declared if cap is not None and cap > 0]


def _cap_rows(rule: RewardCategoryRule, entries: Sequence[SpendEntry], as_of: date) -> list[CapUse]:
    rows: list[CapUse] = []
    for period, cap_inr in _declared_caps(rule):
        window = current_window(period, _ASSUMED_ANCHOR[period], as_of=as_of)
        if window is None:  # unreachable for the periods above; guards a future one
            continue
        in_category = [e for e in entries if e.category_slug is rule.category_slug]
        spent = _sum_spend(in_category, window)
        rows.append(
            CapUse(
                card_id=rule.card_id,
                category_slug=rule.category_slug,
                category_label=rule.category_label,
                period=period,
                window=window,
                cap_inr=cap_inr,
                logged_spend_inr=spent,
                # Headroom floors at zero: an overspend means the cap is gone,
                # not that the user owes it back. The overspend stays visible
                # in `fraction_used_at_least`.
                remaining_inr_at_most=max(0, cap_inr - spent),
                fraction_used_at_least=(Decimal(spent) / Decimal(cap_inr)).quantize(
                    Decimal("0.01")
                ),
                anchor_assumed=True,
            )
        )
    return rows


def _milestone_row(
    milestone: RewardMilestone, entries: Sequence[SpendEntry], as_of: date
) -> MilestoneProgress | None:
    """One spend milestone's progress, or None when there is nothing to walk toward.

    A welcome or anniversary bonus with no spend threshold is not progress —
    rendering it as a bar stuck at 0% would be noise, not information.
    """
    if milestone.spend_threshold_inr is None or milestone.spend_threshold_inr <= 0:
        return None

    period = _MILESTONE_TO_ALLOWANCE[milestone.period]
    window = current_window(period, _ASSUMED_ANCHOR[period], as_of=as_of)
    # Milestones count TOTAL spend on the card, every category — unlike a cap,
    # which is confined to its own category.
    spent = _sum_spend(entries, window)
    return MilestoneProgress(
        card_id=milestone.card_id,
        milestone_id=milestone.id,
        description=milestone.description,
        bonus_points=milestone.bonus_points,
        threshold_inr=milestone.spend_threshold_inr,
        window=window,
        logged_spend_inr=spent,
        remaining_inr_at_most=max(0, milestone.spend_threshold_inr - spent),
        status=_status(spent, milestone.spend_threshold_inr),
        anchor_assumed=True,
    )


def _gate_state(
    access: LoungeAccess, entries: Sequence[SpendEntry], as_of: date
) -> SpendGateState | None:
    """Whether the tier's spend condition is provably unlocked.

    Measured over the PRECEDING window, which is what the issuer means and what
    cardholders most often get wrong: ₹2,00,000 spent this quarter does nothing
    for this quarter's visits.
    """
    if access.spend_gate_inr is None or access.spend_gate_period is None:
        return None
    window = previous_window(access.spend_gate_period, access.reset_anchor, as_of=as_of)
    if window is None:
        return None
    spent = _sum_spend(entries, window)
    return SpendGateState(
        threshold_inr=access.spend_gate_inr,
        window=window,
        logged_spend_inr=spent,
        status=_status(spent, access.spend_gate_inr),
    )


def _lounge_row(
    access: LoungeAccess,
    program_name: str,
    visits: Sequence[LoungeVisit],
    entries: Sequence[SpendEntry],
    as_of: date,
) -> LoungeAllowanceUse:
    window = current_window(access.period, access.reset_anchor, as_of=as_of)
    # Visits are logged against (card, scope), never against a tier: a
    # cardholder has no reason to know which tier admitted them. Where a card
    # holds several tiers for one scope the same visits therefore appear on
    # each — the tiers are alternatives, not additive allowances.
    in_scope = [v for v in visits if v.scope is access.scope]
    counted = [v for v in in_scope if window is None or window.contains(v.occurred_on)]
    visit_count = len(counted)
    guest_count = sum(v.guest_count for v in counted)

    consumed = visit_count + (guest_count if access.guests_share_allowance else 0)
    remaining = (
        None if access.visits_per_period is None else max(0, access.visits_per_period - consumed)
    )

    return LoungeAllowanceUse(
        card_id=access.card_id,
        program_id=access.program_id,
        program_name=program_name,
        scope=access.scope,
        # Explicit, so no caller has to interpret a null: null means unlimited
        # and 0 means none granted — opposite answers.
        is_unlimited=access.visits_per_period is None,
        allowance=access.visits_per_period,
        period=access.period,
        window=window,
        visits_logged_at_least=visit_count,
        guest_visits_logged=guest_count,
        remaining_at_most=remaining,
        guests_share_allowance=access.guests_share_allowance,
        enrollment_required=access.enrollment_required,
        enrollment_url=access.enrollment_url,
        gate=_gate_state(access, entries, as_of),
        conditions=access.conditions,
    )


_NEEDS_RENEWAL_MONTH = (
    "Tell us your renewal month (the month your annual fee is charged) to track "
    "this. The waiver is measured over the year before your renewal, so we will "
    "not guess the window."
)
_NO_WAIVER = "The issuer does not offer a spend-based annual-fee waiver on this card."
_NOT_COVERED = "We have not checked this card's annual-fee waiver yet."


def _fee_waiver_count(
    waiver: FeeWaiver, entries: Sequence[SpendEntry], renewal_month: int, as_of: date
) -> FeeWaiverCount:
    """Progress toward one spend-based waiver over the counted window.

    Eligible spend = logged spend on the card inside the window, minus the
    categories the issuer names as not counting. A lower bound, so:

        needed    = threshold          (AT_LEAST: "Spend Rs. 4,00,000")
                  = threshold + 1      (MORE_THAN: "exceeds ₹800,000", in whole
                                        rupees the least qualifying spend)
        remaining = max(0, needed − eligible)   — an UPPER bound
        status    = REACHED iff remaining == 0, else NOT_PROVEN
    """
    if waiver.threshold_inr is None or waiver.threshold_comparison is None:
        # validate_catalog FW-03 rejects this; refuse rather than count 0.
        raise ValueError(f"spend-based fee waiver {waiver.id} has no threshold terms")
    window = renewal_window(renewal_month, as_of=as_of)
    excluded = set(waiver.excluded_categories)
    eligible = _sum_spend((e for e in entries if e.category_slug not in excluded), window)
    needed = waiver.threshold_inr + (
        1 if waiver.threshold_comparison is ThresholdComparison.MORE_THAN else 0
    )
    remaining = max(0, needed - eligible)
    status = ObservedStatus.REACHED if remaining == 0 else ObservedStatus.NOT_PROVEN
    # HSBC-style: spend IN a card year reverses the fee charged at its START,
    # one year before the renewal that ends the window.
    decided = (
        _add_years(window.end, -1)
        if waiver.window_kind is FeeWaiverWindow.CURRENT_CARD_YEAR
        else window.end
    )
    return FeeWaiverCount(
        renewal_label=month_label(window.end),
        decides_fee_label=month_label(decided),
        window=window,
        logged_spend_inr=eligible,
        remaining_inr_at_most=remaining,
        status=status,
        subject_to_exclusions=waiver.has_unmodelled_exclusions,
        note=_exclusion_note(waiver, status),
    )


def _add_years(first_of_month: date, years: int) -> date:
    # Only ever called on a window boundary, which is always a 1st — no clamp.
    return first_of_month.replace(year=first_of_month.year + years)


def _exclusion_note(waiver: FeeWaiver, status: ObservedStatus) -> str | None:
    """The caveat for exclusions the log cannot separate.

    The log is a lower bound on what the user SPENT, not on what the issuer
    COUNTS: logged rent on a card whose issuer excludes rent inflates the
    count. So REACHED is stated as "reached on your log, subject to …", and a
    NOT_PROVEN warns that the real gap may be larger than "at most".
    """
    if not waiver.has_unmodelled_exclusions:
        return None
    listed = ", ".join(waiver.unmodelled_exclusions)
    if status is ObservedStatus.REACHED:
        return f"Reached on your log — subject to the issuer's exclusions listed: {listed}."
    return (
        f"This counts everything you logged. The issuer excludes {listed} — if any "
        "of your logged spend is one of those, you need more than shown."
    )


def _fee_waiver_row(
    card_id: UUID,
    waiver: FeeWaiver | None,
    entries: Sequence[SpendEntry],
    renewal_month: int | None,
    unverified_ids: frozenset[UUID] | None,
    as_of: date,
) -> FeeWaiverProgress:
    if waiver is None:
        return FeeWaiverProgress(
            card_id=card_id,
            coverage=FeeWaiverCoverage.NOT_COVERED,
            renewal_month=renewal_month,
            reason=_NOT_COVERED,
        )
    flagged = None if unverified_ids is None else waiver.id in unverified_ids
    if waiver.kind is FeeWaiverKind.NONE:
        return FeeWaiverProgress(
            card_id=card_id,
            coverage=FeeWaiverCoverage.NO_WAIVER,
            waiver=waiver,
            needs_verification=flagged,
            renewal_month=renewal_month,
            reason=_NO_WAIVER,
        )
    if renewal_month is None:
        return FeeWaiverProgress(
            card_id=card_id,
            coverage=FeeWaiverCoverage.NEEDS_RENEWAL_MONTH,
            waiver=waiver,
            needs_verification=flagged,
            reason=_NEEDS_RENEWAL_MONTH,
        )
    return FeeWaiverProgress(
        card_id=card_id,
        coverage=FeeWaiverCoverage.TRACKED,
        waiver=waiver,
        needs_verification=flagged,
        renewal_month=renewal_month,
        count=_fee_waiver_count(waiver, entries, renewal_month, as_of),
    )


def observe(
    snapshot: CatalogSnapshot,
    *,
    card_ids: Sequence[UUID],
    spend: Sequence[SpendEntry],
    visits: Sequence[LoungeVisit],
    as_of: date,
    renewal_months: Mapping[UUID, int] | None = None,
    unverified_ids: frozenset[UUID] | None = None,
) -> ObservedActivity:
    """What the log proves for one wallet, on one date.

    Raises `ValueError` for a card id absent from the snapshot — a stale wallet
    fails loudly rather than silently dropping a card, matching /v1/best-card
    and /v1/portfolio. Entries for cards outside `card_ids` are ignored (the
    caller owns the wallet), which is a different case: those rows are real,
    they are just not part of this question.

    `renewal_months` maps a card to the month (1-12) its annual fee is
    charged; a card absent from it gets NEEDS_RENEWAL_MONTH, never a guessed
    window. `unverified_ids` is the Listed-tier index; None means "not
    assessed" and is carried as `needs_verification=None`, never as verified.
    Raises `ValueError` for a renewal month outside 1-12.
    """
    known = {card.id: card for card in snapshot.cards}
    wallet: list[UUID] = []
    for card_id in card_ids:
        if card_id not in known:
            raise ValueError(f"Unknown card {card_id}")
        if card_id not in wallet:  # a duplicated id must not double-count
            wallet.append(card_id)

    in_wallet = set(wallet)
    spend_by_card: dict[UUID, list[SpendEntry]] = defaultdict(list)
    for entry in spend:
        if entry.card_id in in_wallet:
            spend_by_card[entry.card_id].append(entry)
    visits_by_card: dict[UUID, list[LoungeVisit]] = defaultdict(list)
    for logged in visits:
        if logged.card_id in in_wallet:
            visits_by_card[logged.card_id].append(logged)

    program_names = {program.id: program.program_name for program in snapshot.lounge_programs}
    waiver_by_card = {waiver.card_id: waiver for waiver in snapshot.fee_waivers}
    months = renewal_months or {}
    for card_id, month in months.items():
        if card_id in in_wallet and not 1 <= month <= 12:
            raise ValueError(f"renewal_month must be 1-12, got {month} for card {card_id}")

    caps: list[CapUse] = []
    milestones: list[MilestoneProgress] = []
    lounge: list[LoungeAllowanceUse] = []
    uncountable: list[UncountableAllowance] = []
    fee_waivers: list[FeeWaiverProgress] = []

    # Iterate the wallet in the caller's order, and the catalog in snapshot
    # order within it, so the output is deterministic regardless of the order
    # entries arrive in (build rule 8).
    for card_id in wallet:
        entries = spend_by_card[card_id]
        for rule in snapshot.category_rules:
            if rule.card_id == card_id:
                caps.extend(_cap_rows(rule, entries, as_of))
        for milestone in snapshot.milestones:
            if milestone.card_id == card_id:
                row = _milestone_row(milestone, entries, as_of)
                if row is not None:
                    milestones.append(row)
        for access in snapshot.lounge_access:
            if access.card_id != card_id:
                continue
            try:
                lounge.append(
                    _lounge_row(
                        access,
                        program_names.get(access.program_id, "Lounge programme"),
                        visits_by_card[card_id],
                        entries,
                        as_of,
                    )
                )
            except AnchorDateRequired:
                # We decline to count rather than guess. "We need to know when
                # you opened this card" is an acceptable answer; a wrong visit
                # count that sends someone to a desk to be turned away is not.
                uncountable.append(
                    UncountableAllowance(
                        card_id=card_id,
                        scope=access.scope,
                        reason=(
                            "This allowance resets on your own card cycle, so counting it "
                            "needs the date you opened the card — which we do not have yet."
                        ),
                    )
                )

        fee_waivers.append(
            _fee_waiver_row(
                card_id,
                waiver_by_card.get(card_id),
                entries,
                months.get(card_id),
                unverified_ids,
                as_of,
            )
        )

    counted_spend = [e for e in spend if e.card_id in in_wallet]
    counted_visits = [v for v in visits if v.card_id in in_wallet]
    dates = [e.occurred_on for e in counted_spend] + [v.occurred_on for v in counted_visits]

    return ObservedActivity(
        as_of=as_of,
        card_ids=tuple(wallet),
        caps=tuple(caps),
        milestones=tuple(milestones),
        lounge=tuple(lounge),
        uncountable=tuple(uncountable),
        fee_waivers=tuple(fee_waivers),
        logged_spend_total_inr=sum(e.amount_inr for e in counted_spend),
        logged_visit_total=len(counted_visits),
        earliest_entry_on=min(dates) if dates else None,
    )
