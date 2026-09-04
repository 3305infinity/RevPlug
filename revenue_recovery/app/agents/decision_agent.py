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
        return build_ranked_proposal(
            context,
            scorer=ExpectedValueScorer(),
            model_name=self._model_name,
        )
