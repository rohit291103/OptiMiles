"""GET /goals/{id} — the saved-strategy detail behind a dashboard goal card.

Two layers under test, no live DB (same constraint as the repo tests):
- the pure row → `SavedGoalDetail` mapping (`detail_from_row`), which
  reconstructs the persisted JSONB payloads into typed response fields; and
- the HTTP edge: auth is required, and an unknown/foreign goal id is a 404
  (indistinguishable on purpose — the query is user-scoped).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.goals import detail_from_row, display_names
from app.config import Settings, get_settings
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import seed_id
from app.main import create_app
from app.repositories.saved_goals import SavedGoalDetailRow

CARD_ID = str(uuid4())
PARTNER_ID = str(uuid4())


def _row(**overrides: object) -> SavedGoalDetailRow:
    base: dict = {
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
        "reasoning": "Infinia dominates travel spend.",
        "action_items": [
            {"priority": 2, "action": "Set travel autopay", "impact": None, "card_id": None},
            {
                "priority": 1,
                "action": "Move travel spend to Infinia",
                "impact": "+9,000 pts",
                "card_id": CARD_ID,
            },
        ],
        "confidence_score": 0.62,
        "model_version": "template-fallback",
        "catalog_snapshot_version": "cat-b63f738db960",
        "engine_version": "engine-v1",
        "months_to_goal": 7,
        "optimization_score": Decimal("62.10"),
        "card_allocations": {
            "spend_allocation": {"travel": CARD_ID, "dining": CARD_ID},
            "cards_used": [CARD_ID],
            "cards_to_acquire": [],
            "ledger": [
                {
                    "month": 0,
                    "points_by_card": {CARD_ID: 9000},
                    "points_earned_this_month": 9000,
                    "cap_utilization": {},
                    "milestones_triggered": [],
                    "transfers_executed": [],
                    "cumulative_target_miles": 0,
                },
                {
                    "month": 1,
                    "points_by_card": {CARD_ID: 18000},
                    "points_earned_this_month": 9000,
                    "cap_utilization": {},
                    "milestones_triggered": [],
                    "transfers_executed": [],
                    "cumulative_target_miles": 45_000,
                },
            ],
        },
        "milestone_projections": [
            {
                "milestone_id": str(uuid4()),
                "card_id": CARD_ID,
                "expected_month": 3,
                "bonus_points": 2500,
            }
        ],
        "transfer_recommendation": [
            {
                "from_card_id": CARD_ID,
                "to_partner_id": PARTNER_ID,
                "points": 90_000,
                "planned_month": 7,
            }
        ],
    }
    base.update(overrides)
    return SavedGoalDetailRow(**base)


# ── detail_from_row: persisted JSONB → typed response ─────────────────────


def test_maps_goal_and_recommendation_columns() -> None:
    detail = detail_from_row(_row())

    assert detail.destination_city == "Singapore"
    assert detail.cabin_class == "business"
    assert detail.target_miles == 92_000
    assert detail.summary == "Route travel spend through HDFC Infinia to KrisFlyer."
    assert detail.reasoning == "Infinia dominates travel spend."
    assert detail.confidence_score == 0.62
    assert detail.catalog_snapshot_version == "cat-b63f738db960"
    assert detail.engine_version == "engine-v1"


def test_reconstructs_strategy_from_jsonb_payloads() -> None:
    detail = detail_from_row(_row())

    assert detail.strategy is not None
    strategy = detail.strategy
    assert strategy.spend_allocation == {"travel": CARD_ID, "dining": CARD_ID}
    assert strategy.cards_used == (CARD_ID,)
    assert strategy.cards_to_acquire == ()
    assert strategy.months_to_goal == 7
    assert strategy.optimization_score == Decimal("62.10")
    # The ledger keeps exactly the fields the accumulation chart needs.
    assert len(strategy.ledger) == 2
    assert strategy.ledger[1].month == 1
    assert strategy.ledger[1].points_earned_this_month == 9000
    assert strategy.ledger[1].cumulative_target_miles == 45_000
    # Milestones and transfers survive with their persisted values.
    assert strategy.milestones[0].bonus_points == 2500
    assert strategy.milestones[0].expected_month == 3
    assert strategy.transfer_plan[0].points == 90_000
    assert strategy.transfer_plan[0].planned_month == 7


def test_action_items_sorted_by_priority() -> None:
    """Stored order is not guaranteed; the response presents priority order."""
    detail = detail_from_row(_row())
    assert [item.priority for item in detail.action_items] == [1, 2]
    assert detail.action_items[0].action == "Move travel spend to Infinia"
    # The persisted card_id survives reconstruction (parity with the live
    # /goals/recommendation response's ActionItem shape).
    assert str(detail.action_items[0].card_id) == CARD_ID
    assert detail.action_items[1].card_id is None


def test_infeasible_goal_maps_without_strategy() -> None:
    """No simulation_results payloads (infeasible path) ⇒ strategy is None but
    the narration columns still ship — the adjustment story is the answer."""
    detail = detail_from_row(
        _row(
            recommendation_type="goal_feasibility",
            months_to_goal=None,
            optimization_score=None,
            card_allocations=None,
            milestone_projections=None,
            transfer_recommendation=None,
        )
    )
    assert detail.strategy is None
    assert detail.recommendation_type == "goal_feasibility"
    assert detail.summary is not None


# ── display_names: id → name maps for the client ──────────────────────────


def test_display_names_resolve_from_snapshot(snapshot: CatalogSnapshot) -> None:
    """Ids referenced by the saved strategy resolve to catalog display names
    (cosmetic labels from the *current* snapshot; the numbers stay persisted)."""
    infinia = str(seed_id("card", "hdfc-infinia"))
    krisflyer = str(seed_id("partner", "krisflyer"))
    detail = detail_from_row(
        _row(
            card_allocations={
                "spend_allocation": {"travel": infinia},
                "cards_used": [infinia],
                "cards_to_acquire": [],
                "ledger": [],
            },
            transfer_recommendation=[
                {
                    "from_card_id": infinia,
                    "to_partner_id": krisflyer,
                    "points": 90_000,
                    "planned_month": 7,
                }
            ],
            milestone_projections=[],
        )
    )
    assert detail.strategy is not None
    card_names, partner_names = display_names(detail.strategy, snapshot)
    assert card_names[infinia] == "Infinia Metal"
    assert "KrisFlyer" in partner_names[krisflyer]


def test_display_names_skip_unknown_ids(snapshot: CatalogSnapshot) -> None:
    """A goal saved against an older snapshot may reference retired ids — they
    are omitted from the maps (client falls back), never invented."""
    detail = detail_from_row(_row())  # random uuids, not in the seed catalog
    assert detail.strategy is not None
    card_names, partner_names = display_names(detail.strategy, snapshot)
    assert card_names == {}
    assert partner_names == {}


# ── HTTP edge ──────────────────────────────────────────────────────────────


def test_goal_detail_requires_auth() -> None:
    """Per-user data ⇒ no token, no detail (401), same as the list."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get(f"/goals/{uuid4()}")
    assert response.status_code == 401


def test_unknown_goal_is_404(
    monkeypatch: pytest.MonkeyPatch, snapshot: CatalogSnapshot
) -> None:
    """A goal that doesn't exist — or belongs to someone else — is a 404; the
    scoped query makes the two cases deliberately indistinguishable."""

    class FakeResult:
        def mappings(self) -> "FakeResult":
            return self

        def all(self) -> list[dict]:
            return []

    class FakeConn:
        async def execute(self, statement: object, params: dict) -> FakeResult:
            return FakeResult()

        async def __aenter__(self) -> "FakeConn":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    class FakeEngine:
        def connect(self) -> FakeConn:
            return FakeConn()

    secret = "test-jwt-secret-0123456789abcdef0123456789abcdef"
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )

    from app.api import deps

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_jwt_secret=secret
    )
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    monkeypatch.setattr("app.api.goals.get_engine", lambda: FakeEngine())
    with TestClient(app) as client:
        response = client.get(
            f"/goals/{uuid4()}", headers={"Authorization": f"Bearer {token}"}
        )
    app.dependency_overrides.clear()
    assert response.status_code == 404
