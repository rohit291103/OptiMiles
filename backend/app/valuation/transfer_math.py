"""Pure transfer/earn arithmetic — the shared calculation vocabulary.

This module is the ONLY place ratio conversion and cap-blending math lives;
Optimization and Simulation call these functions rather than reimplementing
them (blueprint §3.1). Rules of the house:

- **Exact arithmetic only.** `int` for points/miles/INR, `Decimal` for rates.
  Floats never touch reward math.
- **Rounding is directional and deliberate — always the conservative side:**
  transfers floor to whole ratio blocks (you cannot transfer a fraction of a
  block; flooring never overstates miles); rates quantize to 4 decimal places
  ROUND_DOWN (under-promise). The requirement buffer (Stage 3) ceils UP for
  the same reason: never overstate what the user will have, never understate
  what they need.

Formulas (units in brackets):

  transferable_points(P, link) [pts]:
      0                       if P < min_transfer_points
      min(P, max_transfer)    otherwise (max_transfer is per CALENDAR YEAR;
                              MVP horizons ≤ 12 months apply it once —
                              multi-year horizons must re-apply per year)

  points_to_miles(P, link) [miles] = floor(P / ratio_from) × ratio_to

  marginal_miles(P, link) [miles] = floor(P × ratio_to / ratio_from)
      the MARGINAL worth of P points — what they add to a balance that gets
      transferred in whole blocks later. Differs from points_to_miles only
      when P is not a whole number of blocks — but there it matters a lot:
      150 HDFC Regalia RP into Marriott (100:33) are worth 49 marginal miles,
      against the 33 that block-flooring 150 as a standalone send would give.
      Price a purchase or a bonus with this; model an actual send with
      points_to_miles.

  whole_block_transfer(P, link) [(pts, miles)]:
      blocks = floor(P / ratio_from)
      → (blocks × ratio_from, blocks × ratio_to)
      the points side of the SAME flooring: what actually leaves a balance
      when only whole blocks may transfer — the remainder stays on the card

  miles_per_100(rate, link) [miles/₹100] = rate × ratio_to / ratio_from,
      quantized to 4dp ROUND_DOWN

  CAP OVERFLOW — the ONE implementation (defect fixed 2026-11-02). What
  spend above a rule's monthly cap earns is the rule's `over_cap_earn`:
      over(rule, base) = base   if over_cap_earn = base_rate
                         0      if over_cap_earn = nothing
  A capped rule that does not state it raises — never a silent base rate
  (validate_catalog CR-01 rejects such a row before it gets here).

  category_points_exact(S, rule, base) [pts, exact Decimal, UNfloored]:
      S × acc / 100                                if cap is None or S ≤ cap
      (cap × acc + (S − cap) × over) / 100         otherwise
      Callers floor ONCE per card-month (projector, allocation) or per
      purchase (Best Card) — this function never rounds.

  blended_earn_rate(S, rule, base) [pts/₹100]:
      category_points_exact(S, rule, base) × 100 / S, quantized 4dp ROUND_DOWN
      = acc when S ≤ cap; (cap×acc + (S−cap)×over) / S otherwise
      e.g. SBI online ₹50,000, cap ₹40,000, 5.00, over = nothing:
           (40,000×5 + 10,000×0) / 50,000 = 4.00   (old base-rate rule: 4.20)
"""

from decimal import ROUND_DOWN, Decimal

from app.domain import CurrencyTransferLink, OverCapEarn, RewardCategoryRule

_FOUR_DP = Decimal("0.0001")
_HUNDRED = Decimal(100)


def transferable_points(points: int, link: CurrencyTransferLink) -> int:
    """Points that can actually enter this transfer link (threshold + cap)."""
    if points < link.min_transfer_points:
        return 0
    if link.max_transfer_points is not None:
        return min(points, link.max_transfer_points)
    return points


