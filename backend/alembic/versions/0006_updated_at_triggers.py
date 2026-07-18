"""Make `updated_at` columns true (2026-07-18 code review).

Five tables carry `updated_at TIMESTAMPTZ DEFAULT NOW()` but nothing — no
trigger, no app code — ever set it on UPDATE, so the column silently stayed
equal to `created_at` forever. A column that lies is worse than no column:
this adds the standard BEFORE UPDATE trigger so every row update stamps
`updated_at = NOW()` in the database, where it can't be forgotten by a
future write path.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("users", "cards", "user_cards", "user_goals", "spend_simulations")


def upgrade() -> None:
    # plpgsql body contains ';' — must go through a single op.execute, never
    # the semicolon-splitting helper (same constraint as migration 0004).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $func$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $func$
        """
    )
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS set_updated_at ON {table}")
        op.execute(
            f"""
            CREATE TRIGGER set_updated_at
              BEFORE UPDATE ON {table}
              FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
            """
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS set_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at()")
