"""Stage 6 — the feasibility gate over the real seed catalog.

The bound is a deliberately OPTIMISTIC upper estimate (exact-ratio conversion,
no whole-block flooring, no transfer-timing haircut): it must never falsely
declare a goal infeasible — Simulation (Stage 8) later truths whatever the
generator builds. It IS currency-cap-aware: a hard annual transfer cap
(Atlas 30k, Burgundy 2L) bounds real-world miles no matter how much is earned,
and ignoring it would pass structurally impossible goals.

Fixture (unless a test says otherwise): Hyderabad → Singapore, business × 2
pax, horizon 8 ⇒ required 45,000 × 2 = 90,000 miles, buffer 4,500.

Hand-computed reference numbers (seed catalog of 2026-07-04):

  Infinia-wallet earn (travel 40k, dining 30k / month):
      travel 40,000 ≤ 1.5L cap → 16.65 pts/₹100 → 6,660 pts/mo
      dining default 3.33 → 999 pts/mo             → 7,659 pts/mo
      8 months = 61,272 pts + 20,000 balance = 81,272 → ×1:1 = 81,272 miles

  Burgundy earn (same spend, categories rerouted there):
      travel 30 pts/₹100 → 12,000/mo; dining 6 → 1,800/mo = 13,800/mo
      8 months = 110,400 pts ≤ 2L link cap → ×4/5 = 88,320 miles
      + Infinia balance 20,000 (1:1)                = 108,320 miles
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    FeasibilityVerdict,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.feasibility import assess_feasibility
from app.valuation.opportunities import enumerate_opportunities

TODAY = date(2026, 7, 4)


def _context(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int] | None = None,
    wallet: dict[str, int] | None = None,
    horizon_months: int = 8,
    constraints: ConstraintSet | None = None,
) -> PlanningContext:
    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=horizon_months,
        num_passengers=2,
        confidence=0.95,
    )
    resolution = resolve_goal(intent, snapshot, today=TODAY)
    assert isinstance(resolution, GoalResolution)
    goal = TravelGoal(id=uuid4(), user_id=uuid4(), status="active", **resolution.model_dump())
    spend = (
        spend if spend is not None else {SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000}
    )
    wallet = wallet if wallet is not None else {"hdfc-infinia": 20_000}
    return PlanningContext(
        user_id=goal.user_id,
        goal=goal,
        requirement=estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot=snapshot,
        wallet=tuple(
            WalletCard(card_id=seed_id("card", slug), current_points_balance=balance)
            for slug, balance in wallet.items()
        ),
        spend_profile=SpendProfile(
            items=tuple(
                SpendProfileItem(category_slug=cat, monthly_spend_inr=amount)
                for cat, amount in spend.items()
            )
        ),
        horizon_months=horizon_months,
        constraints=constraints if constraints is not None else ConstraintSet(),
    )


def _assess(context: PlanningContext) -> FeasibilityVerdict:
    return assess_feasibility(enumerate_opportunities(context), context)


NO_NEW_CARDS = ConstraintSet(no_new_cards=True)


# ── The bound, feasible side ──────────────────────────────────────────────


def test_golden_feasible_unconstrained(snapshot: CatalogSnapshot) -> None:
    """Acquisitions allowed → both categories route to Burgundy (best rates):
    110,400 pts × 4/5 = 88,320 + Infinia balance 20,000 = 108,320 ≥ 90,000."""
    verdict = _assess(_context(snapshot))
    assert verdict.feasible is True
    assert verdict.best_case_miles == 108_320
    assert verdict.gap_miles == 90_000 - 108_320  # ≤ 0 when feasible
    assert verdict.tight is False  # 108,320 ≥ 94,500 (required + buffer)
    assert verdict.adjustment_options == ()


def test_golden_infeasible_wallet_only(snapshot: CatalogSnapshot) -> None:
    """no_new_cards → Infinia alone: 61,272 + 20,000 = 81,272 < 90,000."""
    verdict = _assess(_context(snapshot, constraints=NO_NEW_CARDS))
    assert verdict.feasible is False
    assert verdict.best_case_miles == 81_272
    assert verdict.gap_miles == 8_728


def test_golden_tight_when_buffer_missed(snapshot: CatalogSnapshot) -> None:
    """travel 49k: 8 × (8,158.5 + 999) = 73,260 + 20,000 = 93,260 —
    clears 90,000 but not 94,500 ⇒ feasible AND tight (Stage 6 failure
    scenario: 'narrate as tight, not certain')."""
    verdict = _assess(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 49_000, SpendCategory.DINING: 30_000},
            constraints=NO_NEW_CARDS,
        )
    )
    assert verdict.feasible is True
    assert verdict.best_case_miles == 93_260
    assert verdict.tight is True


# ── Portfolio assessment ──────────────────────────────────────────────────


def test_golden_portfolio_assessment(snapshot: CatalogSnapshot) -> None:
    """current_capability is always wallet-only (even when acquisitions are
    allowed); balances convert at actual ratios into every linked program."""
    verdict = _assess(_context(snapshot))
    portfolio = verdict.portfolio
    assert portfolio.current_capability_miles == 81_272
    assert portfolio.reward_gap_miles == 90_000 - 81_272
    assert portfolio.convertible_balances_by_program == {
        "KrisFlyer": 20_000,  # 1:1
        "Maharaja Club": 10_000,  # 2:1
        "Marriott Bonvoy": 10_000,  # 2:1
        "ALL - Accor Live Limitless": 10_000,  # 2:1
    }
    assert portfolio.strengths  # deterministic, non-empty for a linked wallet


# ── Adjustment options (the inverse problems) ─────────────────────────────


def test_golden_adjustment_options_wallet_only(snapshot: CatalogSnapshot) -> None:
    """Infeasible 81,272 vs 90,000. Every option is computed, not narrated:
    extend  : H×7,659 + 20,000 ≥ 90,000 → H=10 (96,590; H=9 gives 88,931)
    add_card: best single acquisition = Burgundy → 108,320
    raise   : +₹10,000/mo travel → +8×1,665 = +13,320 → 94,592
    downgrade: economy = 19,000×2 = 38,000 ≤ 81,272 (bound unchanged)
    """
    verdict = _assess(_context(snapshot, constraints=NO_NEW_CARDS))
    by_kind = {option.kind: option for option in verdict.adjustment_options}
    assert list(by_kind) == ["extend_timeline", "add_card", "raise_spend", "downgrade_cabin"]

    extend = by_kind["extend_timeline"]
    assert extend.extend_to_months == 10
    assert extend.resulting_best_case_miles == 96_590

    add = by_kind["add_card"]
    assert add.add_card_id == seed_id("card", "axis-magnus-burgundy")
    assert add.resulting_best_case_miles == 108_320

    raise_opt = by_kind["raise_spend"]
    assert raise_opt.raise_category_slug == SpendCategory.TRAVEL.value
    assert raise_opt.raise_spend_by_inr == 10_000
    assert raise_opt.resulting_best_case_miles == 94_592

    downgrade = by_kind["downgrade_cabin"]
    assert downgrade.downgrade_cabin_to == "economy"
    assert downgrade.resulting_best_case_miles == 81_272


def test_golden_atlas_transfer_cap_bounds_the_goal(snapshot: CatalogSnapshot) -> None:
    """Atlas-only wallet, travel ₹1L/mo: earn 40,000 EM + 5,000 milestone
    bonuses (3L and 7.5L annual tiers on ₹8L cumulative), but the link cap is
    30,000 EM/year → exactly 60,000 miles. Consequences the options must get
    right: extending the timeline can NEVER fix a saturated cap (no option),
    raising spend can't either (no option); adding Burgundy can (its own 2L
    cap → 200,000 × 4/5 = 160,000)."""
    verdict = _assess(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 100_000},
            wallet={"axis-atlas": 0},
            constraints=NO_NEW_CARDS,
        )
    )
    assert verdict.feasible is False
    assert verdict.best_case_miles == 60_000
    kinds = [option.kind for option in verdict.adjustment_options]
    assert "extend_timeline" not in kinds
    assert "raise_spend" not in kinds
    add = next(o for o in verdict.adjustment_options if o.kind == "add_card")
    assert add.add_card_id == seed_id("card", "axis-magnus-burgundy")
    assert add.resulting_best_case_miles == 160_000


def test_add_card_never_proposes_discontinued_atlas(snapshot: CatalogSnapshot) -> None:
    """Atlas is acquirable: false — no adjustment option may recommend it."""
    verdict = _assess(_context(snapshot, wallet={"hdfc-regalia-gold": 0}, constraints=NO_NEW_CARDS))
    atlas = seed_id("card", "axis-atlas")
    assert all(option.add_card_id != atlas for option in verdict.adjustment_options)


def test_golden_sbi_wallet_infeasible_with_computed_fixes(
    snapshot: CatalogSnapshot,
) -> None:
    """SBI-only wallet: zero opportunities → capability 0; with acquisitions
    allowed the bound is Burgundy routing = 88,320, just short of 90,000.
    Single-change fixes the engine must find:
      extend to 9 months: 9 × 13,800 = 124,200 pts × 4/5 = 99,360 ✓
      raise travel +10k:  8 × 16,800 = 134,400 pts × 4/5 = 107,520 ✓
      downgrade economy:  38,000 ≤ 88,320 ✓
    No add_card option — acquisitions were never blocked (already counted)."""
    verdict = _assess(_context(snapshot, wallet={"sbi-cashback": 50_000}))
    assert verdict.feasible is False
    assert verdict.best_case_miles == 88_320
    assert verdict.portfolio.current_capability_miles == 0
    by_kind = {option.kind: option for option in verdict.adjustment_options}
    assert list(by_kind) == ["extend_timeline", "raise_spend", "downgrade_cabin"]
    assert by_kind["extend_timeline"].extend_to_months == 9
    assert by_kind["extend_timeline"].resulting_best_case_miles == 99_360
    assert by_kind["raise_spend"].raise_spend_by_inr == 10_000
    assert by_kind["raise_spend"].resulting_best_case_miles == 107_520
    assert by_kind["downgrade_cabin"].resulting_best_case_miles == 88_320


def test_max_annual_fee_constraint_excludes_expensive_cards(snapshot: CatalogSnapshot) -> None:
    """max_annual_fees 10,000 removes Burgundy (30,000) from the acquirable
    set: best routing falls back to wallet Infinia rates + nothing better →
    the unconstrained 108,320 must NOT appear."""
    verdict = _assess(_context(snapshot, constraints=ConstraintSet(max_annual_fees_inr=10_000)))
    assert verdict.best_case_miles < 108_320


def test_determinism(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot, constraints=NO_NEW_CARDS)
    a = assess_feasibility(enumerate_opportunities(context), context)
    b = assess_feasibility(enumerate_opportunities(context), context)
    assert a == b


@pytest.mark.parametrize("feasible_case", [True, False])
def test_gap_sign_convention(snapshot: CatalogSnapshot, feasible_case: bool) -> None:
    """gap_miles = required − best_case: ≤ 0 exactly when feasible."""
    constraints = ConstraintSet() if feasible_case else NO_NEW_CARDS
    verdict = _assess(_context(snapshot, constraints=constraints))
    assert verdict.feasible is feasible_case
    assert (verdict.gap_miles <= 0) is feasible_case


def test_bound_is_exact_decimal_not_float(snapshot: CatalogSnapshot) -> None:
    """travel 49k → 8,158.50 pts/mo must accumulate exactly (73,260 + 20,000
    = 93,260) — a float path would drift off this integer."""
    verdict = _assess(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 49_000, SpendCategory.DINING: 30_000},
            constraints=NO_NEW_CARDS,
        )
    )
    assert verdict.best_case_miles == 93_260
    assert Decimal(verdict.best_case_miles) == Decimal("93260")


def test_golden_bound_floors_never_rounds_the_conversion(snapshot: CatalogSnapshot) -> None:
    """The bound's final conversion must FLOOR, not round — an optimistic
    bound that rounds up could pass a goal the whole-block projector can't
    reach. travel 40k / dining 30,200 both route to Burgundy:
        8 × (40,000×30 + 30,200×6)/100 = 110,496 pts (≡ 1 mod 5)
        × 4/5 = 88,396.8 → floor 88,396 (round would give 88,397)
        + Infinia balance 20,000 (1:1) = 108,396."""
    verdict = _assess(
        _context(snapshot, spend={SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_200})
    )
    assert verdict.best_case_miles == 108_396  # 88,396 (floored) + 20,000, NOT 108,397
