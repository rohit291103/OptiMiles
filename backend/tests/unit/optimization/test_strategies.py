"""Stage 7 — candidate strategy generation over the real seed catalog.

Archetypes are different STARTING POINTS of the same honest allocator
(hill-climb on the cap/milestone-aware bound), so candidates are local optima
of different basins — explainably different plans, never overstated ones.
Validation failures discard a candidate, never patch it silently (BR-05).

Default fixture: wallet Infinia (20,000 pts), travel 40k + dining 30k /
month, horizon 8, required 90,000. Hand-computed claims:

  status_quo (all spend on Infinia, transfer cutoff month 6 = 8−1−ceil(10/30)):
      pts@6 = 20,000 + 7 × (6,660 + 999) = 73,613 → 1:1 = 73,613 miles

  one_new_card (Burgundy; travel 30 pts/₹100, dining 6, cutoff 6 = 8−1−ceil(3/30)):
      Burgundy pts@6 = 7 × 13,800 = 96,600 ≤ 2L cap
        whole blocks of 5 → 96,600 sent → × 4/5 = 77,280 miles
      + idle Infinia balance 20,000 (1:1)             = 97,280 miles
      improvement 97,280 > 73,613 × 1.05 → meaningful (BR-02) ✓
"""

from datetime import date
from uuid import UUID, uuid4

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    GoalResolution,
    ParsedGoalIntent,
    PlanningContext,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    StrategyArchetype,
    TravelGoal,
    WalletCard,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.feasibility import assess_feasibility
from app.optimization.strategies import generate_candidates
from app.valuation.opportunities import enumerate_opportunities

TODAY = date(2026, 7, 4)


