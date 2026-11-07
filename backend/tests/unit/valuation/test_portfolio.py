"""Portfolio View — the priced read of the user's own wallet.

Every expected value below is hand-computed from the seed catalog
(`seeds/catalog/cards.yaml`, `transfer_links.yaml`) and traceable to a seeded
rate, ratio or cap. This surface tells a user what their wallet is worth
before they spend anything, so a wrong constant here is a wrong strategy.

SAME CENTRAL INVARIANT AS BEST CARD: comparison is by MILES toward the target
program, never by raw points — HDFC RP, EDGE Miles and MR are different units
and the catalog carries no rupee valuation to make them commensurable.
`test_category_leader_is_by_miles_not_points` is the case that proves it, and
`test_leader_is_none_when_no_card_reaches_the_target` is the case that proves
we refuse to rank the incommensurable rather than guessing.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain import CatalogSnapshot, SpendCategory
from app.valuation.best_card import UnknownCard
from app.valuation.portfolio import build_portfolio


def _card_id(snapshot: CatalogSnapshot, card_name: str):
    return next(c.id for c in snapshot.cards if c.card_name == card_name)


def _krisflyer_id(snapshot: CatalogSnapshot):
    return next(p.id for p in snapshot.partners if p.program_name == "KrisFlyer")


def _portfolio(snapshot: CatalogSnapshot, names: list[str]):
    return build_portfolio(
        snapshot,
        card_ids=[_card_id(snapshot, n) for n in names],
        target_program_id=_krisflyer_id(snapshot),
        unverified_ids=frozenset(),
    )


def _card(portfolio, card_name: str):
    return next(c for c in portfolio.cards if c.card_name == card_name)


def _rule(card, slug: SpendCategory):
    return next(r for r in card.earn_rules if r.category_slug == slug)


def _category(portfolio, slug: SpendCategory):
    return next(c for c in portfolio.categories if c.category_slug == slug)


# ── golden: earn rates priced into KrisFlyer miles per ₹100 ───────────────
# miles/₹100 = earn_rate × ratio_to / ratio_from, quantized 4dp ROUND_DOWN


@pytest.mark.parametrize(
    ("card_name", "slug", "earn_rate", "miles_per_100"),
    [
        # Infinia 3.33 pts/₹100, hdfc-rp-premium 1:1
        ("Infinia Metal", SpendCategory.DEFAULT, "3.33", "3.3300"),
        ("Infinia Metal", SpendCategory.TRAVEL, "16.65", "16.6500"),
        # Regalia Gold 2.50 (5 RP/₹200 since 15 May 2026), hdfc-rp-regalia 2:1
        # → 2.50 ÷ 2 = 1.25
        ("Regalia Gold", SpendCategory.DEFAULT, "2.50", "1.2500"),
        # TravelOne 2.00 / 4.00, hsbc-reward-points 1:1
        ("TravelOne", SpendCategory.DEFAULT, "2.00", "2.0000"),
        ("TravelOne", SpendCategory.TRAVEL, "4.00", "4.0000"),
        # Atlas 2.00 / 5.00, axis-edge-miles 1:2 → doubled
        ("Atlas", SpendCategory.DEFAULT, "2.00", "4.0000"),
        ("Atlas", SpendCategory.TRAVEL, "5.00", "10.0000"),
        # Magnus Burgundy 6.00 / 30.00, axis-edge-rewards 5:4
        ("Magnus for Burgundy", SpendCategory.DEFAULT, "6.00", "4.8000"),
        ("Magnus for Burgundy", SpendCategory.TRAVEL, "30.00", "24.0000"),
        # Platinum Travel 2.00, amex-mr 2:1
        ("Platinum Travel", SpendCategory.DEFAULT, "2.00", "1.0000"),
    ],
)
def test_earn_rules_are_priced_in_target_miles(
    snapshot: CatalogSnapshot, card_name: str, slug: SpendCategory, earn_rate, miles_per_100
) -> None:
    rule = _rule(_card(_portfolio(snapshot, [card_name]), card_name), slug)
    assert rule.earn_rate == Decimal(earn_rate)
    assert rule.miles_per_100 == Decimal(miles_per_100)


def test_cashback_card_is_listed_but_priced_at_none(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback has no transfer link at all (the catalog's deliberate
    negative case). It stays in the portfolio — it IS in the wallet — but
    every miles figure is None rather than zero: unreachable, not worthless."""
    portfolio = _portfolio(snapshot, ["Cashback"])
    card = _card(portfolio, "Cashback")
    assert card.reaches_target is False
    assert card.transfer_links == ()
    assert all(rule.miles_per_100 is None for rule in card.earn_rules)
    assert portfolio.cards_reaching_target == 0


