from __future__ import annotations

from typing import Protocol

from app.domain.models import RecoveryItem


class RecoveryScorer(Protocol):
    """Assigns an expected recovery value to a RecoveryItem."""

    def score(self, item: RecoveryItem) -> int:
        """Return expected recovery value in the same minor units as item.amount_minor."""
        ...


class ExpectedValueScorer:
    """Deterministic expected-value scorer.

    Formula: expected_recovery_value = amount_minor * recovery_probability
    """

    def score(self, item: RecoveryItem) -> int:
        if item.recovery_probability is None:
            raise ValueError("recovery_probability must be set before scoring")
        return int(item.amount_minor * item.recovery_probability)