def _context(
    snapshot: CatalogSnapshot,
    spend: dict[SpendCategory, int] | None = None,
    wallet: dict[str, int] | None = None,
    horizon_months: int = 8,
    constraints: ConstraintSet | None = None,
    num_passengers: int = 2,
) -> PlanningContext:
    intent = ParsedGoalIntent(
        origin_city="Hyderabad",
        destination_city="Singapore",
        cabin_class="business",
        timeline_months=horizon_months,
        num_passengers=num_passengers,
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


def _generate(context: PlanningContext) -> tuple:
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    return generate_candidates(opportunities, verdict, context)


def _card(slug: str) -> UUID:
    return seed_id("card", slug)


NO_NEW_CARDS = ConstraintSet(no_new_cards=True)


# ── Default fixture: archetype composition and golden claims ──────────────


def test_status_quo_always_first_and_default_fixture_shape(
    snapshot: CatalogSnapshot,
) -> None:
    """BR-01: the existing-portfolio strategy is always generated first.
    On this fixture the other archetypes collapse into two distinct plans
    (1–2 candidates is a valid outcome for small wallets)."""
    candidates = _generate(_context(snapshot))
    assert len(candidates) == 2
    assert candidates[0].archetype == StrategyArchetype.STATUS_QUO_OPTIMIZED
    assert candidates[0].cards_to_acquire == ()
    assert candidates[1].archetype == StrategyArchetype.ONE_NEW_CARD
    assert candidates[0].strategy_id == "status_quo_optimized-1"
    assert candidates[1].strategy_id == "one_new_card-1"


def test_golden_status_quo_claim(snapshot: CatalogSnapshot) -> None:
    status_quo = _generate(_context(snapshot))[0]
    assert status_quo.spend_allocation == {
        SpendCategory.TRAVEL: _card("hdfc-infinia"),
        SpendCategory.DINING: _card("hdfc-infinia"),
    }
    assert status_quo.claimed_total_miles == 73_613
    (transfer,) = status_quo.transfer_plan
    assert transfer.from_card_id == _card("hdfc-infinia")
    assert transfer.to_partner_id == seed_id("partner", "krisflyer")
    assert transfer.points == 73_613
    assert transfer.planned_month == 6  # 8 − 1 − ceil(10 days / 30)


def test_golden_one_new_card_burgundy(snapshot: CatalogSnapshot) -> None:
    """The acquisition candidate routes both categories to Burgundy AND still
    transfers the idle Infinia balance — the wallet keeps working."""
    candidate = _generate(_context(snapshot))[1]
    assert candidate.cards_to_acquire == (_card("axis-magnus-burgundy"),)
    assert candidate.claimed_total_miles == 97_280
    assert set(candidate.cards_used) == {_card("axis-magnus-burgundy"), _card("hdfc-infinia")}
    points_by_card = {t.from_card_id: t.points for t in candidate.transfer_plan}
    assert points_by_card == {
        _card("axis-magnus-burgundy"): 96_600,
        _card("hdfc-infinia"): 20_000,
    }
    assert all(t.planned_month == 6 for t in candidate.transfer_plan)


def test_one_new_card_only_meaningful_improvements(snapshot: CatalogSnapshot) -> None:
    """BR-02: HSBC/Regalia/Amex additions don't beat the wallet's own rates —
    Burgundy is the only justifiable acquisition on this fixture."""
    candidates = _generate(_context(snapshot))
    acquiring = [c for c in candidates if c.cards_to_acquire]
    assert {card for c in acquiring for card in c.cards_to_acquire} == {
        _card("axis-magnus-burgundy")
    }


# ── The Phase 4 requirement: discontinued cards are never acquired ────────


def test_atlas_is_never_recommended_for_acquisition(snapshot: CatalogSnapshot) -> None:
    """Atlas (acquirable: false) must not appear in cards_to_acquire even
    when its 1:2 KrisFlyer ratio would look attractive."""
    atlas = _card("axis-atlas")
    for context in (
        _context(snapshot),
        _context(snapshot, spend={SpendCategory.TRAVEL: 100_000}),
        _context(snapshot, wallet={"hdfc-regalia-gold": 0}),
    ):
        for candidate in _generate(context):
            assert atlas not in candidate.cards_to_acquire


def test_atlas_in_wallet_is_still_used(snapshot: CatalogSnapshot) -> None:
    """Existing holders keep the card: in-wallet Atlas may be allocated.
    (1 passenger = 45,000 required — within Atlas's 60,000-mile cap ceiling.)"""
    candidates = _generate(
        _context(
            snapshot,
            wallet={"axis-atlas": 10_000},
            constraints=NO_NEW_CARDS,
            num_passengers=1,
        )
    )
    assert candidates
    assert all(c.cards_used == (_card("axis-atlas"),) for c in candidates)


# ── Constraints (BR-03/BR-04: user constraints are never violated) ────────


def test_no_new_cards_constraint(snapshot: CatalogSnapshot) -> None:
    wallet_card = _card("hdfc-infinia")
    for candidate in _generate(_context(snapshot, constraints=NO_NEW_CARDS)):
        assert candidate.cards_to_acquire == ()
        assert set(candidate.cards_used) == {wallet_card}


def test_max_annual_fee_constraint(snapshot: CatalogSnapshot) -> None:
    """Fee cap 10,000 removes Burgundy (30,000) and Plat Charge (66,000).
    Travel raised to 60k so the wallet alone clears the gate (8 × 10,989 +
    20,000 = 107,912 ≥ 90,000). The affordable additions (DCB ties Infinia's
    rates; Amex PT's milestone play claims 99,530 < 96,923 × 1.05) all fail
    BR-02 → the wallet plan is the only candidate, and nothing acquires."""
    candidates = _generate(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 60_000, SpendCategory.DINING: 30_000},
            constraints=ConstraintSet(max_annual_fees_inr=10_000),
        )
    )
    assert [c.archetype for c in candidates] == [StrategyArchetype.STATUS_QUO_OPTIMIZED]
    assert candidates[0].cards_to_acquire == ()
    assert candidates[0].claimed_total_miles == 96_923  # 20,000 + 7 × 10,989


# ── Adversarial allocation cases (build-plan Phase 4 exit criteria) ───────


