"""Golden tests for what a manual activity log proves.

Every expected figure is hand-computed from the real seed catalog (the fixture
loads `seeds/catalog`), so a seed change that moves a cap or a lounge allowance
fails here loudly rather than drifting.

The invariant under test throughout: a manual log is a LOWER BOUND. It can
prove a threshold was reached; it can never prove one was missed.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain import CatalogSnapshot
from app.domain.activity import LoungeVisit, ObservedStatus, SpendEntry
from app.domain.enums import LoungeScope, SpendCategory
from app.simulation.observed import observe

TODAY = date(2026, 8, 20)  # inside Q3 2026; the preceding quarter is Apr-Jun


def card_id(snapshot: CatalogSnapshot, name: str) -> UUID:
    return next(c.id for c in snapshot.cards if c.card_name == name)


def spend(
    card: UUID, amount: int, *, on: date, category: SpendCategory = SpendCategory.TRAVEL
) -> SpendEntry:
    return SpendEntry(
        id=uuid4(), card_id=card, occurred_on=on, amount_inr=amount, category_slug=category
    )


def visit(
    card: UUID, *, on: date, scope: LoungeScope = LoungeScope.DOMESTIC, guests: int = 0
) -> LoungeVisit:
    return LoungeVisit(id=uuid4(), card_id=card, occurred_on=on, scope=scope, guest_count=guests)


# ── Category caps ────────────────────────────────────────────────────────


def test_empty_log_reports_the_cap_untouched(snapshot: CatalogSnapshot) -> None:
    """A user who has logged nothing still gets the structure — the cap and its
    window — because "₹1,12,500 this month, none of it used yet" is the useful
    answer, not an empty page."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(snapshot, card_ids=[infinia], spend=[], visits=[], as_of=TODAY)

    cap = next(c for c in result.caps if c.card_id == infinia)
    assert cap.category_slug is SpendCategory.TRAVEL
    assert cap.cap_inr == 112_500
    assert cap.logged_spend_inr == 0
    assert cap.remaining_inr_at_most == 112_500
    assert cap.fraction_used_at_least == Decimal("0")
    assert cap.window.start == date(2026, 8, 1)  # monthly cap, calendar month
    assert cap.window.end == date(2026, 9, 1)


def test_logged_spend_consumes_the_cap(snapshot: CatalogSnapshot) -> None:
    """Infinia's SmartBuy travel cap is ₹1,12,500/month (15,000 bonus RP at
    5X, seeded 2026-11-06). ₹60,000 logged in August = 60,000 / 112,500 =
    0.5333… used, which rounds DOWN to 0.53 ("at least"); ₹52,500 left at
    most."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[
            spend(infinia, 50_000, on=date(2026, 8, 2)),
            spend(infinia, 10_000, on=date(2026, 8, 19)),
        ],
        visits=[],
        as_of=TODAY,
    )

    cap = next(c for c in result.caps if c.card_id == infinia)
    assert cap.logged_spend_inr == 60_000
    assert cap.remaining_inr_at_most == 52_500
    assert cap.fraction_used_at_least == Decimal("0.53")


def test_spend_outside_the_window_does_not_count(snapshot: CatalogSnapshot) -> None:
    """A monthly cap resets. July spend is irrelevant to August's cap, and the
    boundary day itself belongs to exactly one window."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[
            spend(infinia, 99_000, on=date(2026, 7, 31)),  # previous window
            spend(infinia, 1_000, on=date(2026, 8, 1)),  # first day of this one
        ],
        visits=[],
        as_of=TODAY,
    )
    assert next(c for c in result.caps if c.card_id == infinia).logged_spend_inr == 1_000


