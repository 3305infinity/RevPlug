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
            metadata={
                "source": "manual_case",
                "is_synthetic": False,
                "proposed_action": "escalate_human",
                "policy_allowed": False,
            },
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
            metadata={"source": "manual_case", "is_synthetic": False},
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

    def test_recovery_item_expected_recovery_value_populated(self, client):
        """Recovery item detail should populate expected_recovery_value when recovery_probability is present."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container
        item = RecoveryItem(
            id="item_ev_test_100",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_ev_100",
            customer_id="cust_ev_100",
            amount_minor=100000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            recovery_probability=0.85,
            expected_recovery_value=85000,
            metadata={"source": "manual_case", "is_synthetic": False},
        )
        container.recovery_items.save(item)

        resp = client.get("/api/recovery-items/item_ev_test_100")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["expected_recovery_value"] == 85000
        assert detail["amount_minor"] == 100000

    def test_clear_recovery_item_preview_and_execution(self, client):
        """DELETE /api/recovery-items/{id} transactionally removes operational item & descendants."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container

        item_id = "clear_test_case_999"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_clear_999",
            customer_id="cust_clear_999",
            amount_minor=50000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            metadata={"source": "manual_case", "is_synthetic": False},
        )
        container.recovery_items.save(item)

        # Add a decision directly to the internal list
        if hasattr(container.decisions, "_decisions"):
            container.decisions._decisions.append({
                "recovery_item_id": item_id,
                "agent_name": "mock",
                "proposed_action": "send_payment_link",
                "reason": "testing clear",
                "confidence": 0.9,
                "policy_allowed": True,
            })

        # Test preview endpoint
        prev_resp = client.get(f"/api/recovery-items/{item_id}/clear-preview")
        assert prev_resp.status_code == 200
        preview = prev_resp.json()
        assert preview["recovery_case"] == 1
        assert preview["decisions_count"] >= 1

        # Test clear endpoint
        clear_resp = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_resp.status_code == 200
        result = clear_resp.json()
        assert result["status"] == "success"
        assert result["recovery_item_id"] == item_id

        # Verify case is gone
        get_resp = client.get(f"/api/recovery-items/{item_id}")
        assert get_resp.status_code == 404

        # Idempotent delete on non-existent case returns 404
        clear_again = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_again.status_code == 404

    def test_clear_recovery_item_preserves_audit_history(self, client):
        """Clearing operational data must preserve audit trail with tombstone event."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container

        item_id = "audit_preserve_case_100"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_audit_100",
            customer_id="cust_audit_100",
            amount_minor=75000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            metadata={"source": "manual_case", "is_synthetic": False},
        )
        container.recovery_items.save(item)

        # Create an audit event for the case using the log method
        if hasattr(container.audit_log, "log"):
            container.audit_log.log(
                recovery_item_id=item_id,
                actor="test",
                action="CASE_CREATED",
                reason="Test case for audit retention",
            )

        # Clear the case
        clear_resp = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_resp.status_code == 200

        # Verify operational data is gone
        get_resp = client.get(f"/api/recovery-items/{item_id}")
        assert get_resp.status_code == 404

        # Verify audit history is preserved and includes tombstone
        if hasattr(container.audit_log, "events_for"):
            events = container.audit_log.events_for(item_id)
            assert len(events) >= 2, f"Expected at least 2 audit events (original + tombstone), got {len(events)}"
            actions = [e.action for e in events]
            assert "CASE_CREATED" in actions, "Original audit event must be preserved"
            assert "case_cleared" in actions, "Tombstone event must be appended"

    def test_clear_recovery_item_cleans_all_descendants(self, client):
        """Clearing a case must remove decisions, attempts, outcomes, promises, jobs, provider_events."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        from app.ledger.attempts import AttemptRecord
        container = client.app.state.container

        item_id = "descendant_case_200"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_desc_200",
            customer_id="cust_desc_200",
            amount_minor=100000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
        )
        container.recovery_items.save(item)

        # Add decision directly to internal list
        if hasattr(container.decisions, "_decisions"):
            container.decisions._decisions.append({
                "recovery_item_id": item_id,
                "agent_name": "mock",
                "proposed_action": "send_payment_link",
                "reason": "testing descendants",
                "confidence": 0.9,
                "policy_allowed": True,
            })

        # Add attempt using AttemptRecord
        if hasattr(container.attempts, "record"):
            container.attempts.record(AttemptRecord(
                recovery_item_id=item_id,
                attempt_number=1,
                action="send_payment_link",
                outcome="success",
            ))

        # Add outcome directly to internal dict
        if hasattr(container.outcomes, "_outcomes"):
            from app.domain.models import RecoveryOutcome, OutcomeType
            container.outcomes._outcomes[item_id] = RecoveryOutcome(
                id=f"outcome_{item_id}",
                recovery_item_id=item_id,
                outcome_type=OutcomeType.RECOVERED,
                expected_recovery_minor=100000,
                actual_recovery_minor=95000,
            )

        # Add promise directly to internal dicts
        if hasattr(container.promises, "_by_item"):
            container.promises._by_item[item_id] = {
                "id": "promise_200",
                "recovery_item_id": item_id,
                "customer_id": "cust_desc_200",
                "promised_amount_minor": 100000,
                "promised_date": "2026-12-31",
                "status": "active",
            }
        if hasattr(container.promises, "_by_id"):
            container.promises._by_id["promise_200"] = {
                "id": "promise_200",
                "recovery_item_id": item_id,
                "customer_id": "cust_desc_200",
                "promised_amount_minor": 100000,
                "promised_date": "2026-12-31",
                "status": "active",
            }

        # Get preview and verify counts are non-zero
        prev_resp = client.get(f"/api/recovery-items/{item_id}/clear-preview")
        assert prev_resp.status_code == 200
        preview = prev_resp.json()
        assert preview["decisions_count"] >= 1
        assert preview["attempts_count"] >= 1
        assert preview["outcomes_count"] >= 1
        assert preview["promises_count"] >= 1

        # Clear the case
        clear_resp = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_resp.status_code == 200

        # Verify preview now shows 0 counts (item is gone)
        prev_resp2 = client.get(f"/api/recovery-items/{item_id}/clear-preview")
        assert prev_resp2.status_code == 404

    def test_clear_recovery_item_updates_dashboard_analytics(self, client):
        """After clearing, dashboard and analytics must no longer count the case."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container

        item_id = "analytics_case_300"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_analytics_300",
            customer_id="cust_analytics_300",
            amount_minor=60000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            metadata={"source": "manual_case", "is_synthetic": False},
        )
        container.recovery_items.save(item)

        # Verify item counts toward dashboard
        summary_before = client.get("/api/dashboard/summary").json()
        total_before = summary_before["total_items"]

        # Clear the case
        clear_resp = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_resp.status_code == 200

        # Verify item no longer counts toward dashboard
        summary_after = client.get("/api/dashboard/summary").json()
        assert summary_after["total_items"] == total_before - 1

    def test_clear_recovery_item_with_batch_membership(self, client):
        """Clearing a batch-scoped item should remove batch metadata before deletion."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone
        container = client.app.state.container

        item_id = "batch_case_400"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_batch_400",
            customer_id="cust_batch_400",
            amount_minor=80000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            metadata={"batch_id": "batch_test_123", "batch_scope": True},
        )
        container.recovery_items.save(item)

        # Verify preview shows batch_id
        prev_resp = client.get(f"/api/recovery-items/{item_id}/clear-preview")
        assert prev_resp.status_code == 200
        preview = prev_resp.json()
        assert preview.get("batch_id") == "batch_test_123"

        # Clear the case
        clear_resp = client.delete(f"/api/recovery-items/{item_id}")
        assert clear_resp.status_code == 200

        # Verify item is gone
        get_resp = client.get(f"/api/recovery-items/{item_id}")
        assert get_resp.status_code == 404
        """Strategy analytics returns 0 cases and empty arrays when no data exists, without fake fallbacks."""
        container = client.app.state.container
        container.reset_demo_data()

        resp = client.get("/api/strategy-analytics")
        assert resp.status_code == 200
        report = resp.json()
        assert report["total_historical_cases"] == 0
        assert report["strategies"] == []
        assert report["opportunity_signals"] == []
        assert report["financial_kpis"]["total_revenue_at_risk_minor"] == 0
        assert report["financial_kpis"]["revenue_recovered_minor"] == 0


