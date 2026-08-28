from __future__ import annotations

from typing import Protocol

from app.domain.context import RecoveryContext
from app.domain.proposals import RecoveryAction, RecoveryProposal


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
    """Deterministic mock agent that produces sensible proposals.

    Does NOT require any LLM API key. Uses only the classified failure
    category and recovery context to produce proposals.

    Proposal logic (mirrors existing policy categories):
      - SOFT + retryable + within budget → RETRY_PAYMENT
      - AUTHENTICATION_REQUIRED → SEND_PAYMENT_LINK
      - HARD → SEND_PAYMENT_LINK (or ESCALATE_HUMAN if repeated)
      - FRAUD → STOP_RECOVERY
      - UNKNOWN → ESCALATE_HUMAN
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

        if context.failure_category == FailureCategory.FRAUD:
            return RecoveryProposal(
                action=RecoveryAction.STOP_RECOVERY,
                reason="Fraud-related failures must not be automatically retried or contacted",
                confidence=0.95,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
            )

        if context.failure_category == FailureCategory.AUTHENTICATION_REQUIRED:
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Customer must re-authenticate; send a payment link to resume",
                confidence=0.8,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
            )

        if context.failure_category == FailureCategory.SOFT:
            if context.customer_opt_out:
                return RecoveryProposal(
                    action=RecoveryAction.STOP_RECOVERY,
                    reason="Customer has opted out of automated recovery; must not retry",
                    confidence=0.95,
                    model_name=self._model_name,
                    evidence={"category": context.failure_category.value, "customer_opt_out": True},
                )
            if context.retryable and context.attempt_count < context.max_attempts:
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason=f"Soft failure (attempt {context.attempt_count + 1}/{context.max_attempts}); retry is appropriate",
                    confidence=0.7,
                    proposed_retry=True,
                    model_name=self._model_name,
                    evidence={
                        "category": context.failure_category.value,
                        "attempt": context.attempt_count + 1,
                    },
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Soft failure but retry budget exhausted; offer payment link",
                confidence=0.6,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
            )

        if context.failure_category == FailureCategory.HARD:
            if context.attempt_count >= 2:
                return RecoveryProposal(
                    action=RecoveryAction.ESCALATE_HUMAN,
                    reason="Hard failure repeated multiple times; escalate to human review",
                    confidence=0.7,
                    model_name=self._model_name,
                    evidence={"category": context.failure_category.value},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Hard failure; offer payment link with alternate method",
                confidence=0.5,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
            )

        # UNKNOWN
        return RecoveryProposal(
            action=RecoveryAction.ESCALATE_HUMAN,
            reason="Unknown failure category; escalate to human for manual review",
            confidence=0.6,
            model_name=self._model_name,
            evidence={"category": context.failure_category.value},
        )
