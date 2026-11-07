"""Golden tests for annual-fee waiver progress in `observe()`.

Every figure is hand-computed from the real seed catalog (the fixture loads
`seeds/catalog`) and the month-only window rule (`renewal_window`: the 11 whole
months between renewal months). The honesty model is the one the rest of the
activity log uses — logged spend is a LOWER bound, so a waiver can be proven
REACHED and never proven missed, and what remains is "at most".

TODAY is 2 Nov 2026 throughout.
"""

from datetime import date
from uuid import UUID, uuid4

import pytest

from app.domain import CatalogSnapshot, FeeWaiverKind
from app.domain.activity import FeeWaiverCoverage, ObservedStatus, SpendEntry
from app.domain.enums import SpendCategory
from app.knowledge.seed_catalog import seed_id
from app.simulation.observed import observe

TODAY = date(2026, 11, 2)


def card_id(snapshot: CatalogSnapshot, name: str) -> UUID:
    return next(c.id for c in snapshot.cards if c.card_name == name)


def spend(
    card: UUID, amount: int, *, on: date, category: SpendCategory = SpendCategory.DEFAULT
) -> SpendEntry:
    return SpendEntry(
        id=uuid4(), card_id=card, occurred_on=on, amount_inr=amount, category_slug=category
    )


def only_row(result, card: UUID):  # type: ignore[no-untyped-def]
    rows = [r for r in result.fee_waivers if r.card_id == card]
    assert len(rows) == 1
    return rows[0]


# ── Tracked progress ─────────────────────────────────────────────────────


def test_regalia_counts_only_the_whole_months_before_a_march_renewal(
    snapshot: CatalogSnapshot,
) -> None:
    """Regalia Gold: ₹4,00,000 in the year before renewal. Renewal month March
    → next renewal Mar 2027 → counted window 1 Apr 2026 – 28 Feb 2027.

      ₹1,50,000 on 10 May 2026   counted
      ₹1,00,000 on  1 Oct 2026   counted
      ₹   20,000 on  2 Nov 2026  counted (today)
      ₹   30,000 on 31 Mar 2026  NOT counted — renewal month, could be either side
      logged = 2,70,000; remaining at most 4,00,000 − 2,70,000 = 1,30,000
    """
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[
            spend(regalia, 150_000, on=date(2026, 5, 10), category=SpendCategory.DINING),
            spend(regalia, 100_000, on=date(2026, 10, 1)),
            spend(regalia, 20_000, on=date(2026, 11, 2)),
            spend(regalia, 30_000, on=date(2026, 3, 31)),
        ],
        visits=[],
        as_of=TODAY,
        renewal_months={regalia: 3},
    )

    row = only_row(result, regalia)
    assert row.coverage is FeeWaiverCoverage.TRACKED
    assert row.renewal_month == 3
    assert row.waiver is not None and row.waiver.threshold_inr == 400_000
    count = row.count
    assert count is not None
    assert count.window.start == date(2026, 4, 1)
    assert count.window.end == date(2027, 3, 1)
    assert count.window.label == "Apr 2026–Feb 2027"
    assert count.renewal_label == "Mar 2027"
    assert count.logged_spend_inr == 270_000
    assert count.remaining_inr_at_most == 130_000
    assert count.status is ObservedStatus.NOT_PROVEN


@pytest.mark.parametrize(
    ("logged", "status", "remaining"),
    [
        (400_000, ObservedStatus.REACHED, 0),  # "Spend Rs. 4,00,000" — met at the figure
        (399_999, ObservedStatus.NOT_PROVEN, 1),
        (400_001, ObservedStatus.REACHED, 0),
    ],
)
def test_an_at_least_threshold_is_met_exactly_at_the_figure(
    snapshot: CatalogSnapshot, logged: int, status: ObservedStatus, remaining: int
) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[spend(regalia, logged, on=date(2026, 6, 15))],
        visits=[],
        as_of=TODAY,
        renewal_months={regalia: 3},
    )
    count = only_row(result, regalia).count
    assert count is not None
    assert count.status is status
    assert count.remaining_inr_at_most == remaining


