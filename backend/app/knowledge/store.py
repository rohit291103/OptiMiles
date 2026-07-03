"""Knowledge Engine DB read path — the SOLE reader of catalog tables
(build rule 3 / blueprint §3.1). Loads active rows into an immutable
CatalogSnapshot; the version is the same content hash the seed loader uses,
so a DB load of identical data reports an identical version.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.domain import (
    AwardChartEntry,
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    RewardCategoryRule,
    RewardCurrency,
    RewardMilestone,
    TransferPartner,
)
from app.knowledge.versioning import content_version


async def load_snapshot(conn: AsyncConnection) -> CatalogSnapshot:
    async def rows(query: str) -> list[dict[str, Any]]:
        result = await conn.execute(text(query))
        return [dict(row) for row in result.mappings()]

    currencies = tuple(
        RewardCurrency.model_validate(r)
        for r in await rows(
            "SELECT id, currency_name, issuer, expiry_rules"
            " FROM reward_currencies WHERE is_active ORDER BY id"
        )
    )
    partners = tuple(
        TransferPartner.model_validate(r)
        for r in await rows(
            "SELECT id, partner_name, program_name, partner_type, iata_code, alliance"
            " FROM transfer_partners WHERE is_active ORDER BY id"
        )
    )
    transfer_links = tuple(
        CurrencyTransferLink.model_validate(r)
        for r in await rows(
            "SELECT id, currency_id, partner_id, ratio_from, ratio_to,"
            " min_transfer_points, max_transfer_points, transfer_fee_inr,"
            " processing_days_min, processing_days_max, notes"
            " FROM currency_transfer_partners WHERE is_active ORDER BY id"
        )
    )
    cards = tuple(
        Card.model_validate(r)
        for r in await rows(
            "SELECT id, bank, card_name, card_network, reward_currency_id,"
            " annual_fee_inr, joining_fee_inr, base_earn_rate, min_income_inr,"
            " has_lounge_access"
            " FROM cards WHERE is_active ORDER BY id"
        )
    )
    category_rules = tuple(
        RewardCategoryRule.model_validate(r)
        for r in await rows(
            "SELECT id, card_id, category_slug, category_label, earn_rate,"
            " monthly_cap_inr, quarterly_cap_inr, annual_cap_inr, notes"
            " FROM reward_categories WHERE is_active ORDER BY id"
        )
    )
    milestones = tuple(
        RewardMilestone.model_validate(r)
        for r in await rows(
            "SELECT id, card_id, milestone_type, spend_threshold_inr, bonus_points,"
            " period, description, valid_from, valid_until"
            " FROM reward_milestones WHERE is_active ORDER BY id"
        )
    )
    award_charts = tuple(
        AwardChartEntry.model_validate(r)
        for r in await rows(
            "SELECT id, partner_id, origin_region, destination_region, cabin_class,"
            " award_type, miles_required, taxes_fees_inr, notes, effective_date"
            " FROM award_charts WHERE is_active ORDER BY id"
        )
    )

    return CatalogSnapshot(
        version=content_version(
            [currencies, partners, transfer_links, cards, category_rules, milestones, award_charts]
        ),
        currencies=currencies,
        partners=partners,
        transfer_links=transfer_links,
        cards=cards,
        category_rules=category_rules,
        milestones=milestones,
        award_charts=award_charts,
    )
