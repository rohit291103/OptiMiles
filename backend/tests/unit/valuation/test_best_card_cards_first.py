"""Best Card, card-first: every card says where its points can go and what
they become, which programs it is best for, and the wallet is put in an
honest order — by programs won, never by raw points across currencies.

Hand-computed from the seeds (see test_best_card_verdicts.py for the rates
and links). ₹10,000 throughout.
"""

from uuid import UUID

from app.domain import CatalogSnapshot, SpendCategory
from app.valuation.best_card import rank_cards_for_spend


def _ids(snapshot: CatalogSnapshot, *names: str) -> list[UUID]:
    by_name = {c.card_name: c.id for c in snapshot.cards}
    return [by_name[n] for n in names]


def _program(snapshot: CatalogSnapshot, name: str) -> UUID:
    return next(p.id for p in snapshot.partners if p.program_name == name)


WALLET = ("Infinia Metal", "Atlas", "TravelOne")


def test_each_card_lists_every_destination_and_what_it_becomes(
    snapshot: CatalogSnapshot,
) -> None:
    """Infinia, ₹10,000 travel: 1,665 RP via SmartBuy, 333 booked direct.
    HDFC premium → Accor 2:1 (832 / 166), KrisFlyer 1:1 (1,665 / 333),
    Maharaja 2:1 (832 / 166), Bonvoy 2:1 (832 / 166) — by program name."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal"),
    )
    (infinia,) = result.ranked
    got = [
        (d.program_name, d.partner_units, d.direct_partner_units, d.ratio_from, d.ratio_to)
        for d in infinia.destinations
    ]
    assert got == [
        ("ALL - Accor Live Limitless", 832, 166, 2, 1),
        ("KrisFlyer", 1_665, 333, 1, 1),
        ("Maharaja Club", 832, 166, 2, 1),
        ("Marriott Bonvoy", 832, 166, 2, 1),
    ]
    kf = next(d for d in infinia.destinations if d.program_name == "KrisFlyer")
    assert kf.partner_name == "Singapore Airlines"
    assert kf.partner_type == "airline"


def test_one_card_that_wins_everywhere_is_the_overall_pick(
    snapshot: CatalogSnapshot,
) -> None:
    """Travel: Infinia wins KrisFlyer (1,665 vs Atlas 1,000), Bonvoy and
    Accor (832 vs TravelOne 400) and Maharaja (only route) → one answer."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, *WALLET),
    )
    infinia_id = _ids(snapshot, "Infinia Metal")[0]
    assert result.overall_pick == infinia_id
    infinia = next(o for o in result.ranked if o.card_id == infinia_id)
    assert len(infinia.best_for) == 4
    # Order: by programs won (Infinia 4), then by best placing anywhere —
    # Atlas is 2nd for KrisFlyer, TravelOne 2nd for Bonvoy/Accor (tie) →
    # card name breaks it. Never by raw points across currencies.
    assert [o.card_name for o in result.ranked] == ["Infinia Metal", "Atlas", "TravelOne"]


