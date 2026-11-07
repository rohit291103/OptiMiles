"""Portfolio View — which rows are Listed-tier, and the join key for progress.

Two additions that let `/cards` show logged progress honestly:

  * `needs_verification` on every row the page renders, so a figure seeded
    from `needs_verification: true` data is labelled unverified (CLAUDE.md →
    tiered coverage: "the UI must say it is unverified");
  * `milestone_id`, so the client can attach `/v1/activity/summary`'s
    `MilestoneProgress` rows to the milestone they measure without matching on
    thresholds (two milestones can share one).

The unverified set is passed explicitly rather than read from the YAML, so
these goldens pin the engine's attribution logic and do not move when the seed
review queue does. Which real rows are flagged is
tests/unit/knowledge/test_provenance.py's concern.
"""

from uuid import UUID

from app.domain import CatalogSnapshot, LoungeScope, SpendCategory
from app.knowledge.seed_catalog import seed_id
from app.valuation.portfolio import WalletPortfolio, build_portfolio

INFINIA = seed_id("card", "hdfc-infinia")
REGALIA = seed_id("card", "hdfc-regalia-gold")
TRAVELONE = seed_id("card", "hsbc-travelone")
ATLAS = seed_id("card", "axis-atlas")
SBI = seed_id("card", "sbi-cashback")


def _build(snapshot: CatalogSnapshot, cards: list[UUID], unverified: set[UUID]) -> WalletPortfolio:
    return build_portfolio(snapshot, card_ids=cards, unverified_ids=frozenset(unverified))


def _card(portfolio: WalletPortfolio, card_id: UUID):
    return next(c for c in portfolio.cards if c.card_id == card_id)


def test_nothing_is_flagged_when_nothing_is_unverified(snapshot: CatalogSnapshot) -> None:
    portfolio = _build(snapshot, [INFINIA, ATLAS, SBI], set())
    for card in portfolio.cards:
        assert card.needs_verification is False
        assert not any(rule.needs_verification for rule in card.earn_rules)
        assert not any(m.needs_verification for m in card.milestones)
        assert not any(link.needs_verification for link in card.transfer_links)
        assert not any(access.needs_verification for access in card.lounge_access)
    assert not any(row.needs_verification for c in portfolio.categories for row in c.rows)


def test_an_earn_rule_is_flagged_by_its_own_row_only(snapshot: CatalogSnapshot) -> None:
    """Infinia's travel rule (the ₹1,50,000/month SmartBuy cap) flagged; its
    default rule is a separately reviewed row and stays verified."""
    portfolio = _build(snapshot, [INFINIA], {seed_id("category", "hdfc-infinia:travel")})
    rules = {rule.category_slug: rule for rule in _card(portfolio, INFINIA).earn_rules}
    assert rules[SpendCategory.TRAVEL].needs_verification is True
    assert rules[SpendCategory.DEFAULT].needs_verification is False
    assert _card(portfolio, INFINIA).needs_verification is False


def test_card_header_is_flagged_by_the_card_row_or_its_currency(
    snapshot: CatalogSnapshot,
) -> None:
    """The panel header states the fee, base rate and the currency's expiry
    rules — facts from the card row AND the currency row."""
    by_currency = _build(snapshot, [INFINIA, REGALIA], {seed_id("currency", "hdfc-rp-regalia")})
    assert _card(by_currency, REGALIA).needs_verification is True
    assert _card(by_currency, INFINIA).needs_verification is False  # hdfc-rp-premium

    by_card = _build(snapshot, [INFINIA, ATLAS], {ATLAS})
    assert _card(by_card, ATLAS).needs_verification is True
    assert _card(by_card, INFINIA).needs_verification is False


def test_milestones_carry_their_snapshot_id_in_display_order(
    snapshot: CatalogSnapshot,
) -> None:
    """Atlas seeds four milestones: [0] ₹3L annual, [1] one-time welcome,
    [2] ₹7.5L annual, [3] ₹15L annual. Display order is threshold-free first,
    then ascending threshold — so ids come out 1, 0, 2, 3."""
    flagged = seed_id("milestone", "axis-atlas:2")
    milestones = _card(_build(snapshot, [ATLAS], {flagged}), ATLAS).milestones
    assert [m.milestone_id for m in milestones] == [
        seed_id("milestone", "axis-atlas:1"),
        seed_id("milestone", "axis-atlas:0"),
        seed_id("milestone", "axis-atlas:2"),
        seed_id("milestone", "axis-atlas:3"),
    ]
    assert [m.spend_threshold_inr for m in milestones] == [None, 300_000, 750_000, 1_500_000]
    assert [m.needs_verification for m in milestones] == [False, False, True, False]


