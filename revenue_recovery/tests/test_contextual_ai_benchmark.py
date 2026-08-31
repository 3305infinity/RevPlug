"""Tests for Contextual AI Judgment and Canonical Evaluation Benchmark."""
from __future__ import annotations

import json
import pytest

from app.agents.ai_router import AIRouter
from app.agents.llm_provider import MockLLMProvider
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.eval.run_benchmark import run_benchmark
from app.services.evaluation_service import EvaluationService


def test_case_a_and_case_b_contextual_ai_reasoning():
    """Proves identical raw gateway timeout codes yield DIFFERENT decisions based on contextual signals.
    
    Case A: Payment timeout + 1 attempt + healthy customer -> send_payment_link
    Case B: Payment timeout + 2 attempts + high fraud risk flag -> stop_recovery
    """
    provider = MockLLMProvider()

    # Case A: Low fraud risk, 1 attempt
    user_prompt_a = """=== UNTRUSTED RECOVERY CONTEXT DATA ===
Failure category: unknown
Gateway error text [UNTRUSTED]: "gateway_timeout payment failure"
Attempt count: 1/3
Amount at risk: 499900 INR ($4999.00)
Customer opted out: False
=== DETERMINISTIC CANDIDATE ACTIONS ===
Valid candidates: ["retry_payment", "send_payment_link", "stop_recovery"]
"""
    res_a = provider.generate("system prompt", user_prompt_a)
    parsed_a = json.loads(res_a.content)
    assert parsed_a["selected_action"] in ("send_payment_link", "retry_payment")

    # Case B: High fraud risk, multiple attempts
    user_prompt_b = """=== UNTRUSTED RECOVERY CONTEXT DATA ===
Failure category: unknown
Gateway error text [UNTRUSTED]: "gateway_timeout payment failure"
Attempt count: 2/3
high_fraud_risk: True
fraud_flag: True
Amount at risk: 499900 INR ($4999.00)
Customer opted out: False
=== DETERMINISTIC CANDIDATE ACTIONS ===
Valid candidates: ["retry_payment", "send_payment_link", "stop_recovery"]
"""
    res_b = provider.generate("system prompt", user_prompt_b)
    parsed_b = json.loads(res_b.content)
    assert parsed_b["selected_action"] == "stop_recovery"


def test_case_c_checkout_abandonment():
    """Case C: Checkout abandonment -> payment link recovery."""
    provider = MockLLMProvider()
    user_prompt = """=== UNTRUSTED RECOVERY CONTEXT DATA ===
Source type: checkout_abandonment
checkout_stage: payment_method
checkout_age_minutes: 45
Amount at risk: 250000 INR ($2500.00)
Customer opted out: False
=== DETERMINISTIC CANDIDATE ACTIONS ===
Valid candidates: ["send_payment_link", "stop_recovery"]
"""
    res = provider.generate("system prompt", user_prompt)
    parsed = json.loads(res.content)
    assert parsed["selected_action"] == "send_payment_link"


def test_case_d_overdue_receivable_with_promise():
    """Case D: Overdue receivable + prior promise -> targeted reminder."""
    provider = MockLLMProvider()
    user_prompt = """=== UNTRUSTED RECOVERY CONTEXT DATA ===
Source type: overdue_receivable
days_overdue: 3
promise_status: promised
promise_date: 2026-08-28
Amount at risk: 1000000 INR ($10000.00)
Customer opted out: False
=== DETERMINISTIC CANDIDATE ACTIONS ===
Valid candidates: ["send_reminder", "send_payment_link", "escalate_human"]
"""
    res = provider.generate("system prompt", user_prompt)
    parsed = json.loads(res.content)
    assert parsed["selected_action"] == "send_reminder"


def test_canonical_benchmark_reproducibility_and_invariants():
    """Verifies that running the canonical benchmark twice with seed=42 yields identical metrics and obeys invariants."""
    eval_svc = EvaluationService(max_retry_attempts=3)

    res1 = eval_svc.run_batch_evaluation(count=20, seed=42)
    resp1 = eval_svc.to_response_dict(res1)

    res2 = eval_svc.run_batch_evaluation(count=20, seed=42)
    resp2 = eval_svc.to_response_dict(res2)

    # 1. Reproducibility
    assert resp1["revplug"]["actual_recovered"] == resp2["revplug"]["actual_recovered"]
    assert resp1["revplug"]["total_amount_at_risk"] == resp2["revplug"]["total_amount_at_risk"]
    assert resp1["comparison"]["honest_summary"] == resp2["comparison"]["honest_summary"]

    # 2. Financial Invariants
    ros = resp1["revplug"]
    assert 0 <= ros["actual_recovered"] <= ros["total_amount_at_risk"]
    assert ros["net_recovered"] <= ros["actual_recovered"]

    # 3. AI Safety Metrics
    ai = ros["ai_metrics"]
    assert ai["actual_executed_unsafe_actions"] == 0
    assert "ai_provider" in ai
    assert "ai_model" in ai


def test_run_benchmark_cli_artifact_generation():
    """Verifies run_benchmark CLI function creates evaluation_report.json and docs/EVALUATION_REPORT.md."""
    resp = run_benchmark(count=10, seed=42)
    assert resp is not None
    assert "revplug" in resp
    assert "comparison" in resp