def test_spend_in_another_category_does_not_touch_the_cap(snapshot: CatalogSnapshot) -> None:
    """The Infinia cap is on SmartBuy travel; dining spend earns elsewhere."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[spend(infinia, 80_000, on=date(2026, 8, 5), category=SpendCategory.DINING)],
        visits=[],
        as_of=TODAY,
    )
    assert next(c for c in result.caps if c.card_id == infinia).logged_spend_inr == 0


def test_another_card_s_spend_does_not_touch_this_cap(snapshot: CatalogSnapshot) -> None:
    infinia = card_id(snapshot, "Infinia Metal")
    atlas = card_id(snapshot, "Atlas")
    result = observe(
        snapshot,
        card_ids=[infinia, atlas],
        spend=[spend(atlas, 80_000, on=date(2026, 8, 5))],
        visits=[],
        as_of=TODAY,
    )
    assert next(c for c in result.caps if c.card_id == infinia).logged_spend_inr == 0
    assert next(c for c in result.caps if c.card_id == atlas).logged_spend_inr == 80_000


def test_overspending_a_cap_never_reports_negative_headroom(snapshot: CatalogSnapshot) -> None:
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[spend(infinia, 200_000, on=date(2026, 8, 5))],
        visits=[],
        as_of=TODAY,
    )
    cap = next(c for c in result.caps if c.card_id == infinia)
    assert cap.remaining_inr_at_most == 0
    assert cap.fraction_used_at_least > 1  # the overspend stays visible


def test_cap_anchor_is_flagged_as_assumed(snapshot: CatalogSnapshot) -> None:
    """The catalog states a cap's PERIOD but never what it resets against —
    most Indian caps are statement-cycle, not calendar-month. We assume the
    calendar and say so, rather than silently implying we know."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(snapshot, card_ids=[infinia], spend=[], visits=[], as_of=TODAY)
    assert all(cap.anchor_assumed for cap in result.caps)


# ── Milestones ───────────────────────────────────────────────────────────


def test_milestone_progress_is_total_spend_not_category_spend(
    snapshot: CatalogSnapshot,
) -> None:
    """Diners Club Black's ₹4,00,000 quarterly milestone counts every rupee on
    the card, whatever the category."""
    dcb = card_id(snapshot, "Diners Club Black Metal")
    result = observe(
        snapshot,
        card_ids=[dcb],
        spend=[
            spend(dcb, 100_000, on=date(2026, 7, 5), category=SpendCategory.TRAVEL),
            spend(dcb, 50_000, on=date(2026, 8, 1), category=SpendCategory.DINING),
            spend(dcb, 25_000, on=date(2026, 8, 19), category=SpendCategory.FUEL),
        ],
        visits=[],
        as_of=TODAY,
    )
    milestone = next(m for m in result.milestones if m.card_id == dcb)
    assert milestone.threshold_inr == 400_000
    assert milestone.logged_spend_inr == 175_000
    assert milestone.remaining_inr_at_most == 225_000
    assert milestone.status is ObservedStatus.NOT_PROVEN


def test_milestone_exactly_at_threshold_is_reached(snapshot: CatalogSnapshot) -> None:
    dcb = card_id(snapshot, "Diners Club Black Metal")
    result = observe(
        snapshot,
        card_ids=[dcb],
        spend=[spend(dcb, 400_000, on=date(2026, 7, 5))],
        visits=[],
        as_of=TODAY,
    )
    milestone = next(m for m in result.milestones if m.card_id == dcb)
    assert milestone.status is ObservedStatus.REACHED
    assert milestone.remaining_inr_at_most == 0


def test_one_rupee_under_the_threshold_is_not_proven(snapshot: CatalogSnapshot) -> None:
    """The boundary case, and the honesty case: one rupee short is NOT_PROVEN,
    never "not reached" — the user may simply not have logged that rupee."""
    dcb = card_id(snapshot, "Diners Club Black Metal")
    result = observe(
        snapshot,
        card_ids=[dcb],
        spend=[spend(dcb, 399_999, on=date(2026, 7, 5))],
        visits=[],
        as_of=TODAY,
    )
    milestone = next(m for m in result.milestones if m.card_id == dcb)
    assert milestone.status is ObservedStatus.NOT_PROVEN
    assert milestone.remaining_inr_at_most == 1


