"""cards.acquirable — closed-to-new-applicants flag (Phase 4 requirement).

Axis Atlas was discontinued for new applicants in 2026 (catalog-expansion
decision log, 2026-07-04): existing holders keep the card, but the
Optimization Engine's one-new-card archetype must never recommend acquiring
it. `acquirable` defaults TRUE — the closed state is the exception, set
from the reviewed seeds.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
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
        ALTER TABLE cards ADD COLUMN acquirable BOOLEAN NOT NULL DEFAULT TRUE;
        COMMENT ON COLUMN cards.acquirable IS
          'FALSE = closed to new applicants (existing holders unaffected) — strategies must never recommend acquiring it'
    """)


def downgrade() -> None:
    _execute("ALTER TABLE cards DROP COLUMN acquirable")
