"""Seed parsing → CatalogSnapshot. The real seeds ARE the fixture: these tests
are the 'seeds pass validation in CI' exit criterion (build plan Phase 1)."""

from decimal import Decimal
from pathlib import Path

import yaml

from app.domain import CatalogSnapshot, SpendCategory
from app.knowledge.seed_catalog import load_seed_snapshot, seed_id

# ── Snapshot shape ────────────────────────────────────────────────────────


def test_loads_full_mvp_catalog(snapshot: CatalogSnapshot) -> None:
    assert len(snapshot.cards) == 9  # 2026-07-04 expansion: +Amex Plat Charge, Magnus→Burgundy
    assert len(snapshot.currencies) == 7
    assert len(snapshot.partners) == 4  # +Marriott Bonvoy, +Accor ALL (hotel)
    assert len(snapshot.transfer_links) == 14  # 6 KrisFlyer + 1 Maharaja + 4 Bonvoy + 3 Accor
    assert len(snapshot.award_charts) == 5
    banks = {card.bank for card in snapshot.cards}
    assert banks == {"HDFC", "HSBC", "Axis", "Amex", "SBI"}


def test_every_card_has_a_default_category(snapshot: CatalogSnapshot) -> None:
    for card in snapshot.cards:
        slugs = {rule.category_slug for rule in snapshot.category_rules if rule.card_id == card.id}
        assert SpendCategory.DEFAULT in slugs, f"{card.card_name} lacks a default category"


def test_ids_are_deterministic_across_loads(seed_dir: Path, snapshot: CatalogSnapshot) -> None:
    """Same seeds ⇒ byte-identical snapshot — the determinism invariant starts here."""
    again = load_seed_snapshot(seed_dir)
    assert again == snapshot
    assert again.version == snapshot.version
    assert seed_id("card", "hdfc-infinia") == seed_id("card", "hdfc-infinia")
    assert seed_id("card", "hdfc-infinia") != seed_id("currency", "hdfc-infinia")


# ── Golden values traceable to the research doc ──────────────────────────


def test_golden_infinia_krisflyer_ratio_is_1_to_1(snapshot: CatalogSnapshot) -> None:
    """Research §1: HDFC Infinia/DCB tier → KrisFlyer at 1:1 (NOT the old 2:1
    example from db-schema-v1 — the research doc supersedes it)."""
    currency_id = seed_id("currency", "hdfc-rp-premium")
    partner_id = seed_id("partner", "krisflyer")
    link = next(
        li
        for li in snapshot.transfer_links
        if li.currency_id == currency_id and li.partner_id == partner_id
    )
    assert (link.ratio_from, link.ratio_to) == (1, 1)


def test_golden_atlas_bottleneck(snapshot: CatalogSnapshot) -> None:
    """Research §2: Atlas 1:2 to KrisFlyer, hard-capped at 30,000 EDGE Miles
    per calendar year ⇒ max 60,000 KrisFlyer miles/year via this link."""
    link = next(
        li
        for li in snapshot.transfer_links
        if li.currency_id == seed_id("currency", "axis-edge-miles")
        and li.partner_id == seed_id("partner", "krisflyer")
    )
    assert (link.ratio_from, link.ratio_to) == (1, 2)
    assert link.max_transfer_points == 30000


def test_golden_amex_mr_ratio_2_to_1(snapshot: CatalogSnapshot) -> None:
    link = next(
        li
        for li in snapshot.transfer_links
        if li.currency_id == seed_id("currency", "amex-mr")
        and li.partner_id == seed_id("partner", "krisflyer")
    )
    assert (link.ratio_from, link.ratio_to) == (2, 1)


def test_golden_dcb_quarterly_milestone(snapshot: CatalogSnapshot) -> None:
    """Research §4: HDFC DCB — 10,000 RP on ₹4L quarterly spend."""
    milestone = next(
        m
        for m in snapshot.milestones
        if m.card_id == seed_id("card", "hdfc-diners-black") and m.milestone_type == "spend_bonus"
    )
    assert milestone.spend_threshold_inr == 400000
    assert milestone.bonus_points == 10000
    assert milestone.period == "quarterly"


def test_golden_infinia_base_rate(snapshot: CatalogSnapshot) -> None:
    card = next(c for c in snapshot.cards if c.id == seed_id("card", "hdfc-infinia"))
    assert card.base_earn_rate == Decimal("3.33")


