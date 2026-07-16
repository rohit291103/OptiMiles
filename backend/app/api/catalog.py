"""Catalog reads (build-plan §7): supported cards, and the wallet reward story.

Plain snapshot reads, no pipeline run. `/cards` lists every card (including
in-wallet-only cards like the discontinued Atlas) with its `acquirable` flag,
so the frontend can show it in a wallet picker but not offer it as a new-card
suggestion. `/education` (guided-flow decision 4) shapes the selected wallet
into its reward story — currencies, earn rules, transfer links, shared
partners — instant and deterministic, for the wizard's education step.
"""

import re
from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.ai_reasoning.education import EducationFacts, narrate_education
from app.ai_reasoning.model import ChatModel
from app.api.deps import get_model, get_snapshot
from app.api.schemas import CardSummary, CatalogCardsResponse
from app.domain import CatalogSnapshot
from app.knowledge.education import (
    CardEducation,
    EducationPayload,
    UnknownCardId,
    wallet_education,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Same tokenization as ai_reasoning (a trailing decimal stays part of the
# token) — used to sweep the finished fact lines into the allow-sets.
_FACT_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


@router.get("/cards", response_model=CatalogCardsResponse)
async def list_cards(
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> CatalogCardsResponse:
    cards = tuple(
        CardSummary(
            id=card.id,
            bank=card.bank,
            card_name=card.card_name,
            annual_fee_inr=card.annual_fee_inr,
            has_lounge_access=card.has_lounge_access,
            acquirable=card.acquirable,
        )
        for card in sorted(snapshot.cards, key=lambda c: c.card_name)
    )
    return CatalogCardsResponse(catalog_snapshot_version=snapshot.version, cards=cards)


@router.get("/education", response_model=EducationPayload)
async def wallet_reward_story(
    card_ids: list[UUID] = Query(min_length=1),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> EducationPayload:
    """The selected wallet's reward story (guided-flow education step).

    Pure catalog-snapshot read — sub-second, no LLM, no simulation. An id the
    catalog has never listed is a 404 (the picker can't produce one, so it's a
    caller bug, not a soft skip)."""
    try:
        return wallet_education(snapshot, tuple(card_ids))
    except UnknownCardId as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


class EducationStoryResponse(BaseModel):
    """LLM-phrased framing of the wallet's reward story (decision 10), or
    null. Null is the norm (no key, a 429, or a failed number-echo check) —
    the wizard's deterministic education render is the template fallback, so
    this endpoint is a pure enhancement the client fetches separately and can
    ignore."""

    narrative: str | None


@router.get("/education/story", response_model=EducationStoryResponse)
async def wallet_reward_story_narrative(
    card_ids: list[UUID] = Query(min_length=1),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    model: ChatModel | None = Depends(get_model),
) -> EducationStoryResponse:
    """One LLM-phrased paragraph over the same education payload — number-echo
    validated against the catalog facts, never blocking the education step."""
    try:
        payload = wallet_education(snapshot, tuple(card_ids))
    except UnknownCardId as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    facts = education_facts(
        payload,
        catalog_card_names=frozenset(card.card_name for card in snapshot.cards),
    )
    narrative = await narrate_education(facts, model=model)
    return EducationStoryResponse(narrative=narrative)


def education_facts(
    payload: EducationPayload,
    *,
    catalog_card_names: frozenset[str] = frozenset(),
) -> EducationFacts:
    """Deterministic fact sheet for the LLM framing — sentences built from the
    education payload, with every number they contain allow-listed (integers
    exactly; non-integral earn rates as verbatim decimal tokens). Lives at the
    API layer because ai_reasoning may not import knowledge.education."""
    numbers: set[int] = {100}  # every rate is "per ₹100"
    decimals: set[str] = set()

    def rate_token(rate: Decimal) -> str:
        # 2.00 → "2" (allow-listed as an integer); 16.65 stays a decimal
        # token. format(..., "f") because normalize() can go scientific.
        if rate == rate.to_integral_value():
            numbers.add(int(rate))
            return str(int(rate))
        token = format(rate.normalize(), "f")
        decimals.add(token)
        return token

    card_lines = tuple(_card_line(card, rate_token, numbers) for card in payload.cards)
    shared_lines = tuple(
        f"{len(partner.card_ids)} of your cards can move points into {partner.program_name}."
        for partner in payload.shared_partners
    )
    numbers.update(len(partner.card_ids) for partner in payload.shared_partners)
    # Structural invariant: any number stated in a line WE hand the LLM is
    # fair to echo — catalog text (category labels, notes-derived labels like
    # "tiered 35/₹200") can embed figures the field-by-field adds above never
    # see, so sweep the finished lines and allow-list every token verbatim.
    for line in (*card_lines, *shared_lines):
        for raw in _FACT_NUMBER_RE.findall(line):
            token = raw.replace(",", "")
            if "." in token and token.partition(".")[2].strip("0"):
                decimals.add(token)
            else:
                numbers.add(int(Decimal(token)))
    allowed_names = frozenset(
        {
            *(card.card_name for card in payload.cards),
            *(card.currency.currency_name for card in payload.cards),
            *(link.program_name for card in payload.cards for link in card.transfer_links),
        }
    )
    return EducationFacts(
        card_lines=card_lines,
        shared_lines=shared_lines,
        allowed_numbers=frozenset(numbers),
        allowed_decimals=frozenset(decimals),
        allowed_names=allowed_names,
        catalog_card_names=catalog_card_names,
    )


def _card_line(
    card: CardEducation,
    rate_token: Callable[[Decimal], str],
    numbers: set[int],
) -> str:
    parts = [f"{card.card_name} ({card.bank}) earns {card.currency.currency_name}."]
    for rule in card.earn_rules:
        caps: list[str] = []
        for amount, period in (
            (rule.monthly_cap_inr, "month"),
            (rule.quarterly_cap_inr, "quarter"),
            (rule.annual_cap_inr, "year"),
        ):
            if amount is not None:
                numbers.add(amount)
                caps.append(f" up to ₹{amount}/{period}")
        parts.append(
            f"{rule.category_label}: {rate_token(rule.earn_rate)} pts/₹100{''.join(caps)}."
        )
    for link in card.transfer_links:
        numbers.update({link.ratio_from, link.ratio_to})
        details = []
        if link.max_transfer_points is not None:
            numbers.add(link.max_transfer_points)
            details.append(f"cap {link.max_transfer_points} pts/year")
        if link.transfer_fee_inr > 0:
            numbers.add(link.transfer_fee_inr)
            details.append(f"fee ₹{link.transfer_fee_inr}")
        numbers.update({link.processing_days_min, link.processing_days_max})
        details.append(f"{link.processing_days_min}-{link.processing_days_max} days")
        parts.append(
            f"Transfers to {link.program_name} at {link.ratio_from}:{link.ratio_to} "
            f"({', '.join(details)})."
        )
    return " ".join(parts)
