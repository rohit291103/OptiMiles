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
