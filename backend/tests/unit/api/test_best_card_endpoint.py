"""GET /v1/best-card — the Phase 1 daily-surface endpoint.

Deliberately anonymous: no auth, no DB, no LLM. The roadmap makes Best Card
available signed-out with a real card picker, so these tests exercise it the
way an unauthenticated visitor will.

The arithmetic itself is proven in tests/unit/valuation/test_best_card.py;
what is under test here is the HTTP contract — defaulting, validation,
error mapping, and caching.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import seed_id
from app.main import create_app

INFINIA = str(seed_id("card", "hdfc-infinia"))
REGALIA = str(seed_id("card", "hdfc-regalia-gold"))
TRAVELONE = str(seed_id("card", "hsbc-travelone"))
SBI = str(seed_id("card", "sbi-cashback"))
MAHARAJA = str(seed_id("partner", "maharaja-club"))
KRISFLYER = str(seed_id("partner", "krisflyer"))


@pytest.fixture
def client(snapshot: CatalogSnapshot) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _get(client: TestClient, **params) -> dict:
    response = client.get("/v1/best-card", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_no_program_is_assumed_when_none_is_given(client: TestClient) -> None:
    """The endpoint used to substitute KrisFlyer here, and the UI printed that
    name to users who had never mentioned it. Omitting the target is now a
    legitimate state with a points-only answer — see CLAUDE.md → *Never Assume
    the User's Goal*."""
    body = _get(client, amount_inr=10_000, category="default", card_ids=[INFINIA])
    assert body["target_program_name"] is None
    assert body["target_program_id"] is None
    assert body["ranking_basis"] == "points"
    assert body["ranked"][0]["points_earned"] == 333
    assert body["ranked"][0]["miles_earned"] is None


def test_points_only_answer_offers_the_reachable_programs(client: TestClient) -> None:
    """So the client can ask, instead of guessing."""
    body = _get(client, amount_inr=10_000, category="default", card_ids=[INFINIA])
    assert [reach["program_name"] for reach in body["partner_reach"]] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Maharaja Club",
        "Marriott Bonvoy",
    ]


def test_choosing_a_program_switches_to_miles(client: TestClient) -> None:
    body = _get(
        client,
        amount_inr=10_000,
        category="default",
        card_ids=[INFINIA],
        target_program_id=KRISFLYER,
    )
    assert body["ranking_basis"] == "miles"
    assert body["target_program_name"] == "KrisFlyer"
    assert body["ranked"][0]["miles_earned"] == 333


def test_ranks_by_miles_not_points(client: TestClient) -> None:
    """The endpoint-level guard on the central invariant: Regalia earns more
    points than TravelOne and must still rank below it."""
    body = _get(
        client,
        amount_inr=10_000,
        category="default",
        card_ids=[REGALIA, TRAVELONE],
        target_program_id=KRISFLYER,
    )
    winner, runner_up = body["ranked"]
    assert winner["card_name"] == "TravelOne"
    assert runner_up["points_earned"] > winner["points_earned"]


def test_accepts_an_explicit_target_program(client: TestClient) -> None:
    body = _get(
        client,
        amount_inr=10_000,
        category="default",
        card_ids=[INFINIA],
        target_program_id=MAHARAJA,
    )
    assert body["target_program_name"] == "Maharaja Club"


def test_unroutable_card_is_reported_separately(client: TestClient) -> None:
    """Only meaningful once a program is chosen — with none chosen there is no
    route being asked about, so nothing can be off it."""
    body = _get(
        client,
        amount_inr=10_000,
        category="default",
        card_ids=[INFINIA, SBI],
        target_program_id=KRISFLYER,
    )
    assert [o["card_name"] for o in body["ranked"]] == ["Infinia Metal"]
    (unroutable,) = body["unroutable"]
    assert unroutable["card_name"] == "Cashback"
    assert unroutable["miles_earned"] is None


def test_response_carries_the_snapshot_version(
    client: TestClient, snapshot: CatalogSnapshot
) -> None:
    body = _get(client, amount_inr=10_000, category="default", card_ids=[INFINIA])
    assert body["catalog_snapshot_version"] == snapshot.version


def test_etag_revalidation_returns_304(client: TestClient) -> None:
    params = {"amount_inr": 10_000, "category": "default", "card_ids": [INFINIA]}
    first = client.get("/v1/best-card", params=params)
    etag = first.headers["ETag"]

    second = client.get("/v1/best-card", params=params, headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_unknown_card_is_404_not_a_silent_drop(client: TestClient) -> None:
    """A stale wallet must fail loudly — silently omitting a card would show
    a confident ranking over a wallet the user did not ask about."""
    response = client.get(
        "/v1/best-card",
        params={
            "amount_inr": 10_000,
            "category": "default",
            "card_ids": [str(seed_id("card", "no-such-card"))],
        },
    )
    assert response.status_code == 404


@pytest.mark.parametrize("amount", [0, -100])
def test_non_positive_amount_is_422(client: TestClient, amount: int) -> None:
    response = client.get(
        "/v1/best-card",
        params={"amount_inr": amount, "category": "default", "card_ids": [INFINIA]},
    )
    assert response.status_code == 422


def test_empty_wallet_is_422(client: TestClient) -> None:
    response = client.get("/v1/best-card", params={"amount_inr": 10_000, "category": "default"})
    assert response.status_code == 422


def test_unknown_category_is_422(client: TestClient) -> None:
    response = client.get(
        "/v1/best-card",
        params={"amount_inr": 10_000, "category": "yachts", "card_ids": [INFINIA]},
    )
    assert response.status_code == 422
