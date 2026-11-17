"""Best Card never answers with an unverified figure (Week 47 Session 2).

CLAUDE.md: "No optimization recommendation may be built from unverified
rows." Best Card is a recommendation surface end to end, so an unverified
figure is not shown with a label. It is left out of the answer altogether,
and the card is named in `withheld` with no numbers attached. Decision log
`2026-11-17-best-card-verified-only.md`.

Two levels of withholding:
  - the card's own earn on this purchase (rule, or base rate where it takes
    part, through the portal or booked direct) is unverified → the card is
    left out everywhere (`program_id is None`)
  - only its transfer into one program (link, currency or partner) is
    unverified → the card keeps its verified points, but is not a candidate
    in that program (`program_id` set)

Hand values from the seeds, ₹10,000 of travel:
  Atlas     5.00 → 500 EDGE Miles × 1:2 = 1,000 KrisFlyer miles
  TravelOne 4.00 → 400 HSBC RP × 1:1 = 400 KrisFlyer / Bonvoy / Accor
  Infinia   16.65 via SmartBuy → 1,665 RP × 1:1 = 1,665 KrisFlyer miles
"""

from uuid import UUID

from app.domain import CatalogSnapshot, SpendCategory
from app.knowledge.seed_catalog import load_unverified_ids, seed_id
from app.valuation.best_card import BestCardResult, rank_cards_for_spend


def _ids(snapshot: CatalogSnapshot, *names: str) -> list[UUID]:
    by_name = {c.card_name: c.id for c in snapshot.cards}
    return [by_name[n] for n in names]


def _program(snapshot: CatalogSnapshot, name: str) -> UUID:
    return next(p.id for p in snapshot.partners if p.program_name == name)


def _atlas_kf_link(snapshot: CatalogSnapshot) -> UUID:
    return next(
        link.id
        for link in snapshot.transfer_links
        if link.currency_id == seed_id("currency", "axis-edge-miles")
        and link.partner_id == _program(snapshot, "KrisFlyer")
    )


def _withheld(result: BestCardResult) -> set[tuple[str, str | None]]:
    return {(w.card_name, w.program_name) for w in result.withheld}


# ── A card whose own earn is unverified is left out everywhere ───────────


def test_an_unverified_rate_is_never_the_answer(snapshot: CatalogSnapshot) -> None:
    """Infinia's SmartBuy figure (1,665) would beat TravelOne (400) in every
    program. With that rule unverified, TravelOne is the answer and Infinia
    is named as withheld — with no figure anywhere in the result."""
    infinia_id = _ids(snapshot, "Infinia Metal")[0]
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "TravelOne"),
        unverified_ids=frozenset({seed_id("category", "hdfc-infinia:travel")}),
    )
    assert [o.card_name for o in result.ranked] == ["TravelOne"]
    assert result.unroutable == ()
    assert _withheld(result) == {("Infinia Metal", None)}

    travelone_id = _ids(snapshot, "TravelOne")[0]
    assert result.overall_pick == travelone_id
    for verdict in result.program_verdicts:
        picks = (verdict.winner, verdict.runner_up, verdict.direct_winner)
        assert all(p is None or p.card_id != infinia_id for p in picks)
    assert all(infinia_id not in reach.card_ids for reach in result.partner_reach)


def test_an_unverified_base_rate_withholds_the_card_even_through_the_portal(
    snapshot: CatalogSnapshot,
) -> None:
    """The SmartBuy rule is verified but the card row (base rate) is not, so
    the booked-direct figure is unverified. A card is in the answer only when
    every figure it would show is verified."""
    infinia_id = _ids(snapshot, "Infinia Metal")[0]
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "TravelOne"),
        unverified_ids=frozenset({infinia_id}),
    )
    assert [o.card_name for o in result.ranked] == ["TravelOne"]
    assert _withheld(result) == {("Infinia Metal", None)}


def test_a_flagged_card_row_does_not_matter_where_the_base_rate_takes_no_part(
    snapshot: CatalogSnapshot,
) -> None:
    """Atlas travel is a non-portal rule under its cap: neither figure rests on
    the card row, so a flag there leaves the answer alone."""
    atlas_id = _ids(snapshot, "Atlas")[0]
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=[atlas_id],
        unverified_ids=frozenset({atlas_id}),
    )
    (atlas,) = result.ranked
    assert atlas.points_earned == 500
    assert result.withheld == ()


# ── A card whose transfer is unverified is left out of that program ──────