def points_to_miles(points: int, link: CurrencyTransferLink) -> int:
    """Whole-block conversion: floor(points / ratio_from) × ratio_to."""
    return (points // link.ratio_from) * link.ratio_to


def marginal_miles(points: int, link: CurrencyTransferLink) -> int:
    """Marginal worth of `points` in the partner program — see module docstring.

    NOT a transfer: no min/max limits and no whole-block flooring, because
    the points being priced join a balance that is transferred in blocks at
    some later date. `points_to_miles` models the send itself.
    """
    exact = Decimal(points) * link.ratio_to / Decimal(link.ratio_from)
    return int(exact.quantize(Decimal(1), rounding=ROUND_DOWN))


def whole_block_transfer(points: int, link: CurrencyTransferLink) -> tuple[int, int]:
    """(points leaving the balance, miles credited) for a whole-block send.

    Simulation's ledger needs both sides of the floor — points_to_miles
    answers only the miles side, and re-deriving the points side elsewhere
    would split ratio conversion across modules.
    """
    blocks = points // link.ratio_from
    return blocks * link.ratio_from, blocks * link.ratio_to


def convert_balance(points: int, link: CurrencyTransferLink) -> int:
    """End-to-end: threshold + annual cap, then whole-block ratio conversion."""
    return points_to_miles(transferable_points(points, link), link)


def miles_per_100(earn_rate: Decimal, link: CurrencyTransferLink) -> Decimal:
    """Target-program miles per ₹100 for a given earn rate through a link."""
    exact = earn_rate * link.ratio_to / Decimal(link.ratio_from)
    # Fixed 4dp form, never normalize(): Decimal("10.0000").normalize() is
    # Decimal("1E+1"), which serializes as the string "1E+1" into JSONB and
    # API payloads. Display formatting is the caller's job.
    return exact.quantize(_FOUR_DP, rounding=ROUND_DOWN)


def over_cap_rate(rule: RewardCategoryRule, base_rate: Decimal) -> Decimal:
    """Points per ₹100 that spend ABOVE `rule`'s cap earns (see module docstring).

    Raises ValueError for a capped rule that does not state `over_cap_earn` —
    assuming the base rate is exactly the defect this replaced.
    """
    if rule.over_cap_earn is OverCapEarn.NOTHING:
        return Decimal(0)
    if rule.over_cap_earn is OverCapEarn.BASE_RATE:
        return base_rate
    raise ValueError(
        f"category rule {rule.id} ({rule.category_label!r}) is capped but does not state "
        "over_cap_earn — catalog integrity failure (validate_catalog CR-01); "
        "refusing to assume what spend above the cap earns"
    )


def category_points_exact(
    monthly_spend_inr: int, rule: RewardCategoryRule, base_rate: Decimal
) -> Decimal:
    """Exact, UNfloored points for routing `monthly_spend_inr` through `rule`
    in one month — the cap split, with overflow priced by `over_cap_rate`.

    Only MONTHLY caps are metered. A quarterly/annual cap raises rather than
    being ignored (which would earn uncapped); validate_catalog CR-03 keeps
    such rows out of the catalog in the first place.
    """
    if rule.quarterly_cap_inr is not None or rule.annual_cap_inr is not None:
        raise ValueError(
            f"category rule {rule.id} ({rule.category_label!r}) carries a quarterly/annual "
            "cap; only monthly caps are metered (validate_catalog CR-03) — refusing to "
            "price it as uncapped"
        )
    cap = rule.monthly_cap_inr
    if cap is None:
        return Decimal(monthly_spend_inr) * rule.earn_rate / _HUNDRED
    over = over_cap_rate(rule, base_rate)  # validates the row even under the cap
    if monthly_spend_inr <= cap:
        return Decimal(monthly_spend_inr) * rule.earn_rate / _HUNDRED
    return (
        Decimal(cap) * rule.earn_rate + Decimal(monthly_spend_inr - cap) * over
    ) / _HUNDRED


def blended_earn_rate(
    monthly_spend_inr: int, rule: RewardCategoryRule, base_rate: Decimal
) -> Decimal:
    """Cap-aware rate for routing a WHOLE category's monthly spend here.

    The honest per-₹100 number for the allocation decision, not the headline
    rate: above the cap the blend falls toward the base rate or toward zero,
    as the rule's `over_cap_earn` states.
    """
    if monthly_spend_inr <= 0:
        return rule.earn_rate
    exact = category_points_exact(monthly_spend_inr, rule, base_rate) * _HUNDRED / Decimal(
        monthly_spend_inr
    )
    if exact == rule.earn_rate:
        return rule.earn_rate  # under the cap: the rule's own rate, unchanged
    return exact.quantize(_FOUR_DP, rounding=ROUND_DOWN)  # never normalize(): see miles_per_100
