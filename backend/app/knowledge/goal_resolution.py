"""Stage 2 — Goal Resolution & Validation (the trust boundary).

Every accepted field is confirmed against the catalog snapshot. Ambiguity goes
back as a ClarificationRequest; a route with no award-chart row is rejected as
UnsupportedRoute with the supported alternatives. Nothing is ever estimated
for an unsupported route.
"""

import calendar
import re
from datetime import date

from app.domain import (
    CabinClass,
    CatalogSnapshot,
    ClarificationRequest,
    GoalResolution,
    ParsedGoalIntent,
    UnsupportedRoute,
)
from app.domain.catalog import AwardChartEntry, TransferPartner
from app.domain.enums import AwardType

_PRIMARY_PROGRAM = "KrisFlyer"

# City → award-chart region. A deliberately small deterministic mapping table
# (blueprint Stage 2); a city not listed here is a clarification, not a guess.
CITY_TO_REGION: dict[str, str] = {
    # India (MVP origins)
    "hyderabad": "India",
    "mumbai": "India",
    "delhi": "India",
    "new delhi": "India",
    "bangalore": "India",
    "bengaluru": "India",
    "chennai": "India",
    "kolkata": "India",
    "pune": "India",
    "ahmedabad": "India",
    # MVP destinations (Scope v2: Singapore, London, New York)
    "singapore": "Southeast Asia",
    "london": "Europe",
    "new york": "North America",
    "new york city": "North America",
    "nyc": "North America",
}


def resolve_goal(
    intent: ParsedGoalIntent, snapshot: CatalogSnapshot, *, today: date
) -> GoalResolution | UnsupportedRoute | ClarificationRequest:
    missing: list[str] = []
    questions: list[str] = []

    origin_region = _region(intent.origin_city)
    if origin_region is None:
        missing.append("origin_city")
        questions.append("Which city will you fly from?")

    destination_region = _region(intent.destination_city)
    if destination_region is None:
        missing.append("destination_city")
        questions.append("Which destination city? Supported today: Singapore, London, New York.")

    cabin = _cabin(intent.cabin_class)
    if cabin is None:
        missing.append("cabin_class")
        questions.append("Which cabin — economy, premium economy, business or first?")

    if intent.timeline_months is None:
        missing.append("timeline_months")
        questions.append("By when do you want to fly (in months from now)?")

    if intent.num_passengers is None:
        missing.append("num_passengers")
        questions.append("How many passengers?")

    if missing:
        return ClarificationRequest(questions=tuple(questions), missing_fields=tuple(missing))

    # For the type-checker: all validated above.
    assert origin_region and destination_region and cabin
    assert intent.timeline_months is not None and intent.num_passengers is not None
    assert intent.origin_city and intent.destination_city

    partners = _candidate_partners(snapshot, intent.program_hint)
    hint_given = _normalize(intent.program_hint) is not None
    if hint_given and len(partners) != 1:
        # Zero matches OR an ambiguous hint ("air" matches both Singapore
        # Airlines and Air India): ambiguity goes back as clarification,
        # never a silent first-match pick (blueprint Stage 2).
        options = partners or snapshot.partners
        return ClarificationRequest(
            questions=(
                f"Which loyalty program did you mean by '{intent.program_hint}'? "
                f"Options: {', '.join(sorted(p.program_name for p in options))}.",
            ),
            missing_fields=("program_hint",),
        )

    chart_match: tuple[TransferPartner, AwardChartEntry] | None = None
    for partner in partners:
        chart = next(
            (
                c
                for c in snapshot.award_charts
                if c.partner_id == partner.id
                and c.origin_region == origin_region
                and c.destination_region == destination_region
                and c.cabin_class == cabin
                and c.award_type == AwardType.SAVER
            ),
            None,
        )
        if chart is not None:
            chart_match = (partner, chart)
            break

    if chart_match is None:
        partner_names = {p.id: p.program_name for p in snapshot.partners}
        supported = sorted(
            f"{c.origin_region} → {c.destination_region} "
            f"({c.cabin_class.value}, {partner_names.get(c.partner_id, '?')})"
            for c in snapshot.award_charts
        )
        return UnsupportedRoute(
            origin_region=origin_region,
            destination_region=destination_region,
            cabin_class=cabin,
            reason=(
                f"No award chart covers {origin_region} → {destination_region} "
                f"in {cabin.value} for the supported programs."
            ),
            supported_routes=tuple(supported),
        )

    partner, chart = chart_match
    origin_city = _tidy(intent.origin_city)
    destination_city = _tidy(intent.destination_city)
    return GoalResolution(
        goal_name=(
            f"{partner.partner_name} {cabin.value.replace('_', ' ')} — "
            f"{origin_city} → {destination_city}"
        ),
        partner_id=partner.id,
        award_chart_id=chart.id,
        origin_city=origin_city,
        destination_city=destination_city,
        origin_region=origin_region,
        destination_region=destination_region,
        cabin_class=cabin,
        award_type=AwardType.SAVER,
        num_passengers=intent.num_passengers,
        target_date=_add_months(today, intent.timeline_months),
    )


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value.strip().lower())
    return collapsed or None


def _tidy(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _region(city: str | None) -> str | None:
    normalized = _normalize(city)
    return CITY_TO_REGION.get(normalized) if normalized else None


def _cabin(value: str | None) -> CabinClass | None:
    normalized = _normalize(value)
    if normalized is None:
        return None
    try:
        return CabinClass(normalized.replace(" ", "_"))
    except ValueError:
        return None


def _candidate_partners(
    snapshot: CatalogSnapshot, program_hint: str | None
) -> tuple[TransferPartner, ...]:
    """Hinted partner if it matches; otherwise all partners, primary first."""
    hint = _normalize(program_hint)
    if hint:
        matched = tuple(
            p
            for p in snapshot.partners
            if hint in p.partner_name.lower()
            or hint in p.program_name.lower()
            or p.partner_name.lower() in hint
            or p.program_name.lower() in hint
        )
        return matched  # empty tuple ⇒ caller asks for clarification
    return tuple(
        sorted(
            snapshot.partners,
            key=lambda p: (p.program_name != _PRIMARY_PROGRAM, p.program_name),
        )
    )


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
