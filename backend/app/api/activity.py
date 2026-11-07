"""Activity log endpoints — logging spends and lounge visits, and what they prove.

ONE resource family for both, by roadmap decision: "design them as one pattern,
not two — same entry surface, same mental model — or users end up with two
separate things to remember and do neither."

Signed-in only, unlike Best Card and Portfolio View. Those are anonymous
because the wallet is whatever the client sends; a log is a personal record
that has to survive a device, so it needs an account. That is also the honest
upgrade path the roadmap wants: the anonymous surfaces sell the account.

`GET /activity/summary` is the read that matters — it fills in exactly the
three holes Portfolio View ships with today ("cap utilisation and milestone
progress need Phase 2 spend data") plus the lounge count, and it carries the
bounds with the numbers so no client can render them as exact.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.auth import require_user
from app.api.deps import get_engine, get_snapshot, get_unverified_ids
from app.domain import CatalogSnapshot
from app.domain.activity import CardRenewalMonth, LoungeVisit, ObservedActivity, SpendEntry
from app.domain.enums import LoungeScope, SpendCategory
from app.repositories.activity import (
    add_lounge_visit,
    add_spend_entry,
    clear_renewal_month,
    delete_lounge_visit,
    delete_spend_entry,
    fetch_activity_for_cards,
    fetch_renewal_months_for_cards,
    list_lounge_visits,
    list_renewal_months,
    list_spend_entries,
    set_renewal_month,
)
from app.simulation.observed import observe

router = APIRouter(prefix="/activity", tags=["activity"])

# Stated server-side rather than left to the UI, exactly as /v1/portfolio does
# with its own caveat: every figure derived from a manual log is a bound, not a
# fact, and a client that renders "1 visit left" as certainty will eventually
# send someone to a lounge desk to be turned away.
_CAVEAT = (
    "These figures come from what you have logged, so they are a floor, not a "
    "record: anything you did not log is not counted. Treat visits used as "
    "'at least this many' and anything remaining as 'at most this many'. "
    "Annual-fee waiver progress counts the spend you logged on the card, which "
    "may include spend the issuer excludes (such as rent or wallet loads), so "
    "a waiver shown as reached is reached on your log, subject to the exclusions "
    "listed with it."
)


class LogSpendRequest(BaseModel):
    card_id: UUID
    occurred_on: date
    amount_inr: int = Field(gt=0, le=100_000_000)
    category_slug: SpendCategory
    note: str | None = Field(default=None, max_length=280)


class LogVisitRequest(BaseModel):
    card_id: UUID
    occurred_on: date
    scope: LoungeScope
    guest_count: int = Field(default=0, ge=0, le=20)
    airport_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    note: str | None = Field(default=None, max_length=280)


class SetRenewalMonthRequest(BaseModel):
    renewal_month: int = Field(ge=1, le=12, description="1 = January … 12 = December")


class RenewalMonthsResponse(BaseModel):
    renewal_months: tuple[CardRenewalMonth, ...]


class SpendEntriesResponse(BaseModel):
    entries: tuple[SpendEntry, ...]


class LoungeVisitsResponse(BaseModel):
    visits: tuple[LoungeVisit, ...]


class ActivitySummaryResponse(ObservedActivity):
    """What the log proves, plus the honesty flag the UI must render."""

    caveat: str


def _reject_future(occurred_on: date, *, today: date) -> None:
    """A log records what happened, not what is planned.

    Enforced here rather than as a CHECK constraint because a CHECK cannot call
    NOW() (it must be immutable), and enforced at all because a future-dated
    entry would count toward a window it has not happened in yet — silently
    inflating a milestone the user has not actually reached.
    """
    if occurred_on > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="occurred_on is in the future — a log records what already happened",
        )


def _require_known_card(snapshot: CatalogSnapshot, card_id: UUID) -> None:
    """404 an unknown card rather than storing an orphan.

    Same posture as /v1/best-card and /v1/portfolio: a stale wallet fails
    loudly and fixably instead of silently dropping a card. The FK would catch
    this too, but as a 500 with no useful message.
    """
    if not any(card.id == card_id for card in snapshot.cards):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown card {card_id}")


@router.post("/spend", response_model=SpendEntry, status_code=status.HTTP_201_CREATED)
async def log_spend(
    payload: LogSpendRequest,
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> SpendEntry:
    """Record one spend against a card."""
    _require_known_card(snapshot, payload.card_id)
    _reject_future(payload.occurred_on, today=date.today())
    async with get_engine().begin() as conn:
        return await add_spend_entry(
            conn,
            user_id=user_id,
            card_id=payload.card_id,
            occurred_on=payload.occurred_on,
            amount_inr=payload.amount_inr,
            category_slug=payload.category_slug,
            note=payload.note,
        )


@router.post("/lounge-visits", response_model=LoungeVisit, status_code=status.HTTP_201_CREATED)
async def log_lounge_visit(
    payload: LogVisitRequest,
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> LoungeVisit:
    """Record one lounge visit.

    Accepted even for a card with no seeded lounge entitlement: coverage is
    partial by design (4 of 9 cards), and refusing to record something the user
    says happened because our catalog is incomplete would be backwards. It
    simply will not be counted against an allowance we do not have.
    """
    _require_known_card(snapshot, payload.card_id)
    _reject_future(payload.occurred_on, today=date.today())
    async with get_engine().begin() as conn:
        return await add_lounge_visit(
            conn,
            user_id=user_id,
            card_id=payload.card_id,
            occurred_on=payload.occurred_on,
            scope=payload.scope,
            guest_count=payload.guest_count,
            airport_code=payload.airport_code,
            note=payload.note,
        )


@router.get("/spend", response_model=SpendEntriesResponse)
async def my_spend(
    user_id: UUID = Depends(require_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SpendEntriesResponse:
    async with get_engine().connect() as conn:
        entries = await list_spend_entries(conn, user_id=user_id, limit=limit, offset=offset)
    return SpendEntriesResponse(entries=entries)


@router.get("/lounge-visits", response_model=LoungeVisitsResponse)
async def my_lounge_visits(
    user_id: UUID = Depends(require_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LoungeVisitsResponse:
    async with get_engine().connect() as conn:
        visits = await list_lounge_visits(conn, user_id=user_id, limit=limit, offset=offset)
    return LoungeVisitsResponse(visits=visits)


@router.delete("/spend/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_spend(entry_id: UUID, user_id: UUID = Depends(require_user)) -> None:
    async with get_engine().begin() as conn:
        deleted = await delete_spend_entry(conn, user_id=user_id, entry_id=entry_id)
    if not deleted:
        # Another user's entry and a nonexistent one are both 404 — the
        # response must not reveal that a row exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such entry")


@router.delete("/lounge-visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_lounge_visit(visit_id: UUID, user_id: UUID = Depends(require_user)) -> None:
    async with get_engine().begin() as conn:
        deleted = await delete_lounge_visit(conn, user_id=user_id, visit_id=visit_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such visit")


@router.get("/renewal-months", response_model=RenewalMonthsResponse)
async def my_renewal_months(user_id: UUID = Depends(require_user)) -> RenewalMonthsResponse:
    """Every renewal month this user has told us, one per card."""
    async with get_engine().connect() as conn:
        saved = await list_renewal_months(conn, user_id=user_id)
    return RenewalMonthsResponse(renewal_months=saved)


@router.put("/renewal-months/{card_id}", response_model=CardRenewalMonth)
async def put_renewal_month(
    card_id: UUID,
    payload: SetRenewalMonthRequest,
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
) -> CardRenewalMonth:
    """Tell us (or correct) the month this card's annual fee is charged.

    Optional, and only ever what the user said — fee-waiver progress is not
    computed without it, and no window is ever assumed in its place. Accepted
    for any catalog card, including one whose waiver we have not covered: it
    is a fact about the user's card, not about our catalog.
    """
    _require_known_card(snapshot, card_id)
    async with get_engine().begin() as conn:
        return await set_renewal_month(
            conn, user_id=user_id, card_id=card_id, renewal_month=payload.renewal_month
        )


@router.delete("/renewal-months/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_renewal_month(card_id: UUID, user_id: UUID = Depends(require_user)) -> None:
    async with get_engine().begin() as conn:
        cleared = await clear_renewal_month(conn, user_id=user_id, card_id=card_id)
    if not cleared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No renewal month set")


@router.get("/summary", response_model=ActivitySummaryResponse)
async def activity_summary(
    card_ids: list[UUID] = Query(min_length=1, max_length=20, description="The user's wallet"),
    as_of: date | None = Query(
        default=None,
        description="Defaults to today. Explicit so a client can reproduce a "
        "past answer — the calculation itself never reads a clock.",
    ),
    user_id: UUID = Depends(require_user),
    snapshot: CatalogSnapshot = Depends(get_snapshot),
    unverified_ids: frozenset[UUID] = Depends(get_unverified_ids),
) -> ActivitySummaryResponse:
    """Cap utilisation, milestone progress and lounge allowances, from the log.

    Not ETag'd, unlike the anonymous catalog reads: the answer depends on the
    caller's private rows and on today's date, so it is neither shareable nor
    stable enough to cache.
    """
    for card_id in card_ids:
        _require_known_card(snapshot, card_id)

    async with get_engine().connect() as conn:
        spend, visits = await fetch_activity_for_cards(conn, user_id=user_id, card_ids=card_ids)
        renewal_months = await fetch_renewal_months_for_cards(
            conn, user_id=user_id, card_ids=card_ids
        )

    observed = observe(
        snapshot,
        card_ids=card_ids,
        spend=spend,
        visits=visits,
        as_of=as_of or date.today(),
        renewal_months=renewal_months,
        unverified_ids=unverified_ids,
    )
    return ActivitySummaryResponse(**observed.model_dump(), caveat=_CAVEAT)
