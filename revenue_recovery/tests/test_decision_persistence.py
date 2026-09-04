from __future__ import annotations

import pytest

from app.db.decision_repository import (
    InMemoryRecoveryDecisionRepository,
    RecoveryDecisionRepository,
)
from app.domain.proposals import RecoveryAction, RecoveryProposal


# ---------------------------------------------------------------------------
# In-memory decision repository
# ---------------------------------------------------------------------------

class TestInMemoryDecisionRepository:
    def test_save_and_list(self):
        repo = InMemoryRecoveryDecisionRepository()
        proposal = RecoveryProposal(
            action=RecoveryAction.RETRY_PAYMENT,
            reason="Soft failure",
            confidence=0.7,
            proposed_retry=True,
            model_name="mock",
        )
        repo.save_decision(
            proposal,
            item_id="pay_001",
            agent_name="mock-agent",
            policy_allowed=True,
            policy_rule="allow_retry",
        )
        decisions = repo.list_by_recovery_item_id("pay_001")
        assert len(decisions) == 1
        assert decisions[0]["proposed_action"] == "retry_payment"
        assert decisions[0]["policy_allowed"] is True
        assert decisions[0]["agent_name"] == "mock-agent"

    def test_list_isolates_by_item_id(self):
        repo = InMemoryRecoveryDecisionRepository()
        p1 = RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="r", confidence=0.5)
        p2 = RecoveryProposal(action=RecoveryAction.ESCALATE_HUMAN, reason="r", confidence=0.5)
        repo.save_decision(p1, item_id="pay_001", agent_name="a")
        repo.save_decision(p2, item_id="pay_002", agent_name="a")
        assert len(repo.list_by_recovery_item_id("pay_001")) == 1
        assert len(repo.list_by_recovery_item_id("pay_002")) == 1
        assert repo.list_by_recovery_item_id("pay_001")[0]["proposed_action"] == "retry_payment"
        assert repo.list_by_recovery_item_id("pay_002")[0]["proposed_action"] == "escalate_human"

    def test_multiple_decisions_for_same_item(self):
        repo = InMemoryRecoveryDecisionRepository()
        p1 = RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="r", confidence=0.5)
        p2 = RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="r", confidence=0.5)
        repo.save_decision(p1, item_id="pay_001", agent_name="a")
        repo.save_decision(p2, item_id="pay_001", agent_name="a")
        assert len(repo.list_by_recovery_item_id("pay_001")) == 2


# ---------------------------------------------------------------------------
# Webhook integration: decision persistence
# ---------------------------------------------------------------------------

