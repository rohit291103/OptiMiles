"""Wallet education read-shape — the guided flow's "how your cards earn" step.

Decision 4 (decision log 2026-07-13): wallet card ids in → a structured reward
story out — per card its reward currency, earn rules (category-accelerated and
portal rates included), transfer links with ratio/cap/fee, and the partners
shared across the wallet (the "Atlas & TravelOne both reach KrisFlyer"
insight). This is a pure reshape of Knowledge Engine data over the pinned
snapshot: no pipeline run, no LLM, no sixth engine. Deterministic by
construction — cards in request order (deduped), earn rules by category slug,
links and shared partners by program name.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.catalog import (
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    RewardCurrency,
    TransferPartner,
)
from app.domain.enums import PartnerType, SpendCategory


class UnknownCardId(LookupError):
    """A requested card id is not in the catalog snapshot — fail loud, the
    caller sent an id the picker could never have shown."""

    def __init__(self, card_id: UUID) -> None:
        super().__init__(f"card {card_id} is not in the catalog snapshot")
        self.card_id = card_id


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class EarnRuleEducation(_Frozen):
    """One category's earn rate on a card, with its human label and caps."""

    category_slug: SpendCategory
    category_label: str
    earn_rate: Decimal
    monthly_cap_inr: int | None = None
    quarterly_cap_inr: int | None = None
    annual_cap_inr: int | None = None
    notes: str | None = None


class TransferLinkEducation(_Frozen):
    """One transfer avenue out of a card's currency, with everything the
    education step narrates: ratio, caps, fee, processing time."""

    partner_id: UUID
    partner_name: str
    program_name: str
    partner_type: PartnerType
    ratio_from: int
    ratio_to: int
    min_transfer_points: int
    max_transfer_points: int | None
    transfer_fee_inr: int
    processing_days_min: int
    processing_days_max: int
    notes: str | None = None


class CardEducation(_Frozen):
    """One wallet card's full reward story."""

    card_id: UUID
    bank: str
    card_name: str
    currency: RewardCurrency
    base_earn_rate: Decimal
    earn_rules: tuple[EarnRuleEducation, ...]
    transfer_links: tuple[TransferLinkEducation, ...]


class SharedPartner(_Frozen):
    """A partner reachable from ≥2 wallet cards — the ecosystem overlap the
    education step builds its story around. `card_ids` keeps wallet order."""

    partner_id: UUID
    partner_name: str
    program_name: str
    partner_type: PartnerType
    card_ids: tuple[UUID, ...]


class EducationPayload(_Frozen):
    """The wallet's reward story, versioned like every other snapshot read."""

    catalog_snapshot_version: str
    cards: tuple[CardEducation, ...]
    shared_partners: tuple[SharedPartner, ...]


def wallet_education(
    snapshot: CatalogSnapshot, card_ids: tuple[UUID, ...]
) -> EducationPayload:
    """Shape the snapshot into the wallet's reward story.

    Cards keep request order (duplicates collapse to first occurrence); an id
    missing from the snapshot raises `UnknownCardId`. Transfer eligibility is
    derived card → currency → link (D-1: links belong to currencies).
    """
    cards_by_id = {card.id: card for card in snapshot.cards}
    partners_by_id = {partner.id: partner for partner in snapshot.partners}
    currencies_by_id = {currency.id: currency for currency in snapshot.currencies}

    ordered_ids: list[UUID] = []
    for card_id in card_ids:
        if card_id not in cards_by_id:
            raise UnknownCardId(card_id)
        if card_id not in ordered_ids:
            ordered_ids.append(card_id)

    cards = tuple(
        _card_education(
            cards_by_id[card_id], snapshot, currencies_by_id, partners_by_id
        )
        for card_id in ordered_ids
    )

    # Partners shared across the wallet: reachable from ≥2 distinct cards.
    reachable: dict[UUID, list[UUID]] = {}
    for card in cards:
        for link in card.transfer_links:
            reachable.setdefault(link.partner_id, []).append(card.card_id)
    shared = tuple(
        SharedPartner(
            partner_id=partner_id,
            partner_name=partners_by_id[partner_id].partner_name,
            program_name=partners_by_id[partner_id].program_name,
            partner_type=partners_by_id[partner_id].partner_type,
            card_ids=tuple(holder_ids),
        )
        for partner_id, holder_ids in sorted(
            reachable.items(), key=lambda kv: partners_by_id[kv[0]].program_name
        )
        if len(holder_ids) >= 2
    )

    return EducationPayload(
        catalog_snapshot_version=snapshot.version,
        cards=cards,
        shared_partners=shared,
    )


def _card_education(
    card: Card,
    snapshot: CatalogSnapshot,
    currencies_by_id: dict[UUID, RewardCurrency],
    partners_by_id: dict[UUID, TransferPartner],
) -> CardEducation:
    earn_rules = tuple(
        EarnRuleEducation(
            category_slug=rule.category_slug,
            category_label=rule.category_label,
            earn_rate=rule.earn_rate,
            monthly_cap_inr=rule.monthly_cap_inr,
            quarterly_cap_inr=rule.quarterly_cap_inr,
            annual_cap_inr=rule.annual_cap_inr,
            notes=rule.notes,
        )
        for rule in sorted(
            (r for r in snapshot.category_rules if r.card_id == card.id),
            key=lambda r: r.category_slug.value,
        )
    )
    links = tuple(
        _link_education(link, partners_by_id[link.partner_id])
        for link in sorted(
            (
                candidate
                for candidate in snapshot.transfer_links
                if candidate.currency_id == card.reward_currency_id
            ),
            key=lambda link: partners_by_id[link.partner_id].program_name,
        )
    )
    return CardEducation(
        card_id=card.id,
        bank=card.bank,
        card_name=card.card_name,
        currency=currencies_by_id[card.reward_currency_id],
        base_earn_rate=card.base_earn_rate,
        earn_rules=earn_rules,
        transfer_links=links,
    )


def _link_education(
    link: CurrencyTransferLink, partner: TransferPartner
) -> TransferLinkEducation:
    return TransferLinkEducation(
        partner_id=partner.id,
        partner_name=partner.partner_name,
        program_name=partner.program_name,
        partner_type=partner.partner_type,
        ratio_from=link.ratio_from,
        ratio_to=link.ratio_to,
        min_transfer_points=link.min_transfer_points,
        max_transfer_points=link.max_transfer_points,
        transfer_fee_inr=link.transfer_fee_inr,
        processing_days_min=link.processing_days_min,
        processing_days_max=link.processing_days_max,
        notes=link.notes,
    )
