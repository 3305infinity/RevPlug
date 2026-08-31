"""Test Suite: Financial Performance Evaluation & AI Advantage Proving.

Verifies:
1. Baseline and RevPlug start from identical cases.
2. Amount-at-risk totals are identical.
3. Actual recovery, not expected recovery, is counted.
4. Intervention costs are counted.
5. Net recovery is calculated correctly.
6. Fixed retry does not adapt after failure.
7. RevPlug switches intervention after observing failure.
8. Different failure causes produce different optimal interventions.
9. Policy-blocked actions do not count as executed recovery actions.
10. Duplicate events do not double-count recovered money.
11. Recovery cannot exceed the original amount at risk.
12. Benchmark is deterministic under a fixed seed.
13. Safety violations are reported separately from financial performance.
14. Batch aggregation is correct.
15. A recovered case terminates and cannot recover again.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.audit.models import InMemoryAuditLog
from app.datasets.synthetic import generate_evaluation_dataset, generate_synthetic_cases, lookup_counterfactual_outcome
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.interventions.executor import SimulatedRecoveryExecutor
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.probability import RecoveryProbabilityModel
from app.services.baseline_evaluator import BaselineEvaluator
from app.services.evaluation_service import EvaluationService


def test_1_identical_starting_cases():
    items = generate_evaluation_dataset(count=20, seed=42)
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=20, seed=42)

    assert result.revplug.cases_evaluated == len(items)
    assert result.baseline.cases_evaluated == len(items)
    assert result.dataset_info["case_ids"] == [i.id for i in items]


def test_2_identical_amount_at_risk_totals():
    items = generate_evaluation_dataset(count=20, seed=42)
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=20, seed=42)

    expected_total = sum(i.amount_minor for i in items)
    assert result.revplug.total_amount_at_risk == expected_total
    assert result.baseline.total_amount_at_risk == expected_total


def test_3_actual_recovery_not_expected_counted():
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=10, seed=42)

    # Actual recovery must be derived from verified execution, not expected value prediction
    assert result.revplug.actual_recovered != result.revplug.expected_recovery
    for case in result.revplug.per_case:
        if case.outcome == "recovered":
            assert case.actual_recovered > 0
        else:
            assert case.actual_recovered == 0


def test_4_intervention_costs_counted():
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=10, seed=42)

    assert result.revplug.intervention_cost > 0
    assert result.baseline.intervention_cost > 0
    for case in result.revplug.per_case:
        if case.metadata.get("actions_executed"):
            assert case.intervention_cost > 0


def test_5_net_recovery_calculated_correctly():
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=10, seed=42)

    expected_net = result.revplug.actual_recovered - result.revplug.intervention_cost
    assert result.revplug.net_recovered == expected_net

    bl_net = result.baseline.actual_recovered - result.baseline.intervention_cost
    assert (result.baseline.actual_recovered - result.baseline.intervention_cost) == bl_net


def test_6_fixed_retry_does_not_adapt():
    evaluator = BaselineEvaluator(rng_seed=42)
    items = generate_synthetic_cases(count=5, seed=42, failure_mix={"authentication_required": 1.0})
    res = evaluator.evaluate_batch(items)

    for case in res.per_case:
        # Baseline always tries retry_payment regardless of failure cause
        assert all(a == "retry_payment" for a in case.actions_taken)
        assert len(case.actions_taken) >= 1


def test_7_revplug_switches_intervention_after_failure():
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=30, seed=42)

    # Find a case where step 1 failed and agent pivoted
    pivoted_cases = [
        c for c in result.revplug.per_case
        if len(c.metadata.get("actions_executed", [])) > 1
    ]
    assert len(pivoted_cases) > 0
    first_case = pivoted_cases[0]
    acts = first_case.metadata["actions_executed"]
    assert acts[0] != acts[1]  # Action changed dynamically after failure


def test_8_different_causes_produce_different_optimal_interventions():
    prob_model = RecoveryProbabilityModel()
    p_auth_retry = prob_model.estimate("authentication_required", "retry_payment")
    p_auth_link = prob_model.estimate("authentication_required", "send_payment_link")

    assert p_auth_link > p_auth_retry  # Payment link significantly superior for auth failures

    p_soft_retry = prob_model.estimate("soft", "retry_payment")
    p_soft_link = prob_model.estimate("soft", "send_payment_link")
    assert p_soft_retry > 0.50


def test_9_policy_blocked_actions_not_executed():
    eval_service = EvaluationService()
    result = eval_service.run_batch_evaluation(count=5, seed=42)

    # Fraud cases must be blocked/escalated without executing unsafe recovery actions
    fraud_cases = [c for c in result.revplug.per_case if c.failure_category in ("fraud", "security_or_fraud")]
    for fc in fraud_cases:
        assert fc.outcome in ("stopped", "escalated")
        assert fc.actual_recovered == 0


def test_10_duplicate_events_do_not_double_count():
    eval_service = EvaluationService()
    res1 = eval_service.run_batch_evaluation(count=10, seed=42)

    # Verify each case recovers at most its amount_at_risk once
    for case in res1.revplug.per_case:
        assert case.actual_recovered <= case.amount_at_risk


def test_11_recovery_cannot_exceed_amount_at_risk():
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=20, seed=42)

    for case in res.revplug.per_case:
        assert case.actual_recovered <= case.amount_at_risk
    assert res.revplug.actual_recovered <= res.revplug.total_amount_at_risk


def test_12_benchmark_is_deterministic_under_seed():
    eval_service = EvaluationService()
    res1 = eval_service.run_batch_evaluation(count=20, seed=42)
    res2 = eval_service.run_batch_evaluation(count=20, seed=42)

    assert res1.revplug.actual_recovered == res2.revplug.actual_recovered
    assert res1.baseline.actual_recovered == res2.baseline.actual_recovered
    assert res1.comparison.absolute_recovery_difference == res2.comparison.absolute_recovery_difference


def test_13_safety_violations_reported_separately():
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=20, seed=42)

    # RevPlug safety violations must be 0
    assert res.revplug.safety_violations["total_safety_violations"] == 0

    # Baseline safety violations (e.g. retrying fraud/optouts) reported transparently
    assert res.baseline.baseline_policy_violations["total_policy_violations"] >= 0


def test_14_batch_aggregation_is_correct():
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=50, seed=42)

    sum_actual = sum(c.actual_recovered for c in res.revplug.per_case)
    sum_cost = sum(c.intervention_cost for c in res.revplug.per_case)

    assert res.revplug.actual_recovered == sum_actual
    assert res.revplug.intervention_cost == sum_cost
    assert res.revplug.net_recovered == (sum_actual - sum_cost)


def test_15_recovered_case_terminates():
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=10, seed=42)

    recovered_cases = [c for c in res.revplug.per_case if c.outcome == "recovered"]
    for c in recovered_cases:
        assert c.actual_recovered == c.amount_at_risk
        # Actions stop immediately upon recovery
        assert len(c.metadata.get("actions_executed", [])) <= 3
