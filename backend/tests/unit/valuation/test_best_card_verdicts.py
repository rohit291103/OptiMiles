"""Best Card, the smarter answer: how you pay, every program at once, and why.

Hand-computed from the seeds (cards.yaml, transfer_links.yaml). ₹10,000 of
travel throughout unless stated:

  Infinia   travel 16.65 via HDFC SmartBuy → 1,665 RP; booked direct the
            portal rate does not apply → base 3.33 → 333 RP
  Atlas     travel 5.00 (portal OR direct airline/hotel) → 500 EDGE Miles
  TravelOne travel 4.00 (airline / aggregator MCCs) → 400 RP

Links: HDFC premium → KrisFlyer 1:1, Maharaja 2:1, Bonvoy 2:1, Accor 2:1;
EDGE Miles → KrisFlyer 1:2; HSBC → KrisFlyer / Bonvoy / Accor 1:1.
"""

from decimal import Decimal
from uuid import UUID

from app.domain import CatalogSnapshot, SpendCategory
from app.knowledge.seed_catalog import seed_id
from app.valuation.best_card import ProgramVerdict, rank_cards_for_spend


def _ids(snapshot: CatalogSnapshot, *names: str) -> list[UUID]:
    by_name = {c.card_name: c.id for c in snapshot.cards}
    return [by_name[n] for n in names]


def _program(snapshot: CatalogSnapshot, name: str) -> UUID:
    return next(p.id for p in snapshot.partners if p.program_name == name)


def _verdict(result, program_name: str) -> ProgramVerdict:
    return next(v for v in result.program_verdicts if v.program_name == program_name)


WALLET = ("Infinia Metal", "Atlas", "TravelOne")


# ── Know how you pay ──────────────────────────────────────────────────────


def test_a_portal_rate_carries_its_portal_and_the_direct_figure(
    snapshot: CatalogSnapshot,
) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Atlas"),
        target_program_id=_program(snapshot, "KrisFlyer"),
    )
    infinia, atlas = result.ranked
    assert infinia.card_name == "Infinia Metal"
    assert infinia.requires_portal == "HDFC SmartBuy"
    assert (infinia.points_earned, infinia.miles_earned) == (1_665, 1_665)
    # Booked direct: floor(100 × 3.33) = 333 RP × 1:1 = 333 miles
    assert (infinia.direct_points_earned, infinia.direct_miles_earned) == (333, 333)
    # Atlas is not portal-gated: its direct figure IS its figure.
    assert atlas.requires_portal is None
    assert (atlas.direct_points_earned, atlas.direct_miles_earned) == (500, 1_000)
    assert (atlas.transfer_ratio_from, atlas.transfer_ratio_to) == (1, 2)


def test_a_rate_without_a_portal_needs_no_direct_alternative(
    snapshot: CatalogSnapshot,
) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Infinia Metal"),
    )
    (infinia,) = result.ranked
    assert infinia.requires_portal is None
    assert infinia.direct_points_earned == infinia.points_earned == 333


# ── Every reachable program at once, no program chosen ────────────────────


def test_points_mode_answers_every_reachable_program(snapshot: CatalogSnapshot) -> None:
    """No program chosen, yet every program the wallet reaches gets its own
    winner — in that program's own unit, so nothing is compared across
    currencies and no ₹ value is invented."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, *WALLET),
    )
    assert result.ranking_basis == "points"
    assert [v.program_name for v in result.program_verdicts] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Maharaja Club",
        "Marriott Bonvoy",
    ]

    kf = _verdict(result, "KrisFlyer")
    # Infinia 1,665 × 1:1 = 1,665 · Atlas 500 × 1:2 = 1,000 · TravelOne 400
    assert kf.winner is not None and kf.winner.card_name == "Infinia Metal"
    assert kf.winner.partner_units == 1_665
    assert kf.winner.requires_portal == "HDFC SmartBuy"
    assert kf.runner_up is not None and kf.runner_up.card_name == "Atlas"
    assert kf.runner_up.partner_units == 1_000
    assert kf.lead == 665
    assert kf.tied is False
    # Booked direct: Infinia 333 · Atlas 1,000 · TravelOne 400 → Atlas
    assert kf.direct_winner is not None and kf.direct_winner.card_name == "Atlas"
    assert kf.direct_winner.partner_units == 1_000

    bonvoy = _verdict(result, "Marriott Bonvoy")
    # Infinia floor(1,665 / 2) = 832 · TravelOne 400 × 1:1 = 400
    assert bonvoy.winner is not None and bonvoy.winner.partner_units == 832
    assert bonvoy.lead == 432
    # Direct: Infinia floor(333 / 2) = 166 · TravelOne 400 → TravelOne
    assert bonvoy.direct_winner is not None
    assert (bonvoy.direct_winner.card_name, bonvoy.direct_winner.partner_units) == (
        "TravelOne",
        400,
    )

    maharaja = _verdict(result, "Maharaja Club")
    # Only Infinia reaches it: floor(1,665 / 2) = 832, no runner-up.
    assert maharaja.winner is not None and maharaja.winner.partner_units == 832
    assert maharaja.runner_up is None and maharaja.lead is None


def test_the_chosen_program_leads_the_verdicts(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, *WALLET),
        target_program_id=_program(snapshot, "Marriott Bonvoy"),
    )
    assert result.program_verdicts[0].program_name == "Marriott Bonvoy"
    assert result.program_verdicts[0].is_target is True
    assert sum(v.is_target for v in result.program_verdicts) == 1


def test_no_direct_winner_when_the_winner_needs_no_portal(snapshot: CatalogSnapshot) -> None:
    """Default spend: Atlas 2.00 × 1:2 = 4.00 miles/₹100 wins KrisFlyer
    without any portal, so there is no 'booking direct?' alternative."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, *WALLET),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is not None and kf.winner.card_name == "Atlas"
    assert kf.winner.partner_units == 400
    assert kf.direct_winner is None


