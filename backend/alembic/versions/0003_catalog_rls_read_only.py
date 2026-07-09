"""Enable RLS on the public catalog tables with a read-only policy.

Supabase exposes every `public` table to PostgREST via the anon key, so the
linter flags catalog tables without RLS as "Critical". The catalog is public
reference data (card names, transfer ratios, award charts) — not secret — but
D-4 wants RLS on as defense-in-depth for any direct-from-frontend read. So:
enable RLS and grant a **public SELECT-only** policy. Reads stay open (the data
is meant to be read); the absence of INSERT/UPDATE/DELETE policies means writes
are denied to anon/authenticated, leaving `repositories/catalog_admin.py` (the
service role, which bypasses RLS) as the only writer — exactly the intended
posture. The eight user-scoped tables already got RLS in 0001.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATALOG_TABLES = (
    "reward_currencies",
    "transfer_partners",
    "cards",
    "reward_categories",
    "currency_transfer_partners",
    "reward_milestones",
    "award_charts",
)


def _execute(sql: str) -> None:
    """asyncpg prepares one command per statement — split multi-statement
    blocks (statements must never contain ';' inside a string literal)."""
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade() -> None:
    for table in _CATALOG_TABLES:
        # Public read-only: RLS on + a SELECT policy for everyone. No write
        # policy ⇒ only the RLS-bypassing service role can mutate the catalog.
        _execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY {table}_public_read ON {table} FOR SELECT
              USING (true)
        """)


def downgrade() -> None:
    for table in _CATALOG_TABLES:
        _execute(f"""
            DROP POLICY IF EXISTS {table}_public_read ON {table};
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY
        """)
