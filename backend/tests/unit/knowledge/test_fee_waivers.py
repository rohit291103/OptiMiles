"""Annual-fee waiver rows — seed goldens and catalog rules FW-01 … FW-03.

Every expected value below is read off the issuer's own document, re-opened
on 2026-11-02 (quotes and URLs are on each row in seeds/catalog/cards.yaml):

  HDFC fee-waiver page, "RENEWAL FEE WAIVER (Retail spends in preceding 12
  months)": Infinia Metal "Spend Rs. 10,00,000", Diners Club Black Metal
  "Spend Rs. 8,00,000", Regalia Gold "Spend Rs. 4,00,000".
  HSBC TravelOne service guide: "fully reversed if total eligible spend …
  during the relevant anniversary year exceeds ₹800,000", for the first year
  AND second year onwards.
  Axis MITC: Magnus for Burgundy "Waived on eligible spends* of INR
  30,00,000 in preceding card anniversary year", * excluding utilities and
  fuel among others. Axis SoSC "Annual Fee Waiver" row: "-" for Atlas.
  SBI MITC: Cashback "999 (Waived off on annual spends of Rs.2 Lakh or more
  in the preceding year)"; T&C: "within the last 365 days from the Annual
  Card Fee billing date".
  Amex Platinum: the ₹20L benefit is vouchers "on … payment of renewal fee".
  Amex Platinum Travel: nothing published about a waiver → no row.
"""

import pytest

from app.domain import (
    CatalogSnapshot,
    FeeWaiver,
    FeeWaiverKind,
    FeeWaiverWindow,
    SpendCategory,
    ThresholdComparison,
)
from app.knowledge.seed_catalog import (
    PROVENANCE_COLLECTIONS,
    load_unverified_ids,
    seed_id,
    snapshot_row_ids,
)
from app.knowledge.validation import CatalogValidationError, validate_catalog


def _waiver(snapshot: CatalogSnapshot, card_name: str) -> FeeWaiver | None:
    card = next(c for c in snapshot.cards if c.card_name == card_name)
    rows = [w for w in snapshot.fee_waivers if w.card_id == card.id]
    assert len(rows) <= 1
    return rows[0] if rows else None


# ── Seed goldens ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("card_name", "threshold"),
    [
        ("Infinia Metal", 1_000_000),
        ("Diners Club Black Metal", 800_000),
        ("Regalia Gold", 400_000),
    ],
)
def test_hdfc_waivers_are_met_at_the_figure_over_the_preceding_year(
    snapshot: CatalogSnapshot, card_name: str, threshold: int
) -> None:
    waiver = _waiver(snapshot, card_name)
    assert waiver is not None
    assert waiver.kind is FeeWaiverKind.SPEND_BASED
    assert waiver.threshold_inr == threshold
    # "Spend Rs. X" — meeting the figure is enough.
    assert waiver.threshold_comparison is ThresholdComparison.AT_LEAST
    assert waiver.window_kind is FeeWaiverWindow.PRECEDING_CARD_YEAR
    # A RENEWAL fee waiver; the first-year fee has its own (voucher) offer.
    assert waiver.waives_renewal_fee is True
    assert waiver.waives_joining_fee is False


def test_hsbc_travelone_must_exceed_8_lakh_and_covers_year_one(
    snapshot: CatalogSnapshot,
) -> None:
    """ "exceeds ₹800,000" is strict, and the service guide repeats the
    reversal for "Standard Annual fees for the first year"."""
    waiver = _waiver(snapshot, "TravelOne")
    assert waiver is not None
    assert waiver.threshold_inr == 800_000
    assert waiver.threshold_comparison is ThresholdComparison.MORE_THAN
    assert waiver.window_kind is FeeWaiverWindow.CURRENT_CARD_YEAR
    assert waiver.waives_renewal_fee is True
    assert waiver.waives_joining_fee is True


def test_magnus_burgundy_excludes_the_categories_axis_names(
    snapshot: CatalogSnapshot,
) -> None:
    waiver = _waiver(snapshot, "Magnus for Burgundy")
    assert waiver is not None
    assert waiver.threshold_inr == 3_000_000
    assert waiver.threshold_comparison is ThresholdComparison.AT_LEAST
    assert waiver.window_kind is FeeWaiverWindow.PRECEDING_CARD_YEAR
    assert set(waiver.excluded_categories) == {SpendCategory.UTILITIES, SpendCategory.FUEL}
    assert waiver.waives_joining_fee is False


