import pytest
from datetime import date, timedelta
from app.audit.models import InMemoryAuditLog
from app.datasets.synthetic import generate_evaluation_dataset
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.baseline_evaluator import BaselineEvaluator
from app.services.evaluation_service import EvaluationService
from app.services.recovery_orchestrator import RecoveryOrchestrator


def test_ev_gate_blocks_non_positive_ev():
    """Verify that actions with non-positive EV are blocked by EV gate."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(
            stopping_rules=StoppingRules(),
            policy_engine=InterventionPolicy(),
        ),
    )

    item = RecoveryItem(
        id="test_ev_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_1",
        customer_id="cust_1",
        amount_minor=10,  # Extremely low amount (₹0.10), EV will be negative due to intervention cost (500)
        currency="INR",
        created_at=None,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
    )

    context = RecoveryContext(
        item_id=item.id,
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=10,
        currency="INR",
        expected_recovery_value=0,
        customer_opt_out=False,
    )

    from app.agents.decision_agent import MockRecoveryDecisionAgent
    orchestrator._agent = MockRecoveryDecisionAgent()

    result = orchestrator.run(item, context)

    assert result.safety_decision == "STOP"
    ev_events = [e for e in result.audit_events if e.action == "ev_check_failed"]
    assert len(ev_events) == 1
    assert ev_events[0].metadata["rule"] == "ev_gate_enforcement"


def test_ground_truth_labels_in_synthetic_dataset():
    """Verify that synthetic dataset generator produces ground-truth metadata."""
    items = generate_evaluation_dataset(count=20, seed=42)
    assert len(items) == 20

    for item in items:
        gt = item.metadata.get("ground_truth")
        assert gt is not None
        assert "true_root_cause" in gt
        assert "correct_action" in gt
        assert "acceptable_actions" in gt
        assert "recoverable" in gt
        assert "should_stop" in gt


def test_decision_quality_metrics_in_evaluation():
    """Verify that evaluation service computes decision quality metrics."""
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=30, seed=42)

    ros = res.revplug
    assert hasattr(ros, "decision_quality")
    dq = ros.decision_quality

    assert "root_cause_accuracy" in dq
    assert "intervention_accuracy" in dq
    assert "proposal_action_accuracy" in dq
    assert "final_action_accuracy" in dq
    assert "escalation_precision" in dq
    assert "stopping_rule_compliance" in dq
    assert "prevented_unsafe_actions" in dq


def test_baseline_policy_violations_tracking():
    """Verify baseline evaluator tracks policy violations."""
    items = generate_evaluation_dataset(count=30, seed=42)
    evaluator = BaselineEvaluator(rng_seed=42)
    res = evaluator.evaluate_batch(items)

    assert hasattr(res, "baseline_policy_violations")
    bv = res.baseline_policy_violations

    assert "fraud_retry" in bv
    assert "do_not_contact_violation" in bv
    assert "hard_decline_retry" in bv
    assert "retry_budget_violation" in bv
    assert "promise_contact_violation" in bv
    assert "total_policy_violations" in bv
    assert bv["total_policy_violations"] > 0


def test_human_approval_re_evaluates_safety_guard():
    """Verify human approval re-checks stopping rules on fresh state."""
    from app.db.container import create_persistence_container
    container = create_persistence_container(mode="memory")

    item = RecoveryItem(
        id="item_opted_out",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_opt",
        customer_id="cust_opted_out",
        amount_minor=10000,
        currency="INR",
        created_at=None,
        status=RecoveryStatus.INTERVENTION_PENDING,
        root_cause="soft",
        metadata={"customer_opted_out": True},
    )
    container.recovery_items.save(item)

    policy = InterventionPolicy(opted_out_customer_ids=frozenset(["cust_opted_out"]))
    stopping = StoppingRules(opted_out_customer_ids=frozenset(["cust_opted_out"]))
    guard = DefaultRecoveryGuard(stopping_rules=stopping, policy_engine=policy)

    stub = item
    decision = guard.evaluate(stub, "send_customer_message", container=container)

    assert not decision.allowed
    assert decision.decision_type == "STOP"
    assert decision.reason_code == "customer_opted_out"
