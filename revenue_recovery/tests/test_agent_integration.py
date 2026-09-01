from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.adapters.razorpay import RazorpayWebhookService
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import InMemoryAuditLog
from app.db.container import create_persistence_container
from app.domain.failures import FailureCategory
from app.idempotency.store import InMemoryIdempotencyStore
from app.policies.engine import InterventionPolicy
from app.scoring.expected_value import ExpectedValueScorer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SECRET = "test_webhook_secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    import hashlib
    import hmac
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payload(event_id: str, payment_id: str, error_reason: str, error_description: str = "Payment failed"):
    return {
        "entity": "event",
        "account_id": "acc_TEST",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": event_id,
        "created_at": 1700000000,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": error_description,
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": error_reason,
                    "created_at": 1700000000,
                }
            }
        },
    }


@pytest.fixture
def service():
    """Build a RazorpayWebhookService with the agent wired in."""
    container = create_persistence_container("memory")
    agent = MockRecoveryDecisionAgent()
    audit_log = container.audit_log
    policy_engine = InterventionPolicy(max_retry_attempts=3)
    orchestrator = RecoveryAgentOrchestrator(
        agent=agent,
        policy_engine=policy_engine,
        audit_log=audit_log,
        validator=ProposalValidator(),
    )
    return RazorpayWebhookService(
        webhook_secret=SECRET,
        scorer=ExpectedValueScorer(),
        policy_engine=policy_engine,
        audit_log=audit_log,
        idempotency_store=container.idempotency,
        provider_events=container.provider_events,
        recovery_items=container.recovery_items,
        decisions=container.decisions,
        attempts=container.attempts,
        agent=agent,
        orchestrator=orchestrator,
    ), audit_log


# ---------------------------------------------------------------------------
# Integration tests: Agent → Validator → Policy → Execution
# ---------------------------------------------------------------------------

class TestAgentWebhookIntegration:
    """Test the full webhook flow with the agent integrated."""

    def test_soft_failure_agent_proposes_retry(self, service):
        svc, audit = service
        payload = _payload("evt_soft", "pay_soft", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        assert item is not None
        assert item.root_cause == "soft"
        assert svc.last_proposal is not None
        assert svc.last_proposal.action.value == "retry_payment"
        assert svc.last_decision.allowed is True

    def test_hard_failure_agent_cannot_retry(self, service):
        svc, audit = service
        payload = _payload("evt_hard", "pay_hard", "card_declined")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        # Agent proposes SEND_PAYMENT_LINK for HARD (not retry)
        assert svc.last_proposal.action.value != "retry_payment"

    def test_fraud_agent_cannot_retry(self, service):
        svc, audit = service
        payload = _payload("evt_fraud", "pay_fraud", "payment_risk_check_failed",
                          "Risk check failed")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        # Agent proposes STOP_RECOVERY for FRAUD
        assert svc.last_proposal.action.value == "stop_recovery"

    def test_unknown_failure_escalates(self, service):
        svc, audit = service
        payload = _payload("evt_unknown", "pay_unknown", "some_unknown_reason")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        assert svc.last_proposal.action.value == "escalate_human"

    def test_duplicate_event_does_not_run_agent(self, service):
        svc, audit = service
        payload = _payload("evt_dup", "pay_dup", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        # First call: processed
        item1, events1, status1 = svc.process_webhook(body, sig)
        assert status1 == "processed"
        proposal1 = svc.last_proposal
        # Second call: duplicate
        item2, events2, status2 = svc.process_webhook(body, sig)
        assert status2 == "duplicate"
        assert item2 is None
        # Agent should not have run again
        assert svc.last_proposal is proposal1  # unchanged

    def test_expected_recovery_value_persisted_in_item(self, service):
        svc, audit = service
        payload = _payload("evt_score", "pay_score", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert item is not None
        assert item.expected_recovery_value is not None
        assert item.expected_recovery_value == 34500  # 50000 * 0.70 - 500

    def test_audit_trail_is_complete(self, service):
        svc, audit = service
        payload = _payload("evt_audit", "pay_audit", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        actions = [e.action for e in events]
        assert "signature_verified" in actions
        assert "failure_classified" in actions
        assert "agent_context_created" in actions
        assert "agent_proposal_created" in actions
        assert "policy_evaluate" in actions

    def test_opt_out_denies_outbound(self):
        """Opted-out customer cannot receive outbound actions."""
        container = create_persistence_container("memory")
        agent = MockRecoveryDecisionAgent()
        audit = container.audit_log
        policy = InterventionPolicy(
            max_retry_attempts=3,
            opted_out_customer_ids=frozenset({"cust_optout_test"}),
        )
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent,
            policy_engine=policy,
            audit_log=audit,
            validator=ProposalValidator(),
        )
        svc = RazorpayWebhookService(
            webhook_secret=SECRET,
            scorer=ExpectedValueScorer(),
            policy_engine=policy,
            audit_log=audit,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=container.decisions,
            attempts=container.attempts,
            agent=agent,
            orchestrator=orchestrator,
        )
        payload = _payload("evt_optout", "pay_optout", "payment_timed_out")
        payload["payload"]["payment"]["entity"]["customer_id"] = "cust_optout_test"
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        assert svc.last_decision.allowed is False

    def test_retry_limit_enforced(self):
        """Retry policy still wins even if agent proposes retry."""
        container = create_persistence_container("memory")
        agent = MockRecoveryDecisionAgent()
        audit = container.audit_log
        policy = InterventionPolicy(max_retry_attempts=0)
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent,
            policy_engine=policy,
            audit_log=audit,
            validator=ProposalValidator(),
        )
        svc = RazorpayWebhookService(
            webhook_secret=SECRET,
            scorer=ExpectedValueScorer(),
            policy_engine=policy,
            audit_log=audit,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=container.decisions,
            attempts=container.attempts,
            agent=agent,
            orchestrator=orchestrator,
        )
        payload = _payload("evt_limit", "pay_limit", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        assert svc.last_decision.allowed is False


# ---------------------------------------------------------------------------
# FastAPI endpoint integration
# ---------------------------------------------------------------------------

class TestEndpointWithAgent:
    """Test the FastAPI endpoint with the agent integrated."""

    def test_endpoint_returns_proposal(self):
        from app.main import create_app
        app = create_app(webhook_secret=SECRET)
        client = TestClient(app)
        payload = _payload("evt_endpoint", "pay_endpoint", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["recovery_item_id"] == "pay_endpoint"
        assert data["failure_category"] == "soft"
        assert data["expected_recovery_value"] == 34500  # 50000 * 0.70 - 500
        assert data["proposed_action"] == "retry_payment"
        assert data["policy_allowed"] is True
        assert data["agent_model"] == "mock"

    def test_endpoint_duplicate_returns_duplicate(self):
        from app.main import create_app
        app = create_app(webhook_secret=SECRET)
        client = TestClient(app)
        payload = _payload("evt_dup_endpoint", "pay_dup_endpoint", "payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        first = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert first.json()["status"] == "processed"
        second = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert second.json()["status"] == "duplicate"

    def test_endpoint_invalid_signature_rejected(self):
        from app.main import create_app
        app = create_app(webhook_secret=SECRET)
        client = TestClient(app)
        payload = _payload("evt_bad", "pay_bad", "payment_timed_out")
        body = json.dumps(payload).encode()
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": "bogus"})
        assert resp.status_code == 400
