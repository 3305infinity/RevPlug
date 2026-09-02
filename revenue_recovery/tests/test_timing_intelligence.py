"""Tests for timing intelligence services.

Tests the TimingEvaluator and RecoveryScheduler services for WAIT decisions.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.timing_signals import TimingSignalType, TimingEvaluation
from app.services.timing_evaluator import TimingEvaluator
from app.services.recovery_scheduler import RecoveryScheduler


def make_item(item_id: str, **overrides):
    """Factory for creating test RecoveryItem instances."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"ext-{item_id}",
        customer_id="cust-1",
        amount_minor=10000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="soft_decline",
        metadata={"failure_category": "soft_decline"},
    )
    defaults.update(overrides)
    return RecoveryItem(**defaults)


class TestTimingEvaluator:
    """Tests for TimingEvaluator service."""

    def test_no_signals_when_fresh_item(self):
        """Fresh item with no history should have no active timing signals."""
        item = make_item("test-item-1")
        evaluator = TimingEvaluator()
        now_in_window = datetime(2026, 9, 2, 11, 0, 0, tzinfo=timezone.utc)
        result = evaluator.evaluate(item, wait_count=0, now=now_in_window)

        assert result.timing_decision == "RECOVER"
        assert result.reason_code == "no_timing_constraint"

    def test_active_promise_signal(self):
        """Active promise should block recovery until promised date."""
        from app.domain.models import PromiseStatus
        item = make_item("test-item-2", metadata={})

        class MockPromise:
            def __init__(self):
                self.id = "promise-1"
                self.item_id = "test-item-2"
                self.status = PromiseStatus.PROMISED
                self.promised_date = (datetime.now(timezone.utc) + timedelta(days=3)).date()

        class MockPromiseRepo:
            def by_item(self, item_id):
                return [MockPromise()] if item_id == "test-item-2" else []

        evaluator = TimingEvaluator()
        result = evaluator.evaluate(
            item,
            promises=MockPromiseRepo(),
            wait_count=0,
        )

        assert result.timing_decision == "WAIT", f"Expected WAIT, got {result.timing_decision}. Signals: {[(s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type, s.active) for s in result.signals]}"
        assert result.reason_code == "active_promise_wait"
        assert result.scheduled_for is not None
        active_signal = next((s for s in result.signals if s.signal_type == TimingSignalType.ACTIVE_PROMISE), None)
        assert active_signal is not None
        assert active_signal.active is True

    def test_contact_limit_window_blocks(self):
        """Contact limit reached should produce WAIT decision."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=3)
        item = make_item(
            "test-item-3",
            status=RecoveryStatus.INTERVENTION_EXECUTED,
            metadata={
                "failure_category": "soft_decline",
                "observations": [
                    {"action": "send_payment_link", "timestamp": old_time.isoformat()},
                    {"action": "send_reminder", "timestamp": old_time.isoformat()},
                    {"action": "alternate_channel", "timestamp": old_time.isoformat()},
                ],
            },
        )

        evaluator = TimingEvaluator(daily_contact_limit=2)
        result = evaluator.evaluate(item, wait_count=0, now=now)

        contact_signal = next((s for s in result.signals if s.signal_type == TimingSignalType.CONTACT_LIMIT_WINDOW), None)
        assert contact_signal is not None, f"No CONTACT_LIMIT_WINDOW signal found. Signals: {[(s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type, s.active) for s in result.signals]}"
        assert contact_signal.active is True
        assert result.timing_decision == "WAIT"
        assert result.reason_code == "contact_frequency_limit"

    def test_historical_window_for_soft_decline(self):
        """Soft decline outside 10-12 window should suggest waiting for optimal window."""
        item = make_item(
            "test-item-4",
            root_cause="insufficient_funds",
            metadata={"failure_category": "insufficient_funds"},
        )

        evaluator = TimingEvaluator()
        result = evaluator.evaluate(item, wait_count=0)

        hist_signal = next((s for s in result.signals if s.signal_type == TimingSignalType.HISTORICAL_SUCCESS_WINDOW), None)
        assert hist_signal is not None

    def test_max_wait_count_triggers_escalation(self):
        """Exceeding max wait count should trigger ESCALATE."""
        item = make_item("test-item-5", metadata={})

        evaluator = TimingEvaluator()
        result = evaluator.evaluate(item, wait_count=3)

        assert result.timing_decision == "ESCALATE"
        assert result.reason_code == "max_waits_exceeded"
        assert result.at_max_waits is True

    def test_scheduled_for_calculation(self):
        """scheduled_for should be properly calculated from active signals."""
        item = make_item(
            "test-item-6",
            metadata={
                "failure_category": "soft_decline",
                "observations": [
                    {"action": "send_payment_link", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()},
                ],
            },
        )

        evaluator = TimingEvaluator(cooldown_minutes=120)
        result = evaluator.evaluate(item, wait_count=0)

        assert result.scheduled_for is not None
        assert result.scheduled_for > datetime.now(timezone.utc)


class TestRecoveryScheduler:
    """Tests for RecoveryScheduler service."""

    def test_initial_wait_count_is_zero(self):
        """New item should have zero wait count."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s1", metadata={})

        eligible, record, escalation_reason = scheduler.evaluate_wait_eligibility(
            item,
            TimingEvaluation(
                item_id=item.id,
                timing_decision="WAIT",
                reason_code="test",
                reason="Test wait",
                scheduled_for=datetime.now(timezone.utc) + timedelta(hours=24),
            ),
        )

        assert eligible is True
        assert record.wait_count == 0
        assert escalation_reason is None

    def test_max_wait_count_blocks_further_waits(self):
        """At max wait count (3), further waits should be blocked."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s2", metadata={})

        evaluation = TimingEvaluation(
            item_id=item.id,
            timing_decision="WAIT",
            reason_code="test",
            reason="Test wait",
            scheduled_for=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        eligible, _, _ = scheduler.evaluate_wait_eligibility(item, evaluation)
        assert eligible is True

        scheduler.record_wait(item, evaluation)
        eligible, _, escalation_reason = scheduler.evaluate_wait_eligibility(item, evaluation)
        assert eligible is True
        assert escalation_reason is None

        scheduler.record_wait(item, evaluation)
        eligible, _, escalation_reason = scheduler.evaluate_wait_eligibility(item, evaluation)
        assert eligible is True

        scheduler.record_wait(item, evaluation)
        eligible, _, escalation_reason = scheduler.evaluate_wait_eligibility(item, evaluation)
        assert eligible is False
        assert escalation_reason is not None
        assert "max_waits_exceeded" in escalation_reason or "Maximum wait count" in escalation_reason

    def test_wait_horizon_exceeded_blocks(self):
        """Wait scheduled beyond 30 days should be blocked."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s3", metadata={})

        evaluation = TimingEvaluation(
            item_id=item.id,
            timing_decision="WAIT",
            reason_code="test",
            reason="Test wait",
            scheduled_for=datetime.now(timezone.utc) + timedelta(days=45),
        )

        eligible, _, escalation_reason = scheduler.evaluate_wait_eligibility(item, evaluation)
        assert eligible is False
        assert escalation_reason is not None
        assert "horizon" in escalation_reason.lower() or "30 days" in escalation_reason

    def test_record_wait_increments_count(self):
        """Recording a wait should increment wait_count."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s4", metadata={})

        evaluation = TimingEvaluation(
            item_id=item.id,
            timing_decision="WAIT",
            reason_code="test",
            reason="Test wait",
            scheduled_for=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        record = scheduler.record_wait(item, evaluation)
        assert record.wait_count == 1

        record = scheduler.record_wait(item, evaluation)
        assert record.wait_count == 2

    def test_reset_wait_clears_record(self):
        """Reset should clear wait tracking."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s5", metadata={})

        evaluation = TimingEvaluation(
            item_id=item.id,
            timing_decision="WAIT",
            reason_code="test",
            reason="Test wait",
            scheduled_for=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        scheduler.record_wait(item, evaluation)
        assert scheduler.get_wait_record(item.id) is not None

        result = scheduler.reset_wait(item.id)
        assert result is True
        assert scheduler.get_wait_record(item.id) is None

    def test_wait_summary_properties(self):
        """Wait summary should have correct computed properties."""
        scheduler = RecoveryScheduler()
        item = make_item("test-item-s6", metadata={})

        summary = scheduler.get_wait_summary(item.id)
        assert summary["wait_count"] == 0
        assert summary["wait_remaining"] == 3
        assert summary["at_max_waits"] is False
        assert summary["max_wait_count"] == 3
        assert summary["max_wait_horizon_days"] == 30
