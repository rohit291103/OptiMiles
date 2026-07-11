"""The persistence seam (repositories/results.py) against a capturing fake
connection — no live DB.

We can't run this against Postgres in this phase (persistence needs a real
`users → auth.users` row, which only Supabase auth mints), so instead we
capture every bound-parameter dict and assert the parts a real Postgres would
enforce: the FK write ORDER, closed CHECK-constraint values land in-set, enum
`.value` coercions don't raise, the infeasible path skips the result row, and
`confidence_score`/`optimization_score` stay in their documented ranges. A real
DB test lands in Phase 7 once auth can provide a user.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.domain import (
    CatalogSnapshot,
    ConstraintSet,
    FinalRecommendation,
    SpendProfile,
    SpendProfileItem,
    WalletCard,
)
from app.domain.enums import SpendCategory
from app.knowledge.requirements import estimate_requirement
from app.knowledge.seed_catalog import seed_id
from app.optimization.ranking import load_ranking_weights
from app.pipeline.context import assemble_context
from app.pipeline.run import run_from_context
from app.repositories.results import delete_goal_lineage, persist_recommendation
from tests.unit.pipeline.helpers import make_goal

TODAY = date(2026, 7, 4)
WEIGHTS = load_ranking_weights(Path("config/ranking-weights-v1.yaml"))

# The closed CHECK sets the schema enforces (0001_initial_schema.py).
_GOAL_TYPES = {"flight", "hotel", "custom"}
_GOAL_STATUSES = {"active", "achieved", "abandoned", "paused"}
_CABINS = {"economy", "premium_economy", "business", "first"}
_REC_TYPES = {
    "spend_routing",
    "card_suggestion",
    "transfer_timing",
    "goal_feasibility",
    "milestone_alert",
}
_SIM_STATUSES = {"draft", "computing", "completed", "stale"}


class CapturingConn:
    """A fake AsyncConnection that records (sql, params) instead of executing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement: object, params: dict) -> None:
        self.calls.append((str(statement), params))

    def table_of(self, index: int) -> str:
        """The target table of the INSERT at call `index`."""
        sql = self.calls[index][0]
        for table in (
            "user_goals",
            "spend_simulations",
            "simulation_results",
            "recommendation_outputs",
        ):
            if f"INTO {table}" in sql:
                return table
        return "?"


async def _feasible_recommendation(snapshot: CatalogSnapshot) -> FinalRecommendation:
    goal = make_goal(snapshot, today=TODAY)
    context = assemble_context(
        goal,
        estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot,
        wallet=(
            WalletCard(card_id=seed_id("card", "hdfc-infinia"), current_points_balance=20_000),
        ),
        spend_profile=SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.TRAVEL, monthly_spend_inr=60_000),
                SpendProfileItem(category_slug=SpendCategory.DINING, monthly_spend_inr=40_000),
            )
        ),
        constraints=None,
        today=TODAY,
    )
    return await run_from_context(context, weights=WEIGHTS, model=None)


async def _infeasible_recommendation(snapshot: CatalogSnapshot) -> FinalRecommendation:
    goal = make_goal(snapshot, today=TODAY)
    context = assemble_context(
        goal,
        estimate_requirement(goal, snapshot, buffer_pct=5.0),
        snapshot,
        wallet=(),
        spend_profile=SpendProfile(
            items=(
                SpendProfileItem(category_slug=SpendCategory.UTILITIES, monthly_spend_inr=1_000),
            )
        ),
        constraints=ConstraintSet(no_new_cards=True),
        today=TODAY,
    )
    return await run_from_context(context, weights=WEIGHTS, model=None)


async def test_feasible_persists_full_lineage_in_fk_order(
    snapshot: CatalogSnapshot,
) -> None:
    rec = await _feasible_recommendation(snapshot)
    assert rec.recommended is not None  # precondition for this test

    conn = CapturingConn()
    ids = await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]

    # Four inserts, in FK-dependency order.
    assert [conn.table_of(i) for i in range(4)] == [
        "user_goals",
        "spend_simulations",
        "simulation_results",
        "recommendation_outputs",
    ]
    assert set(ids) == {"goal_id", "simulation_id", "result_id", "recommendation_id"}


