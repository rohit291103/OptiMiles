"""Valuation Engine pure math — every expected value below is hand-computed
and traceable to the seed catalog / research doc. These functions are the
shared calculation vocabulary for Optimization and Simulation, so a wrong
constant here corrupts every downstream number.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain import CurrencyTransferLink, OverCapEarn, RewardCategoryRule, SpendCategory
from app.valuation.transfer_math import (
    blended_earn_rate,
    category_points_exact,
    convert_balance,
    miles_per_100,
    points_to_miles,
    transferable_points,
    whole_block_transfer,
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


# ── category_points_exact / blended_earn_rate: the ONE cap-overflow rule ──
# Spend above a cap earns whatever the rule's `over_cap_earn` says — the
# card's base rate (Atlas, HDFC SmartBuy) or NOTHING (SBI Cashback). Before
# 2026-11-02 every overflow was priced at base, which overstated SBI.


def _rule(
    rate: str,
    cap: int | None,
    over_cap_earn: OverCapEarn | None,
) -> RewardCategoryRule:
    return RewardCategoryRule(
        id=uuid4(),
        card_id=uuid4(),
        category_slug=SpendCategory.TRAVEL,
        category_label="test",
        earn_rate=Decimal(rate),
        monthly_cap_inr=cap,
        over_cap_earn=over_cap_earn,
    )


_INFINIA_TRAVEL = _rule("16.65", 150_000, OverCapEarn.BASE_RATE)
_SBI_ONLINE = _rule("5.00", 40_000, OverCapEarn.NOTHING)


def test_spend_within_cap_earns_accelerated_rate() -> None:
    assert blended_earn_rate(40_000, _INFINIA_TRAVEL, Decimal("3.33")) == Decimal("16.65")


def test_spend_beyond_cap_blends_down_to_base_when_rule_says_base() -> None:
    """₹200k into a ₹150k cap, overflow at base: (1500×16.65 + 500×3.33) / 2000
    = (24,975 + 1,665) / 2,000 = 13.32 pts/₹100 — hand-computed."""
    assert blended_earn_rate(200_000, _INFINIA_TRAVEL, Decimal("3.33")) == Decimal("13.32")


def test_spend_beyond_cap_earns_nothing_when_rule_says_nothing() -> None:
    """THE DEFECT. SBI online ₹50,000 into a ₹40,000 cap (₹2,000 cashback
    ÷ 5%), overflow earns NOTHING: (400×5.00 + 100×0) / 500 = 2,000/500
    = 4.00/₹100. The old base-rate rule gave (2,000 + 100×1.00)/500 = 4.20."""
    assert blended_earn_rate(50_000, _SBI_ONLINE, Decimal("1.00")) == Decimal("4.00")


def test_points_exact_beyond_cap_earning_nothing_is_the_cap_itself() -> None:
    """SBI online ₹1,00,000: min(1,00,000, 40,000)/100 × 5.00 = 2,000 —
    exactly the ₹2,000 per-cycle cashback ceiling; the other ₹60,000 adds 0.
    (Old rule: 2,000 + 600 × 1.00 = 2,600.)"""
    assert category_points_exact(100_000, _SBI_ONLINE, Decimal("1.00")) == Decimal("2000")


def test_points_exact_beyond_cap_at_base_is_unfloored() -> None:
    """Infinia ₹150,100: 1,500×16.65 + 1×3.33 = 24,975 + 3.33 = 24,978.33 —
    exact, NOT floored (callers floor once per card-month)."""
    assert category_points_exact(150_100, _INFINIA_TRAVEL, Decimal("3.33")) == Decimal(
        "24978.33"
    )


def test_spend_exactly_at_cap_is_boundary_not_blend() -> None:
    assert blended_earn_rate(150_000, _INFINIA_TRAVEL, Decimal("3.33")) == Decimal("16.65")
    # SBI at exactly ₹40,000: 400 × 5.00 = 2,000 — the full rate, nothing lost.
    assert category_points_exact(40_000, _SBI_ONLINE, Decimal("1.00")) == Decimal("2000")


def test_no_cap_means_accelerated_rate() -> None:
    uncapped = _rule("5.00", None, None)
    assert blended_earn_rate(10_000_000, uncapped, Decimal("2.00")) == Decimal("5.00")


def test_capped_rule_that_does_not_state_its_overflow_fails_loudly() -> None:
    """Never silently default: a capped rule with no `over_cap_earn` is a
    catalog integrity failure (validate_catalog rejects it too), not a
    licence to assume the base rate."""
    unstated = _rule("5.00", 40_000, None)
    with pytest.raises(ValueError, match="over_cap_earn"):
        category_points_exact(50_000, unstated, Decimal("1.00"))
    # ...even when the spend fits under the cap: the row itself is broken.
    with pytest.raises(ValueError, match="over_cap_earn"):
        blended_earn_rate(10_000, unstated, Decimal("1.00"))


def test_non_monthly_cap_is_refused_not_ignored() -> None:
    """Only monthly caps are metered. A quarterly/annual cap must raise
    rather than silently earn uncapped (validate_catalog CR-03 keeps such a
    row out of the catalog; this is the belt to that braces)."""
    for field in ("quarterly_cap_inr", "annual_cap_inr"):
        rule = _rule("5.00", None, OverCapEarn.NOTHING).model_copy(update={field: 100_000})
        with pytest.raises(ValueError, match="quarterly/annual"):
            category_points_exact(10_000, rule, Decimal("1.00"))


def test_round_number_rates_never_serialize_as_scientific_notation() -> None:
    """Decimal("10.0000").normalize() is Decimal("1E+1") — which would emit
    the literal string "1E+1" into JSONB/API payloads (reviewer finding,
    2026-07-04). The fixed 4dp form must survive serialization."""
    atlas_rate = miles_per_100(Decimal("5.00"), _link(1, 2))  # lands exactly on 10
    assert atlas_rate == Decimal("10")
    assert "e" not in str(atlas_rate).lower()

    exact_ten_blend = blended_earn_rate(
        100_000, _rule("10.00", 50_000, OverCapEarn.BASE_RATE), Decimal("10.00")
    )
    assert "e" not in str(exact_ten_blend).lower()


# ── whole_block_transfer: the (points_sent, miles) pair Simulation ledgers ──


def test_whole_block_transfer_leaves_remainder_on_balance() -> None:
    """Magnus 5:2, 12,347 points: 2,469 blocks ⇒ 12,345 points leave,
    4,938 miles credit, 2-point remainder stays — flooring never destroys
    points (Phase 3 ledger requirement)."""
    assert whole_block_transfer(12_347, _link(5, 2)) == (12_345, 4_938)


def test_whole_block_transfer_one_to_one_sends_everything() -> None:
    assert whole_block_transfer(70_000, _link(1, 1)) == (70_000, 70_000)


def test_whole_block_transfer_agrees_with_points_to_miles() -> None:
    """The miles side must be points_to_miles exactly — one formula, two
    views, never two implementations."""
    link = _link(2, 1)
    sent, miles = whole_block_transfer(999, link)
    assert (sent, miles) == (998, 499)
    assert miles == points_to_miles(999, link)
