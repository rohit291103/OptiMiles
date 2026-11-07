"""Admin-side catalog sync: seed snapshot → DB. Idempotent — deterministic
seed IDs make upserts stable, and rows absent from the seeds are deactivated
(never deleted: user_goals may lock historical award-chart rows).

Provenance (source / verified_on / needs_verification) intentionally stays in
the reviewed YAML, not the DB — the seeds are the audited artifact.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.domain import CatalogSnapshot

_UPSERTS: dict[str, str] = {
    "reward_currencies": """
        INSERT INTO reward_currencies (id, currency_name, issuer, expiry_rules, is_active)
        VALUES (:id, :currency_name, :issuer, :expiry_rules, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          currency_name = EXCLUDED.currency_name,
          issuer = EXCLUDED.issuer,
          expiry_rules = EXCLUDED.expiry_rules,
          is_active = TRUE
    """,
    "transfer_partners": """
        INSERT INTO transfer_partners
          (id, partner_name, program_name, partner_type, iata_code, alliance, is_active)
        VALUES (:id, :partner_name, :program_name, :partner_type, :iata_code, :alliance, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          partner_name = EXCLUDED.partner_name,
          program_name = EXCLUDED.program_name,
          partner_type = EXCLUDED.partner_type,
          iata_code = EXCLUDED.iata_code,
          alliance = EXCLUDED.alliance,
          is_active = TRUE
    """,
    "cards": """
        INSERT INTO cards
          (id, bank, card_name, card_network, reward_currency_id, annual_fee_inr,
           joining_fee_inr, base_earn_rate, min_income_inr, has_lounge_access,
           acquirable, is_active, updated_at)
        VALUES
          (:id, :bank, :card_name, :card_network, :reward_currency_id, :annual_fee_inr,
           :joining_fee_inr, :base_earn_rate, :min_income_inr, :has_lounge_access,
           :acquirable, TRUE, NOW())
        ON CONFLICT (id) DO UPDATE SET
          bank = EXCLUDED.bank,
          card_name = EXCLUDED.card_name,
          card_network = EXCLUDED.card_network,
          reward_currency_id = EXCLUDED.reward_currency_id,
          annual_fee_inr = EXCLUDED.annual_fee_inr,
          joining_fee_inr = EXCLUDED.joining_fee_inr,
          base_earn_rate = EXCLUDED.base_earn_rate,
          min_income_inr = EXCLUDED.min_income_inr,
          has_lounge_access = EXCLUDED.has_lounge_access,
          acquirable = EXCLUDED.acquirable,
          is_active = TRUE,
          updated_at = NOW()
    """,
    "reward_categories": """
        INSERT INTO reward_categories
          (id, card_id, category_slug, category_label, earn_rate, monthly_cap_inr,
           quarterly_cap_inr, annual_cap_inr, over_cap_earn, requires_portal, notes,
           is_active)
        VALUES
          (:id, :card_id, :category_slug, :category_label, :earn_rate, :monthly_cap_inr,
           :quarterly_cap_inr, :annual_cap_inr, :over_cap_earn, :requires_portal, :notes,
           TRUE)
        ON CONFLICT (id) DO UPDATE SET
          category_slug = EXCLUDED.category_slug,
          category_label = EXCLUDED.category_label,
          earn_rate = EXCLUDED.earn_rate,
          monthly_cap_inr = EXCLUDED.monthly_cap_inr,
          quarterly_cap_inr = EXCLUDED.quarterly_cap_inr,
          annual_cap_inr = EXCLUDED.annual_cap_inr,
          over_cap_earn = EXCLUDED.over_cap_earn,
          requires_portal = EXCLUDED.requires_portal,
          notes = EXCLUDED.notes,
          is_active = TRUE
    """,
    "currency_transfer_partners": """
        INSERT INTO currency_transfer_partners
          (id, currency_id, partner_id, ratio_from, ratio_to, min_transfer_points,
           max_transfer_points, transfer_fee_inr, processing_days_min,
           processing_days_max, notes, is_active)
        VALUES
          (:id, :currency_id, :partner_id, :ratio_from, :ratio_to, :min_transfer_points,
           :max_transfer_points, :transfer_fee_inr, :processing_days_min,
           :processing_days_max, :notes, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          ratio_from = EXCLUDED.ratio_from,
          ratio_to = EXCLUDED.ratio_to,
          min_transfer_points = EXCLUDED.min_transfer_points,
          max_transfer_points = EXCLUDED.max_transfer_points,
          transfer_fee_inr = EXCLUDED.transfer_fee_inr,
          processing_days_min = EXCLUDED.processing_days_min,
          processing_days_max = EXCLUDED.processing_days_max,
          notes = EXCLUDED.notes,
          is_active = TRUE
    """,
    "reward_milestones": """
        INSERT INTO reward_milestones
          (id, card_id, milestone_type, spend_threshold_inr, bonus_points, period,
           description, valid_from, valid_until, is_active)
        VALUES
          (:id, :card_id, :milestone_type, :spend_threshold_inr, :bonus_points, :period,
           :description, :valid_from, :valid_until, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          milestone_type = EXCLUDED.milestone_type,
          spend_threshold_inr = EXCLUDED.spend_threshold_inr,
          bonus_points = EXCLUDED.bonus_points,
          period = EXCLUDED.period,
          description = EXCLUDED.description,
          valid_from = EXCLUDED.valid_from,
          valid_until = EXCLUDED.valid_until,
          is_active = TRUE
    """,
    "award_charts": """
        INSERT INTO award_charts
          (id, partner_id, origin_region, destination_region, cabin_class, award_type,
           miles_required, taxes_fees_inr, notes, effective_date, is_active)
        VALUES
          (:id, :partner_id, :origin_region, :destination_region, :cabin_class,
           :award_type, :miles_required, :taxes_fees_inr, :notes, :effective_date, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          miles_required = EXCLUDED.miles_required,
          taxes_fees_inr = EXCLUDED.taxes_fees_inr,
          notes = EXCLUDED.notes,
          effective_date = EXCLUDED.effective_date,
          is_active = TRUE
    """,
    "lounge_programs": """
        INSERT INTO lounge_programs (id, program_name, operator, notes, is_active)
        VALUES (:id, :program_name, :operator, :notes, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          program_name = EXCLUDED.program_name,
          operator = EXCLUDED.operator,
          notes = EXCLUDED.notes,
          is_active = TRUE
    """,
    "card_lounge_access": """
        INSERT INTO card_lounge_access
          (id, card_id, program_id, scope, visits_per_period, period, reset_anchor,
           guest_visits_per_period, guests_share_allowance, spend_gate_inr,
           spend_gate_period, enrollment_required, enrollment_url, conditions, is_active)
        VALUES
          (:id, :card_id, :program_id, :scope, :visits_per_period, :period, :reset_anchor,
           :guest_visits_per_period, :guests_share_allowance, :spend_gate_inr,
           :spend_gate_period, :enrollment_required, :enrollment_url, :conditions, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          card_id = EXCLUDED.card_id,
          program_id = EXCLUDED.program_id,
          scope = EXCLUDED.scope,
          visits_per_period = EXCLUDED.visits_per_period,
          period = EXCLUDED.period,
          reset_anchor = EXCLUDED.reset_anchor,
          guest_visits_per_period = EXCLUDED.guest_visits_per_period,
          guests_share_allowance = EXCLUDED.guests_share_allowance,
          spend_gate_inr = EXCLUDED.spend_gate_inr,
          spend_gate_period = EXCLUDED.spend_gate_period,
          enrollment_required = EXCLUDED.enrollment_required,
          enrollment_url = EXCLUDED.enrollment_url,
          conditions = EXCLUDED.conditions,
          is_active = TRUE
    """,
    # Migration 0010. Ordered after `cards` (FK). Upserted by id, and the
    # deactivate-absent sweep below retires a card's waiver whose block is
    # removed from the seeds — turning it back into "not covered", never NONE.
    "card_fee_waivers": """
        INSERT INTO card_fee_waivers
          (id, card_id, kind, threshold_inr, threshold_comparison, window_kind,
           waives_renewal_fee, waives_joining_fee, excluded_categories,
           unmodelled_exclusions, conditions, is_active)
        VALUES
          (:id, :card_id, :kind, :threshold_inr, :threshold_comparison, :window_kind,
           :waives_renewal_fee, :waives_joining_fee, :excluded_categories,
           :unmodelled_exclusions, :conditions, TRUE)
        ON CONFLICT (id) DO UPDATE SET
          card_id = EXCLUDED.card_id,
          kind = EXCLUDED.kind,
          threshold_inr = EXCLUDED.threshold_inr,
          threshold_comparison = EXCLUDED.threshold_comparison,
          window_kind = EXCLUDED.window_kind,
          waives_renewal_fee = EXCLUDED.waives_renewal_fee,
          waives_joining_fee = EXCLUDED.waives_joining_fee,
          excluded_categories = EXCLUDED.excluded_categories,
          unmodelled_exclusions = EXCLUDED.unmodelled_exclusions,
          conditions = EXCLUDED.conditions,
          is_active = TRUE
    """,
}


def _rows(snapshot: CatalogSnapshot) -> dict[str, list[dict[str, Any]]]:
    return {
        "reward_currencies": [c.model_dump() for c in snapshot.currencies],
        "transfer_partners": [p.model_dump() for p in snapshot.partners],
        "cards": [c.model_dump() for c in snapshot.cards],
        "reward_categories": [
            {
                **r.model_dump(),
                "category_slug": r.category_slug.value,
                "over_cap_earn": r.over_cap_earn.value if r.over_cap_earn else None,
            }
            for r in snapshot.category_rules
        ],
        "currency_transfer_partners": [li.model_dump() for li in snapshot.transfer_links],
        "reward_milestones": [
            {
                **m.model_dump(),
                "milestone_type": m.milestone_type.value,
                "period": m.period.value,
            }
            for m in snapshot.milestones
        ],
        "award_charts": [
            {
                **c.model_dump(),
                "cabin_class": c.cabin_class.value,
                "award_type": c.award_type.value,
            }
            for c in snapshot.award_charts
        ],
        "lounge_programs": [p.model_dump() for p in snapshot.lounge_programs],
        "card_lounge_access": [
            {
                **a.model_dump(),
                "scope": a.scope.value,
                "period": a.period.value,
                "reset_anchor": a.reset_anchor.value,
                "spend_gate_period": (
                    a.spend_gate_period.value if a.spend_gate_period else None
                ),
            }
            for a in snapshot.lounge_access
        ],
        "card_fee_waivers": [
            {
                # The computed flag is derived, not a column.
                **w.model_dump(exclude={"has_unmodelled_exclusions"}),
                "kind": w.kind.value,
                "threshold_comparison": (
                    w.threshold_comparison.value if w.threshold_comparison else None
                ),
                "window_kind": w.window_kind.value if w.window_kind else None,
                "excluded_categories": [c.value for c in w.excluded_categories],
                "unmodelled_exclusions": list(w.unmodelled_exclusions),
            }
            for w in snapshot.fee_waivers
        ],
    }


async def sync_catalog(conn: AsyncConnection, snapshot: CatalogSnapshot) -> dict[str, int]:
    """Upsert every snapshot row; deactivate rows the seeds no longer contain.
    Returns row counts per table."""
    counts: dict[str, int] = {}
    all_rows = _rows(snapshot)

    for table, statement in _UPSERTS.items():
        rows = all_rows[table]
        for row in rows:
            await conn.execute(text(statement), row)
        seeded_ids = [row["id"] for row in rows]
        await conn.execute(
            text(f"UPDATE {table} SET is_active = FALSE WHERE NOT (id = ANY(:ids))"),
            {"ids": seeded_ids},
        )
        counts[table] = len(rows)
    return counts
