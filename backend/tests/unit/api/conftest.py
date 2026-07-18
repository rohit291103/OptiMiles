"""API-suite fixtures.

The per-IP rate limiters on the anonymous endpoints are module-level (their
whole point is state that outlives a request), which means their counters
would also accumulate across TESTS — every TestClient request comes from the
same fake client IP, so an unrelated test could trip a 429 purely from suite
ordering. Reset the window state before each test; the rate-limit tests
build their own limiter instances and are unaffected.
"""

import pytest

from app.api import simulations


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    for limiter in (simulations.simulate_limiter, simulations.probe_limiter):
        limiter._windows.clear()
