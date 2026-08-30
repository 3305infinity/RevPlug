import pytest
from datetime import date, datetime, timedelta, timezone
from app.audit.models import InMemoryAuditLog
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.hinglish_promise import HinglishPromiseExtractor
from app.services.promise_service import PromiseService
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.db.container import create_persistence_container


def test_payment_failure_workflow_distinguishes_failure_types():
    """Verify payment failure path behaves differently for soft, hard, and fraud."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=InterventionPolicy()),
        agent=MockRecoveryDecisionAgent(),
    )

    # Soft failure → retry allowed
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
    assert res_soft.proposed_action == "retry_payment"

    # Fraud failure → stop
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

    # Fresh checkout (120 mins)
    item_fresh = RecoveryItem(
        id="chk_fresh", source_type=SourceType.CHECKOUT_ABANDONMENT, external_id="c_fresh", customer_id="c3",
        amount_minor=5000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="checkout_abandoned",
        metadata={"checkout_age_minutes": 120}
    )
    ctx_fresh = RecoveryContext(
        item_id=item_fresh.id, failure_category=FailureCategory.UNKNOWN, retryable=False, attempt_count=0,
        amount_minor=5000, currency="INR", expected_recovery_value=2500, customer_opt_out=False,
        metadata={"source_type": "checkout_abandonment", "checkout_age_minutes": 120}
    )
    res_fresh = orchestrator.run(item_fresh, ctx_fresh)
    assert res_fresh.proposed_action == "send_payment_link"

    # Stale checkout (>7 days / 10080 mins)
    item_stale = RecoveryItem(
        id="chk_stale", source_type=SourceType.CHECKOUT_ABANDONMENT, external_id="c_stale", customer_id="c4",
        amount_minor=5000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="checkout_abandoned",
        metadata={"checkout_age_minutes": 15000}
    )
    ctx_stale = RecoveryContext(
        item_id=item_stale.id, failure_category=FailureCategory.UNKNOWN, retryable=False, attempt_count=0,
        amount_minor=5000, currency="INR", expected_recovery_value=0, customer_opt_out=False,
        metadata={"source_type": "checkout_abandonment", "checkout_age_minutes": 15000}
    )
    res_stale = orchestrator.run(item_stale, ctx_stale)
    assert res_stale.proposed_action == "stop_recovery"


def test_overdue_b2b_receivables_escalation_ladder():
    """Verify overdue receivable intervention escalation ladder."""
    agent = MockRecoveryDecisionAgent()

    # Day 1 -> send_reminder
    ctx1 = RecoveryContext(
        item_id="b2b_1", failure_category=FailureCategory.UNKNOWN, retryable=False, attempt_count=0,
        amount_minor=500000, currency="INR", expected_recovery_value=250000, customer_opt_out=False,
        metadata={"source_type": "overdue_receivable", "days_overdue": 1}
    )
    p1 = agent.propose(ctx1)
    assert p1.action.value == "send_reminder"

    # Day 14 -> escalate_human
    ctx14 = RecoveryContext(
        item_id="b2b_14", failure_category=FailureCategory.UNKNOWN, retryable=False, attempt_count=0,
        amount_minor=500000, currency="INR", expected_recovery_value=250000, customer_opt_out=False,
        metadata={"source_type": "overdue_receivable", "days_overdue": 14}
    )
    p14 = agent.propose(ctx14)
    assert p14.action.value == "escalate_human"


def test_hinglish_promise_extraction_and_lifecycle():
    """Verify Hinglish promise extraction, structure, and active stopping behavior."""
    extractor = HinglishPromiseExtractor()

    # Test "5 tareekh ko 50 hazaar transfer kar dunga"
    res1 = extractor.extract("5 tareekh ko 50 hazaar transfer kar dunga", reference_date=date(2026, 8, 1))
    assert res1.intent == "promise_to_pay"
    assert res1.amount_minor == 5000000
    assert res1.promised_date == "2026-08-05"
    assert res1.confidence >= 0.80

    # Test "Friday ko 10000 payment kar dunga"
    res2 = extractor.extract("Friday ko 10000 payment kar dunga", reference_date=date(2026, 8, 28))
    assert res2.intent == "promise_to_pay"
    assert res2.amount_minor == 1000000
    assert res2.confidence >= 0.80

    # Test missing amount -> incomplete_promise
    res3 = extractor.extract("main dekhunga baad me")
    assert res3.confidence <= 0.30

    # Test active promise stopping in recovery orchestrator
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
    assert decision.should_stop
    assert decision.reason_code == "active_promise_pauses_recovery"


def test_idempotency_and_no_double_counting():
    """Verify outcomes recorded twice do not double count actual recovered revenue."""
    container = create_persistence_container(mode="memory")
    from app.domain.models import RecoveryOutcome

    outcome1 = RecoveryOutcome(
        id="out_dup_1", recovery_item_id="item_dup_1", outcome_type="recovered",
        expected_recovery_minor=10000, actual_recovery_minor=10000, recovery_cost_minor=500,
        net_recovery_minor=9500, recovered_at=datetime.now(timezone.utc)
    )
    container.outcomes.save(outcome1)

    # Save exact same outcome again (simulating duplicate webhook or retry)
    outcome2 = RecoveryOutcome(
        id="out_dup_1", recovery_item_id="item_dup_1", outcome_type="recovered",
        expected_recovery_minor=10000, actual_recovery_minor=10000, recovery_cost_minor=500,
        net_recovery_minor=9500, recovered_at=datetime.now(timezone.utc)
    )
    container.outcomes.save(outcome2)

    # Verify single outcome record in repository
    retrieved = container.outcomes.get_for_item("item_dup_1")
    assert retrieved is not None
    assert retrieved.actual_recovery_minor == 10000


def test_audit_trail_api_endpoint():
    """Verify GET /api/recovery-items/{id}/audit-trail endpoint returns chronological timeline."""
    from fastapi.testclient import TestClient
    from app.main import app
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
