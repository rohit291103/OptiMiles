"""Application settings. The LLM provider lives behind this one setting and is
only ever read inside ai_reasoning/ (build rule 3); ranking weights are a
versioned config file, not code (build rule 5)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENGINE_VERSION = "0.1.0"
"""Stamped onto every simulation_results / recommendation_outputs row (D-2)."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/optimiles"
    llm_provider: Literal["openai", "gemini"] = "openai"
    llm_api_key: str = ""
    llm_model: str = Field(
        default="",
        description="Model id for the provider (e.g. 'gpt-4o-mini', "
        "'gemini-2.0-flash', 'qwen/qwen3-next-80b-a3b-instruct:free'); "
        "empty ⇒ a sensible per-provider default",
    )
    llm_base_url: str = Field(
        default="",
        description="Override the OpenAI-compatible base URL (provider "
        "'openai' only). Empty ⇒ real OpenAI. Set to "
        "'https://openrouter.ai/api/v1' to route through OpenRouter, which "
        "exposes many models (incl. free Qwen/DeepSeek) behind the OpenAI API.",
    )
    ranking_weights_path: Path = Path("config/ranking-weights-v1.yaml")
    requirement_buffer_pct: float = 5.0
    supabase_jwt_secret: str = ""
    """Supabase project JWT secret (Settings → API → JWT Secret). Empty ⇒ auth
    is disabled and authenticated endpoints reject every request. Used to verify
    the HS256 access token the frontend's Supabase session mints (D-4: FastAPI
    uses the service role; this only extracts the caller's real auth.users id)."""
    supabase_jwt_audience: str = "authenticated"
    """The `aud` claim Supabase stamps on a signed-in user's access token."""

    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    """Comma-separated browser origins allowed to call the API. The Next dev
    server (:3000) serves the public Goal Simulator; set production origins via
    the `CORS_ALLOW_ORIGINS` env var. Read through `cors_origins`."""

    @property
    def cors_origins(self) -> list[str]:
        """The origin list, split and trimmed — env values are comma-separated
        strings (pydantic-settings would JSON-decode a tuple-typed field)."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
