import time
import pytest
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus, SourceType
from app.main import create_app


@pytest.fixture
def api_client():
    app = create_app(webhook_secret="test-secret")
    return TestClient(app)


def test_step5_create_and_process_recovery_item(api_client):
    """A & B. Create recovery item -> appears in Recovery Cases and status updates after processing."""
    event_id = f"evt_step5_a_{int(time.time())}"
    payment_id = f"pay_step5_a_{int(time.time())}"
    cust_id = f"cust_step5_a_{int(time.time())}"

    # Trigger recovery creation & processing
    r = api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": cust_id,
            "amount_minor": 75000,
            "error_reason": "payment_timed_out",
        },
    )
    assert r.status_code == 200
    res_data = r.json()
    assert res_data["status"] == "processed"
    assert res_data["recovery_item_id"] == payment_id

    # Verify case appears in Recovery Cases API
    r_items = api_client.get("/api/recovery-items")
    assert r_items.status_code == 200
    items = r_items.json()

    match = next((i for i in items if i["id"] == payment_id), None)
    assert match is not None
    assert match["customer_id"] == cust_id
    assert match["amount_minor"] == 75000
    assert match["status"] in ("recovered", "diagnosed", "queued", "intervention_executed", "pending_verification")


def test_step5_customer_history_and_multiple_recoveries(api_client):
    """C, D, E. Single and multiple recoveries appear in Customer History and remain isolated per customer."""
    cust_target = f"cust_target_{int(time.time())}"
    cust_isolated = f"cust_isolated_{int(time.time())}"

    # Event 1 for target customer
    api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_t1_{int(time.time())}",
            "payment_id": f"pay_t1_{int(time.time())}",
            "customer_id": cust_target,
            "amount_minor": 50000,
            "error_reason": "payment_timed_out",
        },
    )

    # Event 2 for target customer
    api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_t2_{int(time.time())}",
            "payment_id": f"pay_t2_{int(time.time())}",
            "customer_id": cust_target,
            "amount_minor": 18000,
            "error_reason": "gateway_technical_error",
        },
    )

    # Event for isolated customer
    api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_iso_{int(time.time())}",
            "payment_id": f"pay_iso_{int(time.time())}",
            "customer_id": cust_isolated,
            "amount_minor": 30000,
            "error_reason": "payment_timed_out",
        },
    )

    # Query target customer history
    r_target = api_client.get(f"/api/customers/{cust_target}")
    assert r_target.status_code == 200
    data_target = r_target.json()
    assert data_target["customer_id"] == cust_target
    assert data_target["total_cases"] == 2
    assert len(data_target["timeline"]) >= 2

    # Query isolated customer history
    r_iso = api_client.get(f"/api/customers/{cust_isolated}")
    assert r_iso.status_code == 200
    data_iso = r_iso.json()
    assert data_iso["customer_id"] == cust_isolated
    assert data_iso["total_cases"] == 1

    # Verify no cross-contamination
    target_case_ids = {c["id"] for c in data_target["cases"]}
    iso_case_ids = {c["id"] for c in data_iso["cases"]}
    assert target_case_ids.isdisjoint(iso_case_ids)


def test_step5_verified_recovery_vs_unverified(api_client):
    """F & G. Verified recovery updates dashboard actual recovered; unverified does NOT."""
    # Query initial dashboard summary
    r_initial = api_client.get("/api/dashboard/summary")
    initial_summary = r_initial.json()
    initial_recovered = initial_summary["actually_recovered"]

    # Trigger soft recovery (executes intervention -> PENDING_VERIFICATION)
    pay_id = f"pay_ver_{int(time.time())}"
    r_rec = api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_ver_{int(time.time())}",
            "payment_id": pay_id,
            "customer_id": "cust_ver_test",
            "amount_minor": 60000,
            "error_reason": "payment_timed_out",
        },
    )
    item_id = r_rec.json()["recovery_item_id"]

    # Unverified execution MUST NOT increase actually_recovered
    r_unver = api_client.get("/api/dashboard/summary")
    assert r_unver.json()["actually_recovered"] == initial_recovered

    # Process authoritative settlement verification
    from app.services.settlement_verifier import SettlementVerifier, SettlementEvent
    container = api_client.app.state.container
    verifier = SettlementVerifier(
        recovery_items=container.recovery_items,
        outcomes=container.outcomes,
        audit_log=container.audit_log,
    )
    verifier.process_settlement(SettlementEvent(
        event_id=f"evt_settle_step5_{pay_id}",
        provider="razorpay",
        recovery_item_id=item_id,
        success=True,
        actual_amount_minor=60000,
    ))

    r_updated = api_client.get("/api/dashboard/summary")
    updated_summary = r_updated.json()

    # Verified recovery MUST increase actually_recovered
    assert updated_summary["actually_recovered"] > initial_recovered


def test_step5_policy_blocked_and_stopped_cases(api_client):
    """H & I. Blocked and stopped cases appear in cases/history with reasons and do NOT inflate recovered numbers."""
    fraud_pay_id = f"pay_fraud_{int(time.time())}"
    cust_fraud = f"cust_fraud_{int(time.time())}"

    # Trigger fraud failure -> blocked by policy/guard
    r_fraud = api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_fraud_{int(time.time())}",
            "payment_id": fraud_pay_id,
            "customer_id": cust_fraud,
            "amount_minor": 99000,
            "error_reason": "payment_risk_check_failed",
        },
    )
    assert r_fraud.status_code == 200
    data_f = r_fraud.json()
    assert data_f["recovery_status"] in ("stopped", "escalated")

    # Check case workspace detail
    r_detail = api_client.get(f"/api/recovery-items/{fraud_pay_id}")
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["status"] in ("stopped", "escalated")
    assert len(detail["audit_events"]) > 0

    # Check customer history
    r_cust = api_client.get(f"/api/customers/{cust_fraud}")
    assert r_cust.status_code == 200
    c_data = r_cust.json()
    assert c_data["stopped_cases"] + c_data["escalated_cases"] >= 1
    assert c_data["actually_recovered"] == 0  # Blocked case must NOT inflate recovered


def test_step5_audit_trail_lifecycle_match(api_client):
    """J. Audit trail contains complete lifecycle represented by Case Workspace."""
    pay_id = f"pay_lifecycle_{int(time.time())}"

    r = api_client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": f"evt_life_{int(time.time())}",
            "payment_id": pay_id,
            "customer_id": "cust_life_test",
            "amount_minor": 45000,
            "error_reason": "payment_timed_out",
        },
    )
    assert r.status_code == 200

    r_detail = api_client.get(f"/api/recovery-items/{pay_id}")
    assert r_detail.status_code == 200
    detail = r_detail.json()

    events = [e["action"] for e in detail["audit_events"]]
    assert "recovery_item_created" in events or "signature_verified" in events
    assert "recovery_scored" in events
    assert "guard_evaluate" in events
