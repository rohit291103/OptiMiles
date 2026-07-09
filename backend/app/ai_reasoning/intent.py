"""Stage 1 — Intent Extraction & Clarification (`extract_intent`).

Free-form text → a machine-checkable `ParsedGoalIntent`, or an honest
`ClarificationRequest` / `ScopeRefusal`. The LLM only PROPOSES; this function
re-validates every field it returns against the catalog vocabulary (the same
`CITY_TO_REGION` / `CabinClass` tables Stage 2 uses), so an out-of-vocabulary
value the model was confident about becomes a `missing_field`, never a
downstream fact. The trust boundary is Stage 2; this stage's job is to make
sure the LLM's output is safely discardable.

Three non-LLM guarantees hold regardless of the model:

- **Vocabulary lists only.** The prompt carries supported city and cabin
  NAMES so the model can normalize "biz to SG" — never ratios, miles, or
  earn rates. It cannot distort facts it was never given.
- **Origin is the only permitted default** (from the user profile, flagged
  `assumed`); every other absent field becomes a clarification question.
- **No model, or a failing model, is not an error.** `model=None` (no API
  key) or an exception returns the full structured-form clarification — the
  natural-language entry is an enhancement, not the only door.

Scope refusal: a low-confidence reading with no usable travel fields is an
out-of-MVP-scope request ("optimize my taxes"); the pipeline never starts.
"""

import logging

from pydantic import BaseModel, ConfigDict

from app.ai_reasoning.model import ChatModel
from app.domain import (
    CabinClass,
    CatalogSnapshot,
    ClarificationRequest,
    ParsedGoalIntent,
)
from app.knowledge.goal_resolution import CITY_TO_REGION

logger = logging.getLogger(__name__)

_ALL_FIELDS = (
    "origin_city",
    "destination_city",
    "cabin_class",
    "timeline_months",
    "num_passengers",
)
_SCOPE_CONFIDENCE_FLOOR = 0.25  # below this AND no usable field ⇒ out of scope

_QUESTIONS = {
    "origin_city": "Which city will you fly from?",
    "destination_city": "Which destination city? Supported today: Singapore, London, New York.",
    "cabin_class": "Which cabin — economy, premium economy, business or first?",
    "timeline_months": "By when do you want to fly (in months from now)?",
    "num_passengers": "How many passengers?",
}


class ScopeRefusal(BaseModel):
    """The request isn't a supported travel goal — pipeline never starts."""

    model_config = ConfigDict(frozen=True)

    message: str


async def extract_intent(
    text: str,
    snapshot: CatalogSnapshot,
    *,
    model: ChatModel | None,
    profile_city: str | None = None,
) -> ParsedGoalIntent | ClarificationRequest | ScopeRefusal:
    if model is None:
        return _ask_for_everything()

    try:
        proposal = await model.complete(
            instructions=_instructions(),
            prompt=_prompt(text, snapshot),
            output_type=ParsedGoalIntent,
        )
    except Exception:
        logger.warning("intent extraction LLM call failed; falling back to clarification")
        return _ask_for_everything()

    return _revalidate(proposal, profile_city)


def _revalidate(
    proposal: ParsedGoalIntent, profile_city: str | None
) -> ParsedGoalIntent | ClarificationRequest | ScopeRefusal:
    """Re-check every proposed field against the catalog vocabulary. The LLM's
    confidence buys nothing here — only vocabulary membership does."""
    assumed: list[str] = []
    origin = _known_city(proposal.origin_city)
    if origin is None and profile_city is not None and _known_city(profile_city):
        origin = _tidy(profile_city)
        assumed.append("origin_city")

    destination = _known_city(proposal.destination_city)
    cabin = _known_cabin(proposal.cabin_class)
    timeline = proposal.timeline_months
    passengers = proposal.num_passengers

    resolved = {
        "origin_city": origin,
        "destination_city": destination,
        "cabin_class": cabin.value if cabin else None,
        "timeline_months": timeline,
        "num_passengers": passengers,
    }
    missing = tuple(field for field in _ALL_FIELDS if not resolved[field])

    # Out-of-MVP-scope: the model wasn't confident and found nothing usable.
    if missing == _ALL_FIELDS and proposal.confidence < _SCOPE_CONFIDENCE_FLOOR:
        return ScopeRefusal(
            message=(
                "That doesn't look like a supported travel goal yet. OptiMiles plans "
                "flights to Singapore, London or New York using Indian credit-card "
                "rewards — tell me where and when you'd like to fly."
            )
        )

    if missing:
        return ClarificationRequest(
            questions=tuple(_QUESTIONS[field] for field in missing),
            missing_fields=missing,
        )

    return ParsedGoalIntent(
        origin_city=origin,
        destination_city=destination,
        cabin_class=cabin.value if cabin else None,
        timeline_months=timeline,
        num_passengers=passengers,
        missing_fields=(),
        assumed_fields=tuple(assumed),
        confidence=proposal.confidence,
    )


def _ask_for_everything() -> ClarificationRequest:
    return ClarificationRequest(
        questions=tuple(_QUESTIONS[field] for field in _ALL_FIELDS),
        missing_fields=_ALL_FIELDS,
    )


def _known_city(city: str | None) -> str | None:
    if city is None:
        return None
    normalized = " ".join(city.strip().lower().split())
    return _tidy(city) if normalized in CITY_TO_REGION else None


def _known_cabin(value: str | None) -> CabinClass | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().lower().split()).replace(" ", "_")
    try:
        return CabinClass(normalized)
    except ValueError:
        return None


def _tidy(value: str) -> str:
    return " ".join(value.strip().split())


def _instructions() -> str:
    return (
        "You read a traveller's free-form goal and extract structured fields for a "
        "credit-card reward planner. Return ONLY what the text supports; never invent "
        "a value. If a field is absent, leave it null and list it in missing_fields. "
        "Normalize synonyms to canonical names (e.g. 'biz'/'J' → 'business', "
        "'SG'/'SIA'→'Singapore'). Set confidence low (< 0.25) if the message is not a "
        "travel goal at all. You are given the supported destinations and cabins only "
        "for normalization — you have no other data and must not state reward numbers."
    )


def _prompt(text: str, snapshot: CatalogSnapshot) -> str:
    destinations = sorted(
        {city.title() for city, region in CITY_TO_REGION.items() if region != "India"}
    )
    cabins = [cabin.value.replace("_", " ") for cabin in CabinClass]
    # Airline program NAMES only (for program_hint normalization) — no ratios.
    programs = sorted(
        p.program_name for p in snapshot.partners if p.partner_type.value == "airline"
    )
    return (
        f"Supported destination cities: {', '.join(destinations)}.\n"
        f"Supported cabins: {', '.join(cabins)}.\n"
        f"Known airline programs: {', '.join(programs)}.\n"
        f"Traveller's message: {text!r}"
    )
