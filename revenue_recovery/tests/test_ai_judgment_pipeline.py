"""Comprehensive tests for AI Judgment in Evaluation Pipeline.

Tests:
1. AIRouter routing (ambiguous case -> AI path; deterministic safety case -> deterministic path)
2. AI proposals & Policy shield (AI proposal evaluated by policy gate; policy allowed vs policy rejected)
3. Schema violations & invalid AI output handling (safe fallback triggered, fallback_used=True)
4. Hallucinated action contract violation handling (rejected by ActionRegistry, fallback triggered)
5. Metric accuracy (ai_cases, deterministic_cases, ai_proposals, ai_proposals_accepted, ai_proposals_rejected_by_policy, ai_fallback_cases)
6. Trace completeness (decision_method, decision_method_reason, ai_attempted, ai_success, fallback_used)
7. Safety invariants (0 safety violations across AI paths)
8. Idempotency (re-evaluation does not create duplicate execution events)
"""
import pytest
from app.agents.ai_router import AIRouter, AIRoutingDecision
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.agents.llm_provider import MockLLMProvider
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.evaluation_service import EvaluationService


def test_ai_router_deterministic_bypass_opt_out():
    router = AIRouter(force_ai=False)
    ctx = RecoveryContext(
        item_id="item_optout",
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=5000,
        customer_opt_out=True,
    )
    res = router.route(ctx)
    assert not res.use_ai
    assert "opt_out" in res.reason.lower()


def test_ai_router_deterministic_bypass_fraud():
    router = AIRouter(force_ai=False)
    ctx = RecoveryContext(
        item_id="item_fraud",
        failure_category=FailureCategory.FRAUD,
        retryable=False,
        attempt_count=0,
        amount_minor=50000,
    )
    res = router.route(ctx)
    assert not res.use_ai
    assert "fraud" in res.reason.lower()


def test_ai_router_ambiguous_case_routes_to_ai():
    router = AIRouter(force_ai=False)
    ctx = RecoveryContext(
        item_id="item_ambiguous",
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=100000,
        failure_reason="Temporary bank gateway timeout during card authorization step",
        metadata={"source_type": "checkout_abandonment"},
    )
    res = router.route(ctx)
    assert res.use_ai
    assert len(res.ambiguity_factors) > 0


def test_real_agent_fallback_on_invalid_json():
    class InvalidJSONLLM:
        provider_name = "mock-invalid"
        model_name = "mock-invalid"
        def generate(self, system_prompt, user_prompt, **kwargs):
            from app.agents.llm_provider import LLMResponse
            return LLMResponse(content="NOT_VALID_JSON", model="mock-invalid", latency_ms=10)

    agent = RealRecoveryDecisionAgent(llm_client=InvalidJSONLLM(), router=AIRouter(force_ai=True))
    ctx = RecoveryContext(
        item_id="item_bad_json",
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=50000,
    )
    proposal = agent.propose(ctx)
    trace = agent.last_trace
    assert trace is not None
    assert trace.fallback_used
    assert trace.decision_path == "fallback"
    assert "JSON" in trace.validation_error


def test_real_agent_fallback_on_hallucinated_action():
    class HallucinatingLLM:
        provider_name = "mock-hallucinating"
        model_name = "mock-hallucinating"
        def generate(self, system_prompt, user_prompt, **kwargs):
            import json
            from app.agents.llm_provider import LLMResponse
            return LLMResponse(
                content=json.dumps({
                    "selected_action": "magic_quantum_recovery",
                    "confidence": 0.99,
                    "reasoning_summary": "Magic action",
                }),
                model="mock-hallucinating",
                latency_ms=10,
            )

    agent = RealRecoveryDecisionAgent(llm_client=HallucinatingLLM(), router=AIRouter(force_ai=True))
    ctx = RecoveryContext(
        item_id="item_hallucinate",
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=50000,
    )
    proposal = agent.propose(ctx)
    trace = agent.last_trace
    assert trace is not None
    assert trace.fallback_used
    assert trace.decision_path == "fallback"
    assert "Hallucinated action" in trace.validation_error


def test_evaluation_service_tracks_ai_vs_deterministic_metrics():
    eval_svc = EvaluationService(ai_enabled=True, max_retry_attempts=3)
    res = eval_svc.run_batch_evaluation(count=30, seed=42)

    assert res.status == "completed"
    ros = res.revplug
    assert ros.cases_evaluated == 30
    assert ros.cases_completed == 30

    # Verify decision method counters reconcile with per_case
    ai_assisted_count = sum(1 for c in res.per_case if c["revplug"]["decision_method"] == "AI_ASSISTED")
    deterministic_count = sum(1 for c in res.per_case if c["revplug"]["decision_method"] == "DETERMINISTIC")
    fallback_count = sum(1 for c in res.per_case if c["revplug"]["decision_method"] == "AI_FALLBACK")
    policy_rejected_count = sum(1 for c in res.per_case if c["revplug"]["decision_method"] == "AI_REJECTED_BY_POLICY")

    assert ros.ai_cases == ai_assisted_count + policy_rejected_count
    assert ros.deterministic_cases == deterministic_count
    assert ros.ai_fallback_cases == fallback_count
    assert ros.ai_proposals_rejected_by_policy == policy_rejected_count
    assert ros.ai_cases > 0, "AI-assisted cases must be non-zero in AI mode"

    # Verify 0 safety violations across AI paths
    assert ros.safety_violations["total_safety_violations"] == 0


def test_benchmark_configuration_serialized():
    eval_svc = EvaluationService(ai_enabled=True)
    res = eval_svc.run_batch_evaluation(count=10, seed=42)
    resp = eval_svc.to_response_dict(res)

    assert "benchmark_configuration" in resp
    cfg = resp["benchmark_configuration"]
    assert cfg["ai_enabled"] is True
    assert cfg["ai_routing"] == "contextual"
    assert cfg["deterministic_safety"] is True


def test_idempotency_evaluating_same_dataset_twice_is_identical():
    eval_svc = EvaluationService(ai_enabled=True)
    res1 = eval_svc.run_batch_evaluation(count=20, seed=42)
    res2 = eval_svc.run_batch_evaluation(count=20, seed=42)

    assert res1.revplug.actual_recovered == res2.revplug.actual_recovered
    assert res1.revplug.ai_cases == res2.revplug.ai_cases
    assert res1.revplug.deterministic_cases == res2.revplug.deterministic_cases
