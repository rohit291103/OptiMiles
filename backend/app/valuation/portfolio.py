"""Portfolio View — what the user's own wallet is worth, before they spend.

Roadmap Phase 1 (`docs/prd/product-roadmap-v1.md`): the surface that turns
`/cards` from catalog browsing into "my cards". A pure function of the
catalog snapshot — no DB, no clock, no randomness, no LLM — so the same
wallet always renders the same portfolio.

WHY THIS LIVES IN VALUATION, NOT KNOWLEDGE
------------------------------------------
The reshape of catalog rows into per-card facts is Knowledge-shaped, but the
part that makes this a portfolio rather than a card list is *priced*: every
earn rate and every milestone bonus is converted into miles in a chosen
target program, and comparison between cards happens in that unit. That is
transfer-value estimation, which is the Valuation Engine's job (CLAUDE.md →
Core Backend Systems 2). No sixth engine; `knowledge/education.py` stays the
wizard's narration-shaped read of the same catalog. The two look alike on
purpose — what they share is iteration and DTO shape, never a calculation,
and Valuation may not import Knowledge anyway (module-boundary test).

WHY EVERYTHING IS PRICED IN MILES, NOT POINTS
---------------------------------------------
Identical to Best Card, and for the same reason: HDFC Reward Points, EDGE
Miles and Membership Rewards are different units, and the catalog carries no
₹-per-point valuation to convert them into a common one (inventing one would
mean seeding numbers with no source — forbidden by the seed policy). The one
honest common denominator is the transfer link. So a card that cannot reach
the target program is reported as unreachable (`miles_per_100 = None`), never
as zero and never ranked against cards that can.

FORMULAS (units in brackets)
----------------------------
  miles_per_100 [miles/₹100]  = `miles_per_100(rate, link)` — the category
      rule's rate, or the card's base rate where no rule covers the category
      (the same fallback Best Card applies).

  bonus_miles [miles]         = `marginal_miles(bonus_points, link)`
      floor(points × ratio_to / ratio_from). Marginal, not a whole-block
      transfer: a milestone bonus lands in a balance that gets transferred in
      blocks later, so applying block flooring here would understate it.

  annual_ceiling_miles [miles] = `points_to_miles(max_transfer_points, link)`
      What the link's per-calendar-year points cap is worth in the target
      program — the number that actually bounds a single-card strategy
      (Atlas: 30,000 EDGE Miles/year = 60,000 KrisFlyer miles).

      WHOLE-BLOCK, not marginal, and here the distinction is real: this cap
      bounds an actual transfer, and you cannot send a fraction of a ratio
      block. At 3:2 a 5-point cap clears one block — 2 miles, not the 3 that
      marginal pricing would claim. Both capped links in today's catalog
      happen to cap on an exact multiple of `ratio_from`, so the two agree
      right now; convenient seed data is not a reason to get it wrong.
      `simulation/projector.py` and `optimization/allocation.py` already
      block-floor after applying this same cap — this matches them.

  best_miles_per_1000_points [miles] = the best `marginal_miles(1000, link)`
      across the wallet's links into one partner — a legible "which of my
      cards is the good door into this program".

WHAT IS DELIBERATELY ABSENT (Phase 1)
-------------------------------------
Cap *utilisation* and milestone *progress* need observed spend, which arrives
with Phase 2 spend logging. This module reports the cap and the threshold —
the target, not the progress bar — and the API says so out loud rather than
implying a zero. Annual-fee *dates* need the user's card-open date, which the
catalog does not and should not hold.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain import (
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    LoungeAccess,
    LoungeScope,
    MilestonePeriod,
    MilestoneType,
    PartnerType,
    RewardCategoryRule,
    RewardCurrency,
    RewardMilestone,
    SpendCategory,
    TransferPartner,
)
from app.valuation.transfer_math import marginal_miles, miles_per_100, points_to_miles
from app.valuation.wallet import (
    PartnerReach,
    UnknownCard,
    links_by_currency,
    partner_reach,
    resolve_target,
    resolve_wallet,
)

__all__ = ["UnknownCard", "WalletPortfolio", "build_portfolio"]

_FALLBACK_LABEL = "All other spend"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class PortfolioEarnRule(_Frozen):
    """One category's earn rate on a card, priced into the target program.

    `miles_per_100` is None exactly when the card's currency has no link to
    the target program. Caps are spend-INR ceilings on the accelerated rate;
    how much of one is already used is unknown until Phase 2.
    """

    category_slug: SpendCategory
    category_label: str
    earn_rate: Decimal
    miles_per_100: Decimal | None
    is_accelerated: bool
    monthly_cap_inr: int | None
    quarterly_cap_inr: int | None
    annual_cap_inr: int | None
    notes: str | None


class PortfolioMilestone(_Frozen):
    """A spend threshold and what crossing it is worth in target miles."""

    milestone_type: MilestoneType
    period: MilestonePeriod
    spend_threshold_inr: int | None
    bonus_points: int
    bonus_miles: int | None
    description: str | None


class PortfolioTransferLink(_Frozen):
    """One avenue out of a card's currency, with its real-world limits."""

    partner_id: UUID
    partner_name: str
    program_name: str
    partner_type: PartnerType
    is_target: bool

    ratio_from: int
    ratio_to: int
    miles_per_1000_points: int
    min_transfer_points: int
    max_transfer_points: int | None
    annual_ceiling_miles: int | None
    transfer_fee_inr: int
    processing_days_min: int
    processing_days_max: int
    notes: str | None


