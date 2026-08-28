from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import copy
import json
import pytest

from app.adapters.razorpay.classifier import RazorpayFailureClassifier
from app.adapters.razorpay.events import RazorpayEventError, RazorpayPaymentFailure, parse_razorpay_event
from app.adapters.razorpay.signatures import RazorpaySignatureError, verify_razorpay_signature
from app.domain.failures import FailureCategory


# ---------------------------------------------------------------------------
# Test fixtures — representative Razorpay payment.failed payloads
# ---------------------------------------------------------------------------

_SOFT_FAILURE_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_soft_001",
    "created_at": 1567610215,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_soft_001",
                "entity": "payment",
                "amount": 50000,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed",
                "error_source": "bank",
                "error_step": "payment_authorization",
                "error_reason": "payment_timed_out",
                "email": "test@example.com",
                "contact": "+919876543210",
                "created_at": 1567610214,
            }
        }
    },
}

_HARD_FAILURE_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_hard_001",
    "created_at": 1567610215,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_hard_001",
                "entity": "payment",
                "amount": 25000,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Card declined by bank",
                "error_source": "bank",
                "error_step": "payment_authorization",
                "error_reason": "card_declined",
                "email": "test@example.com",
                "contact": "+919876543210",
                "created_at": 1567610214,
            }
        }
    },
}

_AUTH_FAILURE_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_auth_001",
    "created_at": 1567610215,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_auth_001",
                "entity": "payment",
                "amount": 10000,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Authentication failed",
                "error_source": "customer",
                "error_step": "payment_authentication",
                "error_reason": "authentication_failed",
                "email": "test@example.com",
                "contact": "+919876543210",
                "created_at": 1567610214,
            }
        }
    },
}

_FRAUD_FAILURE_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_fraud_001",
    "created_at": 1567610215,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_fraud_001",
                "entity": "payment",
                "amount": 75000,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Risk check failed",
                "error_source": "risk",
                "error_step": "payment_authorization",
                "error_reason": "payment_risk_check_failed",
                "email": "test@example.com",
                "contact": "+919876543210",
                "created_at": 1567610214,
            }
        }
    },
}

_UNKNOWN_FAILURE_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_unknown_001",
    "created_at": 1567610215,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_unknown_001",
                "entity": "payment",
                "amount": 30000,
                "currency": "INR",
                "status": "failed",
                "method": "upi",
                "error_code": "UNKNOWN_CODE",
                "error_description": "Something went wrong",
                "error_source": "unknown",
                "error_step": "unknown",
                "error_reason": "unknown_reason",
                "email": "test@example.com",
                "contact": "+919876543210",
                "created_at": 1567610214,
            }
        }
    },
}


def _sign(body: bytes, secret: str) -> str:
    import hashlib, hmac
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------

class TestSignatureVerification:
    SECRET = "whsec_test_secret"
    BODY = b'{"test": "payload"}'

    def test_valid_signature(self):
        sig = _sign(self.BODY, self.SECRET)
        verify_razorpay_signature(self.BODY, sig, self.SECRET)

    def test_invalid_signature_raises(self):
        with pytest.raises(RazorpaySignatureError, match="mismatch"):
            verify_razorpay_signature(self.BODY, "invalid_signature_hex", self.SECRET)

    def test_missing_signature_raises(self):
        with pytest.raises(RazorpaySignatureError, match="Missing"):
            verify_razorpay_signature(self.BODY, None, self.SECRET)

    def test_empty_signature_raises(self):
        with pytest.raises(RazorpaySignatureError, match="Missing"):
            verify_razorpay_signature(self.BODY, "   ", self.SECRET)

    def test_missing_secret_raises(self):
        with pytest.raises(RazorpaySignatureError, match="not configured"):
            verify_razorpay_signature(self.BODY, "sig", "")

    def test_empty_body_raises(self):
        with pytest.raises(RazorpaySignatureError, match="empty"):
            verify_razorpay_signature(b"", "sig", self.SECRET)

    def test_modified_payload_fails(self):
        sig = _sign(self.BODY, self.SECRET)
        modified = self.BODY + b'{"tampered": true}'
        with pytest.raises(RazorpaySignatureError, match="mismatch"):
            verify_razorpay_signature(modified, sig, self.SECRET)

    def test_signature_does_not_leak_secret(self):
        try:
            verify_razorpay_signature(self.BODY, "bad", self.SECRET)
        except RazorpaySignatureError as exc:
            assert self.SECRET not in str(exc)
            assert "whsec" not in str(exc)