# ── the invariant: leadership is by miles, never by points ────────────────


def test_category_leader_is_by_miles_not_points(snapshot: CatalogSnapshot) -> None:
    """Regalia Gold earns MORE points than TravelOne (2.50 vs 2.00 per ₹100)
    but FEWER KrisFlyer miles (1.25 vs 2.00), because its tier transfers 2:1
    against TravelOne's 1:1. Ranking by points would name the worse card."""
    portfolio = _portfolio(snapshot, ["Regalia Gold", "TravelOne"])
    default = _category(portfolio, SpendCategory.DEFAULT)

    assert default.leader_card_id == _card_id(snapshot, "TravelOne")
    rows = {row.card_name: row for row in default.rows}
    assert rows["Regalia Gold"].earn_rate > rows["TravelOne"].earn_rate
    assert rows["Regalia Gold"].miles_per_100 < rows["TravelOne"].miles_per_100


def test_leader_is_none_when_no_card_reaches_the_target(snapshot: CatalogSnapshot) -> None:
    """A wallet of pure cashback has no honest leader: the catalog carries no
    rupee-per-point valuation, so points across currencies cannot be ranked.
    We say "no route" rather than inventing a comparison."""
    default = _category(_portfolio(snapshot, ["Cashback"]), SpendCategory.DEFAULT)
    assert default.leader_card_id is None
    assert default.rows[0].miles_per_100 is None


def test_category_rows_cover_every_wallet_card_at_its_fallback_rate(
    snapshot: CatalogSnapshot,
) -> None:
    """Regalia Gold has no travel rule, so in the travel row it earns its base
    rate — the same fallback Best Card applies — and is flagged un-accelerated
    rather than being dropped from the comparison."""
    portfolio = _portfolio(snapshot, ["Regalia Gold", "Atlas"])
    travel = _category(portfolio, SpendCategory.TRAVEL)

    rows = {row.card_name: row for row in travel.rows}
    assert set(rows) == {"Regalia Gold", "Atlas"}
    assert rows["Regalia Gold"].is_accelerated is False
    assert rows["Regalia Gold"].earn_rate == Decimal("2.50")  # base rate (5 RP/₹200)
    assert rows["Regalia Gold"].category_label == "All other spend"
    assert rows["Atlas"].is_accelerated is True
    assert rows["Atlas"].earn_rate == Decimal("5.00")
    assert travel.leader_card_id == _card_id(snapshot, "Atlas")


def test_categories_are_default_first_then_alphabetical(snapshot: CatalogSnapshot) -> None:
    # Cashback's zero-earn fuel and utilities rows (seeded 2026-11-06) are
    # categories too: a 0.00 row is a real answer ("earns nothing here").
    portfolio = _portfolio(snapshot, ["Infinia Metal", "Cashback"])
    assert [c.category_slug for c in portfolio.categories] == [
        SpendCategory.DEFAULT,
        SpendCategory.FUEL,
        SpendCategory.ONLINE,
        SpendCategory.TRAVEL,
        SpendCategory.UTILITIES,
    ]


def test_no_leader_when_no_routed_card_earns_anything(snapshot: CatalogSnapshot) -> None:
    """Fuel in KrisFlyer miles: TravelOne earns 0.00 (HSBC excludes fuel) ×
    1:1 = 0; Cashback has no route at all. A "winner" at zero miles is not a
    recommendation — no leader is named, and the payload says WHY (nobody
    earns here), which is different from "withheld as unverified"."""
    fuel = _category(_portfolio(snapshot, ["TravelOne", "Cashback"]), SpendCategory.FUEL)
    assert fuel.leader_card_id is None
    assert fuel.no_card_earns is True
    assert fuel.leader_withheld_unverified is False
    travelone = next(r for r in fuel.rows if r.card_name == "TravelOne")
    assert travelone.miles_per_100 == Decimal("0")


def test_a_card_that_earns_still_leads_beside_a_zero_row(snapshot: CatalogSnapshot) -> None:
    """Fuel: Infinia has no fuel rule, so it prices at its 3.33 base × 1:1 =
    3.33 miles/₹100 (HDFC's fuel exclusion is not yet sourced — tracker);
    TravelOne's zero row is 0. Infinia leads, no_card_earns stays False, and
    the category is named neutrally — never by a card's "earns nothing"
    phrasing that the leader contradicts."""
    fuel = _category(_portfolio(snapshot, ["Infinia Metal", "TravelOne"]), SpendCategory.FUEL)
    assert fuel.leader_card_id == _card_id(snapshot, "Infinia Metal")
    assert fuel.no_card_earns is False
    assert "no" not in fuel.category_label.lower()


