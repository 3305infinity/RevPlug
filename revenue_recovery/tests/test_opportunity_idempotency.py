"""Regression test for live data idempotency.

Asserts that creating the same recovery case twice in a row increases
the recovery queue count by exactly 1, not 2.
"""
import time
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.db.container import create_persistence_container
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from datetime import datetime, timezone


def test_live_data_idempotency_does_not_create_duplicate_rows():
    """Create the same live case twice and assert recovery inbox count increases by exactly 1."""
    # Create app with explicit container so we control the data
    container = create_persistence_container("memory")
    app = create_app(webhook_secret="test-secret")
    app.state.container = container
    client = TestClient(app)

    item_id = "live_idempotent_001"
    customer_id = "cust_idempotent_101"

    # Get initial inbox count (should be 0)
    resp1 = client.get("/api/opportunity-inbox")
    assert resp1.status_code == 200
    initial_count = len(resp1.json())

    # Create a live operational item directly
    item = RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"evt_idem_{int(time.time())}",
        customer_id=customer_id,
        amount_minor=499900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="authentication_required",
        recovery_probability=0.7,
        expected_recovery_value=350000,
        intervention_cost=500,
        metadata={"customer_name": "Test Merchant Alpha", "is_synthetic": False, "source": "manual_case"},
    )
    container.recovery_items.save(item)

    resp_after_first = client.get("/api/opportunity-inbox")
    assert resp_after_first.status_code == 200
    count_after_first = len(resp_after_first.json())
    assert count_after_first == initial_count + 1, f"Expected count to increase by 1, got {count_after_first}"

    # Try to create the same item again (simulating duplicate event with same ID)
    item2 = RecoveryItem(
        id=item_id,  # Same ID = idempotent
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"evt_idem_{int(time.time())}_dup",
        customer_id=customer_id,
        amount_minor=499900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="authentication_required",
        recovery_probability=0.7,
        expected_recovery_value=350000,
        intervention_cost=500,
        metadata={"customer_name": "Test Merchant Alpha", "is_synthetic": False, "source": "manual_case"},
    )
    container.recovery_items.save(item2)

    resp_after_second = client.get("/api/opportunity-inbox")
    assert resp_after_second.status_code == 200
    count_after_second = len(resp_after_second.json())

    # Assert no duplicate case was created!
    assert count_after_second == count_after_first, f"Duplicate scenario execution created extra row! Expected {count_after_first}, got {count_after_second}"
