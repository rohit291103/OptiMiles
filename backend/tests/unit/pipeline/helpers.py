"""Shared builders for the pipeline tests: a resolved goal from the seed
catalog, and a scripted ChatModel double (the ai_reasoning conftest fake isn't
visible to this package)."""

from collections.abc import Callable
from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.domain import (
    CatalogSnapshot,
    GoalResolution,
    ParsedGoalIntent,
    TravelGoal,
)
from app.knowledge.goal_resolution import resolve_goal


class FakeChatModel:
    """Scripted ChatModel double. `responder` maps the call to a model
    instance, or raises to simulate an LLM failure/timeout."""

    def __init__(self, responder: Callable[[type[BaseModel]], BaseModel]) -> None:
        self._responder = responder
        self.calls: list[type[BaseModel]] = []

    async def complete(
        self, *, instructions: str, prompt: str, output_type: type[BaseModel]
    ) -> BaseModel:
        self.calls.append(output_type)
        return self._responder(output_type)


def make_goal(
    snapshot: CatalogSnapshot,
    *,
    today: date,
    timeline_months: int = 8,
    num_passengers: int = 1,
    user_id: UUID | None = None,
    origin_city: str = "Hyderabad",
    destination_city: str = "Singapore",
) -> TravelGoal:
    """A resolved, persist-shaped TravelGoal against the real seed catalog."""
    intent = ParsedGoalIntent(
        origin_city=origin_city,
        destination_city=destination_city,
        cabin_class="business",
        timeline_months=timeline_months,
        num_passengers=num_passengers,
        confidence=0.95,
    )
    resolution = resolve_goal(intent, snapshot, today=today)
    assert isinstance(resolution, GoalResolution)
    return TravelGoal(id=uuid4(), user_id=user_id or uuid4(), **resolution.model_dump())
