from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app(webhook_secret="test_secret")
    return TestClient(app)


def _payload(event_id: str, payment_id: str, error_reason: str, amount: int = 50000):
    return {
        "entity": "event", "account_id": "acc_TEST", "event": "payment.failed",
        "contains": ["payment"], "id": event_id, "created_at": 1700000000,
        "payload": {"payment": {"entity": {
            "id": payment_id, "entity": "payment", "amount": amount, "currency": "INR",
            "status": "failed", "method": "card", "error_code": "BAD_REQUEST_ERROR",
            "error_description": "Payment failed", "error_source": "bank",
            "error_step": "payment_authorization", "error_reason": error_reason,
            "created_at": 1700000000,
        }}},
    }


def _sign(body: bytes, secret: str = "test_secret") -> str:
    import hashlib, hmac
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestDashboardAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_dashboard_summary_empty(self, client):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == 0
        assert data["recovered_count"] == 0

    def test_dashboard_summary_with_data(self, client):
        # Trigger a demo event
        payload = _payload("evt_summary", "pay_summary", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] >= 1
        assert data["decisions_total"] >= 1

    def test_recovery_items_list(self, client):
        payload = _payload("evt_list", "pay_list", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

        resp = client.get("/api/recovery-items")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        assert items[0]["id"] is not None
        assert items[0]["status"] is not None

    def test_recovery_item_detail(self, client):
        payload = _payload("evt_detail", "pay_detail", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

        resp = client.get("/api/recovery-items/pay_detail")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == "pay_detail"
        assert "audit_events" in detail
        assert "attempts" in detail
        assert "decisions" in detail

    def test_recovery_item_not_found(self, client):
        resp = client.get("/api/recovery-items/nonexistent")
        assert resp.status_code == 404

    def test_evaluations(self, client):
        resp = client.get("/api/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 10
        assert "pass_rate" in data
        assert "results" in data

    def test_demo_payment_failure(self, client):
        payload = {
            "event_id": "evt_demo_test",
            "payment_id": "pay_demo_test",
            "error_reason": "payment_timed_out",
        }
        resp = client.post("/api/demo/payment-failure", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["recovery_item_id"] == "pay_demo_test"

    def test_demo_payment_failure_duplicate(self, client):
        payload = {
            "event_id": "evt_demo_dup",
            "payment_id": "pay_demo_dup",
            "error_reason": "payment_timed_out",
        }
        # First call
        resp1 = client.post("/api/demo/payment-failure", json=payload)
        assert resp1.json()["status"] == "processed"
        # Second call (duplicate)
        resp2 = client.post("/api/demo/payment-failure", json=payload)
        assert resp2.json()["status"] == "duplicate"

    def test_webhook_then_dashboard(self, client):
        """Full flow: webhook → dashboard shows data."""
        payload = _payload("evt_flow", "pay_flow", "gateway_technical_error")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        # Send webhook
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200

        # Check dashboard
        summary = client.get("/api/dashboard/summary").json()
        assert summary["total_items"] >= 1

        # Check item detail
        detail = client.get("/api/recovery-items/pay_flow").json()
        assert detail["id"] == "pay_flow"
        assert len(detail["audit_events"]) > 0


class TestHumanInTheLoop:
    """Test human approval/rejection workflow."""

    def _create_escalated_item(self, client, root_cause="soft"):
        """Create an escalated item by directly saving to the container."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        # Access the container from the app state
        # The client's app is accessible via client.app (TestClient wraps the app)
        app = client.app if hasattr(client, "app") else None
        container = None
        app = client.app
        container = getattr(app.state, "container", None)
        if container is None:
            pytest.skip("No container available")

        item = RecoveryItem(
            id="pay_escalated_test",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_escalated_test",
            customer_id="cust_test",
            amount_minor=50000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.ESCALATED,
            root_cause=root_cause,
            expected_recovery_value=0,
            metadata={"proposed_action": "escalate_human", "policy_allowed": False},
        )
        container.recovery_items.save(item)
        container.audit_log.log(
            recovery_item_id="pay_escalated_test",
            actor="system",
            action="escalation_created",
            reason="Test escalation",
            metadata={},
        )
        return "pay_escalated_test"

    def test_pending_reviews_empty(self, client):
        resp = client.get("/api/reviews/pending")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pending_reviews_with_escalated(self, client):
        item_id = self._create_escalated_item(client)
        resp = client.get("/api/reviews/pending")
        assert resp.status_code == 200
        items = resp.json()
        assert any(i["id"] == item_id for i in items)

    def test_approve_item(self, client):
        item_id = self._create_escalated_item(client, root_cause="soft")
        resp = client.post(f"/api/recovery-items/{item_id}/approve", json={"action": "stop_recovery"})
        assert resp.status_code == 200
        data = resp.json()
        # stop_recovery is always allowed by policy
        assert data["status"] == "approved"

    def test_reject_item(self, client):
        item_id = self._create_escalated_item(client)
        resp = client.post(f"/api/recovery-items/{item_id}/reject")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    def test_approve_unsafe_action_blocked_by_policy(self, client):
        """Human cannot approve retry for fraud — policy must block it."""
        item_id = self._create_escalated_item(client, root_cause="fraud")
        resp = client.post(f"/api/recovery-items/{item_id}/approve", json={"action": "retry_payment"})
        assert resp.status_code == 200
        data = resp.json()
        # Policy should deny retry for fraud (root_cause=fraud)
        assert data["status"] == "denied_by_policy"

    def test_approve_nonexistent_item(self, client):
        resp = client.post("/api/recovery-items/nonexistent/approve", json={"action": "retry_payment"})
        assert resp.status_code == 404

    def test_reject_nonexistent_item(self, client):
        resp = client.post("/api/recovery-items/nonexistent/reject")
        assert resp.status_code == 404

    def test_agent_trace(self, client):
        item_id = self._create_escalated_item(client)
        resp = client.get(f"/api/recovery-items/{item_id}/agent-trace")
        assert resp.status_code == 200
        data = resp.json()
        assert data["item_id"] == item_id
        assert "agent_events" in data

    def test_items_list_for_control_plane_case_selection(self, client):
        """GET /api/items returns active recovery items for control plane case selection."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container
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

    def test_canonical_evaluation_endpoint(self, client):
        """GET /api/evaluations/canonical returns reproducible benchmark metrics with canonical_metadata."""
        resp = client.get("/api/evaluations/canonical")
        assert resp.status_code == 200
        data = resp.json()
        assert "canonical_metadata" in data
        meta = data["canonical_metadata"]
        assert meta["evaluation_id"] == "REC-BENCH-2026-S42-C50"
        assert meta["seed"] == 42
        assert meta["sample_count"] == 50
        assert "revplug" in data
        assert "baseline" in data
