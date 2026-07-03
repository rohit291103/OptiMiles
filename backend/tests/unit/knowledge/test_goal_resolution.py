"""Stage 2 — goal resolution. The trust boundary: every accepted field is
catalog-confirmed; everything else is an explicit clarification or rejection,
never a guess."""

from datetime import date

from app.domain import (
    CabinClass,
    CatalogSnapshot,
    ClarificationRequest,
    GoalResolution,
    ParsedGoalIntent,
    UnsupportedRoute,
)
from app.knowledge.goal_resolution import resolve_goal
from app.knowledge.seed_catalog import seed_id

TODAY = date(2026, 7, 4)


def _intent(**overrides: object) -> ParsedGoalIntent:
    values: dict[str, object] = {
        "origin_city": "Hyderabad",
        "destination_city": "Singapore",
        "cabin_class": "business",
        "timeline_months": 8,
        "num_passengers": 2,
        "confidence": 0.95,
    }
    values.update(overrides)
    return ParsedGoalIntent.model_validate(values)


def test_resolves_the_flagship_goal(snapshot: CatalogSnapshot) -> None:
    """'Singapore Airlines business class from Hyderabad in 8 months' —
    the definition-of-done scenario (build plan §8)."""
    result = resolve_goal(_intent(), snapshot, today=TODAY)

    assert isinstance(result, GoalResolution)
    assert result.origin_region == "India"
    assert result.destination_region == "Southeast Asia"
    assert result.cabin_class == CabinClass.BUSINESS
    assert result.num_passengers == 2
    assert result.target_date == date(2027, 3, 4)  # 8 months from TODAY
    assert result.partner_id == seed_id("partner", "krisflyer")
    # Locked to the exact chart row so later chart updates never move the goal.
    chart = next(c for c in snapshot.award_charts if c.id == result.award_chart_id)
    assert chart.miles_required == 35000


def test_program_hint_is_normalized(snapshot: CatalogSnapshot) -> None:
    result = resolve_goal(_intent(program_hint="Singapore Air"), snapshot, today=TODAY)
    assert isinstance(result, GoalResolution)
    assert result.partner_id == seed_id("partner", "krisflyer")


def test_unknown_city_asks_for_clarification(snapshot: CatalogSnapshot) -> None:
    """Ambiguous region mapping → back to clarification (blueprint Stage 2),
    never a guessed region."""
    result = resolve_goal(_intent(destination_city="Tokyo"), snapshot, today=TODAY)
    assert isinstance(result, ClarificationRequest)
    assert "destination_city" in result.missing_fields


def test_missing_origin_asks_for_clarification(snapshot: CatalogSnapshot) -> None:
    result = resolve_goal(_intent(origin_city=None), snapshot, today=TODAY)
    assert isinstance(result, ClarificationRequest)
    assert "origin_city" in result.missing_fields


def test_route_without_chart_row_is_explicitly_unsupported(snapshot: CatalogSnapshot) -> None:
    """India → Europe FIRST has no chart row in the seeds: must reject with
    the supported alternatives, never estimate (blueprint Stage 2)."""
    result = resolve_goal(
        _intent(destination_city="London", cabin_class="first"), snapshot, today=TODAY
    )
    assert isinstance(result, UnsupportedRoute)
    assert result.supported_routes  # tells the user what IS possible
    assert any("Europe" in route for route in result.supported_routes)


def test_all_three_mvp_destinations_resolve_in_business(snapshot: CatalogSnapshot) -> None:
    for city, region in [
        ("Singapore", "Southeast Asia"),
        ("London", "Europe"),
        ("New York", "North America"),
    ]:
        result = resolve_goal(_intent(destination_city=city), snapshot, today=TODAY)
        assert isinstance(result, GoalResolution), f"{city} should resolve"
        assert result.destination_region == region


def test_city_matching_is_case_and_spacing_tolerant(snapshot: CatalogSnapshot) -> None:
    result = resolve_goal(
        _intent(origin_city="  hyderabad ", destination_city="new york"), snapshot, today=TODAY
    )
    assert isinstance(result, GoalResolution)
    assert result.destination_region == "North America"


def test_ambiguous_program_hint_asks_for_clarification(snapshot: CatalogSnapshot) -> None:
    """'air' matches both Singapore AIRlines and AIR India: ambiguity must go
    back as clarification, never a silent first-match pick (reviewer finding,
    2026-07-04)."""
    result = resolve_goal(_intent(program_hint="air"), snapshot, today=TODAY)
    assert isinstance(result, ClarificationRequest)
    assert result.missing_fields == ("program_hint",)
    assert "KrisFlyer" in result.questions[0]
    assert "Maharaja Club" in result.questions[0]
