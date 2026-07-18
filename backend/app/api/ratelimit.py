"""Per-IP rate limiting for the anonymous compute-heavy endpoints.

The public simulator runs the full pipeline — seconds of CPU plus an optional
paid LLM call — with no authentication, so an unthrottled client can hog the
single-process server or burn LLM quota. This is a deliberately small
in-process fixed-window limiter: the MVP is one sync process by design (build
rule 7), so an external store (Redis, slowapi's backends) would be
infrastructure ahead of need. Swap the store, not the callers, if the app
ever runs multi-process.

The clock is injected so tests are deterministic (no sleeps); state is a
plain dict pruned lazily on access, bounded by the number of distinct client
IPs seen per window.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status


@dataclass
class RateLimiter:
    """Fixed-window counter per client key.

    `allow(key)` consumes one slot and reports whether the request may
    proceed; `retry_after(key)` is the whole-second remainder of the current
    window (what a 429 should tell the client to wait).
    """

    max_requests: int
    window_seconds: float
    clock: Callable[[], float] = time.monotonic
    prune_threshold: int = 1024
    """Prune expired windows once the table grows past this — the key space
    is client-controlled (IPs, spoofable XFF on direct connections), so
    without pruning the abuse brake would itself be an unbounded-memory
    vector on a public endpoint."""
    _windows: dict[str, tuple[float, int]] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        now = self.clock()
        if len(self._windows) > self.prune_threshold:
            self._prune(now)
        start, count = self._windows.get(key, (now, 0))
        if now - start >= self.window_seconds:
            start, count = now, 0
        if count >= self.max_requests:
            self._windows[key] = (start, count)
            return False
        self._windows[key] = (start, count + 1)
        return True

    def _prune(self, now: float) -> None:
        """Drop every expired window; keys outside their window carry no
        state worth keeping (a returning client just starts a fresh window)."""
        expired = [
            key
            for key, (start, _) in self._windows.items()
            if now - start >= self.window_seconds
        ]
        for key in expired:
            del self._windows[key]

    def retry_after(self, key: str) -> int:
        now = self.clock()
        start, _ = self._windows.get(key, (now, 0))
        remaining = self.window_seconds - (now - start)
        return max(1, int(remaining + 0.999))


def client_ip(request: Request) -> str:
    """The caller's IP for limiting purposes.

    Behind the deployment proxy the socket peer is the proxy itself, so the
    first hop in X-Forwarded-For (the client, as stamped by the platform's
    edge) is preferred. A direct connection falls back to the socket peer.
    Spoofed XFF on a direct connection only lets a client throttle itself
    into someone else's bucket — the failure mode is acceptable for an
    abuse brake (this is not an auth boundary).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def limit_dependency(limiter: RateLimiter) -> Callable[[Request], None]:
    """A FastAPI dependency enforcing `limiter`; 429 + Retry-After when over."""

    def dependency(request: Request) -> None:
        key = client_ip(request)
        if not limiter.allow(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please wait a moment and try again.",
                headers={"Retry-After": str(limiter.retry_after(key))},
            )

    return dependency
