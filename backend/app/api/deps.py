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

import hashlib
import inspect
import json
import logging
from functools import lru_cache
from types import ModuleType
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.ai_reasoning.model import ChatModel, model_from_settings
from app.config import Settings, get_settings
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import load_seed_snapshot, load_unverified_ids, provenance_drift
from app.knowledge.store import load_snapshot
from app.optimization.ranking import RankingWeights, load_ranking_weights

logger = logging.getLogger(__name__)

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
        try:
            warn_on_provenance_drift(_snapshot, get_unverified_ids())
            warn_on_seed_version_drift(
                _snapshot, load_seed_snapshot(get_settings().seed_dir).version
            )
        except (OSError, ValueError):
            # Unreadable seeds must not take down every catalog read; the
            # surfaces that label rows call get_unverified_ids themselves and
            # fail closed there.
            logger.exception("seed provenance could not be loaded")
    return _snapshot


def warn_on_provenance_drift(snapshot: CatalogSnapshot, unverified_ids: frozenset[UUID]) -> None:
    """Log flagged seed ids the loaded snapshot does not contain.

    The snapshot comes from the DB and the flags from the YAML on disk; if the
    DB was loaded from different seeds, a flagged row's label silently goes
    missing. Called once, when the snapshot is first loaded.
    """
    missing = provenance_drift(snapshot, unverified_ids)
    if missing:
        logger.warning(
            "seed provenance drift: %d flagged id(s) not in snapshot %s: %s",
            len(missing),
            snapshot.version,
            ", ".join(sorted(str(row_id) for row_id in missing)),
        )


def payload_digest(model: type[BaseModel], *modules: ModuleType) -> str:
    """The CODE component of an ETag: the response model's JSON schema plus
    the source of the modules that compute the payload.

    An ETag built only from data (snapshot, provenance, query) survives a
    deploy that changes the payload's shape or logic — browsers revalidate,
    get 304, and feed new UI an old body. That happened on 2026-11-07 (Best
    Card crashed reading `partner_name`). sha256 over source text, not
    hash(): identical across workers and restarts, so caching still works.
    Computed once per process at import.
    """
    digest = hashlib.sha256(json.dumps(model.model_json_schema(), sort_keys=True).encode())
    for module in modules:
        digest.update(inspect.getsource(module).encode())
    return digest.hexdigest()[:10]


def warn_on_seed_version_drift(snapshot: CatalogSnapshot, seed_version: str) -> None:
    """Log when the DB snapshot is not the reviewed seeds' content.

    Both versions are content hashes of the same model, so after a reseed
    they are equal. A mismatch means the DB was migrated or edited without a
    seed reload — and new nullable fields (e.g. `requires_portal`) are then
    silently at their permissive default. Called once, on first load.
    """
    if snapshot.version != seed_version:
        logger.warning(
            "catalog drift: DB snapshot %s is not the reviewed seeds (%s) — reload the "
            "seeds after migrating, or new fields serve their defaults",
            snapshot.version,
            seed_version,
        )


@lru_cache
def get_unverified_ids() -> frozenset[UUID]:
    """Ids of catalog rows still awaiting verification (the Listed tier).

    Read from the reviewed seed files, where provenance lives, and cached for
    the process like the snapshot — so CHANGING A FLAG IN THE YAML NEEDS A
    PROCESS RESTART to take effect. A missing seed directory (or a non-boolean
    flag) raises rather than returning an empty set: an empty set would label
    every row verified.
    """
    return load_unverified_ids(get_settings().seed_dir)


@lru_cache
def tier_digest(unverified_ids: frozenset[UUID]) -> str:
    """A short, stable digest of the verification tier, for ETags.

    Cached per distinct set — in production that is once per process, since
    `get_unverified_ids` is itself process-cached.
    """
    joined = ",".join(sorted(str(row_id) for row_id in unverified_ids))
    return hashlib.sha256(joined.encode()).hexdigest()[:8]


@lru_cache
def get_weights() -> RankingWeights:
    return load_ranking_weights(get_settings().ranking_weights_path)


def get_model() -> ChatModel | None:
    """The configured LLM, or None (no key) — the pipeline runs on either."""
    return model_from_settings(get_settings())


def get_config() -> Settings:
    return get_settings()
