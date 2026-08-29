from __future__ import annotations

from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction


class RecoveryProbabilityModel:
    """Deterministic recovery probability estimator.

    Probability is derived from:
    - failure category
    - proposed intervention action
    - attempt number (retries degrade probability)

    The LLM never determines this number.
    """

    _BASE_PROBABILITIES: dict[tuple[str, str], float] = {
        # (failure_category, action) → base probability
        ("soft", "retry_payment"): 0.70,
        ("soft", "send_payment_link"): 0.60,
        ("soft", "send_customer_message"): 0.50,
        ("soft", "escalate_human"): 0.40,
        ("soft", "stop_recovery"): 0.00,
        ("hard", "retry_payment"): 0.35,
        ("hard", "send_payment_link"): 0.45,
        ("hard", "send_customer_message"): 0.30,
        ("hard", "escalate_human"): 0.50,
        ("hard", "stop_recovery"): 0.00,
        ("fraud", "retry_payment"): 0.00,
        ("fraud", "send_payment_link"): 0.00,
        ("fraud", "send_customer_message"): 0.00,
        ("fraud", "escalate_human"): 0.20,
        ("fraud", "stop_recovery"): 0.00,
        ("authentication_required", "retry_payment"): 0.20,
        ("authentication_required", "send_payment_link"): 0.25,
        ("authentication_required", "send_customer_message"): 0.15,
        ("authentication_required", "escalate_human"): 0.30,
        ("authentication_required", "stop_recovery"): 0.00,
        ("unknown", "retry_payment"): 0.10,
        ("unknown", "send_payment_link"): 0.15,
        ("unknown", "send_customer_message"): 0.10,
        ("unknown", "escalate_human"): 0.20,
        ("unknown", "stop_recovery"): 0.00,
    }

    _RETRY_DEGRADATION_PER_ATTEMPT: float = 0.15
    _MIN_PROBABILITY: float = 0.00
    _MAX_PROBABILITY: float = 1.00

    def estimate(
        self,
        failure_category: str,
        proposed_action: str,
        attempt_number: int = 1,
    ) -> float:
        """Estimate recovery probability for a given failure/action combination.

        Args:
            failure_category: Normalized failure category (e.g., "soft", "hard").
            proposed_action: Proposed intervention action (e.g., "retry_payment").
            attempt_number: 1-indexed attempt number. Higher attempts reduce probability.

        Returns:
            Probability between 0.0 and 1.0.
        """
        category = failure_category or "unknown"
        action = proposed_action or "escalate_human"
        base = self._BASE_PROBABILITIES.get((category, action))
        if base is None:
            # Fallback: use action-only default or escalate_human default
            base = self._BASE_PROBABILITIES.get((category, "escalate_human"), 0.10)

        # Degrade probability for retries after the first attempt
        degradation = (attempt_number - 1) * self._RETRY_DEGRADATION_PER_ATTEMPT
        probability = base - degradation

        # Clamp to valid range
        probability = max(self._MIN_PROBABILITY, min(self._MAX_PROBABILITY, probability))
        return probability