def test_golden_closed_to_new_applicants(snapshot: CatalogSnapshot) -> None:
    """Three cards are closed to new applicants; Stage 7's one-new-card
    archetype must never recommend acquiring them, but existing holders keep
    full support.
    - Atlas: discontinued for new applicants (catalog-expansion log, 2026-07-04).
    - Amex Platinum Travel + Platinum Charge: Amex India states "We are
      temporarily pausing the acceptance of new card applications in India"
      on both product pages (checked 2026-11-02)."""
    closed = {
        seed_id("card", "axis-atlas"),
        seed_id("card", "amex-platinum-travel"),
        seed_id("card", "amex-platinum-charge"),
    }
    for card in snapshot.cards:
        assert card.acquirable is (card.id not in closed), card.card_name


def test_every_capped_seed_rule_states_its_overflow(snapshot: CatalogSnapshot) -> None:
    """Golden overflow behaviour per capped rule (issuer terms, 2026-11-02):
    SBI online + offline pay NOTHING past ₹2,000 cashback/cycle; Atlas T&C
    pays the 2/₹100 base rate past ₹2L. HDFC SmartBuy and Magnus Travel EDGE
    are base_rate but needs_verification (not issuer-sourced). HSBC
    TravelOne travel (cap added 2026-11-06) pays the 2/₹100 base rate past
    its cap per HSBC's own service guide."""
    from app.domain import OverCapEarn

    expected = {
        "sbi-cashback:online": OverCapEarn.NOTHING,
        "sbi-cashback:default": OverCapEarn.NOTHING,
        "axis-atlas:travel": OverCapEarn.BASE_RATE,
        "hdfc-infinia:travel": OverCapEarn.BASE_RATE,
        "hdfc-diners-black:travel": OverCapEarn.BASE_RATE,
        "axis-magnus-burgundy:travel": OverCapEarn.BASE_RATE,
        "hsbc-travelone:travel": OverCapEarn.BASE_RATE,
    }
    by_id = {seed_id("category", key): value for key, value in expected.items()}
    capped = [
        r
        for r in snapshot.category_rules
        if r.monthly_cap_inr is not None
        or r.quarterly_cap_inr is not None
        or r.annual_cap_inr is not None
    ]
    assert {r.id for r in capped} == set(by_id)
    for rule in capped:
        assert rule.over_cap_earn == by_id[rule.id], rule.category_label
    sbi_offline = next(r for r in capped if r.id == seed_id("category", "sbi-cashback:default"))
    # ₹2,000 max offline cashback per cycle ÷ 1% = ₹2,00,000 of spend.
    assert sbi_offline.monthly_cap_inr == 200_000


def test_sbi_cashback_has_no_transfer_links(snapshot: CatalogSnapshot) -> None:
    """The deliberate negative case (build plan §6)."""
    sbi_currency = seed_id("currency", "sbi-cashback-inr")
    assert not any(li.currency_id == sbi_currency for li in snapshot.transfer_links)


# ── Provenance discipline (build plan §6) ─────────────────────────────────


def test_every_seed_row_carries_source_and_verified_on(seed_dir: Path) -> None:
    def check_rows(rows: list[dict[str, object]], file: str) -> None:
        for row in rows:
            assert row.get("source"), f"{file}: row missing source: {row}"
            assert row.get("verified_on"), f"{file}: missing verified_on"
            for child_key in ("categories", "milestones"):
                children = row.get(child_key)
                if isinstance(children, list):
                    check_rows(children, f"{file}[{child_key}]")

    for path in sorted(seed_dir.glob("*.yaml")):
        rows = yaml.safe_load(path.read_text())
        assert isinstance(rows, list) and rows, f"{path.name} should be a non-empty list"
        check_rows(rows, path.name)


# Issuer domains whose terms may state a cap's overflow behaviour as fact.
_ISSUER_DOMAINS = (
    "sbicard.com",
    "axis.bank.in",
    "axisbank.com",
    "hdfcbank.com",
    "hdfc.bank.in",  # HDFC and HSBC India moved to .bank.in in 2026; the
    "hsbc.co.in",  # old domains now 301 there, and both are the issuer.
    "hsbc.bank.in",
    "americanexpress.com",
)


