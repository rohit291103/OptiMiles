"""`model_from_settings` gating — no key ⇒ no model ⇒ non-LLM paths run.

This is the switch that lets the whole pipeline run with the LLM disabled: an
empty api_key returns None (and never imports pydantic_ai), so intent falls
back to the structured form and narration to templates. A present key
constructs the real adapter lazily.
"""

from app.ai_reasoning import model_from_settings
from app.ai_reasoning._pydanticai import PydanticAIModel
from app.config import Settings


def test_no_api_key_returns_none() -> None:
    assert model_from_settings(Settings(llm_api_key="")) is None


def test_present_key_returns_pydanticai_adapter() -> None:
    model = model_from_settings(Settings(llm_api_key="sk-test", llm_provider="openai"))
    assert isinstance(model, PydanticAIModel)


def test_default_model_name_per_provider() -> None:
    """An empty llm_model resolves to a sensible provider default (no network
    touched — construction is lazy)."""
    openai = PydanticAIModel(Settings(llm_api_key="k", llm_provider="openai"))
    gemini = PydanticAIModel(Settings(llm_api_key="k", llm_provider="gemini"))
    assert openai._model_name == "gpt-4o-mini"
    assert gemini._model_name == "gemini-2.0-flash"


def test_explicit_model_name_wins() -> None:
    model = PydanticAIModel(Settings(llm_api_key="k", llm_provider="openai", llm_model="gpt-4o"))
    assert model._model_name == "gpt-4o"
