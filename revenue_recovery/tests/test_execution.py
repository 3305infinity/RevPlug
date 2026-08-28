from __future__ import annotations

import pytest

from app.interventions.executor import ExecutionResult, SimulatedRecoveryExecutor
from app.policies.retry import DefaultRetryPolicy
from app.domain.escalation import Escalation, EscalationReason


# ---------------------------------------------------------------------------
# Simulated Executor
# ---------------------------------------------------------------------------

class TestSimulatedExecutor:
    def test_success_scenario(self):
        executor = SimulatedRecoveryExecutor()
        result = executor.execute(self._item(), "retry_payment", attempt_number=1, scenario="success")
        assert result.success is True
        assert result.action == "retry_payment"
        assert result.attempt_number == 1
        assert result.retry_eligible is False

    def test_temporary_failure_scenario(self):
        executor = SimulatedRecoveryExecutor()
        result = executor.execute(self._item(), "retry_payment", attempt_number=1, scenario="temporary_failure")
        assert result.success is False
        assert result.retry_eligible is True
        assert result.error_code == "temporary_failure"

    def test_permanent_failure_scenario(self):
        executor = SimulatedRecoveryExecutor()
        result = executor.execute(self._item(), "retry_payment", attempt_number=1, scenario="permanent_failure")
        assert result.success is False
        assert result.retry_eligible is False
        assert result.error_code == "permanent_failure"

    def test_default_scenario_is_success(self):
        executor = SimulatedRecoveryExecutor()
        result = executor.execute(self._item(), "retry_payment", attempt_number=1)
        assert result.success is True

    def test_unknown_scenario_defaults_to_success(self):
        executor = SimulatedRecoveryExecutor()
        result = executor.execute(self._item(), "retry_payment", attempt_number=1, scenario="nonsense")
        assert result.success is True

    def _item(self):
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        return RecoveryItem(
            id="pay_test", source_type=SourceType.PAYMENT_FAILURE, external_id="evt_test",
            customer_id="cust_test", amount_minor=50000, currency="INR",
            created_at=__import__("datetime").datetime.now(), status=RecoveryStatus.QUEUED,
        )


# ---------------------------------------------------------------------------
# Retry Policy with Exponential Backoff
# ---------------------------------------------------------------------------

class TestRetryPolicy:
    def test_first_retry_allowed(self):
        policy = DefaultRetryPolicy(max_attempts=3, base_delay_seconds=3600)
        item = self._make_item(attempt_count=0)
        decision = policy.evaluate(item)
        assert decision.allowed is True
        assert decision.attempt_number == 1
        assert decision.next_attempt_at is not None

    def test_second_retry_allowed(self):
        policy = DefaultRetryPolicy(max_attempts=3, base_delay_seconds=3600)
        item = self._make_item(attempt_count=1)
        decision = policy.evaluate(item)
        assert decision.allowed is True
        assert decision.attempt_number == 2

    def test_third_retry_allowed(self):
        policy = DefaultRetryPolicy(max_attempts=3, base_delay_seconds=3600)
        item = self._make_item(attempt_count=2)
        decision = policy.evaluate(item)
        assert decision.allowed is True
        assert decision.attempt_number == 3

    def test_fourth_retry_denied(self):
        policy = DefaultRetryPolicy(max_attempts=3, base_delay_seconds=3600)
        item = self._make_item(attempt_count=3)
        decision = policy.evaluate(item)
        assert decision.allowed is False
        assert decision.policy_rule == "retry_limit"

    def test_hard_failure_not_retried(self):
        from app.domain.failures import FailureCategory
        policy = DefaultRetryPolicy(max_attempts=3)
        item = self._make_item(attempt_count=0)
        decision = policy.evaluate(item, category=FailureCategory.HARD)
        assert decision.allowed is False
        assert decision.policy_rule == "block_hard_failure"

    def test_fraud_not_retried(self):
        from app.domain.failures import FailureCategory
        policy = DefaultRetryPolicy(max_attempts=3)
        item = self._make_item(attempt_count=0)
        decision = policy.evaluate(item, category=FailureCategory.FRAUD)
        assert decision.allowed is False

    def test_authentication_not_retried(self):
        from app.domain.failures import FailureCategory
        policy = DefaultRetryPolicy(max_attempts=3)
        item = self._make_item(attempt_count=0)
        decision = policy.evaluate(item, category=FailureCategory.AUTHENTICATION_REQUIRED)
        assert decision.allowed is False

    def test_exponential_backoff(self):
        policy = DefaultRetryPolicy(max_attempts=4, base_delay_seconds=3600)
        from datetime import datetime, timezone
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # Attempt 1: 3600 * 2^0 = 3600
        item0 = self._make_item(attempt_count=0)
        d0 = policy.evaluate(item0, occurred_at=now)
        assert d0.next_attempt_at is not None
        assert (d0.next_attempt_at - now).total_seconds() == 3600
        # Attempt 2: 3600 * 2^1 = 7200
        item1 = self._make_item(attempt_count=1)
        d1 = policy.evaluate(item1, occurred_at=now)
        assert (d1.next_attempt_at - now).total_seconds() == 7200
        # Attempt 3: 3600 * 2^2 = 14400
        item2 = self._make_item(attempt_count=2)
        d2 = policy.evaluate(item2, occurred_at=now)
        assert (d2.next_attempt_at - now).total_seconds() == 14400

    def test_max_delay_cap(self):
        policy = DefaultRetryPolicy(max_attempts=10, base_delay_seconds=3600, max_delay_seconds=100000)
        from datetime import datetime, timezone
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # Attempt 5: 3600 * 2^4 = 57600 (under cap)
        item4 = self._make_item(attempt_count=4)
        d4 = policy.evaluate(item4, occurred_at=now)
        assert (d4.next_attempt_at - now).total_seconds() == 57600
        # Attempt 6: 3600 * 2^5 = 115200 (over cap → capped at 100000)
        item5 = self._make_item(attempt_count=5)
        d5 = policy.evaluate(item5, occurred_at=now)
        assert (d5.next_attempt_at - now).total_seconds() == 100000

    def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts must be non-negative"):
            DefaultRetryPolicy(max_attempts=-1)

    def _make_item(self, attempt_count: int):
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        return RecoveryItem(
            id="pay_test",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_test",
            customer_id="cust_test",
            amount_minor=50000,
            currency="INR",
            created_at=__import__("datetime").datetime.now(),
            status=RecoveryStatus.QUEUED,
            metadata={"attempt_count": attempt_count},
        )


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------

class TestEscalation:
    def test_escalation_creation(self):
        esc = Escalation(
            reason=EscalationReason.RETRY_EXHAUSTED,
            message="Retry exhausted",
            item_id="pay_001",
        )
        assert esc.reason == EscalationReason.RETRY_EXHAUSTED
        assert esc.item_id == "pay_001"
