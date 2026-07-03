"""Stage 10 output: the explanation layer.

The LLM phrases finished numbers; it is never given facts to distort. Every
number and name in the narration is validated against the input payload
(number-echo check); on failure, deterministic templates ship instead —
only eloquence degrades, never truth.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActionItem(BaseModel):
    """One concrete next step, mapped back to a strategy element."""

    model_config = ConfigDict(frozen=True)

    priority: int = Field(ge=1)
    action: str
    impact: str | None = Field(default=None, description="e.g. '+320 miles/month'")
    card_id: UUID | None = None


class RecommendationNarration(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str = Field(description="1–2 sentence TL;DR shown in UI")
    reasoning: str = Field(description="Structured prose over the score breakdown and assumptions")
    action_items: tuple[ActionItem, ...]
    comparison_notes: str | None = Field(
        default=None, description="Why #1 beats the alternatives, from headline differentiators"
    )
    model_version: str = Field(
        description="LLM model id, or 'template-fallback' when templates shipped"
    )
