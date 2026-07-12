"""Stage 5 — Opportunity Enumeration & Valuation (the priced search space).

Contract: one `RewardOpportunity` per (eligible card × spend-profile
category). Eligibility = the card's reward currency has an active transfer
link to the goal's target program (card → currency → link, D-1); SBI Cashback
therefore produces zero opportunities for a KrisFlyer goal by construction.

Pricing: `effective_miles_per_100inr` answers "if this WHOLE category's
monthly spend is routed to this card, how many target-program miles per ₹100
result?" — blended across the accelerated cap (see transfer_math), then
passed through the transfer ratio. That is the granularity at which Stage 7
allocates (one card per category), so it is the decision-relevant number.

Documented deviation from the blueprint's "amortized fees": folding a flat
INR transfer fee into a miles-per-₹100 rate requires a miles→INR valuation
the MVP catalog cannot ground (no cash-price data). Fees stay explicit on
`transfer_path`; Simulation sums them into `total_fees_inr` and Ranking
scores them in the cost dimension. Nothing is hidden — it is just not
laundered into a rate it can't honestly join.

Pure function of PlanningContext: no DB, no clock, no randomness. Output
order is deterministic (cards sorted by id, categories by profile order).
"""

from uuid import UUID

from app.domain import (
    CapStructure,
    CardAggregates,
    CurrencyTransferLink,
    MilestoneType,
    OpportunitySet,
    PlanningContext,
    RewardCategoryRule,
    RewardOpportunity,
    SpendCategory,
    TransferPath,
)
from app.valuation.transfer_math import blended_earn_rate, miles_per_100


def enumerate_opportunities(context: PlanningContext) -> OpportunitySet:
    snapshot = context.snapshot
    target_program = context.requirement.target_program_id
    wallet_ids = {w.card_id for w in context.wallet}

    link_by_currency: dict[UUID, CurrencyTransferLink] = {
        link.currency_id: link
        for link in snapshot.transfer_links
        if link.partner_id == target_program
    }

    rules_by_card: dict[UUID, dict[SpendCategory, RewardCategoryRule]] = {}
    for category_rule in snapshot.category_rules:
        rules_by_card.setdefault(category_rule.card_id, {})[category_rule.category_slug] = (
            category_rule
        )

    opportunities: list[RewardOpportunity] = []
    aggregates: list[CardAggregates] = []

    for card in sorted(snapshot.cards, key=lambda c: str(c.id)):
        link = link_by_currency.get(card.reward_currency_id)
        if link is None:
            continue  # no path to the target program — not in the search space

        transfer_path = TransferPath(
            currency_id=link.currency_id,
            partner_id=link.partner_id,
            ratio_from=link.ratio_from,
            ratio_to=link.ratio_to,
            min_transfer_points=link.min_transfer_points,
            max_transfer_points=link.max_transfer_points,
            transfer_fee_inr=link.transfer_fee_inr,
            processing_days_min=link.processing_days_min,
            processing_days_max=link.processing_days_max,
        )
        card_rules = rules_by_card.get(card.id, {})

        for item in context.spend_profile.items:
            notes: list[str] = []
            rule = card_rules.get(item.category_slug)
            if rule is None:
                rule = card_rules.get(SpendCategory.DEFAULT)
                if rule is not None and item.category_slug != SpendCategory.DEFAULT:
                    notes.append(
                        f"earns at the card's default rate — no accelerated "
                        f"'{item.category_slug.value}' category"
                    )
            if rule is None:
                continue  # validate_catalog guarantees a default; belt-and-braces

            effective_rate = blended_earn_rate(
                monthly_spend_inr=item.monthly_spend_inr,
                accelerated_rate=rule.earn_rate,
                base_rate=card.base_earn_rate,
                monthly_cap_inr=rule.monthly_cap_inr,
            )
            if effective_rate != rule.earn_rate:
                notes.append(
                    f"monthly cap ₹{rule.monthly_cap_inr:,} applies — blended rate over "
                    f"₹{item.monthly_spend_inr:,}/month of declared spend"
                )
            if link.max_transfer_points is not None:
                notes.append(
                    f"annual transfer cap: max {link.max_transfer_points:,} points/year "
                    "through this link"
                )
            # No per-category note for the link's transfer fee: it is already
            # explicit on `transfer_path` and summed into the simulation's
            # `transfer_fees_inr`, which the UI surfaces exactly once in the
            # transfer step — repeating it on every category row was noise.

            opportunities.append(
                RewardOpportunity(
                    card_id=card.id,
                    in_wallet=card.id in wallet_ids,
                    category_slug=item.category_slug,
                    earn_rate=effective_rate,
                    cap_structure=CapStructure(
                        monthly_cap_inr=rule.monthly_cap_inr,
                        quarterly_cap_inr=rule.quarterly_cap_inr,
                        annual_cap_inr=rule.annual_cap_inr,
                    ),
                    transfer_path=transfer_path,
                    effective_miles_per_100inr=miles_per_100(effective_rate, link),
                    valuation_notes=tuple(notes),
                )
            )

        card_milestones = [m for m in snapshot.milestones if m.card_id == card.id]
        aggregates.append(
            CardAggregates(
                card_id=card.id,
                in_wallet=card.id in wallet_ids,
                acquirable=card.acquirable,
                annual_fee_inr=card.annual_fee_inr,
                joining_fee_inr=card.joining_fee_inr,
                welcome_bonus_points=sum(
                    m.bonus_points
                    for m in card_milestones
                    if m.milestone_type == MilestoneType.WELCOME_BONUS
                ),
                milestone_ids=tuple(m.id for m in card_milestones),
            )
        )

    return OpportunitySet(opportunities=tuple(opportunities), card_aggregates=tuple(aggregates))
