"""GET /v1/portfolio — the Phase 1 "my cards" endpoint.

Anonymous like Best Card: no auth, no DB, no LLM. The wallet is whatever the
client sends, so a signed-out visitor gets a portfolio that is genuinely
theirs rather than a demo wallet's.

The arithmetic is proven in tests/unit/valuation/test_portfolio.py; what is
under test here is the HTTP contract — defaulting, validation, error mapping,
caching, and the Phase-1 caveats the payload has to state out loud.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.domain import CatalogSnapshot
from app.knowledge.seed_catalog import seed_id
from app.main import create_app

INFINIA = str(seed_id("card", "hdfc-infinia"))
REGALIA = str(seed_id("card", "hdfc-regalia-gold"))
TRAVELONE = str(seed_id("card", "hsbc-travelone"))
ATLAS = str(seed_id("card", "axis-atlas"))
SBI = str(seed_id("card", "sbi-cashback"))
MAHARAJA = str(seed_id("partner", "maharaja-club"))
KRISFLYER = str(seed_id("partner", "krisflyer"))


@pytest.fixture
def client(snapshot: CatalogSnapshot) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_model] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _get(client: TestClient, **params) -> dict:
    response = client.get("/v1/portfolio", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_no_program_is_assumed_when_none_is_given(client: TestClient) -> None:
    """The portfolio leads with what the catalog states directly. Nothing is
    priced until the user picks where their points are going."""
    body = _get(client, card_ids=[INFINIA])
    assert body["target_program_name"] is None
    assert body["cards_reaching_target"] is None
    assert body["cards"][0]["card_name"] == "Infinia Metal"
    assert body["cards"][0]["reaches_target"] is None
    assert all(rule["miles_per_100"] is None for rule in body["cards"][0]["earn_rules"])
    assert all(category["leader_card_id"] is None for category in body["categories"])
    # ...but the earn rates are real, and so is where the points could go.
    assert body["cards"][0]["earn_rules"][0]["earn_rate"] == "3.33"
    assert [reach["program_name"] for reach in body["partner_reach"]] == [
        "ALL - Accor Live Limitless",
        "KrisFlyer",
        "Maharaja Club",
        "Marriott Bonvoy",
    ]


def test_choosing_a_program_prices_the_wallet(client: TestClient) -> None:
    body = _get(client, card_ids=[INFINIA], target_program_id=KRISFLYER)
    assert body["target_program_name"] == "KrisFlyer"
    assert body["cards_reaching_target"] == 1
    assert body["cards"][0]["earn_rules"][0]["miles_per_100"] == "3.3300"


def test_accepts_an_explicit_target_program(client: TestClient) -> None:
    """The portfolio is goal-relative: repricing the same wallet against a
    different program is the whole point of the target being a parameter."""
    body = _get(client, card_ids=[INFINIA], target_program_id=MAHARAJA)
    assert body["target_program_name"] == "Maharaja Club"
    # hdfc-rp-premium → Maharaja Club is 2:1, against 1:1 into KrisFlyer.
    default_rule = body["cards"][0]["earn_rules"][0]
    assert default_rule["miles_per_100"] == "1.6650"


def test_compares_by_miles_not_points(client: TestClient) -> None:
    """The endpoint-level guard on the central invariant — once a program is
    chosen, the comparison happens in ITS unit, not in points. Provenance is
    pinned empty here so this tests ranking alone."""
    client.app.dependency_overrides[deps.get_unverified_ids] = lambda: frozenset()
    body = _get(client, card_ids=[REGALIA, TRAVELONE], target_program_id=KRISFLYER)
    default = next(c for c in body["categories"] if c["category_slug"] == "default")
    leader = next(row for row in default["rows"] if row["card_id"] == default["leader_card_id"])
    assert leader["card_name"] == "TravelOne"


def test_real_seeds_withhold_a_leader_resting_on_an_unverified_route(
    client: TestClient,
) -> None:
    """Default category in KrisFlyer miles/₹100: Atlas 2.00 × 2/1 = 4.00,
    TravelOne 2.00 × 1/1 = 2.00. Atlas would win, but the reviewed seeds
    still flag its KrisFlyer link — so no leader is named, and the VERIFIED
    runner-up (TravelOne, issuer-confirmed 2026-11-06) is not promoted in
    its place."""
    body = _get(client, card_ids=[ATLAS, TRAVELONE], target_program_id=KRISFLYER)
    default = next(c for c in body["categories"] if c["category_slug"] == "default")
    assert default["leader_card_id"] is None
    assert default["leader_withheld_unverified"] is True
    atlas = next(r for r in default["rows"] if r["card_id"] == ATLAS)
    assert atlas["miles_per_100"] == "4.0000"
    assert atlas["needs_verification"] is True
    travelone = next(r for r in default["rows"] if r["card_id"] == TRAVELONE)
    assert travelone["miles_per_100"] == "2.0000"
    assert travelone["needs_verification"] is False


def test_real_seeds_name_a_leader_once_its_route_is_verified(client: TestClient) -> None:
    """Regalia 2.50 × 1/2 = 1.25 vs TravelOne 2.00 × 1/1 = 2.00. TravelOne's
    currency and KrisFlyer link were confirmed on HSBC India's own pages
    (2026-11-06), so the real seeds now name it — the same wallet that was
    withheld before verification."""
    body = _get(client, card_ids=[REGALIA, TRAVELONE], target_program_id=KRISFLYER)
    default = next(c for c in body["categories"] if c["category_slug"] == "default")
    assert default["leader_card_id"] == TRAVELONE
    assert default["leader_withheld_unverified"] is False


def test_unroutable_card_is_priced_at_null_not_zero(client: TestClient) -> None:
    body = _get(client, card_ids=[INFINIA, SBI], target_program_id=KRISFLYER)
    cashback = next(c for c in body["cards"] if c["card_name"] == "Cashback")
    assert cashback["reaches_target"] is False
    assert cashback["transfer_links"] == []
    assert all(rule["miles_per_100"] is None for rule in cashback["earn_rules"])
    assert body["cards_reaching_target"] == 1


def test_states_the_phase_one_caveats(client: TestClient) -> None:
    """Caps and milestones are shown as targets, not progress — there is no
    spend data until Phase 2. The payload has to say so rather than let the
    UI imply a zero-utilisation reading of a cap."""
    body = _get(client, card_ids=[ATLAS])
    assert body["spend_data_available"] is False
    assert "spend" in body["caveat"].lower()


def test_response_carries_the_snapshot_version(
    client: TestClient, snapshot: CatalogSnapshot
) -> None:
    assert _get(client, card_ids=[INFINIA])["catalog_snapshot_version"] == snapshot.version


def test_etag_revalidation_returns_304(client: TestClient) -> None:
    params = {"card_ids": [INFINIA, ATLAS]}
    etag = client.get("/v1/portfolio", params=params).headers["ETag"]
    second = client.get("/v1/portfolio", params=params, headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_unknown_card_is_404_not_a_silent_drop(client: TestClient) -> None:
    response = client.get(
        "/v1/portfolio", params={"card_ids": [str(seed_id("card", "no-such-card"))]}
    )
    assert response.status_code == 404
    assert "not in catalog snapshot" in response.text


def test_empty_wallet_is_422(client: TestClient) -> None:
    assert client.get("/v1/portfolio").status_code == 422


def test_unknown_target_program_is_422(client: TestClient) -> None:
    """422, matching /v1/best-card: the program id is an unusable argument,
    not a missing page."""
    response = client.get(
        "/v1/portfolio",
        params={"card_ids": [INFINIA], "target_program_id": str(seed_id("partner", "nope"))},
    )
    assert response.status_code == 422
    assert "unknown target program" in response.text


def test_wallet_larger_than_the_cap_is_422(client: TestClient) -> None:
    """The catalog holds 9 cards; a 21-card wallet is a malformed request, not
    a portfolio to price."""
    response = client.get("/v1/portfolio", params={"card_ids": [INFINIA] * 21})
    assert response.status_code == 422


# ── Verification tier + the progress join key ─────────────────────────────


def test_unverified_rows_are_labelled_in_the_payload(snapshot: CatalogSnapshot) -> None:
    """The endpoint threads the provenance index into the engine; which rows
    the real seeds flag is the knowledge tests' concern, so pin a known set."""
    app = create_app()
    app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
    app.dependency_overrides[deps.get_unverified_ids] = lambda: frozenset(
        {seed_id("category", "hdfc-infinia:travel")}
    )
    with TestClient(app) as test_client:
        body = _get(test_client, card_ids=[INFINIA])
    flags = {
        rule["category_slug"]: rule["needs_verification"] for rule in body["cards"][0]["earn_rules"]
    }
    assert flags == {"default": False, "travel": True}
    assert body["cards"][0]["needs_verification"] is False


