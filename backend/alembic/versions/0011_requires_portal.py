"""reward_categories.requires_portal — the booking channel a bonus rate needs.

Some bonus rates apply only when the purchase is booked through the issuer's
own portal: HDFC SmartBuy (Infinia, Diners Club Black travel 5X) and Axis
Travel EDGE (Magnus for Burgundy travel 5X). The same flight booked with the
airline directly earns the card's base rate. Nothing in the schema said so —
the condition lived only in the free-text category_label — so Best Card
priced a direct booking at the portal rate (~5x overstated).

NULL = the rate applies however you pay (e.g. Atlas, whose travel rate also
covers direct airline and hotel bookings). Values come from the reviewed seeds
on the next load; validate_catalog CR-04 keeps them on bonus rates only.
Decision log: 2026-11-07-best-card-verdicts.md.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reward_categories ADD COLUMN requires_portal TEXT")
    op.execute(
        "ALTER TABLE reward_categories ADD CONSTRAINT chk_requires_portal_not_blank "
        "CHECK (requires_portal IS NULL OR btrim(requires_portal) <> '')"
    )
    op.execute(
        "COMMENT ON COLUMN reward_categories.requires_portal IS "
        "'Booking channel this bonus rate requires (e.g. HDFC SmartBuy); booked direct, "
        "the purchase earns the card base rate. NULL = applies however you pay.'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE reward_categories DROP CONSTRAINT chk_requires_portal_not_blank")
    op.execute("ALTER TABLE reward_categories DROP COLUMN requires_portal")