# ── Edge cases: ties and nobody earning ───────────────────────────────────


def test_identical_earners_are_a_tie_not_a_winner(snapshot: CatalogSnapshot) -> None:
    """Infinia and Diners Black share a currency and a SmartBuy rate: 1,665
    each. Naming one by card-name tiebreak would be a coin toss dressed as
    advice."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Diners Club Black Metal"),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.tied is True and kf.lead == 0


def test_nobody_earns_on_fuel(snapshot: CatalogSnapshot) -> None:
    """TravelOne and SBI Cashback both exclude fuel (issuer terms): 0 and 0.
    No winner, in the listing or in any program."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=5_000,
        category=SpendCategory.FUEL,
        card_ids=_ids(snapshot, "TravelOne", "Cashback"),
    )
    assert result.no_card_earns is True
    assert all(v.winner is None for v in result.program_verdicts)


def test_someone_earning_clears_no_card_earns(snapshot: CatalogSnapshot) -> None:
    """Amex Platinum Charge DOES earn on fuel (MR T&C: 5 MR/₹100, seeded
    conservatively at its 2.50 default): ₹5,000 → 125 MR → 2:1 → 62 miles."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=5_000,
        category=SpendCategory.FUEL,
        card_ids=_ids(snapshot, "TravelOne", "Platinum Charge"),
        target_program_id=_program(snapshot, "KrisFlyer"),
    )
    assert result.no_card_earns is False
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is not None and kf.winner.card_name == "Platinum Charge"
    assert kf.winner.partner_units == 62
    # A runner-up may be a zero-earner: TravelOne excludes fuel.
    assert kf.runner_up is not None and kf.runner_up.partner_units == 0


def test_a_wallet_that_cannot_reach_the_program_still_earns(
    snapshot: CatalogSnapshot,
) -> None:
    """SBI Cashback has no route to KrisFlyer, so `ranked` is empty — but it
    earns ₹50 cashback on ₹5,000 offline. 'None of your cards earn' would be
    false; the answer is 'none of them reach this program'."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=5_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Cashback"),
        target_program_id=_program(snapshot, "KrisFlyer"),
    )
    assert result.ranked == ()
    assert result.unroutable[0].points_earned == 50
    assert result.no_card_earns is False


def test_a_tiny_spend_is_too_small_not_an_exclusion(snapshot: CatalogSnapshot) -> None:
    """₹20 at Infinia 3.33 → floor(0.666) = 0 RP; Atlas 2.00 → 0 EDGE Miles.
    That is rounding, not an issuer exclusion: `no_card_earns` stays False
    and each verdict reports `too_small` instead of a winner."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=20,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "Infinia Metal", "Atlas"),
    )
    assert result.no_card_earns is False
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is None and kf.too_small is True


def test_an_exclusion_is_not_too_small(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=5_000,
        category=SpendCategory.FUEL,
        card_ids=_ids(snapshot, "TravelOne"),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is None and kf.too_small is False


# ── Provenance: unverified figures are marked, never passed off ──────────


def test_unverified_rows_mark_the_option_and_the_pick(snapshot: CatalogSnapshot) -> None:
    flagged = frozenset({seed_id("category", "hdfc-infinia:travel")})
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "TravelOne"),
        unverified_ids=flagged,
    )
    by_name = {o.card_name: o for o in result.ranked}
    assert by_name["Infinia Metal"].needs_verification is True
    assert by_name["TravelOne"].needs_verification is False
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is not None and kf.winner.needs_verification is True


def test_no_provenance_supplied_means_not_assessed(snapshot: CatalogSnapshot) -> None:
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal"),
    )
    assert result.ranked[0].needs_verification is None


# ── Direct-booking ties and the portal/non-portal tie ─────────────────────


def test_a_direct_tie_is_marked(snapshot: CatalogSnapshot) -> None:
    """Infinia and Diners Black tie through SmartBuy (1,665) AND booked direct
    (floor(100 × 3.33) = 333 each). The direct alternative is a tie too."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Diners Club Black Metal"),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.direct_winner is not None and kf.direct_winner.partner_units == 333
    assert kf.direct_tied is True