def test_an_unverified_transfer_cannot_win_its_program(snapshot: CatalogSnapshot) -> None:
    """Atlas would win KrisFlyer (1,000 vs 400). With its link unverified,
    TravelOne wins; Atlas keeps its verified 500 EDGE Miles but has no
    KrisFlyer destination and is not a candidate there."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Atlas", "TravelOne"),
        unverified_ids=frozenset({_atlas_kf_link(snapshot)}),
    )
    by_name = {o.card_name: o for o in result.ranked}
    assert by_name["Atlas"].points_earned == 500
    assert by_name["Atlas"].destinations == ()
    assert by_name["Atlas"].best_for == ()
    assert _withheld(result) == {("Atlas", "KrisFlyer")}

    kf = next(v for v in result.program_verdicts if v.program_name == "KrisFlyer")
    assert kf.winner is not None
    assert (kf.winner.card_name, kf.winner.partner_units) == ("TravelOne", 400)
    assert kf.runner_up is None
    assert result.overall_pick == _ids(snapshot, "TravelOne")[0]


def test_with_a_program_chosen_an_unverified_route_is_withheld_not_unroutable(
    snapshot: CatalogSnapshot,
) -> None:
    """'Can't reach KrisFlyer' would be false — Atlas can, we just haven't
    verified how well. So it is withheld, never listed as unroutable."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Atlas", "TravelOne"),
        target_program_id=_program(snapshot, "KrisFlyer"),
        unverified_ids=frozenset({_atlas_kf_link(snapshot)}),
    )
    assert [(o.card_name, o.miles_earned) for o in result.ranked] == [("TravelOne", 400)]
    assert result.unroutable == ()
    assert _withheld(result) == {("Atlas", "KrisFlyer")}


def test_an_unverified_program_is_never_offered_or_answered(snapshot: CatalogSnapshot) -> None:
    kf_id = _program(snapshot, "KrisFlyer")
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Atlas", "TravelOne"),
        unverified_ids=frozenset({kf_id}),
    )
    assert all(v.program_id != kf_id for v in result.program_verdicts)
    assert all(r.partner_id != kf_id for r in result.partner_reach)
    assert _withheld(result) == {("Atlas", "KrisFlyer"), ("TravelOne", "KrisFlyer")}


# ── States that must not be misreported ──────────────────────────────────


def test_nobody_earns_is_not_claimed_while_a_card_is_withheld(
    snapshot: CatalogSnapshot,
) -> None:
    """Infinia earns nothing on fuel (verified). Diners Black's fuel rule is
    flagged, so we do not know what it earns — 'no card earns here' would be
    a claim about a card we left out."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=5_000,
        category=SpendCategory.FUEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Diners Club Black Metal"),
        unverified_ids=frozenset({seed_id("category", "hdfc-diners-black:fuel")}),
    )
    assert [o.card_name for o in result.ranked] == ["Infinia Metal"]
    assert result.no_card_earns is False


def test_a_wallet_with_nothing_verified_has_no_answer(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal"),
        unverified_ids=frozenset({seed_id("category", "hdfc-infinia:travel")}),
    )
    assert result.ranked == ()
    assert result.program_verdicts == ()
    assert result.partner_reach == ()
    assert result.overall_pick is None
    assert result.no_card_earns is False
    assert _withheld(result) == {("Infinia Metal", None)}


def test_no_provenance_supplied_withholds_nothing(snapshot: CatalogSnapshot) -> None:
    """None = not assessed. Engine callers without provenance keep today's
    behaviour; the API always supplies it."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal"),
    )
    assert result.withheld == ()
    assert result.ranked[0].needs_verification is None


def test_withheld_order_does_not_depend_on_wallet_order(snapshot: CatalogSnapshot) -> None:
    flags = frozenset({seed_id("category", "hdfc-infinia:travel"), _atlas_kf_link(snapshot)})
    names = ("Infinia Metal", "Atlas", "TravelOne")
    forward, backward = (
        rank_cards_for_spend(
            snapshot,
            amount_inr=10_000,
            category=SpendCategory.TRAVEL,
            card_ids=_ids(snapshot, *order),
            unverified_ids=flags,
        )
        for order in (names, tuple(reversed(names)))
    )
    assert forward.withheld == backward.withheld


