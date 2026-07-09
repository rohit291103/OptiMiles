"""Stage 4 — Planning Context Assembly.

Composes *user* state (wallet, spend profile, constraints) with the pinned
catalog snapshot and the resolved goal + requirement into one frozen
`PlanningContext` — the sole input to the deterministic core (Stages 5–9).

Two things this stage owns, both blueprint-mandated:

- **Defaults are flagged, never silent.** A caller who gives no spend profile
  gets `DEFAULT_SPEND_PROFILE` with `assumed=True`, so narration can say
  "based on a typical ₹X/month profile — adjust it for a sharper plan"
  (blueprint Stage 4). An empty wallet is a *valid* context: Stage 6 declares
  infeasibility with the obvious fix, it is never an error here.
- **Horizon is derived, not passed.** Months from `today` to the goal's
  `target_date`, rounded UP (a partial final month is still a month the user
  can earn in) and floored at 1 — a same-month target still gets one tick.

Pure and deterministic: no DB, no LLM. The orchestrator hands it already-loaded
user state; this function only shapes it. Flow B (simulation replay) calls this
directly with an edited spend profile to build a *new* context — contexts are
never mutated.
"""

from datetime import date

from app.domain import (
    ConstraintSet,
    PlanningContext,
    RewardRequirement,
    SpendCategory,
    SpendProfile,
    SpendProfileItem,
    TravelGoal,
    WalletCard,
)
from app.domain.catalog import CatalogSnapshot

# A neutral "typical spender" template (blueprint Stage 4: "default spend
# profile template ... every default flagged assumed"). Config, not truth —
# the moment a caller supplies a profile this is not used. Kept modest and
# spread across the earn-heavy categories so a bare goal still produces a
# meaningful, non-trivial plan the user can then refine.
DEFAULT_SPEND_PROFILE: tuple[tuple[SpendCategory, int], ...] = (
    (SpendCategory.TRAVEL, 25_000),
    (SpendCategory.DINING, 20_000),
    (SpendCategory.ONLINE, 20_000),
    (SpendCategory.GROCERIES, 15_000),
    (SpendCategory.UTILITIES, 10_000),
)


def default_spend_profile() -> SpendProfile:
    """The assumed template applied when a caller supplies no spend profile."""
    return SpendProfile(
        items=tuple(
            SpendProfileItem(category_slug=category, monthly_spend_inr=amount)
            for category, amount in DEFAULT_SPEND_PROFILE
        ),
        assumed=True,
    )


def horizon_months(target_date: date, today: date) -> int:
    """Whole months from today to the target, rounded UP, floored at 1.

    A goal due mid-month still gives the user that month to earn in, and a
    target on or before today collapses to a single simulated tick rather than
    a zero-length (and therefore un-simulatable) horizon.
    """
    months = (target_date.year - today.year) * 12 + (target_date.month - today.month)
    if target_date.day > today.day:
        months += 1
    return max(1, months)


def assemble_context(
    goal: TravelGoal,
    requirement: RewardRequirement,
    snapshot: CatalogSnapshot,
    *,
    wallet: tuple[WalletCard, ...],
    spend_profile: SpendProfile | None,
    constraints: ConstraintSet | None,
    today: date,
) -> PlanningContext:
    return PlanningContext(
        user_id=goal.user_id,
        goal=goal,
        requirement=requirement,
        snapshot=snapshot,
        wallet=wallet,
        spend_profile=spend_profile if spend_profile is not None else default_spend_profile(),
        horizon_months=horizon_months(goal.target_date, today),
        constraints=constraints if constraints is not None else ConstraintSet(),
    )