@pytest.mark.parametrize(
    ("logged", "status", "remaining"),
    [
        # "exceeds ₹800,000": ₹8,00,000 exactly does NOT qualify. In whole
        # rupees the least qualifying spend is ₹8,00,001, so ₹1 is still due.
        (800_000, ObservedStatus.NOT_PROVEN, 1),
        (800_001, ObservedStatus.REACHED, 0),
        (799_000, ObservedStatus.NOT_PROVEN, 1_001),
    ],
)
def test_hsbc_must_exceed_its_threshold(
    snapshot: CatalogSnapshot, logged: int, status: ObservedStatus, remaining: int
) -> None:
    travelone = card_id(snapshot, "TravelOne")
    result = observe(
        snapshot,
        card_ids=[travelone],
        spend=[spend(travelone, logged, on=date(2026, 6, 15))],
        visits=[],
        as_of=TODAY,
        renewal_months={travelone: 3},
    )
    count = only_row(result, travelone).count
    assert count is not None
    assert count.status is status
    assert count.remaining_inr_at_most == remaining


def test_magnus_burgundy_does_not_count_the_categories_axis_excludes(
    snapshot: CatalogSnapshot,
) -> None:
    """Renewal month November, today 2 Nov → this month's renewal is the
    target; its window Dec 2025 – Oct 2026 has fully elapsed.

      ₹25,00,000 travel     1 Jun 2026   counted
      ₹ 4,00,000 utilities  1 Jul 2026   excluded by Axis
      ₹ 2,00,000 fuel       1 Aug 2026   excluded by Axis
      ₹ 1,00,000 other      1 Nov 2026   renewal month — not counted
      Logged total is ₹32L, over the ₹30L threshold — but eligible is ₹25L,
      so NOT_PROVEN with at most ₹5,00,000 to go. Counting the total would
      have printed a false "waived".
    """
    magnus = card_id(snapshot, "Magnus for Burgundy")
    result = observe(
        snapshot,
        card_ids=[magnus],
        spend=[
            spend(magnus, 2_500_000, on=date(2026, 6, 1), category=SpendCategory.TRAVEL),
            spend(magnus, 400_000, on=date(2026, 7, 1), category=SpendCategory.UTILITIES),
            spend(magnus, 200_000, on=date(2026, 8, 1), category=SpendCategory.FUEL),
            spend(magnus, 100_000, on=date(2026, 11, 1)),
        ],
        visits=[],
        as_of=TODAY,
        renewal_months={magnus: 11},
    )
    count = only_row(result, magnus).count
    assert count is not None
    assert count.window.start == date(2025, 12, 1)
    assert count.window.end == date(2026, 11, 1)
    assert count.renewal_label == "Nov 2026"
    assert count.logged_spend_inr == 2_500_000
    assert count.remaining_inr_at_most == 500_000
    assert count.status is ObservedStatus.NOT_PROVEN


# ── Exclusions we cannot log (fix round) ─────────────────────────────────


def test_a_reached_subject_to_unmodelled_exclusions_says_so(snapshot: CatalogSnapshot) -> None:
    """Magnus Burgundy: ₹30,00,000 travel logged in Dec 2025 – Oct 2026 meets
    the ₹30L threshold (remaining 0 → REACHED). But Axis also excludes rent,
    wallet loads, … which a user may have logged as travel/other — so the
    wire says "reached on your log, subject to …", never bare proof."""
    magnus = card_id(snapshot, "Magnus for Burgundy")
    result = observe(
        snapshot,
        card_ids=[magnus],
        spend=[spend(magnus, 3_000_000, on=date(2026, 6, 1), category=SpendCategory.TRAVEL)],
        visits=[],
        as_of=TODAY,
        renewal_months={magnus: 11},
    )
    count = only_row(result, magnus).count
    assert count is not None
    assert count.status is ObservedStatus.REACHED
    assert count.remaining_inr_at_most == 0
    assert count.subject_to_exclusions is True
    assert count.note == (
        "Reached on your log — subject to the issuer's exclusions listed: rent, "
        "wallet loads, government payments, EMI conversions, cash withdrawals, "
        "insurance, gold, reversals, fees and charges."
    )


def test_not_proven_with_unmodelled_exclusions_warns_the_gap_may_be_larger(
    snapshot: CatalogSnapshot,
) -> None:
    """Logged spend the issuer excludes understates what is still needed, so
    "at most" also holds only for spend the issuer counts — say so."""
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot,
        card_ids=[regalia],
        spend=[spend(regalia, 100_000, on=date(2026, 6, 1))],
        visits=[],
        as_of=TODAY,
        renewal_months={regalia: 3},
    )
    count = only_row(result, regalia).count
    assert count is not None
    assert count.status is ObservedStatus.NOT_PROVEN
    assert count.subject_to_exclusions is True
    assert count.note == (
        "This counts everything you logged. The issuer excludes Cash on Call, "
        "balance transfers, cash withdrawals — if any of your logged spend is one "
        "of those, you need more than shown."
    )


