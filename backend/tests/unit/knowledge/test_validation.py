"""validate_catalog() invariants (build plan §6). Bad reference data must fail
loudly at load time — never become silent zeros downstream."""

import pytest

from app.domain import CatalogSnapshot, CurrencyTransferLink, SpendCategory
from app.knowledge.seed_catalog import seed_id
from app.knowledge.validation import CatalogValidationError, validate_catalog


def test_real_seeds_pass_validation(snapshot: CatalogSnapshot) -> None:
    """Phase 1 exit criterion — runs in CI on every change."""
    validate_catalog(snapshot)  # must not raise


def _link(currency_slug: str, partner_slug: str, **overrides: object) -> CurrencyTransferLink:
    values: dict[str, object] = {
        "id": seed_id("transfer_link", f"{currency_slug}:{partner_slug}"),
        "currency_id": seed_id("currency", currency_slug),
        "partner_id": seed_id("partner", partner_slug),
        "ratio_from": 1,
        "ratio_to": 1,
        "min_transfer_points": 1000,
        "transfer_fee_inr": 0,
        "processing_days_min": 1,
        "processing_days_max": 5,
    }
    values.update(overrides)
    return CurrencyTransferLink.model_validate(values)


def test_rejects_card_without_default_category(snapshot: CatalogSnapshot) -> None:
    infinia = seed_id("card", "hdfc-infinia")
    broken = snapshot.model_copy(
        update={
            "category_rules": tuple(
                rule
                for rule in snapshot.category_rules
                if not (rule.card_id == infinia and rule.category_slug == SpendCategory.DEFAULT)
            )
        }
    )
    with pytest.raises(CatalogValidationError, match="default"):
        validate_catalog(broken)


def test_rejects_sbi_cashback_with_a_transfer_link(snapshot: CatalogSnapshot) -> None:
    """The negative case is an enforced invariant, not a convention."""
    broken = snapshot.model_copy(
        update={
            "transfer_links": (*snapshot.transfer_links, _link("sbi-cashback-inr", "krisflyer"))
        }
    )
    with pytest.raises(CatalogValidationError, match=r"[Cc]ashback"):
        validate_catalog(broken)


def test_rejects_ratio_outside_sane_bounds(snapshot: CatalogSnapshot) -> None:
    """Sane bounds 1:4 … 5:1 (build plan §6): a 10:1 ratio is a typo, not a fact."""
    links = tuple(
        li.model_copy(update={"ratio_from": 10, "ratio_to": 1})
        if li.currency_id == seed_id("currency", "amex-mr")
        else li
        for li in snapshot.transfer_links
    )
    with pytest.raises(CatalogValidationError, match="ratio"):
        validate_catalog(snapshot.model_copy(update={"transfer_links": links}))


def test_rejects_missing_mvp_route_coverage(snapshot: CatalogSnapshot) -> None:
    """KrisFlyer chart must cover India → {Southeast Asia, Europe, North America}
    × business (the 3 MVP routes)."""
    charts = tuple(
        chart
        for chart in snapshot.award_charts
        if not (chart.destination_region == "Europe" and chart.cabin_class == "business")
    )
    with pytest.raises(CatalogValidationError, match="Europe"):
        validate_catalog(snapshot.model_copy(update={"award_charts": charts}))


def test_rejects_orphan_foreign_keys(snapshot: CatalogSnapshot) -> None:
    orphan = _link("ghost-currency", "krisflyer")
    with pytest.raises(CatalogValidationError, match="orphan"):
        validate_catalog(snapshot.model_copy(update={"transfer_links": (orphan,)}))


def test_rejects_currency_universe_with_no_krisflyer_reach(snapshot: CatalogSnapshot) -> None:
    """At least one active currency must reach the primary MVP program."""
    krisflyer = seed_id("partner", "krisflyer")
    links = tuple(li for li in snapshot.transfer_links if li.partner_id != krisflyer)
    with pytest.raises(CatalogValidationError, match="KrisFlyer"):
        validate_catalog(snapshot.model_copy(update={"transfer_links": links}))


def test_error_reports_all_issues_at_once(snapshot: CatalogSnapshot) -> None:
    """Loud AND complete: a data fix session shouldn't be whack-a-mole."""
    infinia = seed_id("card", "hdfc-infinia")
    broken = snapshot.model_copy(
        update={
            "category_rules": tuple(
                rule for rule in snapshot.category_rules if rule.card_id != infinia
            ),
            "transfer_links": (
                *snapshot.transfer_links,
                _link("sbi-cashback-inr", "krisflyer"),
            ),
        }
    )
    with pytest.raises(CatalogValidationError) as excinfo:
        validate_catalog(broken)
    assert len(excinfo.value.issues) >= 2


def test_rejects_duplicate_category_slug_per_card(snapshot: CatalogSnapshot) -> None:
    """Mirrors DB uq_card_category: fail loudly at validation, not at insert."""
    duplicate = snapshot.category_rules[0].model_copy(
        update={"id": seed_id("category", "duplicate-row")}
    )
    broken = snapshot.model_copy(update={"category_rules": (*snapshot.category_rules, duplicate)})
    with pytest.raises(CatalogValidationError, match="duplicate category"):
        validate_catalog(broken)


def test_milestone_validity_window_rejected_until_projector_enforces_it(
    snapshot: CatalogSnapshot,
) -> None:
    """BR-05/BR-06 (SIM-001): the v1 projector does not evaluate milestone
    valid_from/valid_until — it has no calendar anchor. Until it does, a seed
    row carrying a validity window must fail catalog validation rather than
    silently influence every projection forever (reviewer finding,
    2026-07-04: Unknown Over Incorrect)."""
    from datetime import date

    expired = snapshot.milestones[0].model_copy(update={"valid_until": date(2025, 12, 31)})
    broken = snapshot.model_copy(update={"milestones": (expired, *snapshot.milestones[1:])})
    with pytest.raises(CatalogValidationError, match="validity window"):
        validate_catalog(broken)
