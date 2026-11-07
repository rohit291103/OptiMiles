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
    FeeWaiver,
    LoungeAccess,
    LoungeProgram,
    RewardCategoryRule,
    RewardCurrency,
    RewardMilestone,
    TransferPartner,
)
from app.knowledge.versioning import content_version

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "optimiles.catalog")

# Provenance/authoring keys stripped before hydrating domain models.
# `over_cap_earn_source` is provenance for one field of a capped category rule
# (decision log 2026-11-02-cap-overflow-earn) — reviewed in YAML, never data.
_META_KEYS = frozenset(
    {"source", "verified_on", "needs_verification", "slug", "over_cap_earn_source"}
)


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

    # Lounge programmes are their own file — several cards ride the same one,
    # and a programme goes stale independently of any card (issuers switch
    # vendors mid-year), so it is not card-nested data.
    lounge_programs = tuple(
        LoungeProgram(id=seed_id("lounge_program", row["slug"]), **_fields(row))
        for row in _rows(seed_dir / "lounge_programs.yaml")
    )

    cards: list[Card] = []
    category_rules: list[RewardCategoryRule] = []
    milestones: list[RewardMilestone] = []
    lounge_access: list[LoungeAccess] = []
    fee_waivers: list[FeeWaiver] = []
    for row in _rows(seed_dir / "cards.yaml"):
        card_slug = str(row["slug"])
        card_id = seed_id("card", card_slug)
        cards.append(
            Card(
                id=card_id,
                reward_currency_id=seed_id("currency", row["currency"]),
                **_fields(
                    row,
                    extra_drop=frozenset(
                        {"currency", "categories", "milestones", "lounge_access", "fee_waiver"}
                    ),
                ),
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

        # Coverage is deliberately partial: a card with no block here is "not
        # covered yet", which the read surface must state rather than report
        # as an absence of lounge access.
        for index, access in enumerate(row.get("lounge_access", [])):
            lounge_access.append(
                LoungeAccess(
                    id=seed_id("lounge_access", f"{card_slug}:{index}"),
                    card_id=card_id,
                    program_id=seed_id("lounge_program", access["program"]),
                    **_fields(access, extra_drop=frozenset({"program"})),
                )
            )

        # One block per card at most. No block = "not covered yet", which is a
        # different answer from a sourced `kind: none` block.
        waiver = row.get("fee_waiver")
        if waiver is not None:
            fee_waivers.append(
                FeeWaiver(
                    id=seed_id("fee_waiver", card_slug),
                    card_id=card_id,
                    **_fields(waiver),
                )
            )

    award_charts = tuple(
        AwardChartEntry(
            id=seed_id("award_chart", _award_chart_key(row)),
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
                list(lounge_programs),
                lounge_access,
                fee_waivers,
            ]
        ),
        currencies=currencies,
        partners=partners,
        transfer_links=transfer_links,
        cards=tuple(cards),
        category_rules=tuple(category_rules),
        milestones=tuple(milestones),
        award_charts=award_charts,
        lounge_programs=lounge_programs,
        lounge_access=tuple(lounge_access),
        fee_waivers=tuple(fee_waivers),
    )


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _award_chart_key(row: dict[str, Any]) -> str:
    """The award-chart slug — shared by the snapshot and the provenance index."""
    return ":".join(
        [
            str(row["partner"]),
            _slugify(str(row["origin_region"])),
            _slugify(str(row["destination_region"])),
            str(row["cabin_class"]),
            str(row["award_type"]),
        ]
    )


def load_unverified_ids(seed_dir: Path) -> frozenset[uuid.UUID]:
    """Ids of every seeded row still flagged `needs_verification: true`.

    The Listed tier (CLAUDE.md → *Scope: Breadth With Depth*). Provenance stays
    in the reviewed YAML, never the DB (seeds/README), so a read surface that
    must label a row "unverified" asks here, by the same deterministic id the
    snapshot gives that row — whether the snapshot came from these files or the
    database.

    Flags never inherit: a card-level flag covers the card row's own facts
    (fee, base rate), not its separately reviewed categories or milestones, and
    a flagged child does not flag its card. Each key below MUST mirror the one
    `load_seed_snapshot` uses for the same kind; the drift guards in
    tests/unit/knowledge/test_provenance.py hold that.
    """
    flagged: set[uuid.UUID] = set()

    def note(row: dict[str, Any], kind: str, key: str) -> None:
        # Fail closed: only a real YAML boolean is a flag. A quoted "true" (or
        # a bare `needs_verification:`) read as "not flagged" would publish an
        # unreviewed row as verified.
        if "needs_verification" not in row:
            return
        value = row["needs_verification"]
        if not isinstance(value, bool):
            raise ValueError(
                f"{kind} {key!r}: needs_verification must be true or false, got {value!r}"
            )
        if value:
            flagged.add(seed_id(kind, key))

    for name, kind in (
        ("currencies.yaml", "currency"),
        ("partners.yaml", "partner"),
        ("lounge_programs.yaml", "lounge_program"),
    ):
        for row in _rows(seed_dir / name):
            note(row, kind, str(row["slug"]))
    for row in _rows(seed_dir / "transfer_links.yaml"):
        note(row, "transfer_link", f"{row['currency']}:{row['partner']}")
    for row in _rows(seed_dir / "cards.yaml"):
        card_slug = str(row["slug"])
        note(row, "card", card_slug)
        for category in row.get("categories", []):
            note(category, "category", f"{card_slug}:{category['category_slug']}")
        for index, milestone in enumerate(row.get("milestones", [])):
            note(milestone, "milestone", f"{card_slug}:{index}")
        for index, access in enumerate(row.get("lounge_access", [])):
            note(access, "lounge_access", f"{card_slug}:{index}")
        if row.get("fee_waiver") is not None:
            note(row["fee_waiver"], "fee_waiver", card_slug)
    for row in _rows(seed_dir / "award_charts.yaml"):
        note(row, "award_chart", _award_chart_key(row))
    return frozenset(flagged)


# Every CatalogSnapshot row collection the index above walks. A guard test
# fails if the snapshot gains a collection missing here — rows in it would
# otherwise read as verified by omission.
PROVENANCE_COLLECTIONS: frozenset[str] = frozenset(
    {
        "currencies",
        "partners",
        "transfer_links",
        "lounge_programs",
        "cards",
        "category_rules",
        "milestones",
        "lounge_access",
        "award_charts",
        "fee_waivers",
    }
)


def snapshot_row_ids(snapshot: CatalogSnapshot) -> frozenset[uuid.UUID]:
    """Every row id in the snapshot's provenance-covered collections."""
    return frozenset(
        row.id for name in sorted(PROVENANCE_COLLECTIONS) for row in getattr(snapshot, name)
    )


def provenance_drift(
    snapshot: CatalogSnapshot, unverified_ids: frozenset[uuid.UUID]
) -> frozenset[uuid.UUID]:
    """Flagged ids with no row in `snapshot` — YAML/DB drift.

    Non-empty means the DB was loaded from different seeds than the ones on
    disk, so some flagged row is not where its label expects it.
    """
    return unverified_ids - snapshot_row_ids(snapshot)
