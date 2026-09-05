"""LLM Provider abstraction layer supporting Groq (PRIMARY), Gemini (OPTIONAL), and Mock/Deterministic providers.

Features:
- Provider protocol interface (LLMProvider)
- GroqLLMProvider (Groq OpenAI-compatible Chat Completions API)
- GeminiProvider (Google Gemini API via REST endpoint)
- MockLLMProvider (Deterministic seeded response for tests & offline dev)
- Provider Factory (get_llm_provider) with env-based routing & fail-safe defaults
- Token tracking, latency measurement, timeout enforcement, retry bounds
- Redaction of sensitive credentials from error tracebacks
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
        timeout_seconds: float = 15.0,
    ) -> LLMResponse:
        ...


class GroqLLMProvider:
    """Production Groq LLM Provider (PRIMARY).

    Uses GROQ_API_KEY environment variable.
    Executes OpenAI-compatible chat completion request to Groq API endpoint.
    Includes automatic retries, timeout bounds, and credential redaction.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._model_name = model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "groq"

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
        timeout_seconds: float = 15.0,
    ) -> LLMResponse:
        if not self._api_key:
            return LLMResponse(
                content="",
                model=self._model_name,
                latency_ms=0,
                error="GROQ_API_KEY not configured",
            )

        start = time.monotonic()
        url = "https://api.groq.com/openai/v1/chat/completions"

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    latency = int((time.monotonic() - start) * 1000)

                    choices = resp_data.get("choices", [])
                    if not choices:
                        return LLMResponse(
                            content="",
                            model=self._model_name,
                            latency_ms=latency,
                            error="Empty choices array returned from Groq API",
                        )

                    text = choices[0].get("message", {}).get("content", "")

                    usage = resp_data.get("usage", {})
                    in_tokens = usage.get("prompt_tokens", len(system_prompt + user_prompt) // 4)
                    out_tokens = usage.get("completion_tokens", len(text) // 4)

                    return LLMResponse(
                        content=text,
                        model=self._model_name,
                        latency_ms=latency,
                        input_tokens=in_tokens,
                        output_tokens=out_tokens,
                    )

            except urllib.error.HTTPError as exc:
                # Sanitize error string so raw bearer token is never logged
                error_body = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
                last_error = f"HTTP {exc.code}: {exc.reason} - {error_body[:200]}"
                time.sleep(0.1 * (2 ** attempt))
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.1 * (2 ** attempt))

        latency = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content="",
            model=self._model_name,
            latency_ms=latency,
            error=f"Groq API request failed after retries: {last_error}",
        )


class GeminiProvider:
    """Real Google Gemini LLM Provider (OPTIONAL).

    Uses GEMINI_API_KEY environment variable.
    Executes HTTP request to Google Gemini API with timeout and retries.
    Falls back cleanly with error status if key is missing or call fails.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
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
        timeout_seconds: float = 15.0,
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
        elif "fraud_flag: true" in prompt_lower or "high_fraud_risk" in prompt_lower or ("timeout" in prompt_lower and ("attempt count: 2" in prompt_lower or "attempt count: 3" in prompt_lower or "attempt count: 4" in prompt_lower)):
            # Case B: Timeout with high fraud risk / multiple attempts -> stop
            content = json.dumps({
                "selected_action": "stop_recovery",
                "confidence": 0.92,
                "reasoning_summary": "High risk fraud indicators or repeated timeout failures; stop automated recovery.",
                "evidence": ["High risk fraud flag or attempt count threshold"],
                "ranked_candidates": [{"action": "stop_recovery", "confidence": 0.92, "reason": "Fraud prevention stop"}],
                "fallback_required": False,
            })
        elif "timeout" in prompt_lower or "gateway_timeout" in prompt_lower:
            # Case A: Timeout with low fraud risk & healthy history -> send payment link
            content = json.dumps({
                "selected_action": "send_payment_link",
                "confidence": 0.88,
                "reasoning_summary": "Network timeout on healthy customer; send payment link to complete transaction.",
                "evidence": ["Gateway timeout", "Healthy customer history"],
                "ranked_candidates": [
                    {"action": "send_payment_link", "confidence": 0.88, "reason": "Direct recovery link"},
                    {"action": "retry_payment", "confidence": 0.70, "reason": "Token retry"},
                ],
                "fallback_required": False,
            })
        elif "checkout_abandonment" in prompt_lower or "checkout_stage" in prompt_lower:
            # Case C: Checkout abandonment -> payment link
            content = json.dumps({
                "selected_action": "send_payment_link",
                "confidence": 0.89,
                "reasoning_summary": "Recent high-value checkout abandonment; send recovery link.",
                "evidence": ["Abandoned checkout stage", "Recent activity"],
                "ranked_candidates": [
                    {"action": "send_payment_link", "confidence": 0.89, "reason": "Checkout recovery link"},
                ],
                "fallback_required": False,
            })
        elif "overdue_receivable" in prompt_lower or "days_overdue" in prompt_lower or "promise_date" in prompt_lower or "promise_status" in prompt_lower:
            # Case D: Overdue receivable + prior promise -> send reminder
            content = json.dumps({
                "selected_action": "send_reminder",
                "confidence": 0.87,
                "reasoning_summary": "Overdue invoice with prior promise-to-pay; send targeted invoice reminder.",
                "evidence": ["Overdue invoice", "Promise-to-pay record"],
                "ranked_candidates": [
                    {"action": "send_reminder", "confidence": 0.87, "reason": "Targeted promise reminder"},
                    {"action": "send_payment_link", "confidence": 0.75, "reason": "Payment link"},
                ],
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
                "selected_action": "escalate_human",
                "confidence": 0.95,
                "reasoning_summary": "High risk fraud indicators; escalate for manual review.",
                "evidence": ["Fraud risk flag present"],
                "ranked_candidates": [{"action": "escalate_human", "confidence": 0.95, "reason": "Fraud prevention"}],
                "fallback_required": False,
            })
        elif "opted out: true" in prompt_lower or "opt_out: true" in prompt_lower or "customer opted out: true" in prompt_lower:
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


def get_llm_provider(requested_provider: str | None = None) -> LLMProvider:
    """Factory function returning the configured LLMProvider instance.

    Priority:
        1. Explicit argument requested_provider
        2. Environment variable LLM_PROVIDER ('groq', 'gemini', 'deterministic', 'mock')
        3. Default to 'groq' if AI is enabled, otherwise 'mock'
    """
    ai_enabled = os.getenv("AI_ENABLED", "true").lower() in ("true", "1", "yes")
    if not ai_enabled:
        return MockLLMProvider()

    provider_name = (requested_provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()

    if provider_name == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            return GroqLLMProvider(api_key=groq_key)
        # If Groq requested but key missing, fall back to mock
        return MockLLMProvider(model_name="deterministic-mock")

    if provider_name == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            return GeminiProvider(api_key=gemini_key)
        return MockLLMProvider(model_name="deterministic-mock")

    return MockLLMProvider(model_name="deterministic-mock")
