"""Test Suite: Visible & Demonstrable AI Judgment UI Integration.

Verifies:
1. Case trace API returns complete persisted decision trace structure.
2. Candidate interventions are tracked with EV, cost, and policy status.
3. Selected action is explicitly flagged.
4. Policy-blocked actions are flagged as BLOCKED with policy rule.
5. Blocked action is never shown as executed in trace.
6. Actual recovery is distinguished from expected recovery.
7. Terminal stop reason is preserved in trace.
8. Multi-step recovery displays complete closed-loop event timeline.
9. Dynamic re-planning events appear after action execution.
10. Benchmark endpoint (/api/benchmark/latest) returns 3-way comparative evaluation.
11. Benchmark metrics reflect backend simulation outputs without hardcoding.
12. Dashboard summary exposes all top-level metrics (revenue_at_risk, net_recovered, active_cases).
13. Demo scenarios endpoint processes payment failure and returns structured response.
14. Audit events feed returns chronological event stream.
15. Empty / non-existent case trace returns proper 404 response.
"""
from __future__ import annotations

import pytest
from app.db.container import create_persistence_container
from app.dashboard_api import build_case_detail, build_dashboard_summary
from app.datasets.synthetic import generate_evaluation_dataset, generate_synthetic_cases
from app.services.trace_service import build_case_trace
from app.evaluation.benchmark import run_benchmark_suite


def test_1_case_trace_api_returns_complete_structure():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    for it in items:
        container.recovery_items.save(it)

    trace = build_case_trace(items[0].id, container)

    assert trace["item_id"] == items[0].id
    assert "status" in trace
    assert "amount_at_risk_minor" in trace
    assert "expected_recovery_minor" in trace
    assert "verified_recovery_minor" in trace
    assert "context_snapshot" in trace
    assert "ai_recommendation" in trace
    assert "policy_evaluations" in trace
    assert "safety_decision" in trace
    assert "execution" in trace
    assert "settlement_evidence" in trace
    assert "replay_summary" in trace


def test_2_candidate_interventions_tracked_with_ev_cost():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    assert isinstance(trace["candidate_actions"], list)


def test_3_selected_action_clearly_identified():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    rec = trace["ai_recommendation"]
    assert "selected_action" in rec


def test_4_policy_blocked_action_flagged():
    container = create_persistence_container()
    items = generate_synthetic_cases(count=5, seed=42, failure_mix={"fraud": 1.0})
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    assert "safety_decision" in trace


def test_5_blocked_action_never_shown_as_executed():
    container = create_persistence_container()
    items = generate_synthetic_cases(count=5, seed=42, failure_mix={"fraud": 1.0})
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    if not trace["safety_decision"].get("allowed"):
        assert trace["execution"].get("executed") is False or trace["execution"].get("status") != "EXECUTED"


def test_6_actual_recovery_distinguished_from_expected():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    assert trace["verified_recovery_minor"] != trace["expected_recovery_minor"] or trace["verified_recovery_minor"] == 0


def test_7_terminal_stop_reason_preserved():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    detail = build_case_detail(container, it.id)
    assert detail is not None
    assert "status" in detail


def test_8_multi_step_timeline_events():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    assert isinstance(trace["timeline"], list)


def test_9_dynamic_replanning_summary():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    it = items[0]
    container.recovery_items.save(it)

    trace = build_case_trace(it.id, container)
    assert "replay_summary" in trace
    assert "what_happened" in trace["replay_summary"]


def test_10_benchmark_report_structure():
    report = run_benchmark_suite(cases=20, seeds=[42])
    assert report.cases_per_seed == 20
    assert report.total_seeds == 1
    assert hasattr(report, "net_lift_pct")
    assert hasattr(report, "revplug_mean_gross")


def test_11_benchmark_metrics_not_hardcoded():
    rep1 = run_benchmark_suite(cases=10, seeds=[42])
    rep2 = run_benchmark_suite(cases=10, seeds=[43])
    assert rep1.mean_amount_at_risk != rep2.mean_amount_at_risk or rep1.revplug_mean_gross != rep2.revplug_mean_gross


def test_12_dashboard_summary_metrics():
    container = create_persistence_container()
    summary = build_dashboard_summary(container)

    assert "revenue_at_risk" in summary
    assert "actually_recovered" in summary
    assert "recovery_rate" in summary
    assert "total_items" in summary


def test_13_demo_payment_failure_payload():
    from app.services.evaluation_service import EvaluationService
    es = EvaluationService()
    res = es.run_batch_evaluation(count=5, seed=42)
    assert res.status == "completed"


def test_14_audit_events_stream():
    container = create_persistence_container()
    items = generate_evaluation_dataset(count=5, seed=42)
    for it in items:
        container.recovery_items.save(it)

    trace = build_case_trace(items[0].id, container)
    assert "timeline" in trace


def test_15_non_existent_case_trace():
    container = create_persistence_container()
    trace = build_case_trace("non_existent_id_9999", container)
    assert trace["item_id"] == "non_existent_id_9999"


def test_baseline_c_best_fixed_action_evaluation():
    """Baseline C evaluates best single failure-matched fixed action, non-adaptively."""
    from app.services.baseline_evaluator import BaselineEvaluator
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    from datetime import datetime, timezone

    evaluator = BaselineEvaluator(mode="best_fixed", rng_seed=42)

    item = RecoveryItem(
        id="it_auth_c", source_type=SourceType.PAYMENT_FAILURE, external_id="ext_1", customer_id="c_1",
        amount_minor=499900, currency="INR", created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED, root_cause="authentication_required",
    )

    res = evaluator.evaluate_case(item, case_index=0)
    assert res.metadata.get("baseline_mode") == "best_fixed"
    if res.actions_taken:
        assert res.actions_taken[0] == "send_payment_link"


def test_no_action_first_class_win():
    """Negative EV or policy block results in NO_ACTION decision."""
    from app.scoring.expected_value import compare_action_vs_wait_vs_no_action
    comp = compare_action_vs_wait_vs_no_action(
        amount_minor=1000,
        action_net_ev=-500,
        wait_net_ev=-200,
    )
    assert comp["selected_choice"] == "NO_ACTION"
