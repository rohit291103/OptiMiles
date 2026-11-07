"""Read and write side of the activity log (migration 0008).

The only module that touches `spend_entries` / `lounge_visits` — build rule 3
(only `knowledge/` and `repositories/` reach the database). It fetches and
stores rows; it decides nothing. What the rows *mean* is
`simulation/observed.py`, a pure function that never sees a connection.

Every query is scoped to a single `user_id` — the verified `auth.users` subject
from the access token — and parameterized. The query never spans users; RLS
(D-4, policies in 0008) is the second line of defence behind that scoping.

VOLUME. `list_*` is paged for the log view. The aggregate fetch used by the
observed-activity summary is deliberately UNBOUNDED over the wallet's cards,
because a one-time milestone counts spend with no window at all — truncating it
would silently understate progress, and understating a milestone is the same
class of error as overstating a lounge count. At the scale this feature is used
(hand-logged entries), that is a few hundred rows; if it ever is not, the fix is
a stored running total, not a LIMIT that quietly loses evidence.
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.domain.activity import CardRenewalMonth, LoungeVisit, SpendEntry
from app.domain.enums import LoungeScope, SpendCategory

_INSERT_SPEND = text(
    """
    INSERT INTO spend_entries (id, user_id, card_id, occurred_on, amount_inr, category_slug, note)
    VALUES (:id, :user_id, :card_id, :occurred_on, :amount_inr, :category_slug, :note)
    """
)

_INSERT_VISIT = text(
    """
    INSERT INTO lounge_visits
      (id, user_id, card_id, occurred_on, scope, guest_count, airport_code, note)
    VALUES (:id, :user_id, :card_id, :occurred_on, :scope, :guest_count, :airport_code, :note)
    """
)

# Newest first, tie-broken on id so paging is stable even when two entries
# share a date — the same ordering discipline as saved_goals.py.
_LIST_SPEND = text(
    """
    SELECT id, card_id, occurred_on, amount_inr, category_slug, note
    FROM spend_entries
    WHERE user_id = :user_id
    ORDER BY occurred_on DESC, id DESC
    LIMIT :limit OFFSET :offset
    """
)

_LIST_VISITS = text(
    """
    SELECT id, card_id, occurred_on, scope, guest_count, airport_code, note
    FROM lounge_visits
    WHERE user_id = :user_id
    ORDER BY occurred_on DESC, id DESC
    LIMIT :limit OFFSET :offset
    """
)

# The aggregate reads. `= ANY(:card_ids)` keeps one bind parameter regardless of
# wallet size (asyncpg takes a Python list for a UUID[] directly).
_SPEND_FOR_CARDS = text(
    """
    SELECT id, card_id, occurred_on, amount_inr, category_slug, note
    FROM spend_entries
    WHERE user_id = :user_id AND card_id = ANY(:card_ids)
    ORDER BY occurred_on, id
    """
)

_VISITS_FOR_CARDS = text(
    """
    SELECT id, card_id, occurred_on, scope, guest_count, airport_code, note
    FROM lounge_visits
    WHERE user_id = :user_id AND card_id = ANY(:card_ids)
    ORDER BY occurred_on, id
    """
)

# Renewal months (migration 0010). One row per (user, card): telling us again
# replaces the month rather than adding a second answer.
_UPSERT_RENEWAL_MONTH = text(
    """
    INSERT INTO card_renewal_months (user_id, card_id, renewal_month)
    VALUES (:user_id, :card_id, :renewal_month)
    ON CONFLICT (user_id, card_id) DO UPDATE SET renewal_month = EXCLUDED.renewal_month
    """
)

_LIST_RENEWAL_MONTHS = text(
    """
    SELECT card_id, renewal_month
    FROM card_renewal_months
    WHERE user_id = :user_id
    ORDER BY card_id
    """
)

_RENEWAL_MONTHS_FOR_CARDS = text(
    """
    SELECT card_id, renewal_month
    FROM card_renewal_months
    WHERE user_id = :user_id AND card_id = ANY(:card_ids)
    ORDER BY card_id
    """
)

_DELETE_RENEWAL_MONTH = text(
    "DELETE FROM card_renewal_months WHERE user_id = :user_id AND card_id = :card_id"
)

_DELETE_SPEND = text("DELETE FROM spend_entries WHERE id = :id AND user_id = :user_id")
_DELETE_VISIT = text("DELETE FROM lounge_visits WHERE id = :id AND user_id = :user_id")


async def add_spend_entry(
    conn: AsyncConnection,
    *,
    user_id: UUID,
    card_id: UUID,
    occurred_on: date,
    amount_inr: int,
    category_slug: SpendCategory,
    note: str | None = None,
) -> SpendEntry:
    """Record one spend. Runs in the caller's transaction (`engine.begin()`)."""
    entry_id = uuid4()
    await conn.execute(
        _INSERT_SPEND,
        {
            "id": entry_id,
            "user_id": user_id,
            "card_id": card_id,
            "occurred_on": occurred_on,
            "amount_inr": amount_inr,
            "category_slug": category_slug.value,
            "note": note,
        },
    )
    return SpendEntry(
        id=entry_id,
        card_id=card_id,
        occurred_on=occurred_on,
        amount_inr=amount_inr,
        category_slug=category_slug,
        note=note,
    )


