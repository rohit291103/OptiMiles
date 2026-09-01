"""Portfolio View (roadmap Phase 1) — the user's own wallet, priced.

A pure snapshot read + valuation call: no DB, no LLM, no auth. Anonymous for
the same reason Best Card is — the wallet is whatever the client sends, so a
signed-out visitor gets a portfolio that is genuinely theirs. Wallet
persistence is the client's concern today (Phase 2 gives it a home).

GET (not POST) so the answer is cacheable and shareable, and so the snapshot
version can drive an ETag exactly as `/catalog/cards` does.
"""

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import get_snapshot
from app.domain import CatalogSnapshot
from app.valuation.best_card import UnknownCard
from app.valuation.portfolio import WalletPortfolio, build_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# There is NO default program, deliberately (CLAUDE.md → *Never Assume the
# User's Goal*). Omitting `target_program_id` is a legitimate state, not a
# missing argument: the response comes back in points, with `partner_reach`
# listing what this wallet could reach so the client can offer the choice.
# An earlier version defaulted to KrisFlyer here and the UI printed that name
# to users who had never mentioned it.

# Stated server-side, not left to the UI: caps and milestone thresholds here
# are targets, not progress. Until Phase 2 spend logging lands we do not know
# how much of a cap is already consumed, and a portfolio that silently
# implies "0% used" is the kind of confident wrong answer this product exists
# to avoid.
_CAVEAT = (
    "Caps and milestone thresholds are shown as targets, not progress — "
    "OptiMiles has no record of your actual spend yet, so nothing here "
    "assumes how much of a cap you have already used."
)


class PortfolioResponse(WalletPortfolio):
    """The priced wallet, plus the honesty flags the UI must render."""

    spend_data_available: bool
    caveat: str


@router.get("", response_model=PortfolioResponse)
async def wallet_portfolio(
    request: Request,
    response: Response,
    card_ids: list[UUID] = Query(min_length=1, max_length=20, description="The user's wallet"),
    target_program_id: UUID | None = Query(
        default=None,
        description="Transfer partner to price against. Omit for a points-only "
        "answer plus the programs this wallet can reach.",
    ),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> PortfolioResponse | Response:
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
        portfolio = build_portfolio(
            snapshot, card_ids=card_ids, target_program_id=target_program_id
        )
    except UnknownCard as exc:
        # A stale wallet (card removed from the catalog) is the client's to fix.
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return PortfolioResponse(
        **portfolio.model_dump(),
        spend_data_available=False,
        caveat=_CAVEAT,
    )
