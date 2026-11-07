"""Activity log — logged spends and lounge visits.

Roadmap Phase 1 (lounge visit logging) + Phase 2 (spend logging), built as ONE
pattern by decision: the roadmap requires "same entry surface, same mental
model — or users end up with two separate things to remember and do neither".

TWO TABLES, ONE PATTERN. The shared shape is (user, card, date, note) and the
shared machinery is the period window (`simulation/periods.py`) that both are
counted inside; the payloads have nothing in common (₹ and a category vs. a
scope and a guest count). A single polymorphic table would be half-NULL columns
guarded by per-kind CHECKs — the classic version of this mistake — so the
sharing lives in the window arithmetic, the API surface and the UI, where it is
actually load-bearing. The load-bearing link between them is real and one-way:
a lounge spend gate ("₹60,000 in the preceding quarter") is evaluated FROM the
spend log, which is why neither half could have been built alone.

`card_id` references the catalog, not `user_cards` — the wallet is still a
per-device list (`frontend/src/lib/wallet.ts`) and logging must not be gated on
a server-side wallet that does not exist yet. ON DELETE RESTRICT, deliberately:
a catalog edit must never silently delete a user's own records. Catalog rows are
retired with `is_active = false` and never hard-deleted, so this cannot fire in
normal operation — it is there to make sure that stays true.

No `source` column yet (manual vs. statement upload). Statement/CSV import is
real and named in the same roadmap phase, but it changes BEHAVIOUR, not just
provenance: an imported statement makes the log complete for its period rather
than a lower bound, which is the honesty model in `domain/activity.py`. That
belongs in the slice that ships the importer.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _execute(sql: str) -> None:
    """asyncpg prepares one command per statement — split multi-statement
    blocks. Statements must never contain ';' inside string literals."""
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade() -> None:
    _execute("""
        CREATE TABLE spend_entries (
          id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          card_id       UUID        NOT NULL REFERENCES cards(id) ON DELETE RESTRICT,
          occurred_on   DATE        NOT NULL,
          amount_inr    INTEGER     NOT NULL CHECK (amount_inr > 0),
          category_slug TEXT        NOT NULL CHECK (category_slug IN ('travel', 'dining', 'international', 'fuel', 'groceries', 'utilities', 'online', 'default')),
          note          TEXT,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE spend_entries IS
          'User-logged spend. A LOWER BOUND on real spend - it can prove a milestone or lounge spend gate was reached, never that one was missed.';
        COMMENT ON COLUMN spend_entries.category_slug IS
          'Chosen by the user from the catalog vocabulary. There is no merchant to category mapping by decision - a wrong mapping produces a wrong recommendation.';
    """)

    _execute("""
        CREATE TABLE lounge_visits (
          id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          card_id       UUID        NOT NULL REFERENCES cards(id) ON DELETE RESTRICT,
          occurred_on   DATE        NOT NULL,
          scope         TEXT        NOT NULL CHECK (scope IN ('domestic', 'international')),
          guest_count   INTEGER     NOT NULL DEFAULT 0 CHECK (guest_count >= 0),
          airport_code  TEXT        CHECK (airport_code ~ '^[A-Z]{3}$'),
          note          TEXT,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE lounge_visits IS
          'User-logged lounge visits. Recorded against (card, scope), never against an entitlement tier - a cardholder has no reason to know which tier admitted them, so attribution is the calculator job.';
        COMMENT ON COLUMN lounge_visits.airport_code IS
          'Free IATA-style code. No FK - the airport directory is a separate data track and must not block this.';
    """)

    # The two access patterns, one index each: the paged "my log" list
    # (newest first, tie-broken on id so paging is stable), and the
    # per-card window aggregate the observed-activity calculator reads.
    _execute("""
        CREATE INDEX ix_spend_entries_user_recent ON spend_entries (user_id, occurred_on DESC, id DESC);
        CREATE INDEX ix_spend_entries_user_card   ON spend_entries (user_id, card_id, occurred_on);
        CREATE INDEX ix_lounge_visits_user_recent ON lounge_visits (user_id, occurred_on DESC, id DESC);
        CREATE INDEX ix_lounge_visits_user_card   ON lounge_visits (user_id, card_id, occurred_on)
    """)

    # Mirrors migrations 0006/0007: keep updated_at honest rather than decorative.
    _execute("""
        CREATE TRIGGER trg_spend_entries_updated_at
          BEFORE UPDATE ON spend_entries
          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        CREATE TRIGGER trg_lounge_visits_updated_at
          BEFORE UPDATE ON lounge_visits
          FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # User-scoped tables get owner-only RLS (D-4). FastAPI holds the service
    # role and scopes every query by the verified token subject; this is the
    # second line of defence behind that, same posture as user_goals.
    _execute("""
        ALTER TABLE spend_entries ENABLE ROW LEVEL SECURITY;
        ALTER TABLE lounge_visits ENABLE ROW LEVEL SECURITY;
        CREATE POLICY spend_entries_own ON spend_entries FOR ALL
          USING (auth.uid() = user_id);
        CREATE POLICY lounge_visits_own ON lounge_visits FOR ALL
          USING (auth.uid() = user_id)
    """)


def downgrade() -> None:
    _execute("""
        DROP TABLE IF EXISTS lounge_visits;
        DROP TABLE IF EXISTS spend_entries
    """)
