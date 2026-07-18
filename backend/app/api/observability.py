"""Request logging + request ids — the API's minimal observability layer.

One INFO line per request: method, path, status, wall-clock duration, and a
request id. The 30-second pipeline budget (Scope v2) is a product SLO, and
this line is what makes a breach diagnosable in production without attaching
a profiler. The id is echoed back as `X-Request-ID` (a caller-supplied one is
kept, so traces correlate across the frontend/proxy hop); failures a user
reports can be matched to their exact log line.

Deliberately not metrics/tracing infrastructure — one process, one log
stream (build rule 7). Graduate to structured logging or OTel only when
there's a collector to receive it.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # The exception still propagates to the error handler; the log line
        # must exist even when the response never materialized.
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "%s %s status=500 duration_ms=%.0f request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
        )
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s status=%d duration_ms=%.0f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response
