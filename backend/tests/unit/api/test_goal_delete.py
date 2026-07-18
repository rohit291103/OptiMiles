"""DELETE /goals/{id} — removing a saved goal from the dashboard.

Same constraints as the other goal-endpoint tests (no live DB): auth is
required, an unknown/foreign goal id is a 404 (the scoped repo delete makes the
two indistinguishable), and a successful delete is an empty 204. The lineage
semantics themselves (child-first order, per-statement user scoping) are proven
in tests/unit/repositories/test_results.py.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

_SECRET = "test-jwt-secret-0123456789abcdef0123456789abcdef"


def _token() -> str:
    return jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        _SECRET,
        algorithm="HS256",
    )


class FakeConn:
    async def __aenter__(self) -> "FakeConn":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeEngine:
    """begin() only — the delete runs in one transaction."""

    def begin(self) -> FakeConn:
        return FakeConn()


def _client_with_fake_delete(
    monkeypatch: pytest.MonkeyPatch, *, deleted: bool
) -> TestClient:
    async def fake_delete(conn: object, *, user_id: object, goal_id: object) -> bool:
        return deleted

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_jwt_secret=_SECRET
    )
    monkeypatch.setattr("app.api.goals.get_engine", lambda: FakeEngine())
    monkeypatch.setattr("app.api.goals.delete_goal_lineage", fake_delete)
    return TestClient(app)


def test_delete_goal_requires_auth() -> None:
    """Destructive and per-user ⇒ no token, no delete (401)."""
    app = create_app()
    with TestClient(app) as client:
        response = client.delete(f"/v1/goals/{uuid4()}")
    assert response.status_code == 401


def test_unknown_or_foreign_goal_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client_with_fake_delete(monkeypatch, deleted=False) as client:
        response = client.delete(
            f"/v1/goals/{uuid4()}", headers={"Authorization": f"Bearer {_token()}"}
        )
    assert response.status_code == 404


def test_successful_delete_is_empty_204(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client_with_fake_delete(monkeypatch, deleted=True) as client:
        response = client.delete(
            f"/v1/goals/{uuid4()}", headers={"Authorization": f"Bearer {_token()}"}
        )
    assert response.status_code == 204
    assert response.content == b""
