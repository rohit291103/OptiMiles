"""Stage 10 — Explanation & Narration (`narrate`).

Converts the ranked, structured result into legible prose WITHOUT making it
less true. The design is a sandwich: a deterministic payload of finished
numbers and names → one constrained LLM call that only phrases them → a
deterministic number-echo check that rejects anything the payload can't back.

- **The LLM is handed only facts to phrase.** `build_narration_payload`
  assembles the headline miles, months-to-goal, fees, card/program names,
  differentiator and assumptions — no score weights, no catalog ids, no
  ratios. The model has no retrieval and no tools; it cannot introduce a
  fact because it was given only facts, not access.
- **Number-echo validation.** Every integer and every card/program name in
  the generated narration must appear in the payload's allow-lists. An
  unmatched figure ⇒ ONE regeneration; a second failure ⇒ template.
- **Template fallback.** Assembled from the same payload (`model_version=
  'template-fallback'`). Stilted but true. The numbers ship whether or not
  the LLM is available or honest — only eloquence degrades.

Infeasible path: `recommended is None`; the narration becomes the computed
adjustment menu from the `FeasibilityVerdict`, same echo-checking.
"""

import logging
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai_reasoning.model import ChatModel
from app.domain import (
    FeasibilityVerdict,
    PlanningContext,
    RankedStrategy,
    RecommendationNarration,
)
from app.domain.narration import ActionItem

logger = logging.getLogger(__name__)

_TEMPLATE_VERSION = "template-fallback"
# Capture any trailing decimal as PART of the same token, so "97280.7" is one
# token and cannot be laundered into an allowed "97280" plus an allowed "7".
# Every payload number is an integer, so any non-zero fractional part is a
# fabrication regardless of the integer part.
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


class NarrationTier(BaseModel):
    """One option in the 'your cards → +1 → +2' comparison, as finished facts
    the narrator may cite. Numbers here are added to `allowed_numbers`."""

    model_config = ConfigDict(frozen=True)

    label: str  # the headline differentiator, e.g. "no new cards"
    miles: int
    card_fees_inr: int
    """New-card joining fees only — transfer/program micro-fees are surfaced
    in the plan's transfer step, never in the narrated fee figure."""
    acquire_names: tuple[str, ...]
    is_recommended: bool


class NarrationPayload(BaseModel):
    """The complete, finished fact set handed to the LLM — nothing else."""

    model_config = ConfigDict(frozen=True)

    feasible: bool
    target_program: str
    required_miles: int
    headline_miles: int
    months_to_goal: int | None
    horizon_months: int
    card_fees_inr: int
    buffer_achieved: bool
    differentiator: str
    card_names: tuple[str, ...]
    acquire_names: tuple[str, ...]
    assumptions: tuple[str, ...]
    adjustment_notes: tuple[str, ...]
    comparison: tuple[NarrationTier, ...] = ()
    """The recommended tier + alternatives, for telling the comparison story.
    Empty when there is only one option. Every number here is echo-allowed."""
    allowed_numbers: frozenset[int]
    allowed_names: frozenset[str]
    catalog_card_names: frozenset[str] = frozenset()
    """Every card name in the catalog — the guard set for detecting a real
    card cited in prose but NOT part of this plan (a hallucination)."""


def _integers_in(text: str) -> set[int]:
    """Every integer literal in text (commas stripped, decimals ignored)."""
    found: set[int] = set()
    for raw in _NUMBER_RE.findall(text):
        stripped = raw.replace(",", "")
        if "." in stripped:
            stripped = stripped.partition(".")[0]
        if stripped:
            found.add(int(stripped))
    return found


