from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    """Compact context for the RecoveryDecisionAgent.

    Contains only the information needed to make a recovery proposal.
    Deliberately excludes raw payloads, secrets, and unrelated data.
    """

    failure_category: FailureCategory
    retryable: bool
    attempt_count: int
    amount_minor: int
    currency: str
    expected_recovery_value: int | None
    customer_opt_out: bool
    previous_actions: list[str] = field(default_factory=list)
    failure_code: str = ""
    failure_reason: str = ""
    payment_method: str = ""
    max_attempts: int = 3
    item_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_item_and_failure(
        cls,
        item: RecoveryItem,
        failure: NormalizedFailure,
        *,
        attempt_count: int = 0,
        customer_opt_out: bool = False,
        previous_actions: list[str] | None = None,
        max_attempts: int = 3,
    ) -> RecoveryContext:
        return cls(
            failure_category=failure.category,
            retryable=failure.retryable,
            attempt_count=attempt_count,
            amount_minor=item.amount_minor,
            currency=item.currency,
            expected_recovery_value=item.expected_recovery_value,
            customer_opt_out=customer_opt_out,
            previous_actions=previous_actions or [],
            failure_code=failure.code,
            failure_reason=failure.reason,
            payment_method=failure.metadata.get("payment_method", ""),
            max_attempts=max_attempts,
            item_id=item.id,
            metadata={**item.metadata, "source_type": item.source_type.value},
        )
