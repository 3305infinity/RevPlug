"""LLM Provider abstraction layer supporting Gemini, OpenAI, and Mock providers.

Features:
- Provider protocol interface (LLMProvider)
- GeminiProvider (Google Gemini API via SDK or HTTP endpoint)
- MockLLMProvider (Deterministic seeded response for tests & offline dev)
- Token tracking, latency measurement, timeout enforcement, retry bounds
- Clean separation from business domain logic
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    model: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class LLMProvider(Protocol):
    """Provider-agnostic interface for LLM model calls."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        timeout_seconds: float = 5.0,
    ) -> LLMResponse:
        ...


class GeminiProvider:
    """Real Google Gemini LLM Provider.

    Uses GEMINI_API_KEY environment variable.
    Executes HTTP request to Google Gemini API with timeout and retries.
    Falls back cleanly with error status if key is missing or call fails.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-1.5-flash",
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        timeout_seconds: float = 5.0,
    ) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                content="",
                model=self._model_name,
                latency_ms=0,
                error="GEMINI_API_KEY not configured",
            )

        start = time.monotonic()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model_name}:generateContent"
            f"?key={self._api_key}"
        )

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    latency = int((time.monotonic() - start) * 1000)

                    # Extract content
                    candidates = resp_data.get("candidates", [])
                    if not candidates:
                        return LLMResponse(
                            content="",
                            model=self._model_name,
                            latency_ms=latency,
                            error="Empty response candidates from Gemini API",
                        )

                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)

                    # Token usage metadata
                    usage = resp_data.get("usageMetadata", {})
                    in_tokens = usage.get("promptTokenCount", len(system_prompt + user_prompt) // 4)
                    out_tokens = usage.get("candidatesTokenCount", len(text) // 4)

                    return LLMResponse(
                        content=text,
                        model=self._model_name,
                        latency_ms=latency,
                        input_tokens=in_tokens,
                        output_tokens=out_tokens,
                    )

            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.1 * (2 ** attempt))

        latency = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content="",
            model=self._model_name,
            latency_ms=latency,
            error=f"Gemini API request failed after retries: {last_error}",
        )


class MockLLMProvider:
    """Deterministic mock provider for offline testing and golden benchmark runs."""

    def __init__(self, model_name: str = "mock-llm-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        timeout_seconds: float = 5.0,
    ) -> LLMResponse:
        start = time.monotonic()
        prompt_lower = user_prompt.lower()

        # Prompt injection detection test
        if "ignore all recovery policies" in prompt_lower or "system prompt" in prompt_lower:
            content = json.dumps({
                "selected_action": "stop_recovery",
                "confidence": 0.95,
                "reasoning_summary": "Malicious prompt injection attempt detected in input metadata; defaulting to stop.",
                "evidence": ["Prompt injection string detected"],
                "ranked_candidates": [{"action": "stop_recovery", "confidence": 0.95, "reason": "Security stop"}],
                "fallback_required": False,
            })
        elif "ambiguous" in prompt_lower or "conflicting" in prompt_lower or "unknown" in prompt_lower:
            content = json.dumps({
                "selected_action": "escalate_human",
                "confidence": 0.45,  # Low confidence triggers fallback / human review
                "reasoning_summary": "Ambiguous signals with low confidence; escalate for manual review.",
                "evidence": ["Low confidence ambiguous failure"],
                "ranked_candidates": [{"action": "escalate_human", "confidence": 0.45, "reason": "Low confidence"}],
                "fallback_required": True,
            })
        elif "fraud" in prompt_lower:
            content = json.dumps({
                "selected_action": "stop_recovery",
                "confidence": 0.95,
                "reasoning_summary": "High risk fraud indicators; stop all recovery attempts.",
                "evidence": ["Fraud risk flag present"],
                "ranked_candidates": [{"action": "stop_recovery", "confidence": 0.95, "reason": "Fraud prevention"}],
                "fallback_required": False,
            })
        elif "opted out" in prompt_lower or "opt_out" in prompt_lower:
            content = json.dumps({
                "selected_action": "stop_recovery",
                "confidence": 0.95,
                "reasoning_summary": "Customer opted out of contact.",
                "evidence": ["Opt out consent flag"],
                "ranked_candidates": [{"action": "stop_recovery", "confidence": 0.95, "reason": "Opt out"}],
                "fallback_required": False,
            })
        elif "hard" in prompt_lower or "decline" in prompt_lower:
            content = json.dumps({
                "selected_action": "send_payment_link",
                "confidence": 0.85,
                "reasoning_summary": "Hard failure requires customer updating payment method via link.",
                "evidence": ["Hard decline response code"],
                "ranked_candidates": [
                    {"action": "send_payment_link", "confidence": 0.85, "reason": "Update payment method"},
                    {"action": "escalate_human", "confidence": 0.60, "reason": "Human escalation"},
                ],
                "fallback_required": False,
            })
        else:
            # Standard soft failure
            content = json.dumps({
                "selected_action": "retry_payment",
                "confidence": 0.88,
                "reasoning_summary": "Temporary issuer soft failure; retry payment token.",
                "evidence": ["Soft decline code", "Low attempt count"],
                "ranked_candidates": [
                    {"action": "retry_payment", "confidence": 0.88, "reason": "Temporary failure retry"},
                    {"action": "send_payment_link", "confidence": 0.65, "reason": "Alternative link"},
                ],
                "fallback_required": False,
            })

        latency = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=content,
            model=self._model_name,
            latency_ms=latency,
            input_tokens=len(system_prompt + user_prompt) // 4,
            output_tokens=len(content) // 4,
        )
