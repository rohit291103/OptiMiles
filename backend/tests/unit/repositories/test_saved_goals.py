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

from app.repositories.saved_goals import list_saved_goals


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
