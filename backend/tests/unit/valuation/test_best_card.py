"""Best Card for this Spend — ranking a wallet for a single purchase.

Every expected value below is hand-computed from the seed catalog
(`seeds/catalog/cards.yaml`, `transfer_links.yaml`) and traceable to a
seeded rate + ratio. A wrong constant here tells a user to swipe the wrong
card, which is the most visible way this product can be wrong.

THE CENTRAL INVARIANT under test: ranking is by MILES toward the target
program, never by raw points. Points across currencies are not commensurable
(HDFC RP, EDGE Miles and MR are different units), and the catalog carries no
₹-per-point valuation to make them so. `test_more_points_can_mean_fewer_miles`
is the case that proves the distinction is real and not pedantry.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain import CatalogSnapshot, OverCapEarn, SpendCategory
from app.valuation.best_card import UnknownCard, rank_cards_for_spend


def _card_id(snapshot: CatalogSnapshot, card_name: str):
    return next(c.id for c in snapshot.cards if c.card_name == card_name)


def _krisflyer_id(snapshot: CatalogSnapshot):
    return next(p.id for p in snapshot.partners if p.program_name == "KrisFlyer")


def _rank(snapshot: CatalogSnapshot, names: list[str], amount: int, category: SpendCategory):
    return rank_cards_for_spend(
        snapshot,
        amount_inr=amount,
        category=category,
        card_ids=[_card_id(snapshot, n) for n in names],
        target_program_id=_krisflyer_id(snapshot),
    )


# ── golden per-card values: ₹10,000 of uncategorized spend ────────────────
# points = floor(amount/100 × rate); miles = floor(points × ratio_to / ratio_from)


@pytest.mark.parametrize(
    ("card_name", "expected_points", "expected_miles"),
    [
        # Infinia 3.33 pts/₹100 → 333 pts; hdfc-rp-premium 1:1 → 333 miles
        ("Infinia Metal", 333, 333),
        # Regalia Gold 2.50 (5 RP/₹200 since 15 May 2026) → floor(10,000/100 × 2.50)
        # = 250 pts; hdfc-rp-regalia 2:1 → floor(250/2) = 125
        ("Regalia Gold", 250, 125),
        # TravelOne 2.00 → 200 pts; hsbc-reward-points 1:1 → 200
        ("TravelOne", 200, 200),
        # Atlas 2.00 → 200 pts; axis-edge-miles 1:2 → 400
        ("Atlas", 200, 400),
        # Magnus Burgundy 6.00 → 600 pts; axis-edge-rewards 5:4 → floor(600×4/5) = 480
        ("Magnus for Burgundy", 600, 480),
    ],
)
def test_golden_points_and_miles_for_default_category(
    snapshot: CatalogSnapshot, card_name: str, expected_points: int, expected_miles: int
) -> None:
    result = _rank(snapshot, [card_name], 10_000, SpendCategory.DEFAULT)
    (option,) = result.ranked
    assert option.points_earned == expected_points
    assert option.miles_earned == expected_miles


def test_more_points_can_mean_fewer_miles(snapshot: CatalogSnapshot) -> None:
    """Regalia Gold out-earns TravelOne on POINTS (250 vs 200) and loses on
    MILES (125 vs 200), because Regalia's tier transfers 2:1 while HSBC is
    1:1. Ranking by points would recommend the worse card."""
    result = _rank(snapshot, ["Regalia Gold", "TravelOne"], 10_000, SpendCategory.DEFAULT)
    winner, runner_up = result.ranked

    assert winner.card_name == "TravelOne"
    assert runner_up.card_name == "Regalia Gold"
    assert runner_up.points_earned > winner.points_earned  # points say the opposite
    assert winner.miles_earned > runner_up.miles_earned  # miles decide it


def test_full_wallet_ranks_by_miles_descending(snapshot: CatalogSnapshot) -> None:
    result = _rank(
        snapshot,
        ["Infinia Metal", "Regalia Gold", "TravelOne", "Atlas", "Magnus for Burgundy"],
        10_000,
        SpendCategory.DEFAULT,
    )
    assert [o.card_name for o in result.ranked] == [
        "Magnus for Burgundy",  # 480
        "Atlas",  # 400
        "Infinia Metal",  # 333
        "TravelOne",  # 200
        "Regalia Gold",  # 125 = floor(250 / 2), 250 = 10,000/100 × 2.50
    ]
    assert [o.miles_earned for o in result.ranked] == [480, 400, 333, 200, 125]


# ── accelerated categories and caps ───────────────────────────────────────


def test_accelerated_category_beats_base_rate(snapshot: CatalogSnapshot) -> None:
    """Infinia travel is 16.65 via SmartBuy: ₹10,000 → floor(100 × 16.65) = 1,665."""
    result = _rank(snapshot, ["Infinia Metal"], 10_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == 1_665
    assert option.miles_earned == 1_665
    assert option.is_accelerated is True
    assert option.monthly_cap_inr == 112_500


def test_zero_earn_category_earns_nothing_not_the_base_rate(snapshot: CatalogSnapshot) -> None:
    """HSBC's service guide: "No reward points will be earned for spends in
    the below categories: Utilities(4900) … Fuel(…)". Before the zero-earn
    rows (2026-11-06) ₹5,000 of fuel fell to TravelOne's default row and
    earned floor(50 × 2.00) = 100 points it never earns. Now: 0 — and a
    0.00 rate is not "accelerated"."""
    result = _rank(snapshot, ["TravelOne"], 5_000, SpendCategory.FUEL)
    (option,) = result.ranked
    assert option.points_earned == 0
    assert option.miles_earned == 0
    assert option.is_accelerated is False


@pytest.mark.parametrize(
    ("amount", "points", "exceeded"),
    [
        # At TravelOne's ₹3,75,000 cap (15,000 RP ÷ 4 × ₹100): 3,750 × 4.00
        (375_000, 15_000, False),
        # ₹25,000 past it earns HSBC's stated 2 RP base: 15,000 + 250 × 2.00
        (400_000, 15_500, True),
    ],
)
def test_travelone_travel_cap_boundary(
    snapshot: CatalogSnapshot, amount: int, points: int, exceeded: bool
) -> None:
    result = _rank(snapshot, ["TravelOne"], amount, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == points
    assert option.cap_exceeded is exceeded


def test_default_category_is_not_flagged_accelerated(snapshot: CatalogSnapshot) -> None:
    result = _rank(snapshot, ["Infinia Metal"], 10_000, SpendCategory.DEFAULT)
    (option,) = result.ranked
    assert option.is_accelerated is False
    assert option.cap_exceeded is False


def test_spend_exactly_at_cap_keeps_the_accelerated_rate(snapshot: CatalogSnapshot) -> None:
    """Boundary: ₹1,12,500 is AT Infinia's travel cap (15,000 bonus RP at 5X),
    so the whole amount earns 16.65 → floor(1125 × 16.65) = floor(18,731.25)
    = 18,731. One rupee more blends."""
    result = _rank(snapshot, ["Infinia Metal"], 112_500, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == 18_731
    assert option.cap_exceeded is False


def test_spend_over_cap_blends_down_to_base(snapshot: CatalogSnapshot) -> None:
    """₹2,00,000 travel on Infinia: ₹1,12,500 at 16.65 + ₹87,500 at 3.33
    = (1,873,125 + 291,375) / 200,000 = 10.8225 pts/₹100 → 21,645 points."""
    result = _rank(snapshot, ["Infinia Metal"], 200_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.effective_earn_rate == Decimal("10.8225")
    assert option.points_earned == 21_645
    assert option.cap_exceeded is True


def test_infinia_overflow_is_stated_as_base_rate(snapshot: CatalogSnapshot) -> None:
    """The caller is told WHAT the overflow earned, not left to assume it."""
    result = _rank(snapshot, ["Infinia Metal"], 200_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.over_cap_earn == OverCapEarn.BASE_RATE


# ── over-cap spend that earns NOTHING (defect fixed 2026-11-02) ───────────
# SBI Cashback pays 5% online up to ₹2,000 cashback per statement cycle
# (= ₹40,000 of spend) and 1% offline up to ₹2,000 (= ₹2,00,000), then
# NOTHING. The engine used to pay the 1% base rate on the overflow.


def _rank_points_only(
    snapshot: CatalogSnapshot, names: list[str], amount: int, category: SpendCategory
):
    return rank_cards_for_spend(
        snapshot,
        amount_inr=amount,
        category=category,
        card_ids=[_card_id(snapshot, n) for n in names],
    )


def test_sbi_online_over_cap_earns_nothing_past_the_cap(snapshot: CatalogSnapshot) -> None:
    """₹50,000 online on SBI Cashback:
    ₹40,000 × 5% = 2,000 + ₹10,000 × 0 = 0  ⇒  2,000 points (₹2,000 cashback)
    effective rate = 2,000 / 500 = 4.00 per ₹100.
    BEFORE the fix: 2,000 + ₹10,000 × 1% = 100 ⇒ 2,100 at 4.20/₹100."""
    result = _rank_points_only(snapshot, ["Cashback"], 50_000, SpendCategory.ONLINE)
    (option,) = result.ranked
    assert option.points_earned == 2_000
    assert option.effective_earn_rate == Decimal("4.0000")
    assert option.cap_exceeded is True
    assert option.monthly_cap_inr == 40_000
    assert option.over_cap_earn == OverCapEarn.NOTHING


def test_sbi_online_exactly_at_cap_keeps_the_full_rate(snapshot: CatalogSnapshot) -> None:
    """Boundary: ₹40,000 × 5% = 2,000 — at the cap nothing is lost."""
    result = _rank_points_only(snapshot, ["Cashback"], 40_000, SpendCategory.ONLINE)
    (option,) = result.ranked
    assert option.points_earned == 2_000
    assert option.cap_exceeded is False


def test_sbi_online_odd_rupee_over_cap_is_not_double_rounded(snapshot: CatalogSnapshot) -> None:
    """₹50,001 online: exact points = (40,000 × 5 + 10,001 × 0) / 100 = 2,000.00
    ⇒ 2,000. The displayed rate is the 4dp blend 200,000/50,001 = 3.99992…
    → 3.9999, but points must NOT be re-derived from it: 500.01 × 3.9999 =
    1,999.96 would floor to 1,999 (review finding, 2026-11-03)."""
    result = _rank_points_only(snapshot, ["Cashback"], 50_001, SpendCategory.ONLINE)
    (option,) = result.ranked
    assert option.points_earned == 2_000
    assert option.effective_earn_rate == Decimal("3.9999")


def test_atlas_odd_rupee_over_cap_is_not_double_rounded(snapshot: CatalogSnapshot) -> None:
    """Atlas travel ₹2,00,001 (cap ₹2,00,000, overflow at the 2.00 base):
    exact points = (200,000 × 5 + 1 × 2) / 100 = 1,000,002 / 100 = 10,000.02
    ⇒ 10,000; miles = floor(10,000 × 2 / 1) = 20,000. The old path,
    2,000.01 × 4.9999 (blend 1,000,002/200,001 → 4dp) = 9,999.85, floored to
    9,999 points / 19,998 miles."""
    result = _rank(snapshot, ["Atlas"], 200_001, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == 10_000
    assert option.miles_earned == 20_000
    assert option.effective_earn_rate == Decimal("4.9999")
    assert option.cap_exceeded is True


def test_sbi_offline_over_cap_earns_nothing_past_the_cap(snapshot: CatalogSnapshot) -> None:
    """₹2,50,000 offline (the default row) on SBI Cashback:
    ₹2,00,000 × 1% = 2,000 + ₹50,000 × 0 = 0  ⇒  2,000 points
    effective rate = 2,000 / 2,500 = 0.80 per ₹100.
    BEFORE the fix: no offline cap was seeded at all ⇒ 2,500 at 1.00/₹100."""
    result = _rank_points_only(snapshot, ["Cashback"], 250_000, SpendCategory.DEFAULT)
    (option,) = result.ranked
    assert option.points_earned == 2_000
    assert option.effective_earn_rate == Decimal("0.8000")
    assert option.cap_exceeded is True
    assert option.over_cap_earn == OverCapEarn.NOTHING


# ── cards with no route to the target program ─────────────────────────────


def test_card_without_a_transfer_link_is_separated_not_ranked(
    snapshot: CatalogSnapshot,
) -> None:
    """SBI Cashback earns INR, not a transferable currency — it has no route
    to KrisFlyer and must never be ranked against cards that do. It is
    reported, not hidden: the user still owns it."""
    result = _rank(snapshot, ["Infinia Metal", "Cashback"], 10_000, SpendCategory.DEFAULT)

    assert [o.card_name for o in result.ranked] == ["Infinia Metal"]
    (unroutable,) = result.unroutable
    assert unroutable.card_name == "Cashback"
    assert unroutable.miles_earned is None
    assert unroutable.points_earned == 100  # 1.00 pt/₹100 still earned


def test_wallet_with_no_routable_card_ranks_nothing(snapshot: CatalogSnapshot) -> None:
    result = _rank(snapshot, ["Cashback"], 10_000, SpendCategory.DEFAULT)
    assert result.ranked == ()
    assert len(result.unroutable) == 1


# ── determinism and input validation ──────────────────────────────────────


def test_ties_break_on_card_name_for_determinism(snapshot: CatalogSnapshot) -> None:
    """Infinia and Diners Club Black share hdfc-rp-premium and 3.33 base, so
    they tie exactly. Order must still be stable, not dict/set-dependent."""
    names = ["Infinia Metal", "Diners Club Black Metal"]
    forward = _rank(snapshot, names, 10_000, SpendCategory.DEFAULT)
    reverse = _rank(snapshot, list(reversed(names)), 10_000, SpendCategory.DEFAULT)

    assert [o.card_name for o in forward.ranked] == [o.card_name for o in reverse.ranked]
    assert forward.ranked[0].card_name == "Diners Club Black Metal"  # alphabetical


def test_unknown_card_id_is_rejected(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(UnknownCard):
        rank_cards_for_spend(
            snapshot,
            amount_inr=10_000,
            category=SpendCategory.DEFAULT,
            card_ids=[uuid4()],
            target_program_id=_krisflyer_id(snapshot),
        )


@pytest.mark.parametrize("amount", [0, -1])
def test_non_positive_amount_is_rejected(snapshot: CatalogSnapshot, amount: int) -> None:
    with pytest.raises(ValueError):
        _rank(snapshot, ["Infinia Metal"], amount, SpendCategory.DEFAULT)


def test_empty_wallet_is_rejected(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(ValueError):
        _rank(snapshot, [], 10_000, SpendCategory.DEFAULT)
