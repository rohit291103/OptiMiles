"""The read side (repositories/saved_goals.py) against a fake connection that
returns canned rows — no live DB (same constraint as test_results.py: a real
`users → auth.users` row only exists under Supabase auth).

We assert the parts a real Postgres round-trip would otherwise prove: the query
is scoped to the caller's `user_id`, rows map onto `SavedGoalRow` faithfully,
the numeric `confidence_score` coerces to float, and a goal with no
recommendation (LEFT JOIN miss ⇒ NULLs) still lists rather than being dropped.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.repositories.saved_goals import get_saved_goal, list_saved_goals


class FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict]:
        return self._rows


class CapturingConn:
    """Records the (sql, params) and returns pre-seeded rows."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement: object, params: dict) -> FakeResult:
        self.calls.append((str(statement), params))
        return FakeResult(self._rows)


def _row(**overrides: object) -> dict:
    base = {
        "goal_id": uuid4(),
        "goal_name": "Singapore business · 8 months",
        "goal_type": "flight",
        "destination_city": "Singapore",
        "cabin_class": "business",
        "target_miles": 92_000,
        "target_date": date(2027, 3, 4),
        "status": "active",
        "created_at": datetime(2026, 7, 6, 12, 0, 0),
        "summary": "Route travel spend through HDFC Infinia to KrisFlyer.",
        "confidence_score": Decimal("0.62"),
        "catalog_snapshot_version": "cat-b63f738db960",
    }
    base.update(overrides)
    return base


async def test_query_is_scoped_to_the_caller() -> None:
    """The user_id is bound into the query — the list never spans users."""
    user_id = uuid4()
    conn = CapturingConn([_row()])
    await list_saved_goals(conn, user_id=user_id)  # type: ignore[arg-type]

    sql, params = conn.calls[0]
    assert params == {"user_id": user_id}
    assert "WHERE g.user_id = :user_id" in sql
    # Newest first, so a returning user sees their most recent goal on top.
    assert "ORDER BY g.created_at DESC" in sql


async def test_rows_map_onto_saved_goal_faithfully() -> None:
    conn = CapturingConn([_row()])
    goals = await list_saved_goals(conn, user_id=uuid4())  # type: ignore[arg-type]

    assert len(goals) == 1
    goal = goals[0]
    assert goal.destination_city == "Singapore"
    assert goal.cabin_class == "business"
    assert goal.target_miles == 92_000
    assert goal.summary == "Route travel spend through HDFC Infinia to KrisFlyer."
    # NUMERIC confidence coerces to a plain float for the JSON response.
    assert goal.confidence_score == 0.62
    assert isinstance(goal.confidence_score, float)
    assert goal.catalog_snapshot_version == "cat-b63f738db960"


async def test_goal_without_recommendation_still_lists() -> None:
    """A LEFT JOIN miss (goal saved, no recommendation row) leaves the
    recommendation fields NULL — the goal must still appear, not vanish."""
    conn = CapturingConn(
        [_row(summary=None, confidence_score=None, catalog_snapshot_version=None)]
    )
    goals = await list_saved_goals(conn, user_id=uuid4())  # type: ignore[arg-type]

    assert len(goals) == 1
    assert goals[0].summary is None
    assert goals[0].confidence_score is None


async def test_empty_when_user_has_no_goals() -> None:
    conn = CapturingConn([])
    goals = await list_saved_goals(conn, user_id=uuid4())  # type: ignore[arg-type]
    assert goals == ()


# ── get_saved_goal (the /goals/{id} detail read) ──────────────────────────


