"""Education framing (guided-flow decision 10, decision log 2026-07-13).

The wizard's education step renders deterministic catalog facts; when an LLM
is available, this module lets it PHRASE those facts as a short story that
"lands on top". Same sandwich as Stage 10 narration: a fact sheet of finished
numbers and names in → one constrained call → a number-echo check that
rejects anything the facts can't back. There is no template here — the
deterministic education render IS the fallback, so a failed/absent LLM simply
returns None and the step ships unchanged. A 429 or slow model can never
stall the step (the caller fetches this separately from the facts).

Boundary: this module deliberately takes a self-contained `EducationFacts`
built by the API layer — ai_reasoning may not import knowledge.education
(only the goal-resolution vocabulary is sanctioned, CI-enforced).
"""

import asyncio
import logging
import re

from pydantic import BaseModel, ConfigDict

from app.ai_reasoning.model import ChatModel

logger = logging.getLogger(__name__)

# Same tokenization as narration.py: a trailing decimal stays PART of the
# token, so "16.7" can't be laundered into an allowed "16" plus a "7".
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


class EducationFacts(BaseModel):
    """The complete fact sheet handed to the LLM — nothing else.

    `card_lines`/`shared_lines` are deterministic sentences built from the
    catalog payload (rates, caps, ratios, fees, shared partners). The allow
    sets are derived from those same lines: `allowed_numbers` holds every
    integer, `allowed_decimals` every non-integral token verbatim (earn rates
    like "16.65" — an exact echo is honest, any other fraction is invented).
    """

    model_config = ConfigDict(frozen=True)

    card_lines: tuple[str, ...]
    shared_lines: tuple[str, ...] = ()
    allowed_numbers: frozenset[int]
    allowed_decimals: frozenset[str] = frozenset()
    allowed_names: frozenset[str]
    catalog_card_names: frozenset[str] = frozenset()
    """Every card name in the catalog — the guard for a real card cited in
    prose that is NOT part of this wallet (a hallucination)."""


class EducationStoryDraft(BaseModel):
    """The LLM's structured output: one short story paragraph."""

    story: str


async def narrate_education(
    facts: EducationFacts,
    *,
    model: ChatModel | None,
    timeout_seconds: float = 10.0,
) -> str | None:
    """LLM-phrased framing of the wallet's reward story, or None.

    None whenever the model is absent, slow (each call is bounded by
    `timeout_seconds` — decision 10: framing can never stall the step),
    fails, or twice cites a token the facts can't back — the caller renders
    the deterministic step alone."""
    if model is None:
        return None
    for attempt in range(2):  # one draft + one regeneration
        try:
            draft = await asyncio.wait_for(
                model.complete(
                    instructions=_instructions(),
                    prompt=_prompt(facts),
                    output_type=EducationStoryDraft,
                ),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            logger.warning(
                "education framing timed out after %.1fs on attempt %d",
                timeout_seconds,
                attempt + 1,
            )
            return None
        except Exception:
            logger.warning("education framing LLM call failed on attempt %d", attempt + 1)
            return None
        story = draft.story.strip()
        if not story:
            return None
        offenders = _unsupported_tokens(story, facts)
        if not offenders:
            return story
        logger.warning(
            "education framing draft %d cited unsupported tokens %s; %s",
            attempt + 1,
            sorted(offenders)[:5],
            "regenerating" if attempt == 0 else "dropping the framing",
        )
    return None


def _unsupported_tokens(story: str, facts: EducationFacts) -> set[str]:
    """Every number and known card name in the prose must trace to the facts."""
    offenders: set[str] = set()
    for raw in _NUMBER_RE.findall(story):
        stripped = raw.replace(",", "")
        if stripped in facts.allowed_decimals:
            continue
        if "." in stripped:
            integer_part, _, fraction = stripped.partition(".")
            # A non-zero fraction that isn't a verbatim known rate is invented,
            # even when its integer part is allow-listed.
            if fraction.strip("0"):
                offenders.add(raw)
                continue
            stripped = integer_part
        if int(stripped) not in facts.allowed_numbers:
            offenders.add(raw)
    for name in facts.catalog_card_names:
        if name and name.lower() in story.lower() and name not in facts.allowed_names:
            offenders.add(name)
    return offenders


def _instructions() -> str:
    return (
        "You are introducing a traveller to how their own credit cards earn and "
        "move reward points, before they see a strategy. Write ONE warm, concrete "
        "paragraph (2–4 sentences). Use ONLY the numbers, rates, and card/program "
        "names given — never introduce a figure, card, or program that isn't "
        "there, and never compute or estimate. If the cards share a transfer "
        "partner, make that shared destination the point of the story."
    )


def _prompt(facts: EducationFacts) -> str:
    lines = ["The traveller's cards:"]
    lines.extend(f"  - {line}" for line in facts.card_lines)
    if facts.shared_lines:
        lines.append("Shared transfer partners:")
        lines.extend(f"  - {line}" for line in facts.shared_lines)
    return "\n".join(lines)