def build_narration_payload(
    recommended: RankedStrategy | None,
    verdict: FeasibilityVerdict,
    context: PlanningContext,
    alternatives: tuple[RankedStrategy, ...],
) -> NarrationPayload:
    snapshot = context.snapshot
    names_by_card = {card.id: card.card_name for card in snapshot.cards}
    program = context.requirement.target_program_name
    required = context.requirement.miles_required_total

    numbers: set[int] = {required, context.horizon_months}
    card_names: tuple[str, ...] = ()
    acquire_names: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    adjustment_notes: tuple[str, ...] = ()
    headline = verdict.best_case_miles
    months: int | None = None
    fees = 0
    differentiator = ""
    buffer_achieved = False
    comparison: tuple[NarrationTier, ...] = ()

    if recommended is not None:
        strategy, outcome = recommended.strategy, recommended.simulation
        headline = outcome.miles_at_target_date
        months = outcome.months_to_goal
        fees = outcome.card_fees_inr
        buffer_achieved = outcome.buffer_achieved
        differentiator = recommended.headline_differentiator
        card_names = tuple(names_by_card[c] for c in strategy.cards_used if c in names_by_card)
        acquire_names = tuple(
            names_by_card[c] for c in strategy.cards_to_acquire if c in names_by_card
        )
        assumptions = strategy.assumptions
        numbers.update({headline, fees})
        numbers.update(item.points for item in strategy.transfer_plan)
        numbers.update(m.bonus_points for m in strategy.expected_milestones)
        if months is not None:
            numbers.add(months)
        # Any integer embedded in text WE hand the LLM (assumptions) is fair to
        # echo — allow-list it so a faithful quote isn't flagged as invented.
        for note in assumptions:
            numbers.update(_integers_in(note))
        # The comparison tiers (recommended first, then each alternative) — the
        # story the narrator tells. Only build it when there IS a comparison.
        if alternatives:
            comparison = _build_tiers(recommended, alternatives, names_by_card)
            for tier in comparison:
                numbers.update({tier.miles, tier.card_fees_inr})
    else:
        # Infeasible: the answer is the adjustment menu.
        headline = verdict.best_case_miles
        numbers.add(headline)
        numbers.add(verdict.portfolio.current_capability_miles)
        notes: list[str] = []
        for option in verdict.adjustment_options:
            notes.append(option.description)
            numbers.add(option.resulting_best_case_miles)
            # The description is shown to the LLM (e.g. "raise ... by ₹10,000");
            # a faithful echo of any integer in it is honest, not a fabrication.
            numbers.update(_integers_in(option.description))
        adjustment_notes = tuple(notes)

    allowed_names = frozenset({program, *card_names, *acquire_names, context.goal.destination_city})
    return NarrationPayload(
        catalog_card_names=frozenset(card.card_name for card in snapshot.cards),
        feasible=verdict.feasible,
        target_program=program,
        required_miles=required,
        headline_miles=headline,
        months_to_goal=months,
        horizon_months=context.horizon_months,
        card_fees_inr=fees,
        buffer_achieved=buffer_achieved,
        differentiator=differentiator,
        card_names=card_names,
        acquire_names=acquire_names,
        assumptions=assumptions,
        adjustment_notes=adjustment_notes,
        comparison=comparison,
        allowed_numbers=frozenset(numbers),
        allowed_names=allowed_names,
    )


def _build_tiers(
    recommended: RankedStrategy,
    alternatives: tuple[RankedStrategy, ...],
    names_by_card: dict[UUID, str],
) -> tuple[NarrationTier, ...]:
    """The comparison story: recommended tier first, then each alternative."""
    tiers: list[NarrationTier] = []
    for option, is_recommended in [
        (recommended, True),
        *((alt, False) for alt in alternatives),
    ]:
        tiers.append(
            NarrationTier(
                label=option.headline_differentiator,
                miles=option.simulation.miles_at_target_date,
                card_fees_inr=option.simulation.card_fees_inr,
                acquire_names=tuple(
                    names_by_card[c]
                    for c in option.strategy.cards_to_acquire
                    if c in names_by_card
                ),
                is_recommended=is_recommended,
            )
        )
    return tuple(tiers)


async def narrate(
    recommended: RankedStrategy | None,
    verdict: FeasibilityVerdict,
    context: PlanningContext,
    *,
    alternatives: tuple[RankedStrategy, ...],
    model: ChatModel | None,
) -> RecommendationNarration:
    payload = build_narration_payload(recommended, verdict, context, alternatives)

    if model is not None:
        for attempt in range(2):  # one draft + one regeneration
            try:
                draft = await model.complete(
                    instructions=_instructions(),
                    prompt=_prompt(payload),
                    output_type=RecommendationNarration,
                )
            except Exception:
                logger.warning("narration LLM call failed on attempt %d", attempt + 1)
                break
            unmatched = _unsupported_tokens(draft, payload)
            if not unmatched:
                return draft
            logger.warning(
                "narration draft %d cited unsupported tokens %s; %s",
                attempt + 1,
                sorted(unmatched)[:5],
                "regenerating" if attempt == 0 else "falling back to template",
            )

    return _template(payload)


def _unsupported_tokens(narration: RecommendationNarration, payload: NarrationPayload) -> set[str]:
    """Every number and known-program/card name in the prose must trace to the
    payload. Returns the offending tokens (empty ⇒ faithful)."""
    text = " ".join(
        [
            narration.summary,
            narration.reasoning,
            narration.comparison_notes or "",
            *(item.action for item in narration.action_items),
            *(item.impact or "" for item in narration.action_items),
        ]
    )
    offenders: set[str] = set()

    for raw in _NUMBER_RE.findall(text):
        stripped = raw.replace(",", "")
        if "." in stripped:
            integer_part, _, fraction = stripped.partition(".")
            # A fractional part on an always-integer number is a fabrication,
            # even when the integer part is itself allow-listed.
            if fraction.strip("0"):
                offenders.add(raw)
                continue
            stripped = integer_part
        if int(stripped) not in payload.allowed_numbers:
            offenders.add(raw)

    # Card names are guarded against the FULL catalog: a real card name that
    # isn't part of THIS plan is a hallucination; unknown prose is just prose.
    for name in payload.catalog_card_names:
        if name and name.lower() in text.lower() and name not in payload.allowed_names:
            offenders.add(name)
    return offenders


