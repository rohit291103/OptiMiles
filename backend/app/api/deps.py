"""Shared API dependencies: the catalog snapshot, ranking weights, the LLM
model, and the async DB engine.

The snapshot is the shared read model (blueprint §3.2): loaded once from the DB
and process-cached, since the whole MVP catalog is a few hundred rows. In this
phase it loads lazily on first use and is cached for the process lifetime; a
TTL/refresh-on-admin-update is a later nicety, not needed at MVP scale.

The engine is a module-level singleton (asyncpg pool); routes that persist open
a transaction on it. Routes that only compute (parse, catalog listing, the
public simulator) never touch it.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.ai_reasoning.model import ChatModel, model_from_settings
from app.config import Settings, get_settings
from app.domain import CatalogSnapshot
from app.knowledge.store import load_snapshot
from app.optimization.ranking import RankingWeights, load_ranking_weights

_snapshot: CatalogSnapshot | None = None
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # Bound the connect so best-effort persistence fails fast against an
        # unreachable DB instead of blocking the response for asyncpg's default
        # ~60s timeout (persistence must never hold up the recommendation).
        #
        # `statement_cache_size=0` is REQUIRED against Supabase's transaction-mode
        # pooler (PgBouncer, port 6543): PgBouncer multiplexes connections, so
        # asyncpg's prepared-statement cache collides across sessions
        # (DuplicatePreparedStatementError). Disabling the cache is the standard
        # fix for asyncpg + PgBouncer transaction mode (db-schema §6.5).
        #
        # NullPool + pool_pre_ping: PgBouncer already pools at the server; a
        # client-side pool holds connections PgBouncer may recycle underneath us
        # (ConnectionDoesNotExistError: "connection was closed in the middle of
        # operation"). Don't pool client-side — open per checkout, and pre-ping
        # to validate a connection before use.
        _engine = create_async_engine(
            get_settings().database_url,
            connect_args={"timeout": 5, "statement_cache_size": 0},
            poolclass=NullPool,
            pool_pre_ping=True,
        )
    return _engine


async def get_snapshot() -> CatalogSnapshot:
    """The process-cached catalog snapshot, loaded from the DB on first use."""
    global _snapshot
    if _snapshot is None:
        async with get_engine().connect() as conn:
            _snapshot = await load_snapshot(conn)
    return _snapshot


@lru_cache
def get_weights() -> RankingWeights:
    return load_ranking_weights(get_settings().ranking_weights_path)


def get_model() -> ChatModel | None:
    """The configured LLM, or None (no key) — the pipeline runs on either."""
    return model_from_settings(get_settings())


def get_config() -> Settings:
    return get_settings()
