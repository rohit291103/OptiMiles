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

  miles_per_100(rate, link) [miles/₹100] = rate × ratio_to / ratio_from,
      quantized to 4dp ROUND_DOWN

  blended_earn_rate(S, acc, base, cap) [pts/₹100]:
      acc                                  if cap is None or S ≤ cap
      (cap×acc + (S−cap)×base) / S         otherwise, quantized 4dp ROUND_DOWN
      (rates are per ₹100, so the ₹100 scaling cancels in the blend)
"""

from decimal import ROUND_DOWN, Decimal

from app.domain import CurrencyTransferLink

_FOUR_DP = Decimal("0.0001")


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


def blended_earn_rate(
    monthly_spend_inr: int,
    accelerated_rate: Decimal,
    base_rate: Decimal,
    monthly_cap_inr: int | None,
) -> Decimal:
    """Cap-aware rate for routing a WHOLE category's monthly spend here.

    Spend beyond the accelerated cap earns the card's base rate (schema
    semantics, db-schema-v1 §3.1) — the blend is the honest per-₹100 number
    for the allocation decision, not the headline rate.
    """
    if monthly_cap_inr is None or monthly_spend_inr <= monthly_cap_inr:
        return accelerated_rate
    capped = Decimal(monthly_cap_inr) * accelerated_rate
    overflow = Decimal(monthly_spend_inr - monthly_cap_inr) * base_rate
    exact = (capped + overflow) / Decimal(monthly_spend_inr)
    return exact.quantize(_FOUR_DP, rounding=ROUND_DOWN)  # never normalize(): see miles_per_100
