"""Stage 1 outputs — the LLM's *proposal*, never trusted downstream.

Every field here is re-validated against the catalog in Stage 2 before anything
is persisted or computed. Out-of-vocabulary values become missing_fields, never
pass through.
"""

from pydantic import BaseModel, ConfigDict, Field


class ParsedGoalIntent(BaseModel):
    """Machine-checkable reading of free-form goal text (blueprint Stage 1)."""

    model_config = ConfigDict(frozen=True)

    origin_city: str | None = None
    destination_city: str | None = None
    cabin_class: str | None = None
    program_hint: str | None = None
    timeline_months: int | None = Field(default=None, gt=0)
    num_passengers: int | None = Field(default=None, gt=0)
    missing_fields: tuple[str, ...] = ()
    assumed_fields: tuple[str, ...] = Field(
        default=(), description="Fields defaulted (e.g. origin from profile), flagged honestly"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class ClarificationRequest(BaseModel):
    """One focused question per missing/ambiguous field; loops back to Stage 1."""

    model_config = ConfigDict(frozen=True)

    questions: tuple[str, ...] = Field(min_length=1)
    missing_fields: tuple[str, ...]
