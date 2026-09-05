import random
import time
from typing import Any
from app.domain.context import RecoveryContext
from app.domain.proposals import RecoveryProposal, RecoveryAction

class AgentTimeoutError(Exception):
    pass

class AgentMalformedOutputError(Exception):
    pass

class ChaosRecoveryDecisionAgent:
    """A chaos-testing wrapper for an underlying agent.
    
    Randomly injects failures such as timeouts, unhandled exceptions,
    or malformed responses to ensure the Orchestrator safely falls back
    without taking dangerous actions.
    """
    
    def __init__(self, wrapped_agent: Any, failure_rate: float = 0.5, rng_seed: int | None = None):
        self._wrapped = wrapped_agent
        self._failure_rate = failure_rate
        self._rng = random.Random(rng_seed)
        
    @property
    def name(self) -> str:
        return f"chaos_wrapper({self._wrapped.name})"

    @property
    def model_name(self) -> str:
        return f"chaos_{self._wrapped.model_name}"

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        # Determine if we should inject a failure
        if self._rng.random() < self._failure_rate:
            failure_type = self._rng.choice(["timeout", "exception", "malformed_output"])
            
            if failure_type == "timeout":
                time.sleep(0.1) # Simulate delay
                raise AgentTimeoutError("LLM API timed out after 30 seconds.")
                
            elif failure_type == "exception":
                raise ValueError("Unexpected rate limit error from LLM provider.")
                
            elif failure_type == "malformed_output":
                raise AgentMalformedOutputError("LLM returned unparseable JSON or missing fields.")

        # If no failure, call the underlying agent
        return self._wrapped.propose(context)
