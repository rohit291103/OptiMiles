"""Valuation Engine pure math — every expected value below is hand-computed
and traceable to the seed catalog / research doc. These functions are the
shared calculation vocabulary for Optimization and Simulation, so a wrong
constant here corrupts every downstream number.
"""

from decimal import Decimal
from uuid import uuid4

from app.domain import CurrencyTransferLink
from app.valuation.transfer_math import (
    blended_earn_rate,
    convert_balance,
    miles_per_100,
    points_to_miles,
    transferable_points,
)


def _link(
    ratio_from: int,
    ratio_to: int,
    min_transfer: int = 1000,
    max_transfer: int | None = None,
) -> CurrencyTransferLink:
    return CurrencyTransferLink(
        id=uuid4(),
        currency_id=uuid4(),
        partner_id=uuid4(),
        ratio_from=ratio_from,
        ratio_to=ratio_to,
        min_transfer_points=min_transfer,
        max_transfer_points=max_transfer,
        transfer_fee_inr=0,
        processing_days_min=1,
        processing_days_max=5,
    )


# ── points_to_miles: floor to whole ratio blocks (never overstate) ────────


def test_one_to_one_is_identity() -> None:
    assert points_to_miles(70_000, _link(1, 1)) == 70_000


def test_five_to_two_floors_to_blocks() -> None:
    """Magnus 5:2 (research §1): 12,345 points = 2,469 whole blocks of 5
    → 2,469 × 2 = 4,938 miles. The 0.8-block remainder transfers nothing."""
    assert points_to_miles(12_345, _link(5, 2)) == 4_938


def test_two_to_one_rounds_down_not_half_up() -> None:
    assert points_to_miles(1_001, _link(2, 1)) == 500  # not 500.5, not 501


def test_one_to_two_doubles() -> None:
    """Atlas 1:2 (research §1): each EDGE Mile becomes 2 KrisFlyer miles."""
    assert points_to_miles(30_000, _link(1, 2)) == 60_000


# ── transferable_points: min threshold and annual cap ─────────────────────


def test_below_minimum_transfers_nothing() -> None:
    assert transferable_points(999, _link(2, 1, min_transfer=1000)) == 0


def test_exactly_at_minimum_transfers() -> None:
    assert transferable_points(1_000, _link(2, 1, min_transfer=1000)) == 1_000


def test_annual_cap_truncates() -> None:
    """Research §2 'Atlas Bottleneck': 35,000 EDGE Miles held, but the Group A
    cap allows only 30,000/year through the link."""
    assert transferable_points(35_000, _link(1, 2, max_transfer=30_000)) == 30_000


def test_convert_balance_composes_cap_then_ratio() -> None:
    """The bottleneck end-to-end: 35,000 EM → capped 30,000 → 60,000 KrisFlyer
    miles (the research doc's own worked number)."""
    assert convert_balance(35_000, _link(1, 2, min_transfer=500, max_transfer=30_000)) == 60_000


# ── miles_per_100: earn rate × transfer ratio, quantized 4dp DOWN ─────────


def test_infinia_travel_golden() -> None:
    """Infinia SmartBuy travel 16.65 pts/₹100 × 1:1 = 16.65 miles/₹100."""
    assert miles_per_100(Decimal("16.65"), _link(1, 1)) == Decimal("16.65")


def test_atlas_travel_golden() -> None:
    """Atlas travel 5 EM/₹100 × 1:2 = 10 KrisFlyer miles/₹100 — the best
    uncapped-rate path in the MVP catalog (capped annually at transfer time)."""
    assert miles_per_100(Decimal("5.00"), _link(1, 2)) == Decimal("10.00")


def test_magnus_default_golden() -> None:
    """Magnus 6 ER/₹100 × 5:2 = 2.4 miles/₹100."""
    assert miles_per_100(Decimal("6.00"), _link(5, 2)) == Decimal("2.4")


def test_amex_default_golden() -> None:
    """Amex 2 MR/₹100 × 2:1 = 1 mile/₹100."""
    assert miles_per_100(Decimal("2.00"), _link(2, 1)) == Decimal("1")


def test_nonterminating_division_quantizes_down() -> None:
    """1 pt/₹100 at 3:1 = 0.3333… → 0.3333 (4dp, ROUND_DOWN — under-promise)."""
    assert miles_per_100(Decimal("1.00"), _link(3, 1)) == Decimal("0.3333")


# ── blended_earn_rate: cap-aware marginal economics ───────────────────────


def test_spend_within_cap_earns_accelerated_rate() -> None:
    assert blended_earn_rate(
        monthly_spend_inr=40_000,
        accelerated_rate=Decimal("16.65"),
        base_rate=Decimal("3.33"),
        monthly_cap_inr=150_000,
    ) == Decimal("16.65")


def test_spend_beyond_cap_blends_exactly() -> None:
    """₹200k into a ₹150k cap: (1500×16.65 + 500×3.33) / 2000
    = (24,975 + 1,665) / 2,000 = 13.32 pts/₹100 — hand-computed."""
    assert blended_earn_rate(
        monthly_spend_inr=200_000,
        accelerated_rate=Decimal("16.65"),
        base_rate=Decimal("3.33"),
        monthly_cap_inr=150_000,
    ) == Decimal("13.32")


def test_spend_exactly_at_cap_is_boundary_not_blend() -> None:
    assert blended_earn_rate(
        monthly_spend_inr=150_000,
        accelerated_rate=Decimal("16.65"),
        base_rate=Decimal("3.33"),
        monthly_cap_inr=150_000,
    ) == Decimal("16.65")


def test_no_cap_means_accelerated_rate() -> None:
    assert blended_earn_rate(
        monthly_spend_inr=10_000_000,
        accelerated_rate=Decimal("5.00"),
        base_rate=Decimal("2.00"),
        monthly_cap_inr=None,
    ) == Decimal("5.00")


def test_round_number_rates_never_serialize_as_scientific_notation() -> None:
    """Decimal("10.0000").normalize() is Decimal("1E+1") — which would emit
    the literal string "1E+1" into JSONB/API payloads (reviewer finding,
    2026-07-04). The fixed 4dp form must survive serialization."""
    atlas_rate = miles_per_100(Decimal("5.00"), _link(1, 2))  # lands exactly on 10
    assert atlas_rate == Decimal("10")
    assert "e" not in str(atlas_rate).lower()

    exact_ten_blend = blended_earn_rate(
        monthly_spend_inr=100_000,
        accelerated_rate=Decimal("10.00"),
        base_rate=Decimal("10.00"),
        monthly_cap_inr=50_000,
    )
    assert "e" not in str(exact_ten_blend).lower()
