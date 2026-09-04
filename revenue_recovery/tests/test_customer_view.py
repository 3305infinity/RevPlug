"""Tests for customer-facing recovery view and settlement verification path."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.models import RecoveryStatus


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _create_case(client: TestClient, customer_id: str = "cust_portal_test", amount_minor: int = 499900) -> str:
    payload = {
        "customer_id": customer_id,
        "amount_minor": amount_minor,
        "failure_reason": "soft_gateway_timeout",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_customer_view_case_loads_correct_amount_and_detail(client: TestClient):
    """Valid recovery case should return full item details and correct amount."""
    item_id = _create_case(client, amount_minor=499900)

    resp = client.get(f"/api/recovery-items/{item_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["id"] == item_id
    assert data["amount_minor"] == 499900
    assert data["customer_id"] == "cust_portal_test"
    assert data["status"] in ["detected", "diagnosed", "queued"]


def test_customer_view_nonexistent_case_returns_404(client: TestClient):
    """Non-existent case ID should return 404."""
    resp = client.get("/api/recovery-items/nonexistent_case_999")
    assert resp.status_code == 404


def test_customer_payment_triggers_settlement_verification(client: TestClient):
    """Executing payment via simulate-settlement should verify settlement and transition case to RECOVERED."""
    item_id = _create_case(client, customer_id="cust_settle_test", amount_minor=750000)

    # Trigger settlement verification endpoint
    settle_resp = client.post(f"/api/recovery-items/{item_id}/simulate-settlement")
    assert settle_resp.status_code == 200, settle_resp.text
    settle_data = settle_resp.json()

    assert settle_data["status"] == "success"
    assert settle_data["verification_result"] == "verified"
    assert settle_data["actual_recovery_minor"] == 750000
    assert settle_data["final_status"] == "recovered"

    # Verify case state persisted as RECOVERED
    detail_resp = client.get(f"/api/recovery-items/{item_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["status"] == "recovered"
    assert detail_data["actual_recovery_value"] == 750000
    assert detail_data["outcome"] is not None
    assert detail_data["outcome"]["outcome_type"] == "recovered"


def test_terminal_stopped_case_blocks_settlement_simulation(client: TestClient):
    """Stopped case should block settlement simulation."""
    item_id = _create_case(client, customer_id="cust_stopped_test")

    # Manually stop or recover case
    client.post(f"/api/recovery-items/{item_id}/simulate-settlement")

    # Second settlement attempt on already recovered/terminal item should be blocked
    resp = client.post(f"/api/recovery-items/{item_id}/simulate-settlement")
    assert resp.status_code == 400
    assert "terminal status" in resp.json()["detail"].lower()
