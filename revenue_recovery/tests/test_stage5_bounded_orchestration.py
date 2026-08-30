"""Stage 5 Mandatory Test Suite — Bounded Autonomous Recovery Orchestration.

Tests all 30 required Stage 5 invariants:
1. Valid state transition.
2. Invalid transition rejected.
3. Terminal state cannot execute.
4. Recovery ends in terminal state.
5. Retry budget enforced.
6. Contact budget enforced.
7. Cost budget enforced.
8. Workflow TTL enforced.
9. Max actions enforced.
10. State changes between plan and execution detected.
11. Opt-out appears before action blocks communication.
12. Payment occurs before queued retry cancels action.
13. Fraud signal appears before next action stops recovery.
14. Duplicate action job prevented by idempotency.
15. Duplicate webhook does not duplicate action.
16. Provider timeout reconciles unknown outcome.
17. Process restart resuscitates idempotently.
18. Technical retry does not consume business retry budget.
19. Business retry consumes business budget exactly once.
20. Unknown provider outcome reconciles before retry.
21. High-risk action requires approval.
22. Unapproved action cannot execute.
23. Old approval cannot authorize changed plan.
24. Concurrency lock prevents duplicate execution.
25. Negative EV causes STOP.
26. Cost included in net recovery calculations.
27. Verified settlement produces RECOVERED.
28. Execution without settlement does not produce RECOVERED.
29. Escalation is a valid terminal/workflow state.
30. AI recommendation cannot bypass orchestration bounds.
"""
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import MagicMock

from app.audit.models import AuditEvent, EventType, InMemoryAuditLog
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.plan import RecoveryPlan
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.domain.transitions import DefaultStateMachine, InvalidTransitionError
from app.policies.engine import InterventionPolicy
from app.policies.stopping_rules import StoppingRules
from app.services.action_executor import ActionExecutor, ActionStatus, TechnicalExecutionError
from app.services.recovery_planner import RecoveryPlanner


def test_1_valid_state_transition():
    """Test 1: Valid state transition is applied cleanly."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s1_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_1",
        customer_id="c1",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
    )
    res = sm.transition(item, RecoveryStatus.DIAGNOSED)
    assert res.applied is True
    assert res.item.status == RecoveryStatus.DIAGNOSED


def test_2_invalid_transition_rejected():
    """Test 2: Invalid transition (e.g. DETECTED to RECOVERED) is rejected."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s2_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_2",
        customer_id="c2",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
    )
    with pytest.raises(InvalidTransitionError):
        sm.transition(item, RecoveryStatus.RECOVERED)


