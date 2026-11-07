"""The activity-log persistence seam against a capturing fake connection.

Same approach as test_results.py — no live DB, because a real write needs a
`users → auth.users` row only Supabase mints. So we capture every bound
parameter dict and assert the parts a real Postgres would enforce: closed
CHECK-constraint values land in-set as strings, every statement is scoped by
`user_id`, and the row-count contract on delete is respected.
"""

from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from app.domain.enums import LoungeScope, SpendCategory
from app.repositories.activity import (
    add_lounge_visit,
    add_spend_entry,
    delete_lounge_visit,
    delete_spend_entry,
    fetch_activity_for_cards,
    list_spend_entries,
)

# The closed CHECK sets migration 0008 enforces.
_CATEGORIES = {
    "travel",
    "dining",
    "international",
    "fuel",
    "groceries",
    "utilities",
    "online",
    "default",
}
_SCOPES = {"domestic", "international"}


class FakeResult:
    def __init__(self, rows: list[Any] | None = None, rowcount: int = 0) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self) -> list[Any]:
        return self._rows


class CapturingConn:
    """Records (sql, params) for every execute and returns a canned result."""

    def __init__(self, result: FakeResult | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._result = result or FakeResult()

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        self.calls.append((str(statement), params or {}))
        return self._result


class Row:
    def __init__(self, **fields: Any) -> None:
        self._mapping = fields


@pytest.mark.asyncio
async def test_spend_insert_is_user_scoped_and_check_safe() -> None:
    conn = CapturingConn()
    user, card = uuid4(), uuid4()
    entry = await add_spend_entry(
        conn,  # type: ignore[arg-type]
        user_id=user,
        card_id=card,
        occurred_on=date(2026, 8, 20),
        amount_inr=45_000,
        category_slug=SpendCategory.TRAVEL,
        note="Flight",
    )

    sql, params = conn.calls[0]
    assert "INSERT INTO spend_entries" in sql
    assert params["user_id"] == user
    assert params["amount_inr"] == 45_000
    # The enum must reach Postgres as its string value, not "SpendCategory.TRAVEL".
    assert params["category_slug"] in _CATEGORIES
    assert isinstance(params["category_slug"], str)
    # The returned object carries the minted id so the API can echo it back
    # without a read-after-write round trip.
    assert entry.id == params["id"]
    assert entry.amount_inr == 45_000


@pytest.mark.asyncio
async def test_visit_insert_coerces_scope_to_its_check_value() -> None:
    conn = CapturingConn()
    visit = await add_lounge_visit(
        conn,  # type: ignore[arg-type]
        user_id=uuid4(),
        card_id=uuid4(),
        occurred_on=date(2026, 8, 20),
        scope=LoungeScope.DOMESTIC,
        guest_count=2,
        airport_code="DEL",
    )
    _, params = conn.calls[0]
    assert params["scope"] in _SCOPES
    assert isinstance(params["scope"], str)
    assert params["guest_count"] == 2
    assert visit.airport_code == "DEL"


@pytest.mark.asyncio
async def test_every_read_is_scoped_to_one_user() -> None:
    """The query never spans users; RLS is the second line of defence behind
    this scoping, not the first."""
    conn = CapturingConn()
    user = uuid4()
    await list_spend_entries(conn, user_id=user, limit=10, offset=0)  # type: ignore[arg-type]
    await fetch_activity_for_cards(conn, user_id=user, card_ids=[uuid4()])  # type: ignore[arg-type]

    assert len(conn.calls) == 3  # one list + two aggregate reads
    for sql, params in conn.calls:
        assert "user_id = :user_id" in sql
        assert params["user_id"] == user


@pytest.mark.asyncio
async def test_empty_wallet_does_not_query_at_all() -> None:
    """No cards means no rows can match — skip the round trip rather than
    sending `= ANY('{}')`."""
    conn = CapturingConn()
    spend, visits = await fetch_activity_for_cards(conn, user_id=uuid4(), card_ids=[])  # type: ignore[arg-type]
    assert (spend, visits) == ((), ())
    assert conn.calls == []


@pytest.mark.asyncio
async def test_rows_map_back_into_domain_objects() -> None:
    card, entry_id = uuid4(), uuid4()
    conn = CapturingConn(
        FakeResult(
            rows=[
                Row(
                    id=entry_id,
                    card_id=card,
                    occurred_on=date(2026, 8, 1),
                    amount_inr=1_000,
                    category_slug="dining",
                    note=None,
                )
            ]
        )
    )
    entries = await list_spend_entries(conn, user_id=uuid4())  # type: ignore[arg-type]
    assert len(entries) == 1
    # The DB's TEXT round-trips back into the closed enum, not a bare string.
    assert entries[0].category_slug is SpendCategory.DINING
    assert entries[0].id == entry_id


@pytest.mark.asyncio
async def test_delete_reports_whether_a_row_was_actually_removed() -> None:
    """The API turns False into 404, which is what makes a foreign row and a
    nonexistent one indistinguishable to a prober."""
    hit = CapturingConn(FakeResult(rowcount=1))
    miss = CapturingConn(FakeResult(rowcount=0))
    assert await delete_spend_entry(hit, user_id=uuid4(), entry_id=uuid4()) is True  # type: ignore[arg-type]
    assert await delete_lounge_visit(miss, user_id=uuid4(), visit_id=uuid4()) is False  # type: ignore[arg-type]
    # Scoped in the statement itself — a matching id alone must never delete.
    sql, _ = hit.calls[0]
    assert "user_id = :user_id" in sql
