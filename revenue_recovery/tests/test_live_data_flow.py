import time
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_live_data_flow_canonical_pipeline():
    """End-to-end data flow test ensuring canonical persistence drives all views."""
    app = create_app(webhook_secret="test-secret")
    client = TestClient(app)

    customer_id = "test_customer_001"
    event_id = f"evt_test_flow_{int(time.time())}"
    payment_id = f"pay_test_flow_{int(time.time())}"

    # 1. Trigger recovery for test_customer_001
    res_trigger = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": customer_id,
            "amount_minor": 50000, # ₹500
            "error_reason": "payment_timed_out", # Retryable failure -> RECOVERED
            "metadata": {"source_type": "payment_failure"},
        },
    )
    assert res_trigger.status_code == 200
    trigger_data = res_trigger.json()
    assert trigger_data["status"] == "processed"
    item_id = trigger_data["recovery_item_id"]
    assert item_id is not None
    assert trigger_data["recovery_status"] == "recovered"

    # 2. Check /api/recovery-items
    res_items = client.get("/api/recovery-items")
    assert res_items.status_code == 200
    items = res_items.json()
    found_item = next((i for i in items if i["id"] == item_id), None)
    assert found_item is not None
    assert found_item["customer_id"] == customer_id
    assert found_item["status"] == "recovered"

    # 3. Check /api/customers
    res_cust_list = client.get("/api/customers")
    assert res_cust_list.status_code == 200
    customers = res_cust_list.json()
    found_cust = next((c for c in customers if c["customer_id"] == customer_id), None)
    assert found_cust is not None
    assert found_cust["total_cases"] == 1
    assert found_cust["actually_recovered"] > 0
    assert len(found_cust["cases"]) == 1

    # 4. Check /api/customers/{id}
    res_cust_detail = client.get(f"/api/customers/{customer_id}")
    assert res_cust_detail.status_code == 200
    cust_detail = res_cust_detail.json()
    assert cust_detail["customer_id"] == customer_id
    assert cust_detail["total_cases"] == 1
    assert len(cust_detail["cases"]) == 1
    assert cust_detail["cases"][0]["id"] == item_id

    # 5. Check /api/dashboard/summary
    res_summary = client.get("/api/dashboard/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["actually_recovered"] >= trigger_data["expected_recovery_value"]

    # 6. Duplicate event trigger -> Idempotency test
    res_dup = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": customer_id,
            "amount_minor": 50000,
            "error_reason": "payment_timed_out",
        },
    )
    assert res_dup.status_code == 200
    assert res_dup.json()["status"] == "duplicate"

    # Re-verify dashboard summary does NOT double count
    res_summary2 = client.get("/api/dashboard/summary")
    assert res_summary2.json()["actually_recovered"] == summary["actually_recovered"]

    # 7. Fraud case -> Stopped case test
    fraud_event_id = f"evt_fraud_{int(time.time())}"
    fraud_payment_id = f"pay_fraud_{int(time.time())}"
    res_fraud = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": fraud_event_id,
            "payment_id": fraud_payment_id,
            "customer_id": customer_id,
            "amount_minor": 75000, # ₹750
            "error_reason": "payment_risk_check_failed", # Fraud reason -> STOPPED
        },
    )
    assert res_fraud.status_code == 200
    fraud_data = res_fraud.json()
    assert fraud_data["recovery_status"] == "stopped"

    # Verify stopped case appears under customer history
    res_cust_detail2 = client.get(f"/api/customers/{customer_id}")
    cust_detail2 = res_cust_detail2.json()
    assert cust_detail2["total_cases"] == 2
    assert cust_detail2["stopped_cases"] == 1
