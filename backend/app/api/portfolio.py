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

from app.api.deps import get_snapshot, get_unverified_ids, payload_digest, tier_digest
from app.domain import CatalogSnapshot
from app.valuation import portfolio as portfolio_engine
from app.valuation import transfer_math, wallet
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
# are targets, not progress. This read is anonymous and built from the catalog
# alone, so it cannot know how much of a cap is already consumed, and a
# portfolio that silently implies "0% used" is the kind of confident wrong
# answer this product exists to avoid. Progress comes from the user's activity
# log via the auth-only `GET /v1/activity/summary`, which a signed-in client
# composes with this response (joining caps on card + category and milestones
# on `milestone_id`) and which carries its own lower-bound caveat. That keeps
# this response cacheable and shareable, and keeps both engines pure.
_CAVEAT = (
    "Caps and milestone thresholds are shown as targets, not progress — "
    "this view is built from the catalog alone, with no record of your spend, "
    "so nothing here assumes how much of a cap you have already used."
)


class PortfolioResponse(WalletPortfolio):
    """The priced wallet, plus the honesty flags the UI must render."""

    spend_data_available: bool
    caveat: str


# The code component of the ETag — see deps.payload_digest.
PAYLOAD_DIGEST = payload_digest(PortfolioResponse, portfolio_engine, transfer_math, wallet)


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
    unverified_ids: frozenset[UUID] = Depends(get_unverified_ids),
) -> PortfolioResponse | Response:
    # The result is a pure function of (snapshot, query), so the snapshot
    # version plus a digest of the query string is a sound ETag. sha256 and
    # not the builtin hash(): str hashing is salted per process, so every
    # worker (and every restart) would mint a different ETag for the same
    # query — never a false 304, but never a cache hit either.
    #
    # The verification tier is part of the answer too, and it can change with
    # no change to any value (a row gets verified), so it is in the tag.
    query_digest = hashlib.sha256(request.url.query.encode()).hexdigest()[:12]
    etag = f'"{snapshot.version}-{tier_digest(unverified_ids)}-{query_digest}-{PAYLOAD_DIGEST}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    response.headers["ETag"] = etag

    try:
        portfolio = build_portfolio(
            snapshot,
            card_ids=card_ids,
            target_program_id=target_program_id,
            unverified_ids=unverified_ids,
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
