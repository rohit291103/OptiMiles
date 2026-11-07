"""Allowance and cap period windows — what a logged activity counts toward.

Pure calendar arithmetic over the catalog's `AllowancePeriod` × `ResetAnchor`
vocabulary. No DB, no clock: `as_of` is always passed in, so a window is
replayable (build rule 8, determinism).

WHY THIS IS ITS OWN MODULE. Both halves of activity logging need exactly the
same question answered — "which window does this date fall in?" — for three
different consumers: a category cap (₹ per month/quarter), a milestone (₹ per
period), and a lounge allowance (visits per period). The roadmap names a wrong
window as the likeliest defect in the feature and a wrong lounge count as worse
than no count, so the arithmetic lives in one tested place rather than being
re-derived at three call sites.

THE ORIGIN RULE. Every boundary is computed as `origin + k months`, never by
stepping from the previous boundary. Stepping compounds the end-of-month clamp:
31 Jan → 28 Feb → 28 Mar would walk the anchor day permanently earlier. Computing
from the origin keeps 31 Jan / 30 Apr / 31 Jul, which is what an issuer means.
"""

from calendar import monthrange
from datetime import date

from app.domain.activity import PeriodWindow
from app.domain.enums import AllowancePeriod, ResetAnchor

_MONTH_NAMES = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

# How many months one period spans. STATEMENT_CYCLE is a month measured from the
# statement day rather than the 1st; LIFETIME never resets and has no length.
_PERIOD_MONTHS: dict[AllowancePeriod, int] = {
    AllowancePeriod.MONTHLY: 1,
    AllowancePeriod.QUARTERLY: 3,
    AllowancePeriod.HALF_YEARLY: 6,
    AllowancePeriod.ANNUAL: 12,
    AllowancePeriod.STATEMENT_CYCLE: 1,
}

# Anchors measured against the issuer's own calendar rather than the card's.
_CALENDAR_ANCHORS = frozenset({ResetAnchor.CALENDAR_QUARTER, ResetAnchor.CALENDAR_YEAR})
_CARD_ANCHORS = frozenset({ResetAnchor.CARD_ANNIVERSARY, ResetAnchor.STATEMENT_CYCLE})


class AnchorDateRequired(ValueError):
    """Raised when an anchor needs a per-card date the product has not collected.

    Deliberately loud. A card-anniversary or statement-cycle allowance cannot be
    counted without knowing when the card was opened or when it statements, and
    quietly falling back to the calendar year would produce a confidently wrong
    visit count — the exact failure migration 0007 refuses to allow by making
    `reset_anchor` NOT NULL with no default. Callers surface this as "tell us
    your card open date", never as a number.
    """


def _add_months(origin: date, months: int) -> date:
    """`origin` shifted by whole months, clamping the day to the target month.

    31 Jan + 1 month = 28 Feb (29 in a leap year). Always call with an offset
    from the ORIGIN, never from a previously clamped result — see the module
    docstring's origin rule.
    """
    total = origin.month - 1 + months
    year = origin.year + total // 12
    month = total % 12 + 1
    return date(year, month, min(origin.day, monthrange(year, month)[1]))


def _origin_for(anchor: ResetAnchor, as_of: date, anchor_date: date | None) -> date:
    """The date the period grid is aligned to."""
    if anchor in _CARD_ANCHORS:
        if anchor_date is None:
            raise AnchorDateRequired(
                f"reset_anchor={anchor.value} needs the card's own anchor date "
                "(open date / statement day); it must never fall back to the calendar"
            )
        if as_of < anchor_date:
            raise ValueError(f"as_of {as_of} is before the anchor date {anchor_date}")
        return anchor_date
    # Calendar anchors tile from 1 January. A quarterly period anchored on the
    # calendar therefore yields Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec, and an
    # annual one the calendar year, which is what CALENDAR_QUARTER and
    # CALENDAR_YEAR respectively assert about the issuer's reset.
    return date(as_of.year, 1, 1)


def _window_index(origin: date, period_months: int, as_of: date) -> int:
    """How many whole periods separate `as_of` from `origin`."""
    months = (as_of.year - origin.year) * 12 + (as_of.month - origin.month)
    # The month difference over-counts when as_of has not yet reached the
    # anchor day within its month (origin 12 Mar, as_of 5 Sep → 6 months of
    # calendar, but only 5 complete anniversary months).
    if as_of < _add_months(origin, months):
        months -= 1
    return months // period_months


def _label(period: AllowancePeriod, anchor: ResetAnchor, start: date, end: date) -> str:
    """How a cardholder would say the window out loud."""
    if anchor in _CALENDAR_ANCHORS:
        if period is AllowancePeriod.ANNUAL:
            return str(start.year)
        if period is AllowancePeriod.MONTHLY:
            return f"{_MONTH_NAMES[start.month - 1]} {start.year}"
        # Quarterly and half-yearly read as their span of month names; the
        # en dash matches the UI copy elsewhere in the product.
        last_month = _add_months(end, -1)
        return f"{_MONTH_NAMES[start.month - 1]}–{_MONTH_NAMES[last_month.month - 1]} {start.year}"
    # Card-anchored windows have no name of their own, so name their bounds.
    # `end` is exclusive, so the human-readable last day is the day before.
    last_day = date.fromordinal(end.toordinal() - 1)
    return f"{_fmt(start)} – {_fmt(last_day)}"


