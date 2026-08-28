from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class RetryDecision:
    allowed: bool
    max_attempts: int
    attempt_number: int
    next_attempt_at: datetime | None
    reason: str
    policy_rule: str


class RetryPolicy(Protocol):
    """Determines whether another recovery attempt is allowed."""

    def evaluate(
        self,
        item: RecoveryItem,
        *,
        category: FailureCategory | None = None,
        occurred_at: datetime | None = None,
    ) -> RetryDecision:
        ...


class DefaultRetryPolicy:
    """Deterministic retry policy with exponential backoff.

    Rules:
    - Soft failures can be retried up to max_attempts.
    - Hard failures, fraud, and authentication-required failures are not retried.
    - Retry count is read from item.metadata["attempt_count"].
    - Backoff: base_delay * 2^(attempt-1), capped at max_delay.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay_seconds: int = 3600,
        max_delay_seconds: int = 86400,
    ) -> None:
        if max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        if max_delay_seconds < base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        self._max_attempts = max_attempts
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds

    def evaluate(
        self,
        item: RecoveryItem,
        *,
        category: FailureCategory | None = None,
        occurred_at: datetime | None = None,
    ) -> RetryDecision:
        attempt_count = int(item.metadata.get("attempt_count", 0))

        if category in {
            FailureCategory.HARD,
            FailureCategory.FRAUD,
            FailureCategory.AUTHENTICATION_REQUIRED,
        }:
            return RetryDecision(
                allowed=False,
                max_attempts=self._max_attempts,
                attempt_number=attempt_count,
                next_attempt_at=None,
                reason=f"Category {category.value} is not retryable",
                policy_rule="block_hard_failure",
            )

        if attempt_count >= self._max_attempts:
            return RetryDecision(
                allowed=False,
                max_attempts=self._max_attempts,
                attempt_number=attempt_count,
                next_attempt_at=None,
                reason=f"Retry budget exhausted ({attempt_count}/{self._max_attempts})",
                policy_rule="retry_limit",
            )

        # Calculate next attempt time with exponential backoff.
        now = occurred_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        delay = self._base_delay * (2 ** attempt_count)
        delay = min(delay, self._max_delay)
        next_at = now + timedelta(seconds=delay)

        return RetryDecision(
            allowed=True,
            max_attempts=self._max_attempts,
            attempt_number=attempt_count + 1,
            next_attempt_at=next_at,
            reason=f"Retry allowed (attempt {attempt_count + 1}/{self._max_attempts})",
            policy_rule="allow_retry",
        )
