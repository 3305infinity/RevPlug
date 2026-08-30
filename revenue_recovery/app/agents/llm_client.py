from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached: bool = False
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class LLMClient(Protocol):
    """Provider-agnostic LLM client interface."""

    @property
    def model_name(self) -> str:
        ...

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 500, temperature: float = 0.1) -> LLMResponse:
        ...


class DeterministicLLMClient:
    """Deterministic mock LLM client for testing without API keys.

    Returns structured responses based on context keywords.
    This is NOT a real LLM — it's a deterministic fallback that
    produces valid structured output for known scenarios.
    """

    def __init__(self, *, model_name: str = "deterministic-mock") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 500, temperature: float = 0.1) -> LLMResponse:
        start = time.monotonic()
        content = self._deterministic_response(user_prompt)
        latency = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=content,
            model=self._model_name,
            latency_ms=latency,
            input_tokens=len(system_prompt + user_prompt) // 4,
            output_tokens=len(content) // 4,
        )

    def _deterministic_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "opted out: true" in prompt_lower:
            return json.dumps({
                "action": "stop_recovery",
                "confidence": 0.95,
                "reasoning": "Customer has opted out of automated recovery; must not retry",
                "risk_level": "low",
                "requires_human_approval": False,
            })
        if "3/3" in prompt_lower or "attempt: 3" in prompt_lower or "attempt count: 3" in prompt_lower:
            return json.dumps({
                "action": "send_payment_link",
                "confidence": 0.7,
                "reasoning": "Retry limit reached; offer payment link as alternative",
                "risk_level": "medium",
                "requires_human_approval": False,
            })
        if "fraud" in prompt_lower or "high_risk" in prompt_lower or "fraud_flag" in prompt_lower:
            return json.dumps({
                "action": "escalate_human",
                "confidence": 0.95,
                "reasoning": "Fraud/risk signals detected; must not retry automatically",
                "risk_level": "critical",
                "requires_human_approval": True,
            })
        if "hard" in prompt_lower or "declined" in prompt_lower:
            return json.dumps({
                "action": "escalate_human",
                "confidence": 0.8,
                "reasoning": "Hard failure; customer must update payment method",
                "risk_level": "medium",
                "requires_human_approval": False,
            })
        if "authentication" in prompt_lower:
            return json.dumps({
                "action": "send_customer_message",
                "confidence": 0.75,
                "reasoning": "Customer must re-authenticate; send recovery message with payment link",
                "risk_level": "low",
                "requires_human_approval": False,
            })
        if "unknown" in prompt_lower:
            return json.dumps({
                "action": "escalate_human",
                "confidence": 0.6,
                "reasoning": "Unknown failure type; escalate for manual review",
                "risk_level": "medium",
                "requires_human_approval": True,
            })
        # Default: soft failure → retry
        return json.dumps({
            "action": "retry_payment",
            "confidence": 0.82,
            "reasoning": "Temporary/soft failure; retry is appropriate and low risk",
            "risk_level": "low",
            "requires_human_approval": False,
        })
