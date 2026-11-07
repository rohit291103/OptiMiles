"""Shared wallet vocabulary for the priced surfaces (Best Card, Portfolio).

Both surfaces answer questions about *the user's own cards*, so both need the
same two things: turn a list of card ids into catalog cards (failing loudly on
an id the catalog has never heard of), and work out which transfer programs
that wallet can actually reach.

`partner_reach` is what makes "never assume the user's goal" buildable
(`CLAUDE.md` → *Never Assume the User's Goal*). The product must offer a
choice of target program rather than picking one — and it must offer only
programs this wallet can genuinely reach, or the chooser is full of dead ends.
That is not hypothetical: both Axis currencies reach only KrisFlyer, and
Maharaja Club is reachable only from HDFC's Infinia/Diners tier.
"""

from collections.abc import Sequence, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain import Card, CatalogSnapshot, CurrencyTransferLink, PartnerType
from app.valuation.transfer_math import marginal_miles


class UnknownCard(Exception):
    """A requested card id is not in the catalog snapshot."""


class PartnerReach(BaseModel):
    """A program the wallet can reach, and its best door into it.

    `best_miles_per_1000_points` is a normalized rate for comparing the
    wallet's own routes INTO one program — never for comparing across
    programs, which would be the same category error as comparing points
    across issuers.
    """

    model_config = ConfigDict(frozen=True)

    partner_id: UUID
    partner_name: str
    program_name: str
    partner_type: PartnerType
    is_target: bool
    card_ids: tuple[UUID, ...]
    best_miles_per_1000_points: int
    # True when the partner row or ANY contributing link is unverified — the
    # best rate may come from exactly that link. None means the caller
    # supplied no provenance (Best Card today): "not assessed", which must
    # never be read as verified.
    needs_verification: bool | None


def resolve_wallet(snapshot: CatalogSnapshot, card_ids: Sequence[UUID]) -> tuple[Card, ...]:
    """Card ids → catalog cards, in wallet order, duplicates collapsed.

    Raises `ValueError` on an empty wallet and `UnknownCard` on an id the
    snapshot does not contain — a stale wallet must fail loudly rather than
    quietly produce a confident answer about a wallet nobody asked about.
    """
    if not card_ids:
        raise ValueError("card_ids must not be empty")

    cards_by_id = {card.id: card for card in snapshot.cards}
    wallet: list[Card] = []
    for card_id in dict.fromkeys(card_ids):
        card = cards_by_id.get(card_id)
        if card is None:
            raise UnknownCard(f"card {card_id} is not in catalog snapshot {snapshot.version}")
        wallet.append(card)
    return tuple(wallet)


def links_by_currency(
    snapshot: CatalogSnapshot,
) -> dict[UUID, list[CurrencyTransferLink]]:
    """Transfer links grouped by the currency they belong to (D-1)."""
    grouped: dict[UUID, list[CurrencyTransferLink]] = {}
    for link in snapshot.transfer_links:
        grouped.setdefault(link.currency_id, []).append(link)
    return grouped


def partner_reach(
    snapshot: CatalogSnapshot,
    wallet: Sequence[Card],
    *,
    target_program_id: UUID | None = None,
    unverified_ids: Set[UUID] | None,
) -> tuple[PartnerReach, ...]:
    """Every program this wallet can send points to, best route first-class.

    The chosen target (when there is one) leads; the rest are alphabetical so
    the list is scannable. With no target chosen nothing is privileged —
    which is the point.
    """
    grouped = links_by_currency(snapshot)
    partners_by_id = {partner.id: partner for partner in snapshot.partners}

    cards_by_partner: dict[UUID, list[UUID]] = {}
    best_by_partner: dict[UUID, int] = {}
    flagged_partners: set[UUID] = set()
    for card in wallet:
        for link in grouped.get(card.reward_currency_id, ()):
            if unverified_ids is not None and (
                link.id in unverified_ids or link.partner_id in unverified_ids
            ):
                flagged_partners.add(link.partner_id)
            holders = cards_by_partner.setdefault(link.partner_id, [])
            if card.id not in holders:
                holders.append(card.id)
            rate = marginal_miles(1000, link)
            best_by_partner[link.partner_id] = max(best_by_partner.get(link.partner_id, 0), rate)

    return tuple(
        PartnerReach(
            partner_id=partner_id,
            partner_name=partners_by_id[partner_id].partner_name,
            program_name=partners_by_id[partner_id].program_name,
            partner_type=partners_by_id[partner_id].partner_type,
            is_target=partner_id == target_program_id,
            card_ids=tuple(holders),
            best_miles_per_1000_points=best_by_partner[partner_id],
            needs_verification=(None if unverified_ids is None else partner_id in flagged_partners),
        )
        for partner_id, holders in sorted(
            cards_by_partner.items(),
            key=lambda item: (
                item[0] != target_program_id,
                partners_by_id[item[0]].program_name,
            ),
        )
    )


def target_link_for(
    snapshot: CatalogSnapshot, card: Card, target_program_id: UUID | None
) -> CurrencyTransferLink | None:
    """The card's route into the chosen program, or None (including when no
    program has been chosen — the default state, not an error)."""
    if target_program_id is None:
        return None
    return next(
        (
            link
            for link in links_by_currency(snapshot).get(card.reward_currency_id, ())
            if link.partner_id == target_program_id
        ),
        None,
    )


def resolve_target(
    snapshot: CatalogSnapshot, target_program_id: UUID | None
) -> tuple[UUID | None, str | None]:
    """(id, program name) for a chosen target; (None, None) when none chosen.

    Raises `ValueError` for an id the catalog does not know — an unusable
    argument, distinct from the legitimate "no program chosen yet" state.
    """
    if target_program_id is None:
        return None, None
    partner = next((p for p in snapshot.partners if p.id == target_program_id), None)
    if partner is None:
        raise ValueError(f"unknown target program: {target_program_id}")
    return partner.id, partner.program_name
