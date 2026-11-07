"""Golden tests for allowance/cap period windows.

These windows decide what a logged spend or lounge visit counts *toward*.
A wrong window is the failure mode the roadmap calls out by name (Phase 1 →
Lounge Access Intelligence): "a wrong count is worse than no count", because
it sends someone to a lounge desk to be turned away.

Every expected boundary here is hand-computed from the calendar, not from the
implementation.
"""

from datetime import date

import pytest

from app.domain.enums import AllowancePeriod, ResetAnchor
from app.simulation.periods import AnchorDateRequired, current_window, previous_window


# ── Calendar quarters ────────────────────────────────────────────────────
# The common Indian case (Regalia Gold: 3 domestic visits per calendar
# quarter). Quarters tile the year Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec.
@pytest.mark.parametrize(
    ("as_of", "expected_start", "expected_end"),
    [
        (date(2026, 1, 1), date(2026, 1, 1), date(2026, 4, 1)),  # first instant of Q1
        (date(2026, 2, 14), date(2026, 1, 1), date(2026, 4, 1)),
        (date(2026, 3, 31), date(2026, 1, 1), date(2026, 4, 1)),  # last day of Q1
        (date(2026, 4, 1), date(2026, 4, 1), date(2026, 7, 1)),  # rolls to Q2
        (date(2026, 9, 30), date(2026, 7, 1), date(2026, 10, 1)),
        (date(2026, 12, 31), date(2026, 10, 1), date(2027, 1, 1)),  # crosses the year
    ],
)
def test_calendar_quarter_windows(as_of: date, expected_start: date, expected_end: date) -> None:
    window = current_window(AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=as_of)
    assert (window.start, window.end) == (expected_start, expected_end)


def test_window_end_is_exclusive() -> None:
    """Half-open [start, end) so consecutive windows tile with no gap and no
    overlap — a visit on 1 April belongs to Q2 alone, never to both."""
    q1 = current_window(
        AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=date(2026, 3, 31)
    )
    q2 = current_window(
        AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=date(2026, 4, 1)
    )
    assert q1.end == q2.start
    assert q1.contains(date(2026, 3, 31))
    assert not q1.contains(date(2026, 4, 1))
    assert q2.contains(date(2026, 4, 1))


# ── Calendar year ────────────────────────────────────────────────────────
def test_calendar_year_window() -> None:
    window = current_window(
        AllowancePeriod.ANNUAL, ResetAnchor.CALENDAR_YEAR, as_of=date(2026, 6, 15)
    )
    assert (window.start, window.end) == (date(2026, 1, 1), date(2027, 1, 1))


def test_calendar_half_year_windows() -> None:
    first = current_window(
        AllowancePeriod.HALF_YEARLY, ResetAnchor.CALENDAR_YEAR, as_of=date(2026, 6, 30)
    )
    second = current_window(
        AllowancePeriod.HALF_YEARLY, ResetAnchor.CALENDAR_YEAR, as_of=date(2026, 7, 1)
    )
    assert (first.start, first.end) == (date(2026, 1, 1), date(2026, 7, 1))
    assert (second.start, second.end) == (date(2026, 7, 1), date(2027, 1, 1))


def test_calendar_month_window() -> None:
    window = current_window(
        AllowancePeriod.MONTHLY, ResetAnchor.CALENDAR_YEAR, as_of=date(2026, 2, 28)
    )
    assert (window.start, window.end) == (date(2026, 2, 1), date(2026, 3, 1))


# ── Card anniversary ─────────────────────────────────────────────────────
def test_anniversary_annual_window() -> None:
    """A card opened 12 Mar 2024, as of 1 Sep 2026, is in its third year."""
    window = current_window(
        AllowancePeriod.ANNUAL,
        ResetAnchor.CARD_ANNIVERSARY,
        as_of=date(2026, 9, 1),
        anchor_date=date(2024, 3, 12),
    )
    assert (window.start, window.end) == (date(2026, 3, 12), date(2027, 3, 12))


def test_anniversary_window_on_the_anniversary_itself_rolls_forward() -> None:
    window = current_window(
        AllowancePeriod.ANNUAL,
        ResetAnchor.CARD_ANNIVERSARY,
        as_of=date(2026, 3, 12),
        anchor_date=date(2024, 3, 12),
    )
    assert window.start == date(2026, 3, 12)


