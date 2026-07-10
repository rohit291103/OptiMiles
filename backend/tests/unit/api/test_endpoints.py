"""API v1 surface (build-plan §7), driven with the seed catalog and no LLM.

Dependency overrides swap in the seed snapshot and disable both the LLM
(`model=None`) and persistence, so these tests exercise the HTTP edge — request
shaping, the discriminated response union, and the pipeline wiring — without a
database or a key. The reward math itself is covered by the engine unit suites;
here we prove the endpoints route to it correctly.
"""

from collections.abc import Iterator
from datetime import UTC

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import seed_id
from app.main import create_app


@pytest.fixture
def client(snapshot: CatalogSnapshot) -> Iterator[TestClient]:
    app = create_app()
    # Serve the seed snapshot; disable the LLM. Persistence is disabled by the
    # endpoints under test (/simulations) or made best-effort (recommendation).
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _feasible_body() -> dict:
    return {
        "intent": {
            "origin_city": "Hyderabad",
            "destination_city": "Singapore",
            "cabin_class": "business",
            "timeline_months": 8,
            "num_passengers": 1,
            "confidence": 0.95,
        },
        "wallet": [
            {"card_id": str(seed_id("card", "hdfc-infinia")), "current_points_balance": 20000}
        ],
        "spend_profile": [
            {"category_slug": "travel", "monthly_spend_inr": 60000},
            {"category_slug": "dining", "monthly_spend_inr": 40000},
        ],
    }


# ── /goals/parse ─────────────────────────────────────────────────────────


def test_parse_without_model_returns_clarification(client: TestClient) -> None:
    """No LLM ⇒ Stage 1 falls back to the structured form (ask everything)."""
    response = client.post("/goals/parse", json={"text": "business to SG"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "clarification"
    assert body["clarification"]["missing_fields"]


# ── /simulations (public, no persistence) ────────────────────────────────


def test_simulate_feasible_returns_recommendation(client: TestClient) -> None:
    response = client.post("/simulations", json=_feasible_body())
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "recommendation"
    rec = body["recommendation"]
    assert rec["verdict"]["feasible"] is True
    assert rec["recommended"] is not None
    assert rec["narration"]["model_version"] == "template-fallback"
    assert rec["catalog_snapshot_version"]  # lineage stamped


def test_simulate_default_spend_flagged(client: TestClient) -> None:
    """No spend profile ⇒ the default template is applied and flagged."""
    body = _feasible_body()
    body["spend_profile"] = []
    rec = client.post("/simulations", json=body).json()["recommendation"]
    assert "spend_profile" in rec["assumed_flags"]


def test_simulate_incomplete_intent_is_clarification(client: TestClient) -> None:
    body = _feasible_body()
    body["intent"]["destination_city"] = None
    resp = client.post("/simulations", json=body).json()
    assert resp["kind"] == "clarification"
    assert "destination_city" in resp["clarification"]["missing_fields"]


def test_simulate_unsupported_route(client: TestClient) -> None:
    body = _feasible_body()
    body["intent"]["destination_city"] = "London"
    body["intent"]["cabin_class"] = "economy"  # India→Europe economy is uncharted
    resp = client.post("/simulations", json=body).json()
    assert resp["kind"] == "unsupported_route"
    assert resp["unsupported_route"]["supported_routes"]


# ── /catalog/cards ───────────────────────────────────────────────────────


def test_catalog_lists_cards_with_acquirable_flag(client: TestClient) -> None:
    body = client.get("/catalog/cards").json()
    assert body["catalog_snapshot_version"]
    names = {c["card_name"] for c in body["cards"]}
    assert names  # non-empty
    # The discontinued Atlas is listed but marked non-acquirable.
    atlas = next((c for c in body["cards"] if "Atlas" in c["card_name"]), None)
    if atlas is not None:
        assert atlas["acquirable"] is False


# ── CORS (the browser Goal Simulator crosses origins) ────────────────────


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    """A simulate call from the Next dev origin gets the allow-origin header,
    so the browser doesn't block the response."""
    origin = "http://localhost:3000"
    response = client.post(
        "/simulations", json=_feasible_body(), headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_preflight_allows_authorization_header(client: TestClient) -> None:
    """The signed-in save sends `Authorization: Bearer` cross-origin. The CORS
    preflight must allow that header, or the browser blocks the request before
    it's ever sent — invisible to non-browser tests."""
    response = client.options(
        "/goals/recommendation/save",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed


def test_recommendation_save_requires_auth(client: TestClient) -> None:
    """No bearer token ⇒ 401; the persisting endpoint is not anonymous."""
    response = client.post("/goals/recommendation/save", json=_feasible_body())
    assert response.status_code == 401


def test_my_goals_requires_auth(client: TestClient) -> None:
    """The saved-goals list is per-user ⇒ no token, no list (401)."""
    response = client.get("/goals")
    assert response.status_code == 401


def test_recommendation_save_with_valid_token(snapshot: CatalogSnapshot) -> None:
    """A valid Supabase-style token ⇒ 200 with the recommendation. Persistence
    is best-effort (no DB here), so a failed write is swallowed, not surfaced."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    import jwt

    from app.config import Settings, get_settings

    secret = "test-secret-that-is-at-least-32-bytes-long!!"
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_jwt_secret=secret
    )

    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "iat": now,
         "exp": now + timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    with TestClient(app) as tc:
        response = tc.post(
            "/goals/recommendation/save",
            json=_feasible_body(),
            headers={"Authorization": f"Bearer {token}"},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "recommendation"
    # No DB is configured here, so the best-effort write fails — and the
    # endpoint must report that honestly (persisted=False), never a false
    # "saved". The UI trusts this flag rather than the 200 status.
    assert body["persisted"] is False


def test_cors_rejects_unconfigured_origin(client: TestClient) -> None:
    """An origin not in the allow-list gets no allow-origin header echoed back,
    so the browser blocks the cross-origin read — the list actually restricts."""
    response = client.post(
        "/simulations",
        json=_feasible_body(),
        headers={"Origin": "https://evil.example"},
    )
    # The request still succeeds server-side (CORS is a browser enforcement),
    # but the middleware must not bless the foreign origin.
    assert "access-control-allow-origin" not in response.headers
