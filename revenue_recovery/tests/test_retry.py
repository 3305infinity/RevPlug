from datetime import datetime, timezone

import pytest

from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.policies.retry import DefaultRetryPolicy, RetryDecision


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
        "metadata": {},
    }
    data.update(overrides)
    return RecoveryItem(**data)


def test_attempt_1_allowed(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item)
    assert decision.allowed is True
    assert decision.max_attempts == 3
    assert decision.policy_rule == "allow_retry"


def test_attempt_2_allowed(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 1})
    decision = policy.evaluate(item)
    assert decision.allowed is True


def test_attempt_3_allowed(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 2})
    decision = policy.evaluate(item)
    assert decision.allowed is True


def test_attempt_4_denied(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 3})
    decision = policy.evaluate(item)
    assert decision.allowed is False
    assert decision.policy_rule == "retry_limit"
    assert "3/3" in decision.reason


def test_hard_failure_not_retryable(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item, category=FailureCategory.HARD)
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_fraud_not_retryable(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item, category=FailureCategory.FRAUD)
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_authentication_required_not_retryable(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item, category=FailureCategory.AUTHENTICATION_REQUIRED)
    assert decision.allowed is False
    assert decision.policy_rule == "block_hard_failure"


def test_soft_failure_allowed_within_budget(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 1})
    decision = policy.evaluate(item, category=FailureCategory.SOFT)
    assert decision.allowed is True


def test_unknown_failure_allowed_within_budget(utcnow):
    policy = DefaultRetryPolicy(max_attempts=3)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item, category=FailureCategory.UNKNOWN)
    assert decision.allowed is True


def test_max_attempts_zero_denies_immediately(utcnow):
    policy = DefaultRetryPolicy(max_attempts=0)
    item = base_item(utcnow, metadata={"attempt_count": 0})
    decision = policy.evaluate(item)
    assert decision.allowed is False
    assert decision.policy_rule == "retry_limit"


def test_negative_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts must be non-negative"):
        DefaultRetryPolicy(max_attempts=-1)


def test_default_max_attempts_is_three():
    policy = DefaultRetryPolicy()
    assert policy._max_attempts == 3