# ── milestones: what the bonus is actually worth ──────────────────────────


@pytest.mark.parametrize(
    ("card_name", "threshold", "bonus_points", "bonus_miles"),
    [
        # Diners Black: 10,000 RP at ₹4L/quarter, hdfc-rp-premium 1:1
        ("Diners Club Black Metal", 400000, 10000, 10000),
        # Atlas Silver: 2,500 EDGE Miles at ₹3L/year, axis-edge-miles 1:2
        ("Atlas", 300000, 2500, 5000),
        # Amex Platinum Travel: the ₹1.9L tier was removed in 2026; the only points
        # milestone is 10,000 MR at ₹4L/year, amex-mr 2:1 → 10,000 ÷ 2 = 5,000
        ("Platinum Travel", 400000, 10000, 5000),
        # TravelOne: 10,000 RP at ₹12L/anniversary year (added 2026-11-06),
        # hsbc-reward-points 1:1 → 10,000 miles
        ("TravelOne", 1200000, 10000, 10000),
    ],
)
def test_milestone_bonuses_are_priced_in_target_miles(
    snapshot: CatalogSnapshot, card_name: str, threshold: int, bonus_points: int, bonus_miles: int
) -> None:
    card = _card(_portfolio(snapshot, [card_name]), card_name)
    milestone = next(m for m in card.milestones if m.spend_threshold_inr == threshold)
    assert milestone.bonus_points == bonus_points
    assert milestone.bonus_miles == bonus_miles


def test_threshold_free_milestones_sort_first(snapshot: CatalogSnapshot) -> None:
    """Atlas's welcome bonus has no spend threshold; it is the first thing a
    new holder can act on, so it leads the card's milestone list."""
    card = _card(_portfolio(snapshot, ["Atlas"]), "Atlas")
    assert card.milestones[0].spend_threshold_inr is None
    assert [m.spend_threshold_inr for m in card.milestones[1:]] == [300000, 750000, 1500000]


# ── transfer links: the annual ceiling nobody reads the T&C for ───────────


def test_capped_link_reports_its_annual_ceiling_in_miles(snapshot: CatalogSnapshot) -> None:
    """axis-edge-miles caps KrisFlyer transfers at 30,000 EDGE Miles/calendar
    year at 1:2 — i.e. 60,000 KrisFlyer miles, the number the seed note calls
    out and the one that actually bounds an Atlas-only strategy."""
    card = _card(_portfolio(snapshot, ["Atlas"]), "Atlas")
    link = next(link for link in card.transfer_links if link.is_target)
    assert link.max_transfer_points == 30000
    assert link.annual_ceiling_miles == 60000
    assert link.transfer_fee_inr == 235


def test_uncapped_link_has_no_ceiling(snapshot: CatalogSnapshot) -> None:
    card = _card(_portfolio(snapshot, ["Infinia Metal"]), "Infinia Metal")
    link = next(link for link in card.transfer_links if link.is_target)
    assert link.max_transfer_points is None
    assert link.annual_ceiling_miles is None


def test_target_link_leads_the_card_and_the_rest_are_alphabetical(
    snapshot: CatalogSnapshot,
) -> None:
    card = _card(_portfolio(snapshot, ["Infinia Metal"]), "Infinia Metal")
    assert card.transfer_links[0].is_target is True
    assert card.transfer_links[0].program_name == "KrisFlyer"
    others = [link.program_name for link in card.transfer_links[1:]]
    assert others == sorted(others)
    assert all(link.is_target is False for link in card.transfer_links[1:])


# ── wallet-level rollups ──────────────────────────────────────────────────


def test_partner_reach_reports_the_best_ratio_across_the_wallet(
    snapshot: CatalogSnapshot,
) -> None:
    """Both cards reach KrisFlyer, at 2:1 (Regalia) and 1:2 (Atlas). The
    wallet's best avenue is Atlas's — 2,000 miles per 1,000 points, against
    Regalia's 500 — and that is the number the user plans around."""
    portfolio = _portfolio(snapshot, ["Regalia Gold", "Atlas"])
    krisflyer = next(p for p in portfolio.partner_reach if p.program_name == "KrisFlyer")

    assert krisflyer.is_target is True
    assert krisflyer.card_ids == (
        _card_id(snapshot, "Regalia Gold"),
        _card_id(snapshot, "Atlas"),
    )
    assert krisflyer.best_miles_per_1000_points == 2000
    assert portfolio.cards_reaching_target == 2


