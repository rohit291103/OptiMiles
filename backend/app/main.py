"""FastAPI application factory. Sync single-request pipeline — no queues,
workers, or events (build rule 7)."""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="OptiMiles API",
        version="0.1.0",
        description="Deterministic reward-optimization pipeline for Indian travel rewards.",
    )
    app.include_router(health_router)
    return app


app = create_app()
