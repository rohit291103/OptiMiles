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

from app.domain import CatalogSnapshot, SpendCategory
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
        # Regalia Gold 2.67 → 267 pts; hdfc-rp-regalia 2:1 → floor(267/2) = 133
        ("Regalia Gold", 267, 133),
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
    """Regalia Gold out-earns TravelOne on POINTS (267 vs 200) and loses on
    MILES (133 vs 200), because Regalia's tier transfers 2:1 while HSBC is
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
        "Regalia Gold",  # 133
    ]
    assert [o.miles_earned for o in result.ranked] == [480, 400, 333, 200, 133]


# ── accelerated categories and caps ───────────────────────────────────────


def test_accelerated_category_beats_base_rate(snapshot: CatalogSnapshot) -> None:
    """Infinia travel is 16.65 via SmartBuy: ₹10,000 → floor(100 × 16.65) = 1,665."""
    result = _rank(snapshot, ["Infinia Metal"], 10_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == 1_665
    assert option.miles_earned == 1_665
    assert option.is_accelerated is True
    assert option.monthly_cap_inr == 150_000


def test_default_category_is_not_flagged_accelerated(snapshot: CatalogSnapshot) -> None:
    result = _rank(snapshot, ["Infinia Metal"], 10_000, SpendCategory.DEFAULT)
    (option,) = result.ranked
    assert option.is_accelerated is False
    assert option.cap_exceeded is False


def test_spend_exactly_at_cap_keeps_the_accelerated_rate(snapshot: CatalogSnapshot) -> None:
    """Boundary: ₹1,50,000 is AT Infinia's travel cap, so the whole amount
    earns 16.65 → floor(1500 × 16.65) = 24,975. One rupee more blends."""
    result = _rank(snapshot, ["Infinia Metal"], 150_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.points_earned == 24_975
    assert option.cap_exceeded is False


def test_spend_over_cap_blends_down_to_base(snapshot: CatalogSnapshot) -> None:
    """₹2,00,000 travel on Infinia: ₹1.5L at 16.65 + ₹50k at 3.33
    = (2,497,500 + 166,500) / 200,000 = 13.32 pts/₹100 → 26,640 points."""
    result = _rank(snapshot, ["Infinia Metal"], 200_000, SpendCategory.TRAVEL)
    (option,) = result.ranked
    assert option.effective_earn_rate == Decimal("13.3200")
    assert option.points_earned == 26_640
    assert option.cap_exceeded is True


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
