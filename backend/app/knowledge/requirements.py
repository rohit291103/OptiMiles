"""Stage 3 — Reward Requirement Estimation.

The miles target comes from the goal's LOCKED award-chart row — never an LLM,
never a heuristic. The safety buffer is explicit, configurable, and rounds UP
(a buffer that rounds down understates the safety margin).
"""

import math
from decimal import Decimal

from app.domain import CatalogSnapshot, RewardRequirement, TravelGoal


class ChartRowMissing(LookupError):
    """The goal's locked award_chart_id is absent from the snapshot — a data
    integrity failure that must surface loudly, not as a silent zero."""


def estimate_requirement(
    goal: TravelGoal, snapshot: CatalogSnapshot, buffer_pct: float
) -> RewardRequirement:
    chart = next((c for c in snapshot.award_charts if c.id == goal.award_chart_id), None)
    if chart is None:
        raise ChartRowMissing(
            f"award chart row {goal.award_chart_id} (locked by goal {goal.id}) "
            "is not in the catalog snapshot"
        )

    partner = next(p for p in snapshot.partners if p.id == chart.partner_id)
    total = chart.miles_required * goal.num_passengers
    buffer = math.ceil(total * Decimal(str(buffer_pct)) / 100)
    taxes = chart.taxes_fees_inr * goal.num_passengers if chart.taxes_fees_inr else None

    return RewardRequirement(
        goal_id=goal.id,
        target_program_id=partner.id,
        target_program_name=partner.program_name,
        chart_miles_per_passenger=chart.miles_required,
        miles_required_total=total,
        buffer_miles=buffer,
        taxes_fees_inr_estimate=taxes,
        award_type=goal.award_type,
        one_way=True,
        # Snapshots contain only active rows; the locked row was found, so it
        # is current. The stale-chart warning path (locked row deactivated in
        # a NEWER snapshot) is wired in the pipeline phase, which is the first
        # place two snapshot generations can meet.
        stale_chart=False,
    )
