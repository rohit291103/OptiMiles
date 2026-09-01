"""Lounge access in the portfolio read — and, above all, honest coverage.

Coverage is partial by design (4 of 9 cards at the time of writing), so the
read surface has to distinguish three genuinely different states:

  detailed     — we hold real conditions for this card
  not_detailed — the card HAS lounge access but we haven't researched the
                 conditions yet
  none         — the card has no lounge access

Collapsing "not researched" into "none" would be a false claim about a
benefit the user paid for, and it is the specific failure this tri-state
exists to prevent.
"""

from app.domain import CatalogSnapshot, LoungeScope
from app.valuation.portfolio import build_portfolio


def _ids(snapshot: CatalogSnapshot, names: list[str]):
    return [next(c.id for c in snapshot.cards if c.card_name == n) for n in names]


def _portfolio(snapshot: CatalogSnapshot, names: list[str]):
    return build_portfolio(snapshot, card_ids=_ids(snapshot, names))


def _card(portfolio, name: str):
    return next(c for c in portfolio.cards if c.card_name == name)


def test_a_researched_card_reports_its_real_conditions(snapshot: CatalogSnapshot) -> None:
    card = _card(_portfolio(snapshot, ["Regalia Gold"]), "Regalia Gold")

    assert card.lounge_coverage == "detailed"
    domestic = next(a for a in card.lounge_access if a.scope is LoungeScope.DOMESTIC)
    assert domestic.visits_per_period == 3
    assert domestic.period == "quarterly"
    assert domestic.reset_anchor == "calendar_quarter"
    # The condition most cardholders get wrong: the visits are EARNED by last
    # quarter's spend, not granted.
    assert domestic.spend_gate_inr == 60_000
    assert domestic.spend_gate_period == "quarterly"
    assert domestic.needs_activation is False

    international = next(a for a in card.lounge_access if a.scope is LoungeScope.INTERNATIONAL)
    assert international.visits_per_period == 6
    assert international.spend_gate_inr is None
    assert international.needs_activation is True  # Priority Pass must be held


def test_unlimited_and_zero_are_reported_differently(snapshot: CatalogSnapshot) -> None:
    """Infinia is both at once: unlimited for the holder, zero complimentary
    guest visits. Reporting either as the other would be wrong."""
    card = _card(_portfolio(snapshot, ["Infinia Metal"]), "Infinia Metal")
    international = next(a for a in card.lounge_access if a.scope is LoungeScope.INTERNATIONAL)

    assert international.visits_per_period is None  # unlimited
    assert international.is_unlimited is True
    assert international.guest_visits_per_period == 0  # none, NOT unlimited


def test_an_unresearched_card_says_so_rather_than_claiming_none(
    snapshot: CatalogSnapshot,
) -> None:
    """Atlas has lounge access; we simply have not resolved the conflicting
    published figures yet. Saying "no lounge access" would be a false claim
    about a benefit the cardholder is paying for."""
    card = _card(_portfolio(snapshot, ["Atlas"]), "Atlas")

    assert card.has_lounge_access is True
    assert card.lounge_coverage == "not_detailed"
    assert card.lounge_access == ()


def test_a_card_without_lounge_access_reports_none(snapshot: CatalogSnapshot) -> None:
    card = _card(_portfolio(snapshot, ["Cashback"]), "Cashback")
    assert card.has_lounge_access is False
    assert card.lounge_coverage == "none"
    assert card.lounge_access == ()


def test_wallet_rollup_counts_only_what_is_actually_detailed(
    snapshot: CatalogSnapshot,
) -> None:
    """The count a UI would use to decide whether to show a caveat."""
    portfolio = _portfolio(snapshot, ["Infinia Metal", "Atlas", "Cashback"])
    assert portfolio.lounge_cards_detailed == 1
    assert portfolio.lounge_cards_undetailed == 1


def test_scopes_are_ordered_domestic_first(snapshot: CatalogSnapshot) -> None:
    """Domestic is the common case for an Indian cardholder, so it leads —
    and a fixed order keeps the render deterministic."""
    card = _card(_portfolio(snapshot, ["Platinum Travel"]), "Platinum Travel")
    assert [a.scope for a in card.lounge_access] == [
        LoungeScope.DOMESTIC,
        LoungeScope.INTERNATIONAL,
    ]


def test_amex_quarterly_limit_is_what_gets_reported(snapshot: CatalogSnapshot) -> None:
    """Amex states 8 a year AND 2 a quarter. The quarterly limit binds in any
    real trip, so it is the number reported; the annual total lives in the
    conditions text rather than over-promising a single-trip traveller."""
    card = _card(_portfolio(snapshot, ["Platinum Travel"]), "Platinum Travel")
    domestic = next(a for a in card.lounge_access if a.scope is LoungeScope.DOMESTIC)
    assert (domestic.visits_per_period, domestic.period) == (2, "quarterly")
    assert domestic.conditions is not None and "8 complimentary" in domestic.conditions
