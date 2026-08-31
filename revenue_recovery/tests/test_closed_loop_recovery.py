from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.audit.models import InMemoryAuditLog
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.domain.transitions import DefaultStateMachine
from app.interventions.executor import ExecutionResult, SimulatedRecoveryExecutor
from app.policies.engine import InterventionPolicy, PolicyDecision
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.recovery_orchestrator import RecoveryOrchestrator


class FixedAgent:
    """Agent that returns a sequence of proposals or a fixed proposal."""
    def __init__(self, proposals: list[RecoveryProposal]):
        self._proposals = proposals
        self._index = 0
        self._name = "fixed-agent"
        self._model_name = "test-mock"

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model_name

    def propose(self, context: RecoveryContext) -> RecoveryProposal:
        if self._index < len(self._proposals):
            prop = self._proposals[self._index]
            self._index += 1
            return prop
        return self._proposals[-1]


class CustomOutcomeRepo:
    def __init__(self, outcome: RecoveryOutcome | None = None):
        self.outcome = outcome

    def get_for_item(self, item_id: str) -> RecoveryOutcome | None:
        return self.outcome


class MultiScenarioExecutor:
    """Executor that runs scenarios per action or attempt number."""
    def __init__(self, scenarios: list[tuple[bool, str, bool]]):
        # (success, reason, retry_eligible)
        self.scenarios = scenarios
        self.call_count = 0
        self.actions_executed = []

    def execute(self, item: RecoveryItem, action: str, *, attempt_number: int, scenario: str | None = None) -> ExecutionResult:
        self.actions_executed.append(action)
        if self.call_count < len(self.scenarios):
            succ, reason, retry = self.scenarios[self.call_count]
            self.call_count += 1
            return ExecutionResult(
                success=succ,
                action=action,
                attempt_number=attempt_number,
                reason=reason,
                retry_eligible=retry,
            )
        self.call_count += 1
        return ExecutionResult(
            success=True,
            action=action,
            attempt_number=attempt_number,
            reason="Default success",
            retry_eligible=False,
        )


def _build_test_orchestrator(agent, executor, stopping_rules=None, policy_engine=None, outcomes=None):
    audit_log = InMemoryAuditLog()
    policy = policy_engine or InterventionPolicy(max_retry_attempts=3)
    stop_rules = stopping_rules or StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stop_rules, policy_engine=policy)
    scorer = ExpectedValueScorer()

    return RecoveryOrchestrator(
        agent=agent,
        policy_engine=policy,
        audit_log=audit_log,
        stopping_rules=stop_rules,
        guard=guard,
        scorer=scorer,
        executor=executor,
        outcomes=outcomes,
        state_machine=DefaultStateMachine(),
    )


def _make_item(item_id="item-test", status=RecoveryStatus.DETECTED, root_cause="soft_decline", metadata=None) -> RecoveryItem:
    return RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext-123",
        customer_id="cust-456",
        amount_minor=185000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=status,
        root_cause=root_cause,
        expected_recovery_value=185000,
        intervention_cost=50,
        metadata=metadata or {},
    )


def _make_context(item: RecoveryItem, category=FailureCategory.SOFT) -> RecoveryContext:
    return RecoveryContext(
        item_id=item.id,
        failure_category=category,
        retryable=True,
        amount_minor=item.amount_minor,
        currency=item.currency,
        attempt_count=0,
        customer_opt_out=False,
        max_attempts=3,
        expected_recovery_value=item.expected_recovery_value,
    )


# Scenario 1: Successful first action → RECOVERED
def test_1_successful_first_action_recovered():
    item = _make_item()
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Soft failure retry", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Payment captured", False)])
    outcome_repo = CustomOutcomeRepo(RecoveryOutcome(
        id="out-1", recovery_item_id=item.id, outcome_type="recovered",
        expected_recovery_minor=185000, actual_recovery_minor=185000, net_recovery_minor=184950
    ))
    orchestrator = _build_test_orchestrator(agent, executor, outcomes=outcome_repo)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "recovered"
    assert result.actual_recovery_value == 185000
    assert len(executor.actions_executed) == 1
    assert executor.actions_executed[0] == "retry_payment"


# Scenario 2: First action fails → agent replans → second action succeeds
def test_2_first_action_fails_agent_replans_second_succeeds():
    item = _make_item()
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Soft failure retry", confidence=0.9),
        RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="Retry failed; pivot to link", confidence=0.85),
    ])
    executor = MultiScenarioExecutor([
        (False, "Insufficient funds", True),
        (True, "Payment link paid", False),
    ])
    outcome_repo = CustomOutcomeRepo(RecoveryOutcome(
        id="out-2", recovery_item_id=item.id, outcome_type="recovered",
        expected_recovery_minor=185000, actual_recovery_minor=185000
    ))
    orchestrator = _build_test_orchestrator(agent, executor, outcomes=outcome_repo)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "recovered"
    assert executor.actions_executed == ["retry_payment", "send_payment_link"]


# Scenario 3: First action fails → second action also fails → bounded termination
def test_3_first_action_fails_second_fails_bounded_termination():
    item = _make_item()
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Retry attempt 1", confidence=0.9),
        RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="Payment link attempt 2", confidence=0.85),
        RecoveryProposal(action=RecoveryAction.ESCALATE_HUMAN, reason="All actions failed", confidence=0.9),
    ])
    executor = MultiScenarioExecutor([
        (False, "Insufficient funds", True),
        (False, "Link expired", False),
    ])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "escalated"
    assert result.next_action == "escalate_human"


