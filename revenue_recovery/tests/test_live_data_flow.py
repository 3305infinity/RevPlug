import time
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_live_data_flow_canonical_pipeline():
    """End-to-end data flow test ensuring live operational data drives all views."""
    from app.db.container import create_persistence_container
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    from datetime import datetime, timezone
    from app.services.settlement_verifier import SettlementVerifier, SettlementEvent

    container = create_persistence_container("memory")

    customer_id = "test_customer_001"
    item_id = "live_flow_item_001"

    # 1. Create a live operational recovery item directly
    item = RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"evt_live_flow_{int(time.time())}",
        customer_id=customer_id,
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.PENDING_VERIFICATION,
        root_cause="soft",
        recovery_probability=0.7,
        expected_recovery_value=35000,
        intervention_cost=500,
        metadata={"customer_name": "Live Test Customer", "is_synthetic": False, "source": "manual_case"},
    )
    container.recovery_items.save(item)

    # 2. Check /api/recovery-items (via TestClient with this container)
    from fastapi.testclient import TestClient
    from app.main import create_app
    app = create_app(webhook_secret="test-secret")
    app.state.container = container
    client = TestClient(app)

    res_items = client.get("/api/recovery-items")
    assert res_items.status_code == 200
    items = res_items.json()
    found_item = next((i for i in items if i["id"] == item_id), None)
    assert found_item is not None
    assert found_item["customer_id"] == customer_id

    # 3. Process settlement event via SettlementVerifier
    verifier = SettlementVerifier(
        recovery_items=container.recovery_items,
        outcomes=container.outcomes,
        audit_log=container.audit_log,
    )
    verifier.process_settlement(SettlementEvent(
        event_id=f"evt_settle_{item_id}",
        provider="razorpay",
        recovery_item_id=item_id,
        success=True,
        actual_amount_minor=50000,
    ))

    # 4. Check /api/customers after verified settlement
    res_cust_list = client.get("/api/customers")
    assert res_cust_list.status_code == 200
    customers = res_cust_list.json()
    found_cust = next((c for c in customers if c["customer_id"] == customer_id), None)
    assert found_cust is not None
    assert found_cust["total_cases"] == 1
    assert found_cust["actually_recovered"] == 50000
    assert len(found_cust["cases"]) == 1

    # 5. Check /api/customers/{id}
    res_cust_detail = client.get(f"/api/customers/{customer_id}")
    assert res_cust_detail.status_code == 200
    cust_detail = res_cust_detail.json()
    assert cust_detail["customer_id"] == customer_id
    assert cust_detail["total_cases"] == 1
    assert len(cust_detail["cases"]) == 1
    assert cust_detail["cases"][0]["id"] == item_id

    # 6. Check /api/dashboard/summary
    res_summary = client.get("/api/dashboard/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["actually_recovered"] >= 50000

    # 7. Fraud case -> Stopped case test
    fraud_item_id = "live_flow_fraud_001"
    fraud_item = RecoveryItem(
        id=fraud_item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"evt_fraud_live_{int(time.time())}",
        customer_id=customer_id,
        amount_minor=75000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.STOPPED,
        root_cause="fraud",
        recovery_probability=0.0,
        expected_recovery_value=0,
        intervention_cost=0,
        metadata={"customer_name": "Live Test Customer", "is_synthetic": False, "source": "manual_case", "stopped_reason": "fraud_risk"},
    )
    container.recovery_items.save(fraud_item)

    # Verify stopped case appears under customer history
    res_cust_detail2 = client.get(f"/api/customers/{customer_id}")
    cust_detail2 = res_cust_detail2.json()
    assert cust_detail2["total_cases"] == 2
    assert cust_detail2["stopped_cases"] == 1