def _detail_row(**overrides: object) -> dict:
    """A full lineage row as the detail SQL would surface it — goal columns +
    latest recommendation + its simulation_results JSONB payloads, shaped
    exactly as `repositories/results.py` persists them."""
    card_id = str(uuid4())
    partner_id = str(uuid4())
    base = {
        "goal_id": uuid4(),
        "goal_name": "Singapore business · 8 months",
        "goal_type": "flight",
        "origin_city": "Hyderabad",
        "destination_city": "Singapore",
        "cabin_class": "business",
        "num_passengers": 1,
        "target_miles": 92_000,
        "target_date": date(2027, 3, 4),
        "status": "active",
        "created_at": datetime(2026, 7, 6, 12, 0, 0),
        "recommendation_type": "spend_routing",
        "summary": "Route travel spend through HDFC Infinia to KrisFlyer.",
        "reasoning": "Infinia's 5:3 SmartBuy rate dominates travel spend.",
        "action_items": [
            {"priority": 1, "action": "Move travel spend to Infinia", "impact": "+9,000 pts"}
        ],
        "confidence_score": Decimal("0.62"),
        "model_version": "template-fallback",
        "catalog_snapshot_version": "cat-b63f738db960",
        "engine_version": "engine-v1",
        "months_to_goal": 7,
        "optimization_score": Decimal("62.10"),
        "card_allocations": {
            "spend_allocation": {"travel": card_id, "dining": card_id},
            "cards_used": [card_id],
            "cards_to_acquire": [],
            "ledger": [
                {
                    "month": 0,
                    "points_by_card": {card_id: 9000},
                    "points_earned_this_month": 9000,
                    "cap_utilization": {},
                    "milestones_triggered": [],
                    "transfers_executed": [],
                    "cumulative_target_miles": 0,
                },
                {
                    "month": 1,
                    "points_by_card": {card_id: 18000},
                    "points_earned_this_month": 9000,
                    "cap_utilization": {},
                    "milestones_triggered": [],
                    "transfers_executed": [],
                    "cumulative_target_miles": 0,
                },
            ],
        },
        "milestone_projections": [
            {
                "milestone_id": str(uuid4()),
                "card_id": card_id,
                "expected_month": 3,
                "bonus_points": 2500,
            }
        ],
        "transfer_recommendation": [
            {
                "from_card_id": card_id,
                "to_partner_id": partner_id,
                "points": 90_000,
                "planned_month": 7,
            }
        ],
    }
    base.update(overrides)
    return base


async def test_detail_query_is_scoped_to_caller_and_goal() -> None:
    """Both ids are bound — a user can never read another user's goal by id."""
    user_id, goal_id = uuid4(), uuid4()
    conn = CapturingConn([_detail_row()])
    await get_saved_goal(conn, user_id=user_id, goal_id=goal_id)  # type: ignore[arg-type]

    sql, params = conn.calls[0]
    assert params == {"user_id": user_id, "goal_id": goal_id}
    assert "g.id = :goal_id" in sql
    assert "g.user_id = :user_id" in sql


async def test_detail_returns_none_when_goal_missing_or_not_mine() -> None:
    """No row (unknown id, or someone else's goal) ⇒ None, for the API's 404."""
    conn = CapturingConn([])
    row = await get_saved_goal(conn, user_id=uuid4(), goal_id=uuid4())  # type: ignore[arg-type]
    assert row is None


async def test_detail_maps_full_lineage_row_faithfully() -> None:
    """Every persisted column surfaces unchanged — the JSONB payloads pass
    through as stored (no recomputation), scores/confidence keep exact types."""
    conn = CapturingConn([_detail_row()])
    row = await get_saved_goal(conn, user_id=uuid4(), goal_id=uuid4())  # type: ignore[arg-type]

    assert row is not None
    assert row.origin_city == "Hyderabad"
    assert row.destination_city == "Singapore"
    assert row.num_passengers == 1
    assert row.target_miles == 92_000
    assert row.reasoning == "Infinia's 5:3 SmartBuy rate dominates travel spend."
    assert row.recommendation_type == "spend_routing"
    assert row.confidence_score == 0.62
    assert isinstance(row.confidence_score, float)
    assert row.months_to_goal == 7
    # NUMERIC score stays an exact Decimal — no float round-trip.
    assert row.optimization_score == Decimal("62.10")
    assert row.engine_version == "engine-v1"
    # JSONB payloads exactly as persisted.
    assert row.card_allocations is not None
    assert len(row.card_allocations["ledger"]) == 2
    assert row.card_allocations["ledger"][1]["points_earned_this_month"] == 9000
    assert row.milestone_projections is not None
    assert row.milestone_projections[0]["bonus_points"] == 2500
    assert row.transfer_recommendation is not None
    assert row.transfer_recommendation[0]["points"] == 90_000


async def test_detail_infeasible_goal_has_no_result_payloads() -> None:
    """The infeasible path persists no simulation_results row (results.py) —
    the recommendation columns still surface, the result-side ones are None."""
    conn = CapturingConn(
        [
            _detail_row(
                recommendation_type="goal_feasibility",
                months_to_goal=None,
                optimization_score=None,
                confidence_score=None,
                card_allocations=None,
                milestone_projections=None,
                transfer_recommendation=None,
            )
        ]
    )
    row = await get_saved_goal(conn, user_id=uuid4(), goal_id=uuid4())  # type: ignore[arg-type]

    assert row is not None
    assert row.summary == "Route travel spend through HDFC Infinia to KrisFlyer."
    assert row.recommendation_type == "goal_feasibility"
    assert row.card_allocations is None
    assert row.optimization_score is None
    assert row.confidence_score is None
