from app.audit.models import InMemoryAuditLog
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.chaos_agent import ChaosRecoveryDecisionAgent
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.recovery_orchestrator import RecoveryOrchestrator

def test_orchestrator_resilience_to_agent_failures():
    """Ensure the orchestrator does not crash when the agent fails, and logs the failure."""
    
    # Setup standard components
    audit_log = InMemoryAuditLog()
    base_agent = MockRecoveryDecisionAgent()
    # 100% failure rate to guarantee a failure on every call
    chaos_agent = ChaosRecoveryDecisionAgent(base_agent, failure_rate=1.0, rng_seed=42)
    
    policy_engine = InterventionPolicy()
    stopping_rules = StoppingRules()
    
    orchestrator = RecoveryOrchestrator(
        agent=chaos_agent,
        policy_engine=policy_engine,
        audit_log=audit_log,
        stopping_rules=stopping_rules,
        guard=DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine),
        scorer=ExpectedValueScorer(),
        executor=None,
    )
    
    from datetime import datetime, timezone
    item = RecoveryItem(
        id="stress_fail_01",
        customer_id="cust_1",
        amount_minor=10000,
        currency="INR",
        root_cause="soft",
        status=RecoveryStatus.DETECTED,
        source_type="razorpay_webhook",
        external_id="ext_1",
        created_at=datetime.now(timezone.utc),
    )
    
    context = RecoveryContext(
        item_id=item.id,
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=item.amount_minor,
        currency=item.currency,
        expected_recovery_value=10000,
        customer_opt_out=False,
        failure_code="soft",
        failure_reason="test",
        max_attempts=3,
    )
    
    # Run should NOT raise an exception
    result = orchestrator.run(item, context)
    
    # Agent failed, so proposed_action should be None
    assert result.proposed_action is None
    
    # Audit log should contain agent_failed event
    events = result.audit_events
    failure_event = next((e for e in events if e.action == "agent_failed"), None)
    assert failure_event is not None
    assert "error" in failure_event.metadata
    
    # Since agent failed, the deterministic fallback (rules engine) should have taken over.
    # Without an agent proposal, the rule engine escalates or stops based on safety.
    assert result.safety_decision in ("ESCALATE", "STOP", "DENY")
