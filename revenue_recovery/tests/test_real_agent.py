from __future__ import annotations

import pytest

from app.agents.evaluation import evaluate_agent, get_golden_scenarios
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.agents.llm_client import DeterministicLLMClient, LLMResponse
from app.agents.prompt_builder import RecoveryPromptBuilder
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction


# ---------------------------------------------------------------------------
# Deterministic LLM Client
# ---------------------------------------------------------------------------

class TestDeterministicLLMClient:
    def test_fraud_returns_escalate(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "fraud risk detected")
        assert resp.success
        import json
        data = json.loads(resp.content)
        assert data["action"] == "escalate_human"
        assert data["risk_level"] == "critical"

    def test_hard_returns_escalate(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "hard card decline")
        import json
        data = json.loads(resp.content)
        assert data["action"] == "escalate_human"

    def test_soft_returns_retry(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "soft temporary failure")
        import json
        data = json.loads(resp.content)
        assert data["action"] == "retry_payment"
        assert data["confidence"] == 0.82

    def test_auth_returns_message(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "authentication required")
        import json
        data = json.loads(resp.content)
        assert data["action"] == "send_customer_message"

    def test_unknown_returns_escalate(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "unknown failure")
        import json
        data = json.loads(resp.content)
        assert data["action"] == "escalate_human"

    def test_latency_recorded(self):
        client = DeterministicLLMClient()
        resp = client.generate("system", "soft failure")
        assert resp.latency_ms >= 0


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_system_prompt_contains_constraints(self):
        builder = RecoveryPromptBuilder()
        assert "fraud" in builder.SYSTEM_PROMPT.lower()
        assert "retry_payment" in builder.SYSTEM_PROMPT
        assert "JSON" in builder.SYSTEM_PROMPT
        assert "escalate_human" in builder.SYSTEM_PROMPT

    def test_user_prompt_compact(self):
        builder = RecoveryPromptBuilder()
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            item_id="pay_001",
        )
        prompt = builder.build_user_prompt(ctx)
        assert "soft" in prompt
        assert "50000" in prompt
        assert "INR" in prompt
        # Should NOT contain secrets or unnecessary data
        assert "secret" not in prompt.lower()
        assert "api_key" not in prompt.lower()

    def test_user_prompt_includes_previous_actions(self):
        builder = RecoveryPromptBuilder()
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=1,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            previous_actions=["retry_payment"],
            item_id="pay_001",
        )
        prompt = builder.build_user_prompt(ctx)
        assert "retry_payment" in prompt

    def test_user_prompt_excludes_sensitive_fields(self):
        builder = RecoveryPromptBuilder()
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            item_id="pay_001",
        )
        prompt = builder.build_user_prompt(ctx)
        # Should not contain webhook secrets or credentials
        assert "whsec" not in prompt
        assert "api_key" not in prompt
        assert "password" not in prompt


# ---------------------------------------------------------------------------
# Real Recovery Decision Agent
# ---------------------------------------------------------------------------

class TestRealAgent:
    def test_soft_failure_proposes_retry(self):
        agent = RealRecoveryDecisionAgent()
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            item_id="pay_001",
        )
        proposal = agent.propose(ctx)
        assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
        assert proposal.confidence > 0.5
        assert agent.last_trace is not None
        assert agent.last_trace.validation_passed is True

    def test_fraud_stops_recovery(self):
        agent = RealRecoveryDecisionAgent()
        ctx = RecoveryContext(
            failure_category=FailureCategory.FRAUD,
            retryable=False,
            attempt_count=0,
            amount_minor=100000,
            currency="INR",
            expected_recovery_value=0,
            customer_opt_out=False,
            item_id="pay_fraud_001",
        )
        proposal = agent.propose(ctx)
        assert proposal.action == RecoveryAction.STOP_RECOVERY

    def test_hard_failure_does_not_retry(self):
        agent = RealRecoveryDecisionAgent()
        ctx = RecoveryContext(
            failure_category=FailureCategory.HARD,
            retryable=False,
            attempt_count=0,
            amount_minor=75000,
            currency="INR",
            expected_recovery_value=3750,
            customer_opt_out=False,
            item_id="pay_hard_001",
        )
        proposal = agent.propose(ctx)
        assert proposal.action != RecoveryAction.RETRY_PAYMENT

    def test_agent_name_and_model(self):
        agent = RealRecoveryDecisionAgent()
        assert agent.name == "real-agent"
        assert agent.model_name == "deterministic-mock"

    def test_trace_recorded(self):
        agent = RealRecoveryDecisionAgent()
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            item_id="pay_trace_001",
        )
        agent.propose(ctx)
        trace = agent.last_trace
        assert trace is not None
        assert trace.recovery_item_id == "pay_trace_001"
        assert trace.validation_passed is True
        assert trace.fallback_used is False
        assert trace.latency_ms >= 0


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------

class TestFallback:
    def test_llm_error_falls_back_to_mock(self):
        """If LLM fails, agent falls back to deterministic mock."""

        class FailingLLM:
            model_name = "failing"
            def generate(self, system, user, **kwargs):
                return LLMResponse(content="", model="failing", latency_ms=0, error="API timeout")

        from app.agents.decision_agent import MockRecoveryDecisionAgent
        fallback = MockRecoveryDecisionAgent()
        agent = RealRecoveryDecisionAgent(llm_client=FailingLLM(), fallback_agent=fallback)
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            item_id="pay_001",
        )
        proposal = agent.propose(ctx)
        # Fallback mock agent proposes send_payment_link for SOFT (higher EV than retry)
        assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
        assert agent.last_trace.fallback_used is True

    def test_malformed_json_falls_back(self):
        """If LLM returns garbage, agent falls back to deterministic rules."""

        class GarbageLLM:
            model_name = "garbage"
            def generate(self, system, user, **kwargs):
                return LLMResponse(content="not json at all", model="garbage", latency_ms=0)

        from app.agents.decision_agent import MockRecoveryDecisionAgent
        fallback = MockRecoveryDecisionAgent()
        agent = RealRecoveryDecisionAgent(llm_client=GarbageLLM(), fallback_agent=fallback)
        ctx = RecoveryContext(
            failure_category=FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=100000,
            currency="INR",
            expected_recovery_value=50000,
            customer_opt_out=False,
            item_id="pay_soft_001",
        )
        proposal = agent.propose(ctx)
        # Fallback mock agent proposes SEND_PAYMENT_LINK for SOFT (higher EV than retry)
        assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
        assert agent.last_trace.fallback_used is True


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class TestEvaluation:
    def test_golden_scenarios_exist(self):
        scenarios = get_golden_scenarios()
        assert len(scenarios) >= 10

    def test_mock_agent_passes_evaluation(self):
        from app.agents.decision_agent import MockRecoveryDecisionAgent
        agent = MockRecoveryDecisionAgent()
        report = evaluate_agent(agent)
        assert report.total >= 10
        # Mock agent should pass most scenarios
        assert report.pass_rate >= 0.7

    def test_real_agent_passes_evaluation(self):
        agent = RealRecoveryDecisionAgent()
        report = evaluate_agent(agent)
        assert report.total >= 10
        # Real agent (with deterministic mock LLM) should pass most
        assert report.pass_rate >= 0.7

    def test_evaluation_report_summary(self):
        from app.agents.decision_agent import MockRecoveryDecisionAgent
        agent = MockRecoveryDecisionAgent()
        report = evaluate_agent(agent)
        summary = report.summary()
        assert "Evaluation Report" in summary
        assert f"Total: {report.total}" in summary
