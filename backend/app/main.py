"""FastAPI application factory. Sync single-request pipeline — no queues,
workers, or events (build rule 7)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.catalog import router as catalog_router
from app.api.goals import router as goals_router
from app.api.health import router as health_router
from app.api.simulations import router as simulations_router
from app.config import get_settings


def create_app() -> FastAPI:
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
    app.include_router(health_router)
    app.include_router(goals_router)
    app.include_router(simulations_router)
    app.include_router(catalog_router)
    return app


app = create_app()