def test_a_tie_with_a_portal_card_still_gets_a_direct_answer(
    snapshot: CatalogSnapshot,
) -> None:
    """Make Infinia's SmartBuy rate 10.00 so it ties Atlas at 1,000 KrisFlyer
    miles (1,000 RP × 1:1 vs 500 EDGE × 1:2). Name order puts Atlas first, but
    a direct alternative is still owed: booked direct Infinia earns only 333."""
    rules = tuple(
        r.model_copy(update={"earn_rate": Decimal("10.00")})
        if r.id == seed_id("category", "hdfc-infinia:travel")
        else r
        for r in snapshot.category_rules
    )
    result = rank_cards_for_spend(
        snapshot.model_copy(update={"category_rules": rules}),
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal", "Atlas"),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.tied is True
    assert kf.direct_winner is not None
    assert (kf.direct_winner.card_name, kf.direct_winner.partner_units) == ("Atlas", 1_000)
    assert kf.direct_tied is False


# ── Gated rates past a cap, and the Axis portal path ─────────────────────


def test_direct_pricing_ignores_the_portal_cap(snapshot: CatalogSnapshot) -> None:
    """₹2,00,000 Infinia travel: via SmartBuy 1,125 × 16.65 + 875 × 3.33 =
    21,645; booked direct the whole amount is base: 2,000 × 3.33 = 6,660."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=200_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Infinia Metal"),
    )
    (infinia,) = result.ranked
    assert (infinia.points_earned, infinia.direct_points_earned) == (21_645, 6_660)


def test_axis_travel_edge_is_a_portal_too(snapshot: CatalogSnapshot) -> None:
    """Magnus for Burgundy ₹10,000 travel: 30.00 via Travel EDGE → 3,000 EDGE
    RP × 5:4 = 2,400 miles; booked direct 6.00 → 600 → 480."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, "Magnus for Burgundy"),
    )
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is not None and kf.winner.partner_units == 2_400
    assert kf.winner.requires_portal == "Axis Travel EDGE"
    assert kf.direct_winner is not None and kf.direct_winner.partner_units == 480


def test_options_and_picks_agree_on_the_target(snapshot: CatalogSnapshot) -> None:
    """Pricing happens in two places (options, verdict picks); they must
    never drift apart."""
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=_ids(snapshot, *WALLET),
        target_program_id=_program(snapshot, "KrisFlyer"),
    )
    kf = _verdict(result, "KrisFlyer")
    by_id = {o.card_id: o for o in result.ranked}
    assert kf.winner is not None and kf.runner_up is not None
    assert by_id[kf.winner.card_id].miles_earned == kf.winner.partner_units
    assert by_id[kf.runner_up.card_id].miles_earned == kf.runner_up.partner_units
    assert kf.direct_winner is not None
    assert by_id[kf.direct_winner.card_id].direct_miles_earned == kf.direct_winner.partner_units


# ── Provenance of the DIRECT figure ───────────────────────────────────────


def test_direct_figure_has_its_own_provenance(snapshot: CatalogSnapshot) -> None:
    """Booked direct, Infinia earns its BASE rate — the card row, not the
    SmartBuy rule. A flagged rule must not taint the direct figure, and a
    flagged card row must."""
    kf_id = _program(snapshot, "KrisFlyer")
    infinia_id = _ids(snapshot, "Infinia Metal")[0]

    rule_flagged = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=[infinia_id],
        target_program_id=kf_id,
        unverified_ids=frozenset({seed_id("category", "hdfc-infinia:travel")}),
    ).ranked[0]
    assert rule_flagged.needs_verification is True
    assert rule_flagged.direct_needs_verification is False

    card_flagged = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.TRAVEL,
        card_ids=[infinia_id],
        target_program_id=kf_id,
        unverified_ids=frozenset({infinia_id}),
    ).ranked[0]
    assert card_flagged.needs_verification is False
    assert card_flagged.direct_needs_verification is True


def test_a_capped_overflow_at_base_depends_on_the_card_row(
    snapshot: CatalogSnapshot,
) -> None:
    """Past the SmartBuy cap the excess earns the card's base rate, so the
    blended figure rests on the card row as well as the rule."""
    infinia_id = _ids(snapshot, "Infinia Metal")[0]
    option = rank_cards_for_spend(
        snapshot,
        amount_inr=200_000,
        category=SpendCategory.TRAVEL,
        card_ids=[infinia_id],
        unverified_ids=frozenset({infinia_id}),
    ).ranked[0]
    assert option.cap_exceeded is True
    assert option.needs_verification is True


def test_a_flagged_partner_flags_options_and_picks(snapshot: CatalogSnapshot) -> None:
    kf_id = _program(snapshot, "KrisFlyer")
    result = rank_cards_for_spend(
        snapshot,
        amount_inr=10_000,
        category=SpendCategory.DEFAULT,
        card_ids=_ids(snapshot, "TravelOne"),
        target_program_id=kf_id,
        unverified_ids=frozenset({kf_id}),
    )
    assert result.ranked[0].needs_verification is True
    kf = _verdict(result, "KrisFlyer")
    assert kf.winner is not None and kf.winner.needs_verification is True
