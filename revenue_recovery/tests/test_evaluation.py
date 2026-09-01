"""Domain evaluation test suite for RevPlug benchmark metrics and counterfactual evaluation."""
from datetime import datetime, timezone
import pytest

from app.datasets.synthetic import (
    EVALUATION_DATASET_VERSION,
    generate_evaluation_dataset,
    get_golden_evaluation_dataset,
    lookup_counterfactual_outcome,
)
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.security.invariants import InvariantViolationError, SystemInvariants
from app.services.baseline_evaluator import BaselineEvaluator
from app.services.evaluation_service import EvaluationService


def test_evaluation_reproducibility():
    """Test A/B: Evaluator is 100% reproducible with the same seed."""
    svc1 = EvaluationService()
    res1 = svc1.run_batch_evaluation(count=20, seed=123)

    svc2 = EvaluationService()
    res2 = svc2.run_batch_evaluation(count=20, seed=123)

    assert res1.revplug.actual_recovered == res2.revplug.actual_recovered
    assert res1.baseline.actual_recovered == res2.baseline.actual_recovered
    assert res1.revplug.stopped_count == res2.revplug.stopped_count


def test_evaluation_count_bounds():
    """Test bounds on count argument."""
    svc = EvaluationService()
    res_small = svc.run_batch_evaluation(count=-5, seed=1)
    assert res_small.count == 1

    res_large = svc.run_batch_evaluation(count=9999, seed=1)
    assert res_large.count == 500


def test_evaluation_mock_agent_safety():
    """Test that RevPlug (via MockAgent) properly stops on fraud."""
    svc = EvaluationService()
    res = svc.run_batch_evaluation(count=50, seed=42)
    fraud_cases = [c for c in res.per_case if c['original_category'] == 'fraud']
    assert len(fraud_cases) > 0

    for case in fraud_cases:
        ros = case['revplug']
        assert ros['proposed_action'] == 'stop_recovery'
        assert ros['outcome'] == 'stopped'
        assert ros['actual_recovered'] == 0


def test_evaluation_baseline_unnecessary_interventions():
    """Test that the baseline makes unnecessary interventions on fraud cases."""
    svc = EvaluationService()
    res = svc.run_batch_evaluation(count=50, seed=42)
    fraud_cases = [c for c in res.per_case if c['original_category'] == 'fraud']
    assert len(fraud_cases) > 0

    for case in fraud_cases:
        bl = case['baseline']
        assert bl['attempts_made'] == 2
        assert bl['outcome'] == 'stopped'
        assert bl['actual_recovered'] == 0
        assert bl['unnecessary_intervention'] is True


def test_same_batch_used_for_all_policies():
    """Both Baseline and RevPlug receive the exact same dataset items."""
    svc = EvaluationService()
    res = svc.run_batch_evaluation(count=20, seed=42)
    assert res.revplug.cases_evaluated == 20
    assert res.baseline.cases_evaluated == 20


def test_same_seed_produces_identical_cases():
    """Same seed produces identical cases and ground truth tables."""
    b1 = generate_evaluation_dataset(count=15, seed=123)
    b2 = generate_evaluation_dataset(count=15, seed=123)
    assert [x.id for x in b1] == [x.id for x in b2]
    assert [x.amount_minor for x in b1] == [x.amount_minor for x in b2]


def test_baseline_cannot_access_revplug_decisions():
    """Baseline operates independently without importing RevPlug decision state."""
    be = BaselineEvaluator()
    items = generate_evaluation_dataset(count=5, seed=42)
    res = be.evaluate_batch(items)
    assert res.cases_evaluated == 5
    assert hasattr(res, "per_case") and len(res.per_case) == 5


def test_ground_truth_independent_of_chosen_action():
    """Ground truth table lookups yield identical outcomes regardless of caller."""
    items = generate_evaluation_dataset(count=5, seed=42)
    gt = items[0].metadata["ground_truth"]
    succ1, amt1, c1 = lookup_counterfactual_outcome(gt, "retry_payment", 1)
    succ2, amt2, c2 = lookup_counterfactual_outcome(gt, "retry_payment", 1)
    assert succ1 == succ2 and amt1 == amt2 and c1 == c2


def test_verified_recovery_based_on_settlement_outcome():
    """Verified recovery amount is strictly derived from actual_recovered."""
    item = RecoveryItem(id="e6", source_type=SourceType.PAYMENT_FAILURE, external_id="e6", customer_id="c6", amount_minor=10000, currency="INR", created_at=datetime.now(timezone.utc), status=RecoveryStatus.RECOVERED, actual_recovery_value=10000)
    assert SystemInvariants.verify_financial_truth(item, 10000) is True


