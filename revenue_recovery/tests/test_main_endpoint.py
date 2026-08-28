from __future__ import annotations

import copy
import hashlib
import hmac
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.adapters.razorpay import RazorpayWebhookService
from app.audit.models import InMemoryAuditLog
from app.idempotency.store import InMemoryIdempotencyStore
from app.policies.engine import InterventionPolicy
from app.scoring.expected_value import ExpectedValueScorer


# ---------------------------------------------------------------------------
# Synthetic Razorpay payment.failed payloads (mirrors test_razorpay_adapter.py)
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


SECRET = "whsec_test_secret_for_endpoint"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def service() -> RazorpayWebhookService:
    """A fresh webhook service for each test, with in-memory dependencies."""
    return RazorpayWebhookService(
        webhook_secret=SECRET,
        scorer=ExpectedValueScorer(),
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=InMemoryAuditLog(),
        idempotency_store=InMemoryIdempotencyStore(),
    )


@pytest.fixture
def app(service):
    """A fresh FastAPI app wired with the fresh service."""
    return main_module.create_app(webhook_secret=SECRET, webhook_service=service)


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Import smoke test — uses the module-level singleton
# ---------------------------------------------------------------------------

class TestAppImport:
    def test_app_imports_successfully(self):
        """The app module must import and expose a FastAPI instance."""
        assert isinstance(main_module.app, FastAPI)
        assert main_module.app.title == "Recovery Engine"

    def test_module_app_has_razorpay_route(self):
        """The module-level `app` must always include /webhooks/razorpay."""
        paths = [r.path for r in main_module.app.routes]
        assert "/webhooks/razorpay" in paths

    def test_module_app_has_health_route(self):
        """The module-level `app` must always include /health."""
        paths = [r.path for r in main_module.app.routes]
        assert "/health" in paths

    def test_module_razorpay_route_accepts_post(self):
        """The /webhooks/razorpay route must accept POST."""
        for r in main_module.app.routes:
            if r.path == "/webhooks/razorpay":
                assert "POST" in r.methods
                return
        pytest.fail("Route /webhooks/razorpay not found on module-level app")

    def test_create_app_returns_fresh_fastapi(self):
        """create_app must return a new FastAPI app each time."""
        a = main_module.create_app(webhook_secret=SECRET)
        b = main_module.create_app(webhook_secret=SECRET)
        assert a is not b
        assert isinstance(a, FastAPI)
        assert isinstance(b, FastAPI)

    def test_created_app_has_razorpay_route(self):
        fresh = main_module.create_app(webhook_secret=SECRET)
        paths = [r.path for r in fresh.routes]
        assert "/webhooks/razorpay" in paths

    def test_created_app_has_health_route(self):
        fresh = main_module.create_app(webhook_secret=SECRET)
        paths = [r.path for r in fresh.routes]
        assert "/health" in paths

    def test_razorpay_route_accepts_post(self):
        fresh = main_module.create_app(webhook_secret=SECRET)
        for r in fresh.routes:
            if r.path == "/webhooks/razorpay":
                assert "POST" in r.methods
                return
        pytest.fail("Route /webhooks/razorpay not found")


# ---------------------------------------------------------------------------
# Valid webhook
# ---------------------------------------------------------------------------

