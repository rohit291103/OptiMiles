"""Stage 7 — candidate strategy generation (`generate_candidates`).

Users act on plans, not opportunities: which cards, which spend goes where,
when to transfer. Candidates come from bounded ARCHETYPES, not exhaustive
search — each archetype is a different starting basin of the same honest
allocator (`allocation.hill_climb` on the cap/milestone-aware bound), so
candidates are explainably different local optima, never overstated ones:

1. **status_quo_optimized** — wallet cards only, best-rate start. Always
   attempted first (BR-01); it is also the baseline every acquisition must
   meaningfully beat.
2. **one_new_card** — wallet + one acquirable, constraint-respecting card;
   kept only when its claim beats the baseline by ≥ 5% (BR-02: meaningful
   improvement, not marginal), best 3 by claim.
3. **concentrated** — started from "everything on this milestone-bearing
   card" so multi-category milestone thresholds reachable only by
   concentration survive the climb; converging back into another candidate
   simply dedupes (a valid outcome, per the blueprint).
4. **simplest_viable** — one card for everything, no idle-balance transfers
   (fewest actions); emitted only when that single card still clears the
   requirement.

Claims come from `allocation.claimed_estimate` (transfer-cutoff-aware,
whole-block-floored — built to mirror the projector; Stage 8 still wins any
disagreement). Exit validation (BR-04/BR-05/BR-07): every profile category
allocated, constraints never violated, acquisitions acquirable-only and
within the aggregate fee cap, claim positive; failures DISCARD the
candidate, never patch it. Deterministic throughout: fixed iteration
orders, ties broken by card id, `strategy_id = "<archetype>-<ordinal>"`.
"""

from decimal import Decimal
from uuid import UUID

from app.domain import (
    CandidateStrategy,
    FeasibilityVerdict,
    MilestoneType,
    OpportunitySet,
    PlanningContext,
    RewardOpportunity,
    SpendCategory,
    StrategyArchetype,
)
from app.optimization.allocation import (
    Assignment,
    allowed_card_ids,
    candidate_opportunities,
    claimed_estimate,
    greedy_assignment,
    hill_climb,
)

_MEANINGFUL_IMPROVEMENT = Decimal("1.05")  # BR-02: ≥ 5% over the no-acquisition baseline
_MAX_ONE_NEW_CARD = 3
_MAX_CONCENTRATED_BASINS = 2
_MAX_CANDIDATES = 8  # blueprint Stage 7 upper bound


def generate_candidates(
    opportunities: OpportunitySet,
    verdict: FeasibilityVerdict,
    context: PlanningContext,
) -> tuple[CandidateStrategy, ...]:
    """Bounded archetype candidates for a feasible goal (infeasible ⇒ ()).
    1–2 candidates is a valid outcome for small wallets."""
    if not verdict.feasible:
        return ()

    wallet_ids = frozenset(w.card_id for w in context.wallet)
    allowed = allowed_card_ids(opportunities, wallet_ids, context.constraints)
    categories = {item.category_slug for item in context.spend_profile.items}
    horizon = context.horizon_months
    candidates_by_category = candidate_opportunities(opportunities, allowed)

    drafts: list[tuple[StrategyArchetype, Assignment, bool]] = []

    # 1. Status quo optimized — always attempted first (BR-01).
    status_quo = greedy_assignment(opportunities, context, wallet_ids, horizon)
    baseline_claim = 0
    if set(status_quo) == categories:
        drafts.append((StrategyArchetype.STATUS_QUO_OPTIMIZED, status_quo, True))
        baseline_claim = claimed_estimate(status_quo, context).total_miles

    # 2. One new card — each justifiable acquisition, best 3 by claim.
    scored_additions: list[tuple[int, str, Assignment]] = []
    for aggregate in sorted(opportunities.card_aggregates, key=lambda a: str(a.card_id)):
        if aggregate.in_wallet or aggregate.card_id not in allowed:
            continue
        assignment = greedy_assignment(
            opportunities, context, wallet_ids | {aggregate.card_id}, horizon
        )
        if set(assignment) != categories:
            continue
        if aggregate.card_id not in {o.card_id for o in assignment.values()}:
            continue  # the addition earned no spend — it is the status quo in disguise
        claim = claimed_estimate(assignment, context).total_miles
        if Decimal(claim) <= Decimal(baseline_claim) * _MEANINGFUL_IMPROVEMENT:
            continue  # BR-02
        scored_additions.append((claim, str(aggregate.card_id), assignment))
    scored_additions.sort(key=lambda entry: (-entry[0], entry[1]))
    drafts.extend(
        (StrategyArchetype.ONE_NEW_CARD, assignment, True)
        for _, _, assignment in scored_additions[:_MAX_ONE_NEW_CARD]
    )

    # 3. Concentrated — start from "everything on this milestone card".
    milestone_cards = sorted(
        {
            milestone.card_id
            for milestone in context.snapshot.milestones
            if milestone.card_id in allowed
            and milestone.milestone_type == MilestoneType.SPEND_BONUS
        },
        key=str,
    )
    for card_id in milestone_cards[:_MAX_CONCENTRATED_BASINS]:
        basin = _solo_assignment(candidates_by_category, card_id, categories)
        if basin is None:
            continue
        assignment = hill_climb(basin, candidates_by_category, context, horizon)
        drafts.append((StrategyArchetype.CONCENTRATED, assignment, True))

    # 4. Simplest viable — the best single card that still clears the goal.
    best_solo: tuple[int, str, Assignment] | None = None
    for card_id in sorted(allowed, key=str):
        solo = _solo_assignment(candidates_by_category, card_id, categories)
        if solo is None:
            continue
        claim = claimed_estimate(solo, context, include_idle_balances=False).total_miles
        if claim < context.requirement.miles_required_total:
            continue
        key = (claim, str(card_id), solo)
        if best_solo is None or (claim, str(card_id)) > (best_solo[0], best_solo[1]):
            best_solo = key
    if best_solo is not None:
        drafts.append((StrategyArchetype.SIMPLEST_VIABLE, best_solo[2], False))

    return _build_validated(drafts, opportunities, context, wallet_ids, baseline_claim)


