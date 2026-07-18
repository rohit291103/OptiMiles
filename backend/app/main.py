"""FastAPI application factory. Sync single-request pipeline — no queues,
workers, or events (build rule 7)."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.catalog import router as catalog_router
from app.api.goals import router as goals_router
from app.api.health import router as health_router
from app.api.observability import log_requests
from app.api.simulations import router as simulations_router
from app.config import get_settings


def create_app() -> FastAPI:
    # Uvicorn's --log-level configures only its own loggers; without a root
    # config the app's INFO lines (request log, narration fallbacks) are
    # silently dropped in production. basicConfig is a no-op if the runner
    # already configured logging.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    app = FastAPI(
        title="OptiMiles API",
        version="0.1.0",
        description="Deterministic reward-optimization pipeline for Indian travel rewards.",
    )
    # The Goal Simulator is a browser call from the Next site, so the API's
    # read/simulate surface is CORS-open to the configured origins. `Content-Type`
    # for the JSON body; `Authorization` so the signed-in save (a Bearer-token
    # cross-origin POST) survives the browser preflight. DELETE is listed so the
    # dashboard's "delete goal" preflight passes — without it Starlette answers
    # the OPTIONS preflight 400 and the browser blocks the DELETE before it's
    # sent. No cookies/credentials cross the boundary — the token is an explicit
    # header, not a cookie.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    # One log line per request (method, path, status, duration, request id) —
    # the diagnostic for the 30s pipeline budget; see api/observability.py.
    app.middleware("http")(log_requests)
    # Product API is versioned under /v1 so a future breaking change can ship
    # side-by-side instead of breaking existing clients. /health stays at the
    # root: liveness probes are infrastructure, not part of the product API.
    app.include_router(health_router)
    app.include_router(goals_router, prefix="/v1")
    app.include_router(simulations_router, prefix="/v1")
    app.include_router(catalog_router, prefix="/v1")
    return app


app = create_app()
