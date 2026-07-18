"""Per-IP rate limiting on the anonymous compute-heavy endpoints.

The public simulator runs the full pipeline (seconds of CPU + an optional LLM
call) with no auth — without a bound, one client can hog the single-process
server or burn paid LLM quota. The limiter is a deterministic in-process
fixed window (no external store — the MVP is one process by design, build
rule 7); the clock is injected so these tests never sleep.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.ratelimit import RateLimiter
from app.domain import CatalogSnapshot
from app.main import create_app

# ── The limiter itself (deterministic, injected clock) ────────────────────


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_then_blocks() -> None:
    clock = Clock()
    limiter = RateLimiter(max_requests=3, window_seconds=60, clock=clock)
    assert [limiter.allow("1.2.3.4") for _ in range(3)] == [True, True, True]
    assert limiter.allow("1.2.3.4") is False


def test_window_expiry_resets_the_budget() -> None:
    clock = Clock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=clock)
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False
    clock.now += 61
    assert limiter.allow("1.2.3.4") is True


def test_clients_are_isolated() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=Clock())
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("5.6.7.8") is True
    assert limiter.allow("1.2.3.4") is False


def test_retry_after_reports_the_window_remainder() -> None:
    clock = Clock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.allow("1.2.3.4")
    clock.now += 10
    assert limiter.retry_after("1.2.3.4") == 50


def test_expired_windows_are_pruned_so_memory_stays_bounded() -> None:
    """The key space is client-controlled (IPs / spoofable XFF), so the
    limiter must not accumulate one entry per key forever — expired windows
    are dropped once the table passes the prune threshold."""
    clock = Clock()
    limiter = RateLimiter(
        max_requests=1, window_seconds=60, clock=clock, prune_threshold=100
    )
    for i in range(150):
        limiter.allow(f"10.0.0.{i}")
    assert len(limiter._windows) == 150  # all still within their window
    clock.now += 61  # every window expires
    limiter.allow("fresh-client")
    assert len(limiter._windows) == 1  # expired entries pruned, newcomer kept


# ── Wired into the endpoint ───────────────────────────────────────────────


@pytest.fixture
def strict_client(snapshot: CatalogSnapshot) -> Iterator[TestClient]:
    """A client whose simulate limiter allows exactly one request."""
    from app.api import simulations

    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    app.dependency_overrides[simulations.simulate_limit] = (
        simulations.limit_dependency(RateLimiter(max_requests=1, window_seconds=60))
    )
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def _body() -> dict:
    return {
        "intent": {
            "origin_city": "Hyderabad",
            "destination_city": "Singapore",
            "cabin_class": "business",
            "timeline_months": 8,
            "num_passengers": 1,
            "confidence": 0.95,
        },
        "wallet": [],
        "spend_profile": [{"category_slug": "travel", "monthly_spend_inr": 60000}],
    }


def test_burst_gets_429_with_retry_after(strict_client: TestClient) -> None:
    assert strict_client.post("/v1/simulations", json=_body()).status_code == 200
    blocked = strict_client.post("/v1/simulations", json=_body())
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_catalog_cards_revalidates_via_etag(strict_client: TestClient) -> None:
    """The cards payload is a pure function of the snapshot, so the snapshot
    version doubles as an ETag — a client holding the current version gets a
    bodyless 304 until the catalog actually changes."""
    first = strict_client.get("/v1/catalog/cards")
    etag = first.headers.get("etag")
    assert etag
    revalidated = strict_client.get("/v1/catalog/cards", headers={"If-None-Match": etag})
    assert revalidated.status_code == 304
    assert revalidated.headers["etag"] == etag
