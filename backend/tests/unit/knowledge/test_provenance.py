"""Seed provenance → the set of row ids still awaiting verification.

CLAUDE.md's tiered-coverage rule says a Listed-tier row (`needs_verification:
true`) may appear on informational surfaces only if the UI says it is
unverified. The flag lives in the reviewed YAML, never the DB (seeds/README),
so the read surfaces need it keyed by the same deterministic id the snapshot
uses. These tests pin that keying.

The synthetic catalog below is hand-written so each golden is traceable to one
line; the real-seed tests at the bottom are drift guards (every flagged id must
be a real snapshot row, and every flag in the files must be found) rather than
goldens, because the seed review queue changes as rows get verified.
"""

from pathlib import Path
from typing import get_origin

import pytest
import yaml

from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import (
    PROVENANCE_COLLECTIONS,
    load_unverified_ids,
    provenance_drift,
    seed_id,
    snapshot_row_ids,
)


def _write(seed_dir: Path, name: str, rows: list[dict[str, object]]) -> None:
    (seed_dir / name).write_text(yaml.safe_dump(rows, sort_keys=False))


@pytest.fixture
def tiny_catalog(tmp_path: Path) -> Path:
    _write(
        tmp_path,
        "currencies.yaml",
        [
            {"slug": "rp", "needs_verification": True},
            {"slug": "miles"},
        ],
    )
    _write(tmp_path, "partners.yaml", [{"slug": "kf"}, {"slug": "mc", "needs_verification": False}])
    _write(
        tmp_path,
        "transfer_links.yaml",
        [
            {"currency": "rp", "partner": "kf", "needs_verification": True},
            {"currency": "miles", "partner": "kf"},
        ],
    )
    _write(tmp_path, "lounge_programs.yaml", [{"slug": "pp", "needs_verification": True}])
    _write(
        tmp_path,
        "cards.yaml",
        [
            {
                "slug": "alpha",
                "needs_verification": True,
                "categories": [
                    {"category_slug": "default"},
                    {"category_slug": "travel", "needs_verification": True},
                ],
                "milestones": [
                    {"spend_threshold_inr": 100},
                    {"spend_threshold_inr": 200, "needs_verification": True},
                ],
                "lounge_access": [{"program": "pp", "needs_verification": True}],
            },
            {
                "slug": "beta",
                "categories": [{"category_slug": "default", "needs_verification": True}],
            },
        ],
    )
    _write(
        tmp_path,
        "award_charts.yaml",
        [
            {
                "partner": "kf",
                "origin_region": "India",
                "destination_region": "Southeast Asia",
                "cabin_class": "business",
                "award_type": "saver",
                "needs_verification": True,
            }
        ],
    )
    return tmp_path


def test_every_flagged_row_is_found_under_its_snapshot_id(tiny_catalog: Path) -> None:
    """One id per `needs_verification: true` line above — nine of them — keyed
    exactly as `load_seed_snapshot` keys the row."""
    assert load_unverified_ids(tiny_catalog) == frozenset(
        {
            seed_id("currency", "rp"),
            seed_id("transfer_link", "rp:kf"),
            seed_id("lounge_program", "pp"),
            seed_id("card", "alpha"),
            seed_id("category", "alpha:travel"),
            # Milestones are keyed by position, so the SECOND one is index 1.
            seed_id("milestone", "alpha:1"),
            seed_id("lounge_access", "alpha:0"),
            seed_id("category", "beta:default"),
            seed_id("award_chart", "kf:india:southeast-asia:business:saver"),
        }
    )


def test_unflagged_and_explicitly_false_rows_are_not_listed(tiny_catalog: Path) -> None:
    unverified = load_unverified_ids(tiny_catalog)
    assert seed_id("currency", "miles") not in unverified
    assert seed_id("partner", "mc") not in unverified  # needs_verification: false
    # Flags do not inherit in either direction. Alpha's card-level flag covers
    # the card row's own facts (fee, base rate), not its separately reviewed
    # children; beta's flagged default category does not flag the card.
    assert seed_id("category", "alpha:default") not in unverified
    assert seed_id("milestone", "alpha:0") not in unverified
    assert seed_id("card", "beta") not in unverified


@pytest.mark.parametrize("bad", ["true", "yes", None, 1])
def test_a_non_boolean_flag_fails_closed(tiny_catalog: Path, bad: object) -> None:
    """A quoted "true" is a string, not a flag. Reading it as "not flagged"
    would publish an unreviewed row as verified — so it is a load error."""
    rows = yaml.safe_load((tiny_catalog / "partners.yaml").read_text())
    rows[0]["needs_verification"] = bad
    _write(tiny_catalog, "partners.yaml", rows)
    with pytest.raises(ValueError, match="needs_verification"):
        load_unverified_ids(tiny_catalog)


def test_drift_lists_flagged_ids_the_snapshot_does_not_hold(
    snapshot: CatalogSnapshot,
) -> None:
    """The DB snapshot and the YAML can drift (the DB loaded from older seeds).
    A flagged id with no snapshot row means some row is being shown under a
    different id — or not at all — and its label is lost."""
    real = seed_id("card", "hdfc-infinia")
    stray = seed_id("card", "no-such-card")
    assert provenance_drift(snapshot, frozenset({real, stray})) == frozenset({stray})
    assert provenance_drift(snapshot, frozenset({real})) == frozenset()


# ── Drift guards over the real seeds ──────────────────────────────────────


def test_index_covers_every_snapshot_collection() -> None:
    """If CatalogSnapshot gains a row collection, the provenance index must be
    taught it — otherwise every row in it reads as verified by omission."""
    collections = {
        name
        for name, field in CatalogSnapshot.model_fields.items()
        if get_origin(field.annotation) is tuple
    }
    assert collections == set(PROVENANCE_COLLECTIONS)


def test_real_flags_all_resolve_to_snapshot_rows(seed_dir: Path, snapshot: CatalogSnapshot) -> None:
    """If the keying here ever drifts from `load_seed_snapshot`, a flagged row
    would silently resolve to an id no surface renders — and read as verified."""
    assert provenance_drift(snapshot, load_unverified_ids(seed_dir)) == frozenset()
    assert load_unverified_ids(seed_dir) <= snapshot_row_ids(snapshot)


def _count_flags(node: object) -> int:
    if isinstance(node, dict):
        own = 1 if node.get("needs_verification") is True else 0
        return own + sum(_count_flags(value) for value in node.values())
    if isinstance(node, list):
        return sum(_count_flags(item) for item in node)
    return 0


def test_real_flags_are_all_counted(seed_dir: Path) -> None:
    """Every flagged mapping at ANY depth of the parsed YAML is one id — none
    dropped by a nesting level the walker forgot."""
    flagged = sum(
        _count_flags(yaml.safe_load(path.read_text())) for path in seed_dir.glob("*.yaml")
    )
    assert flagged > 0
    assert len(load_unverified_ids(seed_dir)) == flagged
