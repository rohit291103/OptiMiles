"""Best Card for this Spend — which card to swipe for one purchase.

Roadmap Phase 1 (`docs/prd/product-roadmap-v1.md`): the daily-surface hook.
A pure function of the catalog snapshot — no DB, no clock, no randomness, no
LLM — so the same wallet and amount always produce the same ranking.

TWO MODES, AND THE DEFAULT IS THE MODEST ONE
--------------------------------------------
Raw points are not comparable across cards. HDFC Reward Points, Axis EDGE
Miles and Amex MR are different units, and the catalog carries no ₹-per-point
valuation to convert them into a common one (inventing one would mean seeding
numbers with no source — forbidden by the seed policy). The one honest common
denominator we DO have is the transfer link: miles in a chosen target program.

That is a reason to ASK, not a licence to assume. So:

- `target_program_id=None` (the default) → `ranking_basis="points"`. Every
  card is reported with the points it earns, in its own currency, and no
  miles at all. The order is by points, but it is NOT a ranking and callers
  must not crown a winner on it — across currencies there is no honest
  winner. `partner_reach` says which programs this wallet could reach, so
  the caller can offer the choice.
- `target_program_id=<chosen>` → `ranking_basis="miles"`. Now there is a
  common unit, so there is a real answer: options ranked by miles into that
  program, and cards with no route reported separately.

This replaces an earlier design that defaulted to KrisFlyer because the
(retired) MVP scope named it primary — the UI then printed that program name
to users who had never mentioned it. See `CLAUDE.md` → *Never Assume the
User's Goal* and decision log
`2026-08-26-scope-broadening-and-partner-choice.md`.

FORMULAS (units in brackets)
----------------------------
  effective_earn_rate [pts/₹100]
      = the category rule's rate when the amount fits under its monthly cap,
        else `blended_earn_rate(...)` — the cap-aware blend down to base.
        Falls back to the card's base rate when no rule covers the category.

  points_earned [pts]
      = floor(amount_inr / 100 × effective_earn_rate)

  miles_earned [miles]
      = floor(points_earned × ratio_to / ratio_from)

Rounding is floor throughout, matching the house rule in `transfer_math`:
never overstate what the user will earn.

MARGINAL, NOT A TRANSFER. `miles_earned` deliberately does NOT apply
`points_to_miles`'s whole-block flooring or the link's min/max transfer
limits. Those model an actual transfer event; nobody transfers per
transaction. Applying them here would understate a single purchase badly
(150 HDFC-Regalia RP would floor to 33 miles instead of the marginal 49).
The number reported is the marginal contribution of this spend to a balance
that gets transferred in blocks later.

CAP CAVEAT (Phase 1). Caps in the catalog are MONTHLY spend caps, and until
spend logging lands (Phase 2) we do not know how much of a cap is already
consumed. This function therefore assumes the cap is untouched and reports
`monthly_cap_inr` + `cap_exceeded` so the caller can say so out loud. It is
an assumption made visible, not a hidden one.
"""

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain import (
    CatalogSnapshot,
    CurrencyTransferLink,
    RewardCategoryRule,
    SpendCategory,
)
from app.valuation.transfer_math import blended_earn_rate, marginal_miles, miles_per_100
from app.valuation.wallet import (
    PartnerReach,
    UnknownCard,
    partner_reach,
    resolve_target,
    resolve_wallet,
)

_ONE = Decimal("1")

