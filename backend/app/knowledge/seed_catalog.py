"""Seed YAML → CatalogSnapshot.

IDs are deterministic (UUID5 of kind:slug) so the same seeds always produce
the same snapshot, DB upserts are idempotent, and fixtures never drift from
production identities. The snapshot version is a content hash over the domain
objects (see versioning.py) — identical whether the catalog came from these
files or from the database.
"""

import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from app.domain import (
    AwardChartEntry,
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    RewardCategoryRule,
    RewardCurrency,
    RewardMilestone,
    TransferPartner,
)
from app.knowledge.versioning import content_version

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "optimiles.catalog")

# Provenance/authoring keys stripped before hydrating domain models.
_META_KEYS = frozenset({"source", "verified_on", "needs_verification", "slug"})


def seed_id(kind: str, slug: str) -> uuid.UUID:
    """Deterministic identity for a seeded row."""
    return uuid.uuid5(_NAMESPACE, f"{kind}:{slug}")


def _rows(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a top-level list of rows")
    return data


def _fields(row: dict[str, Any], *, extra_drop: frozenset[str] = frozenset()) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in _META_KEYS and k not in extra_drop}


def load_seed_snapshot(seed_dir: Path) -> CatalogSnapshot:
    currencies = tuple(
        RewardCurrency(id=seed_id("currency", row["slug"]), **_fields(row))
        for row in _rows(seed_dir / "currencies.yaml")
    )
    partners = tuple(
        TransferPartner(id=seed_id("partner", row["slug"]), **_fields(row))
        for row in _rows(seed_dir / "partners.yaml")
    )
    transfer_links = tuple(
        CurrencyTransferLink(
            id=seed_id("transfer_link", f"{row['currency']}:{row['partner']}"),
            currency_id=seed_id("currency", row["currency"]),
            partner_id=seed_id("partner", row["partner"]),
            **_fields(row, extra_drop=frozenset({"currency", "partner"})),
        )
        for row in _rows(seed_dir / "transfer_links.yaml")
    )

    cards: list[Card] = []
    category_rules: list[RewardCategoryRule] = []
    milestones: list[RewardMilestone] = []
    for row in _rows(seed_dir / "cards.yaml"):
        card_slug = str(row["slug"])
        card_id = seed_id("card", card_slug)
        cards.append(
            Card(
                id=card_id,
                reward_currency_id=seed_id("currency", row["currency"]),
                **_fields(row, extra_drop=frozenset({"currency", "categories", "milestones"})),
            )
        )
        for category in row.get("categories", []):
            category_rules.append(
                RewardCategoryRule(
                    id=seed_id("category", f"{card_slug}:{category['category_slug']}"),
                    card_id=card_id,
                    **_fields(category),
                )
            )
        for index, milestone in enumerate(row.get("milestones", [])):
            milestones.append(
                RewardMilestone(
                    id=seed_id("milestone", f"{card_slug}:{index}"),
                    card_id=card_id,
                    **_fields(milestone),
                )
            )

    award_charts = tuple(
        AwardChartEntry(
            id=seed_id(
                "award_chart",
                ":".join(
                    [
                        str(row["partner"]),
                        _slugify(str(row["origin_region"])),
                        _slugify(str(row["destination_region"])),
                        str(row["cabin_class"]),
                        str(row["award_type"]),
                    ]
                ),
            ),
            partner_id=seed_id("partner", row["partner"]),
            **_fields(row, extra_drop=frozenset({"partner"})),
        )
        for row in _rows(seed_dir / "award_charts.yaml")
    )

    return CatalogSnapshot(
        version=content_version(
            [
                currencies,
                partners,
                transfer_links,
                cards,
                category_rules,
                milestones,
                list(award_charts),
            ]
        ),
        currencies=currencies,
        partners=partners,
        transfer_links=transfer_links,
        cards=tuple(cards),
        category_rules=tuple(category_rules),
        milestones=tuple(milestones),
        award_charts=award_charts,
    )


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
