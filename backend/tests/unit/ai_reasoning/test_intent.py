"""Stage 1 — intent extraction, LLM mocked.

Contract (not exact wording): the LLM PROPOSES a reading of free-form text;
this stage re-validates it against the catalog vocabulary before returning,
so an out-of-vocabulary value can never pass downstream — it becomes a
`missing_field` / clarification. Origin may be defaulted from the user
profile (flagged `assumed`); nothing else is ever invented. With the LLM
disabled (model=None), the stage returns a clarification asking for all
fields — the structured-form door, never a guess.
"""

from app.ai_reasoning.intent import ScopeRefusal, extract_intent
from app.domain import CatalogSnapshot, ClarificationRequest, ParsedGoalIntent

from .conftest import FakeChatModel, always, raises


def _llm_intent(**overrides: object) -> ParsedGoalIntent:
    """What the LLM proposes — confidence high unless a test lowers it."""
    base = dict(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=8,
        num_passengers=2,
        confidence=0.95,
    )
    base.update(overrides)
    return ParsedGoalIntent(**base)  # type: ignore[arg-type]


async def _extract(snapshot: CatalogSnapshot, model: object | None, text: str, **kwargs: object):
    return await extract_intent(text, snapshot, model=model, **kwargs)  # type: ignore[arg-type]


# ── Happy path + re-validation ────────────────────────────────────────────


async def test_valid_intent_passes_through(snapshot: CatalogSnapshot) -> None:
    model = FakeChatModel(always(_llm_intent()))
    result = await _extract(snapshot, model, "biz to Singapore from Hyderabad in 8 months, 2 of us")
    assert isinstance(result, ParsedGoalIntent)
    assert result.destination_city == "Singapore"
    assert result.cabin_class == "business"
    assert result.missing_fields == ()


async def test_llm_prompt_carries_only_vocabulary_not_ratios(snapshot: CatalogSnapshot) -> None:
    """The LLM sees supported city/cabin NAMES to normalize against — never
    reward rates, ratios, or miles (build rule 3 spirit: no facts to distort)."""
    model = FakeChatModel(always(_llm_intent()))
    await _extract(snapshot, model, "business to singapore")
    (instructions, prompt, _) = model.calls[0]
    haystack = (instructions + prompt).lower()
    assert "singapore" in haystack and "business" in haystack
    for forbidden in ("ratio", "16.65", "miles_per", "krisflyer miles", "earn_rate"):
        assert forbidden not in haystack


async def test_out_of_vocabulary_destination_becomes_clarification(
    snapshot: CatalogSnapshot,
) -> None:
    """LLM confidently returns 'Tokyo' (not an MVP destination). Re-validation
    catches it — it must NOT pass through as a real destination."""
    model = FakeChatModel(always(_llm_intent(destination_city="Tokyo")))
    result = await _extract(snapshot, model, "business to Tokyo from Hyderabad in 8 months for 2")
    assert isinstance(result, ClarificationRequest)
    assert "destination_city" in result.missing_fields


async def test_out_of_vocabulary_cabin_becomes_clarification(snapshot: CatalogSnapshot) -> None:
    model = FakeChatModel(always(_llm_intent(cabin_class="sleeper pod")))
    result = await _extract(snapshot, model, "sleeper pod to Singapore from Delhi in 6 months, 1")
    assert isinstance(result, ClarificationRequest)
    assert "cabin_class" in result.missing_fields


async def test_missing_field_from_llm_becomes_clarification(snapshot: CatalogSnapshot) -> None:
    """LLM honestly reports it couldn't find the timeline → we ask for it,
    not invent one."""
    model = FakeChatModel(
        always(_llm_intent(timeline_months=None, missing_fields=("timeline_months",)))
    )
    result = await _extract(snapshot, model, "business to Singapore from Mumbai for 2 people")
    assert isinstance(result, ClarificationRequest)
    assert "timeline_months" in result.missing_fields


# ── Origin defaulting (the one permitted assumption) ──────────────────────


async def test_origin_defaults_from_profile_city_flagged_assumed(
    snapshot: CatalogSnapshot,
) -> None:
    """LLM returns no origin; the user's profile city fills it, flagged
    `assumed` so narration can say 'assumed you fly from Pune'."""
    model = FakeChatModel(always(_llm_intent(origin_city=None)))
    result = await _extract(
        snapshot,
        model,
        "business to Singapore in 8 months for 2",
        profile_city="Pune",
    )
    assert isinstance(result, ParsedGoalIntent)
    assert result.origin_city == "Pune"
    assert "origin_city" in result.assumed_fields


async def test_no_origin_and_no_profile_asks(snapshot: CatalogSnapshot) -> None:
    model = FakeChatModel(always(_llm_intent(origin_city=None)))
    result = await _extract(snapshot, model, "business to Singapore in 8 months for 2")
    assert isinstance(result, ClarificationRequest)
    assert "origin_city" in result.missing_fields


# ── Scope refusal ─────────────────────────────────────────────────────────


async def test_out_of_scope_request_is_refused_not_parsed(snapshot: CatalogSnapshot) -> None:
    """'optimize my taxes' → scope-refusal, pipeline never starts. The LLM
    signals this by low confidence + empty travel fields; we don't dress it
    up as a travel goal."""
    model = FakeChatModel(
        always(
            ParsedGoalIntent(
                confidence=0.05,
                missing_fields=(
                    "destination_city",
                    "cabin_class",
                    "timeline_months",
                    "num_passengers",
                ),
            )
        )
    )
    result = await _extract(snapshot, model, "optimize my taxes for this year")
    assert isinstance(result, ScopeRefusal)
    assert result.message


# ── LLM unavailable ───────────────────────────────────────────────────────


async def test_llm_disabled_returns_full_clarification(snapshot: CatalogSnapshot) -> None:
    """model=None (no API key): the natural-language door is closed; the
    stage asks for every field (the frontend's structured form). Never a
    guess, never a crash."""
    result = await _extract(snapshot, None, "biz to Singapore from Hyderabad in 8 months, 2")
    assert isinstance(result, ClarificationRequest)
    assert set(result.missing_fields) == {
        "origin_city",
        "destination_city",
        "cabin_class",
        "timeline_months",
        "num_passengers",
    }


async def test_llm_failure_falls_back_to_clarification(snapshot: CatalogSnapshot) -> None:
    """LLM raises (timeout/refusal) → structured-form fallback, not a 500."""
    model = FakeChatModel(raises(RuntimeError("upstream timeout")))
    result = await _extract(snapshot, model, "business to Singapore from Hyderabad in 8 months, 2")
    assert isinstance(result, ClarificationRequest)


# ── Determinism of the re-validation layer ────────────────────────────────


async def test_revalidation_is_deterministic(snapshot: CatalogSnapshot) -> None:
    model = FakeChatModel(always(_llm_intent(destination_city="Tokyo")))
    first = await _extract(snapshot, model, "x")
    model2 = FakeChatModel(always(_llm_intent(destination_city="Tokyo")))
    second = await _extract(snapshot, model2, "x")
    assert first == second
