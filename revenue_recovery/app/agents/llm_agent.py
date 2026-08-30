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


from app.agents.ai_router import AIRouter
from app.agents.ai_schemas import AIRecommendation, AISchemaValidationError, RankedCandidate
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.llm_provider import MockLLMProvider, LLMProvider
from app.domain.failures import FailureCategory


class RealRecoveryDecisionAgent:
    """Real LLM-backed recovery decision agent with candidate-ranking and safe fallback.

    Architecture:
        1. ROUTING          — AIRouter checks clear vs ambiguous case
        2. CANDIDATE GEN    — Deterministic generation of valid candidate actions
        3. LLM RANKING      — Call LLM to rank candidate actions
        4. SCHEMA VALIDATION— Structured parsing and range validation (0..1 confidence)
        5. CONFIDENCE POLICY— Low confidence (< threshold) triggers fallback
        6. POLICY GATE      — Hard deterministic safety rules enforce final boundary
    """

    def __init__(
        self,
        *,
        llm_client: Any | None = None,
        prompt_builder: RecoveryPromptBuilder | None = None,
        fallback_agent: RecoveryDecisionAgent | None = None,
        router: AIRouter | None = None,
        confidence_threshold: float = 0.50,
        name: str = "real-agent",
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> None:
        from app.agents.llm_client import DeterministicLLMClient
        self._llm = llm_client or DeterministicLLMClient()
        self._prompt_builder = prompt_builder or RecoveryPromptBuilder()
        self._fallback = fallback_agent
        self._router = router or AIRouter(force_ai=True)
        self._confidence_threshold = confidence_threshold
        self._name = name
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._last_trace: AgentTrace | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return getattr(self._llm, "model_name", "mock-llm")

    @property
    def last_trace(self) -> AgentTrace | None:
        return self._last_trace

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        """Run the full multi-stage agent workflow."""
        start = time.monotonic()

        # Stage 1: AIRouting check
        routing = self._router.route(context)

        context_summary = {
            "category": context.failure_category.value,
            "retryable": context.retryable,
            "attempt": context.attempt_count,
            "amount": context.amount_minor,
            "use_ai": routing.use_ai,
            "routing_reason": routing.reason,
        }

        # If clear case -> skip LLM and use deterministic fallback agent
        if not routing.use_ai:
            fallback = self._fallback or MockRecoveryDecisionAgent()
            proposal = fallback.propose(context)
            self._last_trace = AgentTrace(
                recovery_item_id=context.item_id,
                agent_name=self._name,
                model_name="deterministic-rules",
                context_summary=context_summary,
                validation_passed=True,
                fallback_used=False,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return proposal

        # Stage 2: Candidate Generation (Deterministic)
        candidate_actions = self._generate_candidate_actions(context)

        # Stage 3: LLM Candidate Ranking
        system_prompt = self._prompt_builder.SYSTEM_PROMPT_RANKING_V1
        user_prompt = self._prompt_builder.build_ranking_prompt(context, candidate_actions)

        try:
            response = self._llm.generate(
                system_prompt,
                user_prompt,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            latency = int((time.monotonic() - start) * 1000)

            if not response.success:
                return self._fallback_with_trace(
                    context, context_summary, None, None,
                    f"LLM provider error: {response.error}", latency,
                )

            # Stage 4: Structured Schema Parsing & Validation
            parsed = self._extract_json(response.content)
            if parsed is None:
                return self._fallback_with_trace(
                    context, context_summary, response.content, None,
                    "Failed to parse JSON from LLM response", latency,
                )

            selected_act_str = parsed.get("selected_action") or parsed.get("action")
            conf_val = float(parsed.get("confidence", 0.0))

            if not (0.0 <= conf_val <= 1.0):
                return self._fallback_with_trace(
                    context, context_summary, response.content, parsed,
                    f"Schema violation: confidence {conf_val} outside [0..1]", latency,
                )

            # Reject action if not in allowed candidate set (prevents hallucinated tools)
            if selected_act_str not in [a.value for a in RecoveryAction]:
                return self._fallback_with_trace(
                    context, context_summary, response.content, parsed,
                    f"Hallucinated action rejected: {selected_act_str!r}", latency,
                )

            selected_act = RecoveryAction(selected_act_str)

            # Stage 5: Confidence Policy Check
            if conf_val < self._confidence_threshold or parsed.get("fallback_required"):
                return self._fallback_with_trace(
                    context, context_summary, response.content, parsed,
                    f"Low AI confidence ({conf_val:.2f} < {self._confidence_threshold}) — safe fallback triggered", latency,
                )

            # Proposal construction
            proposal = RecoveryProposal(
                action=selected_act,
                reason=parsed.get("reasoning_summary") or parsed.get("reasoning") or "AI recommended action",
                confidence=conf_val,
                proposed_retry=(selected_act == RecoveryAction.RETRY_PAYMENT),
                model_name=self.model_name,
                evidence={
                    "routing_factors": routing.ambiguity_factors,
                    "ranked_candidates": parsed.get("ranked_candidates", []),
                    "prompt_version": RecoveryPromptBuilder.PROMPT_VERSION,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
                diagnosis={"diagnosis_source": "llm", "confidence": conf_val},
            )

            self._last_trace = AgentTrace(
                recovery_item_id=context.item_id,
                agent_name=self._name,
                model_name=self.model_name,
                prompt_version=RecoveryPromptBuilder.PROMPT_VERSION,
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

    def _generate_candidate_actions(self, context: RecoveryContext) -> list[str]:
        """Deterministically generate valid candidate actions for AI ranking."""
        candidates = [
            "retry_payment",
            "send_payment_link",
            "send_reminder",
            "alternate_channel",
            "send_customer_message",
            "escalate_human",
            "stop_recovery",
        ]
        if context.attempt_count >= context.max_attempts or not context.retryable or context.customer_opt_out:
            candidates = [c for c in candidates if c != "retry_payment"]
        if context.customer_opt_out or context.failure_category == FailureCategory.FRAUD:
            candidates = ["stop_recovery", "escalate_human"]
        return candidates

    def _fallback_with_trace(
        self,
        context: RecoveryContext,
        context_summary: dict,
        raw_response: str | None,
        parsed: dict | None,
        error: str,
        latency: int,
    ) -> RecoveryProposal:
        """Fall back safely to deterministic agent and record trace."""
        fallback = self._fallback or MockRecoveryDecisionAgent()
        proposal = fallback.propose(context)

        self._last_trace = AgentTrace(
            recovery_item_id=context.item_id,
            agent_name=self._name,
            model_name=self.model_name,
            prompt_version=RecoveryPromptBuilder.PROMPT_VERSION,
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
        if not text:
            return None
        text = text.strip()
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None