def _instructions() -> str:
    return (
        "You explain a finished credit-card reward plan to the traveller in warm, "
        "concrete prose. Use ONLY the numbers and card/program names given in the "
        "payload — never introduce a figure, card, or program that isn't there. Do "
        "not compute or estimate anything; the numbers are final. Keep the summary to "
        "1–2 sentences. Every action item must map to something in the plan."
    )


def _prompt(payload: NarrationPayload) -> str:
    lines = [
        f"Target program: {payload.target_program}",
        f"Miles required: {payload.required_miles:,}",
    ]
    if payload.feasible:
        lines.append(f"This plan reaches: {payload.headline_miles:,} miles")
        if payload.months_to_goal is not None:
            lines.append(
                f"Goal reached in month {payload.months_to_goal} of "
                f"{payload.horizon_months} (0-indexed)"
            )
        lines.append(f"New-card fees: ₹{payload.card_fees_inr:,}")
        lines.append(f"Buffer achieved: {payload.buffer_achieved}")
        lines.append(f"Why it wins: {payload.differentiator}")
        if payload.card_names:
            lines.append(f"Cards used: {', '.join(payload.card_names)}")
        if payload.acquire_names:
            lines.append(f"New card(s) to apply for: {', '.join(payload.acquire_names)}")
        if len(payload.comparison) >= 2:
            lines.append(
                "Options to compare (tell this as a story — what their current "
                "cards reach vs. what adding a card unlocks):"
            )
            for tier in payload.comparison:
                add = (
                    f"add {', '.join(tier.acquire_names)}"
                    if tier.acquire_names
                    else "no new cards"
                )
                mark = " [recommended]" if tier.is_recommended else ""
                lines.append(
                    f"  - {tier.label} ({add}): {tier.miles:,} miles, "
                    f"₹{tier.card_fees_inr:,} card fees{mark}"
                )
    else:
        lines.append(f"Goal NOT reachable as stated; best case {payload.headline_miles:,} miles.")
        if payload.adjustment_notes:
            lines.append("Adjustments that would work:")
            lines.extend(f"  - {note}" for note in payload.adjustment_notes)
    if payload.assumptions:
        lines.append("Assumptions: " + "; ".join(payload.assumptions))
    return "\n".join(lines)


def _template(payload: NarrationPayload) -> RecommendationNarration:
    """Deterministic narration from the payload — stilted but true."""
    program = payload.target_program
    if payload.feasible:
        month_clause = (
            f" by month {payload.months_to_goal}"
            if payload.months_to_goal is not None
            else " within your timeline"
        )
        summary = (
            f"Reaches {payload.headline_miles:,} {program} miles{month_clause} "
            f"(target {payload.required_miles:,})."
        )
        reasoning_bits = [f"This is the {payload.differentiator} option."]
        if payload.card_names:
            reasoning_bits.append(f"Cards used: {', '.join(payload.card_names)}.")
        if payload.acquire_names:
            reasoning_bits.append(f"Apply for: {', '.join(payload.acquire_names)}.")
        reasoning_bits.append(f"New-card fees ₹{payload.card_fees_inr:,}.")
        if payload.assumptions:
            reasoning_bits.append(" ".join(payload.assumptions) + ".")
        actions = tuple(
            ActionItem(priority=i, action=f"Apply for the {name}")
            for i, name in enumerate(payload.acquire_names, start=1)
        ) or (
            ActionItem(priority=1, action="Route your spend as planned and transfer on schedule"),
        )
    else:
        summary = (
            f"Not reachable as stated — best case {payload.headline_miles:,} "
            f"{program} miles against {payload.required_miles:,} needed."
        )
        reasoning_bits = ["Here are changes that would make it work:"]
        reasoning_bits.extend(f"- {note}." for note in payload.adjustment_notes)
        actions = tuple(
            ActionItem(priority=i, action=note)
            for i, note in enumerate(payload.adjustment_notes, start=1)
        ) or (ActionItem(priority=1, action="Extend your timeline or raise monthly spend"),)

    return RecommendationNarration(
        summary=summary,
        reasoning=" ".join(reasoning_bits),
        action_items=actions,
        comparison_notes=_comparison_notes(payload),
        model_version=_TEMPLATE_VERSION,
    )


def _comparison_notes(payload: NarrationPayload) -> str | None:
    """Deterministic tier story: 'your cards reach X; adding a card lifts you to
    Y for ₹Z'. None when there is no comparison to draw (a single option)."""
    if len(payload.comparison) < 2:
        return None
    parts: list[str] = []
    for tier in payload.comparison:
        fee_clause = (
            "no new card fees"
            if tier.card_fees_inr == 0
            else f"₹{tier.card_fees_inr:,} in card fees"
        )
        if tier.acquire_names:
            lead = f"Adding {', '.join(tier.acquire_names)}"
        else:
            lead = "With your current cards"
        marker = " (recommended)" if tier.is_recommended else ""
        parts.append(f"{lead}: {tier.miles:,} miles for {fee_clause}{marker}.")
    return " ".join(parts)
