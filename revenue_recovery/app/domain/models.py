from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class SourceType(StrEnum):
    PAYMENT_FAILURE = "payment_failure"
    RECEIVABLE = "receivable"
    CHECKOUT_ABANDONMENT = "checkout_abandonment"


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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be a non-empty 3-letter code")
        if self.recovery_probability is not None:
            if not (0.0 <= self.recovery_probability <= 1.0):
                raise ValueError("recovery_probability must be between 0.0 and 1.0")
