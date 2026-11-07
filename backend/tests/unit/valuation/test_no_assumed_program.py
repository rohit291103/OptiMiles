"""No program is assumed until the user chooses one.

`CLAUDE.md` → *Never Assume the User's Goal*, decision log
`2026-08-26-scope-broadening-and-partner-choice.md`. Both priced surfaces used
to default to KrisFlyer because the (now retired) MVP scope named it primary,
and printed the program name in the UI on pages where the user had said
nothing. These tests pin the corrected contract: with no target chosen, the
engines report what the catalog states directly — points, rates, caps — and
report which programs the wallet could reach, so the product can ASK.
"""

from uuid import uuid4

import pytest

from app.domain import CatalogSnapshot, SpendCategory
from app.valuation.best_card import rank_cards_for_spend
from app.valuation.portfolio import build_portfolio
from app.valuation.wallet import UnknownCard, partner_reach, resolve_wallet


def _ids(snapshot: CatalogSnapshot, names: list[str]):
    return [next(c.id for c in snapshot.cards if c.card_name == n) for n in names]


def _partner(snapshot: CatalogSnapshot, program: str):
    return next(p.id for p in snapshot.partners if p.program_name == program)


# ── Best Card with no program chosen ──────────────────────────────────────


def test_best_card_reports_points_only_when_no_program_is_chosen(
    snapshot: CatalogSnapshot,
) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["Regalia Gold", "TravelOne", "Atlas"]),
        target_program_id=None,
    )

    assert result.ranking_basis == "points"
    assert result.target_program_id is None
    assert result.target_program_name is None
    assert all(option.miles_earned is None for option in result.ranked)
    assert all(option.miles_per_100 is None for option in result.ranked)
    # Nothing is "unroutable" when there is no route being asked about.
    assert result.unroutable == ()
    # The points themselves are still real and still shown.
    assert {o.card_name: o.points_earned for o in result.ranked} == {
        "Regalia Gold": 250,  # 10,000/100 × 2.50 (5 RP/₹200 since 15 May 2026)
        "TravelOne": 200,
        "Atlas": 200,
    }


def test_points_only_order_is_by_programs_won_not_points(snapshot: CatalogSnapshot) -> None:
    """With no program chosen the wallet is ordered by PROGRAMS WON — never
    by raw points across currencies (2026-11-07; the old points order put
    Regalia Gold's 250 RP first, though it is the top card nowhere).

    ₹10,000 everyday spend: Regalia 250 RP → KrisFlyer 2:1 = 125, Bonvoy
    100:33 = floor(82.5) = 82, Accor 2:1 = 125. Atlas 200 EDGE → KrisFlyer
    1:2 = 400. TravelOne 200 RP → KrisFlyer / Bonvoy / Accor 1:1 = 200.
    KrisFlyer → Atlas; Bonvoy and Accor → TravelOne; Regalia wins none."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["TravelOne", "Atlas", "Regalia Gold"]),
        target_program_id=None,
    )
    assert result.ranking_basis == "points"
    assert [o.card_name for o in result.ranked] == ["TravelOne", "Atlas", "Regalia Gold"]


def test_choosing_a_program_switches_the_basis_to_miles(snapshot: CatalogSnapshot) -> None:
    """And only then does the honest winner appear: TravelOne earns fewer
    points than Regalia Gold but more KrisFlyer miles."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["Regalia Gold", "TravelOne"]),
        target_program_id=_partner(snapshot, "KrisFlyer"),
    )
    assert result.ranking_basis == "miles"
    assert result.target_program_name == "KrisFlyer"
    assert result.ranked[0].card_name == "TravelOne"


# ── the choice we offer has to be reachable ───────────────────────────────


