import math
from typing import Any

from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction


class RecoveryProbabilityModel:
    """Deterministic recovery probability estimator.

    Probability is derived from:
    - failure category
    - proposed intervention action
    - attempt number (retries degrade probability)
    - rich recovery context (invoice age, customer opt-out, promise state, history)

    The LLM never determines this number.
    """

    _BASE_PROBABILITIES: dict[tuple[str, str], float] = {
        # (failure_category, action) → base probability
        ("soft", "retry_payment"): 0.70,
        ("soft", "send_payment_link"): 0.80,
        ("soft", "send_customer_message"): 0.50,
        ("soft", "send_reminder"): 0.55,
        ("soft", "alternate_channel"): 0.45,
        ("soft", "escalate_human"): 0.40,
        ("soft", "stop_recovery"): 0.00,
        ("hard", "retry_payment"): 0.20,
        ("hard", "send_payment_link"): 0.55,
        ("hard", "send_customer_message"): 0.30,
        ("hard", "send_reminder"): 0.25,
        ("hard", "alternate_channel"): 0.35,
        ("hard", "escalate_human"): 0.50,
        ("hard", "stop_recovery"): 0.00,
        ("fraud", "retry_payment"): 0.00,
        ("fraud", "send_payment_link"): 0.00,
        ("fraud", "send_customer_message"): 0.00,
        ("fraud", "send_reminder"): 0.00,
        ("fraud", "alternate_channel"): 0.00,
        ("fraud", "escalate_human"): 0.20,
        ("fraud", "stop_recovery"): 0.00,
        ("authentication_required", "retry_payment"): 0.15,
        ("authentication_required", "send_payment_link"): 0.75,
        ("authentication_required", "send_customer_message"): 0.65,
        ("authentication_required", "send_reminder"): 0.30,
        ("authentication_required", "alternate_channel"): 0.45,
        ("authentication_required", "escalate_human"): 0.30,
        ("authentication_required", "stop_recovery"): 0.00,
        ("checkout_abandonment", "retry_payment"): 0.05,
        ("checkout_abandonment", "send_payment_link"): 0.80,
        ("checkout_abandonment", "send_customer_message"): 0.40,
        ("checkout_abandonment", "send_reminder"): 0.30,
        ("checkout_abandonment", "alternate_channel"): 0.25,
        ("checkout_abandonment", "escalate_human"): 0.20,
        ("checkout_abandonment", "stop_recovery"): 0.00,
        ("invoice_overdue", "retry_payment"): 0.10,
        ("invoice_overdue", "send_payment_link"): 0.60,
        ("invoice_overdue", "send_customer_message"): 0.50,
        ("invoice_overdue", "send_reminder"): 0.70,
        ("invoice_overdue", "alternate_channel"): 0.55,
        ("invoice_overdue", "escalate_human"): 0.45,
        ("invoice_overdue", "stop_recovery"): 0.00,
        ("mandate_failure", "retry_payment"): 0.35,
        ("mandate_failure", "send_payment_link"): 0.60,
        ("mandate_failure", "send_customer_message"): 0.40,
        ("mandate_failure", "send_reminder"): 0.35,
        ("mandate_failure", "alternate_channel"): 0.40,
        ("mandate_failure", "escalate_human"): 0.50,
        ("mandate_failure", "stop_recovery"): 0.00,
        ("unknown", "retry_payment"): 0.10,
        ("unknown", "send_payment_link"): 0.15,
        ("unknown", "send_customer_message"): 0.10,
        ("unknown", "send_reminder"): 0.10,
        ("unknown", "alternate_channel"): 0.15,
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
        context: dict[str, Any] | None = None,
    ) -> float:
        """Estimate recovery probability for a given failure/action combination.

        Args:
            failure_category: Normalized failure category (e.g., "soft", "hard").
            proposed_action: Proposed intervention action (e.g., "retry_payment").
            attempt_number: 1-indexed attempt number. Higher attempts reduce probability.
            context: Optional contextual metadata dict.

        Returns:
            Probability between 0.0 and 1.0. Fail-closed to safe bounds.
        """
        try:
            category = str(failure_category or "unknown").lower()
            action = str(proposed_action or "escalate_human").lower()
            ctx = context or {}

            # Hard stop conditions
            if ctx.get("customer_opted_out") or ctx.get("customer_opt_out"):
                return 0.00

            if action == "stop_recovery" or action == "no_action":
                return 0.00

            if category == "fraud" and action != "escalate_human":
                return 0.00

            base = self._BASE_PROBABILITIES.get((category, action))
            if base is None:
                # Fallback: action-only or category default
                base = self._BASE_PROBABILITIES.get((category, "escalate_human"), 0.10)

            # Degrade probability for retries after the first attempt
            degradation = max(0, attempt_number - 1) * self._RETRY_DEGRADATION_PER_ATTEMPT
            probability = base - degradation

            # Contextual adjustments
            days_overdue = ctx.get("days_overdue")
            if days_overdue is not None and isinstance(days_overdue, (int, float)) and days_overdue > 7:
                # Older invoices decay in recoverability
                probability -= min(0.30, (days_overdue - 7) * 0.02)

            checkout_age = ctx.get("checkout_age_minutes")
            if checkout_age is not None and isinstance(checkout_age, (int, float)) and checkout_age > 10080:
                # Stale checkouts (>7 days) have very low recovery chance
                probability = min(probability, 0.05)

            if ctx.get("previous_successful_retries", 0) > 0:
                # Customer has good payment history
                probability += 0.05

            # Empirical historical evidence adjustments
            past_link = ctx.get("past_link_success_rate")
            if past_link is not None and action == "send_payment_link":
                probability += (float(past_link) - 0.5) * 0.20

            past_retry = ctx.get("past_retry_success_rate")
            if past_retry is not None and action == "retry_payment":
                probability += (float(past_retry) - 0.5) * 0.20

            pref_channel = ctx.get("preferred_channel")
            if pref_channel and action in (pref_channel, "alternate_channel" if pref_channel == "whatsapp" else pref_channel):
                probability += 0.10

            # Numerical safety checks
            if math.isnan(probability) or math.isinf(probability):
                probability = 0.10

            # Clamp strictly to [0.0, 1.0]
            return max(self._MIN_PROBABILITY, min(self._MAX_PROBABILITY, probability))
        except Exception:
            # Fail-safe default
            return 0.10
