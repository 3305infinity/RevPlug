from datetime import datetime, timezone

import pytest

from app.domain.events import (
    CheckoutAbandonmentEvent,
    PaymentFailureEvent,
    ReceivableOverdueEvent,
)


def test_payment_failure_event():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    event = PaymentFailureEvent(
        external_event_id="evt_1",
        occurred_at=now,
        customer_id="C_1",
        amount_minor=10000,
        currency="INR",
        provider_error_code="E0001",
        reason_code="temporary_processing",
        external_payment_id="pay_1",
    )
    assert event.external_event_id == "evt_1"
    assert event.amount_minor == 10000
    assert event.reason_code == "temporary_processing"
    assert event.external_payment_id == "pay_1"


def test_payment_failure_event_no_razorpay_fields():
    """Ensure provider-specific fields are not required."""
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    event = PaymentFailureEvent(
        external_event_id="evt_2",
        occurred_at=now,
        customer_id="C_2",
    )
    assert event.provider_error_code is None
    assert event.reason_code is None
    assert event.external_payment_id is None


def test_receivable_overdue_event():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    event = ReceivableOverdueEvent(
        external_event_id="evt_3",
        occurred_at=now,
        customer_id="C_3",
        amount_minor=50000,
        currency="INR",
        invoice_id="inv_1",
        days_overdue=14,
        due_at=now,
    )
    assert event.invoice_id == "inv_1"
    assert event.days_overdue == 14


def test_checkout_abandonment_event():
    now = datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)
    event = CheckoutAbandonmentEvent(
        external_event_id="evt_4",
        occurred_at=now,
        customer_id="C_4",
        cart_id="cart_1",
        cart_value_minor=25000,
        currency="INR",
        stage="payment_info",
        item_count=2,
    )
    assert event.cart_id == "cart_1"
    assert event.stage == "payment_info"
    assert event.item_count == 2
