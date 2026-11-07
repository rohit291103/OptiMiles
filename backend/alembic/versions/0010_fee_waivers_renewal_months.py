"""Annual-fee waivers (catalog) and per-card renewal months (user data).

Decision log `2026-11-02-fee-waiver-progress.md`. Two tables, because they
are two different kinds of fact with two different owners:

card_fee_waivers — CATALOG. What the issuer publishes about waiving a card's
annual fee on spend. One row per card at most, its own row rather than columns
on `cards` so the waiver is reviewed (and flagged) separately from the card's
fee and earn rate. Provenance stays in the reviewed YAML, as for every catalog
table. Three answers, not two:
  kind = 'spend_based' — the terms are stated (threshold, whether the
                         threshold itself counts, the window, which fees);
  kind = 'none'        — a SOURCED statement that the issuer lists no waiver;
  no row               — not covered yet.
'none' is never a default for an unresearched card, and the CHECKs make a
row carry its terms iff it is spend-based. No column has a DEFAULT that would
state a fact: `excluded_categories` and `unmodelled_exclusions` are NOT NULL
with no default (an omitted list would silently mean "everything counts").
`unmodelled_exclusions` names what the issuer excludes that we cannot log
separately (rent, wallet loads) — when non-empty, a REACHED is "reached on
your log, subject to these", not proof.

card_renewal_months — USER DATA. The month a user's annual fee is charged,
per (user, card). A MONTH, not a date, deliberately: the waiver window we can
prove from a month alone (the 11 whole months between renewal months —
`simulation/periods.renewal_window`) lies inside the issuer's real window
whatever the day is, so the day would add at most one month of countable
spend while being something most users would have to look up. Less personal
data, same honesty. Optional: no row means "we don't know", and the product
says "tell us your renewal month" rather than assuming one.

`card_id` references the catalog, not `user_cards`, for the same reason as
migration 0008: the wallet is still per-device, and this must not wait for a
server-side wallet. ON DELETE RESTRICT on the card for the same reason too.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
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
        CREATE TABLE card_fee_waivers (
          id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          card_id               UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          kind                  TEXT        NOT NULL CHECK (kind IN ('spend_based', 'none')),
          threshold_inr         INTEGER     CHECK (threshold_inr > 0),
          threshold_comparison  TEXT        CHECK (threshold_comparison IN ('at_least', 'more_than')),
          window_kind           TEXT        CHECK (window_kind IN ('preceding_card_year', 'current_card_year', 'days_365_before_fee_date')),
          waives_renewal_fee    BOOLEAN     NOT NULL,
          waives_joining_fee    BOOLEAN     NOT NULL,
          excluded_categories   TEXT[]      NOT NULL CHECK (excluded_categories <@ ARRAY['travel', 'dining', 'international', 'fuel', 'groceries', 'utilities', 'online', 'default']::TEXT[]),
          unmodelled_exclusions TEXT[]      NOT NULL,
          conditions            TEXT,
          is_active             BOOLEAN     NOT NULL DEFAULT TRUE,
          created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

          CONSTRAINT ck_fee_waiver_terms_iff_spend_based CHECK (
            (kind = 'spend_based') = (
              threshold_inr IS NOT NULL
              AND threshold_comparison IS NOT NULL
              AND window_kind IS NOT NULL
            )
          ),
          CONSTRAINT ck_fee_waiver_spend_based_waives_something CHECK (
            kind <> 'spend_based' OR waives_renewal_fee OR waives_joining_fee
          ),
          CONSTRAINT ck_fee_waiver_none_is_bare CHECK (
            kind <> 'none' OR (
              threshold_inr IS NULL
              AND threshold_comparison IS NULL
              AND window_kind IS NULL
              AND NOT waives_renewal_fee
              AND NOT waives_joining_fee
              AND cardinality(excluded_categories) = 0
              AND cardinality(unmodelled_exclusions) = 0
            )
          )
        );
        COMMENT ON TABLE card_fee_waivers IS
          'What the issuer publishes about waiving the annual fee on spend. kind none is a sourced answer - no row at all means not covered yet. A renewal benefit paid after the fee (vouchers) is NOT a waiver.';
        COMMENT ON COLUMN card_fee_waivers.threshold_comparison IS
          'at_least = meeting the figure qualifies (HDFC, SBI). more_than = it must be exceeded (HSBC exceeds 800,000).';
        COMMENT ON COLUMN card_fee_waivers.excluded_categories IS
          'Logged spend categories the issuer names as not counting. No default - an omitted list would silently mean everything counts.';
        COMMENT ON COLUMN card_fee_waivers.unmodelled_exclusions IS
          'Issuer exclusions our logging vocabulary cannot separate (rent, wallet loads), or a statement that eligible spend is undefined. Non-empty means a REACHED is subject to these exclusions, not proof.'
    """)

    # One active answer per card (FW-02 in validate_catalog mirrors this).
    _execute("""
        CREATE UNIQUE INDEX uq_card_fee_waiver ON card_fee_waivers (card_id) WHERE is_active
    """)

    _execute("""
        CREATE TABLE card_renewal_months (
          user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          card_id        UUID        NOT NULL REFERENCES cards(id) ON DELETE RESTRICT,
          renewal_month  SMALLINT    NOT NULL CHECK (renewal_month BETWEEN 1 AND 12),
          created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY (user_id, card_id)
        );
        COMMENT ON TABLE card_renewal_months IS
          'The month a user annual fee is charged, per card. Optional - absence means unknown and fee-waiver progress is not computed. A month, not a date, by decision.'
    """)

    # Mirrors 0006-0008: keep updated_at honest rather than decorative.
    _execute("""
        CREATE TRIGGER trg_card_fee_waivers_updated_at
          BEFORE UPDATE ON card_fee_waivers
          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        CREATE TRIGGER trg_card_renewal_months_updated_at
          BEFORE UPDATE ON card_renewal_months
          FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # Catalog: world-readable, service-role writes (0003 posture).
    # User data: owner-only (D-4, same as 0008) — the second line of defence
    # behind every query being scoped by the verified token subject.
    _execute("""
        ALTER TABLE card_fee_waivers ENABLE ROW LEVEL SECURITY;
        CREATE POLICY card_fee_waivers_read ON card_fee_waivers FOR SELECT USING (TRUE);
        ALTER TABLE card_renewal_months ENABLE ROW LEVEL SECURITY;
        CREATE POLICY card_renewal_months_own ON card_renewal_months FOR ALL
          USING (auth.uid() = user_id)
    """)


def downgrade() -> None:
    _execute("""
        DROP TABLE IF EXISTS card_renewal_months;
        DROP TABLE IF EXISTS card_fee_waivers
    """)