def test_best_card_offers_only_programs_this_wallet_can_reach(
    snapshot: CatalogSnapshot,
) -> None:
    """An Axis-only wallet reaches KrisFlyer and nothing else. Offering
    Marriott or Accor here would be a dead end — every card would come back
    "no route" after the user chose."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["Atlas", "Magnus for Burgundy"]),
        target_program_id=None,
    )
    assert [reach.program_name for reach in result.partner_reach] == ["KrisFlyer"]
    assert all(reach.is_target is False for reach in result.partner_reach)


def test_an_hdfc_premium_wallet_reaches_four_programs(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["Infinia Metal"]),
        target_program_id=None,
    )
    assert [reach.program_name for reach in result.partner_reach] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Maharaja Club",
        "Marriott Bonvoy",
    ]


def test_a_cashback_only_wallet_is_offered_nothing(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback has no transfer links at all. The honest answer is that
    there is no transfer question to ask — not an empty dropdown of options
    that would all fail."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, ["Cashback"]),
        target_program_id=None,
    )
    assert result.partner_reach == ()
    assert result.ranked[0].points_earned == 100


# ── Portfolio with no program chosen ──────────────────────────────────────


def test_portfolio_prices_nothing_until_a_program_is_chosen(
    snapshot: CatalogSnapshot,
) -> None:
    portfolio = build_portfolio(
        snapshot,
        card_ids=_ids(snapshot, ["Infinia Metal", "Atlas"]),
        target_program_id=None,
        unverified_ids=frozenset(),
    )

    assert portfolio.target_program_id is None
    assert portfolio.target_program_name is None
    assert portfolio.cards_reaching_target is None
    for card in portfolio.cards:
        assert card.reaches_target is None
        assert all(rule.miles_per_100 is None for rule in card.earn_rules)
        assert all(milestone.bonus_miles is None for milestone in card.milestones)
        # The transfer links themselves are still the useful, factual answer
        # to "where can this card send points" — that is catalog data, not an
        # assumption, and it is what the chooser is built from.
        assert card.transfer_links
        assert all(link.is_target is False for link in card.transfer_links)


def test_no_category_has_a_leader_without_a_chosen_program(
    snapshot: CatalogSnapshot,
) -> None:
    """There is no honest winner across currencies, so we name none — and the
    earn rates are still shown so the page is not empty."""
    portfolio = build_portfolio(
        snapshot,
        card_ids=_ids(snapshot, ["Infinia Metal", "Atlas"]),
        target_program_id=None,
        unverified_ids=frozenset(),
    )
    for category in portfolio.categories:
        assert category.leader_card_id is None
        assert all(row.miles_per_100 is None for row in category.rows)
        assert all(row.earn_rate > 0 for row in category.rows)


def test_portfolio_still_reports_where_points_could_go(snapshot: CatalogSnapshot) -> None:
    portfolio = build_portfolio(
        snapshot,
        card_ids=_ids(snapshot, ["Infinia Metal", "Atlas"]),
        target_program_id=None,
        unverified_ids=frozenset(),
    )
    assert [reach.program_name for reach in portfolio.partner_reach] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Maharaja Club",
        "Marriott Bonvoy",
    ]


# ── the shared wallet helpers ─────────────────────────────────────────────


def test_resolve_wallet_keeps_order_and_collapses_duplicates(
    snapshot: CatalogSnapshot,
) -> None:
    ids = _ids(snapshot, ["TravelOne", "Infinia Metal", "TravelOne"])
    assert [c.card_name for c in resolve_wallet(snapshot, ids)] == [
        "TravelOne",
        "Infinia Metal",
    ]


def test_resolve_wallet_fails_loudly_on_an_unknown_card(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(UnknownCard):
        resolve_wallet(snapshot, [uuid4()])


def test_resolve_wallet_rejects_an_empty_wallet(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(ValueError, match="card_ids"):
        resolve_wallet(snapshot, [])


def test_partner_reach_puts_a_chosen_target_first(snapshot: CatalogSnapshot) -> None:
    wallet = resolve_wallet(snapshot, _ids(snapshot, ["Infinia Metal"]))
    reach = partner_reach(
        snapshot,
        wallet,
        target_program_id=_partner(snapshot, "Marriott Bonvoy"),
        unverified_ids=None,
    )
    assert reach[0].program_name == "Marriott Bonvoy"
    assert reach[0].is_target is True
    assert [r.program_name for r in reach[1:]] == sorted(r.program_name for r in reach[1:])
    # No provenance supplied (Best Card's case) → "not assessed", never False.
    assert all(r.needs_verification is None for r in reach)
