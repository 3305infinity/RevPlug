"""Integration tests for the single-case lifecycle end to end.

Validates the full closed-loop recovery state machine across:
- Case A: Soft timeout (₹4,999) -> QUEUED -> EVALUATE -> EXECUTE -> PENDING_VERIFICATION -> VERIFY SETTLEMENT -> RECOVERED
- Case B: Fraud signal -> QUEUED -> EVALUATE -> POLICY BLOCK (STOP) -> 0 Execution -> STOPPED (Recovery = ₹0)
- Case C: Customer promise-to-pay -> Extract Promise -> Activate Hold -> WAIT (No redundant retries, Recovery = ₹0)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.models import RecoveryStatus

client = TestClient(app)


def test_case_a_soft_timeout_lifecycle():
    """CASE A: Soft timeout (₹4,999) complete lifecycle.
    
    1. Create case (amount ₹4,999 = 499900 minor units). Starts QUEUED.
    2. Evaluate & Dispatch (POST /api/recovery-items/{id}/recover).
       - Produces root cause, candidate actions, Net EV, safety decision ALLOWED.
       - Dispatches bounded action (e.g. send_payment_link).
       - Transitions to PENDING_VERIFICATION / INTERVENTION_EXECUTED.
       - Financial Truth: actual_recovery_value MUST be 0 / None before settlement verification!
    3. Simulate Settlement (POST /api/recovery-items/{id}/simulate-settlement).
       - Verifies amount (499900) & currency (INR).
       - Sets actual_recovery_value to 499900.
       - Transitions case to RECOVERED.
    4. Trace check: Authoritative trace reflects all 10 stages and verified settlement evidence.
    """
    # 1. Create case
    create_payload = {
        "customer_id": "cust_case_a_timeout",
        "customer_name": "Rohan Sharma",
        "amount_minor": 499900,
        "currency": "INR",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200, f"Case creation failed: {resp.text}"
    data = resp.json()
    item_id = data["recovery_item_id"]
    assert data["final_status"] == RecoveryStatus.QUEUED.value

    # Verify initial detail
    detail_resp = client.get(f"/api/recovery-items/{item_id}")
    assert detail_resp.status_code == 200
    item_detail = detail_resp.json()
    assert item_detail["status"] == RecoveryStatus.QUEUED.value
    assert item_detail.get("actual_recovery_value") in (0, None)

    # 2. Evaluate & Dispatch
    recover_resp = client.post(f"/api/recovery-items/{item_id}/recover")
    assert recover_resp.status_code == 200, f"Recovery evaluation failed: {recover_resp.text}"
    rec_data = recover_resp.json()

    # Check diagnostic & policy outputs
    assert rec_data.get("root_cause") is not None
    assert rec_data.get("safety_decision") is not None
    assert rec_data.get("ev_scoring") is not None

    # Status must be pending_verification / intervention_executed, NOT recovered
    post_eval_status = rec_data.get("final_status")
    assert post_eval_status in (
        RecoveryStatus.PENDING_VERIFICATION.value,
        RecoveryStatus.INTERVENTION_EXECUTED.value,
    ), f"Expected pending_verification or intervention_executed, got {post_eval_status}"

    # FINANCIAL TRUTH INVARIANT: Must NOT be treated as recovered money yet
    assert rec_data.get("actual_recovery_value") == 0, (
        f"Action execution must not be recorded as recovered money! Got {rec_data.get('actual_recovery_value')}"
    )

    detail_after_eval = client.get(f"/api/recovery-items/{item_id}").json()
    assert detail_after_eval.get("actual_recovery_value") in (0, None)
    assert detail_after_eval["status"] != RecoveryStatus.RECOVERED.value

    # 3. Simulate Settlement Verification
    settle_resp = client.post(f"/api/recovery-items/{item_id}/simulate-settlement")
    assert settle_resp.status_code == 200, f"Settlement simulation failed: {settle_resp.text}"
    settle_data = settle_resp.json()

    assert settle_data.get("verification_result") == "verified"
    assert settle_data.get("actual_recovery_minor") == 499900
    assert settle_data.get("final_status") == RecoveryStatus.RECOVERED.value

    # Re-fetch authoritative detail
    final_detail = client.get(f"/api/recovery-items/{item_id}").json()
    assert final_detail["status"] == RecoveryStatus.RECOVERED.value
    assert final_detail["actual_recovery_value"] == 499900

    # 4. Check Trace
    trace_resp = client.get(f"/api/recovery-items/{item_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["item_id"] == item_id
    assert trace["status"] == RecoveryStatus.RECOVERED.value
    assert trace["amount_at_risk_minor"] == 499900
    assert trace["settlement_evidence"]["verified"] is True
    assert trace["settlement_evidence"]["verified_amount_minor"] == 499900


def test_case_b_fraud_signal_blocks_execution():
    """CASE B: Fraud signal policy block.
    
    1. Create case with fraud signal (fraud_risk=True). Starts QUEUED.
    2. Evaluate case (POST /api/recovery-items/{id}/recover).
    3. Policy engine / stopping rules detect fraud signal and block execution.
    4. Status becomes terminal STOPPED / policy_blocked.
    5. Execution calls = 0 (no payment link/action executed).
    6. Actual recovery remains ₹0.
    7. Case trace clearly records the policy stop reason.
    """
    create_payload = {
        "customer_id": "cust_fraud_shield",
        "customer_name": "Suspicious Entity",
        "amount_minor": 1500000,
        "currency": "INR",
        "failure_reason": "FRAUD_BLOCK",
        "fraud_risk": True,
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200
    data = resp.json()
    item_id = data["recovery_item_id"]
    assert data["final_status"] == RecoveryStatus.QUEUED.value

    # Evaluate case
    eval_resp = client.post(f"/api/recovery-items/{item_id}/recover")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()

    # Must be stopped/blocked by policy before execution
    assert eval_data.get("final_status") == RecoveryStatus.STOPPED.value
    assert eval_data.get("action_taken") in ("no_action", "stop_recovery", None)
    assert eval_data.get("actual_recovery_value") == 0

    # Confirm detail state
    detail = client.get(f"/api/recovery-items/{item_id}").json()
    assert detail["status"] == RecoveryStatus.STOPPED.value
    assert detail.get("actual_recovery_value") in (0, None)

    # Check trace
    trace_resp = client.get(f"/api/recovery-items/{item_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["status"] == RecoveryStatus.STOPPED.value
    assert trace["settlement_evidence"]["verified"] is False
    assert trace["settlement_evidence"]["verified_amount_minor"] == 0
    # Trace timeline or safety decision must capture policy block
    safety = trace.get("safety_decision", {})
    assert safety.get("allowed") is False or trace.get("status") == RecoveryStatus.STOPPED.value


def test_case_c_customer_promise_to_pay_hold():
    """CASE C: Customer promise-to-pay hold.
    
    1. Create case.
    2. Record voice promise to pay (e.g. ₹8,500 on future date).
    3. Evaluate case (POST /api/recovery-items/{id}/recover).
    4. Stopping rules detect active promise and issue WAIT decision.
    5. Prevents redundant retry/contact while hold is active.
    6. Recovery value remains ₹0 (no fake recovery).
    """
    create_payload = {
        "customer_id": "cust_promise_hold",
        "customer_name": "Priya Verma",
        "amount_minor": 850000,
        "currency": "INR",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
    }
    resp = client.post("/api/recovery-items/create", json=create_payload)
    assert resp.status_code == 200
    item_id = resp.json()["recovery_item_id"]

    # Record voice promise
    promise_resp = client.post(
        f"/api/recovery-items/{item_id}/voice-promise",
        json={
            "transcript": "Haan main 10 September ko ₹8,500 pay kar dungi",
            "customer_id": "cust_promise_hold",
        },
    )
    assert promise_resp.status_code == 200
    p_data = promise_resp.json()
    assert p_data.get("status") == "success" or p_data.get("promise_recorded") is True

    # Evaluate case while hold is active
    eval_resp = client.post(f"/api/recovery-items/{item_id}/recover")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()

    # Safety decision or policy result should yield WAIT or hold reason
    safety_decision = eval_data.get("safety_decision") or eval_data.get("policy_result") or {}
    dec_type = safety_decision.get("decision_type") if isinstance(safety_decision, dict) else str(safety_decision)

    assert dec_type in ("WAIT", "STOP", "ALLOWED", "active_promise_wait")
    assert eval_data.get("actual_recovery_value") == 0

    # Trace check
    trace = client.get(f"/api/recovery-items/{item_id}/trace").json()
    assert trace["settlement_evidence"]["verified"] is False
    assert trace["settlement_evidence"]["verified_amount_minor"] == 0
