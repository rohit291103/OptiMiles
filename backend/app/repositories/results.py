"""Stage 11 persistence — writing a FinalRecommendation's lineage chain.

The orchestrator owns all writes (blueprint §3.1); engines stay pure. This
module is the *only* writer of the user-result tables, and it writes the full
FK lineage in one transaction so a stored recommendation is always
reconstructable: `user_goals → spend_simulations → simulation_results →
recommendation_outputs`, every result row stamped with
`catalog_snapshot_version + engine_version` (D-2).

Kept off the deterministic pipeline path on purpose: `pipeline/run.py` produces
the `FinalRecommendation` with no DB, and this function persists it afterward.
That is what lets the byte-identical determinism test run without a database.

Persistence is best-effort at the request level (blueprint Stage 11: "the
response still returns; failed writes retried once and logged") — the caller
decides whether a write failure is fatal; nothing user-visible depends on it.
"""

import json
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.domain import FinalRecommendation, RankedStrategy

# recommendation_outputs.recommendation_type is a closed CHECK set; a feasible
# plan is spend-routing guidance, an infeasible one is a feasibility verdict.
_TYPE_FEASIBLE = "spend_routing"
_TYPE_INFEASIBLE = "goal_feasibility"


async def persist_recommendation(
    conn: AsyncConnection,
    recommendation: FinalRecommendation,
    *,
    user_id: UUID,
) -> dict[str, UUID]:
    """Write the goal → simulation → result → recommendation chain.

    Returns the minted ids so the API can echo a goal/recommendation id back.
    Runs inside whatever transaction the caller opened (`engine.begin()`).

    **Precondition:** `user_id` must reference an existing `users` row (which
    itself FKs `auth.users`). This is a real authenticated user — the seam does
    NOT create one, because a `users` row can only exist for a Supabase-auth
    identity. The API therefore does not call this until auth lands (Phase 7);
    passing an unbacked id here will fail the `user_goals.user_id` FK.
    """
    goal = recommendation.goal
    requirement = recommendation.requirement

    await conn.execute(
        text(
            """
            INSERT INTO user_goals
              (id, user_id, goal_name, goal_type, partner_id, award_chart_id,
               origin_city, destination_city, cabin_class, award_type,
               num_passengers, target_miles, target_date, status)
            VALUES
              (:id, :user_id, :goal_name, :goal_type, :partner_id, :award_chart_id,
               :origin_city, :destination_city, :cabin_class, :award_type,
               :num_passengers, :target_miles, :target_date, :status)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": goal.id,
            "user_id": user_id,
            "goal_name": goal.goal_name,
            "goal_type": goal.goal_type.value,
            "partner_id": goal.partner_id,
            "award_chart_id": goal.award_chart_id,
            "origin_city": goal.origin_city,
            "destination_city": goal.destination_city,
            "cabin_class": goal.cabin_class.value,
            "award_type": goal.award_type.value,
            "num_passengers": goal.num_passengers,
            "target_miles": requirement.miles_required_total,
            "target_date": goal.target_date,
            "status": goal.status.value,
        },
    )

    simulation_id = uuid4()
    await conn.execute(
        text(
            """
            INSERT INTO spend_simulations (id, user_id, goal_id, simulation_name, status)
            VALUES (:id, :user_id, :goal_id, :name, 'completed')
            """
        ),
        {
            "id": simulation_id,
            "user_id": user_id,
            "goal_id": goal.id,
            "name": goal.goal_name,
        },
    )

    # No simulation_results row on the infeasible path — the adjustment menu is
    # the answer, and there is no ranked strategy to project.
    result_id: UUID | None = None
    if recommendation.recommended is not None:
        result_id = await _write_result_row(
            conn, recommendation, simulation_id, recommendation.recommended
        )

    recommendation_id = await _write_recommendation_row(
        conn, recommendation, user_id, simulation_id, result_id
    )

    ids: dict[str, UUID] = {
        "goal_id": goal.id,
        "simulation_id": simulation_id,
        "recommendation_id": recommendation_id,
    }
    if result_id is not None:
        ids["result_id"] = result_id
    return ids


async def _write_result_row(
    conn: AsyncConnection,
    recommendation: FinalRecommendation,
    simulation_id: UUID,
    recommended: RankedStrategy,
) -> UUID:
    strategy = recommended.strategy
    outcome = recommended.simulation
    result_id = uuid4()

    # JSONB payloads — the month-by-month ledger and plan, serialized in JSON
    # mode so UUID/Decimal keys and values round-trip. The extra "story" keys
    # (allocation_details, score_breakdown, headline, strategy_options) ride in
    # this same free-form JSONB so a saved goal reconstructs everything the live
    # simulator shows, with no schema migration.
    allocations = {
        "spend_allocation": {
            slug.value: str(cid) for slug, cid in strategy.spend_allocation.items()
        },
        "cards_used": [str(c) for c in strategy.cards_used],
        "cards_to_acquire": [str(c) for c in strategy.cards_to_acquire],
        "ledger": [entry.model_dump(mode="json") for entry in outcome.ledger],
        "allocation_details": [
            detail.model_dump(mode="json") for detail in recommended.allocation_details
        ],
        "score_breakdown": recommended.score_breakdown.model_dump(mode="json"),
        "headline_differentiator": recommended.headline_differentiator,
        "strategy_options": _strategy_options(recommendation),
    }
    milestones = [m.model_dump(mode="json") for m in strategy.expected_milestones]
    transfers = [t.model_dump(mode="json") for t in strategy.transfer_plan]

    # `total_monthly_*` are per-month averages (their schema name and pairing
    # in db-schema-v1). The month-by-month truth lives in `card_allocations`;
    # these two are the at-a-glance rate. Average points earned per simulated
    # month across all cards, and the target-program miles the plan lands
    # divided by the months it took (falling back to the full horizon when the
    # goal is missed) — never a cumulative total masquerading as a monthly one.
    months_elapsed = len(outcome.ledger) or 1
    total_points = sum(
        points for entry in outcome.ledger for points in entry.points_by_card.values()
    )
    monthly_points = total_points // months_elapsed
    miles_divisor = outcome.months_to_goal or months_elapsed
    monthly_miles = Decimal(outcome.miles_at_target_date) / Decimal(max(1, miles_divisor))

    await conn.execute(
        text(
            """
            INSERT INTO simulation_results
              (id, simulation_id, goal_id, total_monthly_points_earned,
               total_monthly_miles_earned, months_to_goal, optimization_score,
               card_allocations, milestone_projections, transfer_recommendation,
               catalog_snapshot_version, engine_version)
            VALUES
              (:id, :simulation_id, :goal_id, :points, :miles, :months, :score,
               CAST(:allocations AS JSONB), CAST(:milestones AS JSONB),
               CAST(:transfers AS JSONB), :snapshot_version, :engine_version)
            """
        ),
        {
            "id": result_id,
            "simulation_id": simulation_id,
            "goal_id": recommendation.goal.id,
            "points": monthly_points,
            "miles": str(monthly_miles.quantize(Decimal("0.01"))),
            "months": outcome.months_to_goal,
            "score": str(recommended.score),
            "allocations": _json(allocations),
            "milestones": _json(milestones),
            "transfers": _json(transfers),
            "snapshot_version": recommendation.catalog_snapshot_version,
            "engine_version": recommendation.engine_version,
        },
    )
    return result_id


async def _write_recommendation_row(
    conn: AsyncConnection,
    recommendation: FinalRecommendation,
    user_id: UUID,
    simulation_id: UUID,
    result_id: UUID | None,
) -> UUID:
    narration = recommendation.narration
    recommendation_id = uuid4()
    action_items = (
        [item.model_dump(mode="json") for item in narration.action_items] if narration else []
    )
    # confidence derives from the deterministic score, never LLM self-report
    # (blueprint Stage 9); scale the 0–100 composite into the 0–1 column and
    # quantize to the column's NUMERIC(4,2) so the stored value is exactly what
    # we computed, not what Postgres happens to round to.
    confidence = (
        str((recommendation.recommended.score / 100).quantize(Decimal("0.01")))
        if recommendation.recommended
        else None
    )

    await conn.execute(
        text(
            """
            INSERT INTO recommendation_outputs
              (id, user_id, simulation_id, goal_id, result_id, recommendation_type,
               summary, reasoning, action_items, confidence_score, model_version,
               catalog_snapshot_version, engine_version)
            VALUES
              (:id, :user_id, :simulation_id, :goal_id, :result_id, :rec_type,
               :summary, :reasoning, CAST(:action_items AS JSONB), :confidence,
               :model_version, :snapshot_version, :engine_version)
            """
        ),
        {
            "id": recommendation_id,
            "user_id": user_id,
            "simulation_id": simulation_id,
            "goal_id": recommendation.goal.id,
            "result_id": result_id,
            "rec_type": _TYPE_FEASIBLE if recommendation.verdict.feasible else _TYPE_INFEASIBLE,
            "summary": narration.summary if narration else "",
            "reasoning": narration.reasoning if narration else "",
            "action_items": _json(action_items),
            "confidence": confidence,
            "model_version": narration.model_version if narration else None,
            "snapshot_version": recommendation.catalog_snapshot_version,
            "engine_version": recommendation.engine_version,
        },
    )
    return recommendation_id


def _strategy_options(recommendation: FinalRecommendation) -> list[dict[str, object]]:
    """The 'your cards → +1 card → +2' tier list: the recommended strategy plus
    every alternative, each a compact summary (headline, miles, fees, cards to
    add) — enough to render the comparison story, not the full simulations. The
    recommended one is flagged and listed first; order otherwise follows rank."""
    tiers: list[dict[str, object]] = []
    ranked = []
    if recommendation.recommended is not None:
        ranked.append((recommendation.recommended, True))
    ranked.extend((alt, False) for alt in recommendation.alternatives)
    for option, is_recommended in ranked:
        tiers.append(
            {
                "strategy_id": option.strategy.strategy_id,
                "archetype": option.strategy.archetype.value,
                "headline_differentiator": option.headline_differentiator,
                "miles_at_target_date": option.simulation.miles_at_target_date,
                "months_to_goal": option.simulation.months_to_goal,
                "total_fees_inr": option.simulation.total_fees_inr,
                "cards_used": [str(c) for c in option.strategy.cards_used],
                "cards_to_acquire": [str(c) for c in option.strategy.cards_to_acquire],
                "score": str(option.score),
                "is_recommended": is_recommended,
                "co_recommended": option.co_recommended,
            }
        )
    return tiers


def _json(value: object) -> str:
    """Serialize a JSON-safe structure for a `CAST(:x AS JSONB)` bind."""
    return json.dumps(value)


# The FKs pointing at user_goals (migration 0001) are ON DELETE SET NULL from
# spend_simulations/recommendation_outputs but NO ACTION from
# simulation_results.goal_id — so a bare goal delete would either strand
# lineage rows with NULL goal ids or be rejected outright. Deleting a goal
# therefore removes the whole lineage explicitly, child-first:
# recommendation_outputs → simulation_results → spend_simulations → the goal
# row itself. (simulation_results would also cascade from its parent
# spend_simulations row, but only when its goal_id matches that parent's — an
# unenforced invariant of persist_recommendation, so it gets its own DELETE
# rather than trusting the cascade.) Every statement binds the caller's
# user_id as well as the goal id — simulation_results has no user_id column,
# so it scopes through the ownership of the goal itself — and RLS (D-4) is
# the second line of defence.
_DELETE_LINEAGE_SQL = (
    text(
        """
        DELETE FROM recommendation_outputs
        WHERE goal_id = :goal_id AND user_id = :user_id
        """
    ),
    text(
        """
        DELETE FROM simulation_results sr
        USING user_goals g
        WHERE sr.goal_id = g.id AND g.id = :goal_id AND g.user_id = :user_id
        """
    ),
    text(
        """
        DELETE FROM spend_simulations
        WHERE goal_id = :goal_id AND user_id = :user_id
        """
    ),
    text(
        """
        DELETE FROM user_goals
        WHERE id = :goal_id AND user_id = :user_id
        """
    ),
)


async def delete_goal_lineage(
    conn: AsyncConnection, *, user_id: UUID, goal_id: UUID
) -> bool:
    """Delete one of `user_id`'s goals and its stored lineage.

    Runs inside whatever transaction the caller opened (`engine.begin()`), so
    the lineage never half-disappears. Returns True iff the goal row itself was
    deleted; False means the goal doesn't exist or belongs to someone else
    (deliberately indistinguishable, same as the reads in saved_goals.py).
    """
    params = {"user_id": user_id, "goal_id": goal_id}
    for statement in _DELETE_LINEAGE_SQL[:-1]:
        await conn.execute(statement, params)
    result = await conn.execute(_DELETE_LINEAGE_SQL[-1], params)
    return result.rowcount > 0