# Scenario 4: Policy blocks proposed next action
def test_4_policy_blocks_proposed_next_action():
    item = _make_item(root_cause="hard_decline")
    ctx = _make_context(item, category=FailureCategory.HARD)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Invalid retry on hard failure", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision == "DENY" or result.safety_decision == "ESCALATE" or result.safety_decision == "STOP"
    assert len(executor.actions_executed) == 0


# Scenario 5: Fraud condition prevents further automated action
def test_5_fraud_condition_prevents_action():
    item = _make_item(root_cause="fraud")
    ctx = _make_context(item, category=FailureCategory.FRAUD)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Unsafe retry", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision == "STOP"
    assert result.final_state == "stopped"
    assert result.stop_reason in ("fraud_detected", "policy_blocked")
    assert len(executor.actions_executed) == 0


# Scenario 6: Customer opt-out prevents further communication
def test_6_customer_opt_out_prevents_communication():
    item = _make_item(metadata={"customer_opted_out": True})
    ctx = _make_context(item)
    ctx = RecoveryContext(
        item_id=item.id, failure_category=FailureCategory.SOFT, customer_opt_out=True, amount_minor=10000
    )
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="Opted out attempt", confidence=0.85)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    stop_rules = StoppingRules(opted_out_customer_ids=frozenset(["cust-456"]))
    orchestrator = _build_test_orchestrator(agent, executor, stopping_rules=stop_rules)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision == "STOP"
    assert result.final_state == "stopped"
    assert result.stop_reason == "customer_opted_out"
    assert len(executor.actions_executed) == 0


# Scenario 7: Disputed invoice prevents automated collection
def test_7_disputed_invoice_prevents_collection():
    item = _make_item(metadata={"disputed": True})
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="Disputed attempt", confidence=0.85)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision == "STOP"
    assert result.final_state == "stopped"
    assert result.stop_reason == "invoice_disputed"
    assert len(executor.actions_executed) == 0


# Scenario 8: Action budget is exhausted
def test_8_action_budget_exhausted():
    item = _make_item(metadata={"attempt_count": 3})
    ctx = RecoveryContext(
        item_id=item.id, failure_category=FailureCategory.SOFT, attempt_count=3, max_attempts=3, amount_minor=10000
    )
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Over budget retry", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    stop_rules = StoppingRules(max_attempts=3)
    orchestrator = _build_test_orchestrator(agent, executor, stopping_rules=stop_rules)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision == "STOP" or result.safety_decision == "ESCALATE"
    assert result.final_state in ("stopped", "escalated")
    assert len(executor.actions_executed) == 0


# Scenario 9: Duplicate webhook / event does not duplicate recovery action
def test_9_duplicate_event_processing():
    item = _make_item(status=RecoveryStatus.RECOVERED)
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Already recovered", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "recovered"
    assert len(executor.actions_executed) == 0


# Scenario 10: API timeout / retry does not cause duplicate execution
def test_10_api_timeout_retry():
    item = _make_item()
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="Payment link timeout retry", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([
        (False, "API Timeout", True)
    ])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    # First attempt executed, failed gracefully with timeout observation
    assert len(executor.actions_executed) == 1
    assert result.execution_result["retry_eligible"] is True


# Scenario 11: Already recovered case cannot execute another recovery action
def test_11_already_recovered_cannot_reexecute():
    item = _make_item(status=RecoveryStatus.RECOVERED)
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Duplicate trigger", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "recovered"
    assert len(executor.actions_executed) == 0


# Scenario 12: Agent proposes an invalid/unknown action and the system safely handles it
def test_12_invalid_unknown_action_handled_safely():
    item = _make_item()
    ctx = _make_context(item)
    invalid_action = type("UnknownAction", (), {"value": "unknown_action_type"})()
    agent = FixedAgent([
        RecoveryProposal(action=invalid_action, reason="Invalid action", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Should not run", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.safety_decision in ("DENY", "STOP", "ESCALATE")
    assert len(executor.actions_executed) == 0


# Scenario 13: Agent repeatedly proposes the same action and system prevents infinite loop
def test_13_repeated_proposal_prevents_infinite_loop():
    item = _make_item()
    ctx = _make_context(item)
    # Agent keeps returning RETRY_PAYMENT repeatedly
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Loop 1", confidence=0.9),
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Loop 2", confidence=0.9),
        RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, reason="Loop 3", confidence=0.9),
    ])
    executor = MultiScenarioExecutor([
        (False, "Failed 1", True),
        (False, "Failed 2", True),
        (False, "Failed 3", True),
    ])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx, max_loop_iterations=5)

    # Loop should halt before infinite execution
    assert result.final_state in ("stopped", "escalated")
    assert result.stop_reason in ("no_positive_action", "retry_budget_exhausted")
    assert len(executor.actions_executed) <= 2


# Scenario 14: Human escalation produces a terminal state with an audit record
def test_14_human_escalation_terminal_with_audit():
    item = _make_item()
    ctx = _make_context(item)
    agent = FixedAgent([
        RecoveryProposal(action=RecoveryAction.ESCALATE_HUMAN, reason="Human review required", confidence=0.9)
    ])
    executor = MultiScenarioExecutor([(True, "Escalated", False)])
    orchestrator = _build_test_orchestrator(agent, executor)

    result = orchestrator.run(item, ctx)

    assert result.final_state == "escalated"
    assert result.next_action == "escalate_human"
    assert any(evt.action == "next_step_evaluated" or evt.action == "guard_evaluate" for evt in result.audit_events)
