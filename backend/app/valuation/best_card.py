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
        else `blended_earn_rate(...)` — the cap-aware blend, with the excess
        earning what the rule's `over_cap_earn` states (the base rate, or
        nothing — SBI Cashback pays 0 past its ₹2,000-cashback cap).
        Falls back to the card's base rate when no rule covers the category.

  points_earned [pts]
      = floor(transfer_math.category_points_exact(amount_inr, rule, base))
        (floor(amount_inr / 100 × base) with no rule) — ONE floor of the
        exact cap split. `effective_earn_rate` is for display only: past a
        cap it is a 4dp ROUND_DOWN blend, and re-multiplying it would round
        twice.

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

HOW YOU PAY (decision log 2026-11-07-best-card-verdicts.md). Some bonus
rates apply only when booked through the issuer's own portal
(`RewardCategoryRule.requires_portal`: HDFC SmartBuy, Axis Travel EDGE).
Every option is priced both ways: `points_earned` through the portal (the
best case, and the ranking basis), `direct_points_earned` booked directly —
where the gated rule does not apply and the card earns its base rate.

  direct_points_earned [pts] = floor(amount_inr / 100 × base_earn_rate)
      when the rule is portal-gated; otherwise = points_earned

EVERY PROGRAM AT ONCE. `program_verdicts` answers the question for each
program the wallet reaches, in THAT program's own unit — so nothing is ever
compared across currencies and no ₹-per-point value is invented, yet the
user gets an answer without first having to choose. Per program:

  winner     = the card with the most partner units (miles / hotel points);
               None when nobody earns anything there (an issuer exclusion)
  lead       = winner − runner-up, in partner units; `tied` when 0 — a
               card-name tiebreak is not advice
  direct_winner = the best card if the user books DIRECT, set only when the
               winner's rate needs a portal

CARD-FIRST (2026-11-07, user feedback "too vague"). The user's question is
"which card do I swipe", so every option also carries its `destinations`
(each program it can transfer to, and what this spend becomes there, via
portal and booked direct) and `best_for` (the programs where it is the top
card, ties included). With no program chosen the wallet is ORDERED — never
ranked by raw points across currencies — by:

  1. programs won (len(best_for)), most first
  2. best placing in any program (0 = first somewhere)
  3. card name, then id
  Cards that transfer nowhere (SBI Cashback) come last.

`overall_pick` = the card that is the sole top card in EVERY program where
anyone earns — the one honest single answer. None when winners differ or tie.

PROVENANCE. With `unverified_ids` supplied, every option and pick carries
`needs_verification` (its rule — or the card's base rate — or its transfer
link / currency is still flagged in the seeds). None = not assessed, which
must never be read as verified.

CAP CAVEAT (Phase 1). Caps in the catalog are MONTHLY spend caps, and until
spend logging lands (Phase 2) we do not know how much of a cap is already
consumed. This function therefore assumes the cap is untouched and reports
`monthly_cap_inr` + `cap_exceeded` so the caller can say so out loud. It is
an assumption made visible, not a hidden one.
"""

from collections.abc import Sequence, Set
from decimal import ROUND_DOWN, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain import (
    Card,
    CatalogSnapshot,
    CurrencyTransferLink,
    OverCapEarn,
    RewardCategoryRule,
    SpendCategory,
)
from app.domain.enums import PartnerType
from app.valuation.transfer_math import (
    blended_earn_rate,
    category_points_exact,
    marginal_miles,
    miles_per_100,
)
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
    "CardDestination",
    "CardSpendOption",
    "ProgramVerdict",
    "UnknownCard",
    "VerdictPick",
    "rank_cards_for_spend",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class CardDestination(_Frozen):
    """One program this card can send its points to, and what this spend
    becomes there — in THAT program's unit, via portal and booked direct."""

    program_id: UUID
    program_name: str
    partner_name: str
    partner_type: PartnerType
    partner_units: int
    direct_partner_units: int
    ratio_from: int
    ratio_to: int
    needs_verification: bool | None
    """Provenance of the converted figure: rate (or base) + link, currency,
    partner. None = not assessed."""


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
    over_cap_earn: OverCapEarn | None
    """What spend above `monthly_cap_inr` earns (base_rate | nothing); None
    when the rate has no cap. Lets the UI say it instead of assuming base."""

    points_earned: int
    miles_earned: int | None
    miles_per_100: Decimal | None

    requires_portal: str | None
    """The portal this rate needs (e.g. 'HDFC SmartBuy'); None = however you pay."""
    direct_points_earned: int
    direct_miles_earned: int | None
    """What the same spend earns booked DIRECT. Equal to the portal figures
    when `requires_portal` is None."""
    transfer_ratio_from: int | None
    transfer_ratio_to: int | None
    """The target link's ratio, for showing the working; None without a route."""
    needs_verification: bool | None
    """True when a row the PORTAL figure rests on is still flagged: the rule,
    the card row whenever the base rate takes part (no rule, or overflow past
    a cap at base), and the target link / currency / partner. None when no
    provenance was supplied."""
    direct_needs_verification: bool | None
    """The same, for the DIRECT figure — which rests on the card row (base
    rate) instead of a portal-gated rule."""
    destinations: tuple[CardDestination, ...] = ()
    """Every program this card reaches, by program name."""
    best_for: tuple[UUID, ...] = ()
    """Programs where this card is the top card (ties included)."""
    order_position: int | None = None
    """1-based place in the no-program order; equal standing shares a
    number. None when a program is chosen (that list is a real ranking)."""