def test_a_flagged_target_program_leaves_nothing_unroutable_that_can_reach_it(
    snapshot: CatalogSnapshot,
) -> None:
    """KrisFlyer itself unverified, and chosen: TravelOne and Atlas both reach
    it, so both are withheld — never 'can't reach'. SBI Cashback genuinely
    has no route, so it alone is unroutable."""
    kf_id = _program(snapshot, "KrisFlyer")
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Atlas", "TravelOne", "Cashback"),
        target_program_id=kf_id,
        unverified_ids=frozenset({kf_id}),
    )
    assert result.ranked == ()
    assert [o.card_name for o in result.unroutable] == ["Cashback"]
    assert _withheld(result) == {("Atlas", "KrisFlyer"), ("TravelOne", "KrisFlyer")}


def test_a_flagged_currency_withholds_its_transfers_not_its_points(
    snapshot: CatalogSnapshot,
) -> None:
    """Points earned come from the card and its rule; the currency row says
    where they can go (transfer entitlement, expiry). So a flagged currency
    withholds every transfer, and leaves the verified points figure."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Regalia Gold"),
        unverified_ids=frozenset({seed_id("currency", "hdfc-rp-regalia")}),
    )
    (regalia,) = result.ranked
    assert regalia.points_earned > 0
    assert regalia.destinations == ()
    assert result.program_verdicts == ()
    assert {program for _, program in _withheld(result)} == {
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Marriott Bonvoy",
    }


# ── The property, over the real seed flags ───────────────────────────────


def _rows_behind(snapshot: CatalogSnapshot, option, category: SpendCategory) -> set[UUID]:
    """The seed rows a shown option rests on, worked out from the snapshot and
    the option's own fields — NOT from the engine's provenance helpers, so a
    bug there cannot hide here. Conservative: the card row counts whenever a
    base rate could take part (no rule, a portal rule's direct figure, or an
    overflow at base past a cap)."""
    card = next(c for c in snapshot.cards if c.id == option.card_id)
    rule = next(
        (
            r
            for r in snapshot.category_rules
            if r.card_id == card.id and r.category_slug == category
        ),
        None,
    )
    rows: set[UUID] = set()
    if rule is not None:
        rows.add(rule.id)
    if rule is None or rule.requires_portal is not None or option.cap_exceeded:
        rows.add(card.id)
    return rows


def _link_rows(snapshot: CatalogSnapshot, card_id: UUID, program_id: UUID) -> set[UUID]:
    card = next(c for c in snapshot.cards if c.id == card_id)
    link = next(
        li
        for li in snapshot.transfer_links
        if li.currency_id == card.reward_currency_id and li.partner_id == program_id
    )
    return {link.id, link.currency_id, link.partner_id}


def test_with_the_real_seed_flags_nothing_shown_rests_on_a_flagged_row(
    snapshot: CatalogSnapshot, seed_dir
) -> None:
    """Every card, every category, every program chosen or none, under and
    far over the caps: no figure in the result rests on a flagged row. This
    is the standing guard for the rule."""
    flags = load_unverified_ids(seed_dir)
    every_card = [card.id for card in snapshot.cards]
    targets: list[UUID | None] = [None, *(p.id for p in snapshot.partners)]
    for category in SpendCategory:
        for amount in (25_000, 10_000_000):
            for target in targets:
                result = rank_cards_for_spend(
                    snapshot,
                    amount_inr=amount,
                    category=category,
                    card_ids=every_card,
                    target_program_id=target,
                    unverified_ids=flags,
                )
                where = (category, amount, target)
                options = {o.card_id: o for o in (*result.ranked, *result.unroutable)}
                for option in options.values():
                    assert _rows_behind(snapshot, option, category).isdisjoint(flags), where
                    for d in option.destinations:
                        rows = _link_rows(snapshot, option.card_id, d.program_id)
                        assert rows.isdisjoint(flags), (*where, option.card_name, d.program_name)
                    if target is not None and option.miles_earned is not None:
                        assert _link_rows(snapshot, option.card_id, target).isdisjoint(flags)
                for verdict in result.program_verdicts:
                    assert verdict.program_id not in flags, where
                    for pick in (verdict.winner, verdict.runner_up, verdict.direct_winner):
                        if pick is not None:
                            assert pick.card_id in options, where
                            rows = _link_rows(snapshot, pick.card_id, verdict.program_id)
                            assert rows.isdisjoint(flags), (*where, pick.card_name)
                for reach in result.partner_reach:
                    assert reach.partner_id not in flags, where
                    assert all(
                        _link_rows(snapshot, card_id, reach.partner_id).isdisjoint(flags)
                        for card_id in reach.card_ids
                    ), where
                if result.overall_pick is not None:
                    assert result.overall_pick in options, where
