import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    # Make sure we use the InMemory mode for tests
    import os
    os.environ["STORAGE_MODE"] = "memory"
    return TestClient(app)

def test_human_approval_cannot_bypass_policy_engine(client: TestClient):
    """
    Verify that even if a human tries to approve an action that violates safety rules
    (like retrying a fraud payment), the PolicyEngine blocks it.
    """
    import time
    # 1. Create a fraud payment which fails the fraud_rule
    resp = client.post("/api/demo/payment-failure", json={
        "amount_minor": 50000,
        "error_reason": "payment_risk_check_failed",
        "event_id": f"evt_demo_{time.time()}_test1"
    })
    assert resp.status_code == 200
    data = resp.json()
    item_id = data["recovery_item_id"]
    
    # 2. Assert it's stopped initially
    assert data["recovery_status"] == "stopped"
    assert data["stopped_reason"] == "fraud_detected"
    
    # 3. Simulate human trying to override the decision in the review queue
    approve_resp = client.post(f"/api/recovery-items/{item_id}/approve", json={"action": "retry_payment"})
    assert approve_resp.status_code == 200
    
    approve_data = approve_resp.json()
    assert approve_data["status"] == "denied_by_policy"
    assert "fraud" in approve_data["message"].lower()

def test_reset_data_removes_all_synthetic_state(client: TestClient):
    """
    Verify that calling the demo reset endpoint successfully clears all synthetic data.
    """
    import time
    # 1. Create synthetic data
    client.post("/api/demo/payment-failure", json={
        "amount_minor": 50000,
        "event_id": f"evt_demo_{time.time()}_test2"
    })
    
    # Verify items exist
    items_resp = client.get("/api/recovery-items")
    assert len(items_resp.json()) > 0
    
    # 2. Reset demo data
    reset_resp = client.post("/api/demo/reset")
    assert reset_resp.status_code == 200
    
    # 3. Verify items are gone
    items_resp2 = client.get("/api/recovery-items")
    assert len(items_resp2.json()) == 0

def test_backend_returns_execution_stopped_by_policy(client: TestClient):
    """
    Verify the backend correctly returns a detailed policy rule error when
    execution is halted by a guardrail.
    """
    import time
    # Create an item that violates a rule
    resp = client.post("/api/demo/payment-failure", json={
        "amount_minor": 50000,
        "error_reason": "payment_risk_check_failed",
        "event_id": f"evt_demo_{time.time()}_test3"
    })
    assert resp.status_code == 200
    data = resp.json()
    
    # For a stopped item, the endpoint returns the stopped_reason and stopped_rule
    assert data["stopped_reason"] == "fraud_detected"
    assert "fraud" in data["stopped_rule"].lower()