class VerdictPick(_Frozen):
    """One card's figure inside one program's verdict."""

    card_id: UUID
    bank: str
    card_name: str
    partner_units: int
    """Miles (airline) or points (hotel) in THE PROGRAM's own unit."""
    requires_portal: str | None
    needs_verification: bool | None


class ProgramVerdict(_Frozen):
    """The answer for one program the wallet can reach — see module docstring."""

    program_id: UUID
    program_name: str
    partner_name: str
    partner_type: PartnerType
    is_target: bool
    winner: VerdictPick | None
    runner_up: VerdictPick | None
    lead: int | None
    tied: bool
    too_small: bool
    """No winner because the spend rounds to under one unit everywhere — NOT
    because nobody earns here. Distinct so the UI never calls rounding an
    issuer exclusion."""
    direct_winner: VerdictPick | None
    direct_tied: bool
    """The direct alternative is itself a tie — no direct card to name."""


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

    program_verdicts: tuple[ProgramVerdict, ...]
    """Every reachable program's winner, chosen target first."""
    overall_pick: UUID | None
    """The sole top card in every program where anyone earns; None when the
    answer depends on the program (or ties)."""
    no_card_earns: bool
    """Every card in the wallet — routable or not — has a ZERO rate here (an
    issuer exclusion). Decided on rates, never on floored points, so a tiny
    spend or a wallet that just can't reach the program is not reported as
    'nobody earns'."""


def rank_cards_for_spend(
    snapshot: CatalogSnapshot,
    *,
    amount_inr: int,
    category: SpendCategory,
    card_ids: Sequence[UUID],
    target_program_id: UUID | None = None,
    unverified_ids: Set[UUID] | None = None,
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
        points = _points_for(amount_inr, rule, card.base_earn_rate)
        direct_points = _direct_points(amount_inr, rule, card, points)

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
            over_cap_earn=rule.over_cap_earn if rule is not None and cap is not None else None,
            points_earned=points,
            miles_earned=marginal_miles(points, link) if link else None,
            miles_per_100=miles_per_100(rate, link) if link else None,
            requires_portal=rule.requires_portal if rule is not None else None,
            direct_points_earned=direct_points,
            direct_miles_earned=marginal_miles(direct_points, link) if link else None,
            transfer_ratio_from=link.ratio_from if link else None,
            transfer_ratio_to=link.ratio_to if link else None,
            needs_verification=_flagged(
                unverified_ids, rule, card, link, base_involved=_base_involved(rule, amount_inr)
            ),
            direct_needs_verification=_direct_flagged(unverified_ids, rule, card, link, amount_inr),
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
            (-(o.miles_earned or 0), o.card_name, str(o.card_id))
            if target_id is not None
            else (-o.points_earned, o.card_name, str(o.card_id))
        )
    )
    unroutable.sort(key=lambda o: (-o.points_earned, o.card_name, str(o.card_id)))

    reach = partner_reach(
        snapshot, wallet, target_program_id=target_id, unverified_ids=unverified_ids
    )
    computed = [
        _verdict(
            snapshot,
            wallet,
            partner_id=entry.partner_id,
            is_target=entry.is_target,
            amount_inr=amount_inr,
            rule_by_card=rule_by_card,
            unverified_ids=unverified_ids,
        )
        for entry in reach
    ]
    verdicts = tuple(verdict for verdict, _, _ in computed)

    # Card-first fields: where each card's points go, what it wins, its best
    # placing anywhere (see module docstring).
    destinations: dict[UUID, list[CardDestination]] = {card.id: [] for card in wallet}
    best_for: dict[UUID, list[UUID]] = {card.id: [] for card in wallet}
    best_place: dict[UUID, int] = {}
    for verdict, order, tops in computed:
        for card_id, destination in order:
            destinations[card_id].append(destination)
            # Competition placing from the FIGURES: how many cards earn
            # strictly more here. Equal earners share a place — a name
            # tiebreak must never push a tied card down the order.
            place = sum(1 for _, d in order if d.partner_units > destination.partner_units)
            best_place[card_id] = min(best_place.get(card_id, place), place)
        for card_id in tops:
            best_for[card_id].append(verdict.program_id)

    def card_first(option: CardSpendOption) -> CardSpendOption:
        return option.model_copy(
            update={
                "destinations": tuple(
                    sorted(destinations[option.card_id], key=lambda d: d.program_name)
                ),
                "best_for": tuple(best_for[option.card_id]),
            }
        )

    ranked = [card_first(o) for o in ranked]
    unroutable = [card_first(o) for o in unroutable]
    if target_id is None:

        def standing(o: CardSpendOption) -> tuple[int, int]:
            return (-len(o.best_for), best_place.get(o.card_id, len(wallet) + 1))

        ranked.sort(key=lambda o: (*standing(o), o.card_name, str(o.card_id)))
        # Dense positions: equal standing → same number ("1, 1, 2"), so the
        # list never presents a name tiebreak as a ranking.
        positions: dict[tuple[int, int], int] = {}
        for option in ranked:
            positions.setdefault(standing(option), len(positions) + 1)
        ranked = [o.model_copy(update={"order_position": positions[standing(o)]}) for o in ranked]

    earning = [v for v in verdicts if v.winner is not None]
    sole_tops = {v.winner.card_id for v in earning if v.winner is not None and not v.tied}
    overall_pick = (
        next(iter(sole_tops))
        if earning and len(sole_tops) == 1 and all(not v.tied for v in earning)
        else None
    )
    no_card_earns = all(o.effective_earn_rate == 0 for o in (*ranked, *unroutable))

    return BestCardResult(
        catalog_snapshot_version=snapshot.version,
        amount_inr=amount_inr,
        category=category,
        ranking_basis="miles" if target_id is not None else "points",
        target_program_id=target_id,
        target_program_name=target_name,
        ranked=tuple(ranked),
        unroutable=tuple(unroutable),
        partner_reach=reach,
        program_verdicts=verdicts,
        overall_pick=overall_pick,
        no_card_earns=no_card_earns,
    )


