"""Application settings. The LLM provider lives behind this one setting and is
only ever read inside ai_reasoning/ (build rule 3); ranking weights are a
versioned config file, not code (build rule 5)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ENGINE_VERSION = "0.1.0"
"""Stamped onto every simulation_results / recommendation_outputs row (D-2)."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/optimiles"
    llm_provider: Literal["openai", "gemini"] = "openai"
    llm_api_key: str = ""
    ranking_weights_path: Path = Path("config/ranking-weights-v1.yaml")
    requirement_buffer_pct: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
