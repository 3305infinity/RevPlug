"""Tests for Policy Configuration Versioning, Human Review Queue, and Dashboard Redesign."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.policy_config_service import PolicyConfigStore
from app.db.container import create_persistence_container
from app.main import app


def test_policy_config_store_versioning():
    """Verifies policy config updates spawn explicit new versions (v1.0 -> v1.1)."""
    store = PolicyConfigStore.get_instance()
    cfg1 = store.get_config()
    assert cfg1.version == "v1.0"

    cfg2 = store.update_config({"max_retries": 4})
    assert cfg2.version == "v1.1"
    assert cfg2.max_retries == 4
    assert len(store.get_history()) >= 2


def test_policy_config_api_endpoints():
    """Verifies GET and PUT /api/policy-config endpoints."""
    client = TestClient(app)

    resp_get = client.get("/api/policy-config")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert "version" in data
    assert "preview_summary" in data

    resp_put = client.put("/api/policy-config", json={"max_retries": 5})
    assert resp_put.status_code == 200
    updated_data = resp_put.json()
    assert updated_data["max_retries"] == 5
    assert updated_data["version"] != data["version"]


def test_human_review_action_resumes_playbook():
    """Verifies POST /api/reviews/{id}/action validates human decision through policy engine and resumes playbook."""
    client = TestClient(app)

    # Seed an item into app container
    container = app.state.container
    item = RecoveryItem(
        id="item_rev_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_rev_101",
        customer_id="cust_rev_101",
        amount_minor=8400000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.ESCALATED,
        root_cause="dispute",
    )
    container.recovery_items.save(item)

    resp_act = client.post(f"/api/reviews/{item.id}/action", json={"action": "approve"})
    assert resp_act.status_code == 200
    res = resp_act.json()

    assert res["item_id"] == item.id
    assert res["action_taken"] == "approve"
    assert res["policy_validated"] is True
    assert res["playbook_resumed"] is True

    # Item status should be updated to INTERVENTION_PENDING
    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.INTERVENTION_PENDING
