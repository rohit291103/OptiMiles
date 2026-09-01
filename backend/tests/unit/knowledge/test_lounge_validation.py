"""Catalog rules for lounge access (LA-01 … LA-05).

Lounge conditions are the most perishable data in the catalog — Indian
issuers have repeatedly added spend gates and switched vendors mid-year — and
a wrong condition is worse than no condition, because it sends someone to a
lounge desk to be turned away. These rules exist to make a row that cannot be
read correctly fail at load time rather than at the airport.
"""

import pytest

from app.domain import (
    AllowancePeriod,
    CatalogSnapshot,
    LoungeAccess,
    LoungeScope,
    ResetAnchor,
)
from app.knowledge.seed_catalog import seed_id
from app.knowledge.validation import CatalogValidationError, validate_catalog


def _access(snapshot: CatalogSnapshot, **overrides) -> LoungeAccess:
    base = dict(
        id=seed_id("lounge_access", "test:0"),
        card_id=snapshot.cards[0].id,
        program_id=seed_id("lounge_program", "priority-pass"),
        scope=LoungeScope.DOMESTIC,
        visits_per_period=4,
        period=AllowancePeriod.QUARTERLY,
        reset_anchor=ResetAnchor.CALENDAR_QUARTER,
    )
    return LoungeAccess(**{**base, **overrides})


def _with(snapshot: CatalogSnapshot, *rows: LoungeAccess) -> CatalogSnapshot:
    return snapshot.model_copy(update={"lounge_access": rows})


def test_the_seed_catalog_passes(snapshot: CatalogSnapshot) -> None:
    """The seeded lounge rows are themselves the first test."""
    validate_catalog(snapshot)


def test_lounge_row_must_reference_a_real_card(snapshot: CatalogSnapshot) -> None:
    orphan = _access(snapshot, card_id=seed_id("card", "no-such-card"))
    with pytest.raises(CatalogValidationError, match="LA-01"):
        validate_catalog(_with(snapshot, orphan))


def test_lounge_row_must_reference_a_real_programme(snapshot: CatalogSnapshot) -> None:
    orphan = _access(snapshot, program_id=seed_id("lounge_program", "no-such-programme"))
    with pytest.raises(CatalogValidationError, match="LA-02"):
        validate_catalog(_with(snapshot, orphan))


def test_a_spend_gate_must_say_over_what_period(snapshot: CatalogSnapshot) -> None:
    """ "Rs 60,000" is not a condition anyone can act on without knowing the
    window it is measured over — a gate missing its period is unreadable, so
    it must never load."""
    with pytest.raises(CatalogValidationError, match="LA-03"):
        validate_catalog(_with(snapshot, _access(snapshot, spend_gate_inr=60_000)))


def test_a_gate_period_without_an_amount_is_also_rejected(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(CatalogValidationError, match="LA-03"):
        validate_catalog(
            _with(snapshot, _access(snapshot, spend_gate_period=AllowancePeriod.QUARTERLY))
        )


def test_a_counted_allowance_must_declare_its_reset_anchor(snapshot: CatalogSnapshot) -> None:
    """The user's explicit decision (2026-08-26): the anchor is seeded per
    card, never defaulted. Issuers reset variously on the calendar quarter,
    the card anniversary and the statement cycle, so a silent calendar-quarter
    assumption is the likeliest source of a wrong visit count."""
    with pytest.raises(CatalogValidationError, match="LA-04"):
        validate_catalog(
            _with(snapshot, _access(snapshot, reset_anchor=ResetAnchor.NOT_APPLICABLE))
        )


def test_an_unlimited_allowance_may_have_no_anchor(snapshot: CatalogSnapshot) -> None:
    """Nothing resets when there is no count — Infinia's domestic access."""
    validate_catalog(
        _with(
            snapshot,
            _access(
                snapshot,
                visits_per_period=None,
                reset_anchor=ResetAnchor.NOT_APPLICABLE,
            ),
        )
    )


def test_zero_visits_still_needs_an_anchor_only_if_counted(snapshot: CatalogSnapshot) -> None:
    """Zero is a count, not an absence — "no complimentary guest visits this
    quarter" is a claim about a period, so it has to name one."""
    with pytest.raises(CatalogValidationError, match="LA-04"):
        validate_catalog(
            _with(
                snapshot,
                _access(snapshot, visits_per_period=0, reset_anchor=ResetAnchor.NOT_APPLICABLE),
            )
        )


def test_one_row_per_card_programme_and_scope_unless_tiers_differ(
    snapshot: CatalogSnapshot,
) -> None:
    """Two rows for the same card+programme+scope are only meaningful when
    they are different spend tiers. Identical gates mean one of them is a
    duplicate that would double-count a user's entitlement."""
    duplicate = _access(snapshot, id=seed_id("lounge_access", "test:1"))
    with pytest.raises(CatalogValidationError, match="LA-05"):
        validate_catalog(_with(snapshot, _access(snapshot), duplicate))


def test_tiered_rows_for_the_same_scope_are_allowed(snapshot: CatalogSnapshot) -> None:
    """Atlas-style tiering: the same card and programme, more visits at a
    higher spend. Distinguished by the gate, so both rows are real."""
    validate_catalog(
        _with(
            snapshot,
            _access(
                snapshot,
                visits_per_period=8,
                spend_gate_inr=300_000,
                spend_gate_period=AllowancePeriod.ANNUAL,
            ),
            _access(
                snapshot,
                id=seed_id("lounge_access", "test:1"),
                visits_per_period=12,
                spend_gate_inr=750_000,
                spend_gate_period=AllowancePeriod.ANNUAL,
            ),
        )
    )
