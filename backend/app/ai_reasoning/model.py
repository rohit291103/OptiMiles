"""The one seam between OptiMiles and an LLM.

Both AI stages (intent extraction, narration) depend ONLY on the `ChatModel`
protocol below — a single structured-output call. Production supplies a
PydanticAI-backed adapter (`_pydanticai.py`); tests supply a fake; and when no
provider is configured, `model_from_settings()` returns `None` and the callers
take their non-LLM path (structured-form intent, template narration). This is
how build rule 3 ("only ai_reasoning/ touches an LLM") stays a one-import
truth: the sole `pydantic_ai` import lives in the adapter, constructed lazily
and only when a key is actually present.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import Settings

StructuredT = TypeVar("StructuredT", bound=BaseModel)


class ChatModel(Protocol):
    """A single constrained call: prompt + instructions → a validated model.

    The implementation guarantees the returned object is an instance of
    `output_type` (schema-enforced) or raises. It never sees catalog data it
    wasn't handed in the prompt — the callers decide what facts to include.
    """

    async def complete(
        self,
        *,
        instructions: str,
        prompt: str,
        output_type: type[StructuredT],
    ) -> StructuredT: ...


def model_from_settings(settings: Settings) -> ChatModel | None:
    """The configured LLM, or None when disabled (no key). None is a
    first-class state: the pipeline runs fully on it, degrading only
    eloquence (narration) and the natural-language door (intent), never
    correctness."""
    if not settings.llm_api_key:
        return None
    from app.ai_reasoning._pydanticai import PydanticAIModel

    return PydanticAIModel(settings)