def test_quarterly_milestone_uses_the_calendar_quarter(snapshot: CatalogSnapshot) -> None:
    dcb = card_id(snapshot, "Diners Club Black Metal")
    result = observe(snapshot, card_ids=[dcb], spend=[], visits=[], as_of=TODAY)
    milestone = next(m for m in result.milestones if m.card_id == dcb)
    assert milestone.window is not None
    assert (milestone.window.start, milestone.window.end) == (date(2026, 7, 1), date(2026, 10, 1))


def test_annual_milestone_tiers_each_get_a_row(snapshot: CatalogSnapshot) -> None:
    """Atlas has three annual spend milestones (₹3L / ₹7.5L / ₹15L). ₹8,00,000
    logged proves the first two and leaves the third open."""
    atlas = card_id(snapshot, "Atlas")
    result = observe(
        snapshot,
        card_ids=[atlas],
        spend=[spend(atlas, 800_000, on=date(2026, 3, 1))],
        visits=[],
        as_of=TODAY,
    )
    tiers = sorted(
        (m for m in result.milestones if m.card_id == atlas), key=lambda m: m.threshold_inr
    )
    assert [m.threshold_inr for m in tiers] == [300_000, 750_000, 1_500_000]
    assert [m.status for m in tiers] == [
        ObservedStatus.REACHED,
        ObservedStatus.REACHED,
        ObservedStatus.NOT_PROVEN,
    ]
    assert tiers[2].remaining_inr_at_most == 700_000


def test_welcome_bonus_is_not_tracked_as_progress(snapshot: CatalogSnapshot) -> None:
    """A welcome bonus has no spend threshold to walk toward, so it is not a
    progress bar — showing one at 0% would be noise, not information.

    Atlas is the case that bites: it carries four milestone rows in the seeds,
    three spend tiers plus a thresholdless welcome bonus, and only the three
    tiers are progress."""
    atlas = card_id(snapshot, "Atlas")
    seeded = [m for m in snapshot.milestones if m.card_id == atlas]
    assert len(seeded) == 4 and any(m.spend_threshold_inr is None for m in seeded)

    rows = observe(snapshot, card_ids=[atlas], spend=[], visits=[], as_of=TODAY).milestones
    assert len(rows) == 3
    assert all(m.threshold_inr > 0 for m in rows)


# ── Lounge allowances ────────────────────────────────────────────────────


def test_lounge_visits_count_against_the_quarterly_allowance(
    snapshot: CatalogSnapshot,
) -> None:
    """Regalia Gold: 3 domestic visits per calendar quarter. Two logged in Q3
    leaves at most one."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[],
        visits=[visit(regalia, on=date(2026, 7, 10)), visit(regalia, on=date(2026, 8, 3))],
        as_of=TODAY,
    )
    domestic = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    )
    assert domestic.allowance == 3
    assert domestic.visits_logged_at_least == 2
    assert domestic.remaining_at_most == 1
    assert domestic.window is not None
    assert domestic.window.label == "Jul–Sep 2026"


def test_visits_from_last_quarter_do_not_count(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[],
        visits=[visit(regalia, on=date(2026, 6, 30)), visit(regalia, on=date(2026, 7, 1))],
        as_of=TODAY,
    )
    domestic = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    )
    assert domestic.visits_logged_at_least == 1


def test_domestic_and_international_are_counted_separately(snapshot: CatalogSnapshot) -> None:
    """They almost never match on an Indian card — Regalia Gold is 3/quarter
    domestic and 6/year international — so one combined number could only be
    wrong."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[],
        visits=[
            visit(regalia, on=date(2026, 7, 10)),
            visit(regalia, on=date(2026, 7, 11), scope=LoungeScope.INTERNATIONAL),
        ],
        as_of=TODAY,
    )
    rows = {row.scope: row for row in result.lounge if row.card_id == regalia}
    assert rows[LoungeScope.DOMESTIC].visits_logged_at_least == 1
    assert rows[LoungeScope.DOMESTIC].remaining_at_most == 2
    assert rows[LoungeScope.INTERNATIONAL].allowance == 6
    assert rows[LoungeScope.INTERNATIONAL].visits_logged_at_least == 1
    assert rows[LoungeScope.INTERNATIONAL].remaining_at_most == 5