# ---------------------------------------------------------------------------
# Event parsing tests
# ---------------------------------------------------------------------------

class TestEventParsing:
    def test_soft_failure_parses(self):
        failure = parse_razorpay_event(json.dumps(_SOFT_FAILURE_PAYLOAD).encode())
        assert failure.razorpay_event_id == "evt_soft_001"
        assert failure.razorpay_payment_id == "pay_soft_001"
        assert failure.amount_minor == 50000
        assert failure.currency == "INR"
        assert failure.error_reason == "payment_timed_out"

    def test_hard_failure_parses(self):
        failure = parse_razorpay_event(json.dumps(_HARD_FAILURE_PAYLOAD).encode())
        assert failure.error_reason == "card_declined"
        assert failure.error_source == "bank"

    def test_auth_failure_parses(self):
        failure = parse_razorpay_event(json.dumps(_AUTH_FAILURE_PAYLOAD).encode())
        assert failure.error_reason == "authentication_failed"
        assert failure.error_step == "payment_authentication"

    def test_unsupported_event_raises(self):
        payload = copy.deepcopy(_SOFT_FAILURE_PAYLOAD)
        payload["event"] = "payment.captured"
        with pytest.raises(RazorpayEventError, match="Unsupported"):
            parse_razorpay_event(json.dumps(payload).encode())

    def test_invalid_json_raises(self):
        with pytest.raises(RazorpayEventError, match="Invalid JSON"):
            parse_razorpay_event(b"not json")

    def test_missing_payment_entity_raises(self):
        payload = copy.deepcopy(_SOFT_FAILURE_PAYLOAD)
        payload["payload"] = {}
        with pytest.raises(RazorpayEventError, match="Missing"):
            parse_razorpay_event(json.dumps(payload).encode())

    def test_non_integer_amount_raises(self):
        payload = copy.deepcopy(_SOFT_FAILURE_PAYLOAD)
        payload["payload"]["payment"]["entity"]["amount"] = "not_an_int"
        with pytest.raises(RazorpayEventError, match="integer"):
            parse_razorpay_event(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# Failure classification tests
# ---------------------------------------------------------------------------

class TestFailureClassification:
    classifier = RazorpayFailureClassifier()

    def test_soft_failure_maps_to_soft(self):
        failure = parse_razorpay_event(json.dumps(_SOFT_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.category == FailureCategory.SOFT
        assert result.retryable is True

    def test_hard_failure_maps_to_hard(self):
        failure = parse_razorpay_event(json.dumps(_HARD_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.category == FailureCategory.HARD
        assert result.retryable is False

    def test_auth_failure_maps_to_authentication_required(self):
        failure = parse_razorpay_event(json.dumps(_AUTH_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.category == FailureCategory.AUTHENTICATION_REQUIRED
        assert result.retryable is False

    def test_fraud_failure_maps_to_fraud(self):
        failure = parse_razorpay_event(json.dumps(_FRAUD_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.category == FailureCategory.FRAUD
        assert result.retryable is False

    def test_unknown_failure_maps_to_unknown(self):
        failure = parse_razorpay_event(json.dumps(_UNKNOWN_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.category == FailureCategory.UNKNOWN
        assert result.retryable is False

    def test_unknown_is_not_retryable(self):
        failure = parse_razorpay_event(json.dumps(_UNKNOWN_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.retryable is False

    def test_classification_preserves_metadata(self):
        failure = parse_razorpay_event(json.dumps(_SOFT_FAILURE_PAYLOAD).encode())
        result = self.classifier.classify(failure)
        assert result.metadata["payment_method"] == "card"
        assert result.metadata["currency"] == "INR"
        assert result.metadata["amount_minor"] == 50000