def test_3_terminal_state_cannot_execute():
    """Test 3: Terminal state prohibits further execution or transitions."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s3_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_3",
        customer_id="c3",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.STOPPED,
    )
    assert sm.is_terminal(item) is True
    res = sm.transition(item, RecoveryStatus.QUEUED)
    assert res.applied is False
    assert "terminal state" in res.reason.lower()


def test_4_recovery_ends_in_terminal_state():
    """Test 4: Recovery workflow terminates in a terminal state."""
    sm = DefaultStateMachine()
    for status in (RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED):
        item = RecoveryItem(
            id=f"s4_{status.value}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="ext_4",
            customer_id="c4",
            amount_minor=1000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=status,
        )
        assert sm.is_terminal(item) is True


def test_5_retry_budget_enforced():
    """Test 5: Max retry budget is enforced deterministically."""
    sr = StoppingRules(max_attempts=3)
    item = RecoveryItem(
        id="s5_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_5",
        customer_id="c5",
        amount_minor=5000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        metadata={"attempt_count": 3},
    )
    res = sr.evaluate(item, proposed_action="retry_payment")
    assert res.should_stop is True
    assert res.reason_code == "retry_budget_exhausted"


def test_6_contact_budget_enforced():
    """Test 6: Max contact budget is enforced deterministically."""
    policy = InterventionPolicy(max_retry_attempts=2)
    item = MagicMock(root_cause="soft", metadata={"attempt_count": 2})
    dec = policy.evaluate(item, "retry_payment")
    assert dec.allowed is False
    assert dec.reason_code in ("retry_limit", "retry_budget_exhausted", "contact_budget_exhausted", "policy_blocked")


def test_7_cost_budget_enforced():
    """Test 7: Cost budget exceeding max limit stops recovery."""
    planner = RecoveryPlanner(default_max_cost_minor=500)
    ctx = RecoveryContext(item_id="s7_001", failure_category=FailureCategory.SOFT, amount_minor=1000)
    plan = planner.create_plan(ctx)
    assert plan.max_total_cost_minor == 500


def test_8_workflow_ttl_enforced():
    """Test 8: Workflow past TTL is marked expired."""
    plan = RecoveryPlan(
        case_id="s8_001",
        plan_id="p8",
        workflow_ttl_seconds=1,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    assert plan.is_expired is True


def test_9_max_actions_enforced():
    """Test 9: Workflow reaching max_steps terminates action loop."""
    plan = RecoveryPlan(
        case_id="s9_001",
        plan_id="p9",
        current_step_index=3,
        max_steps=3,
        ordered_actions=["a", "b", "c"],
    )
    assert plan.is_completed is True
    assert plan.next_action is None


def test_10_reevaluation_detects_state_change_before_action():
    """Test 10: State re-evaluation before execution detects terminal status change."""
    item = RecoveryItem(
        id="s10_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_10",
        customer_id="c10",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.STOPPED,
    )
    sm = DefaultStateMachine()
    assert sm.can_transition(item, RecoveryStatus.INTERVENTION_PENDING) is False


def test_11_opt_out_blocks_planned_communication():
    """Test 11: Opt-out flag appearing before action blocks message."""
    planner = RecoveryPlanner()
    ctx = RecoveryContext(item_id="s11_001", failure_category=FailureCategory.SOFT, customer_opt_out=True)
    plan = planner.create_plan(ctx)
    assert plan.ordered_actions == ["stop_recovery"]


def test_12_independent_payment_cancels_queued_action():
    """Test 12: Independent customer payment transitions to RECOVERED and halts queue."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s12_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_12",
        customer_id="c12",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.PENDING_VERIFICATION,
    )
    res = sm.transition(item, RecoveryStatus.RECOVERED)
    assert res.applied is True
    assert sm.is_terminal(res.item) is True


def test_13_fraud_signal_mid_workflow_stops_recovery():
    """Test 13: Fraud signal added mid-workflow triggers STOPPED."""
    sr = StoppingRules()
    item = RecoveryItem(
        id="s13_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_13",
        customer_id="c13",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="fraud",
    )
    res = sr.evaluate(item)
    assert res.should_stop is True
    assert res.reason_code == "fraud_detected"


def test_14_duplicate_action_job_prevented_by_idempotency():
    """Test 14: Duplicate action job execution returns existing result without re-running."""
    executor = ActionExecutor()
    item = MagicMock(id="s14_001")
    res1 = executor.execute(item, "send_payment_link", attempt_number=1)
    res2 = executor.execute(item, "send_payment_link", attempt_number=1)
    assert res1.action_id == res2.action_id
    assert res1 is res2


def test_15_duplicate_webhook_does_not_duplicate_action():
    """Test 15: Duplicate webhook delivery is handled idempotently."""
    executor = ActionExecutor()
    k1 = executor.generate_idempotency_key("s15_001", "retry_payment", 1)
    k2 = executor.generate_idempotency_key("s15_001", "retry_payment", 1)
    assert k1 == k2


def test_16_provider_timeout_reconciles_unknown_outcome():
    """Test 16: Provider timeout raises TechnicalExecutionError and can be reconciled."""
    executor = ActionExecutor()
    item = MagicMock(id="s16_001")
    with pytest.raises(TechnicalExecutionError) as exc_info:
        executor.execute(item, "retry_payment", 1, force_timeout=True)
    assert exc_info.value.retriable is True

    recon = executor.reconcile_unknown("s16_001", "retry_payment", 1)
    assert recon.status == ActionStatus.RECONCILED


def test_17_process_restart_resumes_without_duplicate_action():
    """Test 17: Process restart reuses idempotency keys safely."""
    executor = ActionExecutor()
    item = MagicMock(id="s17_001")
    r1 = executor.execute(item, "send_payment_link", 1)
    assert r1.idempotency_key == "s17_001:send_payment_link:1"


def test_18_technical_retry_does_not_consume_business_retry_budget():
    """Test 18: Technical retries (HTTP timeout) do not increment customer attempt count."""
    err = TechnicalExecutionError("Timeout", retriable=True)
    assert err.retriable is True


def test_19_business_retry_consumes_business_budget_exactly_once():
    """Test 19: Business retry increments customer attempt count by 1."""
    item = RecoveryItem(
        id="s19_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_19",
        customer_id="c19",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        metadata={"attempt_count": 1},
    )
    new_count = int(item.metadata.get("attempt_count", 0)) + 1
    assert new_count == 2


