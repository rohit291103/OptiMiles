"""The orchestrator — composes the 11-stage pipeline into one linear function.

This is the plain Python "pipeline orchestration is deterministic code" the
blueprint mandates (§0.2): no LLM decides which stage runs next, no graph
framework, the same order every request. The two AI stages (1 and 10) are
fenced behind a `ChatModel | None` and both degrade to non-LLM paths, so the
whole pipeline runs end-to-end with no API key.

Three entry points share the deterministic stages:

- **`run_goal_pipeline`** — Flow A. Raw text (or an already-resolved intent for
  the client-held clarification loop) → intent → resolution → requirement →
  context → the deterministic core → narration → assembled recommendation. Any
  stage that can't proceed returns an honest early-exit result
  (`ClarificationNeeded` / `RouteUnsupported` / `ScopeRefusal`) — the pipeline
  never guesses past a gap.

- **`run_from_context`** — Flow B re-entry (Stage 4 onward). A ready
  `PlanningContext` (the public simulator, a spend-tweak replay) →
  core → narration → recommendation. Deterministic and, with `model=None`,
  byte-identical on repeat: the standing determinism invariant lives here.
  Infeasible goals still produce a best-effort plan when one is allocatable
  (`recommended` set, `misses_goal=True`) plus the adjustment menu; only a
  wallet with nothing to allocate leaves `recommended=None`.

- **`run_feasibility_probe`** — the guided wizard's silent early check
  (decision 5, 2026-07-13): the same Stage 1–4 prefix, then Stage 5 + the
  Stage-6 bound check only. Verdict + adjustment menu out, sub-second, no
  candidates/simulation/narration.

The orchestrator owns no DB writes and no engine internals; it calls engine
entry points in order and shapes their outputs. Persistence is the caller's job
(`repositories/results.py`), kept off the pure path so the determinism test
needs no database.
"""

