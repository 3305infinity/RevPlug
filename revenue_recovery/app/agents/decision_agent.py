from __future__ import annotations

from typing import Protocol

from app.agents.candidate_scorer import _data_driven_confidence, _eligible_candidates, _score_candidates
from app.agents.llm_client import DeterministicLLMClient, LLMClient, LLMResponse
from app.domain.actions import ActionRegistry
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.scoring.expected_value import ExpectedValueScorer


class RecoveryDecisionAgent(Protocol):
    """Interface for agents that produce recovery proposals.

    Implementations MUST ONLY produce proposals. They must NEVER directly
    execute actions, move money, or contact customers.
    """

    @property
    def name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        """Propose a recovery action based on the given context.

        Returns a structured RecoveryProposal. Does NOT execute anything.
        """
        ...


class MockRecoveryDecisionAgent:
    """Deterministic mock agent that produces sensible proposals with ranked candidates.

    Does NOT require any LLM API key. Uses only the classified failure
    category and recovery context to produce proposals.

    Proposal logic (mirrors existing policy categories):
      - SOFT + retryable + within budget → RETRY_PAYMENT
      - AUTHENTICATION_REQUIRED → SEND_PAYMENT_LINK
      - HARD → SEND_PAYMENT_LINK (or ESCALATE_HUMAN if repeated)
      - FRAUD → STOP_RECOVERY
      - UNKNOWN → ESCALATE_HUMAN

    Each proposal includes a ranked candidate list scored by EV_net.
    Confidence is derived from comparable historical outcomes, not hardcoded.
    """

    def __init__(self, *, name: str = "mock-agent", model_name: str = "mock") -> None:
        self._name = name
        self._model_name = model_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model_name

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        from app.domain.failures import FailureCategory

        source_type = context.metadata.get("source_type") or getattr(context, "source_type", "payment_failure")
        diagnosis_source = "rules" if context.failure_category != FailureCategory.UNKNOWN else "llm"

        # Domain-specific primary action selection (preserves existing semantics)
        if source_type in {"overdue_receivable", "receivable"}:
            days_overdue = int(context.metadata.get("days_overdue", 1))
            if days_overdue < 3:
                primary_action = RecoveryAction.SEND_REMINDER
                primary_reason = "Day 1 overdue: Gentle invoice reminder"
            elif days_overdue < 7:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Day 3 overdue: Invoice payment link reminder"
            elif days_overdue < 14:
                primary_action = RecoveryAction.ALTERNATE_CHANNEL
                primary_reason = "Day 7 overdue: Alternate channel notice"
            else:
                primary_action = RecoveryAction.ESCALATE_HUMAN
                primary_reason = "Day 14 overdue: Escalate to human operator"
        elif source_type == "checkout_abandonment":
            abandoned_mins = int(context.metadata.get("checkout_age_minutes", context.metadata.get("abandoned_minutes", 30)))
            if abandoned_mins > 10080:
                primary_action = RecoveryAction.STOP_RECOVERY
                primary_reason = "Checkout abandonment stale (>7 days)"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Recent checkout abandonment; send recovery payment link"
        elif source_type == "subscription_failure":
            if context.failure_category == FailureCategory.SOFT and context.attempt_count < context.max_attempts:
                primary_action = RecoveryAction.RETRY_PAYMENT
                primary_reason = "Soft subscription failure; retry payment token"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Subscription failure non-retryable or budget exhausted; send link"
        elif source_type == "mandate_failure":
            retry_eligible = context.metadata.get("retry_eligible", True)
            if retry_eligible and context.attempt_count < context.max_attempts:
                primary_action = RecoveryAction.RETRY_PAYMENT
                primary_reason = "Mandate failure temporary error; queue delayed retry"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Mandate failure non-retryable; request manual payment link"
        elif context.failure_category == FailureCategory.FRAUD:
            primary_action = RecoveryAction.STOP_RECOVERY
            primary_reason = "Fraud-related failures must not be automatically retried or contacted"
        elif context.failure_category == FailureCategory.AUTHENTICATION_REQUIRED:
            if "send_payment_link" in context.previous_actions and (context.last_observation or {}).get("status") == "failed":
                primary_action = RecoveryAction.ESCALATE_HUMAN
                primary_reason = "Payment link sent for re-authentication failed; escalate to human"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Customer must re-authenticate; send a payment link to resume"
        elif context.failure_category == FailureCategory.SOFT:
            if context.customer_opt_out:
                primary_action = RecoveryAction.STOP_RECOVERY
                primary_reason = "Customer has opted out of automated recovery; must not retry"
            elif "retry_payment" in context.previous_actions and (context.last_observation or {}).get("status") == "failed":
                if "send_payment_link" not in context.previous_actions:
                    primary_action = RecoveryAction.SEND_PAYMENT_LINK
                    primary_reason = "Payment retry failed; pivot to direct payment link"
                elif "alternate_channel" not in context.previous_actions:
                    primary_action = RecoveryAction.ALTERNATE_CHANNEL
                    primary_reason = "Payment link failed; attempt recovery via alternate notification channel"
                else:
                    primary_action = RecoveryAction.ESCALATE_HUMAN
                    primary_reason = "Multiple recovery interventions failed; escalate for human assistance"
            elif context.retryable and context.attempt_count < context.max_attempts:
                primary_action = RecoveryAction.RETRY_PAYMENT
                primary_reason = f"Soft failure (attempt {context.attempt_count + 1}/{context.max_attempts}); retry is appropriate"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Soft failure but retry budget exhausted; offer payment link"
        elif context.failure_category == FailureCategory.HARD:
            if "send_payment_link" in context.previous_actions and (context.last_observation or {}).get("status") == "failed":
                primary_action = RecoveryAction.ESCALATE_HUMAN
                primary_reason = "Hard failure payment link attempt failed; escalate to human review"
            elif context.attempt_count >= 2:
                primary_action = RecoveryAction.ESCALATE_HUMAN
                primary_reason = "Hard failure repeated multiple times; escalate to human review"
            else:
                primary_action = RecoveryAction.SEND_PAYMENT_LINK
                primary_reason = "Hard failure; offer payment link with alternate method"
        else:
            primary_action = RecoveryAction.ESCALATE_HUMAN
            primary_reason = "Unknown failure category; escalate to human for manual review"

        if not ActionRegistry.is_valid(primary_action.value):
            primary_action = RecoveryAction.ESCALATE_HUMAN
            primary_reason = "Primary action not in registry; escalate for safety"

        eligible = _eligible_candidates(context)
        if primary_action.value not in eligible:
            eligible.insert(0, primary_action.value)

        scorer = ExpectedValueScorer()
        scored = _score_candidates(context, eligible, scorer=scorer)
        confidence = _data_driven_confidence(context, scored)

        return RecoveryProposal(
            action=primary_action,
            reason=primary_reason,
            confidence=confidence,
            proposed_retry=(primary_action == RecoveryAction.RETRY_PAYMENT),
            model_name=self._model_name,
            evidence={
                "source_type": source_type,
                "days_overdue": context.metadata.get("days_overdue"),
                "category": context.failure_category.value,
            },
            diagnosis={"diagnosis_source": diagnosis_source},
            candidates=scored,
        )