class PortfolioLoungeAccess(_Frozen):
    """One lounge entitlement, shaped for display.

    `is_unlimited` exists so a caller never has to interpret a null: on this
    surface None means unlimited and 0 means none, and those are opposite
    answers. A UI that treated the null as "no data" would tell an Infinia
    holder they have no lounge access.
    """

    program_name: str
    scope: LoungeScope
    visits_per_period: int | None
    is_unlimited: bool
    period: str
    reset_anchor: str
    guest_visits_per_period: int | None
    guests_share_allowance: bool
    spend_gate_inr: int | None
    spend_gate_period: str | None
    needs_activation: bool
    enrollment_url: str | None
    conditions: str | None


class PortfolioCard(_Frozen):
    """One wallet card: what it earns, what it unlocks, where it can send."""

    card_id: UUID
    bank: str
    card_name: str
    card_network: str
    currency_id: UUID
    currency_name: str
    currency_expiry_rules: str | None

    annual_fee_inr: int
    joining_fee_inr: int
    base_earn_rate: Decimal
    has_lounge_access: bool
    acquirable: bool

    # Three genuinely different states, never collapsed into two:
    #   "detailed"     — we hold real conditions
    #   "not_detailed" — the card HAS lounge access, we haven't researched it
    #   "none"         — the card has no lounge access
    # Reporting "not researched" as "none" would be a false claim about a
    # benefit the cardholder is paying for.
    lounge_coverage: Literal["detailed", "not_detailed", "none"]
    lounge_access: tuple[PortfolioLoungeAccess, ...]

    reaches_target: bool | None
    earn_rules: tuple[PortfolioEarnRule, ...]
    milestones: tuple[PortfolioMilestone, ...]
    transfer_links: tuple[PortfolioTransferLink, ...]


class CategoryRow(_Frozen):
    """One card's standing in one category — the comparison, per card."""

    card_id: UUID
    card_name: str
    category_label: str
    earn_rate: Decimal
    miles_per_100: Decimal | None
    is_accelerated: bool
    monthly_cap_inr: int | None


class CategoryLeader(_Frozen):
    """Which card to reach for in one category, and the full comparison.

    `leader_card_id` is None when no program has been chosen at all, and also
    when a program is chosen that no wallet card reaches: with nothing to
    compare in, we decline to rank rather than fall back to incommensurable
    points.
    """

    category_slug: SpendCategory
    category_label: str
    leader_card_id: UUID | None
    rows: tuple[CategoryRow, ...]