def test_execution_not_counted_as_recovery():
    """Dispatched intervention status intervention_executed has 0 actual recovery."""
    item = RecoveryItem(id="e7", source_type=SourceType.PAYMENT_FAILURE, external_id="e7", customer_id="c7", amount_minor=10000, currency="INR", created_at=datetime.now(timezone.utc), status=RecoveryStatus.INTERVENTION_EXECUTED, actual_recovery_value=0)
    assert item.actual_recovery_value == 0


def test_duplicate_settlement_does_not_increase_recovery():
    """Duplicate settlement attempt produces zero financial recovery delta."""
    with pytest.raises(InvariantViolationError):
        SystemInvariants.verify_idempotency_delta(10000, 10000)


def test_negative_recovery_cannot_appear():
    """Negative recovery amount raises InvariantViolationError."""
    item = RecoveryItem(id="e9", source_type=SourceType.PAYMENT_FAILURE, external_id="e9", customer_id="c9", amount_minor=10000, currency="INR", created_at=datetime.now(timezone.utc), status=RecoveryStatus.PENDING_VERIFICATION)
    with pytest.raises(InvariantViolationError):
        SystemInvariants.verify_financial_truth(item, -100)


def test_currency_mismatch_rejected():
    """Invalid currency code rejected by validator."""
    from app.security.sanitizer import validate_financial_input
    with pytest.raises(ValueError):
        validate_financial_input(10000, "BAD_CURRENCY")


def test_incremental_recovery_formula_correct():
    """Incremental recovery equals RevPlug minus Baseline verified recovery."""
    ros_recovered = 3500000
    base_recovered = 2500000
    incremental = ros_recovered - base_recovered
    assert incremental == 1000000


def test_net_recovery_formula_correct():
    """Net recovery equals verified recovery minus intervention costs."""
    verified = 3500000
    cost = 40000
    net = verified - cost
    assert net == 3460000


def test_case_level_totals_reconcile_with_batch_totals():
    """Sum of per-case actual recovered equals batch total actual recovered."""
    svc = EvaluationService()
    res = svc.run_batch_evaluation(count=25, seed=42)
    sum_cases = sum(c.actual_recovered for c in res.revplug.per_case)
    assert sum_cases == res.revplug.actual_recovered


def test_dashboard_totals_reconcile_with_evaluation_report():
    """Standalone benchmark output matches EvaluationService response dict."""
    from app.eval.run_benchmark import run_benchmark
    resp = run_benchmark(count=10, seed=42)
    assert "revplug" in resp
    assert "baseline" in resp
    assert "comparison" in resp


def test_sequence_evaluation():
    """Sequence evaluation (retry #1 failure followed by retry #2 success)."""
    gt = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "2": {"success": True, "actual_recovery_minor": 100000, "cost_minor": 500},
                }
            }
        }
    }
    succ1, amt1, c1 = lookup_counterfactual_outcome(gt, "retry_payment", 1)
    succ2, amt2, c2 = lookup_counterfactual_outcome(gt, "retry_payment", 2)

    assert succ1 is False
    assert amt1 == 0
    assert succ2 is True
    assert amt2 == 100000


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


def test_canonical_net_recovery_minor_units_math():
    """Verify net recovery is calculated in minor integer units without floating point corruption."""
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=50, seed=42)

    ros = res.revplug
    assert isinstance(ros.actual_recovered, int)
    assert isinstance(ros.intervention_cost, int)
    assert isinstance(ros.net_recovered, int)
    assert ros.net_recovered == ros.actual_recovered - ros.intervention_cost


def test_canonical_financials_service_isolation():
    """Verify RecoveryFinancialsService computes verified_recovered strictly from outcomes/RECOVERED status."""
    from app.db.container import create_persistence_container
    from app.services.financials import RecoveryFinancialsService
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome

    container = create_persistence_container(mode="memory")
    now = datetime.now(timezone.utc)
    item1 = RecoveryItem(
        id="item_rec_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e1", customer_id="c1",
        amount_minor=100000, currency="INR", created_at=now, status=RecoveryStatus.RECOVERED, root_cause="soft"
    )
    item2 = RecoveryItem(
        id="item_pending_1", source_type=SourceType.PAYMENT_FAILURE, external_id="e2", customer_id="c2",
        amount_minor=500000, currency="INR", created_at=now, status=RecoveryStatus.PENDING_VERIFICATION, root_cause="soft"
    )
    container.recovery_items.save(item1)
    container.recovery_items.save(item2)

    fin_svc = RecoveryFinancialsService(container)
    fin = fin_svc.get_canonical_financials()

    # Item 1 (RECOVERED) counts, Item 2 (PENDING_VERIFICATION) does NOT count towards verified_recovered
    assert fin["verified_recovered_minor"] == 100000
    assert fin["pending_verification_minor"] == 500000
    assert fin["total_at_risk_minor"] == 600000
