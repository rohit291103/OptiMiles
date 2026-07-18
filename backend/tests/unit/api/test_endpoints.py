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
    response = client.post("/v1/goals/parse", json={"text": "business to SG"})
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "clarification"
    assert body["clarification"]["missing_fields"]


# ── /simulations (public, no persistence) ────────────────────────────────


def test_simulate_feasible_returns_recommendation(client: TestClient) -> None:
    response = client.post("/v1/simulations", json=_feasible_body())
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
    rec = client.post("/v1/simulations", json=body).json()["recommendation"]
    assert "spend_profile" in rec["assumed_flags"]


def test_simulate_accepts_total_spend_budget(client: TestClient) -> None:
    """Guided-flow slice 1: a total-over-horizon budget alone (no category
    split) runs the full pipeline on the server-derived template split, and the
    profile is honestly flagged assumed."""
    body = _feasible_body()
    del body["spend_profile"]
    body["total_spend_inr"] = 800_000
    response = client.post("/v1/simulations", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "recommendation"
    rec = payload["recommendation"]
    assert rec["recommended"] is not None
    assert "spend_profile" in rec["assumed_flags"]


def test_simulate_rejects_total_and_profile_together(client: TestClient) -> None:
    """`total_spend_inr` and `spend_profile` are mutually exclusive — sending
    both is a 422 at the edge, never a silent preference."""
    body = _feasible_body()
    body["total_spend_inr"] = 800_000  # _feasible_body already has spend_profile
    response = client.post("/v1/simulations", json=body)
    assert response.status_code == 422


def test_simulate_rejects_non_positive_total(client: TestClient) -> None:
    body = _feasible_body()
    del body["spend_profile"]
    body["total_spend_inr"] = 0
    assert client.post("/v1/simulations", json=body).status_code == 422


def test_simulate_incomplete_intent_is_clarification(client: TestClient) -> None:
    body = _feasible_body()
    body["intent"]["destination_city"] = None
    resp = client.post("/v1/simulations", json=body).json()
    assert resp["kind"] == "clarification"
    assert "destination_city" in resp["clarification"]["missing_fields"]


def test_simulate_unsupported_route(client: TestClient) -> None:
    body = _feasible_body()
    body["intent"]["destination_city"] = "London"
    body["intent"]["cabin_class"] = "economy"  # India→Europe economy is uncharted
    resp = client.post("/v1/simulations", json=body).json()
    assert resp["kind"] == "unsupported_route"
    assert resp["unsupported_route"]["supported_routes"]


# ── /catalog/cards ───────────────────────────────────────────────────────


def test_catalog_lists_cards_with_acquirable_flag(client: TestClient) -> None:
    body = client.get("/v1/catalog/cards").json()
    assert body["catalog_snapshot_version"]
    names = {c["card_name"] for c in body["cards"]}
    assert names  # non-empty
    # The discontinued Atlas is listed but marked non-acquirable.
    atlas = next((c for c in body["cards"] if "Atlas" in c["card_name"]), None)
    if atlas is not None:
        assert atlas["acquirable"] is False


def test_simulate_wallet_infeasible_returns_labeled_acquisition_pair(
    client: TestClient,
) -> None:
    """Slice 8 through the REAL dependency default (get_weights → v2 config):
    an empty wallet that can't clear the goal gets the labeled cheapest /
    best-value acquisition pair in the presented routes — this pins the live
    /simulations response shape, since the v2 default changes route
    composition for the one-shot flow too, not just the wizard."""
    body = {
        "intent": {
            "origin_city": "Hyderabad",
            "destination_city": "Singapore",
            "cabin_class": "business",
            "timeline_months": 12,
            "num_passengers": 1,
            "confidence": 0.95,
        },
        "wallet": [],
        "spend_profile": [
            {"category_slug": "travel", "monthly_spend_inr": 40000},
            {"category_slug": "dining", "monthly_spend_inr": 30000},
        ],
    }
    rec = client.post("/v1/simulations", json=body).json()["recommendation"]
    routes = [rec["recommended"], *rec["alternatives"]]
    roles = [r["acquisition_role"] for r in routes if r is not None]
    labeled = [r for r in roles if r is not None]
    assert labeled, "empty wallet can't clear — the pair must be labeled"
    assert set(labeled) == {"cheapest", "best_value"} or set(labeled) == {
        "cheapest_and_best_value"
    }


# ── /simulations/probe (guided-flow slice 3) ─────────────────────────────


def test_probe_feasible_goal_returns_quiet_verdict(client: TestClient) -> None:
    response = client.post("/v1/simulations/probe", json=_feasible_body())
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "feasibility"
    assert body["verdict"]["feasible"] is True
    assert body["miles_required_total"] > 0
    assert body["catalog_snapshot_version"]


def test_probe_hopeless_goal_returns_adjustment_menu(client: TestClient) -> None:
    """The wizard's early interrupt: 2 pax on a transfer-capped Atlas with no
    new cards → infeasible verdict with the adjustment menu, no pipeline run."""
    intent = dict(_feasible_body()["intent"], num_passengers=2)
    body = {
        "intent": intent,
        "wallet": [
            {"card_id": str(seed_id("card", "axis-atlas")), "current_points_balance": 0}
        ],
        "spend_profile": [{"category_slug": "travel", "monthly_spend_inr": 100000}],
        "constraints": {"no_new_cards": True},
    }
    response = client.post("/v1/simulations/probe", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "feasibility"
    assert payload["verdict"]["feasible"] is False
    assert payload["verdict"]["adjustment_options"]


def test_probe_rejects_total_and_profile_together(client: TestClient) -> None:
    body = _feasible_body()
    body["total_spend_inr"] = 800_000
    assert client.post("/v1/simulations/probe", json=body).status_code == 422


# ── /catalog/education (guided-flow slice 2) ─────────────────────────────


def test_education_returns_wallet_reward_story(client: TestClient) -> None:
    """Atlas + TravelOne → both cards' chains to KrisFlyer with real rates,
    straight off the snapshot (no pipeline run)."""
    atlas = str(seed_id("card", "axis-atlas"))
    travelone = str(seed_id("card", "hsbc-travelone"))
    response = client.get(
        "/v1/catalog/education", params={"card_ids": [atlas, travelone]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["catalog_snapshot_version"]
    assert [c["card_name"] for c in body["cards"]] == ["Atlas", "TravelOne"]
    assert [p["program_name"] for p in body["shared_partners"]] == ["KrisFlyer"]


def test_education_unknown_card_is_404(client: TestClient) -> None:
    from uuid import uuid4

    response = client.get("/v1/catalog/education", params={"card_ids": [str(uuid4())]})
    assert response.status_code == 404


def test_education_requires_at_least_one_card(client: TestClient) -> None:
    response = client.get("/v1/catalog/education")
    assert response.status_code == 422


def test_education_story_without_model_is_null(client: TestClient) -> None:
    """No LLM ⇒ the framing endpoint returns null and 200 — the deterministic
    education render is the fallback, so null is the honest norm."""
    atlas = str(seed_id("card", "axis-atlas"))
    response = client.get("/v1/catalog/education/story", params={"card_ids": [atlas]})
    assert response.status_code == 200
    assert response.json() == {"narrative": None}


def test_education_facts_allowlist_covers_every_stated_number() -> None:
    """The fact sheet's allow-sets must back every figure its own lines state
    (rates, caps, ratios, fees, days) — otherwise a faithful LLM echo would be
    rejected. Golden spot-checks trace to the seed YAML (Atlas: an integral
    rate, a capped travel rule, a 1:2 link with fee; DCB's 16.65 portal rate
    must survive as a decimal token); the self-consistency sweep then runs
    over the FULL catalog (every card, incl. Amex Plat Charge's 2.50 base
    rate) so a refactor that breaks the build-and-allow-at-one-site invariant
    fails here whatever card it breaks on."""
    import re
    from decimal import Decimal
    from pathlib import Path

    from app.api.catalog import education_facts
    from app.knowledge.education import wallet_education
    from app.knowledge.seed_catalog import load_seed_snapshot

    snapshot = load_seed_snapshot(Path("seeds/catalog"))
    payload = wallet_education(snapshot, tuple(card.id for card in snapshot.cards))
    facts = education_facts(payload)
    # Atlas: travel 5/₹100 capped ₹2L/month; KrisFlyer 1:2, 30k cap, ₹235 fee.
    assert {5, 2, 200_000, 1, 30_000, 235, 100} <= set(facts.allowed_numbers)
    # Non-integral rates are verbatim decimal tokens: DCB's SmartBuy portal
    # 16.65 and Amex Platinum Charge's 2.5 base rate.
    assert "16.65" in facts.allowed_decimals
    assert "2.5" in facts.allowed_decimals
    # Every number stated in the lines is allow-listed (no self-contradiction).
    for line in (*facts.card_lines, *facts.shared_lines):
        for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", line):
            token = raw.replace(",", "")
            if token in facts.allowed_decimals:
                continue
            assert int(Decimal(token)) in facts.allowed_numbers, (token, line)


# ── CORS (the browser Goal Simulator crosses origins) ────────────────────


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    """A simulate call from the Next dev origin gets the allow-origin header,
    so the browser doesn't block the response."""
    origin = "http://localhost:3000"
    response = client.post(
        "/v1/simulations", json=_feasible_body(), headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_preflight_allows_authorization_header(client: TestClient) -> None:
    """The signed-in save sends `Authorization: Bearer` cross-origin. The CORS
    preflight must allow that header, or the browser blocks the request before
    it's ever sent — invisible to non-browser tests."""
    response = client.options(
        "/v1/goals/recommendation/save",
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
    response = client.post("/v1/goals/recommendation/save", json=_feasible_body())
    assert response.status_code == 401


def test_my_goals_requires_auth(client: TestClient) -> None:
    """The saved-goals list is per-user ⇒ no token, no list (401)."""
    response = client.get("/v1/goals")
    assert response.status_code == 401


def test_my_goals_rejects_out_of_range_page_params(snapshot: CatalogSnapshot) -> None:
    """`limit`/`offset` are bounded at the edge (1..100, ≥0) — out-of-range
    values are a 422, never a silently clamped (or unbounded) query."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    import jwt

    from app.config import Settings, get_settings

    secret = "test-secret-that-is-at-least-32-bytes-long!!"
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=secret)
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "iat": now,
         "exp": now + timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as tc:
        for query in ("limit=0", "limit=101", "offset=-1"):
            assert tc.get(f"/v1/goals?{query}", headers=headers).status_code == 422
    app.dependency_overrides.clear()


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
            "/v1/goals/recommendation/save",
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
    # A failed save carries no goal id — the UI must never link to a goal
    # that was not actually written.
    assert body["saved_goal_id"] is None


def test_successful_save_returns_the_goal_id(
    snapshot: CatalogSnapshot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A landed save echoes the persisted goal's id so the client can navigate
    straight to the saved goal instead of re-fetching the whole list."""
    from contextlib import asynccontextmanager
    from datetime import datetime, timedelta
    from uuid import UUID, uuid4

    import jwt

    from app.api import recommend as recommend_module
    from app.config import Settings, get_settings

    persisted_ids: dict[str, UUID] = {}

    async def fake_persist(conn: object, recommendation: object, *, user_id: UUID) -> dict:
        ids = {"goal_id": recommendation.goal.id, "recommendation_id": uuid4()}  # type: ignore[attr-defined]
        persisted_ids.update(ids)
        return ids

    class FakeEngine:
        @asynccontextmanager
        async def begin(self):  # type: ignore[no-untyped-def]
            yield object()

    monkeypatch.setattr(recommend_module, "persist_recommendation", fake_persist)
    monkeypatch.setattr(recommend_module, "get_engine", lambda: FakeEngine())

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
            "/v1/goals/recommendation/save",
            json=_feasible_body(),
            headers={"Authorization": f"Bearer {token}"},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["persisted"] is True
    assert body["saved_goal_id"] == str(persisted_ids["goal_id"])


def test_cors_rejects_unconfigured_origin(client: TestClient) -> None:
    """An origin not in the allow-list gets no allow-origin header echoed back,
    so the browser blocks the cross-origin read — the list actually restricts."""
    response = client.post(
        "/v1/simulations",
        json=_feasible_body(),
        headers={"Origin": "https://evil.example"},
    )
    # The request still succeeds server-side (CORS is a browser enforcement),
    # but the middleware must not bless the foreign origin.
    assert "access-control-allow-origin" not in response.headers