class WalletPortfolio(_Frozen):
    """The user's wallet, priced against one target program."""

    catalog_snapshot_version: str
    target_program_id: UUID | None
    target_program_name: str | None

    cards: tuple[PortfolioCard, ...]
    categories: tuple[CategoryLeader, ...]
    partner_reach: tuple[PartnerReach, ...]

    # None (not 0) when no program has been chosen — "how many of your cards
    # reach it" is not a question with an answer yet.
    cards_reaching_target: int | None
    # What a UI needs to decide whether to show a coverage caveat.
    lounge_cards_detailed: int
    lounge_cards_undetailed: int
    total_annual_fees_inr: int
    total_joining_fees_inr: int


def build_portfolio(
    snapshot: CatalogSnapshot,
    *,
    card_ids: Sequence[UUID],
    target_program_id: UUID | None = None,
) -> WalletPortfolio:
    """Shape `card_ids` into a portfolio, priced only if a program is chosen.

    Cards keep wallet order (duplicates collapse to first occurrence). Raises
    `ValueError` on an empty wallet or an unknown target program, and
    `UnknownCard` when a card id is not in the snapshot — a stale wallet must
    fail loudly rather than quietly render an incomplete portfolio.
    """
    target_id, target_name = resolve_target(snapshot, target_program_id)
    wallet = resolve_wallet(snapshot, card_ids)

    currencies_by_id = {currency.id: currency for currency in snapshot.currencies}
    partners_by_id = {p.id: p for p in snapshot.partners}
    grouped_links = links_by_currency(snapshot)

    rules_by_card: dict[UUID, list[RewardCategoryRule]] = {}
    for rule in snapshot.category_rules:
        rules_by_card.setdefault(rule.card_id, []).append(rule)

    milestones_by_card: dict[UUID, list[RewardMilestone]] = {}
    for milestone in snapshot.milestones:
        milestones_by_card.setdefault(milestone.card_id, []).append(milestone)

    lounge_by_card: dict[UUID, list[LoungeAccess]] = {}
    for access in snapshot.lounge_access:
        lounge_by_card.setdefault(access.card_id, []).append(access)
    lounge_program_names = {p.id: p.program_name for p in snapshot.lounge_programs}

    target_link_by_card = {
        card.id: (
            next(
                (
                    link
                    for link in grouped_links.get(card.reward_currency_id, ())
                    if link.partner_id == target_id
                ),
                None,
            )
            if target_id is not None
            else None
        )
        for card in wallet
    }

    cards = tuple(
        _portfolio_card(
            card,
            currency=currencies_by_id[card.reward_currency_id],
            rules=rules_by_card.get(card.id, []),
            milestones=milestones_by_card.get(card.id, []),
            lounge=lounge_by_card.get(card.id, []),
            lounge_program_names=lounge_program_names,
            links=grouped_links.get(card.reward_currency_id, []),
            partners_by_id=partners_by_id,
            target_link=target_link_by_card[card.id],
            target_program_id=target_id,
        )
        for card in wallet
    )

    return WalletPortfolio(
        catalog_snapshot_version=snapshot.version,
        target_program_id=target_id,
        target_program_name=target_name,
        cards=cards,
        categories=_categories(wallet, rules_by_card, target_link_by_card),
        partner_reach=partner_reach(snapshot, wallet, target_program_id=target_id),
        cards_reaching_target=(
            sum(1 for card in cards if card.reaches_target) if target_id is not None else None
        ),
        lounge_cards_detailed=sum(1 for c in cards if c.lounge_coverage == "detailed"),
        lounge_cards_undetailed=sum(1 for c in cards if c.lounge_coverage == "not_detailed"),
        total_annual_fees_inr=sum(card.annual_fee_inr for card in wallet),
        total_joining_fees_inr=sum(card.joining_fee_inr for card in wallet),
    )


