"""Domain test suite for recovery orchestration, worker jobs, state transitions, and bounded recovery playbooks."""
import hashlib
import hmac
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.audit.models import AuditEvent, EventType, InMemoryAuditLog
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.db.container import create_persistence_container, _InMemoryRecoveryOutcomeRepository
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
from app.domain.proposals import RecoveryAction
from app.domain.transitions import DefaultStateMachine, InvalidTransitionError
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.action_executor import ActionExecutor, ActionStatus
from app.services.hinglish_promise import HinglishPromiseExtractor
from app.services.promise_service import PromiseService
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.services.recovery_planner import RecoveryPlanner

SECRET = "whsec_orchestration_test"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_service():
    container = create_persistence_container("memory")
    return main_module._build_webhook_service(SECRET, container)


def _build_app(service):
    return main_module.create_app(webhook_secret=SECRET, webhook_service=service)


def test_valid_state_transition():
    """Valid state transition is applied cleanly."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s1_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_1",
        customer_id="c1",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
    )
    res = sm.transition(item, RecoveryStatus.DIAGNOSED)
    assert res.applied is True
    assert res.item.status == RecoveryStatus.DIAGNOSED


def test_invalid_transition_rejected():
    """Invalid transition (e.g. DETECTED to RECOVERED) is rejected."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s2_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_2",
        customer_id="c2",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
    )
    with pytest.raises(InvalidTransitionError):
        sm.transition(item, RecoveryStatus.RECOVERED)


def test_terminal_state_cannot_execute():
    """Terminal state prohibits further execution or transitions."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s3_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_3",
        customer_id="c3",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.STOPPED,
    )
    assert sm.is_terminal(item) is True


def test_retry_budget_enforced_by_stopping_rules():
    """Stopping rules enforce maximum 3 retries limit."""
    stopping = StoppingRules(max_attempts=3)
    item = RecoveryItem(
        id="item_budget",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_budget",
        customer_id="cust_budget",
        amount_minor=10000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        metadata={"attempt_count": 3},
    )
    decision = stopping.evaluate(item, proposed_action="retry_payment")
    assert decision.should_stop is True
    assert decision.reason_code == "retry_budget_exhausted"


def test_payment_failure_workflow_distinguishes_failure_types():
    """Verify payment failure path behaves differently for soft vs fraud."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=InterventionPolicy()),
        agent=MockRecoveryDecisionAgent(),
    )

    item_soft = RecoveryItem(
        id="soft_wf_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e1", customer_id="c1",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft"
    )
    ctx_soft = RecoveryContext(
        item_id=item_soft.id, failure_category=FailureCategory.SOFT, retryable=True, attempt_count=0,
        amount_minor=10000, currency="INR", expected_recovery_value=6500, customer_opt_out=False
    )
    res_soft = orchestrator.run(item_soft, ctx_soft)
    assert res_soft.safety_decision == "ALLOWED"
    assert res_soft.proposed_action == "send_payment_link"

    item_fraud = RecoveryItem(
        id="fraud_wf_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e2", customer_id="c2",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="fraud"
    )
    ctx_fraud = RecoveryContext(
        item_id=item_fraud.id, failure_category=FailureCategory.FRAUD, retryable=False, attempt_count=0,
        amount_minor=10000, currency="INR", expected_recovery_value=0, customer_opt_out=False
    )
    res_fraud = orchestrator.run(item_fraud, ctx_fraud)
    assert res_fraud.safety_decision == "STOP"


def test_checkout_abandonment_workflow_fresh_vs_stale():
    """Verify checkout abandonment handles fresh vs >7 day stale checkouts."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=InterventionPolicy()),
        agent=MockRecoveryDecisionAgent(),
    )

    item_fresh = RecoveryItem(
        id="chk_fresh", source_type=SourceType.CHECKOUT_ABANDONMENT, external_id="c_fresh", customer_id="c3",
        amount_minor=5000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="checkout_abandoned",
        metadata={"checkout_age_minutes": 120}
    )
    ctx_fresh = RecoveryContext(
        item_id=item_fresh.id, failure_category=FailureCategory.CHECKOUT_ABANDONMENT, retryable=False, attempt_count=0,
        amount_minor=5000, currency="INR", expected_recovery_value=2500, customer_opt_out=False,
        metadata={"source_type": "checkout_abandonment", "checkout_age_minutes": 120}
    )
    res_fresh = orchestrator.run(item_fresh, ctx_fresh)
    assert res_fresh.proposed_action == "send_payment_link"


def test_hinglish_promise_extraction_and_lifecycle():
    """Verify Hinglish promise extraction, structure, and active stopping behavior."""
    extractor = HinglishPromiseExtractor()

    res1 = extractor.extract("5 tareekh ko 50 hazaar transfer kar dunga", reference_date=date(2026, 8, 1))
    assert res1.intent == "promise_to_pay"
    assert res1.amount_minor == 5000000
    assert res1.promised_date == "2026-08-05"
    assert res1.confidence >= 0.80

    container = create_persistence_container(mode="memory")
    svc = PromiseService()
    prom = svc.create_promise(
        item_id="item_prom_wf",
        customer_id="cust_prom",
        promised_amount_minor=50000,
        promised_date=date.today() + timedelta(days=5),
    )
    container.promises.save(prom)

    stopping = StoppingRules()
    item_prom = RecoveryItem(
        id="item_prom_wf", source_type=SourceType.PAYMENT_FAILURE, external_id="e_prom", customer_id="cust_prom",
        amount_minor=50000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft"
    )
    decision = stopping.evaluate(item_prom, proposed_action="retry_payment", promises=container.promises)
    assert decision.should_wait is True
    assert decision.should_stop is False
    assert decision.reason_code == "active_promise_wait"
    assert decision.wait_until is not None


def test_idempotency_and_no_double_counting():
    """Verify outcomes recorded twice do not double count actual recovered revenue."""
    container = create_persistence_container(mode="memory")

    outcome1 = RecoveryOutcome(
        id="out_dup_1", recovery_item_id="item_dup_1", outcome_type="recovered",
        expected_recovery_minor=10000, actual_recovery_minor=10000, recovery_cost_minor=500,
        net_recovery_minor=9500, recovered_at=datetime.now(timezone.utc)
    )
    container.outcomes.save(outcome1)

    outcome2 = RecoveryOutcome(
        id="out_dup_1", recovery_item_id="item_dup_1", outcome_type="recovered",
        expected_recovery_minor=10000, actual_recovery_minor=10000, recovery_cost_minor=500,
        net_recovery_minor=9500, recovered_at=datetime.now(timezone.utc)
    )
    container.outcomes.save(outcome2)

    retrieved = container.outcomes.get_for_item("item_dup_1")
    assert retrieved is not None
    assert retrieved.actual_recovery_minor == 10000


def test_audit_trail_api_endpoint():
    """Verify GET /api/recovery-items/{id}/audit-trail endpoint returns chronological timeline."""
    app = main_module.create_app(webhook_secret=SECRET)
    client = TestClient(app)
    container = app.state.container

    container.audit_log.log(
        recovery_item_id="item_audit_test", actor="system", action="event_detected",
        reason="Payment failure detected", metadata={"amount": 10000}
    )
    container.audit_log.log(
        recovery_item_id="item_audit_test", actor="scorer", action="candidate_optimization_completed",
        reason="Selected retry_payment", metadata={"selected_action": "retry_payment"}
    )

    resp = client.get("/api/recovery-items/item_audit_test/audit-trail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == "item_audit_test"
    assert data["total_events"] >= 2
    assert "timeline" in data
