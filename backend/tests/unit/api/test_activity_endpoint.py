"""/v1/activity — logging spends and lounge visits, and the summary they feed.

No live DB: the repository seam is faked, exactly as the goal-endpoint tests
do. What is proven here is the endpoint's own contract — auth, validation, the
404 posture on unknown or foreign rows, and that the summary carries its
honesty caveat. The arithmetic itself is proven against the real seed catalog
in tests/unit/simulation/test_observed.py.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.domain import CatalogSnapshot
from app.domain.activity import LoungeVisit, SpendEntry
from app.domain.enums import LoungeScope, SpendCategory
from app.main import create_app

_SECRET = "test-jwt-secret-0123456789abcdef0123456789abcdef"
USER = uuid4()


def _token(sub: UUID = USER) -> str:
    return jwt.encode(
        {"sub": str(sub), "aud": "authenticated", "exp": datetime.now(UTC) + timedelta(hours=1)},
        _SECRET,
        algorithm="HS256",
    )


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


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
def infinia(snapshot: CatalogSnapshot) -> UUID:
    return next(c.id for c in snapshot.cards if c.card_name == "Infinia Metal")


@pytest.fixture
def regalia(snapshot: CatalogSnapshot) -> UUID:
    return next(c.id for c in snapshot.cards if c.card_name == "Regalia Gold")


@pytest.fixture
def client(snapshot: CatalogSnapshot, monkeypatch: pytest.MonkeyPatch) -> Any:
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_jwt_secret=_SECRET)
    monkeypatch.setattr("app.api.activity.get_engine", lambda: FakeEngine())

    # The summary also reads renewal months (migration 0010); none set here —
    # tests/unit/api/test_activity_renewal_months.py covers that path.
    async def no_renewal_months(conn: object, **kwargs: Any) -> dict[UUID, int]:
        return {}

    monkeypatch.setattr("app.api.activity.fetch_renewal_months_for_cards", no_renewal_months)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── Auth ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/v1/activity/spend"),
        ("post", "/v1/activity/lounge-visits"),
        ("get", "/v1/activity/spend"),
        ("get", "/v1/activity/lounge-visits"),
        ("get", "/v1/activity/summary?card_ids=" + str(uuid4())),
    ],
)
def test_every_activity_route_requires_auth(client: TestClient, method: str, path: str) -> None:
    """A log is a personal record — unlike Best Card and Portfolio View, none
    of this is anonymous."""
    kwargs = {"json": {}} if method == "post" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


# ── Logging a spend ──────────────────────────────────────────────────────


def test_log_spend_returns_the_stored_entry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, infinia: UUID
) -> None:
    async def fake_add(conn: object, **kwargs: Any) -> SpendEntry:
        return SpendEntry(
            id=uuid4(),
            card_id=kwargs["card_id"],
            occurred_on=kwargs["occurred_on"],
            amount_inr=kwargs["amount_inr"],
            category_slug=kwargs["category_slug"],
            note=kwargs["note"],
        )

    monkeypatch.setattr("app.api.activity.add_spend_entry", fake_add)
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(infinia),
            "occurred_on": "2026-08-20",
            "amount_inr": 45000,
            "category_slug": "travel",
            "note": "Flight to BLR",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["amount_inr"] == 45000
    assert body["category_slug"] == "travel"
    assert body["note"] == "Flight to BLR"


def test_future_dated_spend_is_rejected(client: TestClient, infinia: UUID) -> None:
    """A log records what happened, not what is planned — a future entry would
    count toward a window it has not happened in and inflate a milestone."""
    tomorrow = date.today() + timedelta(days=1)
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(infinia),
            "occurred_on": tomorrow.isoformat(),
            "amount_inr": 1000,
            "category_slug": "travel",
        },
    )
    assert response.status_code == 422
    assert "future" in response.json()["detail"]


def test_todays_spend_is_accepted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, infinia: UUID
) -> None:
    """The boundary: today is not the future."""

    async def fake_add(conn: object, **kwargs: Any) -> SpendEntry:
        return SpendEntry(
            id=uuid4(),
            card_id=kwargs["card_id"],
            occurred_on=kwargs["occurred_on"],
            amount_inr=kwargs["amount_inr"],
            category_slug=kwargs["category_slug"],
        )

    monkeypatch.setattr("app.api.activity.add_spend_entry", fake_add)
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(infinia),
            "occurred_on": date.today().isoformat(),
            "amount_inr": 1000,
            "category_slug": "travel",
        },
    )
    assert response.status_code == 201


def test_unknown_card_is_404_not_a_foreign_key_crash(client: TestClient) -> None:
    """Same posture as /v1/best-card and /v1/portfolio: a stale wallet fails
    loudly and fixably rather than 500ing on the FK."""
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(uuid4()),
            "occurred_on": "2026-08-20",
            "amount_inr": 1000,
            "category_slug": "travel",
        },
    )
    assert response.status_code == 404


@pytest.mark.parametrize("amount", [0, -500])
def test_non_positive_amounts_are_rejected(client: TestClient, infinia: UUID, amount: int) -> None:
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(infinia),
            "occurred_on": "2026-08-20",
            "amount_inr": amount,
            "category_slug": "travel",
        },
    )
    assert response.status_code == 422


def test_category_outside_the_catalog_vocabulary_is_rejected(
    client: TestClient, infinia: UUID
) -> None:
    """Categories are the catalog's closed vocabulary — there is no
    merchant→category mapping to invent a new slug from."""
    response = client.post(
        "/v1/activity/spend",
        headers=_auth(),
        json={
            "card_id": str(infinia),
            "occurred_on": "2026-08-20",
            "amount_inr": 1000,
            "category_slug": "crypto",
        },
    )
    assert response.status_code == 422


# ── Logging a lounge visit ───────────────────────────────────────────────


def test_log_lounge_visit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, regalia: UUID
) -> None:
    async def fake_add(conn: object, **kwargs: Any) -> LoungeVisit:
        return LoungeVisit(
            id=uuid4(),
            card_id=kwargs["card_id"],
            occurred_on=kwargs["occurred_on"],
            scope=kwargs["scope"],
            guest_count=kwargs["guest_count"],
            airport_code=kwargs["airport_code"],
        )

    monkeypatch.setattr("app.api.activity.add_lounge_visit", fake_add)
    response = client.post(
        "/v1/activity/lounge-visits",
        headers=_auth(),
        json={
            "card_id": str(regalia),
            "occurred_on": "2026-08-20",
            "scope": "domestic",
            "guest_count": 1,
            "airport_code": "DEL",
        },
    )
    assert response.status_code == 201
    assert response.json()["airport_code"] == "DEL"
    assert response.json()["guest_count"] == 1


def test_visit_is_accepted_for_a_card_with_no_seeded_entitlement(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, snapshot: CatalogSnapshot
) -> None:
    """Lounge coverage is deliberately partial (4 of 9 cards). Refusing to
    record something the user says happened because our catalog is incomplete
    would be backwards — it simply is not counted against an allowance we do
    not have."""
    atlas = next(c.id for c in snapshot.cards if c.card_name == "Atlas")
    assert not [a for a in snapshot.lounge_access if a.card_id == atlas]

    async def fake_add(conn: object, **kwargs: Any) -> LoungeVisit:
        return LoungeVisit(
            id=uuid4(),
            card_id=kwargs["card_id"],
            occurred_on=kwargs["occurred_on"],
            scope=kwargs["scope"],
            guest_count=kwargs["guest_count"],
        )

    monkeypatch.setattr("app.api.activity.add_lounge_visit", fake_add)
    response = client.post(
        "/v1/activity/lounge-visits",
        headers=_auth(),
        json={"card_id": str(atlas), "occurred_on": "2026-08-20", "scope": "domestic"},
    )
    assert response.status_code == 201


def test_malformed_airport_code_is_rejected(client: TestClient, regalia: UUID) -> None:
    response = client.post(
        "/v1/activity/lounge-visits",
        headers=_auth(),
        json={
            "card_id": str(regalia),
            "occurred_on": "2026-08-20",
            "scope": "domestic",
            "airport_code": "Delhi T3",
        },
    )
    assert response.status_code == 422


# ── Deleting ─────────────────────────────────────────────────────────────


def test_deleting_someone_elses_entry_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The repository delete is user-scoped, so a foreign row and a
    nonexistent one are indistinguishable — which is the point: the response
    must not reveal that a row exists."""

    async def fake_delete(conn: object, **kwargs: Any) -> bool:
        return False

    monkeypatch.setattr("app.api.activity.delete_spend_entry", fake_delete)
    response = client.delete(f"/v1/activity/spend/{uuid4()}", headers=_auth())
    assert response.status_code == 404