def test_when_winners_differ_there_is_no_overall_pick(snapshot: CatalogSnapshot) -> None:
    """Everyday spend: KrisFlyer → Atlas (2.00 × 1:2 = 400 vs Infinia 333,
    TravelOne 200); Bonvoy & Accor → TravelOne (200 vs Infinia
    floor(333/2) = 166); Maharaja → Infinia (166, only route)."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, *WALLET),
    )
    assert result.overall_pick is None
    wins = {o.card_name: len(o.best_for) for o in result.ranked}
    assert wins == {"TravelOne": 2, "Atlas": 1, "Infinia Metal": 1}
    # TravelOne (2 wins) first; Atlas and Infinia (1 each, both 1st
    # somewhere) by name.
    assert [o.card_name for o in result.ranked] == ["TravelOne", "Atlas", "Infinia Metal"]


def test_a_single_card_is_the_pick_when_it_reaches_somewhere(
    snapshot: CatalogSnapshot,
) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Atlas"),
    )
    (atlas,) = result.ranked
    assert result.overall_pick == atlas.card_id
    (only,) = atlas.destinations
    # 200 EDGE Miles × 1:2 = 400 KrisFlyer miles; Atlas reaches nothing else.
    assert (only.program_name, only.partner_units) == ("KrisFlyer", 400)


def test_a_tie_at_the_top_is_not_an_overall_pick(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Diners Club Black Metal"),
    )
    assert result.overall_pick is None
    # Both share every top spot.
    assert all(len(o.best_for) == 4 for o in result.ranked)


def test_cards_with_nowhere_to_go_come_last(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback pays cash and transfers nowhere: no destinations, no
    wins — listed after every card that reaches a program."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Cashback", "Atlas"),
    )
    assert [o.card_name for o in result.ranked] == ["Atlas", "Cashback"]
    cashback = result.ranked[1]
    assert cashback.destinations == () and cashback.best_for == ()


def test_a_chosen_program_keeps_the_miles_ranking(snapshot: CatalogSnapshot) -> None:
    """With a program chosen the order is that program's units, as before."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, *WALLET),
        target_program_id=_program(snapshot, "Marriott Bonvoy"),
    )
    # Bonvoy: TravelOne 200, Infinia 166; Atlas has no route (unroutable).
    assert [o.card_name for o in result.ranked] == ["TravelOne", "Infinia Metal"]
    assert [o.card_name for o in result.unroutable] == ["Atlas"]


def test_a_destination_carries_its_own_provenance(snapshot: CatalogSnapshot) -> None:
    """ "Becomes 400 KrisFlyer miles" rests on the Atlas → KrisFlyer link.
    The card's own points can be verified while that conversion is not."""
    from app.knowledge.seed_catalog import seed_id

    link = next(
        li.id
        for li in snapshot.transfer_links
        if li.currency_id == seed_id("currency", "axis-edge-miles")
        and li.partner_id == _program(snapshot, "KrisFlyer")
    )
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Atlas"),
        unverified_ids=frozenset({link}),
    )
    (atlas,) = result.ranked
    assert atlas.needs_verification is False
    assert atlas.destinations[0].needs_verification is True


def test_tied_top_cards_share_first_place_in_the_order(snapshot: CatalogSnapshot) -> None:
    """Everyday ₹10,000: Infinia and Diners share a currency and a rate, so
    they TIE for KrisFlyer (333 each, TravelOne 200) and Maharaja (166 each);
    TravelOne tops Bonvoy and Accor (200 vs floor(333/2) = 166). All three
    top two programs. A tied card must not be pushed down the order because
    it came second in a name tiebreak — before the fix Infinia sat behind
    TravelOne at place 1."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Infinia Metal", "Diners Club Black Metal", "TravelOne"),
    )
    assert [o.card_name for o in result.ranked] == [
        "Diners Club Black Metal",
        "Infinia Metal",
        "TravelOne",
    ]
    # Same standing → same position; the list is an order, not a ranking.
    assert [o.order_position for o in result.ranked] == [1, 1, 1]


def test_order_positions_are_dense_and_shared_only_on_equal_standing(
    snapshot: CatalogSnapshot,
) -> None:
    """Everyday spend, Infinia + Atlas + TravelOne: TravelOne 2 wins, Atlas
    and Infinia 1 win each (both first somewhere) → positions 1, 2, 2."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, *WALLET),
    )
    assert [(o.card_name, o.order_position) for o in result.ranked] == [
        ("TravelOne", 1),
        ("Atlas", 2),
        ("Infinia Metal", 2),
    ]


def test_a_chosen_program_has_no_order_positions(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, *WALLET),
        target_program_id=_program(snapshot, "KrisFlyer"),
    )
    assert all(o.order_position is None for o in result.ranked)
