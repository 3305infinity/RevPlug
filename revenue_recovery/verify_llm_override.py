from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.agents.ai_router import AIRouter
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.agents.llm_client import LLMResponse

class MockLLM:
    model_name = 'mock'
    provider_name = 'mock'
    def generate(self, *args, **kwargs):
        return LLMResponse(
            content='{"selected_action": "retry_payment", "confidence": 0.95, "reasoning_summary": "test"}',
            model='mock',
            latency_ms=10,
            success=True,
        )

agent = RealRecoveryDecisionAgent(llm_client=MockLLM(), router=AIRouter(force_ai=True))
ctx = RecoveryContext(
    item_id='test',
    failure_category=FailureCategory.AUTHENTICATION_REQUIRED,
    retryable=False,
    attempt_count=0,
    amount_minor=50000,
    currency='INR',
    expected_recovery_value=0,
    customer_opt_out=False,
)
proposal = agent.propose(ctx)
print('action:', proposal.action.value)
print('confidence:', proposal.confidence)
print('llm_override:', proposal.evidence.get('llm_override'))
print('top_net_ev:', proposal.evidence.get('top_net_ev'))