async def add_lounge_visit(
    conn: AsyncConnection,
    *,
    user_id: UUID,
    card_id: UUID,
    occurred_on: date,
    scope: LoungeScope,
    guest_count: int = 0,
    airport_code: str | None = None,
    note: str | None = None,
) -> LoungeVisit:
    """Record one lounge visit against (card, scope) — never against a tier."""
    visit_id = uuid4()
    await conn.execute(
        _INSERT_VISIT,
        {
            "id": visit_id,
            "user_id": user_id,
            "card_id": card_id,
            "occurred_on": occurred_on,
            "scope": scope.value,
            "guest_count": guest_count,
            "airport_code": airport_code,
            "note": note,
        },
    )
    return LoungeVisit(
        id=visit_id,
        card_id=card_id,
        occurred_on=occurred_on,
        scope=scope,
        guest_count=guest_count,
        airport_code=airport_code,
        note=note,
    )


def _to_spend(row: object) -> SpendEntry:
    m = row._mapping  # type: ignore[attr-defined]
    return SpendEntry(
        id=m["id"],
        card_id=m["card_id"],
        occurred_on=m["occurred_on"],
        amount_inr=m["amount_inr"],
        category_slug=SpendCategory(m["category_slug"]),
        note=m["note"],
    )


def _to_visit(row: object) -> LoungeVisit:
    m = row._mapping  # type: ignore[attr-defined]
    return LoungeVisit(
        id=m["id"],
        card_id=m["card_id"],
        occurred_on=m["occurred_on"],
        scope=LoungeScope(m["scope"]),
        guest_count=m["guest_count"],
        airport_code=m["airport_code"],
        note=m["note"],
    )


async def list_spend_entries(
    conn: AsyncConnection, *, user_id: UUID, limit: int = 50, offset: int = 0
) -> tuple[SpendEntry, ...]:
    result = await conn.execute(_LIST_SPEND, {"user_id": user_id, "limit": limit, "offset": offset})
    return tuple(_to_spend(row) for row in result.fetchall())


async def list_lounge_visits(
    conn: AsyncConnection, *, user_id: UUID, limit: int = 50, offset: int = 0
) -> tuple[LoungeVisit, ...]:
    result = await conn.execute(
        _LIST_VISITS, {"user_id": user_id, "limit": limit, "offset": offset}
    )
    return tuple(_to_visit(row) for row in result.fetchall())


async def fetch_activity_for_cards(
    conn: AsyncConnection, *, user_id: UUID, card_ids: Sequence[UUID]
) -> tuple[tuple[SpendEntry, ...], tuple[LoungeVisit, ...]]:
    """Everything logged against these cards — the input to `observe()`.

    Unbounded by date on purpose (see the module docstring): a one-time
    milestone has no window, so any cutoff would silently understate it.
    """
    if not card_ids:
        return (), ()
    params = {"user_id": user_id, "card_ids": list(card_ids)}
    spend_rows = (await conn.execute(_SPEND_FOR_CARDS, params)).fetchall()
    visit_rows = (await conn.execute(_VISITS_FOR_CARDS, params)).fetchall()
    return (
        tuple(_to_spend(row) for row in spend_rows),
        tuple(_to_visit(row) for row in visit_rows),
    )


async def delete_spend_entry(conn: AsyncConnection, *, user_id: UUID, entry_id: UUID) -> bool:
    """Delete one entry. False when it does not exist OR is not this user's —
    the caller renders both as 404, so a probe cannot distinguish them."""
    result = await conn.execute(_DELETE_SPEND, {"id": entry_id, "user_id": user_id})
    return bool(result.rowcount)


async def delete_lounge_visit(conn: AsyncConnection, *, user_id: UUID, visit_id: UUID) -> bool:
    result = await conn.execute(_DELETE_VISIT, {"id": visit_id, "user_id": user_id})
    return bool(result.rowcount)


async def set_renewal_month(
    conn: AsyncConnection, *, user_id: UUID, card_id: UUID, renewal_month: int
) -> CardRenewalMonth:
    """Record (or replace) the month this user's annual fee is charged on a card.

    Validated before the round trip — the DB CHECK is the backstop, not the
    first line — so a bad month is a ValueError here, never a 500.
    """
    # Constructing the model first validates 1-12 (pydantic's ValidationError
    # is a ValueError) before anything is sent.
    saved = CardRenewalMonth(card_id=card_id, renewal_month=renewal_month)
    await conn.execute(
        _UPSERT_RENEWAL_MONTH,
        {"user_id": user_id, "card_id": card_id, "renewal_month": renewal_month},
    )
    return saved


def _to_renewal_month(row: object) -> CardRenewalMonth:
    m = row._mapping  # type: ignore[attr-defined]
    return CardRenewalMonth(card_id=m["card_id"], renewal_month=m["renewal_month"])


async def list_renewal_months(
    conn: AsyncConnection, *, user_id: UUID
) -> tuple[CardRenewalMonth, ...]:
    result = await conn.execute(_LIST_RENEWAL_MONTHS, {"user_id": user_id})
    return tuple(_to_renewal_month(row) for row in result.fetchall())


async def fetch_renewal_months_for_cards(
    conn: AsyncConnection, *, user_id: UUID, card_ids: Sequence[UUID]
) -> dict[UUID, int]:
    """card → renewal month, for the wallet — the `renewal_months` input to
    `observe()`. A card the user has not told us about is simply absent."""
    if not card_ids:
        return {}
    result = await conn.execute(
        _RENEWAL_MONTHS_FOR_CARDS, {"user_id": user_id, "card_ids": list(card_ids)}
    )
    saved = [_to_renewal_month(row) for row in result.fetchall()]
    return {row.card_id: row.renewal_month for row in saved}


async def clear_renewal_month(conn: AsyncConnection, *, user_id: UUID, card_id: UUID) -> bool:
    """Forget the month. False when there was none (or it is not this user's)."""
    result = await conn.execute(_DELETE_RENEWAL_MONTH, {"user_id": user_id, "card_id": card_id})
    return bool(result.rowcount)
