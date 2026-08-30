from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    PAYMENT_FAILURE = "payment_failure"
    RECEIVABLE = "receivable"
    OVERDUE_RECEIVABLE = "overdue_receivable"
    CHECKOUT_ABANDONMENT = "checkout_abandonment"
    SUBSCRIPTION_FAILURE = "subscription_failure"
    MANDATE_FAILURE = "mandate_failure"
    PROMISE_TO_PAY = "promise_to_pay"


class RecoveryStatus(StrEnum):
    DETECTED = "detected"
    DIAGNOSED = "diagnosed"
    QUEUED = "queued"
    INTERVENTION_PENDING = "intervention_pending"
    INTERVENTION_EXECUTED = "intervention_executed"
    RECOVERED = "recovered"
    FAILED = "failed"
    ESCALATED = "escalated"
    STOPPED = "stopped"


class OutcomeType(StrEnum):
    RECOVERED = "recovered"
    PARTIALLY_RECOVERED = "partially_recovered"
    FAILED = "failed"
    STOPPED = "stopped"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class PromiseStatus(StrEnum):
    PROMISED = "promised"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ProviderEventStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class RecoveryItem:
    """Canonical representation of any piece of revenue currently at risk."""

    id: str
    source_type: SourceType
    external_id: str
    customer_id: str
    amount_minor: int
    currency: str
    created_at: datetime
    due_at: datetime | None = None
    status: RecoveryStatus = RecoveryStatus.DETECTED
    root_cause: str | None = None
    recovery_probability: float | None = None
    expected_recovery_value: int | None = None
    intervention_cost: int | None = None
    failure_category: str | None = None
    provider: str | None = None
    provider_event_id: str | None = None
    actual_recovery_value: int | None = None
    recovery_status: str | None = None
    score_version: str | None = None
    scoring_reason: str | None = None
    priority: str | None = None
    stopped_reason: str | None = None
    stopped_rule: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be a non-empty 3-letter code")
        if self.recovery_probability is not None:
            if not (0.0 <= self.recovery_probability <= 1.0):
                raise ValueError("recovery_probability must be between 0.0 and 1.0")
        if self.actual_recovery_value is not None and self.actual_recovery_value < 0:
            raise ValueError("actual_recovery_value must be non-negative")
        if self.intervention_cost is not None and self.intervention_cost < 0:
            raise ValueError("intervention_cost must be non-negative")


@dataclass(frozen=True, slots=True)
class RecoveryOutcome:
    """Authoritative financial outcome record for a recovery item."""

    id: str
    recovery_item_id: str
    outcome_type: str
    expected_recovery_minor: int
    actual_recovery_minor: int | None = None
    recovery_cost_minor: int = 0
    net_recovery_minor: int | None = None
    recovered_at: datetime | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.actual_recovery_minor is not None:
            if self.actual_recovery_minor < 0:
                raise ValueError("actual_recovery_minor must be non-negative")
            amount_at_risk = self.metadata.get("amount_at_risk") if isinstance(self.metadata, dict) else None
            if amount_at_risk is not None and isinstance(amount_at_risk, int) and amount_at_risk > 0:
                if self.actual_recovery_minor > amount_at_risk:
                    object.__setattr__(self, "actual_recovery_minor", amount_at_risk)
        if self.recovery_cost_minor < 0:
            raise ValueError("recovery_cost_minor must be non-negative")
        if self.actual_recovery_minor is not None and self.net_recovery_minor is None:
            object.__setattr__(self, "net_recovery_minor", self.actual_recovery_minor - self.recovery_cost_minor)


@dataclass(frozen=True, slots=True)
class Promise:
    """Promise-to-pay record linked to a recovery item."""

    id: str
    recovery_item_id: str
    customer_id: str
    promised_amount_minor: int
    promised_date: date
    status: str = PromiseStatus.PROMISED.value
    created_at: datetime | None = None
    fulfilled_at: datetime | None = None
    expired_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderEvent:
    """Raw provider event for durable idempotent ingestion."""

    id: str
    provider: str
    provider_event_id: str
    received_at: datetime
    event_type: str
    raw_payload: dict[str, Any]
    processing_status: str = ProviderEventStatus.PENDING.value
    processed_at: datetime | None = None
    recovery_item_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
