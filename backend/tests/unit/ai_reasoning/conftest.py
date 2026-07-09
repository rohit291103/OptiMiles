"""A fake ChatModel so the AI-reasoning tests never touch a network or a key.

`FakeChatModel` returns a scripted structured object (or raises), and records
the instructions/prompt it was handed so tests can assert the LLM was given
ONLY the facts it's allowed to see (no ratios, no catalog internals).
"""

from collections.abc import Callable

from pydantic import BaseModel


class FakeChatModel:
    """Scripted ChatModel double. `responder` maps (instructions, prompt,
    output_type) → a model instance, or raises to simulate LLM failure."""

    def __init__(self, responder: Callable[[str, str, type[BaseModel]], BaseModel]) -> None:
        self._responder = responder
        self.calls: list[tuple[str, str, type[BaseModel]]] = []

    async def complete(
        self, *, instructions: str, prompt: str, output_type: type[BaseModel]
    ) -> BaseModel:
        self.calls.append((instructions, prompt, output_type))
        return self._responder(instructions, prompt, output_type)


def always(value: BaseModel) -> Callable[[str, str, type[BaseModel]], BaseModel]:
    def responder(instructions: str, prompt: str, output_type: type[BaseModel]) -> BaseModel:
        return value

    return responder


def raises(exc: Exception) -> Callable[[str, str, type[BaseModel]], BaseModel]:
    def responder(instructions: str, prompt: str, output_type: type[BaseModel]) -> BaseModel:
        raise exc

    return responder