class TestValidWebhook:
    def test_valid_webhook_returns_200(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 200

    def test_valid_webhook_reaches_service(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        data = resp.json()
        assert data["status"] == "processed"
        assert data["recovery_item_id"] == "pay_soft_001"
        assert data["failure_category"] == "soft"
        assert data["expected_recovery_value"] is not None
        assert data["audit_event_count"] > 0

    def test_valid_webhook_uses_raw_bytes_not_reserialized_json(self, client):
        """The endpoint must verify against the exact bytes received.

        If the endpoint parsed and re-serialized the body, a signature
        computed on the original body would still match (Python's json
        output is deterministic for dicts with sorted keys at most). The
        definitive proof: add a trailing space to the body — the original
        signature must no longer match, proving the raw bytes are used.
        """
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        tampered = body + b" "
        resp = client.post(
            "/webhooks/razorpay",
            content=tampered,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400

    def test_valid_webhook_then_duplicate_returns_200_duplicate(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        first = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert first.json()["status"] == "processed"
        second = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"


# ---------------------------------------------------------------------------
# Invalid signature
# ---------------------------------------------------------------------------

class TestInvalidSignature:
    def test_invalid_signature_returns_400(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "deadbeef" * 8},
        )
        assert resp.status_code == 400

    def test_invalid_signature_does_not_reach_service(self, client):
        """An invalid signature must be rejected before any domain processing."""
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "0" * 64},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["status"] == "rejected"
        assert "signature" in data["reason"]

    def test_modified_body_with_valid_signature_returns_400(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        tampered = json.dumps(dict(_SOFT_FAILURE_PAYLOAD, id="evt_tampered")).encode()
        resp = client.post(
            "/webhooks/razorpay",
            content=tampered,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400

    def test_wrong_secret_signature_returns_400(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body, secret="wrong_secret")
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Missing signature
# ---------------------------------------------------------------------------

class TestMissingSignature:
    def test_missing_signature_header_returns_400(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post("/webhooks/razorpay", content=body)
        assert resp.status_code == 400

    def test_missing_signature_does_not_reach_service(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post("/webhooks/razorpay", content=body)
        data = resp.json()
        assert data["status"] == "rejected"
        assert "signature" in data["reason"]

    def test_empty_signature_header_returns_400(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": ""},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Malformed payload (signature OK, body invalid)
# ---------------------------------------------------------------------------

class TestMalformedPayload:
    def test_invalid_json_with_valid_signature_returns_422(self, client):
        body = b"not json at all"
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 422

    def test_unsupported_event_type_returns_422(self, client):
        payload = copy.deepcopy(_SOFT_FAILURE_PAYLOAD)
        payload["event"] = "payment.captured"
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 422

    def test_malformed_payload_does_not_create_recovery_item(self, client):
        payload = copy.deepcopy(_SOFT_FAILURE_PAYLOAD)
        payload["payload"] = {}
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 422
        assert resp.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# Secret not logged
# ---------------------------------------------------------------------------

class TestSecretNotLeaked:
    def test_response_body_does_not_contain_secret(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert SECRET not in resp.text
        assert resp.status_code == 200

    def test_error_response_does_not_contain_secret(self, client):
        body = json.dumps(_SOFT_FAILURE_PAYLOAD).encode()
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "bogus"},
        )
        assert SECRET not in resp.text
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Smoke test payload — verifies scripts/smoke_test_razorpay.py is compatible
# ---------------------------------------------------------------------------

_SMOKE_TEST_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_SMOKE_TEST",
    "event": "payment.failed",
    "contains": ["payment"],
    "id": "evt_smoke_001",
    "created_at": 1700000000,
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_smoke_001",
                "entity": "payment",
                "amount": 50000,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed (synthetic smoke test)",
                "error_source": "bank",
                "error_step": "payment_authorization",
                "error_reason": "payment_timed_out",
                "created_at": 1700000000,
            }
        }
    },
}


class TestSmokeTestPayload:
    """The smoke test script sends this exact payload. It must be accepted."""

    def test_smoke_test_payload_is_accepted(self, client):
        body = json.dumps(_SMOKE_TEST_PAYLOAD).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["recovery_item_id"] == "pay_smoke_001"

    def test_smoke_test_payload_uses_raw_bytes_for_signature(self, client):
        """A tampered body with the smoke-test signature must be rejected.

        Proves the endpoint does not re-serialize the JSON before verifying.
        """
        body = json.dumps(_SMOKE_TEST_PAYLOAD).encode()
        sig = _sign(body)
        tampered = body + b" "
        resp = client.post(
            "/webhooks/razorpay",
            content=tampered,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400