def _fmt(day: date) -> str:
    return f"{day.day} {_MONTH_NAMES[day.month - 1]} {day.year}"


def current_window(
    period: AllowancePeriod,
    anchor: ResetAnchor,
    *,
    as_of: date,
    anchor_date: date | None = None,
) -> PeriodWindow | None:
    """The window containing `as_of`, or None when nothing ever resets.

    None is returned for `LIFETIME` and for `NOT_APPLICABLE`, which the seeds
    use for unlimited entitlements ("nothing to reset when it is unlimited",
    cards.yaml). The anchor wins over the period there: Infinia's unlimited
    access is seeded `period: annual, reset_anchor: not_applicable`, and
    inventing a 2026 window for it would imply a count that does not exist.

    Raises `AnchorDateRequired` when the anchor is card-relative and no
    `anchor_date` was supplied — never a silent calendar fallback.
    """
    if anchor is ResetAnchor.NOT_APPLICABLE or period is AllowancePeriod.LIFETIME:
        return None

    period_months = _PERIOD_MONTHS[period]
    origin = _origin_for(anchor, as_of, anchor_date)
    index = _window_index(origin, period_months, as_of)
    start = _add_months(origin, index * period_months)
    end = _add_months(origin, (index + 1) * period_months)
    return PeriodWindow(start=start, end=end, label=_label(period, anchor, start, end))


def previous_window(
    period: AllowancePeriod,
    anchor: ResetAnchor,
    *,
    as_of: date,
    anchor_date: date | None = None,
) -> PeriodWindow | None:
    """The window immediately before the one containing `as_of`.

    Its own function because spend gates are stated against the PRECEDING
    period — Regalia Gold's 3 domestic visits this quarter are unlocked by
    ₹60,000 spent *last* quarter — and that off-by-one-period is the condition
    cardholders most often get wrong. Callers should not re-derive it.
    """
    window = current_window(period, anchor, as_of=as_of, anchor_date=anchor_date)
    if window is None:
        return None
    # Step back by one period from the current window's own start: that start
    # is already on the origin grid, so this stays consistent with the origin
    # rule without needing the origin itself.
    day_in_previous = date.fromordinal(window.start.toordinal() - 1)
    return current_window(period, anchor, as_of=day_in_previous, anchor_date=anchor_date)


def month_label(day: date) -> str:
    """'Mar 2027' — how a cardholder names the month `day` falls in."""
    return f"{_MONTH_NAMES[day.month - 1]} {day.year}"


# A renewal window is the whole months strictly between two renewal months.
_RENEWAL_WINDOW_MONTHS = 11


def renewal_window(renewal_month: int, *, as_of: date) -> PeriodWindow:
    """The annual-fee waiver window we can PROVE, from a renewal month alone.

    The product collects the month the annual fee is charged, never the day
    (decision log 2026-11-02-fee-waiver-progress). Issuers measure the waiver
    over the 12 months / card anniversary year ending at the renewal (HDFC,
    HSBC, Axis) or the 365 days before the fee date (SBI). Without the day,
    the edges of that window are uncertain by up to a month, so this returns
    the part that is inside the real window WHATEVER the day is:

        [1st of the month after last year's renewal month,
         1st of this renewal month)

    — the 11 whole months in between. Spend in the renewal month itself is
    not counted, because it may fall either side of the renewal. Counting
    less than the issuer counts keeps the log a lower bound; counting a day
    the issuer does not count could produce a false REACHED. The subset claim
    is proven exhaustively in tests/unit/simulation/test_renewal_window.py.

    WHICH RENEWAL. The next one — or, during the renewal month itself, this
    month's: its window has fully elapsed and answers "did I qualify for the
    fee posting now?". It rolls forward once the renewal month is over.

    Origin rule (module docstring): the start is computed from the renewal
    month's own 1st, never by stepping. Every boundary is a 1st, so no
    end-of-month clamp can arise anyway.
    """
    if not 1 <= renewal_month <= 12:
        raise ValueError(f"renewal_month must be 1-12, got {renewal_month}")
    year = as_of.year if as_of.month <= renewal_month else as_of.year + 1
    renewal = date(year, renewal_month, 1)
    start = _add_months(renewal, -_RENEWAL_WINDOW_MONTHS)
    last_month = _add_months(renewal, -1)
    if start.year == last_month.year:
        label = f"{_MONTH_NAMES[start.month - 1]}–{month_label(last_month)}"
    else:
        label = f"{month_label(start)}–{month_label(last_month)}"
    return PeriodWindow(start=start, end=renewal, label=label)
