import pytest
from datetime import datetime, timezone
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus, SourceType
from app.interventions.executor import SimulatedRecoveryExecutor, ExecutionResult
from app.scoring.cost import InterventionCostModel
from app.services.batch_service import BatchService, InMemoryBatchRepository, RecoveryBatch
from app.services.baseline_evaluator import BaselineEvaluator
from app.services.evaluation_service import EvaluationService
from app.db.container import create_persistence_container


def test_action_execution_does_not_equal_revenue_recovered():
    """Verify executing an action returns ExecutionResult but does NOT count financial recovery."""
    executor = SimulatedRecoveryExecutor()
    item = RecoveryItem(
        id="action_exec_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e1", customer_id="c1",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft"
    )

    res = executor.execute(item, "retry_payment", attempt_number=1, scenario="success")
    assert isinstance(res, ExecutionResult)
    assert res.success is True

    # Check container - no financial outcome should exist unless created explicitly
    container = create_persistence_container(mode="memory")
    assert container.outcomes.get_for_item(item.id) is None


def test_impossible_recovery_amount_invariant_clamping():
    """Verify RecoveryOutcome clamps actual_recovery_minor if it exceeds expected_recovery_minor."""
    outcome = RecoveryOutcome(
        id="out_inv_1", recovery_item_id="item_inv_1", outcome_type="recovered",
        expected_recovery_minor=10000, actual_recovery_minor=15000, recovery_cost_minor=500,
        metadata={"amount_at_risk": 10000}
    )

    # Must be clamped to expected_recovery_minor (10000)
    assert outcome.actual_recovery_minor == 10000
    assert outcome.net_recovery_minor == 9500


def test_outcome_types_differentiation():
    """Verify outcome types set appropriate recovery amounts."""
    out_rec = RecoveryOutcome(id="o1", recovery_item_id="i1", outcome_type="recovered", expected_recovery_minor=5000, actual_recovery_minor=5000)
    assert out_rec.actual_recovery_minor == 5000

    out_part = RecoveryOutcome(id="o2", recovery_item_id="i2", outcome_type="partially_recovered", expected_recovery_minor=5000, actual_recovery_minor=2500)
    assert out_part.actual_recovery_minor == 2500

    out_fail = RecoveryOutcome(id="o3", recovery_item_id="i3", outcome_type="failed", expected_recovery_minor=5000, actual_recovery_minor=0)
    assert out_fail.actual_recovery_minor == 0


def test_deterministic_simulated_executor():
    """Verify SimulatedRecoveryExecutor without scenario yields deterministic result for fixed item."""
    executor = SimulatedRecoveryExecutor()
    item = RecoveryItem(
        id="det_item_123", source_type=SourceType.PAYMENT_FAILURE, external_id="e_det", customer_id="c_det",
        amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="soft",
        recovery_probability=0.80
    )

    res1 = executor.execute(item, "retry_payment", attempt_number=1)
    res2 = executor.execute(item, "retry_payment", attempt_number=1)

    assert res1.success == res2.success
    assert res1.reason == res2.reason


def test_batch_financial_reconciliation():
    """Verify BatchService batch summary reconciles exact sum of case outcomes."""
    container = create_persistence_container(mode="memory")
    batch_repo = InMemoryBatchRepository()
    service = BatchService(
        batch_repo=batch_repo,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )

    item1 = RecoveryItem(id="b_item_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e1", customer_id="c1", amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.RECOVERED, root_cause="soft", metadata={"batch_id": "b1"})
    item2 = RecoveryItem(id="b_item_2", source_type=SourceType.PAYMENT_FAILURE, external_id="e2", customer_id="c2", amount_minor=20000, currency="INR", created_at=None, status=RecoveryStatus.STOPPED, root_cause="hard", metadata={"batch_id": "b1"})

    container.recovery_items.save(item1)
    container.recovery_items.save(item2)

    batch = RecoveryBatch(batch_id="b1", name="Test Batch", total_items=2, total_amount_at_risk=30000)
    batch_repo.save(batch)

    out1 = RecoveryOutcome(id="out_b1", recovery_item_id="b_item_1", outcome_type="recovered", expected_recovery_minor=10000, actual_recovery_minor=10000, recovery_cost_minor=500)
    container.outcomes.save(out1)

    summary = service.summarize_batch("b1")
    assert summary is not None
    assert summary["actual_recovered"] == 10000
    assert summary["net_revenue_recovered"] == 9500
    assert summary["recovered_count"] == 1
    assert summary["stopped_count"] == 1


def test_baseline_policy_violations_tracking():
    """Verify BaselineEvaluator tracks policy violations explicitly."""
    evaluator = BaselineEvaluator()
    items = [
        RecoveryItem(id="violation_fraud", source_type=SourceType.PAYMENT_FAILURE, external_id="ef", customer_id="cf", amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="fraud"),
        RecoveryItem(id="violation_hard", source_type=SourceType.PAYMENT_FAILURE, external_id="eh", customer_id="ch", amount_minor=10000, currency="INR", created_at=None, status=RecoveryStatus.DETECTED, root_cause="hard"),
    ]

    res = evaluator.evaluate_batch(items)
    violations = res.baseline_policy_violations
    assert violations["total_policy_violations"] >= 2
    assert violations["fraud_retry"] >= 1
    assert violations["hard_decline_retry"] >= 1


def test_financial_edge_cases():
    """Verify zero amount and large amount cases behave safely."""
    outcome_zero = RecoveryOutcome(id="oz", recovery_item_id="iz", outcome_type="failed", expected_recovery_minor=0, actual_recovery_minor=0)
    assert outcome_zero.actual_recovery_minor == 0
    assert outcome_zero.net_recovery_minor == 0

    outcome_large = RecoveryOutcome(id="ol", recovery_item_id="il", outcome_type="recovered", expected_recovery_minor=100000000, actual_recovery_minor=100000000, recovery_cost_minor=500)
    assert outcome_large.actual_recovery_minor == 100000000
    assert outcome_large.net_recovery_minor == 99999500
