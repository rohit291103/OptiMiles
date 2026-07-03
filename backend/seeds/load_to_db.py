"""Load the reviewed seed catalog into the database, then read it back and
prove the round-trip: DB snapshot version must equal the seed snapshot
version (content-hash lineage, D-2).

Usage:  cd backend && uv run python seeds/load_to_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.knowledge.seed_catalog import load_seed_snapshot
from app.knowledge.store import load_snapshot
from app.knowledge.validation import validate_catalog
from app.repositories.catalog_admin import sync_catalog

SEED_DIR = Path(__file__).resolve().parent / "catalog"


async def main() -> None:
    seed_snapshot = load_seed_snapshot(SEED_DIR)
    validate_catalog(seed_snapshot)
    print(f"seeds valid — version {seed_snapshot.version}")

    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        counts = await sync_catalog(conn, seed_snapshot)
    for table, count in counts.items():
        print(f"  {table}: {count} rows")

    async with engine.connect() as conn:
        db_snapshot = await load_snapshot(conn)
    validate_catalog(db_snapshot)
    await engine.dispose()

    # Order-independent comparison: seeds are in YAML order, the DB reads
    # back in id order. Content (and therefore the content-hash version)
    # must match exactly; tuple order legitimately differs.
    for field in (
        "currencies",
        "partners",
        "transfer_links",
        "cards",
        "category_rules",
        "milestones",
        "award_charts",
    ):
        seed_rows = sorted(getattr(seed_snapshot, field), key=lambda o: str(o.id))
        db_rows = sorted(getattr(db_snapshot, field), key=lambda o: str(o.id))
        if seed_rows != db_rows:
            raise SystemExit(f"ROUND-TRIP MISMATCH in {field}: DB content differs from seeds")
    if db_snapshot.version != seed_snapshot.version:
        raise SystemExit(
            f"ROUND-TRIP VERSION MISMATCH: DB={db_snapshot.version} seeds={seed_snapshot.version}"
        )
    print(f"round-trip OK — DB snapshot version {db_snapshot.version} matches seeds")


if __name__ == "__main__":
    asyncio.run(main())