def test_milestones_carry_the_id_activity_progress_reports(client: TestClient) -> None:
    body = _get(client, card_ids=[ATLAS])
    assert {m["milestone_id"] for m in body["cards"][0]["milestones"]} == {
        str(seed_id("milestone", f"axis-atlas:{index}")) for index in range(4)
    }


def test_default_provenance_is_the_reviewed_seed_files(seed_dir) -> None:
    """Unoverridden, the dependency reads the same YAML the seed tests load —
    never an empty set that would present every row as verified."""
    from app.knowledge.seed_catalog import load_unverified_ids

    deps.get_unverified_ids.cache_clear()
    assert deps.get_unverified_ids() == load_unverified_ids(seed_dir)


def test_etag_changes_when_the_verification_tier_does(snapshot: CatalogSnapshot) -> None:
    """A row can be verified (or re-flagged) without its values changing, so
    the snapshot version alone would serve a stale label as a 304."""

    def etag_for(unverified: frozenset) -> str:
        app = create_app()
        app.dependency_overrides[deps.get_snapshot] = lambda: snapshot
        app.dependency_overrides[deps.get_unverified_ids] = lambda: unverified
        with TestClient(app) as test_client:
            return test_client.get("/v1/portfolio", params={"card_ids": [INFINIA]}).headers["ETag"]

    flagged = frozenset({seed_id("category", "hdfc-infinia:travel")})
    assert etag_for(flagged) != etag_for(frozenset())
    assert etag_for(flagged) == etag_for(frozenset(flagged))


