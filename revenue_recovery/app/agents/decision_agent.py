from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.agents.candidate_scorer import _data_driven_confidence, _eligible_candidates, _score_candidates, build_ranked_proposal
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
    """Deterministic mock agent that produces EV-ranked proposals.

    Does NOT require any LLM API key. Uses the existing candidate-generation,
    EV-scoring, and data-driven confidence pipeline to produce proposals
    with the same structure as the real agent.

    Domain knowledge is expressed through candidate ELIGIBILITY rules,
    not through a competing hardcoded final-action selection.
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
        source_type = context.metadata.get("source_type") or getattr(context, "source_type", "payment_failure")
        diagnosis_source = "rules"

        eligible = _eligible_candidates(context)
        if not eligible:
            eligible = [RecoveryAction.STOP_RECOVERY.value]

        proposal = build_ranked_proposal(
            context,
            scorer=ExpectedValueScorer(),
            model_name=self._model_name,
        )

        domain_action = self._domain_routing(proposal.action, context, eligible)
        routing_override_reason = self._domain_routing_reason(context)

        if routing_override_reason is not None:
            proposal = RecoveryProposal(
                action=domain_action,
                reason=routing_override_reason,
                confidence=0.5,
                proposed_retry=(domain_action == RecoveryAction.RETRY_PAYMENT),
                model_name=self._model_name,
                evidence={
                    "source_type": source_type,
                    "days_overdue": context.metadata.get("days_overdue"),
                    "category": context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category),
                    "routing_reason": "domain_routing_override",
                },
                diagnosis={"diagnosis_source": diagnosis_source},
                candidates=proposal.candidates,
            )
        elif proposal.action.value not in eligible:
            for act in eligible:
                if ActionRegistry.is_valid(act):
                    proposal = RecoveryProposal(
                        action=RecoveryAction(act),
                        reason=f"Deterministic domain rules route to {act.replace('_', ' ').title()} for {source_type} / {context.failure_category.value if hasattr(context.failure_category, 'value') else context.failure_category}",
                        confidence=0.5,
                        proposed_retry=(act == RecoveryAction.RETRY_PAYMENT.value),
                        model_name=self._model_name,
                        evidence={
                            "source_type": source_type,
                            "days_overdue": context.metadata.get("days_overdue"),
                            "category": context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category),
                            "routing_reason": "domain_eligibility_override",
                        },
                        diagnosis={"diagnosis_source": diagnosis_source},
                        candidates=proposal.candidates,
                    )
                    break

        return proposal

    def _domain_routing(self, ev_action: RecoveryAction, context: RecoveryContext, eligible: list[str]) -> RecoveryAction:
        """Apply domain-specific routing rules to ensure consistent behavior with legacy agent."""
        category = context.failure_category
        attempt = context.attempt_count
        source_type = context.metadata.get("source_type", "")

        if source_type == "checkout_abandonment":
            checkout_age = int(context.metadata.get("checkout_age_minutes", context.metadata.get("abandoned_minutes", 30)))
            if checkout_age > 10080:
                return RecoveryAction.STOP_RECOVERY
            return RecoveryAction.SEND_PAYMENT_LINK

        if category == FailureCategory.HARD:
            if attempt == 0:
                if RecoveryAction.SEND_PAYMENT_LINK.value in eligible:
                    return RecoveryAction.SEND_PAYMENT_LINK
            if attempt >= 2:
                if RecoveryAction.ESCALATE_HUMAN.value in eligible:
                    return RecoveryAction.ESCALATE_HUMAN

        if category == FailureCategory.AUTHENTICATION_REQUIRED:
            if RecoveryAction.SEND_PAYMENT_LINK.value in eligible:
                return RecoveryAction.SEND_PAYMENT_LINK

        if category == FailureCategory.UNKNOWN:
            if RecoveryAction.ESCALATE_HUMAN.value in eligible:
                return RecoveryAction.ESCALATE_HUMAN

        if category == FailureCategory.FRAUD or context.customer_opt_out:
            if RecoveryAction.STOP_RECOVERY.value in eligible:
                return RecoveryAction.STOP_RECOVERY

        if category == FailureCategory.MANDATE_FAILURE:
            rep_count = int(context.metadata.get("representation_count", 0))
            max_reps = int(context.metadata.get("max_representations", 3))
            if rep_count >= max_reps:
                if RecoveryAction.ESCALATE_HUMAN.value in eligible:
                    return RecoveryAction.ESCALATE_HUMAN
                if RecoveryAction.SEND_PAYMENT_LINK.value in eligible:
                    return RecoveryAction.SEND_PAYMENT_LINK
            next_rep_str = context.metadata.get("next_representation_date")
            if next_rep_str:
                try:
                    next_rep_dt = datetime.fromisoformat(next_rep_str)
                    if datetime.now(timezone.utc) < next_rep_dt:
                        if RecoveryAction.SEND_PAYMENT_LINK.value in eligible:
                            return RecoveryAction.SEND_PAYMENT_LINK
                except (ValueError, TypeError):
                    pass
            if RecoveryAction.RETRY_PAYMENT.value in eligible:
                return RecoveryAction.RETRY_PAYMENT

        if category == FailureCategory.SOFT:
            if context.customer_opt_out:
                if RecoveryAction.STOP_RECOVERY.value in eligible:
                    return RecoveryAction.STOP_RECOVERY
            if attempt >= context.max_attempts and RecoveryAction.SEND_PAYMENT_LINK.value in eligible:
                return RecoveryAction.SEND_PAYMENT_LINK

        return ev_action

    def _domain_routing_reason(self, context: RecoveryContext) -> str | None:
        """Return routing override reason if domain rules require a specific action, None otherwise."""
        category = context.failure_category
        source_type = context.metadata.get("source_type", "")

        if source_type == "checkout_abandonment":
            checkout_age = int(context.metadata.get("checkout_age_minutes", context.metadata.get("abandoned_minutes", 30)))
            if checkout_age > 10080:
                return f"Domain rules route to Stop Recovery for stale checkout abandonment ({checkout_age} minutes)"
            return f"Domain rules route to Send Payment Link for fresh checkout abandonment ({checkout_age} minutes)"

        if category == FailureCategory.HARD:
            if context.attempt_count == 0:
                return f"Domain rules route to Send Payment Link for first-time hard failure"
            if context.attempt_count >= 2:
                return f"Domain rules route to Escalate Human for repeated hard failure ({context.attempt_count} attempts)"

        if category == FailureCategory.AUTHENTICATION_REQUIRED:
            return "Domain rules route to Send Payment Link for authentication required"

        if category == FailureCategory.UNKNOWN:
            return "Domain rules route to Escalate Human for unknown failure category"

        if category == FailureCategory.FRAUD or context.customer_opt_out:
            return "Domain rules route to Stop Recovery for fraud or opt-out"

        if category == FailureCategory.MANDATE_FAILURE:
            rep_count = int(context.metadata.get("representation_count", 0))
            max_reps = int(context.metadata.get("max_representations", 3))
            if rep_count >= max_reps:
                return f"Domain rules route to Escalate Human for exhausted mandate representations ({rep_count}/{max_reps})"
            next_rep_str = context.metadata.get("next_representation_date")
            if next_rep_str:
                try:
                    next_rep_dt = datetime.fromisoformat(next_rep_str)
                    if datetime.now(timezone.utc) < next_rep_dt:
                        return f"Domain rules route to Send Payment Link for mandate failure before representation window opens ({next_rep_str})"
                except (ValueError, TypeError):
                    pass
            return "Domain rules route to Retry Payment for available mandate representation window"

        if category == FailureCategory.SOFT:
            if context.customer_opt_out:
                return "Domain rules route to Stop Recovery for soft failure with opt-out"
            if context.attempt_count >= context.max_attempts:
                return "Domain rules route to Send Payment Link for soft failure with exhausted retry budget"

        return None
