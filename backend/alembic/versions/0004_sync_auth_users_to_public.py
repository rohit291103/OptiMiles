"""Sync new Supabase auth.users into public.users (+ backfill).

`user_goals.user_id` (and every user-scoped table) FKs `public.users`, but
Supabase Auth only creates rows in `auth.users`. Nothing bridged the two, so a
signed-in save FK-violated (`public.users` was empty). This is the standard
Supabase pattern: an AFTER INSERT trigger on auth.users that mirrors the new
identity into public.users. Also backfills any auth.users that already exist.

`full_name` is pulled from the OAuth/user metadata when present. The insert is
idempotent (ON CONFLICT DO NOTHING) so re-runs and races are safe.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _execute(sql: str) -> None:
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade() -> None:
    # The trigger function lives in public and runs as SECURITY DEFINER so it
    # can write public.users regardless of the inserting role.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
          INSERT INTO public.users (id, full_name)
          VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name')
          ON CONFLICT (id) DO NOTHING;
          RETURN NEW;
        END;
        $func$
        """
    )
    # Defense-in-depth: a SECURITY DEFINER function is EXECUTE-able by PUBLIC by
    # default. It can only run as this trigger (NEW is unavailable otherwise),
    # but revoke direct EXECUTE anyway so no role can call it outside the trigger.
    op.execute("REVOKE EXECUTE ON FUNCTION public.handle_new_auth_user() FROM PUBLIC")
    _execute("""
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
          AFTER INSERT ON auth.users
          FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user()
    """)
    # Backfill identities that already exist in auth.users.
    op.execute(
        """
        INSERT INTO public.users (id, full_name)
        SELECT id, raw_user_meta_data->>'full_name'
        FROM auth.users
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    _execute("""
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        DROP FUNCTION IF EXISTS public.handle_new_auth_user()
    """)
