"""Tests for Single Case Recovery Control Plane & Orchestration."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.main import app


def test_items_list_for_control_plane_case_selection():
    """Verifies GET /api/items returns active recovery items for control plane case selection."""
    client = TestClient(app)

    container = app.state.container
    item = RecoveryItem(
        id="cp_item_505",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_cp_505",
        customer_id="cust_cp_505",
        amount_minor=650000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="payment_timed_out",
    )
    container.recovery_items.save(item)

    resp = client.get("/api/items")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert any(i["id"] == "cp_item_505" for i in items)


def test_orchestration_run_for_selected_case_id():
    """Verifies POST /api/run-simulation executes server-side orchestration targeting the selected item ID."""
    client = TestClient(app)

    container = app.state.container
    item = RecoveryItem(
        id="cp_item_606",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_cp_606",
        customer_id="cust_cp_606",
        amount_minor=899900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="payment_timed_out",
    )
    container.recovery_items.save(item)

    payload = {
        "item_id": item.id,
        "customer_id": item.customer_id,
        "amount_minor": item.amount_minor,
        "failure_reason": item.root_cause,
        "source_type": item.source_type.value,
        "ai_provider": "groq",
    }

    resp = client.post("/api/run-simulation", json=payload)
    assert resp.status_code == 200
    res = resp.json()

    assert "attempt_number" in res or "status" in res or "action_taken" in res