# ── Which fee a window decides (fix round, item 3) ───────────────────────


def test_most_windows_decide_the_fee_at_their_end(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    result = observe(
        snapshot, card_ids=[regalia], spend=[], visits=[], as_of=TODAY, renewal_months={regalia: 3}
    )
    count = only_row(result, regalia).count
    assert count is not None
    assert count.renewal_label == "Mar 2027"
    assert count.decides_fee_label == "Mar 2027"  # the Mar 2027 renewal fee is waived


def test_hsbc_in_its_renewal_month_settles_the_year_just_closed(
    snapshot: CatalogSnapshot,
) -> None:
    """HSBC reverses the fee charged at the START of a card year when spend IN
    that year exceeds ₹8L. Renewal month November, today 2 Nov 2026:

      * the card year Nov 2025 → Nov 2026 has just closed; its reversal (of
        the fee charged in Nov 2025) is what is being settled now — counted
        window Dec 2025 – Oct 2026;
      * the fee charged this month is decided by spend in the year now
        beginning, which has nothing in it yet; it becomes the target once
        November is over (window Dec 2026 – Oct 2027, deciding the Nov 2026 fee).

    Judged correct as is: during the renewal month the closed year is the
    live question. The label names the fee explicitly so the copy cannot
    claim it is about this month's charge.
    """
    travelone = card_id(snapshot, "TravelOne")
    now = observe(
        snapshot,
        card_ids=[travelone],
        spend=[spend(travelone, 900_000, on=date(2026, 3, 1))],
        visits=[],
        as_of=TODAY,
        renewal_months={travelone: 11},
    )
    count = only_row(now, travelone).count
    assert count is not None
    assert count.window.label == "Dec 2025–Oct 2026"
    assert count.renewal_label == "Nov 2026"
    assert count.decides_fee_label == "Nov 2025"
    assert count.logged_spend_inr == 900_000
    assert count.status is ObservedStatus.REACHED  # 9L > 8L

    later = observe(
        snapshot,
        card_ids=[travelone],
        spend=[spend(travelone, 900_000, on=date(2026, 3, 1))],
        visits=[],
        as_of=date(2026, 12, 1),
        renewal_months={travelone: 11},
    )
    next_count = only_row(later, travelone).count
    assert next_count is not None
    assert next_count.window.label == "Dec 2026–Oct 2027"
    assert next_count.decides_fee_label == "Nov 2026"
    assert next_count.logged_spend_inr == 0
    # 8,00,000 + 1 − 0 (strict threshold, whole rupees).
    assert next_count.remaining_inr_at_most == 800_001


def test_sbi_window_starts_on_the_first_whole_month(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback: ₹2,00,000 or more in the 365 days before the fee date.
    Renewal month January → next renewal Jan 2027 → counted 1 Feb – 31 Dec
    2026. ₹2,00,000 on 1 Feb counts and proves it; ₹50,000 on 31 Jan does not
    count (January may fall either side of last year's fee date)."""
    sbi = card_id(snapshot, "Cashback")
    result = observe(
        snapshot,
        card_ids=[sbi],
        spend=[
            spend(sbi, 200_000, on=date(2026, 2, 1), category=SpendCategory.ONLINE),
            spend(sbi, 50_000, on=date(2026, 1, 31)),
        ],
        visits=[],
        as_of=TODAY,
        renewal_months={sbi: 1},
    )
    count = only_row(result, sbi).count
    assert count is not None
    assert count.window.label == "Feb–Dec 2026"
    assert count.logged_spend_inr == 200_000
    assert count.status is ObservedStatus.REACHED
    assert count.remaining_inr_at_most == 0


def test_spend_on_another_card_never_counts(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[regalia, infinia],
        spend=[spend(infinia, 900_000, on=date(2026, 6, 1))],
        visits=[],
        as_of=TODAY,
        renewal_months={regalia: 3, infinia: 3},
    )
    regalia_count = only_row(result, regalia).count
    infinia_count = only_row(result, infinia).count
    assert regalia_count is not None and regalia_count.logged_spend_inr == 0
    assert infinia_count is not None and infinia_count.logged_spend_inr == 900_000
    # Infinia needs ₹10,00,000: ₹9,00,000 logged leaves at most ₹1,00,000.
    assert infinia_count.remaining_inr_at_most == 100_000


# ── The three ways a card is NOT tracked ─────────────────────────────────


def test_without_a_renewal_month_the_waiver_is_stated_but_not_counted(
    snapshot: CatalogSnapshot,
) -> None:
    """We never assume a window. The terms are still shown — "₹10L in the
    year before renewal" is useful on its own — but no progress number."""
    infinia = card_id(snapshot, "Infinia Metal")
    result = observe(
        snapshot,
        card_ids=[infinia],
        spend=[spend(infinia, 1_200_000, on=date(2026, 6, 1))],
        visits=[],
        as_of=TODAY,
    )
    row = only_row(result, infinia)
    assert row.coverage is FeeWaiverCoverage.NEEDS_RENEWAL_MONTH
    assert row.count is None
    assert row.renewal_month is None
    assert row.waiver is not None and row.waiver.threshold_inr == 1_000_000
    assert row.reason is not None and "renewal month" in row.reason


def test_a_card_with_no_waiver_says_so_even_with_a_renewal_month(
    snapshot: CatalogSnapshot,
) -> None:
    atlas = card_id(snapshot, "Atlas")
    result = observe(
        snapshot,
        card_ids=[atlas],
        spend=[spend(atlas, 1_000_000, on=date(2026, 6, 1))],
        visits=[],
        as_of=TODAY,
        renewal_months={atlas: 5},
    )
    row = only_row(result, atlas)
    assert row.coverage is FeeWaiverCoverage.NO_WAIVER
    assert row.waiver is not None and row.waiver.kind is FeeWaiverKind.NONE
    assert row.count is None
    assert row.renewal_month == 5


def test_an_unresearched_card_is_not_covered_rather_than_waiverless(
    snapshot: CatalogSnapshot,
) -> None:
    travel = card_id(snapshot, "Platinum Travel")
    result = observe(
        snapshot, card_ids=[travel], spend=[], visits=[], as_of=TODAY, renewal_months={travel: 4}
    )
    row = only_row(result, travel)
    assert row.coverage is FeeWaiverCoverage.NOT_COVERED
    assert row.waiver is None
    assert row.count is None
    assert row.needs_verification is None


# ── Shape, order, provenance ─────────────────────────────────────────────


def test_one_row_per_wallet_card_in_wallet_order(snapshot: CatalogSnapshot) -> None:
    names = ["Cashback", "Atlas", "Infinia Metal", "Platinum Travel"]
    ids = [card_id(snapshot, n) for n in names]
    result = observe(
        snapshot,
        card_ids=[*ids, ids[0]],  # a duplicated id must not produce two rows
        spend=[],
        visits=[],
        as_of=TODAY,
        # A renewal month for a card outside the wallet is ignored.
        renewal_months={ids[0]: 1, card_id(snapshot, "Regalia Gold"): 3},
    )
    assert [r.card_id for r in result.fee_waivers] == ids
    assert [r.coverage for r in result.fee_waivers] == [
        FeeWaiverCoverage.TRACKED,
        FeeWaiverCoverage.NO_WAIVER,
        FeeWaiverCoverage.NEEDS_RENEWAL_MONTH,
        FeeWaiverCoverage.NOT_COVERED,
    ]


def test_the_listed_tier_flag_is_carried_and_unassessed_is_not_false(
    snapshot: CatalogSnapshot,
) -> None:
    """Same convention as PartnerReach: None means "not assessed", never
    "verified"."""
    regalia = card_id(snapshot, "Regalia Gold")
    waiver_id = seed_id("fee_waiver", "hdfc-regalia-gold")

    def flag(unverified: frozenset[UUID] | None) -> bool | None:
        kwargs = {} if unverified is None else {"unverified_ids": unverified}
        result = observe(snapshot, card_ids=[regalia], spend=[], visits=[], as_of=TODAY, **kwargs)
        return only_row(result, regalia).needs_verification

    assert flag(None) is None
    assert flag(frozenset()) is False
    assert flag(frozenset({waiver_id})) is True


def test_an_impossible_renewal_month_is_refused(snapshot: CatalogSnapshot) -> None:
    regalia = card_id(snapshot, "Regalia Gold")
    with pytest.raises(ValueError, match="renewal_month"):
        observe(
            snapshot,
            card_ids=[regalia],
            spend=[],
            visits=[],
            as_of=TODAY,
            renewal_months={regalia: 13},
        )