def _verdict(
    snapshot: CatalogSnapshot,
    wallet: Sequence[Card],
    *,
    partner_id: UUID,
    is_target: bool,
    amount_inr: int,
    rule_by_card: dict[UUID, RewardCategoryRule],
    unverified_ids: Set[UUID] | None,
) -> tuple[ProgramVerdict, list[tuple[UUID, CardDestination]], list[UUID]]:
    """One program's answer, in its own unit. Card name breaks ties only for
    ORDER; an exact tie is reported as `tied`, never as a win."""
    partner = next(p for p in snapshot.partners if p.id == partner_id)
    links = {
        link.currency_id: link for link in snapshot.transfer_links if link.partner_id == partner_id
    }

    best: list[tuple[int, str, str, VerdictPick]] = []
    direct: list[tuple[int, str, str, VerdictPick]] = []
    any_positive_rate = False
    destination_by_card: dict[UUID, CardDestination] = {}
    for card in wallet:
        link = links.get(card.reward_currency_id)
        if link is None:
            continue
        rule = rule_by_card.get(card.id)
        any_positive_rate |= (rule.earn_rate if rule is not None else card.base_earn_rate) > 0
        points = _points_for(amount_inr, rule, card.base_earn_rate)
        direct_points = _direct_points(amount_inr, rule, card, points)
        portal = rule.requires_portal if rule is not None else None
        pick = VerdictPick(
            card_id=card.id,
            bank=card.bank,
            card_name=card.card_name,
            partner_units=marginal_miles(points, link),
            requires_portal=portal,
            needs_verification=_flagged(
                unverified_ids, rule, card, link, base_involved=_base_involved(rule, amount_inr)
            ),
        )
        best.append((pick.partner_units, card.card_name, str(card.id), pick))
        # Booked direct, a portal-gated rule does not apply: the card is on its
        # base rate, so the pick's provenance is the card row, not the rule.
        direct_pick = pick.model_copy(
            update={
                "partner_units": marginal_miles(direct_points, link),
                "requires_portal": None,
                "needs_verification": _direct_flagged(unverified_ids, rule, card, link, amount_inr),
            }
        )
        direct.append((direct_pick.partner_units, card.card_name, str(card.id), direct_pick))
        destination_by_card[card.id] = CardDestination(
            program_id=partner.id,
            program_name=partner.program_name,
            partner_name=partner.partner_name,
            partner_type=partner.partner_type,
            partner_units=pick.partner_units,
            direct_partner_units=direct_pick.partner_units,
            ratio_from=link.ratio_from,
            ratio_to=link.ratio_to,
            needs_verification=pick.needs_verification,
        )

    # Name, then id, break ties for ORDER only; an exact tie is reported.
    best.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    direct.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))

    top_units = best[0][0] if best else 0
    winner = best[0][3] if top_units > 0 else None
    # A runner-up may itself earn 0 (an exclusion) — still reported, so the
    # lead reads as "this many more than nothing".
    runner_up = best[1][3] if winner is not None and len(best) > 1 else None
    lead = winner.partner_units - runner_up.partner_units if winner and runner_up else None
    # Owed whenever ANY card sharing the top figure needs a portal — name
    # order among tied cards must not decide whether the user is told.
    needs_direct = winner is not None and any(
        entry[3].requires_portal is not None for entry in best if entry[0] == top_units
    )
    direct_winner = direct[0][3] if needs_direct and direct[0][0] > 0 else None
    direct_tied = direct_winner is not None and len(direct) > 1 and direct[1][0] == direct[0][0]
    order = [(entry[3].card_id, destination_by_card[entry[3].card_id]) for entry in best]
    tops = [entry[3].card_id for entry in best if winner is not None and entry[0] == top_units]
    verdict = ProgramVerdict(
        program_id=partner.id,
        program_name=partner.program_name,
        partner_name=partner.partner_name,
        partner_type=partner.partner_type,
        is_target=is_target,
        winner=winner,
        runner_up=runner_up,
        lead=lead,
        tied=lead == 0,
        too_small=winner is None and any_positive_rate,
        direct_winner=direct_winner,
        direct_tied=direct_tied,
    )
    return verdict, order, tops


