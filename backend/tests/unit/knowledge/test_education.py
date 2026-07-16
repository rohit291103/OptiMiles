"""Wallet education read-shape (knowledge/education.py) — guided-flow slice 2.

Decision 4 (decision log 2026-07-13): wallet card ids in → the wallet's reward
story out — per card its currency, earn rules (portal/category-accelerated
rates included), transfer links with ratio/cap/fee, plus partners shared across
the wallet. A pure reshape of the catalog snapshot: no pipeline run, no LLM.

Goldens are traced line-for-line to `seeds/catalog/*.yaml` (the canonical
example from the design doc: Atlas & TravelOne both reach KrisFlyer — Atlas at
1:2 capped 30k/yr + ₹235 fee, TravelOne at 1:1 uncapped).
"""

from decimal import Decimal

import pytest

from app.domain import CatalogSnapshot
from app.knowledge.education import UnknownCardId, wallet_education
from app.knowledge.seed_catalog import seed_id

ATLAS = seed_id("card", "axis-atlas")
TRAVELONE = seed_id("card", "hsbc-travelone")
SBI_CASHBACK = seed_id("card", "sbi-cashback")
KRISFLYER = seed_id("partner", "krisflyer")


def test_atlas_and_travelone_reward_story(snapshot: CatalogSnapshot) -> None:
    """The design doc's canonical wallet, checked against the seed rows."""
    payload = wallet_education(snapshot, (ATLAS, TRAVELONE))

    assert payload.catalog_snapshot_version == snapshot.version
    assert [c.card_id for c in payload.cards] == [ATLAS, TRAVELONE]

    atlas, travelone = payload.cards

    # Atlas — EDGE Miles, travel accelerated to 5/₹100 capped ₹2L/month.
    assert atlas.card_name == "Atlas"
    assert atlas.bank == "Axis"
    assert atlas.currency.currency_name == "EDGE Miles"
    assert atlas.base_earn_rate == Decimal("2.00")
    travel_rule = next(r for r in atlas.earn_rules if r.category_slug == "travel")
    assert travel_rule.earn_rate == Decimal("5.00")
    assert travel_rule.monthly_cap_inr == 200_000
    assert travel_rule.category_label == "Direct airlines, hotels and travel"

    # Atlas → KrisFlyer: 1:2, 30k EDGE Miles/yr cap, ₹235 fee (seed row).
    assert len(atlas.transfer_links) == 1
    atlas_kf = atlas.transfer_links[0]
    assert atlas_kf.partner_id == KRISFLYER
    assert atlas_kf.program_name == "KrisFlyer"
    assert (atlas_kf.ratio_from, atlas_kf.ratio_to) == (1, 2)
    assert atlas_kf.max_transfer_points == 30_000
    assert atlas_kf.transfer_fee_inr == 235

    # TravelOne — HSBC Reward Points, travel at 4/₹100 uncapped, 1:1 links to
    # KrisFlyer + Bonvoy + Accor (3 links, sorted by program name).
    assert travelone.currency.currency_name == "HSBC Reward Points"
    assert travelone.base_earn_rate == Decimal("2.00")
    t1_travel = next(r for r in travelone.earn_rules if r.category_slug == "travel")
    assert t1_travel.earn_rate == Decimal("4.00")
    assert t1_travel.monthly_cap_inr is None
    assert [link.program_name for link in travelone.transfer_links] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Marriott Bonvoy",
    ]
    t1_kf = next(
        link for link in travelone.transfer_links if link.partner_id == KRISFLYER
    )
    assert (t1_kf.ratio_from, t1_kf.ratio_to) == (1, 1)
    assert t1_kf.max_transfer_points is None
    assert t1_kf.transfer_fee_inr == 0

    # The shared-ecosystem insight: both cards reach KrisFlyer, nothing else.
    assert len(payload.shared_partners) == 1
    shared = payload.shared_partners[0]
    assert shared.partner_id == KRISFLYER
    assert shared.program_name == "KrisFlyer"
    assert shared.card_ids == (ATLAS, TRAVELONE)


def test_single_card_has_no_shared_partners(snapshot: CatalogSnapshot) -> None:
    """'Shared' means reachable from ≥2 wallet cards — one card shares nothing."""
    payload = wallet_education(snapshot, (TRAVELONE,))
    assert payload.shared_partners == ()
    assert len(payload.cards) == 1


def test_cashback_card_has_no_transfer_links(snapshot: CatalogSnapshot) -> None:
    """SBI Cashback's currency has no transfer links by construction — the
    education payload states that honestly rather than omitting the card."""
    payload = wallet_education(snapshot, (SBI_CASHBACK,))
    assert payload.cards[0].transfer_links == ()


def test_duplicate_ids_dedupe_to_first_occurrence(snapshot: CatalogSnapshot) -> None:
    payload = wallet_education(snapshot, (ATLAS, TRAVELONE, ATLAS))
    assert [c.card_id for c in payload.cards] == [ATLAS, TRAVELONE]


def test_unknown_card_id_fails_loud(snapshot: CatalogSnapshot) -> None:
    from uuid import uuid4

    bogus = uuid4()
    with pytest.raises(UnknownCardId):
        wallet_education(snapshot, (ATLAS, bogus))


def test_education_is_deterministic(snapshot: CatalogSnapshot) -> None:
    """Same wallet + same snapshot ⇒ identical payload (build rule 8 applies
    to reads shaped for the wizard too)."""
    a = wallet_education(snapshot, (ATLAS, TRAVELONE))
    b = wallet_education(snapshot, (ATLAS, TRAVELONE))
    assert a == b