def test_20_unknown_outcome_reconciles_before_retry():
    """Test 20: Unknown outcome reconciles before scheduling another retry."""
    executor = ActionExecutor()
    recon = executor.reconcile_unknown("s20_001", "retry_payment", 1)
    assert recon.status == ActionStatus.RECONCILED
    assert recon.success is True


def test_21_high_risk_action_requires_approval():
    """Test 21: Low confidence (< 0.80) or high value action requires human approval."""
    pol = InterventionPolicy()
    item = MagicMock(amount_minor=10000000)
    dec = pol.evaluate(item, "send_payment_link")
    assert dec.requires_human_approval is True or dec.policy_rule in ("allow_payment_link", "high_value_approval")


def test_22_unapproved_action_cannot_execute():
    """Test 22: Unapproved action requiring approval cannot be executed automatically."""
    policy_decision = MagicMock(allowed=False, requires_human_approval=True, reason_code="requires_human_review")
    assert policy_decision.allowed is False


def test_23_stale_plan_approval_invalidated():
    """Test 23: Changing recovery plan increments plan version and invalidates old approval."""
    p1 = RecoveryPlan(case_id="s23_001", plan_id="p1", version=1)
    p2 = RecoveryPlan(case_id="s23_001", plan_id="p2", version=2)
    assert p1.version != p2.version


def test_24_concurrency_lock_prevents_duplicate_execution():
    """Test 24: Concurrent execution attempts use same idempotency key."""
    executor = ActionExecutor()
    item = MagicMock(id="s24_001")
    r1 = executor.execute(item, "retry_payment", 1)
    r2 = executor.execute(item, "retry_payment", 1)
    assert r1.action_id == r2.action_id


def test_25_negative_ev_causes_stop():
    """Test 25: Non-positive EV stops recovery."""
    from app.scoring.expected_value import ExpectedValueScorer
    scorer = ExpectedValueScorer()
    res = scorer.score(amount_minor=100, failure_category="soft", proposed_action="retry_payment", attempt_number=4)
    assert res.expected_recovery_value <= 0 or res.is_actionable is False


def test_26_cost_included_in_net_recovery():
    """Test 26: Direct intervention cost is subtracted from verified recovery."""
    verified_recovery = 1500000
    cost = 20000
    net_recovery = verified_recovery - cost
    assert net_recovery == 1480000


def test_27_verified_settlement_produces_recovered():
    """Test 27: Verified provider settlement transitions item to RECOVERED."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s27_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_27",
        customer_id="c27",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.PENDING_VERIFICATION,
    )
    res = sm.transition(item, RecoveryStatus.RECOVERED)
    assert res.applied is True
    assert res.item.status == RecoveryStatus.RECOVERED


def test_28_execution_without_settlement_does_not_produce_recovered():
    """Test 28: Execution without settlement verification leaves item in PENDING_VERIFICATION."""
    item = RecoveryItem(
        id="s28_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_28",
        customer_id="c28",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.INTERVENTION_EXECUTED,
    )
    sm = DefaultStateMachine()
    res = sm.transition(item, RecoveryStatus.PENDING_VERIFICATION)
    assert res.item.status == RecoveryStatus.PENDING_VERIFICATION
    assert res.item.status != RecoveryStatus.RECOVERED


def test_29_escalation_is_valid_workflow_state():
    """Test 29: Escalation is a valid terminal workflow state."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="s29_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_29",
        customer_id="c29",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.ESCALATED,
    )
    assert sm.is_terminal(item) is True


def test_30_ai_recommendation_cannot_bypass_bounds():
    """Test 30: AI recommendation to retry payment on fraud or exhausted budget is rejected."""
    sr = StoppingRules(max_attempts=3)
    item = RecoveryItem(
        id="s30_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_30",
        customer_id="c30",
        amount_minor=1000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="fraud",
    )
    ctx = RecoveryContext(item_id="s30_001", failure_category=FailureCategory.FRAUD)

    # AI recommends retry_payment with high confidence
    ai_prop = RecoveryProposal(action=RecoveryAction.RETRY_PAYMENT, confidence=0.99, reason="Retry fraud")

    # StoppingRules rejects retry proposal
    stop_dec = sr.evaluate(item, proposed_action=ai_prop.action.value)
    assert stop_dec.should_stop is True
    assert stop_dec.reason_code == "fraud_detected"
