"""Golden + bound tests for the annual-fee waiver window (`renewal_window`).

The product collects only a renewal MONTH, never a day. These tests pin the
two claims that makes safe:

  * the window is the 11 whole calendar months strictly between the previous
    and the next occurrence of the renewal month — hand-computed below;
  * that window lies INSIDE the issuer's real window whatever day in the
    renewal month the fee actually falls on, for both window shapes the
    catalog carries (a 12-month card year, and SBI's 365 days). So spend
    counted in it is spend the issuer counts too: the lower bound holds.
"""

from calendar import monthrange
from datetime import date, timedelta

import pytest

from app.simulation.periods import month_label, renewal_window

# ── Hand-computed goldens ────────────────────────────────────────────────


def test_renewal_later_this_year_counts_back_from_it() -> None:
    """Renewal in March, today 2 Nov 2026 → the next renewal is Mar 2027.
    The window is Apr 2026 … Feb 2027: 11 whole months, ending the day
    before March begins."""
    window = renewal_window(3, as_of=date(2026, 11, 2))
    assert window.start == date(2026, 4, 1)
    assert window.end == date(2027, 3, 1)
    assert window.label == "Apr 2026–Feb 2027"


def test_inside_the_renewal_month_the_window_is_the_year_just_closing() -> None:
    """Renewal in November, today 2 Nov 2026. Without the day we cannot tell
    whether the fee posted yesterday or posts on the 28th, so the renewal
    this month is the target and its window — Dec 2025 … Oct 2026 — has fully
    elapsed. It rolls to the next year only once November is over."""
    window = renewal_window(11, as_of=date(2026, 11, 2))
    assert window.start == date(2025, 12, 1)
    assert window.end == date(2026, 11, 1)
    assert window.label == "Dec 2025–Oct 2026"

    last_day = renewal_window(11, as_of=date(2026, 11, 30))
    assert last_day == window


def test_a_renewal_month_already_past_targets_next_year() -> None:
    """Renewal in October, today 2 Nov 2026 → next renewal Oct 2027; the
    window opened yesterday-but-one, on 1 Nov 2026."""
    window = renewal_window(10, as_of=date(2026, 11, 2))
    assert window.start == date(2026, 11, 1)
    assert window.end == date(2027, 10, 1)
    assert window.label == "Nov 2026–Sep 2027"


def test_january_renewal_from_new_years_eve() -> None:
    window = renewal_window(1, as_of=date(2026, 12, 31))
    assert window.start == date(2026, 2, 1)
    assert window.end == date(2027, 1, 1)
    # Start and end month fall in one calendar year, so the year is said once
    # — the same convention as the calendar-quarter labels ("Jul–Sep 2026").
    assert window.label == "Feb–Dec 2026"


def test_december_renewal_from_new_years_day() -> None:
    window = renewal_window(12, as_of=date(2026, 1, 1))
    assert window.start == date(2026, 1, 1)
    assert window.end == date(2026, 12, 1)
    assert window.label == "Jan–Nov 2026"


def test_the_renewal_month_label_is_the_window_end() -> None:
    assert month_label(renewal_window(3, as_of=date(2026, 11, 2)).end) == "Mar 2027"


@pytest.mark.parametrize("month", [0, 13, -1])
def test_a_month_outside_1_to_12_is_refused(month: int) -> None:
    with pytest.raises(ValueError, match="renewal_month"):
        renewal_window(month, as_of=date(2026, 11, 2))


# ── The lower-bound claim, exhaustively ──────────────────────────────────


def _minus_twelve_months(day: date) -> date:
    """The issuer's own card-year start: same day a year earlier, clamped."""
    return date(day.year - 1, day.month, min(day.day, monthrange(day.year - 1, day.month)[1]))


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days)]


def test_the_window_sits_inside_every_real_window_it_could_be() -> None:
    """For every renewal month, every as-of date across five years (two of
    them leap years) and every day the renewal could really fall on, our
    window is a subset of BOTH real windows:

      * the card year      [R − 12 months, R)   — HDFC, HSBC, Axis
      * SBI's 365 days     [R − 365 days, R)

    If this ever fails, counted spend could include a day the issuer does not
    count, and a REACHED could be false.
    """
    for as_of in _days(date(2024, 1, 1), date(2029, 1, 1)):
        for month in range(1, 13):
            window = renewal_window(month, as_of=as_of)
            # Always 11 whole months, starting on a 1st, never in the future
            # relative to today, and ending no more than a month behind today.
            assert window.start.day == 1 and window.end.day == 1
            assert window.end.month == month
            assert window.start <= as_of
            assert as_of < date(
                window.end.year, window.end.month, monthrange(window.end.year, month)[1]
            ) + timedelta(days=1)
            for day in range(1, monthrange(window.end.year, month)[1] + 1):
                renewal = date(window.end.year, month, day)
                assert _minus_twelve_months(renewal) <= window.start
                assert renewal - timedelta(days=365) <= window.start
                assert window.end <= renewal
