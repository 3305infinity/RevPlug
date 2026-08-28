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
    assert decision.policy_rule == "allow_stop"