async def test_check_constraint_values_are_in_set(snapshot: CatalogSnapshot) -> None:
    rec = await _feasible_recommendation(snapshot)
    conn = CapturingConn()
    await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]

    goal_params = conn.calls[0][1]
    assert goal_params["goal_type"] in _GOAL_TYPES
    assert goal_params["status"] in _GOAL_STATUSES
    assert goal_params["cabin_class"] in _CABINS
    assert goal_params["target_miles"] > 0

    rec_params = conn.calls[3][1]
    assert rec_params["rec_type"] in _REC_TYPES
    # feasible ⇒ spend_routing; confidence in [0, 1]; score column in [0, 100].
    assert rec_params["rec_type"] == "spend_routing"
    assert Decimal("0") <= Decimal(rec_params["confidence"]) <= Decimal("1")
    result_params = conn.calls[2][1]
    assert Decimal("0") <= Decimal(result_params["score"]) <= Decimal("100")
    # monthly figures are per-month averages, not cumulative totals.
    assert Decimal(result_params["miles"]) <= rec.recommended.simulation.miles_at_target_date  # type: ignore[union-attr]


async def test_infeasible_skips_result_row_and_confidence(
    snapshot: CatalogSnapshot,
) -> None:
    rec = await _infeasible_recommendation(snapshot)
    assert rec.recommended is None  # precondition

    conn = CapturingConn()
    ids = await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]

    # No simulation_results row: goal, simulation, recommendation only.
    assert [conn.table_of(i) for i in range(3)] == [
        "user_goals",
        "spend_simulations",
        "recommendation_outputs",
    ]
    assert "result_id" not in ids
    rec_params = conn.calls[2][1]
    assert rec_params["rec_type"] == "goal_feasibility"
    assert rec_params["result_id"] is None
    assert rec_params["confidence"] is None


async def test_spend_simulation_status_is_valid(snapshot: CatalogSnapshot) -> None:
    """The simulation row's status must be a CHECK-valid value ('completed')."""
    rec = await _feasible_recommendation(snapshot)
    conn = CapturingConn()
    await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]
    sim_sql = conn.calls[1][0]
    assert any(status in sim_sql for status in _SIM_STATUSES)


# ── The persisted "story" (per-category detail + breakdown + tiers) ─────────
#
# These extra fields ride inside the existing card_allocations JSONB (no schema
# migration): the story a saved goal must reconstruct to match the live
# simulator — per-category earn detail, the 6-part score breakdown, the
# recommended strategy's headline, and a compact list of the alternative tiers.


async def test_persists_allocation_details_and_score_story(
    snapshot: CatalogSnapshot,
) -> None:
    rec = await _feasible_recommendation(snapshot)
    assert rec.recommended is not None
    assert rec.recommended.allocation_details  # precondition: engine produced them

    conn = CapturingConn()
    await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]

    allocations = json.loads(conn.calls[2][1]["allocations"])

    # Per-category earn detail is persisted, one row per allocated category,
    # each carrying the rate/effective/points the UI shows.
    details = allocations["allocation_details"]
    assert len(details) == len(rec.recommended.allocation_details)
    sample = details[0]
    assert {"category_slug", "card_id", "monthly_spend_inr", "earn_rate",
            "effective_miles_per_100inr", "monthly_points", "notes"} <= set(sample)

    # The 6-part score breakdown survives (was previously dropped).
    breakdown = allocations["score_breakdown"]
    assert set(breakdown) == {
        "goal_achievement", "efficiency", "cost", "simplicity",
        "portfolio_utilization", "risk",
    }
    assert allocations["headline_differentiator"] == rec.recommended.headline_differentiator


