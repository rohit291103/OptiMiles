"""Domain-type contracts the pipeline relies on: immutability, honest-default
fields, and enum-enforced vocabulary. Engine calculations get their own TDD
fixtures in later phases — these tests only pin the shared kernel's shape."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain import (
    CapStructure,
    ClarificationRequest,
    ParsedGoalIntent,
    RewardOpportunity,
    SpendCategory,
    TransferPath,
)


def _transfer_path() -> TransferPath:
    return TransferPath(
        currency_id=uuid4(),
        partner_id=uuid4(),
        ratio_from=2,
        ratio_to=1,
        min_transfer_points=1000,
        transfer_fee_inr=0,
        processing_days_min=1,
        processing_days_max=5,
    )


def test_domain_models_are_frozen() -> None:
    intent = ParsedGoalIntent(confidence=0.9)
    with pytest.raises(ValidationError):
        intent.confidence = 0.1  # type: ignore[misc]


def test_every_exported_domain_model_is_frozen() -> None:
    """Immutability is a pipeline invariant (stages never mutate inputs) —
    enforce it for every model the kernel exports, not just the ones with
    behavior tests."""
    from pydantic import BaseModel

    import app.domain as domain

    models = [
        obj
        for name in domain.__all__
        if isinstance(obj := getattr(domain, name), type) and issubclass(obj, BaseModel)
    ]
    assert models, "expected the domain barrel to export Pydantic models"
    for model in models:
        assert model.model_config.get("frozen") is True, f"{model.__name__} must be frozen"


def test_parsed_intent_defaults_are_honest() -> None:
    """No invented values: everything unstated is None/empty, not defaulted."""
    intent = ParsedGoalIntent(confidence=0.5)
    assert intent.destination_city is None
    assert intent.missing_fields == ()
    assert intent.assumed_fields == ()


def test_clarification_requires_at_least_one_question() -> None:
    with pytest.raises(ValidationError):
        ClarificationRequest(questions=(), missing_fields=("destination_city",))


def test_opportunity_rejects_unknown_category_slug() -> None:
    with pytest.raises(ValidationError):
        RewardOpportunity(
            card_id=uuid4(),
            in_wallet=True,
            category_slug="crypto",  # type: ignore[arg-type]
            earn_rate=Decimal("5.00"),
            transfer_path=_transfer_path(),
            effective_miles_per_100inr=Decimal("2.50"),
        )


def test_opportunity_keeps_decimal_precision() -> None:
    opportunity = RewardOpportunity(
        card_id=uuid4(),
        in_wallet=False,
        category_slug=SpendCategory.TRAVEL,
        earn_rate=Decimal("5.00"),
        cap_structure=CapStructure(monthly_cap_inr=100_000),
        transfer_path=_transfer_path(),
        effective_miles_per_100inr=Decimal("2.50"),
    )
    assert opportunity.effective_miles_per_100inr == Decimal("2.50")
    assert isinstance(opportunity.effective_miles_per_100inr, Decimal)


def test_transfer_path_rejects_zero_ratio() -> None:
    with pytest.raises(ValidationError):
        TransferPath(
            currency_id=uuid4(),
            partner_id=uuid4(),
            ratio_from=0,
            ratio_to=1,
            min_transfer_points=1000,
            transfer_fee_inr=0,
            processing_days_min=1,
            processing_days_max=5,
        )