def test_anniversary_quarterly_windows_tile_from_the_origin_not_each_other() -> None:
    """Boundaries are always computed from the origin, never by stepping from
    the previous boundary — otherwise a short month permanently drags the
    anchor day earlier (31 Jan -> 28 Feb -> 28 Mar, which is wrong)."""
    opened = date(2024, 1, 31)
    q = current_window(
        AllowancePeriod.QUARTERLY,
        ResetAnchor.CARD_ANNIVERSARY,
        as_of=date(2026, 5, 1),
        anchor_date=opened,
    )
    # 31 Jan + 27 months = 30 Apr 2026 (April has 30 days, so the day clamps);
    # + 30 months = 31 Jul 2026. The clamp must not leak into the next boundary.
    assert (q.start, q.end) == (date(2026, 4, 30), date(2026, 7, 31))


def test_anniversary_anchor_without_a_date_is_an_explicit_error() -> None:
    """We do not collect a card-open date yet, so this must fail loudly rather
    than silently defaulting to the calendar year — a silent default is exactly
    the wrong-count failure the seeds refuse to accept (migration 0007)."""
    with pytest.raises(AnchorDateRequired):
        current_window(AllowancePeriod.ANNUAL, ResetAnchor.CARD_ANNIVERSARY, as_of=date(2026, 9, 1))


def test_statement_cycle_needs_an_anchor_date_too() -> None:
    with pytest.raises(AnchorDateRequired):
        current_window(
            AllowancePeriod.STATEMENT_CYCLE, ResetAnchor.STATEMENT_CYCLE, as_of=date(2026, 9, 1)
        )


def test_statement_cycle_window() -> None:
    """Statement day 15: on 20 Aug the open cycle runs 15 Aug - 15 Sep."""
    window = current_window(
        AllowancePeriod.STATEMENT_CYCLE,
        ResetAnchor.STATEMENT_CYCLE,
        as_of=date(2026, 8, 20),
        anchor_date=date(2024, 6, 15),
    )
    assert (window.start, window.end) == (date(2026, 8, 15), date(2026, 9, 15))


def test_as_of_before_the_anchor_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="before"):
        current_window(
            AllowancePeriod.ANNUAL,
            ResetAnchor.CARD_ANNIVERSARY,
            as_of=date(2023, 1, 1),
            anchor_date=date(2024, 3, 12),
        )


# ── Unbounded ────────────────────────────────────────────────────────────
def test_lifetime_period_has_no_window() -> None:
    """Nothing resets, so there is no window to count within — None, not a
    fabricated 100-year range."""
    assert (
        current_window(AllowancePeriod.LIFETIME, ResetAnchor.NOT_APPLICABLE, as_of=date(2026, 9, 1))
        is None
    )


def test_not_applicable_anchor_has_no_window() -> None:
    """Infinia's unlimited access is seeded period=annual, anchor=not_applicable
    ("nothing to reset when it is unlimited"). The anchor wins."""
    assert (
        current_window(AllowancePeriod.ANNUAL, ResetAnchor.NOT_APPLICABLE, as_of=date(2026, 9, 1))
        is None
    )


# ── Previous window (the spend gate reads it) ────────────────────────────
def test_previous_calendar_quarter() -> None:
    """Regalia Gold's 3 domestic visits are unlocked by spend in the PRECEDING
    quarter — the condition most cardholders get wrong, so it gets its own
    function rather than arithmetic at the call site."""
    window = previous_window(
        AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=date(2026, 8, 20)
    )
    assert window is not None
    assert (window.start, window.end) == (date(2026, 4, 1), date(2026, 7, 1))


def test_previous_window_crossing_a_year_boundary() -> None:
    window = previous_window(
        AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=date(2026, 1, 5)
    )
    assert window is not None
    assert (window.start, window.end) == (date(2025, 10, 1), date(2026, 1, 1))


def test_previous_window_is_none_when_nothing_resets() -> None:
    assert (
        previous_window(
            AllowancePeriod.LIFETIME, ResetAnchor.NOT_APPLICABLE, as_of=date(2026, 9, 1)
        )
        is None
    )


# ── Labels ───────────────────────────────────────────────────────────────
def test_quarter_label_reads_as_a_person_would_say_it() -> None:
    window = current_window(
        AllowancePeriod.QUARTERLY, ResetAnchor.CALENDAR_QUARTER, as_of=date(2026, 8, 20)
    )
    assert window is not None
    assert window.label == "Jul–Sep 2026"


def test_annual_calendar_label() -> None:
    window = current_window(
        AllowancePeriod.ANNUAL, ResetAnchor.CALENDAR_YEAR, as_of=date(2026, 8, 20)
    )
    assert window is not None
    assert window.label == "2026"


def test_anniversary_label_names_its_own_start() -> None:
    window = current_window(
        AllowancePeriod.ANNUAL,
        ResetAnchor.CARD_ANNIVERSARY,
        as_of=date(2026, 9, 1),
        anchor_date=date(2024, 3, 12),
    )
    assert window is not None
    assert window.label == "12 Mar 2026 – 11 Mar 2027"
