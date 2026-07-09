"""GET /health — liveness + catalog snapshot version (build plan §7)."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import get_snapshot
from app.config import ENGINE_VERSION

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    engine_version: str
    catalog_snapshot_version: str | None


@router.get("/health")
async def health() -> HealthResponse:
    # Liveness must not depend on the DB: report the snapshot version when it
    # loads, but a DB hiccup returns status=ok with a null version, not a 500.
    version: str | None = None
    try:
        version = (await get_snapshot()).version
    except Exception:
        logger.warning("health: catalog snapshot unavailable", exc_info=True)
    return HealthResponse(
        status="ok",
        engine_version=ENGINE_VERSION,
        catalog_snapshot_version=version,
    )