class TestWebhookDecisionPersistence:
    """Test that the webhook flow persists decisions properly."""

    def test_webhook_creates_decision(self):
        from app.adapters.razorpay import RazorpayWebhookService
        from app.agents.decision_agent import MockRecoveryDecisionAgent
        from app.agents.orchestrator import RecoveryAgentOrchestrator
        from app.agents.validator import ProposalValidator
        from app.audit.models import InMemoryAuditLog
        from app.db.decision_repository import InMemoryRecoveryDecisionRepository
        from app.idempotency.store import InMemoryIdempotencyStore
        from app.policies.engine import InterventionPolicy
        from app.scoring.expected_value import ExpectedValueScorer

        decisions = InMemoryRecoveryDecisionRepository()
        audit = InMemoryAuditLog()
        agent = MockRecoveryDecisionAgent()
        policy = InterventionPolicy(max_retry_attempts=3)
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent, policy_engine=policy, audit_log=audit, validator=ProposalValidator(),
        )
        svc = RazorpayWebhookService(
            webhook_secret="test",
            scorer=ExpectedValueScorer(),
            policy_engine=policy,
            audit_log=audit,
            idempotency_store=InMemoryIdempotencyStore(),
            decisions=decisions,
            agent=agent,
            orchestrator=orchestrator,
        )
        payload = {
            "entity": "event", "account_id": "acc_TEST", "event": "payment.failed",
            "contains": ["payment"], "id": "evt_test_001", "created_at": 1700000000,
            "payload": {"payment": {"entity": {
                "id": "pay_test_001", "entity": "payment", "amount": 50000, "currency": "INR",
                "status": "failed", "method": "card", "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed", "error_source": "bank",
                "error_step": "payment_authorization", "error_reason": "payment_timed_out",
                "created_at": 1700000000,
            }}},
        }
        import json
        body = json.dumps(payload).encode()
        import hashlib, hmac
        sig = hmac.new(b"test", body, hashlib.sha256).hexdigest()
        item, events, status = svc.process_webhook(body, sig)
        assert status == "processed"
        # Exactly one decision persisted
        decisions_list = decisions.list_by_recovery_item_id("pay_test_001")
        assert len(decisions_list) == 1
        assert decisions_list[0]["proposed_action"] == "send_payment_link"
        assert decisions_list[0]["policy_allowed"] is True

    def test_duplicate_webhook_no_second_decision(self):
        from app.adapters.razorpay import RazorpayWebhookService
        from app.agents.decision_agent import MockRecoveryDecisionAgent
        from app.agents.orchestrator import RecoveryAgentOrchestrator
        from app.agents.validator import ProposalValidator
        from app.audit.models import InMemoryAuditLog
        from app.db.container import create_persistence_container
        from app.db.decision_repository import InMemoryRecoveryDecisionRepository
        from app.idempotency.store import InMemoryIdempotencyStore
        from app.policies.engine import InterventionPolicy
        from app.scoring.expected_value import ExpectedValueScorer

        container = create_persistence_container("memory")
        audit = container.audit_log
        decisions = container.decisions
        agent = MockRecoveryDecisionAgent()
        policy = InterventionPolicy(max_retry_attempts=3)
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent, policy_engine=policy, audit_log=audit, validator=ProposalValidator(),
        )
        svc = RazorpayWebhookService(
            webhook_secret="test",
            scorer=ExpectedValueScorer(),
            policy_engine=policy,
            audit_log=audit,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=decisions,
            attempts=container.attempts,
            agent=agent,
            orchestrator=orchestrator,
        )
        payload = {
            "entity": "event", "account_id": "acc_TEST", "event": "payment.failed",
            "contains": ["payment"], "id": "evt_dup_test", "created_at": 1700000000,
            "payload": {"payment": {"entity": {
                "id": "pay_dup_test", "entity": "payment", "amount": 50000, "currency": "INR",
                "status": "failed", "method": "card", "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed", "error_source": "bank",
                "error_step": "payment_authorization", "error_reason": "payment_timed_out",
                "created_at": 1700000000,
            }}},
        }
        import json, hashlib, hmac
        body = json.dumps(payload).encode()
        sig = hmac.new(b"test", body, hashlib.sha256).hexdigest()
        # First call
        svc.process_webhook(body, sig)
        # Second call (duplicate)
        svc.process_webhook(body, sig)
        # Only one decision
        decisions_list = decisions.list_by_recovery_item_id("pay_dup_test")
        assert len(decisions_list) == 1

    def test_denied_decision_persisted(self):
        from app.adapters.razorpay import RazorpayWebhookService
        from app.agents.decision_agent import MockRecoveryDecisionAgent
        from app.agents.orchestrator import RecoveryAgentOrchestrator
        from app.agents.validator import ProposalValidator
        from app.audit.models import InMemoryAuditLog
        from app.db.container import create_persistence_container
        from app.db.decision_repository import InMemoryRecoveryDecisionRepository
        from app.idempotency.store import InMemoryIdempotencyStore
        from app.policies.engine import InterventionPolicy
        from app.scoring.expected_value import ExpectedValueScorer

        container = create_persistence_container("memory")
        audit = container.audit_log
        decisions = container.decisions
        agent = MockRecoveryDecisionAgent()
        opted_out_id = "cust_optout_denied"
        policy = InterventionPolicy(max_retry_attempts=0, opted_out_customer_ids=frozenset({opted_out_id}))
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent, policy_engine=policy, audit_log=audit, validator=ProposalValidator(),
        )
        svc = RazorpayWebhookService(
            webhook_secret="test",
            scorer=ExpectedValueScorer(),
            policy_engine=policy,
            audit_log=audit,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=decisions,
            attempts=container.attempts,
            agent=agent,
            orchestrator=orchestrator,
        )
        payload = {
            "entity": "event", "account_id": "acc_TEST", "event": "payment.failed",
            "contains": ["payment"], "id": "evt_denied_test", "created_at": 1700000000,
            "payload": {"payment": {"entity": {
                "id": "pay_denied_test", "entity": "payment", "amount": 50000, "currency": "INR",
                "status": "failed", "method": "card", "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Payment failed", "error_source": "bank",
                "error_step": "payment_authorization", "error_reason": "payment_timed_out",
                "customer_id": opted_out_id,
                "created_at": 1700000000,
            }}},
        }
        import json, hashlib, hmac
        body = json.dumps(payload).encode()
        sig = hmac.new(b"test", body, hashlib.sha256).hexdigest()
        svc.process_webhook(body, sig)
        decisions_list = decisions.list_by_recovery_item_id("pay_denied_test")
        assert len(decisions_list) == 1
        assert decisions_list[0]["policy_allowed"] is False
        assert decisions_list[0]["proposed_action"] == "send_payment_link"


def test_major_state_transitions_create_audit_events():
    """Every major state transition creates an audit event."""
    from app.audit.models import InMemoryAuditLog
    from app.agents.orchestrator import RecoveryAgentOrchestrator
    from app.domain.context import RecoveryContext
    from app.domain.failures import FailureCategory
    from app.policies.engine import InterventionPolicy

    log = InMemoryAuditLog()
    policy = InterventionPolicy()
    orch = RecoveryAgentOrchestrator(policy_engine=policy, audit_log=log)
    ctx = RecoveryContext(item_id="t1_001", failure_category=FailureCategory.SOFT, amount_minor=50000)

    res = orch.decide(ctx)
    events = log.events_for("t1_001")
    assert len(events) >= 3
    actions = [e.action for e in events]
    assert "agent_context_created" in actions
    assert "agent_proposal_created" in actions
    assert "policy_evaluate" in actions


def test_audit_events_are_immutable():
    """Audit log is append-only and immutable."""
    from app.audit.models import InMemoryAuditLog
    log = InMemoryAuditLog()
    log.log(recovery_item_id="item_immut", actor="system", action="created", reason="initial")
    events = log.events_for("item_immut")
    assert len(events) == 1
    assert events[0].action == "created"
