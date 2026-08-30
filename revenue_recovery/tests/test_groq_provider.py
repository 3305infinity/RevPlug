"""Tests for Stage 10 — Groq Primary AI Provider Architecture & Fallbacks."""

import json
import os
from unittest.mock import MagicMock, patch
import pytest

from app.agents.llm_provider import GroqLLMProvider, GeminiProvider, MockLLMProvider, get_llm_provider
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction


def test_groq_provider_initialization():
    provider = GroqLLMProvider(api_key="mock_groq_key", model_name="llama-3.3-70b-versatile")
    assert provider.provider_name == "groq"
    assert provider.model_name == "llama-3.3-70b-versatile"


def test_groq_provider_missing_key():
    provider = GroqLLMProvider(api_key="")
    response = provider.generate("system prompt", "user prompt")
    assert not response.success
    assert "GROQ_API_KEY not configured" in response.error


@patch("urllib.request.urlopen")
def test_groq_provider_valid_response(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [{
            "message": {
                "content": json.dumps({
                    "selected_action": "send_payment_link",
                    "confidence": 0.92,
                    "reasoning_summary": "Soft decline timeout; send payment link to customer.",
                    "ranked_candidates": [{"action": "send_payment_link", "confidence": 0.92}],
                })
            }
        }],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45}
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    provider = GroqLLMProvider(api_key="mock_key")
    response = provider.generate("System", "User")

    assert response.success
    assert response.input_tokens == 120
    assert response.output_tokens == 45
    assert "send_payment_link" in response.content


@patch("urllib.request.urlopen")
def test_groq_provider_http_error_sanitization(mock_urlopen):
    import urllib.error
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.groq.com/openai/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None,
    )

    provider = GroqLLMProvider(api_key="secret_groq_key_12345")
    response = provider.generate("System", "User")

    assert not response.success
    assert "secret_groq_key_12345" not in response.error
    assert "HTTP 401" in response.error


def test_get_llm_provider_environment_routing():
    with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "test_key"}):
        p = get_llm_provider()
        assert p.provider_name == "groq"

    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test_key"}):
        p = get_llm_provider()
        assert p.provider_name == "gemini"

    with patch.dict(os.environ, {"LLM_PROVIDER": "deterministic"}):
        p = get_llm_provider()
        assert p.provider_name == "mock"

    with patch.dict(os.environ, {"AI_ENABLED": "false"}):
        p = get_llm_provider()
        assert p.provider_name == "mock"


def test_deterministic_bypass_opt_out():
    agent = RealRecoveryDecisionAgent(llm_client=MockLLMProvider())
    context = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        customer_opt_out=True,  # Opted out -> must bypass LLM completely
        attempt_count=1,
    )
    proposal = agent.propose(context)
    assert proposal.action == RecoveryAction.STOP_RECOVERY
    assert agent.last_trace is not None
    assert agent.last_trace.decision_path == "deterministic"


def test_deterministic_bypass_fraud():
    agent = RealRecoveryDecisionAgent(llm_client=MockLLMProvider())
    context = RecoveryContext(
        failure_category=FailureCategory.FRAUD,
        customer_opt_out=True,  # Opted out -> must bypass LLM
        attempt_count=1,
    )
    proposal = agent.propose(context)
    assert proposal.action == RecoveryAction.STOP_RECOVERY
    assert agent.last_trace.decision_path == "deterministic"


@patch("urllib.request.urlopen")
def test_real_agent_groq_structured_proposal(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [{
            "message": {
                "content": json.dumps({
                    "selected_action": "send_payment_link",
                    "confidence": 0.89,
                    "reasoning_summary": "3DS timeout; send hosted payment link.",
                    "ranked_candidates": [{"action": "send_payment_link", "confidence": 0.89}],
                })
            }
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 40}
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    provider = GroqLLMProvider(api_key="mock_key")
    agent = RealRecoveryDecisionAgent(llm_client=provider)

    context = RecoveryContext(
        failure_category=FailureCategory.UNKNOWN,  # Ambiguous failure -> calls Groq
        failure_reason="Authentication challenge timed out",
        attempt_count=1,
    )

    proposal = agent.propose(context)
    assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
    assert proposal.confidence == 0.89
    assert agent.last_trace.decision_path == "groq"
    assert agent.last_trace.validation_passed is True


@pytest.mark.live_ai
def test_live_groq_api_call():
    """Optional integration test executing a live call if GROQ_API_KEY is available."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY environment variable not set")

    provider = GroqLLMProvider(api_key=api_key)
    response = provider.generate(
        system_prompt="You are a recovery decision AI. Return JSON with selected_action and confidence.",
        user_prompt="Ambiguous payment failure authorization timeout. Amount INR 5000.",
    )
    assert response.success
    assert len(response.content) > 0