def _is_issuer_url(value: str) -> bool:
    from urllib.parse import urlparse

    host = urlparse(value.strip()).hostname or ""
    return value.strip().startswith("https://") and any(
        host == domain or host.endswith("." + domain) for domain in _ISSUER_DOMAINS
    )


def test_unsourced_overflow_keeps_its_rule_unverified(seed_dir: Path) -> None:
    """Every capped category rule names where its `over_cap_earn` came from
    in `over_cap_earn_source`: an issuer https URL, or "secondary: …".
    A rule whose overflow is NOT issuer-sourced must stay
    needs_verification: true — breadth never earns the right to state a
    guess as fact (CLAUDE.md, tiered coverage)."""
    cards = yaml.safe_load((seed_dir / "cards.yaml").read_text())
    capped_seen = 0
    for card in cards:
        for rule in card.get("categories", []):
            if not any(
                rule.get(k) is not None
                for k in ("monthly_cap_inr", "quarterly_cap_inr", "annual_cap_inr")
            ):
                assert "over_cap_earn_source" not in rule, (card["slug"], rule["category_slug"])
                continue
            capped_seen += 1
            where = f"{card['slug']}:{rule['category_slug']}"
            source = rule.get("over_cap_earn_source")
            assert isinstance(source, str) and source.strip(), f"{where}: no over_cap_earn_source"
            sourced = not source.strip().lower().startswith("secondary") and _is_issuer_url(source)
            if not sourced:
                assert rule.get("needs_verification") is True, (
                    f"{where}: over_cap_earn is not issuer-sourced ({source!r}) "
                    "but the row is not needs_verification: true"
                )
    assert capped_seen == 7  # the seven capped rules pinned in the golden above


def test_overflow_source_classifier() -> None:
    assert _is_issuer_url("https://www.sbicard.com/sbi-card-en/assets/docs/pdf/x.pdf")
    assert _is_issuer_url("https://www.axis.bank.in/docs/x.pdf")
    assert _is_issuer_url("https://www.hsbc.bank.in/content/dam/x.pdf")
    assert not _is_issuer_url("https://hsbc.bank.in.evil.example/x")
    assert not _is_issuer_url("https://insideflyer.com/posts/hdfc")
    assert not _is_issuer_url("https://www.sbicard.com.evil.example/x")
    assert not _is_issuer_url("http://www.sbicard.com/x")  # not https


def test_version_ignores_decimal_trailing_zeros(snapshot: CatalogSnapshot) -> None:
    """3.33 and 3.330 are the same content — the version hash must agree,
    or a NUMERIC(6,2) DB column could 'change' the catalog version."""
    padded_rules = tuple(
        r.model_copy(update={"earn_rate": Decimal(str(r.earn_rate) + "0")})
        for r in snapshot.category_rules
    )
    padded = snapshot.model_copy(update={"category_rules": padded_rules})
    from app.knowledge.versioning import content_version

    groups = lambda s: [  # noqa: E731
        s.currencies,
        s.partners,
        s.transfer_links,
        s.cards,
        s.category_rules,
        s.milestones,
        s.award_charts,
    ]
    assert content_version(groups(padded)) == content_version(groups(snapshot))


def test_db_read_queries_are_order_deterministic() -> None:
    """Every catalog SELECT in store.py must ORDER BY id — Postgres row order
    is undefined otherwise, and snapshot equality is order-sensitive
    (reviewer finding, 2026-07-04)."""
    from pathlib import Path

    import app.knowledge.store as store

    source = Path(store.__file__).read_text()
    # 10 since migration 0010 added card_fee_waivers.
    assert source.count("WHERE is_active ORDER BY id") == 10


def test_portal_gated_rules_are_exactly_the_issuer_portal_rates(
    snapshot: CatalogSnapshot,
) -> None:
    """Golden: the three bonus rates that only apply when booked through the
    issuer's own portal (HDFC SmartBuy; Axis Travel EDGE). Atlas earns its
    travel rate on direct airline/hotel bookings too, and TravelOne on any
    airline / aggregator MCC — neither is gated."""
    gated = {
        r.id: r.requires_portal for r in snapshot.category_rules if r.requires_portal is not None
    }
    assert gated == {
        seed_id("category", "hdfc-infinia:travel"): "HDFC SmartBuy",
        seed_id("category", "hdfc-diners-black:travel"): "HDFC SmartBuy",
        seed_id("category", "axis-magnus-burgundy:travel"): "Axis Travel EDGE",
    }