class TestQueueSemanticsAndStatusClassification:
    def test_status_sets_semantics(self):
        """Verifies _ACTIVE_STATUSES and _TERMINAL_STATUSES are correctly partitioned."""
        from app.dashboard_api import _ACTIVE_STATUSES, _TERMINAL_STATUSES, _AT_RISK_STATUSES

        # Active statuses must include pending_verification and open states
        assert "pending_verification" in _ACTIVE_STATUSES
        assert "queued" in _ACTIVE_STATUSES
        assert "intervention_executed" in _ACTIVE_STATUSES

        # Terminal statuses must include recovered, stopped, failed, escalated
        assert "recovered" in _TERMINAL_STATUSES
        assert "stopped" in _TERMINAL_STATUSES
        assert "failed" in _TERMINAL_STATUSES
        assert "escalated" in _TERMINAL_STATUSES

        # Terminal statuses must NOT be in _ACTIVE_STATUSES or _AT_RISK_STATUSES
        for term in _TERMINAL_STATUSES:
            assert term not in _ACTIVE_STATUSES
            assert term not in _AT_RISK_STATUSES

    def test_dashboard_summary_revenue_at_risk_excludes_terminal_cases(self, client):
        """Revenue at risk and expected recovery must aggregate active open cases only."""
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        container = client.app.state.container
        container.reset_demo_data()

        # 1. Active pending_verification item
        item_active = RecoveryItem(
            id="item_active_verif",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_active_1",
            customer_id="cust_sem_1",
            amount_minor=100000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.PENDING_VERIFICATION,
            expected_recovery_value=65000,
            metadata={"source": "webhook_live", "is_synthetic": False},
        )
        # 2. Terminal stopped item
        item_stopped = RecoveryItem(
            id="item_terminal_stop",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_stopped_1",
            customer_id="cust_sem_2",
            amount_minor=200000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.STOPPED,
            expected_recovery_value=120000,
            stopped_reason="High fraud risk signal",
            metadata={"source": "webhook_live", "is_synthetic": False},
        )
        # 3. Terminal recovered item
        item_recovered = RecoveryItem(
            id="item_terminal_rec",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_rec_1",
            customer_id="cust_sem_3",
            amount_minor=300000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.RECOVERED,
            actual_recovery_value=300000,
            metadata={"source": "webhook_live", "is_synthetic": False},
        )

        container.recovery_items.save(item_active)
        container.recovery_items.save(item_stopped)
        container.recovery_items.save(item_recovered)

        summary = client.get("/api/dashboard/summary").json()

        # Revenue at risk must include only active item (100,000 minor)
        assert summary["revenue_at_risk"] == 100000

        # Expected recovery must include only active item (65,000 minor)
        assert summary["expected_recovery"] == 65000



