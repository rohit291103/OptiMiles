"""Route coverage — which goals the engine can actually price.

The goal form offers only what Stage 2 will accept: a city must map to a
region (CITY_TO_REGION) AND a SAVER award-chart row must exist for that
region pair and cabin. Golden values are the reviewed seeds
(`seeds/catalog/award_charts.yaml`: India → Southeast Asia in economy,
business and first; India → Europe and India → North America in business).
"""

from datetime import date

from app.domain import CabinClass, CatalogSnapshot, GoalResolution, ParsedGoalIntent
from app.domain.enums import AwardType
from app.knowledge.goal_resolution import covered_routes, resolve_goal

TODAY = date(2026, 11, 6)


def test_destinations_and_their_cabins_come_from_award_charts(snapshot: CatalogSnapshot) -> None:
    coverage = covered_routes(snapshot)
    by_city = {d.city: d for d in coverage.destinations}
    assert sorted(by_city) == ["London", "New York", "Singapore"]
    assert by_city["Singapore"].region == "Southeast Asia"
    # Cabins in travel order, never alphabetical.
    singapore = coverage.cabins_for("India", "Southeast Asia")
    assert singapore == (CabinClass.ECONOMY, CabinClass.BUSINESS, CabinClass.FIRST)
    assert coverage.cabins_for("India", "Europe") == (CabinClass.BUSINESS,)
    assert coverage.cabins_for("India", "North America") == (CabinClass.BUSINESS,)


def test_origins_are_every_mapped_city_with_a_route(snapshot: CatalogSnapshot) -> None:
    """One display name per city — aliases (Bengaluru, New Delhi, NYC) are
    accepted by Stage 2 but never listed twice."""
    origins = [o.city for o in covered_routes(snapshot).origins]
    assert origins == [
        "Ahmedabad",
        "Bangalore",
        "Chennai",
        "Delhi",
        "Hyderabad",
        "Kolkata",
        "Mumbai",
        "Pune",
    ]


def test_an_uncovered_pair_has_no_cabins(snapshot: CatalogSnapshot) -> None:
    assert covered_routes(snapshot).cabins_for("Europe", "India") == ()


def test_a_region_without_chart_rows_drops_out(snapshot: CatalogSnapshot) -> None:
    """Coverage follows the data: remove the Europe row and London is no
    longer offered — the form can never offer a route Stage 2 would reject."""
    charts = tuple(c for c in snapshot.award_charts if c.destination_region != "Europe")
    coverage = covered_routes(snapshot.model_copy(update={"award_charts": charts}))
    assert "London" not in {d.city for d in coverage.destinations}


def test_only_saver_rows_count(snapshot: CatalogSnapshot) -> None:
    """Stage 2 matches SAVER rows only, so coverage must too."""
    charts = tuple(
        c.model_copy(update={"award_type": AwardType.ADVANTAGE})
        if c.destination_region == "North America"
        else c
        for c in snapshot.award_charts
    )
    coverage = covered_routes(snapshot.model_copy(update={"award_charts": charts}))
    assert coverage.cabins_for("India", "North America") == ()
    assert "New York" not in {d.city for d in coverage.destinations}


def test_every_offered_combination_resolves(snapshot: CatalogSnapshot) -> None:
    """The contract the form relies on: anything offered is accepted."""
    coverage = covered_routes(snapshot)
    for origin in coverage.origins:
        for destination in coverage.destinations:
            for cabin in coverage.cabins_for(origin.region, destination.region):
                intent = ParsedGoalIntent(
                    origin_city=origin.city,
                    destination_city=destination.city,
                    cabin_class=cabin.value,
                    timeline_months=8,
                    num_passengers=1,
                    confidence=1.0,
                )
                result = resolve_goal(intent, snapshot, today=TODAY)
                assert isinstance(result, GoalResolution), (origin, destination, cabin)
