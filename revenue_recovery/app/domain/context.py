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
    retryable: bool = True
    attempt_count: int = 0
    amount_minor: int = 100000
    currency: str = "INR"
    expected_recovery_value: int | None = None
    customer_opt_out: bool = False
    previous_actions: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    failure_code: str = ""
    failure_reason: str = ""
    payment_method: str = ""
    max_attempts: int = 3
    item_id: str = ""
    customer_profile: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def last_observation(self) -> dict[str, Any] | None:
        """Return the most recent execution observation if available."""
        return self.observations[-1] if self.observations else None

    def with_observation(self, observation: dict[str, Any]) -> RecoveryContext:
        """Return a new RecoveryContext with an added observation and action history."""
        from dataclasses import replace
        action = observation.get("action")
        new_actions = list(self.previous_actions)
        if action and (not new_actions or new_actions[-1] != action):
            new_actions.append(action)
        new_observations = list(self.observations) + [observation]
        return replace(
            self,
            previous_actions=new_actions,
            observations=new_observations,
            attempt_count=self.attempt_count + 1 if action else self.attempt_count,
        )

    @classmethod
    def from_item_and_failure(
        cls,
        item: RecoveryItem,
        failure: NormalizedFailure,
        *,
        attempt_count: int = 0,
        customer_opt_out: bool = False,
        previous_actions: list[str] | None = None,
        observations: list[dict[str, Any]] | None = None,
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
            observations=observations or item.metadata.get("observations", []),
            failure_code=failure.code,
            failure_reason=failure.reason,
            payment_method=failure.metadata.get("payment_method", ""),
            max_attempts=max_attempts,
            item_id=item.id,
            metadata={**item.metadata, "source_type": item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type)},
        )
