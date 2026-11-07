"""Regression (2026-11-07): Best Card crashed in the browser with
"Cannot read properties of undefined (reading 'split')".

The ETag was snapshot + ENGINE_VERSION + provenance + query — nothing about
the CODE that shapes the payload. The card-first redesign added fields
(partner_name, destinations, best_for, overall_pick) without changing any
of those, so browsers revalidated, got 304, and fed the new UI the old body.

Every ETag'd catalog surface now also carries a digest of its response
model's schema and the source of the modules that compute it.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import deps
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import seed_id
from app.main import create_app


@pytest.fixture
def client(snapshot: CatalogSnapshot) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class _ShapeA(BaseModel):
    a: int


class _ShapeB(BaseModel):
    a: int
    b: int


def test_digest_changes_with_the_response_shape() -> None:
    assert deps.payload_digest(_ShapeA) != deps.payload_digest(_ShapeB)


def test_digest_changes_with_the_computing_code() -> None:
    from app.valuation import best_card, portfolio

    assert deps.payload_digest(_ShapeA, best_card) != deps.payload_digest(_ShapeA, portfolio)


def test_digest_is_deterministic() -> None:
    """sha256, not hash(): identical across workers and restarts."""
    from app.valuation import best_card

    assert deps.payload_digest(_ShapeA, best_card) == deps.payload_digest(_ShapeA, best_card)


def test_the_pre_fix_best_card_etag_no_longer_matches(client: TestClient) -> None:
    """A browser holding the pre-fix ETag for the same query must get the
    new body (200), not a 304 onto a stale shape."""
    card = seed_id("card", "axis-atlas")
    params = {"amount_inr": 10_000, "category": "default", "card_ids": [str(card)]}
    fresh = client.get("/v1/best-card", params=params)
    etag = fresh.headers["ETag"]
    from app.api.best_card import PAYLOAD_DIGEST

    assert PAYLOAD_DIGEST in etag
    stale = etag.replace(f"-{PAYLOAD_DIGEST}", "")
    assert (
        client.get("/v1/best-card", params=params, headers={"If-None-Match": stale}).status_code
        == 200
    )
    assert (
        client.get("/v1/best-card", params=params, headers={"If-None-Match": etag}).status_code
        == 304
    )


def test_portfolio_and_catalog_etags_carry_their_digest(client: TestClient) -> None:
    from app.api import catalog, portfolio

    card = str(seed_id("card", "axis-atlas"))
    assert (
        portfolio.PAYLOAD_DIGEST
        in client.get("/v1/portfolio", params={"card_ids": [card]}).headers["ETag"]
    )
    assert catalog.CARDS_DIGEST in client.get("/v1/catalog/cards").headers["ETag"]
    assert catalog.ROUTES_DIGEST in client.get("/v1/catalog/routes").headers["ETag"]