def _direct_points(
    amount_inr: int, rule: RewardCategoryRule | None, card: Card, portal_points: int
) -> int:
    """Booked direct, a portal-gated rule does not apply — the card earns its
    base rate. Any other rule applies however you pay."""
    if rule is None or rule.requires_portal is None:
        return portal_points
    return _points_for(amount_inr, None, card.base_earn_rate)


def _base_involved(rule: RewardCategoryRule | None, amount_inr: int) -> bool:
    """Does the card's base rate take part in this figure? Yes with no rule,
    and when spend past a cap earns the base rate."""
    if rule is None:
        return True
    cap = rule.monthly_cap_inr
    return cap is not None and amount_inr > cap and rule.over_cap_earn == OverCapEarn.BASE_RATE


def _flagged(
    unverified_ids: Set[UUID] | None,
    rule: RewardCategoryRule | None,
    card: Card,
    link: CurrencyTransferLink | None,
    *,
    base_involved: bool,
) -> bool | None:
    """Provenance of a priced figure: every row it rests on — the rule, the
    card row when the base rate takes part, and (when converted) the link,
    its currency and the partner. One convention for options and picks.
    None = no provenance supplied (not assessed, never 'verified')."""
    if unverified_ids is None:
        return None
    ids: set[UUID] = set()
    if rule is not None:
        ids.add(rule.id)
    if base_involved:
        ids.add(card.id)
    if link is not None:
        ids |= {link.id, link.currency_id, link.partner_id}
    return not ids.isdisjoint(unverified_ids)


def _direct_flagged(
    unverified_ids: Set[UUID] | None,
    rule: RewardCategoryRule | None,
    card: Card,
    link: CurrencyTransferLink | None,
    amount_inr: int,
) -> bool | None:
    """Booked direct, a portal-gated rule drops out and the base rate applies
    (card row); any other rule prices direct exactly as it does anyway."""
    if rule is not None and rule.requires_portal is not None:
        return _flagged(unverified_ids, None, card, link, base_involved=True)
    return _flagged(
        unverified_ids, rule, card, link, base_involved=_base_involved(rule, amount_inr)
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

    # One purchase larger than the whole monthly cap: the excess earns what
    # the rule states — the base rate, or nothing (SBI Cashback).
    blended = blended_earn_rate(amount_inr, rule, base_rate)
    return blended, cap, True


def _points_for(amount_inr: int, rule: RewardCategoryRule | None, base_rate: Decimal) -> int:
    """floor of the EXACT points — one rounding, from the cap split itself.

    Never re-derived from the displayed `effective_earn_rate`: past a cap that
    rate is a 4dp ROUND_DOWN blend, and multiplying it back out rounds twice
    (SBI online ₹50,001 would give 500.01 × 3.9999 = 1,999.96 → 1,999 instead
    of the exact 2,000.00 → 2,000).
    """
    exact = (
        Decimal(amount_inr) * base_rate / Decimal(100)
        if rule is None
        else category_points_exact(amount_inr, rule, base_rate)
    )
    return int(exact.quantize(_ONE, rounding=ROUND_DOWN))
