from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.evaluation import (
    EvaluationReport,
    GoldenScenario,
    ScenarioResult,
    evaluate_agent,
    get_golden_scenarios,
)
from app.agents.llm_agent import AgentTrace, RealRecoveryDecisionAgent
from app.agents.llm_client import DeterministicLLMClient, LLMClient, LLMResponse
from app.agents.llm_provider import get_llm_provider
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.prompt_builder import RecoveryPromptBuilder
from app.agents.validator import ProposalValidator, ProposalValidationError


def build_agent():
    """Build the recovery decision agent based on RECOVERY_AGENT_MODE env var.

    Modes:
        mock (default): deterministic mock agent, no API key needed
        llm: real LLM-backed agent with fallback to mock
    """
    import os
    mode = os.environ.get("RECOVERY_AGENT_MODE", "mock").lower()
    if mode == "llm":
        return RealRecoveryDecisionAgent(
            llm_client=get_llm_provider(),
            fallback_agent=MockRecoveryDecisionAgent(),
            name="real-agent",
        )
    return MockRecoveryDecisionAgent(
        name="sandbox-agent",
        model_name="deterministic-mock",
    )


__all__ = [
    "RecoveryDecisionAgent",
    "MockRecoveryDecisionAgent",
    "RealRecoveryDecisionAgent",
    "RecoveryAgentOrchestrator",
    "ProposalValidator",
    "ProposalValidationError",
    "LLMClient",
    "LLMResponse",
    "DeterministicLLMClient",
    "RecoveryPromptBuilder",
    "AgentTrace",
    "EvaluationReport",
    "GoldenScenario",
    "ScenarioResult",
    "evaluate_agent",
    "get_golden_scenarios",
    "build_agent",
]
