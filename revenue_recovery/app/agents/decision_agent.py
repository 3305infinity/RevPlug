from __future__ import annotations

from typing import Protocol

from app.agents.candidate_scorer import _data_driven_confidence, _eligible_candidates, _score_candidates, build_ranked_proposal
from app.agents.llm_client import DeterministicLLMClient, LLMClient, LLMResponse
from app.domain.actions import ActionRegistry
from app.domain.context import RecoveryContext
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

        if proposal.action.value not in eligible:
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