def test_golden_milestone_diversion_beats_rate_greedy(snapshot: CatalogSnapshot) -> None:
    """Watchout #3, milestone side. Wallet DCB + Burgundy, dining ₹140k/mo:
    pure rate-greedy sends dining to Burgundy (4.8 > 3.33 miles/₹100), but
    diverting it to DCB crosses the ₹4L quarterly milestone twice before the
    month-6 transfer cutoff:

      DCB pts@6   = 7 × 4,662 + 20,000 (fires m2, m5)      = 52,634 → 52,634
      Burgundy@6  = 7 × 12,000 = 84,000 → blocks ×4/5      = 67,200
      claimed     = 119,834   (rate-greedy would claim only 114,240)
    """
    candidates = _generate(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 140_000},
            wallet={"hdfc-diners-black": 0, "axis-magnus-burgundy": 0},
            constraints=NO_NEW_CARDS,
        )
    )
    status_quo = candidates[0]
    assert status_quo.spend_allocation == {
        SpendCategory.TRAVEL: _card("axis-magnus-burgundy"),
        SpendCategory.DINING: _card("hdfc-diners-black"),
    }
    assert status_quo.claimed_total_miles == 119_834
    milestone_months = sorted(m.expected_month for m in status_quo.expected_milestones)
    assert milestone_months == [2, 5]
    assert all(m.bonus_points == 10_000 for m in status_quo.expected_milestones)


def test_golden_cap_saturation_reroutes_spend(snapshot: CatalogSnapshot) -> None:
    """Watchout #3, cap side. Wallet Infinia (20k) + Burgundy, travel ₹1L/mo:
    all-on-Burgundy saturates its 2L annual transfer cap (7 × 31,800 =
    222,600 pts, 22,600 wasted). Rerouting dining to Infinia is worth more:

      Burgundy travel-only @6 = 210,000 → capped 200,000 → 160,000 miles
      Infinia dining @6       = 20,000 + 7 × 999 = 26,993 → 26,993 miles
      claimed = 186,993   (naïve all-on-Burgundy claims only 180,000)

    The capped transfer plan must send exactly 200,000 points — never more.
    """
    candidates = _generate(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 100_000, SpendCategory.DINING: 30_000},
            wallet={"hdfc-infinia": 20_000, "axis-magnus-burgundy": 0},
            constraints=NO_NEW_CARDS,
        )
    )
    status_quo = candidates[0]
    assert status_quo.spend_allocation == {
        SpendCategory.TRAVEL: _card("axis-magnus-burgundy"),
        SpendCategory.DINING: _card("hdfc-infinia"),
    }
    assert status_quo.claimed_total_miles == 186_993
    points_by_card = {t.from_card_id: t.points for t in status_quo.transfer_plan}
    assert points_by_card[_card("axis-magnus-burgundy")] == 200_000

    simplest = next(c for c in candidates if c.archetype == StrategyArchetype.SIMPLEST_VIABLE)
    assert simplest.cards_used == (_card("axis-magnus-burgundy"),)
    assert simplest.claimed_total_miles == 160_000  # clears 90,000 with one card, no
    # idle-balance transfer: fewest actions, honestly fewer miles


# ── Cheapest viable (always tries the cheapest acquisition, not just the
# highest-earning one — every archetype above optimizes for miles; without
# this one, a card like Magnus (₹30,000) can shadow out cards like Diners
# Club (₹10,000) that would ALSO clear the goal, and a cost-conscious user
# never sees the cheap option even exists) ─────────────────────────────────


