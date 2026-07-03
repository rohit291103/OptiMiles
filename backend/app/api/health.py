"""GET /health — liveness + catalog snapshot version (build plan §7)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import ENGINE_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    engine_version: str
    catalog_snapshot_version: str | None


@router.get("/health")
async def health() -> HealthResponse:
    # catalog_snapshot_version stays None until the Knowledge Engine lands
    # (build-plan Phase 1) and a seeded catalog can be loaded.
    return HealthResponse(
        status="ok",
        engine_version=ENGINE_VERSION,
        catalog_snapshot_version=None,
    )
