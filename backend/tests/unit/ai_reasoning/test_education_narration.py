"""Education framing (guided-flow decision 10, slice 10) — the LLM may only
PHRASE the wallet's reward story; every number it utters must trace to the
deterministic fact sheet, and any failure degrades to None (the wizard's
deterministic education render IS the template fallback, so nothing blocks).

Lighter-touch AI-layer tests per the tdd skill: contract, not wording.
"""

import pytest

from app.ai_reasoning.education import (
    EducationFacts,
    EducationStoryDraft,
    narrate_education,
)
from tests.unit.ai_reasoning.conftest import FakeChatModel, always


def _facts() -> EducationFacts:
    return EducationFacts(
        card_lines=(
            "Atlas (Axis) earns EDGE Miles. Direct airlines, hotels and travel: "
            "5 pts/₹100 up to ₹200000/month. All other spend: 2 pts/₹100. "
            "Transfers: KrisFlyer at 1:2 (cap 30000 pts/year, fee ₹235, 1-3 days).",
            "Diners Club Black Metal (HDFC) earns HDFC Reward Points. Travel via "
            "SmartBuy portal: 16.65 pts/₹100.",
        ),
        shared_lines=("2 of your cards (Atlas, Diners Club Black Metal) reach KrisFlyer.",),
        allowed_numbers=frozenset({1, 2, 3, 5, 100, 235, 30000, 200000}),
        allowed_decimals=frozenset({"16.65"}),
        allowed_names=frozenset({"Atlas", "Diners Club Black Metal", "KrisFlyer"}),
        catalog_card_names=frozenset({"Atlas", "Diners Club Black Metal", "Magnus for Burgundy"}),
    )


async def test_no_model_returns_none() -> None:
    assert await narrate_education(_facts(), model=None) is None


async def test_faithful_story_is_returned() -> None:
    story = (
        "Your Atlas earns 5 pts per ₹100 on travel and moves to KrisFlyer at "
        "1:2, while the Diners Club Black Metal earns 16.65 pts/₹100 through "
        "the portal - both feed the same KrisFlyer balance."
    )
    model = FakeChatModel(always(EducationStoryDraft(story=story)))
    assert await narrate_education(_facts(), model=model) == story
    assert len(model.calls) == 1


async def test_fabricated_number_regenerates_then_gives_up() -> None:
    """An integer the facts can't back ⇒ one regeneration; a second failure ⇒
    None — the deterministic step renders alone, never a wrong number."""
    bad = EducationStoryDraft(story="Atlas earns 7 pts per ₹100 on travel.")
    model = FakeChatModel(always(bad))
    assert await narrate_education(_facts(), model=model) is None
    assert len(model.calls) == 2


async def test_fabricated_decimal_is_rejected() -> None:
    """A decimal-glued figure ('16.7') isn't laundered by its integer part."""
    bad = EducationStoryDraft(story="The portal rate is 16.7 pts/₹100.")
    model = FakeChatModel(always(bad))
    assert await narrate_education(_facts(), model=model) is None


async def test_known_decimal_rate_is_allowed() -> None:
    good = EducationStoryDraft(story="The portal rate is 16.65 pts per ₹100.")
    model = FakeChatModel(always(good))
    assert await narrate_education(_facts(), model=model) is not None


async def test_catalog_card_outside_wallet_is_a_hallucination() -> None:
    """A real catalog card that is NOT in the wallet must not be cited."""
    bad = EducationStoryDraft(
        story="Your Atlas pairs well with the Magnus for Burgundy."
    )
    model = FakeChatModel(always(bad))
    assert await narrate_education(_facts(), model=model) is None


async def test_llm_failure_degrades_silently() -> None:
    from tests.unit.ai_reasoning.conftest import raises

    model = FakeChatModel(raises(RuntimeError("429")))
    assert await narrate_education(_facts(), model=model) is None


async def test_prompt_carries_only_fact_lines() -> None:
    """The LLM sees exactly the deterministic fact sheet — cards, shared
    partners — never catalog internals beyond it."""
    model = FakeChatModel(always(EducationStoryDraft(story="Atlas story.")))
    facts = _facts()
    await narrate_education(facts, model=model)
    _, prompt, _ = model.calls[0]
    for line in (*facts.card_lines, *facts.shared_lines):
        assert line in prompt


@pytest.mark.parametrize("story", ["", "   "])
async def test_empty_story_collapses_to_none(story: str) -> None:
    model = FakeChatModel(always(EducationStoryDraft(story=story)))
    assert await narrate_education(_facts(), model=model) is None


async def test_slow_model_is_abandoned_within_the_timeout() -> None:
    """Decision 10: a slow model can never stall the step. The framing call
    is bounded — a model that outlives the timeout degrades to None instead
    of hanging the request."""
    import asyncio

    class SlowModel:
        async def complete(self, **kwargs: object) -> EducationStoryDraft:
            await asyncio.sleep(30)
            return EducationStoryDraft(story="too late")

    result = await narrate_education(_facts(), model=SlowModel(), timeout_seconds=0.05)
    assert result is None