def test_partner_reach_puts_the_target_first(snapshot: CatalogSnapshot) -> None:
    portfolio = _portfolio(snapshot, ["Infinia Metal"])
    assert portfolio.partner_reach[0].program_name == "KrisFlyer"
    rest = [p.program_name for p in portfolio.partner_reach[1:]]
    assert rest == sorted(rest)


def test_fee_totals_sum_the_wallet(snapshot: CatalogSnapshot) -> None:
    # Infinia ₹12,500 annual / ₹12,500 joining; Platinum Travel ₹5,000 / ₹5,000
    # (Amex first-year fee is now ₹5,000) → joining 12,500 + 5,000 = 17,500
    portfolio = _portfolio(snapshot, ["Infinia Metal", "Platinum Travel"])
    assert portfolio.total_annual_fees_inr == 17500
    assert portfolio.total_joining_fees_inr == 17500


def test_duplicate_card_ids_collapse_and_are_counted_once(snapshot: CatalogSnapshot) -> None:
    portfolio = _portfolio(snapshot, ["Infinia Metal", "Infinia Metal"])
    assert len(portfolio.cards) == 1
    assert portfolio.total_annual_fees_inr == 12500


def test_cards_keep_wallet_order(snapshot: CatalogSnapshot) -> None:
    names = ["TravelOne", "Infinia Metal", "Atlas"]
    assert [c.card_name for c in _portfolio(snapshot, names).cards] == names


def test_same_wallet_produces_an_identical_portfolio(snapshot: CatalogSnapshot) -> None:
    """Determinism is a standing test (build rule 8)."""
    names = ["Infinia Metal", "Atlas", "Cashback"]
    assert _portfolio(snapshot, names) == _portfolio(snapshot, names)


def test_snapshot_version_is_carried(snapshot: CatalogSnapshot) -> None:
    portfolio = _portfolio(snapshot, ["Infinia Metal"])
    assert portfolio.catalog_snapshot_version == snapshot.version
    assert portfolio.target_program_name == "KrisFlyer"


# ── failure modes ─────────────────────────────────────────────────────────


def test_unknown_card_fails_loudly(snapshot: CatalogSnapshot) -> None:
    """A stale wallet must not silently lose a card — the answer would look
    complete and be wrong."""
    with pytest.raises(UnknownCard):
        build_portfolio(
            snapshot,
            card_ids=[uuid4()],
            target_program_id=_krisflyer_id(snapshot),
            unverified_ids=frozenset(),
        )


