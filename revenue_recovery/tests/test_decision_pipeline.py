"""Decision pipeline architecture and safety invariant regression tests."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.agents.candidate_scorer import _eligible_candidates, build_ranked_proposal
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.db.container import create_in_memory_container


def test_eligible_candidates_excludes_fraud_and_opt_out():
    """Fraud or customer opt-out must return strictly STOP_RECOVERY as candidate."""
    ctx_fraud = RecoveryContext(
        failure_category=FailureCategory.FRAUD,
        retryable=False,
        attempt_count=0,
        amount_minor=500000,
        currency="INR",
        customer_opt_out=False,
        item_id="item_fraud_test",
    )
    eligible_fraud = _eligible_candidates(ctx_fraud)
    assert eligible_fraud == [RecoveryAction.STOP_RECOVERY.value]

    ctx_optout = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=500000,
        currency="INR",
        customer_opt_out=True,
        item_id="item_optout_test",
    )
    eligible_optout = _eligible_candidates(ctx_optout)
    assert eligible_optout == [RecoveryAction.STOP_RECOVERY.value]


def test_retry_budget_exhausted_excludes_retry():
    """Exhausting retry attempts must exclude retry_payment from eligible candidates."""
    ctx = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=3,
        max_attempts=3,
        amount_minor=500000,
        currency="INR",
        customer_opt_out=False,
        item_id="item_retry_budget_test",
    )
    eligible = _eligible_candidates(ctx)
    assert RecoveryAction.RETRY_PAYMENT.value not in eligible


def test_deterministic_ranking_same_input():
    """Same context must produce identical candidate ordering and top proposal."""
    ctx = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=1200000,
        currency="INR",
        customer_opt_out=False,
        item_id="item_det_test",
    )

    agent = MockRecoveryDecisionAgent()
    prop1 = agent.propose(ctx)
    prop2 = agent.propose(ctx)

    assert prop1.action == prop2.action
    assert prop1.reason == prop2.reason
    assert prop1.confidence == prop2.confidence
    assert [c.action for c in prop1.candidates] == [c.action for c in prop2.candidates]


def test_proposal_evidence_contains_inspectable_eligibility_trace():
    """Decision trace must record eligible and excluded candidate explanations."""
    ctx = RecoveryContext(
        failure_category=FailureCategory.AUTHENTICATION_REQUIRED,
        retryable=False,
        attempt_count=0,
        amount_minor=800000,
        currency="INR",
        customer_opt_out=False,
        item_id="item_auth_trace",
    )

    prop = build_ranked_proposal(ctx, scorer=ExpectedValueScorer())

    assert "eligible_candidates" in prop.evidence
    assert "excluded_candidates" in prop.evidence

    eligible_actions = [e["action"] for e in prop.evidence["eligible_candidates"]]
    assert RecoveryAction.SEND_PAYMENT_LINK.value in eligible_actions
    assert RecoveryAction.RETRY_PAYMENT.value not in eligible_actions


def test_policy_gate_blocks_execution_on_policy_denial():
    """If policy denies high-EV proposal, orchestrator MUST NOT execute action."""
    container = create_in_memory_container()

    # Fraud item produces high gross EV if scored, but policy blocks it
    item = RecoveryItem(
        id="item_fraud_policy_gate",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fraud_gate",
        customer_id="cust_fraud_gate",
        amount_minor=1000000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        root_cause="fraud",
    )
    container.recovery_items.save(item)

    ctx = RecoveryContext(
        failure_category=FailureCategory.FRAUD,
        retryable=False,
        attempt_count=0,
        amount_minor=1000000,
        currency="INR",
        customer_opt_out=False,
        item_id=item.id,
    )

    policy_engine = InterventionPolicy()
    stopping_rules = StoppingRules()
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    agent = MockRecoveryDecisionAgent()
    scorer = ExpectedValueScorer()

    orchestrator = RecoveryOrchestrator(
        agent=agent,
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        stopping_rules=stopping_rules,
        guard=guard,
        scorer=scorer,
        outcomes=container.outcomes,
    )

    res = orchestrator.run(item, ctx)

    # Execution MUST be skipped / None
    assert res.execution_result is None or res.execution_result.get("success") is False
    assert res.safety_decision in ("STOP", "DENY")

    # Item must be in terminal STOPPED state
    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status in [RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED]


def test_systemic_incident_triggers_wait_decision():
    """Systemic incident flag on retry_payment triggers WAIT decision."""
    container = create_in_memory_container()
    item = RecoveryItem(
        id="item_incident_test",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_incident",
        customer_id="cust_incident",
        amount_minor=500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
        metadata={"systemic_suppress": True},
    )
    container.recovery_items.save(item)

    ctx = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=500000,
        currency="INR",
        customer_opt_out=False,
        item_id=item.id,
        metadata={"systemic_suppress": True},
    )

    policy_engine = InterventionPolicy()
    stopping_rules = StoppingRules()
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    agent = MockRecoveryDecisionAgent()
    scorer = ExpectedValueScorer()

    orchestrator = RecoveryOrchestrator(
        agent=agent,
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        stopping_rules=stopping_rules,
        guard=guard,
        scorer=scorer,
    )

    res = orchestrator.run(item, ctx)
    assert res.safety_decision in ("WAIT", "STOP")
    assert res.execution_result is None
