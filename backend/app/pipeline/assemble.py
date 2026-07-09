"""Stage 11 — Recommendation Assembly.

Shapes the deterministic artifacts (goal, requirement, verdict, ranked
strategies, narration) into the `FinalRecommendation` package and stamps
lineage (`catalog_snapshot_version` + `engine_version`, D-2) so every
historical recommendation is reproducible. Pure: it composes already-finished
objects and originates no numbers of its own. Persistence is a separate concern
(`repositories/results.py`), called by the orchestrator after assembly.

Two derived fields are assembled here from existing artifacts, not invented:

- **`assumed_flags`** — UI hints. Surfaces the `assumed` spend profile and any
  `assumed_fields` on the intent (e.g. origin taken from the user profile), so
  the frontend can say "based on a default — edit to refine."
- **`risks_and_limitations`** — the honest caveats the blueprint's
  Recommendation Package requires, drawn from the verdict (tight feasibility,
  stale chart) and the recommended strategy's own risk signals.
"""

from app.config import ENGINE_VERSION
from app.domain import (
    FeasibilityVerdict,
    FinalRecommendation,
    ParsedGoalIntent,
    PlanningContext,
    RankedStrategy,
    RecommendationNarration,
)

# MVP scope excludes award availability (miles ≠ seats); the recommendation
# must state the assumption rather than imply a guaranteed seat.
_SAVER_AVAILABILITY_CAVEAT = (
    "Assumes saver award availability on your dates — miles are necessary but "
    "not sufficient; confirm seats before committing to the plan."
)


def assemble_recommendation(
    context: PlanningContext,
    verdict: FeasibilityVerdict,
    ranked: tuple[RankedStrategy, ...],
    narration: RecommendationNarration | None,
    *,
    intent: ParsedGoalIntent | None = None,
) -> FinalRecommendation:
    recommended = ranked[0] if ranked else None
    alternatives = ranked[1:] if len(ranked) > 1 else ()

    return FinalRecommendation(
        goal=context.goal,
        requirement=context.requirement,
        verdict=verdict,
        recommended=recommended,
        alternatives=alternatives,
        narration=narration,
        risks_and_limitations=_risks(context, verdict, recommended),
        assumed_flags=_assumed_flags(context, intent),
        catalog_snapshot_version=context.snapshot.version,
        engine_version=ENGINE_VERSION,
    )


def _assumed_flags(
    context: PlanningContext, intent: ParsedGoalIntent | None
) -> tuple[str, ...]:
    flags: list[str] = []
    if context.spend_profile.assumed:
        flags.append("spend_profile")
    if intent is not None:
        flags.extend(intent.assumed_fields)
    if context.requirement.stale_chart:
        flags.append("award_chart")
    return tuple(flags)


def _risks(
    context: PlanningContext,
    verdict: FeasibilityVerdict,
    recommended: RankedStrategy | None,
) -> tuple[str, ...]:
    risks: list[str] = [_SAVER_AVAILABILITY_CAVEAT]

    if not verdict.feasible:
        risks.append(
            "Not reachable as stated within your timeline — see the adjustment "
            "options for changes that would make it work."
        )
    elif verdict.tight:
        risks.append(
            "Feasible but tight: the plan clears the target with little margin "
            "above the safety buffer, so a small shortfall in spend or a "
            "devaluation could put it at risk."
        )

    if recommended is not None and recommended.simulation.misses_goal:
        risks.append(
            "The top plan is the closest available but falls short of the target "
            "in simulation — treat its projection as a best effort, not a "
            "guarantee."
        )

    if context.requirement.stale_chart:
        risks.append(
            "The award chart for this route was updated after your goal was "
            "created; this plan uses the chart values locked at creation time."
        )

    return tuple(risks)
