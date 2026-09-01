"""Best Card for this Spend (roadmap Phase 1) — the daily-surface endpoint.

A pure snapshot read + valuation call: no DB, no LLM, no auth. That is
deliberate — the roadmap makes this feature available signed-out with a real
card picker, because the acquisition argument only works if the answer is
genuinely the user's own rather than a demo wallet's.

GET (not POST) so the answer is cacheable and shareable, and so the snapshot
version can drive an ETag exactly as `/catalog/cards` does.
"""

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import get_snapshot
from app.domain import CatalogSnapshot, SpendCategory
from app.valuation.best_card import BestCardResult, UnknownCard, rank_cards_for_spend

router = APIRouter(prefix="/best-card", tags=["best-card"])

# There is NO default program, deliberately (CLAUDE.md → *Never Assume the
# User's Goal*). Omitting `target_program_id` is a legitimate state, not a
# missing argument: the response comes back in points, with `partner_reach`
# listing what this wallet could reach so the client can offer the choice.
# An earlier version defaulted to KrisFlyer here and the UI printed that name
# to users who had never mentioned it.


@router.get("", response_model=BestCardResult)
async def best_card_for_spend(
    request: Request,
    response: Response,
    amount_inr: int = Query(gt=0, le=10_000_000, description="Purchase amount in rupees"),
    category: SpendCategory = Query(description="Spend category slug"),
    card_ids: list[UUID] = Query(min_length=1, max_length=20, description="The user's wallet"),
    target_program_id: UUID | None = Query(
        default=None,
        description="Transfer partner to price against. Omit for a points-only "
        "answer plus the programs this wallet can reach.",
    ),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> BestCardResult | Response:
    # The result is a pure function of (snapshot, query), so the snapshot
    # version plus a digest of the query string is a sound ETag. sha256 and
    # not the builtin hash(): str hashing is salted per process, so every
    # worker (and every restart) would mint a different ETag for the same
    # query — never a false 304, but never a cache hit either.
    query_digest = hashlib.sha256(request.url.query.encode()).hexdigest()[:12]
    etag = f'"{snapshot.version}-{query_digest}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    response.headers["ETag"] = etag

    try:
        return rank_cards_for_spend(
            snapshot,
            amount_inr=amount_inr,
            category=category,
            card_ids=card_ids,
            target_program_id=target_program_id,
        )
    except UnknownCard as exc:
        # A stale wallet (card removed from the catalog) is the client's to fix.
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