def test_cheapest_viable_tries_every_acquirable_card_not_just_the_best_rate(
    snapshot: CatalogSnapshot,
) -> None:
    """1 passenger, empty wallet, horizon 12 (required 45,000): Diners Club
    Black Metal (₹10,000 fee) alone clears the goal at 84,249 miles — far
    cheaper than Magnus (₹30,000, 121,440 miles). Hand-computed:

      DCB solo (travel 16.65×, dining 3.33×, transfer cutoff month 10):
      claim@10 = 10 × (40,000×0.1665 + 30,000×0.0333) = 10 × 8,424.9 → 84,249

    Without the cheapest-viable search this candidate simply would not exist
    on fixtures where hill-climbing from every OTHER basin also converges
    away from it — proven by the sibling test below, which asserts the exact
    opposite absence on the default (higher-required) fixture. On THIS
    fixture, DCB also happens to be `one_new_card`'s best-3rd-by-claim pick
    (dedup keeps first-in, so the surviving candidate may carry either
    label) — what matters is that the cheap, goal-clearing option is never
    silently dropped, which is exactly what BR-02 did before this change
    (DCB alone doesn't beat an empty-wallet baseline by 5%... except an
    empty baseline is 0, so BR-02 was accidentally toothless here; the
    non-empty-wallet sibling test below is the one that actually exercises
    the BR-02 exemption)."""
    candidates = _generate(
        _context(
            snapshot,
            spend={SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000},
            wallet={},
            horizon_months=12,
            num_passengers=1,
        )
    )
    dcb = next(
        (c for c in candidates if c.cards_to_acquire == (_card("hdfc-diners-black"),)), None
    )
    assert dcb is not None
    assert dcb.cards_used == (_card("hdfc-diners-black"),)
    assert dcb.claimed_total_miles == 84_249
    assert dcb.spend_allocation == {
        SpendCategory.TRAVEL: _card("hdfc-diners-black"),
        SpendCategory.DINING: _card("hdfc-diners-black"),
    }
    (transfer,) = dcb.transfer_plan
    assert transfer.points == 84_249
    assert transfer.planned_month == 10

    # Magnus (₹30,000) also clears this fixture at a higher claim — both must
    # coexist as distinct options, not have the cheap one pruned away.
    acquired_cards = {c.cards_to_acquire[0] for c in candidates if len(c.cards_to_acquire) == 1}
    assert {_card("hdfc-diners-black"), _card("axis-magnus-burgundy")} <= acquired_cards


def test_cheapest_viable_survives_br02_when_the_wallet_baseline_is_already_strong(
    snapshot: CatalogSnapshot,
) -> None:
    """The bug this whole archetype exists to fix: with a strong wallet
    (Infinia + Atlas), status quo alone already claims 59,565 — so Diners
    Club Black Metal's 51,282-mile claim (still clearing the 45,000 target)
    FAILS one_new_card's ≥5%-over-baseline gate (BR-02) and would vanish
    without the cheapest_viable exemption, leaving Magnus (₹30,000) as the
    only acquisition a user ever sees, even though a ₹10,000 card also
    works. Hand-computed: DCB solo, travel 16.65×/dining 3.33×/online
    3.33×/groceries 3.33×/utilities 3.33×, cutoff month 6 (8−1−ceil(10/30)):
      pts@6 = 7 × (30,000×.1665 + 20,000×.0333×3 + 15,000×.0333)
            = 7 × (4,995 + 1,998 + 499.5) → floored per-month = 7 × 7,326 = 51,282
    """
    candidates = _generate(
        _context(
            snapshot,
            spend={
                SpendCategory.TRAVEL: 30_000,
                SpendCategory.DINING: 20_000,
                SpendCategory.ONLINE: 20_000,
                SpendCategory.GROCERIES: 15_000,
                SpendCategory.UTILITIES: 15_000,
            },
            wallet={"hdfc-infinia": 0, "axis-atlas": 0},
            horizon_months=8,
            num_passengers=1,
        )
    )
    dcb = next(
        (c for c in candidates if c.cards_to_acquire == (_card("hdfc-diners-black"),)), None
    )
    assert dcb is not None
    assert dcb.claimed_total_miles == 51_282
    assert dcb.claimed_total_miles >= 45_000  # clears the goal despite not beating baseline+5%


def test_cheapest_viable_absent_when_no_single_new_card_alone_clears_the_goal(
    snapshot: CatalogSnapshot,
) -> None:
    """Default fixture (required 90,000): hand-computed in this module's
    docstring-adjacent test comments, no single acquirable card alone clears
    it without hill-climbing away from itself (only Magnus + idle Infinia
    balance combined clears it) — cheapest_viable must not fabricate a
    single-card plan that doesn't actually work, and no OTHER archetype
    should have produced a single-card acquisition either."""
    candidates = _generate(_context(snapshot))
    assert not any(
        len(c.cards_to_acquire) == 1 and c.cards_used == c.cards_to_acquire for c in candidates
    )


