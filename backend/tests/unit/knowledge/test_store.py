"""`load_snapshot` — the Knowledge Engine's sole DB reader (build rule 3).

No live DB here (same constraint as the repository tests): a fake connection
serves canned rows per table, derived from the seed snapshot itself. That
makes the assertion exact and strong — DB rows carrying the same content as
the YAML seeds must hydrate an EQUAL `CatalogSnapshot` with an IDENTICAL
content-hash version (the module's documented invariant: "a DB load of
identical data reports an identical version"). A column-mapping or
enum-casting mistake in any of the seven queries breaks the equality.
"""

import re
from typing import Any

from app.domain import CatalogSnapshot
from app.knowledge.store import load_snapshot

# table name → the snapshot tuple its SELECT must reproduce
_TABLE_TO_FIELD = {
    "reward_currencies": "currencies",
    "transfer_partners": "partners",
    "currency_transfer_partners": "transfer_links",
    "cards": "cards",
    "reward_categories": "category_rules",
    "reward_milestones": "milestones",
    "award_charts": "award_charts",
}

_FROM_RE = re.compile(r"FROM\s+(\w+)")
_SELECT_RE = re.compile(r"SELECT\s+(.*?)\s+FROM", re.DOTALL)


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class SeedBackedConn:
    """Serves each catalog SELECT the seed snapshot's rows for that table,
    shaped exactly as asyncpg would return them (plain column dicts)."""

    def __init__(self, snapshot: CatalogSnapshot) -> None:
        self._snapshot = snapshot
        self.queries: list[str] = []

    async def execute(self, statement: object) -> FakeResult:
        sql = str(statement)
        self.queries.append(sql)
        table = _FROM_RE.search(sql)
        columns = _SELECT_RE.search(sql)
        assert table and columns, f"unrecognized catalog query: {sql}"
        field = _TABLE_TO_FIELD[table.group(1)]
        selected = [c.strip() for c in columns.group(1).split(",")]
        # Serve ONLY the selected columns, as the DB would — a typo'd or
        # missing column in the SELECT list must fail here, not ship a
        # silently-defaulted snapshot field.
        rows = []
        for item in getattr(self._snapshot, field):
            dumped = item.model_dump()
            rows.append({c: dumped[c] for c in selected})
        return FakeResult(rows)


async def test_db_rows_hydrate_an_identical_snapshot(snapshot: CatalogSnapshot) -> None:
    conn = SeedBackedConn(snapshot)
    loaded = await load_snapshot(conn)  # type: ignore[arg-type]

    # Same content ⇒ same content-hash version, whether loaded from YAML or DB.
    assert loaded.version == snapshot.version
    # And every typed collection round-trips exactly (field mapping, enum
    # casting, Decimal handling — all seven queries).
    assert loaded == snapshot


async def test_reads_only_active_rows_in_deterministic_order(
    snapshot: CatalogSnapshot,
) -> None:
    """Every catalog query filters `is_active` and orders by id — the
    snapshot must be stable across loads (determinism is a standing test)."""
    conn = SeedBackedConn(snapshot)
    await load_snapshot(conn)  # type: ignore[arg-type]

    assert len(conn.queries) == len(_TABLE_TO_FIELD)
    for sql in conn.queries:
        assert "WHERE is_active" in sql
        assert "ORDER BY id" in sql
