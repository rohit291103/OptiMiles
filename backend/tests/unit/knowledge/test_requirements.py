"""Stage 3 — reward requirement estimation. The number comes from the award
chart, never from anywhere else; the buffer is explicit and surfaced."""

from datetime import date
from uuid import uuid4

import pytest

from app.domain import CatalogSnapshot, GoalResolution, TravelGoal
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.requirements import ChartRowMissing, estimate_requirement
from app.knowledge.seed_catalog import seed_id

TODAY = date(2026, 7, 4)


def _goal(snapshot: CatalogSnapshot, **intent_overrides: object) -> TravelGoal:
    from tests.unit.knowledge.test_goal_resolution import _intent

    resolution = resolve_goal(_intent(**intent_overrides), snapshot, today=TODAY)
    assert isinstance(resolution, GoalResolution)
    return TravelGoal(id=uuid4(), user_id=uuid4(), status="active", **resolution.model_dump())


def test_golden_singapore_business_for_two(snapshot: CatalogSnapshot) -> None:
    """45,000 chart miles (post-Nov-2025 Zone 6 saver) × 2 passengers =
    90,000; 5% buffer = 4,500."""
    goal = _goal(snapshot)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)

    assert requirement.chart_miles_per_passenger == 45000
    assert requirement.miles_required_total == 90000
    assert requirement.buffer_miles == 4500
    assert requirement.taxes_fees_inr_estimate == 8000 * 2
    assert requirement.target_program_id == seed_id("partner", "krisflyer")
    assert requirement.target_program_name == "KrisFlyer"
    assert requirement.stale_chart is False


def test_buffer_rounds_up_never_down(snapshot: CatalogSnapshot) -> None:
    """A buffer that rounds down understates the safety margin:
    1 passenger × 45,000 × 3.33% = 1,498.5 → must ceil to 1,499."""
    goal = _goal(snapshot, num_passengers=1)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=3.33)
    assert requirement.buffer_miles == 1499


def test_single_passenger_economy(snapshot: CatalogSnapshot) -> None:
    goal = _goal(snapshot, cabin_class="economy", num_passengers=1)
    requirement = estimate_requirement(goal, snapshot, buffer_pct=5.0)
    assert requirement.chart_miles_per_passenger == 19000
    assert requirement.miles_required_total == 19000
    assert requirement.buffer_miles == 950


def test_locked_chart_row_missing_fails_loudly(snapshot: CatalogSnapshot) -> None:
    goal = _goal(snapshot).model_copy(update={"award_chart_id": uuid4()})
    with pytest.raises(ChartRowMissing):
        estimate_requirement(goal, snapshot, buffer_pct=5.0)