def test_unlimited_access_reports_no_remaining_count(snapshot: CatalogSnapshot) -> None:
    """Infinia is unlimited (seeded `reset_anchor: not_applicable`). There is
    no window and no remaining count — reporting "0 left" or a 2026 window
    would both be lies."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[],
        visits=[visit(infinia, on=date(2026, 8, 1))],
        as_of=TODAY,
    )
    domestic = next(
        row for row in result.lounge if row.card_id == infinia and row.scope is LoungeScope.DOMESTIC
    )
    assert domestic.is_unlimited is True
    assert domestic.allowance is None
    assert domestic.remaining_at_most is None
    assert domestic.window is None
    assert domestic.visits_logged_at_least == 1  # still counted, just not limited


def test_zero_allowance_is_not_unlimited(snapshot: CatalogSnapshot) -> None:
    """Platinum Travel grants zero complimentary INTERNATIONAL visits (the
    Priority Pass membership is free; the visits are not). Zero and unlimited
    are opposite answers and must never collapse."""
    amex = card_id(snapshot, "Platinum Travel")
    result = observe(snapshot, card_ids=[amex], spend=[], visits=[], as_of=TODAY)
    international = next(
        row
        for row in result.lounge
        if row.card_id == amex and row.scope is LoungeScope.INTERNATIONAL
    )
    assert international.is_unlimited is False
    assert international.allowance == 0
    assert international.remaining_at_most == 0


def test_guest_visits_consume_the_allowance_only_when_shared(
    snapshot: CatalogSnapshot,
) -> None:
    """Regalia Gold seeds `guest_visits_per_period: 0` and does not share the
    holder's allowance, so a guest brought along is recorded but does not eat
    the cardholder's own three visits."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[],
        visits=[visit(regalia, on=date(2026, 7, 10), guests=2)],
        as_of=TODAY,
    )
    domestic = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    )
    assert domestic.guest_visits_logged == 2
    assert domestic.visits_logged_at_least == 1
    assert domestic.remaining_at_most == 2  # not 0 — guests do not share here


def test_visits_never_report_negative_headroom(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[],
        visits=[visit(regalia, on=date(2026, 7, d)) for d in (1, 2, 3, 4, 5)],
        as_of=TODAY,
    )
    domestic = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    )
    assert domestic.visits_logged_at_least == 5
    assert domestic.remaining_at_most == 0


# ── The spend gate ───────────────────────────────────────────────────────


def test_spend_gate_reads_the_PRECEDING_window(snapshot: CatalogSnapshot) -> None:
    """Regalia Gold's 3 domestic visits are unlocked by ₹60,000 spent in the
    PRECEDING quarter. As of 20 Aug 2026 that window is Apr-Jun, not Jul-Sep —
    the condition most cardholders get wrong."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[spend(regalia, 60_000, on=date(2026, 5, 15))],
        visits=[],
        as_of=TODAY,
    )
    gate = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    ).gate
    assert gate is not None
    assert gate.threshold_inr == 60_000
    assert (gate.window.start, gate.window.end) == (date(2026, 4, 1), date(2026, 7, 1))
    assert gate.logged_spend_inr == 60_000
    assert gate.status is ObservedStatus.REACHED


def test_spend_in_the_current_quarter_does_not_open_this_quarter_s_gate(
    snapshot: CatalogSnapshot,
) -> None:
    """The exact mistake the gate exists to prevent: ₹2,00,000 spent in July
    and August does nothing for July-September's visits."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[spend(regalia, 200_000, on=date(2026, 7, 15))],
        visits=[],
        as_of=TODAY,
    )
    gate = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    ).gate
    assert gate is not None
    assert gate.logged_spend_inr == 0
    assert gate.status is ObservedStatus.NOT_PROVEN