__all__ = [
    "BestCardResult",
    "CardSpendOption",
    "UnknownCard",
    "rank_cards_for_spend",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class CardSpendOption(_Frozen):
    """One card priced for this purchase.

    `miles_earned` / `miles_per_100` are None exactly when the card's reward
    currency has no transfer link to the target program.
    """

    card_id: UUID
    bank: str
    card_name: str
    currency_name: str

    category_label: str
    is_accelerated: bool
    effective_earn_rate: Decimal
    monthly_cap_inr: int | None
    cap_exceeded: bool

    points_earned: int
    miles_earned: int | None
    miles_per_100: Decimal | None


class BestCardResult(_Frozen):
    """The wallet priced for one purchase.

    `ranking_basis` tells the caller how much the order means: "miles" is a
    real ranking in a unit the user chose; "points" is a listing across
    incomparable currencies and must not be presented as a winner.
    """

    catalog_snapshot_version: str
    amount_inr: int
    category: SpendCategory
    ranking_basis: Literal["miles", "points"]
    target_program_id: UUID | None
    target_program_name: str | None

    ranked: tuple[CardSpendOption, ...]
    unroutable: tuple[CardSpendOption, ...]
    partner_reach: tuple[PartnerReach, ...]


def rank_cards_for_spend(
    snapshot: CatalogSnapshot,
    *,
    amount_inr: int,
    category: SpendCategory,
    card_ids: Sequence[UUID],
    target_program_id: UUID | None = None,
) -> BestCardResult:
    """Price `card_ids` for spending `amount_inr` in `category`.

    With no `target_program_id` the answer is points-only — see the two-modes
    note above. Raises `ValueError` on a non-positive amount, an empty wallet,
    or an unknown target program; `UnknownCard` when a card id is not in the
    snapshot (a stale wallet must fail loudly, not silently drop a card).
    """
    if amount_inr <= 0:
        raise ValueError(f"amount_inr must be positive, got {amount_inr}")

    target_id, target_name = resolve_target(snapshot, target_program_id)
    wallet = resolve_wallet(snapshot, card_ids)

    currencies_by_id = {currency.id: currency for currency in snapshot.currencies}
    link_by_currency: dict[UUID, CurrencyTransferLink] = (
        {link.currency_id: link for link in snapshot.transfer_links if link.partner_id == target_id}
        if target_id is not None
        else {}
    )
    rule_by_card: dict[UUID, RewardCategoryRule] = {
        rule.card_id: rule for rule in snapshot.category_rules if rule.category_slug == category
    }

    ranked: list[CardSpendOption] = []
    unroutable: list[CardSpendOption] = []

    for card in wallet:
        card_id = card.id
        rule = rule_by_card.get(card_id)
        rate, cap, cap_exceeded = _effective_rate(card.base_earn_rate, rule, amount_inr)
        points = _points_for(amount_inr, rate)

        link = link_by_currency.get(card.reward_currency_id)
        option = CardSpendOption(
            card_id=card.id,
            bank=card.bank,
            card_name=card.card_name,
            currency_name=currencies_by_id[card.reward_currency_id].currency_name,
            category_label=rule.category_label if rule else "All other spend",
            is_accelerated=rule is not None and rule.earn_rate > card.base_earn_rate,
            effective_earn_rate=rate,
            monthly_cap_inr=cap,
            cap_exceeded=cap_exceeded,
            points_earned=points,
            miles_earned=marginal_miles(points, link) if link else None,
            miles_per_100=miles_per_100(rate, link) if link else None,
        )
        # With no program chosen nothing is "unroutable" — there is no route
        # being asked about, so every card belongs in the one list.
        if target_id is None or link:
            ranked.append(option)
        else:
            unroutable.append(option)

    # Miles decide when there is a chosen unit; otherwise points order the
    # listing. Card name breaks ties either way, so the order never depends
    # on input ordering or dict iteration (determinism is a standing test).
    ranked.sort(
        key=lambda o: (
            (-(o.miles_earned or 0), o.card_name)
            if target_id is not None
            else (-o.points_earned, o.card_name)
        )
    )
    unroutable.sort(key=lambda o: (-o.points_earned, o.card_name))

    return BestCardResult(
        catalog_snapshot_version=snapshot.version,
        amount_inr=amount_inr,
        category=category,
        ranking_basis="miles" if target_id is not None else "points",
        target_program_id=target_id,
        target_program_name=target_name,
        ranked=tuple(ranked),
        unroutable=tuple(unroutable),
        partner_reach=partner_reach(snapshot, wallet, target_program_id=target_id),
    )


def _effective_rate(
    base_rate: Decimal, rule: RewardCategoryRule | None, amount_inr: int
) -> tuple[Decimal, int | None, bool]:
    """(rate applied, the accelerated rate's monthly cap, whether it blew it)."""
    if rule is None:
        return base_rate, None, False

    cap = rule.monthly_cap_inr
    if cap is None or amount_inr <= cap:
        return rule.earn_rate, cap, False

    # One purchase larger than the whole monthly cap: the excess earns base.
    blended = blended_earn_rate(amount_inr, rule.earn_rate, base_rate, cap)
    return blended, cap, True


def _points_for(amount_inr: int, rate_per_100: Decimal) -> int:
    exact = Decimal(amount_inr) / Decimal(100) * rate_per_100
    return int(exact.quantize(_ONE, rounding=ROUND_DOWN))