def test_successful_delete_is_204(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_delete(conn: object, **kwargs: Any) -> bool:
        return True

    monkeypatch.setattr("app.api.activity.delete_lounge_visit", fake_delete)
    response = client.delete(f"/v1/activity/lounge-visits/{uuid4()}", headers=_auth())
    assert response.status_code == 204


# ── The summary ──────────────────────────────────────────────────────────


def _fake_fetch(spend: tuple[SpendEntry, ...] = (), visits: tuple[LoungeVisit, ...] = ()) -> Any:
    async def fetch(conn: object, **kwargs: Any) -> tuple[Any, Any]:
        return spend, visits

    return fetch


def test_summary_fills_the_holes_portfolio_view_ships_with(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, infinia: UUID
) -> None:
    """Portfolio View states that cap utilisation and milestone progress need
    spend data. This is that data: ₹60,000 logged against Infinia's
    ₹150,000/month SmartBuy travel cap."""
    monkeypatch.setattr(
        "app.api.activity.fetch_activity_for_cards",
        _fake_fetch(
            spend=(
                SpendEntry(
                    id=uuid4(),
                    card_id=infinia,
                    occurred_on=date(2026, 8, 4),
                    amount_inr=60_000,
                    category_slug=SpendCategory.TRAVEL,
                ),
            )
        ),
    )
    response = client.get(
        f"/v1/activity/summary?card_ids={infinia}&as_of=2026-08-20", headers=_auth()
    )
    assert response.status_code == 200
    body = response.json()
    cap = next(c for c in body["caps"] if c["category_slug"] == "travel")
    assert cap["logged_spend_inr"] == 60_000
    assert cap["remaining_inr_at_most"] == 52_500  # ₹1,12,500 cap − ₹60,000 logged
    assert body["logged_spend_total_inr"] == 60_000


def test_summary_carries_the_bound_caveat(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, infinia: UUID
) -> None:
    """Stated server-side, not left to the UI — the same posture as
    /v1/portfolio's own caveat. A client that renders these as exact will
    eventually tell someone they have a lounge visit they do not."""
    monkeypatch.setattr("app.api.activity.fetch_activity_for_cards", _fake_fetch())
    response = client.get(f"/v1/activity/summary?card_ids={infinia}", headers=_auth())
    assert response.status_code == 200
    assert "at least" in response.json()["caveat"]


def test_summary_field_names_carry_their_bounds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, regalia: UUID
) -> None:
    """The wire format itself must not offer an exact-sounding `remaining` —
    a client cannot accidentally render a bound as a fact."""
    monkeypatch.setattr(
        "app.api.activity.fetch_activity_for_cards",
        _fake_fetch(
            visits=(
                LoungeVisit(
                    id=uuid4(),
                    card_id=regalia,
                    occurred_on=date(2026, 7, 10),
                    scope=LoungeScope.DOMESTIC,
                ),
            )
        ),
    )
    response = client.get(
        f"/v1/activity/summary?card_ids={regalia}&as_of=2026-08-20", headers=_auth()
    )
    domestic = next(r for r in response.json()["lounge"] if r["scope"] == "domestic")
    assert domestic["visits_logged_at_least"] == 1
    assert domestic["remaining_at_most"] == 2
    assert "remaining" not in domestic  # only the bounded name exists


def test_summary_rejects_an_unknown_card(client: TestClient) -> None:
    response = client.get(f"/v1/activity/summary?card_ids={uuid4()}", headers=_auth())
    assert response.status_code == 404


def test_summary_requires_at_least_one_card(client: TestClient) -> None:
    response = client.get("/v1/activity/summary", headers=_auth())
    assert response.status_code == 422
