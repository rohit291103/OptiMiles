"""Read side of the goal lineage — listing a user's saved goals for the
"My Goals" view (build-plan Phase 7 follow-up).

The mirror of `results.py`: that module is the only *writer* of the user-result
tables; this is the read query the API uses to show a signed-in user the goals
they saved. Scoped to a single `user_id` (the verified `auth.users` id from the
access token) — the query never spans users, and RLS (D-4) is the second line
of defence behind that scoping.

One row per goal, newest first, each joined to its latest
`recommendation_outputs` row so the list card can show the one-line summary and
the snapshot it was computed against without a second round trip. Read-only and
parameterized; it writes nothing.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class SavedGoalRow:
    """One saved goal joined to its most recent recommendation.

    Everything here is read straight from persisted columns — no recomputation,
    so the list reflects exactly what was stored at save time (and the
    `catalog_snapshot_version` that produced it)."""

    goal_id: UUID
    goal_name: str
    goal_type: str
    destination_city: str | None
    cabin_class: str | None
    target_miles: int
    target_date: date | None
    status: str
    created_at: datetime
    # From the latest recommendation_outputs row (may be absent if a goal was
    # somehow saved without one — left None rather than dropping the goal).
    summary: str | None
    confidence_score: float | None
    catalog_snapshot_version: str | None


# Latest recommendation per goal via a LEFT JOIN LATERAL (so a goal with no
# recommendation still lists, with NULL recommendation fields). The inner
# ORDER BY breaks ties on `id` after `created_at` so the pick is deterministic
# even if two outputs for one goal ever share a timestamp — determinism is a
# standing invariant. Goals themselves are ordered newest first.
_LIST_SQL = text(
    """
    SELECT
      g.id                AS goal_id,
      g.goal_name         AS goal_name,
      g.goal_type         AS goal_type,
      g.destination_city  AS destination_city,
      g.cabin_class       AS cabin_class,
      g.target_miles      AS target_miles,
      g.target_date       AS target_date,
      g.status            AS status,
      g.created_at        AS created_at,
      r.summary           AS summary,
      r.confidence_score  AS confidence_score,
      r.catalog_snapshot_version AS catalog_snapshot_version
    FROM user_goals g
    LEFT JOIN LATERAL (
      SELECT ro.summary, ro.confidence_score, ro.catalog_snapshot_version
      FROM recommendation_outputs ro
      WHERE ro.goal_id = g.id
      ORDER BY ro.created_at DESC, ro.id DESC
      LIMIT 1
    ) r ON TRUE
    WHERE g.user_id = :user_id
    ORDER BY g.created_at DESC
    """
)


@dataclass(frozen=True)
class SavedGoalDetailRow:
    """One saved goal's full persisted lineage — the goal row, its latest
    recommendation, and that recommendation's simulation_results payloads.

    The JSONB columns (`card_allocations`, `milestone_projections`,
    `transfer_recommendation`, `action_items`) surface exactly as
    `repositories/results.py` wrote them — reconstruction into response types
    happens at the API edge, never by recomputing engine outputs."""

    goal_id: UUID
    goal_name: str
    goal_type: str
    origin_city: str | None
    destination_city: str | None
    cabin_class: str | None
    num_passengers: int | None
    target_miles: int
    target_date: date | None
    status: str
    created_at: datetime
    # Latest recommendation_outputs row (LEFT JOIN — None fields if absent).
    recommendation_type: str | None
    summary: str | None
    reasoning: str | None
    action_items: list[dict[str, Any]] | None
    confidence_score: float | None
    model_version: str | None
    catalog_snapshot_version: str | None
    engine_version: str | None
    # Its simulation_results row (absent only when nothing was allocatable —
    # infeasible goals normally persist a best-effort plan, results.py).
    months_to_goal: int | None
    optimization_score: Decimal | None
    card_allocations: dict[str, Any] | None
    milestone_projections: list[dict[str, Any]] | None
    transfer_recommendation: list[dict[str, Any]] | None


# The detail read behind a dashboard goal card. Scoped to BOTH ids — a user can
# never read another user's goal by guessing its UUID; no row ⇒ the API 404s
# without revealing whether the goal exists. Same deterministic latest-pick as
# the list query, then LEFT JOIN to the simulation_results row that
# recommendation references (absent only when nothing was allocatable;
# infeasible goals normally carry a best-effort plan's row).
_DETAIL_SQL = text(
    """
    SELECT
      g.id                AS goal_id,
      g.goal_name         AS goal_name,
      g.goal_type         AS goal_type,
      g.origin_city       AS origin_city,
      g.destination_city  AS destination_city,
      g.cabin_class       AS cabin_class,
      g.num_passengers    AS num_passengers,
      g.target_miles      AS target_miles,
      g.target_date       AS target_date,
      g.status            AS status,
      g.created_at        AS created_at,
      r.recommendation_type AS recommendation_type,
      r.summary           AS summary,
      r.reasoning         AS reasoning,
      r.action_items      AS action_items,
      r.confidence_score  AS confidence_score,
      r.model_version     AS model_version,
      r.catalog_snapshot_version AS catalog_snapshot_version,
      r.engine_version    AS engine_version,
      sr.months_to_goal   AS months_to_goal,
      sr.optimization_score AS optimization_score,
      sr.card_allocations AS card_allocations,
      sr.milestone_projections AS milestone_projections,
      sr.transfer_recommendation AS transfer_recommendation
    FROM user_goals g
    LEFT JOIN LATERAL (
      SELECT ro.recommendation_type, ro.summary, ro.reasoning, ro.action_items,
             ro.confidence_score, ro.model_version, ro.catalog_snapshot_version,
             ro.engine_version, ro.result_id
      FROM recommendation_outputs ro
      WHERE ro.goal_id = g.id
      ORDER BY ro.created_at DESC, ro.id DESC
      LIMIT 1
    ) r ON TRUE
    LEFT JOIN simulation_results sr ON sr.id = r.result_id
    WHERE g.id = :goal_id AND g.user_id = :user_id
    """
)


async def get_saved_goal(
    conn: AsyncConnection, *, user_id: UUID, goal_id: UUID
) -> SavedGoalDetailRow | None:
    """The full persisted lineage for one of `user_id`'s goals, or None when
    the goal doesn't exist or belongs to someone else (deliberately
    indistinguishable — the query never spans users)."""
    result = await conn.execute(_DETAIL_SQL, {"user_id": user_id, "goal_id": goal_id})
    rows = result.mappings().all()
    if not rows:
        return None
    row = rows[0]
    return SavedGoalDetailRow(
        goal_id=row["goal_id"],
        goal_name=row["goal_name"],
        goal_type=row["goal_type"],
        origin_city=row["origin_city"],
        destination_city=row["destination_city"],
        cabin_class=row["cabin_class"],
        num_passengers=row["num_passengers"],
        target_miles=row["target_miles"],
        target_date=row["target_date"],
        status=row["status"],
        created_at=row["created_at"],
        recommendation_type=row["recommendation_type"],
        summary=row["summary"],
        reasoning=row["reasoning"],
        action_items=row["action_items"],
        confidence_score=(
            float(row["confidence_score"])
            if row["confidence_score"] is not None
            else None
        ),
        model_version=row["model_version"],
        catalog_snapshot_version=row["catalog_snapshot_version"],
        engine_version=row["engine_version"],
        months_to_goal=row["months_to_goal"],
        optimization_score=row["optimization_score"],
        card_allocations=row["card_allocations"],
        milestone_projections=row["milestone_projections"],
        transfer_recommendation=row["transfer_recommendation"],
    )


async def list_saved_goals(
    conn: AsyncConnection, *, user_id: UUID
) -> tuple[SavedGoalRow, ...]:
    """The `user_id`'s saved goals, newest first, each with its latest
    recommendation summary. Empty tuple when the user has saved nothing."""
    result = await conn.execute(_LIST_SQL, {"user_id": user_id})
    rows = result.mappings().all()
    return tuple(
        SavedGoalRow(
            goal_id=row["goal_id"],
            goal_name=row["goal_name"],
            goal_type=row["goal_type"],
            destination_city=row["destination_city"],
            cabin_class=row["cabin_class"],
            target_miles=row["target_miles"],
            target_date=row["target_date"],
            status=row["status"],
            created_at=row["created_at"],
            summary=row["summary"],
            confidence_score=(
                float(row["confidence_score"])
                if row["confidence_score"] is not None
                else None
            ),
            catalog_snapshot_version=row["catalog_snapshot_version"],
        )
        for row in rows
    )
