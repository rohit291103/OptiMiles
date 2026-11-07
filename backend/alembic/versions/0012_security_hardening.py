"""Security hardening from the Supabase security advisor (2026-11-07 audit).

1. `alembic_version` had row-level security OFF while Supabase grants the
   public `anon` / `authenticated` roles full table privileges by default —
   anyone holding the (public, browser-shipped) anon key could INSERT, UPDATE
   or DELETE the migration bookkeeping row and break future upgrades. RLS on
   with no policies denies those roles; the `postgres` owner that the backend
   and alembic connect as is the table owner and is not subject to RLS.
2. `handle_new_auth_user()` is a SECURITY DEFINER trigger function exposed as
   `/rest/v1/rpc/handle_new_auth_user`. It only ever needs to run as the
   `on_auth_user_created` trigger, and trigger firing does not check EXECUTE,
   so the public roles lose the right to call it directly.
3. `set_updated_at()` had a role-mutable search_path. It only uses NOW() and
   NEW, so pinning search_path to empty (pg_catalog is always searched) is
   behaviour-neutral.

No user data or catalog content changes. Verified after applying: anon can no
longer write `alembic_version`; sign-up trigger and timestamps unaffected.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.alembic_version FROM anon, authenticated")
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.handle_new_auth_user() FROM PUBLIC, anon, authenticated"
    )
    op.execute("ALTER FUNCTION public.set_updated_at() SET search_path = ''")


def downgrade() -> None:
    op.execute("ALTER FUNCTION public.set_updated_at() RESET search_path")
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.handle_new_auth_user() TO PUBLIC, anon, authenticated"
    )
    op.execute("GRANT ALL ON public.alembic_version TO anon, authenticated")
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