def test_empty_wallet_is_rejected(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(ValueError, match="card_ids"):
        build_portfolio(
            snapshot,
            card_ids=[],
            target_program_id=_krisflyer_id(snapshot),
            unverified_ids=frozenset(),
        )


def test_unknown_target_program_is_rejected(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(ValueError, match="unknown target program"):
        build_portfolio(
            snapshot,
            card_ids=[_card_id(snapshot, "Infinia Metal")],
            target_program_id=uuid4(),
            unverified_ids=frozenset(),
        )


# ── review follow-ups (backend-reviewer, 2026-08-26) ──────────────────────


def test_annual_ceiling_floors_to_whole_transfer_blocks(snapshot: CatalogSnapshot) -> None:
    """The yearly cap bounds a REAL send, so it floors to whole ratio blocks.

    Both capped links in today's catalog happen to cap on an exact multiple
    of `ratio_from`, which makes whole-block and marginal pricing agree — so
    this test builds a link that does not, and pins the conservative answer.
    A 30,001-point cap at 1:2 still clears only 30,000 points (60,000 miles);
    a 5-point cap at 3:2 clears one block, i.e. 2 miles, not 3.
    """
    atlas = _card_id(snapshot, "Atlas")
    axis_currency = next(c.reward_currency_id for c in snapshot.cards if c.id == atlas)
    krisflyer = _krisflyer_id(snapshot)

    def ceiling(ratio_from: int, ratio_to: int, cap: int) -> int | None:
        links = tuple(
            link.model_copy(
                update={"ratio_from": ratio_from, "ratio_to": ratio_to, "max_transfer_points": cap}
            )
            if link.currency_id == axis_currency and link.partner_id == krisflyer
            else link
            for link in snapshot.transfer_links
        )
        patched = snapshot.model_copy(update={"transfer_links": links})
        card = _card(_portfolio(patched, ["Atlas"]), "Atlas")
        return next(link for link in card.transfer_links if link.is_target).annual_ceiling_miles

    assert ceiling(1, 2, 30_001) == 60_002  # 30,001 whole 1-point blocks
    assert ceiling(3, 2, 5) == 2  # one whole block, NOT floor(5 × 2/3) = 3
    assert ceiling(5, 4, 30_001) == 24_000  # 6,000 whole blocks, remainder stranded


def test_milestone_bonus_is_none_when_the_card_cannot_reach_the_target(
    snapshot: CatalogSnapshot,
) -> None:
    """Axis lost its Marriott link in the Apr-2026 devaluation, so Atlas's
    milestones are unreachable in that program — None, never a zero, exactly
    as `miles_per_100` behaves for an unroutable card."""
    marriott = next(p.id for p in snapshot.partners if p.program_name == "Marriott Bonvoy")
    portfolio = build_portfolio(
        snapshot,
        card_ids=[_card_id(snapshot, "Atlas")],
        target_program_id=marriott,
        unverified_ids=frozenset(),
    )
    card = _card(portfolio, "Atlas")

    assert card.reaches_target is False
    assert card.milestones  # the milestones themselves are still reported
    assert all(milestone.bonus_miles is None for milestone in card.milestones)
    assert all(rule.miles_per_100 is None for rule in card.earn_rules)


def test_category_label_comes_from_the_strongest_claim_not_the_wallet_order(
    snapshot: CatalogSnapshot,
) -> None:
    """Infinia and Atlas both accelerate travel under different names. The
    category takes the name of the card with the strongest claim to it — not
    whichever card the caller happened to list first, which would make the
    same wallet render two different labels."""
    forward = _category(_portfolio(snapshot, ["Atlas", "Infinia Metal"]), SpendCategory.TRAVEL)
    reverse = _category(_portfolio(snapshot, ["Infinia Metal", "Atlas"]), SpendCategory.TRAVEL)

    assert forward.category_label == "Travel via SmartBuy portal"  # Infinia, 16.65
    assert reverse.category_label == forward.category_label


def test_category_label_ignores_cards_with_no_rule_for_it(snapshot: CatalogSnapshot) -> None:
    """Regalia Gold has no travel rule, so it falls back to "All other retail spend"
    in the travel row — but it must not lend that name to the category."""
    travel = _category(_portfolio(snapshot, ["Regalia Gold", "Atlas"]), SpendCategory.TRAVEL)
    assert travel.category_label == "Travel EDGE portal, direct airlines and direct hotels"


def test_catalog_fields_pass_through_untouched(snapshot: CatalogSnapshot) -> None:
    """These are pure pass-throughs with no arithmetic, but they are what the
    UI renders — pin them so a refactor cannot quietly drop one."""
    card = _card(_portfolio(snapshot, ["Atlas"]), "Atlas")
    assert card.card_network == "Visa"
    assert card.has_lounge_access is True
    assert card.acquirable is False  # discontinued for new applicants
    assert card.currency_name == "EDGE Miles"
    assert card.currency_expiry_rules == "No expiry while card is active"
    assert card.joining_fee_inr == 5000

    infinia = _card(_portfolio(snapshot, ["Infinia Metal"]), "Infinia Metal")
    travel = _rule(infinia, SpendCategory.TRAVEL)
    assert travel.monthly_cap_inr == 112500
    assert travel.quarterly_cap_inr is None
    assert travel.annual_cap_inr is None
    assert travel.notes is not None and "SmartBuy" in travel.notes


def test_earn_rules_state_what_spend_past_a_cap_earns(snapshot: CatalogSnapshot) -> None:
    """A cap is half a fact without its overflow (decision log
    2026-11-02-cap-overflow-earn): SBI online and offline earn NOTHING past
    their ₹2,000-cashback caps; Atlas travel falls to its base rate; an
    uncapped rule carries no overflow value at all."""
    from app.domain import OverCapEarn

    portfolio = _portfolio(snapshot, ["Cashback", "Atlas"])
    sbi, atlas = _card(portfolio, "Cashback"), _card(portfolio, "Atlas")
    assert _rule(sbi, SpendCategory.ONLINE).over_cap_earn == OverCapEarn.NOTHING
    assert _rule(sbi, SpendCategory.DEFAULT).over_cap_earn == OverCapEarn.NOTHING
    assert _rule(sbi, SpendCategory.DEFAULT).monthly_cap_inr == 200_000  # ₹2,000 ÷ 1%
    assert _rule(atlas, SpendCategory.TRAVEL).over_cap_earn == OverCapEarn.BASE_RATE
    assert _rule(atlas, SpendCategory.DEFAULT).over_cap_earn is None