def _portfolio_card(
    card: Card,
    *,
    currency: RewardCurrency,
    rules: list[RewardCategoryRule],
    milestones: list[RewardMilestone],
    lounge: list[LoungeAccess],
    lounge_program_names: dict[UUID, str],
    links: list[CurrencyTransferLink],
    partners_by_id: dict[UUID, TransferPartner],
    target_link: CurrencyTransferLink | None,
    target_program_id: UUID | None,
) -> PortfolioCard:
    earn_rules = tuple(
        PortfolioEarnRule(
            category_slug=rule.category_slug,
            category_label=rule.category_label,
            earn_rate=rule.earn_rate,
            miles_per_100=(miles_per_100(rule.earn_rate, target_link) if target_link else None),
            is_accelerated=rule.earn_rate > card.base_earn_rate,
            monthly_cap_inr=rule.monthly_cap_inr,
            quarterly_cap_inr=rule.quarterly_cap_inr,
            annual_cap_inr=rule.annual_cap_inr,
            notes=rule.notes,
        )
        # Default first (it is the rate that applies to most spend), then the
        # accelerated ones strongest-first; slug breaks any remaining tie so
        # the order never depends on snapshot iteration.
        for rule in sorted(
            rules,
            key=lambda r: (
                r.category_slug != SpendCategory.DEFAULT,
                -r.earn_rate,
                r.category_slug,
            ),
        )
    )

    card_milestones = tuple(
        PortfolioMilestone(
            milestone_type=milestone.milestone_type,
            period=milestone.period,
            spend_threshold_inr=milestone.spend_threshold_inr,
            bonus_points=milestone.bonus_points,
            bonus_miles=(
                marginal_miles(milestone.bonus_points, target_link) if target_link else None
            ),
            description=milestone.description,
        )
        # Threshold-free bonuses (welcome, anniversary) first — they are what
        # a holder can act on today — then by ascending spend threshold.
        for milestone in sorted(
            milestones,
            key=lambda m: (
                m.spend_threshold_inr is not None,
                m.spend_threshold_inr or 0,
                -m.bonus_points,
                m.description or "",
            ),
        )
    )

    transfer_links = tuple(
        PortfolioTransferLink(
            partner_id=link.partner_id,
            partner_name=partners_by_id[link.partner_id].partner_name,
            program_name=partners_by_id[link.partner_id].program_name,
            partner_type=partners_by_id[link.partner_id].partner_type,
            is_target=link.partner_id == target_program_id,
            ratio_from=link.ratio_from,
            ratio_to=link.ratio_to,
            miles_per_1000_points=marginal_miles(1000, link),
            min_transfer_points=link.min_transfer_points,
            max_transfer_points=link.max_transfer_points,
            annual_ceiling_miles=(
                points_to_miles(link.max_transfer_points, link)
                if link.max_transfer_points is not None
                else None
            ),
            transfer_fee_inr=link.transfer_fee_inr,
            processing_days_min=link.processing_days_min,
            processing_days_max=link.processing_days_max,
            notes=link.notes,
        )
        # The target program leads — it is the one the user's goal needs —
        # and the rest are alphabetical so the list is scannable.
        for link in sorted(
            links,
            key=lambda link: (
                link.partner_id != target_program_id,
                partners_by_id[link.partner_id].program_name,
            ),
        )
    )

    lounge_access = tuple(
        PortfolioLoungeAccess(
            program_name=lounge_program_names[access.program_id],
            scope=access.scope,
            visits_per_period=access.visits_per_period,
            is_unlimited=access.visits_per_period is None,
            period=access.period.value,
            reset_anchor=access.reset_anchor.value,
            guest_visits_per_period=access.guest_visits_per_period,
            guests_share_allowance=access.guests_share_allowance,
            spend_gate_inr=access.spend_gate_inr,
            spend_gate_period=(
                access.spend_gate_period.value if access.spend_gate_period else None
            ),
            needs_activation=access.enrollment_required,
            enrollment_url=access.enrollment_url,
            conditions=access.conditions,
        )
        # Domestic first — the common case for an Indian cardholder — then by
        # spend gate so a tier ladder reads cheapest-first. Fixed order keeps
        # the render deterministic.
        for access in sorted(
            lounge,
            key=lambda a: (
                a.scope is not LoungeScope.DOMESTIC,
                a.spend_gate_inr or 0,
                lounge_program_names[a.program_id],
            ),
        )
    )

    return PortfolioCard(
        card_id=card.id,
        bank=card.bank,
        card_name=card.card_name,
        card_network=card.card_network,
        currency_id=currency.id,
        currency_name=currency.currency_name,
        currency_expiry_rules=currency.expiry_rules,
        annual_fee_inr=card.annual_fee_inr,
        joining_fee_inr=card.joining_fee_inr,
        base_earn_rate=card.base_earn_rate,
        has_lounge_access=card.has_lounge_access,
        lounge_coverage=(
            "detailed" if lounge_access else "not_detailed" if card.has_lounge_access else "none"
        ),
        lounge_access=lounge_access,
        acquirable=card.acquirable,
        # None, not False: with no program chosen, "does this card reach it"
        # has no answer — and False would read as "no route", which is a
        # claim we have not been asked to make.
        reaches_target=(target_link is not None) if target_program_id is not None else None,
        earn_rules=earn_rules,
        milestones=card_milestones,
        transfer_links=transfer_links,
    )


