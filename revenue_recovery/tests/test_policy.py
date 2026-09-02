from datetime import datetime, timezone

import pytest

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.policies.engine import InterventionPolicy, PolicyDecision


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def base_item(utcnow, **overrides):
    data = {
        "id": "ri_1",
        "source_type": SourceType.PAYMENT_FAILURE,
        "external_id": "ext_1",
        "customer_id": "C_1",
        "amount_minor": 10000,
        "currency": "INR",
        "created_at": utcnow,
        "status": RecoveryStatus.DETECTED,
        "root_cause": "temporary_processing",
        "recovery_probability": 0.4,
        "metadata": {},
    }
    data.update(overrides)
    return RecoveryItem(**data)


def test_retry_allowed_within_budget(utcnow):
    policy = InterventionPolicy(max_retry_attempts=2)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is True
    assert decision.requires_human_approval is False
    assert decision.policy_rule == "allow_retry"


def test_retry_blocked_when_budget_exhausted(utcnow):
    policy = InterventionPolicy(max_retry_attempts=2)
    item = base_item(utcnow, metadata={"attempt_count": 2})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert decision.policy_rule == "retry_limit"
    assert "2/2" in decision.reason


def test_hard_failure_blocks_retry(utcnow):
    policy = InterventionPolicy(max_retry_attempts=3)
    item = base_item(utcnow, root_cause="hard_decline", metadata={"attempt_count": 0})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert decision.policy_rule == "block_hard_failure"


def test_fraud_blocks_retry(utcnow):
    policy = InterventionPolicy(max_retry_attempts=3)
    item = base_item(utcnow, root_cause="fraud", metadata={"attempt_count": 0})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_authentication_required_blocks_retry(utcnow):
    policy = InterventionPolicy(max_retry_attempts=3)
    item = base_item(utcnow, root_cause="authentication_required", metadata={"attempt_count": 0})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_security_or_fraud_blocks_retry(utcnow):
    policy = InterventionPolicy(max_retry_attempts=3)
    item = base_item(utcnow, root_cause="security_or_fraud", metadata={"attempt_count": 0})
    decision = policy.evaluate(item, "retry_payment")
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_discount_within_autonomous_limit(utcnow):
    policy = InterventionPolicy(autonomous_discount_minor=5000)
    item = base_item(utcnow, metadata={"discount_minor": 3000})
    decision = policy.evaluate(item, "send_discount")
    assert decision.allowed is True
    assert decision.requires_human_approval is False
    assert decision.policy_rule == "allow_discount"


def test_discount_above_autonomous_limit_requires_approval(utcnow):
    policy = InterventionPolicy(autonomous_discount_minor=5000)
    item = base_item(utcnow, metadata={"discount_minor": 6000})
    decision = policy.evaluate(item, "send_discount")
    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert decision.policy_rule == "discount_ceiling"


def test_opted_out_customer_blocks_outbound(utcnow):
    policy = InterventionPolicy(opted_out_customer_ids=frozenset({"C_BLOCKED"}))
    item = base_item(utcnow, customer_id="C_BLOCKED")
    decision = policy.evaluate(item, "send_reminder")
    assert decision.allowed is False
    assert decision.requires_human_approval is False
    assert decision.policy_rule == "opt_out_block"


def test_opted_out_customer_allows_non_outbound(utcnow):
    policy = InterventionPolicy(opted_out_customer_ids=frozenset({"C_BLOCKED"}))
    item = base_item(utcnow, customer_id="C_BLOCKED")
    decision = policy.evaluate(item, "stop_recovery")
    assert decision.allowed is True


def test_unknown_action_default_deny(utcnow):
    policy = InterventionPolicy()
    item = base_item(utcnow)
    decision = policy.evaluate(item, "unknown_action")
    assert decision.allowed is False
    assert decision.requires_human_approval is False
    assert decision.policy_rule == "default_deny"
    assert "unknown_action" in decision.reason


def test_contact_within_budget(utcnow):
    policy = InterventionPolicy()
    item = base_item(utcnow, metadata={"contact_attempt_count": 0, "max_contacts": 5})
    decision = policy.evaluate(item, "send_reminder")
    assert decision.allowed is True
    assert decision.policy_rule == "allow_outbound"


def test_contact_budget_exhausted_requires_approval(utcnow):
    policy = InterventionPolicy()
    item = base_item(utcnow, metadata={"contact_attempt_count": 5, "max_contacts": 5})
    decision = policy.evaluate(item, "send_reminder")
    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert decision.policy_rule == "contact_limit"


def test_max_retry_attempts_negative_raises():
    with pytest.raises(ValueError, match="max_retry_attempts must be non-negative"):
        InterventionPolicy(max_retry_attempts=-1)


