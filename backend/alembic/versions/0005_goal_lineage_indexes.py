"""Indexes for the goal-lineage read/delete paths (2026-07-18 code review).

`repositories/saved_goals.py` picks each goal's latest recommendation via
`LEFT JOIN LATERAL (... WHERE ro.goal_id = g.id ORDER BY ro.created_at DESC,
ro.id DESC LIMIT 1)`, and `repositories/results.py::delete_goal_lineage`
deletes by `goal_id` from both `recommendation_outputs` and
`simulation_results` — but migration 0001 indexed neither table's `goal_id`.
Both were per-goal sequential scans that degrade as rows accumulate.

The composite index matches the lateral's filter + ORDER BY exactly, so the
latest-pick is a single index descent. `simulation_results.goal_id` only needs
equality lookups (delete + the detail join arrives via `id`), so a plain
index suffices.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _execute(sql: str) -> None:
    """asyncpg prepares one command per statement — split multi-statement
    blocks. Statements in this file must never contain ';' inside string
    literals (keep table/column comments semicolon-free)."""
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade() -> None:
    _execute("""
        CREATE INDEX idx_recs_goal_latest
          ON recommendation_outputs (goal_id, created_at DESC, id DESC);
        CREATE INDEX idx_results_goal_id
          ON simulation_results (goal_id)
    """)


def downgrade() -> None:
    _execute("""
        DROP INDEX IF EXISTS idx_recs_goal_latest;
        DROP INDEX IF EXISTS idx_results_goal_id
    """)
