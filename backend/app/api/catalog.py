"""GET /catalog/cards — supported cards for pickers (build-plan §7).

A plain snapshot read. Every card is returned (including in-wallet-only cards
like the discontinued Atlas) with its `acquirable` flag, so the frontend can
show it in a wallet picker but not offer it as a new-card suggestion.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_snapshot
from app.api.schemas import CardSummary, CatalogCardsResponse
from app.domain import CatalogSnapshot

router = APIRouter(prefix="/catalog", tags=["catalog"])


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