def test_an_unmet_gate_is_never_reported_as_locked(snapshot: CatalogSnapshot) -> None:
    """₹59,999 logged does not prove the gate closed — the user may not have
    logged everything. NOT_PROVEN, and the UI must phrase it as such."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[spend(regalia, 59_999, on=date(2026, 5, 1))],
        visits=[],
        as_of=TODAY,
    )
    gate = next(
        row for row in result.lounge if row.card_id == regalia and row.scope is LoungeScope.DOMESTIC
    ).gate
    assert gate is not None
    assert gate.status is ObservedStatus.NOT_PROVEN


def test_ungated_entitlement_has_no_gate(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(snapshot, card_ids=[regalia], spend=[], visits=[], as_of=TODAY)
    international = next(
        row
        for row in result.lounge
        if row.card_id == regalia and row.scope is LoungeScope.INTERNATIONAL
    )
    assert international.gate is None


# ── Coverage, totals and cards we cannot answer for ──────────────────────


def test_cards_without_lounge_rows_produce_no_lounge_claims(
    snapshot: CatalogSnapshot,
) -> None:
    """Atlas is deliberately unseeded (irreconcilable published data). Absence
    must stay absence — never a row saying zero visits."""
    atlas = card_id(snapshot, "Atlas")
    result = observe(snapshot, card_ids=[atlas], spend=[], visits=[], as_of=TODAY)
    assert not [row for row in result.lounge if row.card_id == atlas]


def test_totals_and_log_reach_are_reported(snapshot: CatalogSnapshot) -> None:
    """`earliest_entry_on` is what makes every other figure honest: nothing
    before it is known, which is why they are bounds."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[
            spend(infinia, 10_000, on=date(2026, 6, 4)),
            spend(infinia, 25_000, on=date(2026, 8, 4)),
        ],
        visits=[visit(infinia, on=date(2026, 8, 5))],
        as_of=TODAY,
    )
    assert result.logged_spend_total_inr == 35_000
    assert result.logged_visit_total == 1
    assert result.earliest_entry_on == date(2026, 6, 4)


def test_earliest_entry_considers_visits_too(snapshot: CatalogSnapshot) -> None:
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[spend(infinia, 10_000, on=date(2026, 8, 4))],
        visits=[visit(infinia, on=date(2026, 2, 1))],
        as_of=TODAY,
    )
    assert result.earliest_entry_on == date(2026, 2, 1)


def test_empty_log_has_no_reach(snapshot: CatalogSnapshot) -> None:
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(snapshot, card_ids=[infinia], spend=[], visits=[], as_of=TODAY)
    assert result.earliest_entry_on is None


def test_entries_for_cards_outside_the_wallet_are_ignored(snapshot: CatalogSnapshot) -> None:
    """The caller decides the wallet; a stale entry for a removed card must not
    silently inflate a total."""
    infinia = card_id(snapshot, "Infinia Metal")
    atlas = card_id(snapshot, "Atlas")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[spend(atlas, 50_000, on=date(2026, 8, 1))],
        visits=[],
        as_of=TODAY,
    )
    assert result.logged_spend_total_inr == 0


def test_unknown_card_id_is_rejected(snapshot: CatalogSnapshot) -> None:
    """A stale wallet fails loudly rather than silently dropping a card —
    the same posture as /v1/best-card and /v1/portfolio."""
    with pytest.raises(ValueError, match=r"[Uu]nknown card"):
        observe(snapshot, card_ids=[uuid4()], spend=[], visits=[], as_of=TODAY)


def test_result_is_deterministic_for_the_same_inputs(snapshot: CatalogSnapshot) -> None:
    """Build rule 8. Entry order must not change the output."""
    dcb = card_id(snapshot, "Diners Club Black Metal")
    entries = [
        spend(dcb, 10_000, on=date(2026, 7, 5)),
        spend(dcb, 20_000, on=date(2026, 8, 5)),
        spend(dcb, 30_000, on=date(2026, 9, 5)),
    ]
    first = observe(snapshot, card_ids=[dcb], spend=entries, visits=[], as_of=TODAY)
    second = observe(
        snapshot, card_ids=[dcb], spend=list(reversed(entries)), visits=[], as_of=TODAY
    )
    assert first == second