def _solo_assignment(
    candidates_by_category: dict[SpendCategory, tuple[RewardOpportunity, ...]],
    card_id: UUID,
    categories: set[SpendCategory],
) -> Assignment | None:
    """Route every profile category to one card; None if it can't cover all."""
    assignment: Assignment = {}
    for category in categories:
        opportunity = next(
            (o for o in candidates_by_category.get(category, ()) if o.card_id == card_id),
            None,
        )
        if opportunity is None:
            return None
        assignment[category] = opportunity
    return assignment


def _build_validated(
    drafts: list[tuple[StrategyArchetype, Assignment, bool]],
    opportunities: OpportunitySet,
    context: PlanningContext,
    wallet_ids: frozenset[UUID],
    baseline_claim: int,
) -> tuple[CandidateStrategy, ...]:
    """Exit validation + dedupe + deterministic ids. Invalid candidates are
    discarded, never patched (BR-05)."""
    categories = {item.category_slug for item in context.spend_profile.items}
    non_acquirable = {
        aggregate.card_id for aggregate in opportunities.card_aggregates if not aggregate.acquirable
    }
    fees_by_card = {
        aggregate.card_id: aggregate.annual_fee_inr for aggregate in opportunities.card_aggregates
    }

    built: list[CandidateStrategy] = []
    ordinals: dict[StrategyArchetype, int] = {}
    seen: set[object] = set()
    for archetype, assignment, include_idle in drafts:
        if set(assignment) != categories:
            continue  # partial strategies are invalid outputs
        estimate = claimed_estimate(assignment, context, include_idle_balances=include_idle)
        if estimate.total_miles <= 0:
            continue
        plan_cards = {item.from_card_id for item in estimate.transfer_plan}
        cards_used = tuple(sorted({o.card_id for o in assignment.values()} | plan_cards, key=str))
        cards_to_acquire = tuple(c for c in cards_used if c not in wallet_ids)

        # BR-03/BR-04: constraints are never violated, even by a drifted basin.
        if cards_to_acquire and context.constraints.no_new_cards:
            continue
        if any(card_id in non_acquirable for card_id in cards_to_acquire):
            continue
        max_fee = context.constraints.max_annual_fees_inr
        if max_fee is not None and sum(fees_by_card[c] for c in cards_to_acquire) > max_fee:
            continue
        # BR-02 applies to any acquiring candidate, whatever basin produced it.
        if cards_to_acquire and Decimal(estimate.total_miles) <= (
            Decimal(baseline_claim) * _MEANINGFUL_IMPROVEMENT
        ):
            continue

        fingerprint = (
            tuple(sorted((category.value, str(o.card_id)) for category, o in assignment.items())),
            cards_to_acquire,
            estimate.transfer_plan,
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        ordinals[archetype] = ordinals.get(archetype, 0) + 1
        built.append(
            CandidateStrategy(
                strategy_id=f"{archetype.value}-{ordinals[archetype]}",
                archetype=archetype,
                cards_used=cards_used,
                cards_to_acquire=cards_to_acquire,
                spend_allocation={
                    category: opportunity.card_id for category, opportunity in assignment.items()
                },
                transfer_plan=estimate.transfer_plan,
                expected_milestones=estimate.expected_milestones,
                claimed_total_miles=estimate.total_miles,
                assumptions=(
                    f"monthly spend profile held constant for {context.horizon_months} months",
                    "each card's points transfer once, timed so processing completes "
                    "before the target date",
                ),
            )
        )
        if len(built) == _MAX_CANDIDATES:
            break
    return tuple(built)
