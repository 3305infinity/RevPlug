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

        # Determine diagnosis source (rules vs llm)
        source_type = context.metadata.get("source_type") or getattr(context, "source_type", "payment_failure")
        diagnosis_source = "rules" if context.failure_category != FailureCategory.UNKNOWN else "llm"

        # 1. Overdue Receivables Ladder
        if source_type in {"overdue_receivable", "receivable"}:
            days_overdue = int(context.metadata.get("days_overdue", 1))
            if days_overdue < 3:
                action = RecoveryAction.SEND_REMINDER
                reason = "Day 1 overdue: Gentle invoice reminder"
            elif days_overdue < 7:
                action = RecoveryAction.SEND_PAYMENT_LINK
                reason = "Day 3 overdue: Invoice payment link reminder"
            elif days_overdue < 14:
                action = RecoveryAction.ALTERNATE_CHANNEL
                reason = "Day 7 overdue: Alternate channel notice"
            else:
                action = RecoveryAction.ESCALATE_HUMAN
                reason = "Day 14 overdue: Escalate to human operator"
            return RecoveryProposal(
                action=action,
                reason=reason,
                confidence=0.9,
                model_name=self._model_name,
                evidence={"source_type": source_type, "days_overdue": days_overdue},
                diagnosis={"diagnosis_source": diagnosis_source},
            )

        # 2. Checkout Abandonment
        if source_type == "checkout_abandonment":
            abandoned_mins = int(context.metadata.get("checkout_age_minutes", context.metadata.get("abandoned_minutes", 30)))
            if abandoned_mins > 10080:  # > 7 days
                return RecoveryProposal(
                    action=RecoveryAction.STOP_RECOVERY,
                    reason="Checkout abandonment stale (>7 days)",
                    confidence=0.9,
                    model_name=self._model_name,
                    evidence={"abandoned_mins": abandoned_mins},
                    diagnosis={"diagnosis_source": "rules"},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Recent checkout abandonment; send recovery payment link",
                confidence=0.85,
                model_name=self._model_name,
                evidence={"abandoned_mins": abandoned_mins},
                diagnosis={"diagnosis_source": "rules"},
            )

        # 3. Subscription Failure
        if source_type == "subscription_failure":
            if context.failure_category == FailureCategory.SOFT and context.attempt_count < context.max_attempts:
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason="Soft subscription failure; retry payment token",
                    confidence=0.8,
                    proposed_retry=True,
                    model_name=self._model_name,
                    evidence={"attempt_count": context.attempt_count},
                    diagnosis={"diagnosis_source": "rules"},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Subscription failure non-retryable or budget exhausted; send link",
                confidence=0.75,
                model_name=self._model_name,
                evidence={"attempt_count": context.attempt_count},
                diagnosis={"diagnosis_source": "rules"},
            )

        # 4. Mandate Failure
        if source_type == "mandate_failure":
            retry_eligible = context.metadata.get("retry_eligible", True)
            if retry_eligible and context.attempt_count < context.max_attempts:
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason="Mandate failure temporary error; queue delayed retry",
                    confidence=0.8,
                    proposed_retry=True,
                    model_name=self._model_name,
                    evidence={"retry_eligible": True},
                    diagnosis={"diagnosis_source": "rules"},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Mandate failure non-retryable; request manual payment link",
                confidence=0.75,
                model_name=self._model_name,
                evidence={"retry_eligible": False},
                diagnosis={"diagnosis_source": "rules"},
            )

        # 5. Standard Payment Failure & General Rules
        if context.failure_category == FailureCategory.FRAUD:
            return RecoveryProposal(
                action=RecoveryAction.STOP_RECOVERY,
                reason="Fraud-related failures must not be automatically retried or contacted",
                confidence=0.95,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
                diagnosis={"diagnosis_source": "rules"},
            )

        if context.failure_category == FailureCategory.AUTHENTICATION_REQUIRED:
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Customer must re-authenticate; send a payment link to resume",
                confidence=0.8,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
                diagnosis={"diagnosis_source": "rules"},
            )

        if context.failure_category == FailureCategory.SOFT:
            if context.customer_opt_out:
                return RecoveryProposal(
                    action=RecoveryAction.STOP_RECOVERY,
                    reason="Customer has opted out of automated recovery; must not retry",
                    confidence=0.95,
                    model_name=self._model_name,
                    evidence={"category": context.failure_category.value, "customer_opt_out": True},
                    diagnosis={"diagnosis_source": "rules"},
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
                    diagnosis={"diagnosis_source": "rules"},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Soft failure but retry budget exhausted; offer payment link",
                confidence=0.6,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
                diagnosis={"diagnosis_source": "rules"},
            )

        if context.failure_category == FailureCategory.HARD:
            if context.attempt_count >= 2:
                return RecoveryProposal(
                    action=RecoveryAction.ESCALATE_HUMAN,
                    reason="Hard failure repeated multiple times; escalate to human review",
                    confidence=0.7,
                    model_name=self._model_name,
                    evidence={"category": context.failure_category.value},
                    diagnosis={"diagnosis_source": "rules"},
                )
            return RecoveryProposal(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                reason="Hard failure; offer payment link with alternate method",
                confidence=0.5,
                model_name=self._model_name,
                evidence={"category": context.failure_category.value},
                diagnosis={"diagnosis_source": "rules"},
            )

        # UNKNOWN / Ambiguous case -> Uses LLM or fallback
        return RecoveryProposal(
            action=RecoveryAction.ESCALATE_HUMAN,
            reason="Unknown failure category; escalate to human for manual review",
            confidence=0.6,
            model_name=self._model_name,
            evidence={"category": context.failure_category.value},
            diagnosis={"diagnosis_source": "llm"},
        )