async def test_persists_alternative_tiers(snapshot: CatalogSnapshot) -> None:
    """The alternatives (the 'your cards → +1 → +2' story) are persisted as a
    compact tier list — enough to render the comparison, not full simulations."""
    rec = await _feasible_recommendation(snapshot)
    assert rec.recommended is not None

    conn = CapturingConn()
    await persist_recommendation(conn, rec, user_id=uuid4())  # type: ignore[arg-type]
    allocations = json.loads(conn.calls[2][1]["allocations"])

    tiers = allocations["strategy_options"]
    # Recommended + every alternative, each a compact summary.
    assert len(tiers) == 1 + len(rec.alternatives)
    first = tiers[0]
    assert {"headline_differentiator", "miles_at_target_date", "total_fees_inr",
            "cards_to_acquire", "is_recommended"} <= set(first)
    assert first["is_recommended"] is True
    if len(tiers) > 1:
        assert tiers[1]["is_recommended"] is False

    # The persisted tier numbers must be exactly the recommended strategy's
    # simulated figures (not recomputed) — golden traceable to `rec`.
    assert first["miles_at_target_date"] == rec.recommended.simulation.miles_at_target_date
    assert first["total_fees_inr"] == rec.recommended.simulation.total_fees_inr
    assert first["headline_differentiator"] == rec.recommended.headline_differentiator
    assert first["score"] == str(rec.recommended.score)


# ── delete_goal_lineage (behind DELETE /goals/{id}) ─────────────────────────
#
# The FKs pointing at user_goals (0001) are ON DELETE SET NULL from
# spend_simulations/recommendation_outputs but NO ACTION from
# simulation_results.goal_id — a bare goal delete would strand rows or be
# rejected. The delete must therefore remove the whole lineage explicitly,
# child-first, inside the caller's transaction — and stay scoped to the
# caller's user_id throughout (simulation_results has no user_id column, so
# its statement scopes through the goal's ownership via USING user_goals).


class DeletingConn:
    """Records (sql, params) and reports a configurable rowcount for the
    final user_goals delete (0 ⇒ unknown or foreign goal)."""

    def __init__(self, goal_rowcount: int) -> None:
        self._goal_rowcount = goal_rowcount
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement: object, params: dict) -> object:
        sql = str(statement)
        self.calls.append((sql, params))

        class _Result:
            rowcount = self._goal_rowcount if "FROM user_goals" in sql else 0

        return _Result()


async def test_delete_removes_lineage_child_first_and_scopes_every_statement() -> None:
    """Order: recommendation_outputs → simulation_results (explicit — its
    goal_id FK is NO ACTION, and the cascade from spend_simulations only
    covers it when the two goal_ids agree) → spend_simulations → user_goals;
    every DELETE binds BOTH ids so the operation can never touch another
    user's rows."""
    user_id, goal_id = uuid4(), uuid4()
    conn = DeletingConn(goal_rowcount=1)
    deleted = await delete_goal_lineage(conn, user_id=user_id, goal_id=goal_id)  # type: ignore[arg-type]

    assert deleted is True
    tables = [
        table
        for sql, _ in conn.calls
        for table in (
            "recommendation_outputs",
            "simulation_results",
            "spend_simulations",
            "user_goals",
        )
        if f"FROM {table}" in sql
    ]
    assert tables == [
        "recommendation_outputs",
        "simulation_results",
        "spend_simulations",
        "user_goals",
    ]
    for sql, params in conn.calls:
        assert sql.lstrip().upper().startswith("DELETE")
        assert params == {"user_id": user_id, "goal_id": goal_id}
        assert ":user_id" in sql and ":goal_id" in sql


async def test_delete_returns_false_when_goal_missing_or_foreign() -> None:
    """No user_goals row deleted (unknown id, or someone else's goal) ⇒ False,
    for the API's 404 — deliberately indistinguishable, like the reads."""
    conn = DeletingConn(goal_rowcount=0)
    deleted = await delete_goal_lineage(conn, user_id=uuid4(), goal_id=uuid4())  # type: ignore[arg-type]
    assert deleted is False
