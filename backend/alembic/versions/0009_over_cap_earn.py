"""reward_categories.over_cap_earn — what spend ABOVE a category cap earns.

Defect fixed (decision log `2026-11-02-cap-overflow-earn.md`): 0001 baked one
answer into the schema comment — "Beyond the cap, spend earns base_earn_rate"
— and every engine priced overflow that way. That is true for some issuers
(Axis Atlas's T&C pays the base rate on the excess) and false for others: SBI
Cashback pays NOTHING once its ₹2,000-per-statement-cycle online (or offline)
cashback limit is reached. Spend past ₹40,000 online was being projected at
1%, money the card never pays.

The overflow behaviour is a fact about each capped rule, so it is a column on
the rule, stated per row from the issuer's terms:

  'base_rate' — spend above the cap earns the card's base_earn_rate
  'nothing'   — spend above the cap earns zero

NULL, and only NULL, on an UNCAPPED rule (there is no overflow to describe).
The CHECK makes that two-way: a capped rule cannot leave it unstated and an
uncapped rule cannot carry a meaningless value. No DEFAULT, deliberately —
a silent default is exactly the assumption being removed.

BACKFILL (explicit, not a default): every row that is capped TODAY was loaded
under 0001's documented semantics, so it is backfilled 'base_rate' — that
restates what the database already claimed rather than inventing a new fact.
The reviewed seeds (`seeds/catalog/cards.yaml`) carry the sourced per-row
value and the next seed load overwrites this backfill. SBI Cashback's capped
rules — online (cap ₹40,000) AND offline/`default` (cap ₹2,00,000) — are
corrected to 'nothing' here too, so the live catalog does not keep the
known-wrong 'base_rate' between this migration and that load. The SBI lookup
is by (bank, card_name, category_slug IN ('online', 'default')) — catalog rows
have no seed slug column — and only touches rows that are capped at that
moment (`over_cap_earn IS NOT NULL` after the first UPDATE). The offline cap
itself arrives with the next seed load (in a pre-0009 DB the default row is
uncapped), so on today's DB the 'default' half matches nothing; it is there so
that any SBI rule capped at migration time gets the issuer's 'nothing', never
the base-rate backfill.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
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
        ALTER TABLE reward_categories ADD COLUMN over_cap_earn TEXT;

        UPDATE reward_categories
           SET over_cap_earn = 'base_rate'
         WHERE monthly_cap_inr IS NOT NULL
            OR quarterly_cap_inr IS NOT NULL
            OR annual_cap_inr IS NOT NULL;

        UPDATE reward_categories rc
           SET over_cap_earn = 'nothing'
          FROM cards c
         WHERE rc.card_id = c.id
           AND c.bank = 'SBI'
           AND c.card_name = 'Cashback'
           AND rc.category_slug IN ('online', 'default')
           AND rc.over_cap_earn IS NOT NULL;

        ALTER TABLE reward_categories
          ADD CONSTRAINT chk_over_cap_earn_value
          CHECK (over_cap_earn IS NULL OR over_cap_earn IN ('base_rate', 'nothing'));

        ALTER TABLE reward_categories
          ADD CONSTRAINT chk_over_cap_earn_iff_capped
          CHECK (
            (over_cap_earn IS NULL) = (
              monthly_cap_inr IS NULL
              AND quarterly_cap_inr IS NULL
              AND annual_cap_inr IS NULL
            )
          );

        COMMENT ON COLUMN reward_categories.over_cap_earn IS
          'What spend ABOVE this rule''s cap earns - base_rate (the card base_earn_rate) or nothing (zero). Stated per row from issuer terms. NULL iff the rule is uncapped.';

        COMMENT ON COLUMN reward_categories.monthly_cap_inr IS
          'Max eligible spend/month at this rate. What spend beyond the cap earns is over_cap_earn - never assumed.'
    """)


def downgrade() -> None:
    _execute("""
        ALTER TABLE reward_categories DROP CONSTRAINT chk_over_cap_earn_iff_capped;
        ALTER TABLE reward_categories DROP CONSTRAINT chk_over_cap_earn_value;
        ALTER TABLE reward_categories DROP COLUMN over_cap_earn;
        COMMENT ON COLUMN reward_categories.monthly_cap_inr IS
          'Max eligible spend/month at this rate. Beyond the cap, spend earns base_earn_rate.'
    """)
