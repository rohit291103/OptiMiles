"""The one place in the codebase that imports an LLM client (build rule 3).

`PydanticAIModel` adapts PydanticAI's `Agent` to the `ChatModel` protocol: a
single structured-output call per invocation, schema-enforced to the caller's
`output_type`. The provider (OpenAI / Gemini) is chosen from settings; the
underlying model is constructed lazily so importing this module never reaches
the network, and the whole thing is only ever instantiated when a key is
present (`model_from_settings`).

This module is deliberately thin and untested by the unit suite — it holds no
OptiMiles logic, only the wiring. The intent/narration behaviour is tested
against a fake `ChatModel`; this adapter's correctness is a live-key smoke
test (run manually once keys exist), not a mocked unit test, because mocking
PydanticAI's internals would test the mock, not the integration.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.config import Settings

if TYPE_CHECKING:
    from pydantic_ai.models import Model

_DEFAULT_MODELS = {"openai": "gpt-4o-mini", "gemini": "gemini-2.0-flash"}


class PydanticAIModel:
    """ChatModel backed by a PydanticAI Agent (provider behind config)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.llm_model or _DEFAULT_MODELS[settings.llm_provider]

    def _build_model(self) -> "Model":
        provider = self._settings.llm_provider
        if provider == "openai":
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            return OpenAIChatModel(
                self._model_name,
                provider=OpenAIProvider(api_key=self._settings.llm_api_key),
            )
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(
            self._model_name,
            provider=GoogleProvider(api_key=self._settings.llm_api_key),
        )

    async def complete[StructuredT: BaseModel](
        self,
        *,
        instructions: str,
        prompt: str,
        output_type: type[StructuredT],
    ) -> StructuredT:
        from pydantic_ai import Agent

        agent: Agent[None, StructuredT] = Agent(
            self._build_model(),
            output_type=output_type,
            instructions=instructions,
        )
        result = await agent.run(prompt)
        return result.output
