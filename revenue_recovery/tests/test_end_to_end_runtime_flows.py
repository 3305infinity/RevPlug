"""End-to-end integration and regression tests for runtime flows."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.classification import classify_root_cause
from app.domain.models import RecoveryStatus
from app.services.financials import RecoveryFinancialsService
from app.main import app


def test_1_create_recovery_case_valid_succeeds():
    """Valid case creation creates a persisted RecoveryItem and returns 201."""
    client = TestClient(app)
    payload = {
        "customer_id": "cust_test_inc",
        "customer_name": "Test Merchant Alpha",
        "amount_minor": 499900,
        "currency": "INR",
        "event_type": "payment_failed",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
        "reference_id": "inv_884102",
    }
    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("rec_")
    assert data["customer_id"] == "cust_test_inc"
    assert data["root_cause"] == "SOFT_GATEWAY_TIMEOUT"
    assert data["status"] == "queued" or data["status"] == "detected"


def test_2_create_recovery_case_malformed_returns_400():
    """Invalid amount returns 400 with field-level detail."""
    client = TestClient(app)
    payload = {
        "customer_id": "cust_invalid",
        "amount_minor": 0,
        "event_type": "payment_failed",
    }
    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "Amount at risk must be a positive integer" in data["detail"]


def test_3_evaluate_and_recover_canonical_endpoint():
    """POST /api/recovery-items/{id}/recover evaluates case and transitions status."""
    client = TestClient(app)

    # 1. Create a case
    create_resp = client.post("/api/recovery-items/create", json={
        "customer_id": "cust_eval_test",
        "amount_minor": 250000,
        "failure_reason": "soft_gateway_timeout",
        "payment_method": "upi",
    })
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # 2. Evaluate and recover
    eval_resp = client.post(f"/api/recovery-items/{item_id}/recover")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["status"] == "success"
    assert eval_data["final_status"] == "recovered"
    assert eval_data["action_taken"] in ("retry_payment", "send_payment_link", "no_action")


def test_4_evaluate_missing_item_returns_404():
    """Non-existent case ID returns clean 404."""
    client = TestClient(app)
    resp = client.post("/api/recovery-items/rec_non_existent_9999/recover")
    assert resp.status_code == 404
    assert "could not be found" in resp.json()["detail"]


def test_5_canonical_failure_reason_mappings():
    """All supported failure reasons map to canonical root causes."""
    assert classify_root_cause("soft_gateway_timeout") == "SOFT_GATEWAY_TIMEOUT"
    assert classify_root_cause("authentication_required") == "AUTHENTICATION_REQUIRED"
    assert classify_root_cause("insufficient_funds") == "INSUFFICIENT_FUNDS"
    assert classify_root_cause("expired_card") == "HARD_EXPIRED_CARD"
    assert classify_root_cause("fraud_flagged") == "FRAUD_BLOCK"
    assert classify_root_cause("customer_opt_out") == "CONSENT_BLOCK"
    assert classify_root_cause("invoice_disputed") == "DISPUTE_RAISED"
    assert classify_root_cause("unknown_unmapped_signal").startswith("UNCLASSIFIED:")


def test_6_fraud_risk_blocks_execution():
    """Fraud flag creates a stopped case with fraud block status."""
    client = TestClient(app)
    resp = client.post("/api/recovery-items/create", json={
        "customer_id": "cust_fraud_check",
        "amount_minor": 990000,
        "fraud_risk": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "stopped"
    assert "fraud" in data["stopped_reason"].lower()


def test_7_opt_out_blocks_communication():
    """Consent opt-out creates a stopped case with consent shield active."""
    client = TestClient(app)
    resp = client.post("/api/recovery-items/create", json={
        "customer_id": "cust_opt_out_check",
        "amount_minor": 150000,
        "consent_opt_out": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "stopped"
    assert "opt-out" in data["stopped_reason"].lower()


def test_8_canonical_financials_service():
    """RecoveryFinancialsService computes authoritative financial totals."""
    container = app.state.container
    svc = RecoveryFinancialsService(container)
    fin = svc.get_canonical_financials()
    assert "total_at_risk_minor" in fin
    assert "verified_recovered_minor" in fin
    assert "net_recovered_minor" in fin
    assert fin["net_recovered_minor"] >= 0