def test_sbi_cashback_counts_365_days_and_waives_the_renewal_only(
    snapshot: CatalogSnapshot,
) -> None:
    waiver = _waiver(snapshot, "Cashback")
    assert waiver is not None
    assert waiver.threshold_inr == 200_000
    assert waiver.threshold_comparison is ThresholdComparison.AT_LEAST  # "or more"
    assert waiver.window_kind is FeeWaiverWindow.DAYS_365_BEFORE_FEE_DATE
    assert waiver.waives_renewal_fee is True
    assert waiver.waives_joining_fee is False


@pytest.mark.parametrize("card_name", ["Atlas", "Platinum Charge"])
def test_no_waiver_is_a_sourced_answer_with_no_terms(
    snapshot: CatalogSnapshot, card_name: str
) -> None:
    """Atlas: the issuer's waiver row reads "-". Platinum Charge: the ₹20L
    renewal BENEFIT is paid after the fee — a benefit, not a waiver."""
    waiver = _waiver(snapshot, card_name)
    assert waiver is not None
    assert waiver.kind is FeeWaiverKind.NONE
    assert waiver.threshold_inr is None
    assert waiver.waives_renewal_fee is False
    assert waiver.waives_joining_fee is False


# ── Exclusions we cannot log (fix round, 2026-11-02) ─────────────────────
#
# Re-read against each issuer's own waiver terms:
#   HDFC MITC (updated 29 Oct 2026), fee table footnote "* Exclude
#     transactions - Cash on Call, Balance Transfer, Cash Withdrawal".
#   Axis MITC footnote *: rent, wallet, utilities, government, EMI, cash,
#     reversals/fees; from 20 Apr 2024 also insurance, gold, fuel.
#   HSBC and SBI say only "eligible spend" and define it nowhere in the
#     documents reached — so the exclusion is stated as unknown, not empty.


@pytest.mark.parametrize(
    ("card_name", "expected"),
    [
        ("Infinia Metal", ("Cash on Call", "balance transfers", "cash withdrawals")),
        ("Diners Club Black Metal", ("Cash on Call", "balance transfers", "cash withdrawals")),
        ("Regalia Gold", ("Cash on Call", "balance transfers", "cash withdrawals")),
        (
            "Magnus for Burgundy",
            (
                "rent",
                "wallet loads",
                "government payments",
                "EMI conversions",
                "cash withdrawals",
                "insurance",
                "gold",
                "reversals, fees and charges",
            ),
        ),
    ],
)
def test_listed_exclusions_we_cannot_log_are_carried_by_name(
    snapshot: CatalogSnapshot, card_name: str, expected: tuple[str, ...]
) -> None:
    waiver = _waiver(snapshot, card_name)
    assert waiver is not None
    assert waiver.unmodelled_exclusions == expected
    assert waiver.has_unmodelled_exclusions is True


@pytest.mark.parametrize("card_name", ["TravelOne", "Cashback"])
def test_an_undefined_eligible_spend_is_an_unmodelled_exclusion_not_none(
    snapshot: CatalogSnapshot, card_name: str
) -> None:
    """Seeding [] would claim "everything you log counts"; the issuer never
    said that."""
    waiver = _waiver(snapshot, card_name)
    assert waiver is not None
    assert waiver.has_unmodelled_exclusions is True
    assert waiver.excluded_categories == ()  # nothing sourced to model


@pytest.mark.parametrize("card_name", ["Atlas", "Platinum Charge"])
def test_a_no_waiver_row_has_no_exclusions(snapshot: CatalogSnapshot, card_name: str) -> None:
    waiver = _waiver(snapshot, card_name)
    assert waiver is not None
    assert waiver.has_unmodelled_exclusions is False


@pytest.mark.parametrize(
    ("slug", "flagged"),
    [
        # HDFC states the window as "12 billing cycles of your anniversary
        # year" (Regalia Gold fees page) — how cycles align to the renewal is
        # unstated, so the month-only subset proof is not established.
        ("hdfc-infinia", True),
        ("hdfc-diners-black", True),
        ("hdfc-regalia-gold", True),
        # Service guide "exceeds ₹800,000" vs KFS "₹800,000 or more"; and
        # "eligible spend" undefined.
        ("hsbc-travelone", True),
        # "Eligible spends" undefined in the MITC and T&C reached.
        ("sbi-cashback", True),
        ("axis-magnus-burgundy", False),
        ("axis-atlas", False),
        ("amex-platinum-charge", False),
    ],
)
def test_waiver_verification_tier(seed_dir, slug: str, flagged: bool) -> None:  # type: ignore[no-untyped-def]
    assert (seed_id("fee_waiver", slug) in load_unverified_ids(seed_dir)) is flagged