def _categories(
    wallet: Sequence[Card],
    rules_by_card: dict[UUID, list[RewardCategoryRule]],
    target_link_by_card: dict[UUID, CurrencyTransferLink | None],
) -> tuple[CategoryLeader, ...]:
    """Every category any wallet card accelerates, compared across the wallet.

    Cards without a rule for a category still appear, at their base rate —
    the same fallback Best Card applies. Dropping them would hide the real
    comparison ("is my travel card actually better here?").
    """
    slugs = {rule.category_slug for card in wallet for rule in rules_by_card.get(card.id, [])}
    slugs.add(SpendCategory.DEFAULT)

    leaders: list[CategoryLeader] = []
    for slug in sorted(slugs, key=lambda s: (s != SpendCategory.DEFAULT, s)):
        rows: list[CategoryRow] = []
        labelled: list[CategoryRow] = []
        for card in wallet:
            rule = next(
                (r for r in rules_by_card.get(card.id, []) if r.category_slug == slug), None
            )
            rate = rule.earn_rate if rule else card.base_earn_rate
            link = target_link_by_card[card.id]
            row = CategoryRow(
                card_id=card.id,
                card_name=card.card_name,
                category_label=rule.category_label if rule else _FALLBACK_LABEL,
                earn_rate=rate,
                miles_per_100=miles_per_100(rate, link) if link else None,
                is_accelerated=rule is not None and rule.earn_rate > card.base_earn_rate,
                monthly_cap_inr=rule.monthly_cap_inr if rule else None,
            )
            rows.append(row)
            if rule is not None:
                labelled.append(row)
        # Miles decide; card name breaks ties so the leader never depends on
        # wallet ordering. Cards with no route are not candidates at all.
        routed = [row for row in rows if row.miles_per_100 is not None]
        leader = (
            min(routed, key=lambda row: (-(row.miles_per_100 or Decimal(0)), row.card_name))
            if routed
            else None
        )
        # The category's name comes from a card that actually HAS a rule for
        # it — accelerated first, then by rate, then by card name. "The first
        # accelerated row" made the label depend on the order the caller
        # happened to list their cards in: same wallet, different label. A
        # card with no rule cannot name a category it does not have.
        by_claim = sorted(
            labelled, key=lambda row: (not row.is_accelerated, -row.earn_rate, row.card_name)
        )
        label = by_claim[0].category_label if by_claim else _FALLBACK_LABEL
        leaders.append(
            CategoryLeader(
                category_slug=slug,
                category_label=label,
                leader_card_id=leader.card_id if leader else None,
                rows=tuple(rows),
            )
        )
    return tuple(leaders)
