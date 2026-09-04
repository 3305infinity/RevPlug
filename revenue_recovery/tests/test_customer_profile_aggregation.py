"""Regression tests for Customer Profile Aggregation logic against actual RecoveryItem state.

Validates that:
1. Active pending case shows active exposure, open opportunities, and at-risk revenue.
2. Recovered case shows 0 active exposure, 0 expected recovery, 100% recovery rate, Settled & Clear status, while preserving last failed payment timestamp and root cause.
3. Stopped case shows 0 active exposure, 0 expected recovery, No Active Exposure status, while preserving last failed payment timestamp.
4. Customer with only historical cases shows 0 active exposure, active_cases_count = 0, No Active Exposure status, and no active recovery pressure label.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.models import RecoveryStatus

client = TestClient(app)


def test_customer_profile_scenario_1_active_pending_case():
    """Scenario 1: Customer with an active pending case."""
    cid = "cust_prof_active_01"
    create_payload = {
        "customer_id": cid,
        "customer_name": "Active Customer",
        "amount_minor": 499900,
        "currency": "INR",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200
    item_id = resp.json()["recovery_item_id"]

    # Fetch customer recovery profile
    prof_resp = client.get(f"/api/customers/{cid}/recovery-profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()

    assert prof["customer_id"] == cid
    assert prof["active_cases_count"] == 1
    assert prof["current_amount_at_risk_minor"] == 499900
    assert prof["recovery_status"] in ("Active Exposure", "Awaiting Verification")
    assert prof["current_subscription_state"] == "Overdue"
    assert "No active recovery concerns" not in prof["why_this_matters"]


def test_customer_profile_scenario_2_recovered_case():
    """Scenario 2: Customer with a recovered case."""
    cid = "cust_prof_recovered_02"
    create_payload = {
        "customer_id": cid,
        "customer_name": "Settled Customer",
        "amount_minor": 499900,
        "currency": "INR",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200
    item_id = resp.json()["recovery_item_id"]

    # Evaluate & verify settlement to transition to RECOVERED
    client.post(f"/api/recovery-items/{item_id}/recover")
    client.post(f"/api/recovery-items/{item_id}/simulate-settlement")

    # Fetch customer recovery profile
    prof_resp = client.get(f"/api/customers/{cid}/recovery-profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()

    assert prof["active_cases_count"] == 0
    assert prof["current_amount_at_risk_minor"] == 0
    assert prof["current_expected_recovery_minor"] == 0
    assert prof["actually_recovered_lifetime_minor"] == 499900
    assert prof["historical_recovery_rate"] == 1.0
    assert prof["recovery_status"] == "Settled & Clear"
    assert prof["current_subscription_state"] == "Active"
    # Rule 6: Last Failed shows latest failed event even if case is now terminal
    assert prof["last_failed_payment_at"] is not None
    assert prof["last_failed_reason"] in ("payment_timed_out", "SOFT")
    assert prof["why_this_matters"] == "No active recovery concerns"


def test_customer_profile_scenario_3_stopped_case():
    """Scenario 3: Customer with a policy-stopped case."""
    cid = "cust_prof_stopped_03"
    create_payload = {
        "customer_id": cid,
        "customer_name": "Blocked Customer",
        "amount_minor": 1500000,
        "currency": "INR",
        "failure_reason": "FRAUD_BLOCK",
        "fraud_risk": True,
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200
    item_id = resp.json()["recovery_item_id"]

    # Evaluate case (policy blocks execution)
    client.post(f"/api/recovery-items/{item_id}/recover")

    # Fetch customer recovery profile
    prof_resp = client.get(f"/api/customers/{cid}/recovery-profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()

    assert prof["active_cases_count"] == 0
    assert prof["current_amount_at_risk_minor"] == 0
    assert prof["current_expected_recovery_minor"] == 0
    assert prof["actually_recovered_lifetime_minor"] == 0
    assert prof["recovery_status"] == "No Active Exposure"
    assert prof["current_subscription_state"] == "Active"
    # Rule 6: Last Failed shows latest failed event even if case is now terminal
    assert prof["last_failed_payment_at"] is not None
    assert prof["why_this_matters"] == "No active recovery concerns"


def test_customer_profile_scenario_4_historical_only_no_active():
    """Scenario 4: Customer with past historical cases (1 recovered, 1 stopped) and 0 active cases."""
    cid = "cust_prof_historical_04"
    
    # 1. Recovered case
    r1 = client.post("/api/recovery-items/create", json={
        "customer_id": cid,
        "amount_minor": 300000,
        "failure_reason": "payment_timed_out",
    }).json()
    id1 = r1["recovery_item_id"]
    client.post(f"/api/recovery-items/{id1}/recover")
    client.post(f"/api/recovery-items/{id1}/simulate-settlement")

    # 2. Stopped case
    r2 = client.post("/api/recovery-items/create", json={
        "customer_id": cid,
        "amount_minor": 500000,
        "failure_reason": "FRAUD_BLOCK",
        "fraud_risk": True,
    }).json()
    id2 = r2["recovery_item_id"]
    client.post(f"/api/recovery-items/{id2}/recover")

    # Fetch customer recovery profile
    prof_resp = client.get(f"/api/customers/{cid}/recovery-profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()

    assert prof["total_cases_count"] == 2
    assert prof["active_cases_count"] == 0
    assert prof["current_amount_at_risk_minor"] == 0
    assert prof["current_expected_recovery_minor"] == 0
    assert prof["actually_recovered_lifetime_minor"] == 300000
    assert prof["recovery_status"] == "No Active Exposure"
    assert prof["current_subscription_state"] == "Active"
    assert prof["why_this_matters"] == "No active recovery concerns"
    assert prof["recovery_pressure_summary"] == "No recent recovery pressure"
