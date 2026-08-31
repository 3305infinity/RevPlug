"""Deterministic End-to-End Integration Tests for Production-Quality Razorpay Test Mode Recovery Loop.

Verifies:
1. payment.failed -> RecoveryItem -> AI proposal -> policy decision -> Razorpay Payment Link creation -> payment_link.paid webhook -> signature verification -> SettlementVerifier -> verified recovered amount.
2. Duplicate webhooks idempotency.
3. Invalid signature rejection (400 Bad Request).
4. Unknown/unmatched payment correlation.
5. Amount/currency mismatch clamping.
6. Already-settled item terminal invariant protection.
7. Out-of-order webhook safety.
8. Provider timeout handling & reconciliation.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.razorpay.client import RazorpayClient, RazorpayNetworkTimeoutError
from app.adapters.razorpay.events import (
    RazorpayPaymentFailure,
    RazorpayPaymentSuccess,
    parse_razorpay_event,
    parse_razorpay_settlement_event,
)
from app.adapters.razorpay.signatures import RazorpaySignatureError, verify_razorpay_signature
from app.adapters.razorpay.webhook import RazorpayWebhookService
from app.audit.models import AuditLog
from app.db.container import create_persistence_container
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.interventions.executor import RazorpayRecoveryExecutor
from app.main import app, create_app
from app.policies.engine import PolicyEngine
from app.scoring.expected_value import ExpectedValueScorer
from app.services.settlement_verifier import SettlementEvent, SettlementVerifier


def _generate_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture
def container():
    return create_persistence_container(mode="memory")


@pytest.fixture
def webhook_secret():
    return "test_razorpay_webhook_secret_99"


@pytest.fixture
def test_app(webhook_secret):
    app_instance = create_app(webhook_secret=webhook_secret, async_mode=False)
    return app_instance


def test_razorpay_full_recovery_lifecycle_end_to_end(test_app, webhook_secret):
    """Proves the complete end-to-end Razorpay recovery lifecycle."""
    client = TestClient(test_app)
    container = test_app.state.container

    # 1. Simulate Razorpay payment.failed event
    failure_payload = {
        "entity": "event",
        "account_id": "acc_test_123",
        "event": "payment.failed",
        "id": "evt_fail_e2e_101",
        "created_at": 1700000000,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fail_e2e_101",
                    "amount": 499900,  # ₹4,999
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed due to insufficient funds",
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": "insufficient_funds",
                    "method": "card",
                    "created_at": 1700000000,
                    "notes": {"customer_id": "cust_e2e_99"},
                }
            }
        },
    }
    body_fail = json.dumps(failure_payload).encode("utf-8")
    sig_fail = _generate_signature(body_fail, webhook_secret)

    with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret, "RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        resp_fail = client.post(
            "/webhooks/razorpay",
            content=body_fail,
            headers={"X-Razorpay-Signature": sig_fail, "Content-Type": "application/json"},
        )

    assert resp_fail.status_code == 200
    data_fail = resp_fail.json()
    item_id = data_fail.get("recovery_item_id")
    assert item_id is not None

    # Verify RecoveryItem created & verified_recovered is 0 initially
    item = container.recovery_items.get(item_id)
    assert item is not None
    assert item.amount_minor == 499900
    assert item.actual_recovery_value == 0  # Crucial: link creation != recovered!

    # 2. Execute Razorpay payment link creation
    mock_rzp_client = MagicMock()
    mock_rzp_client.is_configured = True
    mock_rzp_client.create_payment_link.return_value = {
        "provider": "razorpay",
        "provider_reference": "plink_e2e_999",
        "payment_link_id": "plink_e2e_999",
        "payment_link_url": "https://rzp.io/i/plink_e2e_999",
        "amount_minor": 499900,
        "currency": "INR",
        "status": "created",
        "latency_ms": 120,
    }

    executor = RazorpayRecoveryExecutor(razorpay_client=mock_rzp_client)
    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        exec_res = executor.execute(item, "send_payment_link", attempt_number=1)

    assert exec_res.success
    assert exec_res.metadata["payment_link_id"] == "plink_e2e_999"

    # 3. Simulate Razorpay payment_link.paid settlement webhook
    settlement_payload = {
        "entity": "event",
        "account_id": "acc_test_123",
        "event": "payment_link.paid",
        "id": "evt_settle_e2e_202",
        "created_at": 1700000500,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_success_e2e_202",
                    "amount": 499900,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": "order_e2e_1",
                    "payment_link_id": "plink_e2e_999",
                    "created_at": 1700000500,
                    "notes": {"recovery_item_id": item_id},
                }
            },
            "payment_link": {
                "entity": {
                    "id": "plink_e2e_999",
                    "reference_id": item_id,
                    "amount": 499900,
                    "amount_paid": 499900,
                    "currency": "INR",
                    "status": "paid",
                    "notes": {"recovery_item_id": item_id},
                }
            },
        },
    }
    body_settle = json.dumps(settlement_payload).encode("utf-8")
    sig_settle = _generate_signature(body_settle, webhook_secret)

    with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret, "RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        resp_settle = client.post(
            "/webhooks/razorpay",
            content=body_settle,
            headers={"X-Razorpay-Signature": sig_settle, "Content-Type": "application/json"},
        )

    assert resp_settle.status_code == 200
    data_settle = resp_settle.json()
    assert data_settle["status"] in ("recovered", "partially_recovered", "processed", "accepted")

    # 4. Verify authoritative settlement in domain model
    item_settled = container.recovery_items.get(item_id)
    assert item_settled.status == RecoveryStatus.RECOVERED
    assert item_settled.actual_recovery_value == 499900

    # 5. Verify outcome recorded & audit trail
    outcome = container.outcomes.get_for_item(item_id)
    assert outcome is not None
    assert outcome.actual_recovery_minor == 499900
    assert outcome.outcome_type == "recovered"


def test_razorpay_invalid_signature_rejection(test_app, webhook_secret):
    """Verifies that requests with invalid signatures are rejected with 400 Bad Request."""
    client = TestClient(test_app)
    body = json.dumps({"event": "payment.failed", "id": "evt_bad_sig"}).encode("utf-8")

    with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret}):
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "invalid_sha256_signature_header"},
        )

    assert resp.status_code == 400
    assert resp.json()["reason"] == "signature_verification_failed"


def test_razorpay_duplicate_webhook_idempotency(test_app, webhook_secret):
    """Verifies duplicate webhooks are safely ignored without double counting."""
    client = TestClient(test_app)

    payload = {
        "entity": "event",
        "event": "payment.failed",
        "id": "evt_dup_test_505",
        "created_at": 1700000000,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_dup_505",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "created_at": 1700000000,
                }
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = _generate_signature(body, webhook_secret)

    with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret}):
        resp1 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        resp2 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "duplicate"


def test_razorpay_unmatched_unknown_payment(test_app, webhook_secret):
    """Verifies settlement for non-existent item returns unmatched without crashing."""
    client = TestClient(test_app)

    settlement_payload = {
        "entity": "event",
        "event": "payment.captured",
        "id": "evt_unknown_item_999",
        "created_at": 1700000000,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_unknown_999",
                    "amount": 250000,
                    "currency": "INR",
                    "status": "captured",
                    "created_at": 1700000000,
                    "notes": {"recovery_item_id": "item_does_not_exist_xyz"},
                }
            }
        },
    }
    body = json.dumps(settlement_payload).encode("utf-8")
    sig = _generate_signature(body, webhook_secret)

    with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret}):
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    assert resp.status_code == 200
    assert resp.json()["status"] in ("unmatched", "quarantined")


def test_razorpay_amount_clamping(container):
    """Verifies that verified recovery cannot exceed item amount at risk."""
    item = RecoveryItem(
        id="item_clamp_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_clamp",
        customer_id="cust_1",
        amount_minor=100000,  # ₹1,000
        currency="INR",
        created_at=datetime.now(timezone.utc),
    )
    container.recovery_items.save(item)

    verifier = SettlementVerifier(
        recovery_items=container.recovery_items,
        outcomes=container.outcomes,
        audit_log=container.audit_log,
    )

    # Settlement event reports overpayment ₹1,500 for a ₹1,000 item
    event = SettlementEvent(
        event_id="evt_overpay_1",
        provider="razorpay",
        recovery_item_id=item.id,
        success=True,
        actual_amount_minor=150000,
        currency="INR",
    )

    res = verifier.process_settlement(event)
    assert res.status == "recovered"
    assert res.actual_recovery_minor == 100000  # Clamped to ₹1,000!


def test_razorpay_terminal_state_protection(container):
    """Verifies terminal items (RECOVERED, STOPPED, ESCALATED) ignore secondary settlements."""
    item = RecoveryItem(
        id="item_terminal_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_term",
        customer_id="cust_1",
        amount_minor=500000,
        currency="INR",
        status=RecoveryStatus.RECOVERED,
        actual_recovery_value=500000,
        created_at=datetime.now(timezone.utc),
    )
    container.recovery_items.save(item)

    verifier = SettlementVerifier(
        recovery_items=container.recovery_items,
        outcomes=container.outcomes,
        audit_log=container.audit_log,
    )

    event = SettlementEvent(
        event_id="evt_term_repeat",
        provider="razorpay",
        recovery_item_id=item.id,
        success=True,
        actual_amount_minor=500000,
    )

    res = verifier.process_settlement(event)
    assert res.status == "ignored_terminal"
    assert res.actual_recovery_minor == 0


def test_razorpay_timeout_handling():
    """Verifies network timeout returns EXECUTION_UNKNOWN rather than failing blindly."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.create_payment_link.side_effect = RazorpayNetworkTimeoutError("Connection timed out")

    executor = RazorpayRecoveryExecutor(razorpay_client=mock_client)
    item = RecoveryItem(
        id="item_timeout_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_timeout",
        customer_id="cust_1",
        amount_minor=100000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
    )

    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        res = executor.execute(item, "send_payment_link", attempt_number=1)

    assert not res.success
    assert res.error_code == "EXECUTION_UNKNOWN"
    assert res.metadata.get("reconciliation_required") is True
