"""Phase 0 exit criterion: GET /health returns 200 (build plan §5)."""

from fastapi.testclient import TestClient

from app.config import ENGINE_VERSION
from app.main import app


def test_health_returns_200_with_versions() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine_version"] == ENGINE_VERSION
    # No catalog is seeded until build-plan Phase 1.
    assert body["catalog_snapshot_version"] is None
