from datetime import datetime, timezone

import pytest

from app.domain.events import (
    CheckoutAbandonmentEvent,
    PaymentFailureEvent,
    ReceivableOverdueEvent,
)
from app.domain.models import (
    RecoveryItem,
    RecoveryStatus,
    SourceType,
)


def test_recovery_item_creation():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    item = RecoveryItem(
        id="ri_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_1",
        customer_id="C_1",
        amount_minor=10000,
        currency="INR",
        created_at=now,
        due_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="temporary_processing",
        recovery_probability=0.5,
        expected_recovery_value=5000,
    )
    assert item.id == "ri_1"
    assert item.source_type == SourceType.PAYMENT_FAILURE
    assert item.amount_minor == 10000
    assert item.recovery_probability == 0.5
    assert item.status == RecoveryStatus.DETECTED


def test_recovery_item_defaults():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    item = RecoveryItem(
        id="ri_2",
        source_type=SourceType.RECEIVABLE,
        external_id="ext_2",
        customer_id="C_2",
        amount_minor=0,
        currency="INR",
        created_at=now,
    )
    assert item.status == RecoveryStatus.DETECTED
    assert item.root_cause is None
    assert item.recovery_probability is None
    assert item.expected_recovery_value is None
    assert item.metadata == {}


def test_recovery_item_validates_negative_amount():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="amount_minor must be non-negative"):
        RecoveryItem(
            id="ri_3",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_3",
            customer_id="C_3",
            amount_minor=-1,
            currency="INR",
            created_at=now,
        )


def test_recovery_item_validates_currency_length():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="currency must be a non-empty 3-letter code"):
        RecoveryItem(
            id="ri_4",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_4",
            customer_id="C_4",
            amount_minor=100,
            currency="IN",
            created_at=now,
        )


def test_recovery_item_validates_probability_range():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="recovery_probability must be between 0.0 and 1.0"):
        RecoveryItem(
            id="ri_5",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_5",
            customer_id="C_5",
            amount_minor=100,
            currency="INR",
            created_at=now,
            recovery_probability=1.5,
        )


def test_source_type_values():
    assert SourceType.PAYMENT_FAILURE.value == "payment_failure"
    assert SourceType.RECEIVABLE.value == "receivable"
    assert SourceType.CHECKOUT_ABANDONMENT.value == "checkout_abandonment"


def test_recovery_status_values():
    assert RecoveryStatus.DETECTED.value == "detected"
    assert RecoveryStatus.RECOVERED.value == "recovered"
    assert RecoveryStatus.STOPPED.value == "stopped"