def test_cheapest_viable_respects_no_new_cards_and_fee_cap(snapshot: CatalogSnapshot) -> None:
    """`no_new_cards` with an empty wallet leaves nothing to allocate at all.
    A ₹5,000 cap excludes DCB (₹10,000) — only HSBC/Amex Platinum Travel
    (≤₹5,000) qualify by fee, and neither alone clears this fixture's goal
    (hand-computed above: HSBC 33,000 / Amex PT 30,500 < 45,000 required) —
    so every acquiring candidate is an honest best-effort (claim short of the
    requirement, fee cap respected); cheapest/simplest_viable must not
    fabricate a goal-clearing plan."""
    fixture = dict(
        spend={SpendCategory.TRAVEL: 40_000, SpendCategory.DINING: 30_000},
        wallet={},
        horizon_months=12,
        num_passengers=1,
    )
    assert _generate(_context(snapshot, constraints=NO_NEW_CARDS, **fixture)) == ()

    capped = _context(snapshot, constraints=ConstraintSet(max_annual_fees_inr=5_000), **fixture)
    candidates = _generate(capped)
    assert candidates  # best-effort acquisitions within the cap now surface
    required = capped.requirement.miles_required_total
    fees = {
        a.card_id: a.annual_fee_inr
        for a in enumerate_opportunities(capped).card_aggregates
    }
    for candidate in candidates:
        assert sum(fees[c] for c in candidate.cards_to_acquire) <= 5_000
        assert candidate.claimed_total_miles < required


# ── Contract guarantees ───────────────────────────────────────────────────


def test_every_candidate_allocates_every_profile_category(snapshot: CatalogSnapshot) -> None:
    """BR-05: partial strategies are invalid outputs."""
    context = _context(snapshot)
    categories = {item.category_slug for item in context.spend_profile.items}
    for candidate in _generate(context):
        assert set(candidate.spend_allocation) == categories


def test_infeasible_verdict_still_generates_best_effort(snapshot: CatalogSnapshot) -> None:
    """An unreachable goal still gets candidates: the Stage-6 bound is a true
    upper bound, so every claim honestly falls short of the requirement —
    ranking can then present the least-bad route alongside the adjustment
    menu instead of returning silence."""
    context = _context(snapshot, horizon_months=2)
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    assert verdict.feasible is False
    candidates = generate_candidates(opportunities, verdict, context)
    assert candidates  # best-effort, not silence
    assert candidates[0].archetype == StrategyArchetype.STATUS_QUO_OPTIMIZED
    required = context.requirement.miles_required_total
    assert all(c.claimed_total_miles < required for c in candidates)


def test_infeasible_with_unusable_wallet_generates_nothing(snapshot: CatalogSnapshot) -> None:
    """Best-effort still requires something to allocate: a cashback-only wallet
    (zero opportunities by construction) with acquisitions forbidden yields no
    candidates — the adjustment menu alone is the honest answer."""
    context = _context(snapshot, wallet={"sbi-cashback": 0}, constraints=NO_NEW_CARDS)
    opportunities = enumerate_opportunities(context)
    verdict = assess_feasibility(opportunities, context)
    assert verdict.feasible is False
    assert generate_candidates(opportunities, verdict, context) == ()


def test_bounded_candidate_count(snapshot: CatalogSnapshot) -> None:
    """Blueprint Stage 7: 3–8 candidates bounded above; duplicates removed."""
    candidates = _generate(
        _context(snapshot, spend={SpendCategory.TRAVEL: 100_000, SpendCategory.DINING: 60_000})
    )
    assert 1 <= len(candidates) <= 8
    fingerprints = [
        (tuple(sorted(c.spend_allocation.items())), c.cards_to_acquire, c.transfer_plan)
        for c in candidates
    ]
    assert len(fingerprints) == len(set(fingerprints))


def test_determinism(snapshot: CatalogSnapshot) -> None:
    context = _context(snapshot)
    assert _generate(context) == _generate(context)