def test_milestone_ids_are_the_ones_activity_progress_reports(
    snapshot: CatalogSnapshot,
) -> None:
    """The join key must be the same id `simulation/observed.py` stamps on
    `MilestoneProgress.milestone_id` — the snapshot's own milestone id."""
    seeded = {m.id for m in snapshot.milestones if m.card_id == ATLAS}
    shown = {m.milestone_id for m in _card(_build(snapshot, [ATLAS], set()), ATLAS).milestones}
    assert shown == seeded


def test_a_transfer_link_is_flagged_by_its_link_row(snapshot: CatalogSnapshot) -> None:
    portfolio = _build(
        snapshot, [TRAVELONE], {seed_id("transfer_link", "hsbc-reward-points:marriott-bonvoy")}
    )
    flags = {
        link.program_name: link.needs_verification
        for link in _card(portfolio, TRAVELONE).transfer_links
    }
    assert flags["Marriott Bonvoy"] is True
    assert flags["KrisFlyer"] is False


def test_lounge_access_is_flagged_by_its_row_or_its_programme(
    snapshot: CatalogSnapshot,
) -> None:
    """Infinia: [0] issuer-direct domestic, [1] Priority Pass international.
    A flagged programme taints every tier that rides on it; a flagged access
    row taints only itself."""
    by_program = _build(snapshot, [INFINIA], {seed_id("lounge_program", "priority-pass")})
    flags = {a.scope: a.needs_verification for a in _card(by_program, INFINIA).lounge_access}
    assert flags == {LoungeScope.DOMESTIC: False, LoungeScope.INTERNATIONAL: True}

    by_row = _build(snapshot, [INFINIA], {seed_id("lounge_access", "hdfc-infinia:0")})
    flags = {a.scope: a.needs_verification for a in _card(by_row, INFINIA).lounge_access}
    assert flags == {LoungeScope.DOMESTIC: True, LoungeScope.INTERNATIONAL: False}


def test_category_cells_follow_the_row_that_supplied_the_rate(
    snapshot: CatalogSnapshot,
) -> None:
    """SBI has an `online` rule; Infinia does not, so Infinia's online cell is
    its BASE rate — a card-row fact. Flagging the Infinia card row therefore
    flags that fallback cell, and flagging SBI's online rule flags SBI's."""
    portfolio = _build(
        snapshot, [SBI, INFINIA], {INFINIA, seed_id("category", "sbi-cashback:online")}
    )
    online = next(c for c in portfolio.categories if c.category_slug == SpendCategory.ONLINE)
    flags = {row.card_id: row.needs_verification for row in online.rows}
    assert flags == {SBI: True, INFINIA: True}

    default = next(c for c in portfolio.categories if c.category_slug == SpendCategory.DEFAULT)
    # Both cards seed their own default rule, so the card-row flag does NOT
    # reach this row: the rate came from the (unflagged) default rule.
    assert {row.card_id: row.needs_verification for row in default.rows} == {
        SBI: False,
        INFINIA: False,
    }


# ── Derived values inherit the flags of everything they are derived from ──
#
# A miles figure is earn_rate × ratio_to / ratio_from: the rate comes from the
# category rule (or card row), the ratio from the transfer link, and the link
# belongs to the currency. A verified rate times an unverified ratio is an
# unverified number. With no programme chosen there is no derived figure, so
# nothing upstream of the rate can taint it.

KRISFLYER = seed_id("partner", "krisflyer")
ATLAS_KF = seed_id("transfer_link", "axis-edge-miles:krisflyer")  # 1:2
TRAVELONE_KF = seed_id("transfer_link", "hsbc-reward-points:krisflyer")  # 1:1


def _priced(snapshot: CatalogSnapshot, cards: list[UUID], unverified: set[UUID]) -> WalletPortfolio:
    return build_portfolio(
        snapshot,
        card_ids=cards,
        target_program_id=KRISFLYER,
        unverified_ids=frozenset(unverified),
    )


def _category(portfolio: WalletPortfolio, slug: SpendCategory):
    return next(c for c in portfolio.categories if c.category_slug == slug)


