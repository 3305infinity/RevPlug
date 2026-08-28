from datetime import datetime, timezone

import pytest

from app.ledger.attempts import AttemptLedger, AttemptRecord, InMemoryAttemptLedger


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def test_record_attempt(utcnow):
    ledger = InMemoryAttemptLedger()
    record = AttemptRecord(
        recovery_item_id="ri_1",
        attempt_number=1,
        action="retry_payment",
        executed_at=utcnow,
        outcome="success",
    )
    result = ledger.record(record)
    assert result is record
    assert len(ledger.attempts_for("ri_1")) == 1


def test_multiple_attempts_for_same_item(utcnow):
    ledger = InMemoryAttemptLedger()
    for i in range(3):
        ledger.record(AttemptRecord(
            recovery_item_id="ri_1",
            attempt_number=i + 1,
            action="retry_payment",
            outcome="failed" if i < 2 else "success",
        ))
    attempts = ledger.attempts_for("ri_1")
    assert len(attempts) == 3
    assert attempts[0].attempt_number == 1
    assert attempts[2].outcome == "success"


def test_attempts_isolated_by_recovery_item_id(utcnow):
    ledger = InMemoryAttemptLedger()
    ledger.record(AttemptRecord(recovery_item_id="ri_1", attempt_number=1, action="retry_payment"))
    ledger.record(AttemptRecord(recovery_item_id="ri_2", attempt_number=1, action="send_reminder"))
    assert len(ledger.attempts_for("ri_1")) == 1
    assert len(ledger.attempts_for("ri_2")) == 1


def test_empty_ledger_returns_empty_list():
    ledger = InMemoryAttemptLedger()
    assert ledger.attempts_for("ri_1") == []


def test_record_with_metadata():
    ledger = InMemoryAttemptLedger()
    record = AttemptRecord(
        recovery_item_id="ri_1",
        attempt_number=1,
        action="retry_payment",
        metadata={"provider_idempotency_key": "retry:ri_1:1"},
    )
    ledger.record(record)
    attempts = ledger.attempts_for("ri_1")
    assert attempts[0].metadata["provider_idempotency_key"] == "retry:ri_1:1"


def test_record_without_optional_fields(utcnow):
    ledger = InMemoryAttemptLedger()
    record = AttemptRecord(
        recovery_item_id="ri_1",
        attempt_number=1,
        action="retry_payment",
    )
    ledger.record(record)
    assert ledger.attempts_for("ri_1")[0].scheduled_at is None
    assert ledger.attempts_for("ri_1")[0].executed_at is None
    assert ledger.attempts_for("ri_1")[0].outcome == ""
    assert ledger.attempts_for("ri_1")[0].failure_reason is None
