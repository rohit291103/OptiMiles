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


def test_golden_atlas_discontinued_not_acquirable(snapshot: CatalogSnapshot) -> None:
    """Atlas is discontinued for new applicants (2026) — the one non-acquirable
    card. Stage 7's one-new-card archetype must never recommend acquiring it
    (catalog-expansion decision log, 2026-07-04)."""
    atlas = next(c for c in snapshot.cards if c.id == seed_id("card", "axis-atlas"))
    assert atlas.acquirable is False
    for card in snapshot.cards:
        if card.id != atlas.id:
            assert card.acquirable is True, f"{card.card_name} should default acquirable"


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
    assert source.count("WHERE is_active ORDER BY id") == 7