def test_a_flagged_link_taints_every_miles_figure_it_prices(snapshot: CatalogSnapshot) -> None:
    portfolio = _priced(snapshot, [INFINIA, ATLAS], {ATLAS_KF})
    atlas = _card(portfolio, ATLAS)
    # Atlas's own rules and milestones are verified rows; their miles are not.
    assert [r.needs_verification for r in atlas.earn_rules] == [True, True]
    assert all(m.bonus_miles is not None for m in atlas.milestones)
    assert [m.needs_verification for m in atlas.milestones] == [True, True, True, True]
    travel = _category(portfolio, SpendCategory.TRAVEL)
    assert {row.card_id: row.needs_verification for row in travel.rows} == {
        INFINIA: False,  # hdfc-rp-premium → KrisFlyer link is not flagged
        ATLAS: True,
    }
    # Infinia's own figures are untouched by another card's link.
    assert not any(r.needs_verification for r in _card(portfolio, INFINIA).earn_rules)


def test_without_a_programme_a_flagged_link_taints_no_rate(snapshot: CatalogSnapshot) -> None:
    portfolio = _build(snapshot, [ATLAS], {ATLAS_KF})
    atlas = _card(portfolio, ATLAS)
    assert all(r.miles_per_100 is None for r in atlas.earn_rules)
    assert not any(r.needs_verification for r in atlas.earn_rules)
    assert not any(m.needs_verification for m in atlas.milestones)
    # The link itself is still shown, and still labelled.
    assert [link.needs_verification for link in atlas.transfer_links] == [True]


def test_a_flagged_currency_taints_its_priced_figures(snapshot: CatalogSnapshot) -> None:
    hdfc_premium = seed_id("currency", "hdfc-rp-premium")
    priced = _card(_priced(snapshot, [INFINIA], {hdfc_premium}), INFINIA)
    assert [r.needs_verification for r in priced.earn_rules] == [True, True]
    unpriced = _card(_build(snapshot, [INFINIA], {hdfc_premium}), INFINIA)
    assert [r.needs_verification for r in unpriced.earn_rules] == [False, False]
    assert unpriced.needs_verification is True  # the header states the currency


def test_a_flagged_partner_taints_every_link_into_it(snapshot: CatalogSnapshot) -> None:
    portfolio = _build(snapshot, [TRAVELONE], {KRISFLYER})
    flags = {
        link.program_name: link.needs_verification
        for link in _card(portfolio, TRAVELONE).transfer_links
    }
    assert flags == {
        "ALL - Accor Live Limitless": False,
        "KrisFlyer": True,
        "Marriott Bonvoy": False,
    }


def test_partner_reach_is_flagged_by_any_contributing_link_or_the_partner(
    snapshot: CatalogSnapshot,
) -> None:
    by_link = _build(snapshot, [INFINIA, TRAVELONE], {TRAVELONE_KF})
    assert {r.program_name: r.needs_verification for r in by_link.partner_reach} == {
        "ALL - Accor Live Limitless": False,
        "KrisFlyer": True,  # Infinia's route is verified; TravelOne's is not
        "Maharaja Club": False,
        "Marriott Bonvoy": False,
    }
    by_partner = _build(snapshot, [TRAVELONE], {seed_id("partner", "marriott-bonvoy")})
    assert {r.program_name: r.needs_verification for r in by_partner.partner_reach} == {
        "ALL - Accor Live Limitless": False,
        "KrisFlyer": False,
        "Marriott Bonvoy": True,
    }


# ── "Which card wins" is never decided by an unverified row ───────────────


def test_an_unverified_would_be_winner_withholds_the_leader(snapshot: CatalogSnapshot) -> None:
    """Default category, KrisFlyer miles/₹100: Infinia 3.33 × 1/1 = 3.33,
    Atlas 2.00 × 2/1 = 4.00. Atlas would win — but its link is flagged, so
    there is no verified leader. Crowning Infinia instead would highlight the
    smaller number beside a larger one and call it the winner."""
    default = _category(_priced(snapshot, [INFINIA, ATLAS], {ATLAS_KF}), SpendCategory.DEFAULT)
    assert default.leader_card_id is None
    assert default.leader_withheld_unverified is True


def test_a_verified_winner_still_leads_over_a_flagged_runner_up(
    snapshot: CatalogSnapshot,
) -> None:
    """Travel: Infinia 16.65 × 1/1 = 16.65 beats Atlas 5.00 × 2/1 = 10.00.
    The flagged row loses on its own (unverified) number, so the verified
    winner's lead does not rest on it being right."""
    travel = _category(_priced(snapshot, [INFINIA, ATLAS], {ATLAS_KF}), SpendCategory.TRAVEL)
    assert travel.leader_card_id == INFINIA
    assert travel.leader_withheld_unverified is False


def test_nothing_is_withheld_when_there_is_nothing_to_rank(snapshot: CatalogSnapshot) -> None:
    for category in _build(snapshot, [INFINIA, ATLAS], {ATLAS_KF}).categories:
        assert category.leader_card_id is None
        assert category.leader_withheld_unverified is False
