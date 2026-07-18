"""Request logging + request-id middleware.

The 30s pipeline budget is a product SLO — when a request runs long, the log
line with its duration is the first (and currently only) diagnostic. Every
response also carries an `X-Request-ID` so a user-reported failure can be
matched to its log line.
"""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as tc:
        yield tc


def test_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_supplied_request_id_is_echoed(client: TestClient) -> None:
    """A caller-supplied id (e.g. from the frontend or a proxy) is kept, so
    traces correlate across hops instead of being re-minted here."""
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


def test_request_is_logged_with_duration(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.api.observability"):
        client.get("/health")
    line = next(r for r in caplog.records if "GET /health" in r.getMessage())
    message = line.getMessage()
    assert "status=200" in message
    assert "duration_ms=" in message
    assert "request_id=" in message
