"""AIRouter — Determines whether a case requires AI reasoning or deterministic processing.

Principles:
- Clear safety stops (explicit opt-out, fraud risk flag, retry budget exhaustion) skip LLM calls.
- Ambiguous cases (unknown failure codes, free-text errors, conflicting signals, complex multi-channel history, multi-candidate strategy ranking) route to AI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory


@dataclass(frozen=True, slots=True)
class AIRoutingDecision:
    """Result of AIRouter evaluation."""

    use_ai: bool
    reason: str
    ambiguity_factors: list[str]


class AIRouter:
    """Evaluates RecoveryContext to determine if AI intervention is needed."""

    def __init__(self, *, force_ai: bool = False, confidence_threshold: float = 0.80) -> None:
        self._force_ai = force_ai
        self._confidence_threshold = confidence_threshold

    def route(self, context: RecoveryContext) -> AIRoutingDecision:
        """Route context to AI or Deterministic processing path."""
        if self._force_ai:
            return AIRoutingDecision(
                use_ai=True,
                reason="Forced AI routing via configuration",
                ambiguity_factors=["force_ai_config"],
            )

        # 0. Deterministic Safety Bypasses (Do not call LLM for clear safety/budget bounds)
        if context.customer_opt_out:
            return AIRoutingDecision(
                use_ai=False,
                reason="deterministic_safety_bypass_opt_out",
                ambiguity_factors=[],
            )

        if context.attempt_count >= context.max_attempts:
            return AIRoutingDecision(
                use_ai=False,
                reason="deterministic_safety_bypass_retry_budget_exhausted",
                ambiguity_factors=[],
            )

        if context.failure_category == FailureCategory.FRAUD:
            return AIRoutingDecision(
                use_ai=False,
                reason="deterministic_safety_bypass_fraud_protection",
                ambiguity_factors=[],
            )

        ambiguity_factors: list[str] = []

        # 1. Unknown failure category
        if context.failure_category == FailureCategory.UNKNOWN:
            ambiguity_factors.append("unknown_failure_category")

        # 2. Free-text failure reason / error description
        reason_text = (context.failure_reason or "").strip()
        if reason_text and len(reason_text) > 10 and not reason_text.isalnum():
            ambiguity_factors.append("free_text_failure_reason")

        # 3. Conflicting metadata signals
        meta = context.metadata or {}
        if meta.get("conflicting_signals") or meta.get("ambiguous"):
            ambiguity_factors.append("conflicting_signals_flag")

        # 4. Unusual or complex history
        if len(context.previous_actions or []) > 1:
            ambiguity_factors.append("multi_attempt_history")

        if meta.get("customer_notes") or meta.get("communication_history"):
            ambiguity_factors.append("unstructured_customer_text")

        # 5. Multiple candidate actions requiring contextual ranking
        # Categories like soft, authentication_required, checkout_abandonment, overdue_receivable, mandate_failure
        # have multiple plausible interventions (send_payment_link vs retry_payment vs send_reminder vs alternate_channel)
        if context.failure_category in (
            FailureCategory.SOFT,
            FailureCategory.AUTHENTICATION_REQUIRED,
            FailureCategory.HARD,
            FailureCategory.UNKNOWN,
        ) or meta.get("dataset_label") in (
            "healthy_soft", "mixed", "enterprise_receivables", "checkout_abandonment"
        ) or meta.get("source_type") in (
            "checkout_abandonment", "subscription_failure", "overdue_receivable", "mandate_failure"
        ):
            ambiguity_factors.append("multiple_valid_interventions_require_contextual_ranking")

        use_ai = len(ambiguity_factors) > 0

        if use_ai:
            reason = f"Ambiguous case detected ({', '.join(ambiguity_factors)}) — routing to AI"
        else:
            reason = "Clear deterministic case — skipping LLM call"

        return AIRoutingDecision(
            use_ai=use_ai,
            reason=reason,
            ambiguity_factors=ambiguity_factors,
        )
