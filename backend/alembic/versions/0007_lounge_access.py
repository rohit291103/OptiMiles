"""Lounge Access Intelligence — programmes and per-card entitlements.

Roadmap Phase 1 (`docs/prd/product-roadmap-v1.md` → Lounge Access
Intelligence). Replaces nothing yet, deliberately: `cards.has_lounge_access`
STAYS as the coarse fallback until every supported card has real rows here.
Dropping it while coverage is partial would turn "we have not researched this
card yet" into the false claim "this card has no lounge access" — the exact
trust failure this feature exists to prevent. The column goes in a later
migration, once coverage is complete.

Provenance (source / verified_on / needs_verification) is deliberately NOT
stored here, matching every other catalog table: the reviewed YAML seeds are
the audited artifact (`repositories/catalog_admin.py`). Lounge rows carry the
heaviest provenance in the repo, and it belongs where a human reviews it.

Design notes worth carrying:
- Domestic and international entitlements are separate ROWS, never one
  combined count. They almost never match on an Indian card.
- `reset_anchor` is NOT NULL with no default. Issuers reset variously on the
  calendar quarter, the card anniversary and the statement cycle; a silent
  default is the likeliest source of a wrong visit count, and a wrong count
  sends someone to a lounge desk to be turned away.
- Tiered cards get one row per tier, distinguished by `spend_gate_inr`, which
  is why the uniqueness constraint includes the gate.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
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
        CREATE TABLE lounge_programs (
          id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          program_name  TEXT        NOT NULL UNIQUE,
          operator      TEXT,
          notes         TEXT,
          is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE lounge_programs IS
          'Networks lounge access rides on (Priority Pass, DreamFolks, LoungeOne, network and issuer-direct programmes). Most perishable rows in the catalog - issuers switch vendors mid-year.';
    """)

    _execute("""
        CREATE TABLE card_lounge_access (
          id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          card_id                 UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          program_id              UUID        NOT NULL REFERENCES lounge_programs(id),
          scope                   TEXT        NOT NULL CHECK (scope IN ('domestic', 'international')),

          visits_per_period       INTEGER     CHECK (visits_per_period >= 0),
          period                  TEXT        NOT NULL CHECK (period IN ('monthly', 'quarterly', 'half_yearly', 'annual', 'statement_cycle', 'lifetime')),
          reset_anchor            TEXT        NOT NULL CHECK (reset_anchor IN ('calendar_quarter', 'calendar_year', 'card_anniversary', 'statement_cycle', 'not_applicable')),

          guest_visits_per_period INTEGER     CHECK (guest_visits_per_period >= 0),
          guests_share_allowance  BOOLEAN     NOT NULL DEFAULT FALSE,

          spend_gate_inr          INTEGER     CHECK (spend_gate_inr >= 0),
          spend_gate_period       TEXT        CHECK (spend_gate_period IN ('monthly', 'quarterly', 'half_yearly', 'annual', 'statement_cycle', 'lifetime')),

          enrollment_required     BOOLEAN     NOT NULL DEFAULT FALSE,
          enrollment_url          TEXT,
          conditions              TEXT,

          is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
          created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

          CONSTRAINT ck_lounge_spend_gate_paired CHECK (
            (spend_gate_inr IS NULL) = (spend_gate_period IS NULL)
          ),
          CONSTRAINT ck_lounge_counted_needs_anchor CHECK (
            visits_per_period IS NULL OR reset_anchor <> 'not_applicable'
          )
        );
        COMMENT ON TABLE card_lounge_access IS
          'One card entitlement in one programme for one scope. NULL visits_per_period means unlimited - 0 means none granted, which is a different and real answer.';
        COMMENT ON COLUMN card_lounge_access.reset_anchor IS
          'Seeded explicitly per card, never defaulted - the likeliest source of a wrong visit count.';
        COMMENT ON COLUMN card_lounge_access.spend_gate_inr IS
          'Spend in the PRECEDING spend_gate_period that unlocks these visits. The condition most cardholders get wrong.';
    """)

    _execute("""
        CREATE UNIQUE INDEX uq_card_lounge_scope_tier
          ON card_lounge_access (card_id, program_id, scope, COALESCE(spend_gate_inr, -1))
          WHERE is_active
    """)
    _execute("""
        CREATE INDEX ix_card_lounge_access_card ON card_lounge_access (card_id) WHERE is_active
    """)
    # Mirrors migration 0006: keep updated_at honest rather than decorative.
    _execute("""
        CREATE TRIGGER trg_card_lounge_access_updated_at
          BEFORE UPDATE ON card_lounge_access
          FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # Catalog tables are world-readable, writes are service-role only —
    # same posture as migration 0003.
    _execute("""
        ALTER TABLE lounge_programs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE card_lounge_access ENABLE ROW LEVEL SECURITY;
        CREATE POLICY lounge_programs_read ON lounge_programs FOR SELECT USING (TRUE);
        CREATE POLICY card_lounge_access_read ON card_lounge_access FOR SELECT USING (TRUE)
    """)


def downgrade() -> None:
    _execute("""
        DROP TABLE IF EXISTS card_lounge_access;
        DROP TABLE IF EXISTS lounge_programs
    """)