from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from app.ai_reasoning.intent import ScopeRefusal, extract_intent
from app.ai_reasoning.model import ChatModel
from app.ai_reasoning.narration import narrate
from app.domain import (
    CatalogSnapshot,
    ClarificationRequest,
    ConstraintSet,
    FeasibilityVerdict,
    FinalRecommendation,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    RankedStrategy,
    SpendProfile,
    TravelGoal,
    UnsupportedRoute,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.optimization.feasibility import assess_feasibility
from app.optimization.ranking import (
    RankingWeights,
    rank,
    select_guided_routes,
    select_route_options,
)
from app.optimization.strategies import generate_candidates
from app.pipeline.assemble import assemble_recommendation
from app.pipeline.context import assemble_context
from app.simulation.projector import simulate
from app.valuation.opportunities import enumerate_opportunities


class ClarificationNeeded(BaseModel):
    """Early exit: the input is incomplete/ambiguous (Stage 1 or 2)."""

    model_config = ConfigDict(frozen=True)

    request: ClarificationRequest


class RouteUnsupported(BaseModel):
    """Early exit: no award chart covers the requested route (Stage 2)."""

    model_config = ConfigDict(frozen=True)

    route: UnsupportedRoute


class ScopeRefused(BaseModel):
    """Early exit: the request isn't a supported travel goal (Stage 1)."""

    model_config = ConfigDict(frozen=True)

    refusal: ScopeRefusal


# What Flow A can produce: a finished recommendation, or an honest reason it
# couldn't start. Every branch is explicit — nothing is silently defaulted.
PipelineOutcome = (
    FinalRecommendation | ClarificationNeeded | RouteUnsupported | ScopeRefused
)


class FeasibilityProbe(BaseModel):
    """Stages 1–6 only — the wizard's silent early check (guided-flow
    decision 5). Just the verdict (with its adjustment menu) plus the numbers
    the interrupt UI needs; no candidates, no simulation, no narration. No
    minted ids either, so repeat probes are fully identical."""

    model_config = ConfigDict(frozen=True)

    verdict: FeasibilityVerdict
    miles_required_total: int
    horizon_months: int
    catalog_snapshot_version: str


# What the probe can produce: a verdict, or the same honest early exits as
# Flow A (the probe runs the identical Stage 1–4 prefix).
ProbeOutcome = FeasibilityProbe | ClarificationNeeded | RouteUnsupported | ScopeRefused


async def run_goal_pipeline(
    *,
    text: str | None,
    intent: ParsedGoalIntent | None,
    snapshot: CatalogSnapshot,
    weights: RankingWeights,
    buffer_pct: float,
    user_id: UUID,
    wallet: tuple[WalletCard, ...] = (),
    spend_profile: SpendProfile | None = None,
    total_spend_inr: int | None = None,
    constraints: ConstraintSet | None = None,
    profile_city: str | None = None,
    model: ChatModel | None = None,
    today: date | None = None,
) -> PipelineOutcome:
    """Flow A: goal text (or a pre-resolved intent) → recommendation package.

    Pass `intent` directly to skip Stage 1 — this is how the client-held
    clarification loop resubmits an accumulated intent once it's complete.
    Pass `text` to run intent extraction (LLM or structured-form fallback).
    Pass `total_spend_inr` (mutually exclusive with `spend_profile`) to have
    Stage 4 derive the assumed template split from one total-over-horizon
    budget — the split needs the horizon, so it can only happen here.
    """
    prepared = await _prepare_context(
        text=text,
        intent=intent,
        snapshot=snapshot,
        buffer_pct=buffer_pct,
        user_id=user_id,
        wallet=wallet,
        spend_profile=spend_profile,
        total_spend_inr=total_spend_inr,
        constraints=constraints,
        profile_city=profile_city,
        model=model,
        today=today or date.today(),
    )
    if not isinstance(prepared, tuple):
        return prepared
    context, resolved_intent = prepared
    return await run_from_context(
        context, weights=weights, model=model, intent=resolved_intent
    )


async def run_feasibility_probe(
    *,
    text: str | None,
    intent: ParsedGoalIntent | None,
    snapshot: CatalogSnapshot,
    buffer_pct: float,
    user_id: UUID,
    wallet: tuple[WalletCard, ...] = (),
    spend_profile: SpendProfile | None = None,
    total_spend_inr: int | None = None,
    constraints: ConstraintSet | None = None,
    profile_city: str | None = None,
    model: ChatModel | None = None,
    today: date | None = None,
) -> ProbeOutcome:
    """Stages 1–6 only: the wizard's silent early feasibility check.

    Same Stage 1–4 prefix as Flow A (identical early exits), then opportunity
    enumeration and the cheap Stage-6 bound check — no candidate generation, no
    simulation, no narration, so it returns in well under a second. Clearly
    hopeless goals get the adjustment menu before the user is walked through
    education (guided-flow decision 5)."""
    prepared = await _prepare_context(
        text=text,
        intent=intent,
        snapshot=snapshot,
        buffer_pct=buffer_pct,
        user_id=user_id,
        wallet=wallet,
        spend_profile=spend_profile,
        total_spend_inr=total_spend_inr,
        constraints=constraints,
        profile_city=profile_city,
        model=model,
        today=today or date.today(),
    )
    if not isinstance(prepared, tuple):
        return prepared
    context, _ = prepared

    # Stage 5 + the Stage-6 bound check — the whole cost of the probe.
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    return FeasibilityProbe(
        verdict=verdict,
        miles_required_total=context.requirement.miles_required_total,
        horizon_months=context.horizon_months,
        catalog_snapshot_version=context.snapshot.version,
    )


async def _prepare_context(
    *,
    text: str | None,
    intent: ParsedGoalIntent | None,
    snapshot: CatalogSnapshot,
    buffer_pct: float,
    user_id: UUID,
    wallet: tuple[WalletCard, ...],
    spend_profile: SpendProfile | None,
    total_spend_inr: int | None,
    constraints: ConstraintSet | None,
    profile_city: str | None,
    model: ChatModel | None,
    today: date,
) -> (
    tuple[PlanningContext, ParsedGoalIntent]
    | ClarificationNeeded
    | RouteUnsupported
    | ScopeRefused
):
    """Stages 1–4, shared by Flow A and the feasibility probe: intent →
    resolution → requirement → PlanningContext, or the honest early exit."""
    # Stage 1 — Intent Extraction & Clarification (AI edge, or skipped).
    if intent is None:
        if text is None:
            raise ValueError("run_goal_pipeline requires either text or intent")
        proposal = await extract_intent(
            text, snapshot, model=model, profile_city=profile_city
        )
        if isinstance(proposal, ClarificationRequest):
            return ClarificationNeeded(request=proposal)
        if isinstance(proposal, ScopeRefusal):
            return ScopeRefused(refusal=proposal)
        intent = proposal

    # Stages 2–3 — Resolution (trust boundary) + Requirement estimation.
    resolution = resolve_goal(intent, snapshot, today=today)
    if isinstance(resolution, ClarificationRequest):
        return ClarificationNeeded(request=resolution)
    if isinstance(resolution, UnsupportedRoute):
        return RouteUnsupported(route=resolution)
    assert isinstance(resolution, GoalResolution)

    goal = _goal_from_resolution(resolution, user_id)
    requirement = estimate_requirement(goal, snapshot, buffer_pct)

    # Stage 4 — Planning Context assembly (defaults flagged assumed).
    context = assemble_context(
        goal,
        requirement,
        snapshot,
        wallet=wallet,
        spend_profile=spend_profile,
        total_spend_inr=total_spend_inr,
        constraints=constraints,
        today=today,
    )
    return context, intent


async def run_from_context(
    context: PlanningContext,
    *,
    weights: RankingWeights,
    model: ChatModel | None = None,
    intent: ParsedGoalIntent | None = None,
) -> FinalRecommendation:
    """Stages 5–11 over a ready PlanningContext (Flow B re-entry point).

    Deterministic through Stage 9; Stage 10 (narration) is the only LLM touch
    and falls back to a template with `model=None`. With `model=None` the whole
    function is byte-identical on repeat — the determinism invariant.
    """
    # Stage 5 — Opportunity enumeration & valuation.
    opportunities = enumerate_opportunities(context)

    # Stage 6 — Feasibility verdict. Infeasible no longer short-circuits
    # Stages 7–9: an unreachable goal still deserves the least-bad plan
    # (honestly marked misses_goal) alongside the adjustment menu. The
    # verdict shapes narration and risks, not whether a plan exists.
    verdict = assess_feasibility(opportunities, context)

    # Stage 7 — Candidate generation (validated at exit). May be empty when
    # nothing is allocatable (e.g. cashback-only wallet, no acquisitions).
    candidates = generate_candidates(opportunities, verdict, context)
    # Stage 8 — Timeline simulation, once per candidate.
    pairs = tuple((candidate, simulate(candidate, context)) for candidate in candidates)
    # Stage 9 — Ranking & selection (reconciled against simulation);
    # opportunities threaded through so each ranked strategy carries its
    # per-category earn story (allocation_details) for the UI. The package
    # presents at most 3 genuinely different routes — one per distinct
    # acquisition set (archetype variants of the same acquisition collapse
    # to the best-ranked plan).
    ranked = rank(pairs, context, weights, opportunities=opportunities)
    # Guided-flow presentation (decisions 8–9, 2026-07-13): when the wallet
    # can't clear the goal but an acquisition can, present the labeled
    # cheapest + best-value pair (plus the wallet best-effort). Everywhere
    # else — wallet clears, nothing clears, or a config without the
    # acquisition profile — the standard ≤3-distinct-routes selection stands.
    guided = (
        select_guided_routes(ranked, weights.acquisition)
        if weights.acquisition is not None
        else None
    )
    presented = guided if guided is not None else select_route_options(ranked)
    recommended: RankedStrategy | None = presented[0] if presented else None

    # Stage 10 — Explanation & narration (AI edge; template fallback).
    narration = await narrate(
        recommended,
        verdict,
        context,
        alternatives=presented[1:] if len(presented) > 1 else (),
        model=model,
    )

    # Stage 11 — Assembly (lineage stamped).
    return assemble_recommendation(context, verdict, presented, narration, intent=intent)


def _goal_from_resolution(resolution: GoalResolution, user_id: UUID) -> TravelGoal:
    """Persist-shaped goal from a resolved draft. The id is minted here; the
    orchestrator's persistence layer writes it as the user_goals row."""
    return TravelGoal(id=uuid4(), user_id=user_id, **resolution.model_dump())
