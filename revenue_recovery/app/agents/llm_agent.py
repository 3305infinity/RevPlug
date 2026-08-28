from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.decision_agent import RecoveryDecisionAgent
from app.agents.llm_client import DeterministicLLMClient, LLMClient, LLMResponse
from app.agents.prompt_builder import RecoveryPromptBuilder
from app.domain.context import RecoveryContext
from app.domain.proposals import RecoveryAction, RecoveryProposal


@dataclass(frozen=True, slots=True)
class AgentTrace:
    """Structured trace of an agent decision for auditability."""

    recovery_item_id: str
    agent_name: str
    model_name: str
    prompt_version: str = "v1"
    context_summary: dict[str, Any] = field(default_factory=dict)
    raw_response: str | None = None
    parsed_proposal: dict[str, Any] | None = None
    validation_passed: bool = False
    validation_error: str | None = None
    fallback_used: bool = False
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RealRecoveryDecisionAgent:
    """Real LLM-backed recovery decision agent with multi-stage workflow.

    Stages:
        1. CONTEXT_BUILD  — construct compact RecoveryContext
        2. DECISION       — call LLM for structured proposal
        3. VALIDATION     — parse + schema-validate output
        4. FALLBACK       — on any failure, fall back to deterministic mock

    The agent NEVER executes actions. It only produces proposals.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        prompt_builder: RecoveryPromptBuilder | None = None,
        fallback_agent: RecoveryDecisionAgent | None = None,
        name: str = "real-agent",
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> None:
        self._llm = llm_client or DeterministicLLMClient()
        self._prompt_builder = prompt_builder or RecoveryPromptBuilder()
        self._fallback = fallback_agent
        self._name = name
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._last_trace: AgentTrace | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._llm.model_name

    @property
    def last_trace(self) -> AgentTrace | None:
        return self._last_trace

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        """Run the full multi-stage agent workflow."""
        start = time.monotonic()

        # Stage 1: CONTEXT_BUILD — already done by caller (RecoveryContext)
        context_summary = {
            "category": context.failure_category.value,
            "retryable": context.retryable,
            "attempt": context.attempt_count,
            "amount": context.amount_minor,
        }

        # Stage 2: DECISION — call LLM
        system_prompt = self._prompt_builder.SYSTEM_PROMPT
        user_prompt = self._prompt_builder.build_user_prompt(context)

        try:
            response = self._llm.generate(
                system_prompt, user_prompt,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            latency = int((time.monotonic() - start) * 1000)

            if not response.success:
                return self._fallback_with_trace(
                    context, context_summary, None, None,
                    f"LLM error: {response.error}", latency,
                )

            # Stage 3: VALIDATION — parse JSON
            parsed = self._extract_json(response.content)
            if parsed is None:
                return self._fallback_with_trace(
                    context, context_summary, response.content, None,
                    "Failed to parse JSON from LLM output", latency,
                )

            # Validate action is in allowed set
            if parsed.get("action") not in [a.value for a in RecoveryAction]:
                return self._fallback_with_trace(
                    context, context_summary, response.content, parsed,
                    f"Invalid action: {parsed.get('action')}", latency,
                )

            # Build proposal
            proposal = RecoveryProposal(
                action=RecoveryAction(parsed["action"]),
                reason=parsed.get("reasoning", "No reasoning provided"),
                confidence=float(parsed.get("confidence", 0.5)),
                model_name=self.model_name,
                evidence={
                    "risk_level": parsed.get("risk_level", "unknown"),
                    "requires_human_approval": parsed.get("requires_human_approval", False),
                    "raw_response": response.content[:500],
                },
            )

            self._last_trace = AgentTrace(
                recovery_item_id=context.item_id,
                agent_name=self._name,
                model_name=self.model_name,
                context_summary=context_summary,
                raw_response=response.content[:1000],
                parsed_proposal=parsed,
                validation_passed=True,
                latency_ms=latency,
            )

            return proposal

        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            return self._fallback_with_trace(
                context, context_summary, None, None,
                str(exc), latency,
            )

    def _fallback_with_trace(
        self,
        context: RecoveryContext,
        context_summary: dict,
        raw_response: str | None,
        parsed: dict | None,
        error: str,
        latency: int,
    ) -> RecoveryProposal:
        """Fall back to deterministic agent and record the trace."""
        fallback = self._fallback
        if fallback is not None:
            proposal = fallback.propose(context)
        else:
            # Ultimate fallback: escalate
            from app.agents.decision_agent import MockRecoveryDecisionAgent
            proposal = MockRecoveryDecisionAgent().propose(context)

        self._last_trace = AgentTrace(
            recovery_item_id=context.item_id,
            agent_name=self._name,
            model_name=self.model_name,
            context_summary=context_summary,
            raw_response=raw_response,
            parsed_proposal=parsed,
            validation_passed=False,
            validation_error=error,
            fallback_used=True,
            latency_ms=latency,
        )
        return proposal

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON from LLM output with robust fallback."""
        text = text.strip()
        # Try markdown code block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Try raw JSON
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None
