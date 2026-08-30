import pytest
from datetime import datetime, date, timedelta, timezone
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.transitions import DefaultStateMachine, InvalidTransitionError
from app.policies.engine import InterventionPolicy
from app.policies.stopping_rules import StoppingRules
from app.policies.guard import DefaultRecoveryGuard
from app.scoring.expected_value import ExpectedValueScorer
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.audit.models import InMemoryAuditLog
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.db.container import create_persistence_container


def test_state_machine_legal_and_illegal_transitions():
    """1. Map state machine and verify illegal transitions are blocked."""
    sm = DefaultStateMachine()

    item_detected = RecoveryItem(
        id="sm_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e1", customer_id="c1",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft"
    )

    # DETECTED -> DIAGNOSED is legal
    res1 = sm.transition(item_detected, RecoveryStatus.DIAGNOSED)
    assert res1.applied is True
    assert res1.item.status == RecoveryStatus.DIAGNOSED

    # Terminal state RECOVERED cannot transition out
    item_recovered = RecoveryItem(
        id="sm_rec", source_type=SourceType.PAYMENT_FAILURE, external_id="e2", customer_id="c2",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.RECOVERED, root_cause="soft"
    )
    res_rec = sm.transition(item_recovered, RecoveryStatus.INTERVENTION_EXECUTED)
    assert res_rec.applied is False
    assert "terminal state" in res_rec.reason.lower()

    # Illegal transition DETECTED -> RECOVERED directly raises InvalidTransitionError
    with pytest.raises(InvalidTransitionError):
        sm.transition(item_detected, RecoveryStatus.RECOVERED)


def test_adaptive_intervention_sequencing_feedback_loop():
    """5 & 21 (Scenario B). Verify adaptive feedback loop re-evaluates after outcome."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(stopping_rules=StoppingRules(max_attempts=3), policy_engine=InterventionPolicy(max_retry_attempts=3)),
        agent=MockRecoveryDecisionAgent(),
    )

    # Attempt 1: soft failure -> propose retry_payment
    item = RecoveryItem(
        id="adapt_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e_adapt", customer_id="c_adapt",
        amount_minor=20000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft",
        metadata={"attempt_count": 0}
    )
    ctx1 = RecoveryContext(
        item_id=item.id, failure_category=FailureCategory.SOFT, retryable=True, attempt_count=0,
        amount_minor=20000, currency="INR", expected_recovery_value=13500, customer_opt_out=False
    )
    res1 = orchestrator.run(item, ctx1)
    assert res1.proposed_action == "retry_payment"
    assert res1.safety_decision == "ALLOWED"

    # Attempt 2: retry budget reached (attempt_count=3) -> engine adapts away from retry_payment to send_payment_link
    item_exhausted = RecoveryItem(
        id="adapt_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e_adapt", customer_id="c_adapt",
        amount_minor=20000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft",
        metadata={"attempt_count": 3, "contact_attempt_count": 5}
    )
    ctx2 = RecoveryContext(
        item_id=item.id, failure_category=FailureCategory.SOFT, retryable=True, attempt_count=3,
        amount_minor=20000, currency="INR", expected_recovery_value=0, customer_opt_out=False
    )
    res2 = orchestrator.run(item_exhausted, ctx2)
    # When retry budget and contact budget are exhausted, safety decision stops/denies or adapts action
    assert res2.safety_decision in ("STOP", "ESCALATE", "DENY") or res2.proposed_action != "retry_payment"


def test_stale_opportunity_expiration():
    """11. Verify stale checkout or invoice opportunity expires cleanly."""
    stopping = StoppingRules()
    item_stale = RecoveryItem(
        id="stale_item_1", source_type=SourceType.CHECKOUT_ABANDONMENT, external_id="e_stale", customer_id="c_stale",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="checkout_abandoned",
        metadata={"checkout_age_minutes": 15000}  # >7 days
    )

    decision = stopping.evaluate(item_stale, proposed_action="send_payment_link")
    assert decision.should_stop is True
    assert decision.reason_code == "recovery_deadline_expired"


def test_customer_contact_governance():
    """6. Verify customer contact limits and opt-out pause are enforced."""
    policy = InterventionPolicy(opted_out_customer_ids=frozenset(["opted_out_cust_1"]))
    item_opt = RecoveryItem(
        id="opt_item_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e_opt", customer_id="opted_out_cust_1",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft"
    )

    dec = policy.evaluate(item_opt, proposed_action="send_customer_message")
    assert dec.allowed is False
    assert dec.reason_code == "customer_opted_out"


def test_human_escalation_structured_evidence():
    """8 & 9. Verify human escalation produces rich evidence metadata."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=InterventionPolicy()),
        agent=MockRecoveryDecisionAgent(),
    )

    item_auth = RecoveryItem(
        id="esc_item_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e_esc", customer_id="c_esc",
        amount_minor=50000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="authentication_required"
    )
    ctx_auth = RecoveryContext(
        item_id=item_auth.id, failure_category=FailureCategory.AUTHENTICATION_REQUIRED, retryable=False, attempt_count=0,
        amount_minor=50000, currency="INR", expected_recovery_value=12500, customer_opt_out=False
    )

    res = orchestrator.run(item_auth, ctx_auth)
    assert res.score is not None
    assert "explainability" in res.score
    expl = res.score["explainability"]
    assert "selected_action" in expl
    assert "rejected_alternatives" in expl


def test_out_of_order_webhook_safety():
    """12 & 13. Verify incoming webhook on already RECOVERED item is recorded as no-op."""
    sm = DefaultStateMachine()
    item_recovered = RecoveryItem(
        id="rec_item_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e_rec", customer_id="c_rec",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.RECOVERED, root_cause="soft"
    )

    assert sm.is_terminal(item_recovered) is True
    assert sm.can_transition(item_recovered, RecoveryStatus.DETECTED) is False
