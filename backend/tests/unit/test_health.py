"""GET /health returns 200 (build plan §5 Phase-0 criterion; version wired in
Phase 6). Liveness must never depend on the DB — a snapshot-load failure still
returns 200 with a null version rather than a 500."""

import pytest
from fastapi.testclient import TestClient

from app.config import ENGINE_VERSION
from app.main import create_app


def test_health_returns_200_when_snapshot_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DB down ⇒ status ok, version null, no 500. Health calls get_snapshot
    directly (not via Depends) precisely so it can swallow this failure."""

    async def _boom() -> object:
        raise RuntimeError("db unreachable")

    monkeypatch.setattr("app.api.health.get_snapshot", _boom)
    client = TestClient(create_app())

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine_version"] == ENGINE_VERSION
    assert body["catalog_snapshot_version"] is None
