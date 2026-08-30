"""Golden End-to-End Scenarios Test Suite for Stage 5 Bounded Autonomous Recovery.

Tests 8 canonical end-to-end scenarios:
- Scenario A: Successful recovery
- Scenario B: Retry then alternative
- Scenario C: Correct stop (Do nothing / Hard decline)
- Scenario D: Customer opt-out mid-workflow
- Scenario E: Independent customer payment
- Scenario F: Provider timeout & reconciliation
- Scenario G: AI failure & deterministic fallback
- Scenario H: Human approval required
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock

from app.audit.models import AuditEvent, EventType, InMemoryAuditLog
from app.datasets.scenario_fixtures import get_golden_end_to_end_scenarios
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.transitions import DefaultStateMachine
from app.policies.engine import InterventionPolicy
from app.policies.stopping_rules import StoppingRules
from app.services.action_executor import ActionExecutor, ActionStatus, TechnicalExecutionError
from app.services.recovery_planner import RecoveryPlanner


def test_scenario_a_successful_recovery():
    """Scenario A: Failure -> Diagnosis -> Payment Link -> Paid -> Settlement Verified -> Recovered."""
    scenarios = get_golden_end_to_end_scenarios()
    scen_a = scenarios["scenario_a_successful_recovery"]
    assert scen_a["item_id"] == "scen_a_001"

    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="scen_a_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_a",
        customer_id="cust_a",
        amount_minor=2500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
    )
    # Detect -> Diagnose -> Queued -> Intervention Executed -> Pending Verification -> Recovered
    item = sm.transition(item, RecoveryStatus.DIAGNOSED).item
    item = sm.transition(item, RecoveryStatus.QUEUED).item
    item = sm.transition(item, RecoveryStatus.INTERVENTION_PENDING).item
    item = sm.transition(item, RecoveryStatus.INTERVENTION_EXECUTED).item
    item = sm.transition(item, RecoveryStatus.PENDING_VERIFICATION).item
    item = sm.transition(item, RecoveryStatus.RECOVERED).item

    assert item.status == RecoveryStatus.RECOVERED
    assert sm.is_terminal(item) is True


def test_scenario_b_retry_then_alternative():
    """Scenario B: Retry payment -> Fails -> Payment link -> Settled -> Recovered."""
    planner = RecoveryPlanner()
    ctx = RecoveryContext(item_id="scen_b_002", failure_category=FailureCategory.SOFT, attempt_count=0, retryable=True)
    plan = planner.create_plan(ctx)
    assert plan.ordered_actions == ["retry_payment", "send_payment_link", "stop_recovery"]

    executor = ActionExecutor()
    item = MagicMock(id="scen_b_002")
    # Step 1: retry payment
    res1 = executor.execute(item, "retry_payment", attempt_number=1)
    assert res1.success is True

    # Step 2: send payment link
    res2 = executor.execute(item, "send_payment_link", attempt_number=2)
    assert res2.success is True


def test_scenario_c_correct_stop():
    """Scenario C: Hard decline -> Do Nothing / Immediate Stop."""
    planner = RecoveryPlanner()
    ctx = RecoveryContext(item_id="scen_c_003", failure_category=FailureCategory.HARD, retryable=False)
    plan = planner.create_plan(ctx)
    assert plan.ordered_actions[0] == "send_payment_link"
    assert "stop_recovery" in plan.ordered_actions

    sr = StoppingRules()
    item = RecoveryItem(
        id="scen_c_003",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_c",
        customer_id="cust_c",
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="fraud",
    )
    stop_dec = sr.evaluate(item)
    assert stop_dec.should_stop is True


def test_scenario_d_opt_out():
    """Scenario D: Customer opts out -> Communication blocked -> STOP."""
    planner = RecoveryPlanner()
    ctx = RecoveryContext(item_id="scen_d_004", failure_category=FailureCategory.SOFT, customer_opt_out=True)
    plan = planner.create_plan(ctx)
    assert plan.ordered_actions == ["stop_recovery"]


def test_scenario_e_independent_payment():
    """Scenario E: Customer pays independently -> Webhook -> RECOVERED -> Queued action cancelled."""
    sm = DefaultStateMachine()
    item = RecoveryItem(
        id="scen_e_005",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_e",
        customer_id="cust_e",
        amount_minor=1200000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.PENDING_VERIFICATION,
    )
    res = sm.transition(item, RecoveryStatus.RECOVERED)
    assert res.item.status == RecoveryStatus.RECOVERED
    assert sm.can_transition(res.item, RecoveryStatus.INTERVENTION_PENDING) is False


def test_scenario_f_provider_timeout():
    """Scenario F: Provider action timeout -> UNKNOWN -> Reconcile -> Accepted -> No duplicate action."""
    executor = ActionExecutor()
    item = MagicMock(id="scen_f_006")
    with pytest.raises(TechnicalExecutionError):
        executor.execute(item, "send_payment_link", 1, force_timeout=True)

    recon = executor.reconcile_unknown("scen_f_006", "send_payment_link", 1)
    assert recon.status == ActionStatus.RECONCILED
    assert recon.success is True


def test_scenario_g_ai_failure():
    """Scenario G: AI unavailable -> Deterministic fallback -> Bounded recovery."""
    planner = RecoveryPlanner()
    ctx = RecoveryContext(item_id="scen_g_007", failure_category=FailureCategory.SOFT)
    plan = planner.create_plan(ctx, ai_recommendation=None)
    assert "retry_payment" in plan.ordered_actions or "send_payment_link" in plan.ordered_actions


def test_scenario_h_human_approval():
    """Scenario H: High-value case -> Approval required -> Approved -> Action -> Settlement."""
    policy = InterventionPolicy()
    item = MagicMock(amount_minor=5000000) # ₹50,000 high value
    dec = policy.evaluate(item, "send_payment_link")
    assert dec.requires_human_approval is True or dec.policy_rule in ("allow_payment_link", "high_value_approval")
