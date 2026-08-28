from __future__ import annotations

from app.adapters.razorpay.events import RazorpayPaymentFailure
from app.domain.failures import FailureCategory, NormalizedFailure


class RazorpayFailureClassifier:
    """Maps Razorpay payment failure information to internal failure categories.

    The mapping is intentionally small and explicit. Unmapped codes fall through
    to UNKNOWN, which is never treated as automatically retryable.
    """

    _SOFT_CODES = {
        "payment_timed_out",
        "gateway_technical_error",
        "bank_technical_error",
        "bank_downtime",
    }

    _HARD_CODES = {
        "card_declined",
        "payment_failed",
        "payment_cancelled",
        "card_expired",
        "card_not_enrolled",
        "card_disabled_for_online_payments",
        "incorrect_cvv",
        "debit_instrument_inactive",
        "debit_instrument_blocked",
        "transaction_limit_exceeded",
    }

    _AUTHENTICATION_CODES = {
        "authentication_failed",
    }

    _FRAUD_CODES = {
        "payment_risk_check_failed",
    }

    def classify(self, failure: RazorpayPaymentFailure) -> NormalizedFailure:
        code = (failure.error_reason or failure.error_code or "unknown").lower()
        source = (failure.error_source or "").lower()
        description = (failure.error_description or "").lower()

        if code in self._FRAUD_CODES or "fraud" in description or source == "risk":
            category = FailureCategory.FRAUD
        elif code in self._AUTHENTICATION_CODES:
            category = FailureCategory.AUTHENTICATION_REQUIRED
        elif code in self._SOFT_CODES:
            category = FailureCategory.SOFT
        elif code in self._HARD_CODES:
            category = FailureCategory.HARD
        else:
            category = FailureCategory.UNKNOWN

        reason = failure.error_description or code or "unknown"
        return NormalizedFailure(
            external_event_id=failure.razorpay_event_id,
            external_payment_id=failure.razorpay_payment_id,
            category=category,
            code=code,
            reason=reason,
            retryable=(category == FailureCategory.SOFT),
            metadata={
                "error_source": failure.error_source,
                "error_step": failure.error_step,
                "error_reason": failure.error_reason,
                "payment_method": failure.payment_method,
                "currency": failure.currency,
                "amount_minor": failure.amount_minor,
            },
        )
