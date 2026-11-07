"""The renewal-month persistence seam (migration 0010) against a capturing
fake connection — same approach as test_activity.py: no live DB, so assert
what Postgres would enforce (user scoping, the 1-12 CHECK, the upsert key) and
the row-count contract on delete."""

from typing import Any
from uuid import uuid4

import pytest

from app.repositories.activity import (
    clear_renewal_month,
    fetch_renewal_months_for_cards,
    list_renewal_months,
    set_renewal_month,
)


class FakeResult:
    def __init__(self, rows: list[Any] | None = None, rowcount: int = 0) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self) -> list[Any]:
        return self._rows


class CapturingConn:
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
async def test_setting_a_month_upserts_on_user_and_card() -> None:
    """Telling us again replaces the month; it never adds a second row."""
    conn = CapturingConn()
    user, card = uuid4(), uuid4()
    saved = await set_renewal_month(conn, user_id=user, card_id=card, renewal_month=3)  # type: ignore[arg-type]

    sql, params = conn.calls[0]
    assert "INSERT INTO card_renewal_months" in sql
    assert "ON CONFLICT (user_id, card_id)" in sql
    assert params == {"user_id": user, "card_id": card, "renewal_month": 3}
    assert saved.card_id == card and saved.renewal_month == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("month", [0, 13])
async def test_an_impossible_month_never_reaches_the_database(month: int) -> None:
    conn = CapturingConn()
    with pytest.raises(ValueError):
        await set_renewal_month(conn, user_id=uuid4(), card_id=uuid4(), renewal_month=month)  # type: ignore[arg-type]
    assert conn.calls == []


@pytest.mark.asyncio
async def test_every_read_and_write_is_scoped_to_one_user() -> None:
    conn = CapturingConn()
    user = uuid4()
    await list_renewal_months(conn, user_id=user)  # type: ignore[arg-type]
    await fetch_renewal_months_for_cards(conn, user_id=user, card_ids=[uuid4()])  # type: ignore[arg-type]
    await clear_renewal_month(conn, user_id=user, card_id=uuid4())  # type: ignore[arg-type]
    assert len(conn.calls) == 3
    for sql, params in conn.calls:
        assert "user_id = :user_id" in sql
        assert params["user_id"] == user


@pytest.mark.asyncio
async def test_wallet_fetch_maps_card_to_month_and_skips_empty_wallets() -> None:
    card = uuid4()
    conn = CapturingConn(FakeResult(rows=[Row(card_id=card, renewal_month=11)]))
    assert await fetch_renewal_months_for_cards(conn, user_id=uuid4(), card_ids=[card]) == {  # type: ignore[arg-type]
        card: 11
    }

    empty = CapturingConn()
    assert await fetch_renewal_months_for_cards(empty, user_id=uuid4(), card_ids=[]) == {}  # type: ignore[arg-type]
    assert empty.calls == []


@pytest.mark.asyncio
async def test_clear_reports_whether_a_month_was_removed() -> None:
    hit = CapturingConn(FakeResult(rowcount=1))
    miss = CapturingConn(FakeResult(rowcount=0))
    assert await clear_renewal_month(hit, user_id=uuid4(), card_id=uuid4()) is True  # type: ignore[arg-type]
    assert await clear_renewal_month(miss, user_id=uuid4(), card_id=uuid4()) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_list_returns_domain_rows_in_a_stable_order() -> None:
    a, b = uuid4(), uuid4()
    conn = CapturingConn(
        FakeResult(rows=[Row(card_id=a, renewal_month=1), Row(card_id=b, renewal_month=12)])
    )
    rows = await list_renewal_months(conn, user_id=uuid4())  # type: ignore[arg-type]
    assert [(r.card_id, r.renewal_month) for r in rows] == [(a, 1), (b, 12)]
    sql, _ = conn.calls[0]
    assert "ORDER BY card_id" in sql
