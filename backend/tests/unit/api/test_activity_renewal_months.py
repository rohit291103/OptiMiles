"""/v1/activity/renewal-months and the fee-waiver rows on /v1/activity/summary.

Repository seam faked, as in test_activity_endpoint.py. The arithmetic is
proven in tests/unit/simulation/test_observed_fee_waivers.py; this file proves
the endpoint contract — auth, validation, 404 posture, and that the summary
actually passes the user's renewal months and the verification tier through.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.domain import CatalogSnapshot
from app.domain.activity import CardRenewalMonth
from app.knowledge.seed_catalog import seed_id
from app.main import create_app

_SECRET = "test-jwt-secret-0123456789abcdef0123456789abcdef"
USER = uuid4()


def _auth() -> dict[str, str]:
    token = jwt.encode(
        {"sub": str(USER), "aud": "authenticated", "exp": datetime.now(UTC) + timedelta(hours=1)},
        _SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class FakeConn:
    async def __aenter__(self) -> "FakeConn":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeEngine:
    def begin(self) -> FakeConn:
        return FakeConn()

    def connect(self) -> FakeConn:
        return FakeConn()


@pytest.fixture
def regalia(snapshot: CatalogSnapshot) -> UUID:
    return next(c.id for c in snapshot.cards if c.card_name == "Regalia Gold")


@pytest.fixture
def store() -> dict[UUID, int]:
    """An in-memory stand-in for this user's card_renewal_months rows."""
    return {}


@pytest.fixture
def client(
    snapshot: CatalogSnapshot, monkeypatch: pytest.MonkeyPatch, store: dict[UUID, int]
) -> Any:
    async def fake_set(conn: object, *, user_id: UUID, card_id: UUID, renewal_month: int) -> Any:
        assert user_id == USER
        saved = CardRenewalMonth(card_id=card_id, renewal_month=renewal_month)
        store[card_id] = renewal_month
        return saved

    async def fake_list(conn: object, *, user_id: UUID) -> Any:
        assert user_id == USER
        return tuple(CardRenewalMonth(card_id=c, renewal_month=m) for c, m in store.items())

    async def fake_clear(conn: object, *, user_id: UUID, card_id: UUID) -> bool:
        assert user_id == USER
        return store.pop(card_id, None) is not None

    async def fake_fetch(conn: object, *, user_id: UUID, card_ids: Any) -> dict[UUID, int]:
        assert user_id == USER
        return {c: m for c, m in store.items() if c in card_ids}

    async def fake_activity(conn: object, **kwargs: Any) -> Any:
        return (), ()

    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=_SECRET)
    app.dependency_overrides[deps.get_unverified_ids] = lambda: frozenset(
        {seed_id("fee_waiver", "hdfc-regalia-gold")}
    )
    monkeypatch.setattr("app.api.activity.get_engine", lambda: FakeEngine())
    monkeypatch.setattr("app.api.activity.set_renewal_month", fake_set)
    monkeypatch.setattr("app.api.activity.list_renewal_months", fake_list)
    monkeypatch.setattr("app.api.activity.clear_renewal_month", fake_clear)
    monkeypatch.setattr("app.api.activity.fetch_renewal_months_for_cards", fake_fetch)
    monkeypatch.setattr("app.api.activity.fetch_activity_for_cards", fake_activity)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/activity/renewal-months"),
        ("put", f"/v1/activity/renewal-months/{uuid4()}"),
        ("delete", f"/v1/activity/renewal-months/{uuid4()}"),
    ],
)
def test_renewal_month_routes_require_auth(client: TestClient, method: str, path: str) -> None:
    kwargs = {"json": {"renewal_month": 3}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_set_then_list_then_clear(client: TestClient, regalia: UUID) -> None:
    put = client.put(
        f"/v1/activity/renewal-months/{regalia}", headers=_auth(), json={"renewal_month": 3}
    )
    assert put.status_code == 200
    assert put.json() == {"card_id": str(regalia), "renewal_month": 3}

    listed = client.get("/v1/activity/renewal-months", headers=_auth())
    assert listed.json() == {"renewal_months": [{"card_id": str(regalia), "renewal_month": 3}]}

    assert (
        client.delete(f"/v1/activity/renewal-months/{regalia}", headers=_auth()).status_code == 204
    )
    # Clearing twice is a 404, like deleting a log entry that is not there.
    assert (
        client.delete(f"/v1/activity/renewal-months/{regalia}", headers=_auth()).status_code == 404
    )


@pytest.mark.parametrize("month", [0, 13, "march"])
def test_an_impossible_month_is_a_422(client: TestClient, regalia: UUID, month: object) -> None:
    response = client.put(
        f"/v1/activity/renewal-months/{regalia}", headers=_auth(), json={"renewal_month": month}
    )
    assert response.status_code == 422


def test_an_unknown_card_is_a_404(client: TestClient) -> None:
    response = client.put(
        f"/v1/activity/renewal-months/{uuid4()}", headers=_auth(), json={"renewal_month": 3}
    )
    assert response.status_code == 404


def test_the_caveat_warns_that_waiver_counts_include_excluded_spend(
    client: TestClient, regalia: UUID
) -> None:
    caveat = client.get(f"/v1/activity/summary?card_ids={regalia}", headers=_auth()).json()[
        "caveat"
    ]
    assert "may include spend the issuer excludes" in caveat
    assert "reached on your log, subject to the exclusions" in caveat


def test_the_summary_tracks_a_waiver_once_the_month_is_known(
    client: TestClient, regalia: UUID
) -> None:
    before = client.get(f"/v1/activity/summary?card_ids={regalia}", headers=_auth()).json()
    (row,) = before["fee_waivers"]
    assert row["coverage"] == "needs_renewal_month"
    assert row["count"] is None
    assert row["waiver"]["threshold_inr"] == 400_000
    # The tier override above flags this waiver — the flag reaches the wire.
    assert row["needs_verification"] is True

    client.put(f"/v1/activity/renewal-months/{regalia}", headers=_auth(), json={"renewal_month": 3})
    after = client.get(
        f"/v1/activity/summary?card_ids={regalia}&as_of=2026-11-02", headers=_auth()
    ).json()
    (row,) = after["fee_waivers"]
    assert row["coverage"] == "tracked"
    assert row["renewal_month"] == 3
    assert row["count"]["window"]["label"] == "Apr 2026–Feb 2027"
    assert row["count"]["renewal_label"] == "Mar 2027"
    assert row["count"]["remaining_inr_at_most"] == 400_000
    assert row["count"]["status"] == "not_proven"