def test_autonomous_discount_negative_raises():
    with pytest.raises(ValueError, match="autonomous_discount_minor must be non-negative"):
        InterventionPolicy(autonomous_discount_minor=-1)


def test_stop_recovery_always_allowed(utcnow):
    policy = InterventionPolicy()
    item = base_item(utcnow)
    decision = policy.evaluate(item, "stop_recovery")
    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_policy_config_store_versioning():
    """Verifies policy config updates spawn explicit new versions (v1.0 -> v1.1)."""
    from app.services.policy_config_service import PolicyConfigStore
    store = PolicyConfigStore.get_instance()
    cfg1 = store.get_config()
    assert cfg1.version == "v1.0"

    cfg2 = store.update_config({"max_retries": 4})
    assert cfg2.version == "v1.1"
    assert cfg2.max_retries == 4
    assert len(store.get_history()) >= 2


def test_policy_config_api_endpoints():
    """Verifies GET and PUT /api/policy-config endpoints."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    resp_get = client.get("/api/policy-config")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert "version" in data
    assert "preview_summary" in data

    resp_put = client.put("/api/policy-config", json={"max_retries": 5})
    assert resp_put.status_code == 200
    updated_data = resp_put.json()
    assert updated_data["max_retries"] == 5
    assert updated_data["version"] != data["version"]


def test_human_review_action_resumes_playbook():
    """Verifies POST /api/reviews/{id}/action validates human decision through policy engine and resumes playbook."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    container = app.state.container
    item = RecoveryItem(
        id="item_rev_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_rev_101",
        customer_id="cust_rev_101",
        amount_minor=8400000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.ESCALATED,
        root_cause="dispute",
        metadata={"source": "manual_case", "is_synthetic": False},
    )
    container.recovery_items.save(item)

    resp_act = client.post(f"/api/reviews/{item.id}/action", json={"action": "approve"})
    assert resp_act.status_code == 200
    res = resp_act.json()

    assert res["item_id"] == item.id
    assert res["action_taken"] == "approve"
    assert res["policy_validated"] is True
    assert res["playbook_resumed"] is True

    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.INTERVENTION_PENDING


def test_ev_gate_blocks_non_positive_ev():
    """Verify that actions with non-positive EV are blocked by EV gate."""
    from app.audit.models import InMemoryAuditLog
    from app.domain.context import RecoveryContext
    from app.domain.failures import FailureCategory
    from app.policies.guard import DefaultRecoveryGuard
    from app.policies.stopping_rules import StoppingRules
    from app.scoring.expected_value import ExpectedValueScorer
    from app.services.recovery_orchestrator import RecoveryOrchestrator

    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(
            stopping_rules=StoppingRules(),
            policy_engine=InterventionPolicy(),
        ),
    )

    item = RecoveryItem(
        id="test_ev_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_1",
        customer_id="cust_1",
        amount_minor=10,
        currency="INR",
        created_at=None,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
    )

    context = RecoveryContext(
        item_id=item.id,
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=10,
        currency="INR",
        expected_recovery_value=0,
        customer_opt_out=False,
    )

    from app.agents.decision_agent import MockRecoveryDecisionAgent
    orchestrator._agent = MockRecoveryDecisionAgent()

    result = orchestrator.run(item, context)

    assert result.safety_decision == "STOP"
    ev_events = [e for e in result.audit_events if e.action == "ev_check_failed"]
    assert len(ev_events) == 1
    assert ev_events[0].metadata["rule"] == "ev_gate_enforcement"


def test_human_approval_re_evaluates_safety_guard():
    """Verify human approval re-checks stopping rules on fresh state."""
    from app.db.container import create_persistence_container
    from app.policies.guard import DefaultRecoveryGuard
    from app.policies.stopping_rules import StoppingRules

    container = create_persistence_container(mode="memory")

    item = RecoveryItem(
        id="item_opted_out",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_opt",
        customer_id="cust_opted_out",
        amount_minor=10000,
        currency="INR",
        created_at=None,
        status=RecoveryStatus.INTERVENTION_PENDING,
        root_cause="soft",
        metadata={"customer_opted_out": True},
    )
    container.recovery_items.save(item)

    policy = InterventionPolicy(opted_out_customer_ids=frozenset(["cust_opted_out"]))
    stopping = StoppingRules(opted_out_customer_ids=frozenset(["cust_opted_out"]))
    guard = DefaultRecoveryGuard(stopping_rules=stopping, policy_engine=policy)

    decision = guard.evaluate(item, "send_customer_message", container=container)

    assert not decision.allowed
    assert decision.decision_type == "STOP"
    assert decision.reason_code == "customer_opted_out"
