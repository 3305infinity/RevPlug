from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RecoveryEvent:
    """Base internal domain event.

    External provider-specific details must be normalized into this shape
    before entering the domain layer.
    """

    external_event_id: str
    occurred_at: datetime
    customer_id: str
    raw_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PaymentFailureEvent(RecoveryEvent):
    """Normalized payment failure event.

    Provider-agnostic. Adapters translate Razorpay / Stripe / etc. into this.
    """

    amount_minor: int = 0
    currency: str = ""
    provider_error_code: str | None = None
    reason_code: str | None = None
    external_payment_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReceivableOverdueEvent(RecoveryEvent):
    """Normalized overdue receivable event."""

    amount_minor: int = 0
    currency: str = ""
    invoice_id: str = ""
    days_overdue: int = 0
    due_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CheckoutAbandonmentEvent(RecoveryEvent):
    """Normalized checkout abandonment event."""

    cart_id: str = ""
    cart_value_minor: int = 0
    currency: str = ""
    stage: str = ""
    item_count: int = 0