# ── Provenance plumbing: cached digest, drift warning ─────────────────────


def test_tier_digest_is_cached_per_unverified_set() -> None:
    """Computed once per distinct set (once per process in production), not
    per request."""
    flagged = frozenset({seed_id("category", "hdfc-infinia:travel")})
    deps.tier_digest.cache_clear()
    first = deps.tier_digest(flagged)
    assert deps.tier_digest(frozenset(flagged)) == first
    assert deps.tier_digest.cache_info().hits == 1
    assert deps.tier_digest(frozenset()) != first


def test_drift_between_snapshot_and_seed_flags_is_logged(
    snapshot: CatalogSnapshot, caplog: pytest.LogCaptureFixture
) -> None:
    stray = seed_id("card", "no-such-card")
    with caplog.at_level("WARNING", logger="app.api.deps"):
        deps.warn_on_provenance_drift(snapshot, frozenset({stray, seed_id("card", "hdfc-infinia")}))
    assert len(caplog.records) == 1
    assert str(stray) in caplog.records[0].getMessage()

    caplog.clear()
    with caplog.at_level("WARNING", logger="app.api.deps"):
        deps.warn_on_provenance_drift(snapshot, frozenset({seed_id("card", "hdfc-infinia")}))
    assert caplog.records == []


def test_a_db_not_reloaded_from_these_seeds_is_logged(
    snapshot: CatalogSnapshot, caplog: pytest.LogCaptureFixture
) -> None:
    """Fail-open guard (2026-11-07 review): a field like `requires_portal`
    defaults to None = "applies however you pay". A DB migrated but not
    reseeded would silently price direct bookings at the portal rate again.
    The DB snapshot's content version equals the seed snapshot's after a
    reload, so a mismatch is the signal."""
    with caplog.at_level("WARNING", logger="app.api.deps"):
        deps.warn_on_seed_version_drift(snapshot, snapshot.version)
    assert caplog.records == []

    with caplog.at_level("WARNING", logger="app.api.deps"):
        stale = snapshot.model_copy(update={"version": "cat-stale"})
        deps.warn_on_seed_version_drift(stale, snapshot.version)
    assert len(caplog.records) == 1
    assert "cat-stale" in caplog.records[0].getMessage()
