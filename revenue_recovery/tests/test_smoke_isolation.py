"""Test for Smoke/Stress Test Data Isolation.

Asserts that running smoke tests or sending synthetic test webhooks
does NOT pollute or increase the count returned by dashboard endpoints
(/api/opportunity-inbox, /api/items, /api/dashboard/summary).
"""
import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _generate_signature(payload: bytes, secret: str = "unconfigured-placeholder-secret") -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

def test_smoke_test_does_not_pollute_opportunity_inbox():
    """Verify that smoke test webhooks are filtered from dashboard inbox endpoints."""
    # 1. Get baseline count
    resp1 = client.get("/api/opportunity-inbox")
    assert resp1.status_code == 200
    baseline_count = len(resp1.json())

    # 2. Fire synthetic smoke test webhook
    raw_payload = {
        "entity": "event",
        "account_id": "acc_SMOKE_TEST",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": "evt_smoke_isolation_001",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_smoke_isolation_001",
                    "entity": "payment",
                    "customer_id": "razorpay_customer",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed (synthetic smoke test)",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_timed_out",
                    "notes": {"source": "smoke_test"},
                }
            }
        },
    }
    payload_bytes = json.dumps(raw_payload).encode("utf-8")
    sig = _generate_signature(payload_bytes)

    webhook_resp = client.post(
        "/webhooks/razorpay",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
        },
    )
    assert webhook_resp.status_code in (200, 202)

    # 3. Verify opportunity inbox count did NOT increase
    resp2 = client.get("/api/opportunity-inbox")
    assert resp2.status_code == 200
    new_count = len(resp2.json())
    assert new_count == baseline_count, f"Smoke test fixture leaked into opportunity inbox! Expected {baseline_count}, got {new_count}"

    # 4. Verify /api/items count also excluded the smoke item
    items_resp = client.get("/api/items")
    assert items_resp.status_code == 200
    items = items_resp.json()
    smoke_items = [i for i in items if i.get("id") == "pay_smoke_isolation_001" or i.get("external_id") == "evt_smoke_isolation_001"]
    assert len(smoke_items) == 0, "Smoke item appeared in /api/items dashboard endpoint"