def test_platinum_travel_is_not_covered_rather_than_claimed_waiverless(
    snapshot: CatalogSnapshot,
) -> None:
    """The issuer page lists the fee and says nothing either way — absence of
    a published waiver is not a published absence of one."""
    assert _waiver(snapshot, "Platinum Travel") is None


def test_fee_waivers_are_covered_by_the_provenance_index(snapshot: CatalogSnapshot) -> None:
    """Rows in a collection the index does not walk would read as verified by
    omission."""
    assert "fee_waivers" in PROVENANCE_COLLECTIONS
    ids = snapshot_row_ids(snapshot)
    assert all(w.id in ids for w in snapshot.fee_waivers)


# ── Catalog rules ────────────────────────────────────────────────────────


def _spend_based(snapshot: CatalogSnapshot, **overrides: object) -> FeeWaiver:
    base: dict[str, object] = dict(
        id=seed_id("fee_waiver", "test"),
        card_id=next(c.id for c in snapshot.cards if c.card_name == "Atlas"),
        kind=FeeWaiverKind.SPEND_BASED,
        threshold_inr=500_000,
        threshold_comparison=ThresholdComparison.AT_LEAST,
        window_kind=FeeWaiverWindow.PRECEDING_CARD_YEAR,
        waives_renewal_fee=True,
    )
    return FeeWaiver(**{**base, **overrides})  # type: ignore[arg-type]


def _with(snapshot: CatalogSnapshot, *rows: FeeWaiver) -> CatalogSnapshot:
    return snapshot.model_copy(update={"fee_waivers": rows})


def test_the_seeded_waivers_pass(snapshot: CatalogSnapshot) -> None:
    validate_catalog(snapshot)


def test_a_waiver_must_belong_to_a_real_card(snapshot: CatalogSnapshot) -> None:
    orphan = _spend_based(snapshot, card_id=seed_id("card", "no-such-card"))
    with pytest.raises(CatalogValidationError, match="FW-01"):
        validate_catalog(_with(snapshot, orphan))


def test_a_card_has_at_most_one_waiver(snapshot: CatalogSnapshot) -> None:
    """Two rows would mean two answers to one question — which applies?"""
    first = _spend_based(snapshot)
    second = _spend_based(snapshot, id=seed_id("fee_waiver", "test-2"), threshold_inr=1)
    with pytest.raises(CatalogValidationError, match="FW-02"):
        validate_catalog(_with(snapshot, first, second))


@pytest.mark.parametrize("missing", ["threshold_inr", "threshold_comparison", "window_kind"])
def test_a_spend_based_waiver_must_state_all_its_terms(
    snapshot: CatalogSnapshot, missing: str
) -> None:
    """ "₹4L" without the window, or without whether ₹4L exactly counts, is
    not a condition anyone can check progress against."""
    with pytest.raises(CatalogValidationError, match="FW-03"):
        validate_catalog(_with(snapshot, _spend_based(snapshot, **{missing: None})))


def test_a_spend_based_waiver_must_waive_something(snapshot: CatalogSnapshot) -> None:
    with pytest.raises(CatalogValidationError, match="FW-03"):
        validate_catalog(_with(snapshot, _spend_based(snapshot, waives_renewal_fee=False)))


@pytest.mark.parametrize(
    "extra",
    [
        {"threshold_inr": 100_000},
        {"threshold_comparison": ThresholdComparison.AT_LEAST},
        {"window_kind": FeeWaiverWindow.PRECEDING_CARD_YEAR},
        {"waives_renewal_fee": True},
        {"excluded_categories": (SpendCategory.FUEL,)},
        {"unmodelled_exclusions": ("rent",)},
    ],
)
def test_a_no_waiver_row_carries_no_terms(snapshot: CatalogSnapshot, extra: dict) -> None:
    """A NONE row with a threshold is two contradictory answers in one row."""
    blank: dict[str, object] = dict(
        kind=FeeWaiverKind.NONE,
        threshold_inr=None,
        threshold_comparison=None,
        window_kind=None,
        waives_renewal_fee=False,
    )
    row = _spend_based(snapshot, **{**blank, **extra})
    with pytest.raises(CatalogValidationError, match="FW-03"):
        validate_catalog(_with(snapshot, row))
