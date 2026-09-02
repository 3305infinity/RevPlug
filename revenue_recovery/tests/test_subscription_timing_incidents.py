"""Tests for Subscription Recovery, Time-Optimal Timing & Revenue Incident Manager."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.recovery_timing import RecoveryTimingOptimizer
from app.services.revenue_incident_manager import RevenueIncidentManager
from app.db.container import create_persistence_container
from app.main import app


def test_recovery_timing_optimizer():
    """Verifies evidence-backed time-optimal recovery window calculation."""
    optimizer = RecoveryTimingOptimizer()
    item = RecoveryItem(
        id="item_tm_1",
        source_type=SourceType.SUBSCRIPTION_FAILURE,
        external_id="ext_tm_1",
        customer_id="cust_tm_1",
        amount_minor=499900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
    )

    opt = optimizer.calculate_optimal_window(item)

    assert "Tomorrow 10:30 AM" in opt.scheduled_display
    assert opt.optimal_retry_ev_minor > opt.immediate_retry_ev_minor
    assert "Customer historically completes" in opt.reason
    assert opt.expected_recovery_prob > 0.5


def test_revenue_incident_manager_cluster_detection_and_resolution():
    """Verifies systemic incident cluster detection, suppression policy, and resolution."""
    container = create_persistence_container("memory")

    # Seed items that trigger systemic detection: >= 3 with same (method, root_cause)
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    now = datetime.now(timezone.utc)
    for i in range(5):
        item = RecoveryItem(
            id=f"seed_upi_auth_{i}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"ext_seed_{i}",
            customer_id=f"cust_seed_{i}",
            amount_minor=500000 + i * 100000,
            currency="INR",
            created_at=now,
            status=RecoveryStatus.QUEUED,
            root_cause="authentication_required",
            metadata={
                "source": "webhook_live",
                "is_synthetic": False,
                "is_test_fixture": False,
                "method": "upi",
                "customer_name": f"Test Customer {i}",
            },
        )
        container.recovery_items.save(item)

    mgr = RevenueIncidentManager(container)
    incidents = mgr.detect_incidents()
    assert len(incidents) >= 1

    inc = incidents[0]
    assert inc.payment_method == "UPI"
    assert inc.status == "ACTIVE"
    assert inc.lift_vs_baseline > 1.5
    assert "authentication_required" in inc.failure_category.lower() or inc.failure_category == "authentication_required"
    assert "Suppress" in inc.recommendation or "suppress" in inc.recommendation.lower()

    res = mgr.resolve_incident(inc.incident_id)
    assert res["status"] == "RESOLVED"


def test_incidents_api_endpoints():
    """Verifies GET /api/incidents/summary, /active, and POST /api/incidents/{id}/resolve endpoints."""
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    from app.db.container import create_persistence_container

    # Seed a container with data that triggers systemic detection
    seeded_container = create_persistence_container("memory")
    now = datetime.now(timezone.utc)
    for i in range(5):
        item = RecoveryItem(
            id=f"seed_api_{i}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"ext_api_{i}",
            customer_id=f"cust_api_{i}",
            amount_minor=500000 + i * 100000,
            currency="INR",
            created_at=now,
            status=RecoveryStatus.QUEUED,
            root_cause="authentication_required",
            metadata={
                "source": "webhook_live",
                "is_synthetic": False,
                "is_test_fixture": False,
                "method": "upi",
                "customer_name": f"API Customer {i}",
            },
        )
        seeded_container.recovery_items.save(item)

    # Set the seeded container on the app state
    original_container = getattr(app.state, "container", None)
    app.state.container = seeded_container

    try:
        client = TestClient(app)

        resp_sum = client.get("/api/incidents/summary")
        assert resp_sum.status_code == 200
        sum_data = resp_sum.json()
        assert "active_incidents_count" in sum_data
        assert "revenue_protected_by_waiting_minor" in sum_data

        resp_act = client.get("/api/incidents/active")
        assert resp_act.status_code == 200
        act_data = resp_act.json()
        assert isinstance(act_data, list)
        assert len(act_data) >= 1

        target_id = act_data[0]["incident_id"]
        resp_res = client.post(f"/api/incidents/{target_id}/resolve")
        assert resp_res.status_code == 200
        assert resp_res.json()["status"] == "RESOLVED"
    finally:
        if original_container is not None:
            app.state.container = original_container
        elif hasattr(app.state, "container"):
            delattr(app.state, "container")
