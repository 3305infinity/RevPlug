from datetime import datetime, timezone

import pytest

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.transitions import (
    DefaultStateMachine,
    InvalidTransitionError,
    RecoveryStateMachine,
)


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def base_item(utcnow, status=RecoveryStatus.DETECTED):
    return RecoveryItem(
        id="ri_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_1",
        customer_id="C_1",
        amount_minor=10000,
        currency="INR",
        created_at=utcnow,
        status=status,
    )


def test_detected_to_diagnosed(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(base_item(utcnow), RecoveryStatus.DIAGNOSED)
    assert result.applied is True
    assert result.item.status == RecoveryStatus.DIAGNOSED


def test_diagnosed_to_queued(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(base_item(utcnow, RecoveryStatus.DIAGNOSED), RecoveryStatus.QUEUED)
    assert result.applied is True
    assert result.item.status == RecoveryStatus.QUEUED


def test_queued_to_intervention_pending(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(base_item(utcnow, RecoveryStatus.QUEUED), RecoveryStatus.INTERVENTION_PENDING)
    assert result.applied is True
    assert result.item.status == RecoveryStatus.INTERVENTION_PENDING


def test_intervention_pending_to_executed(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(
        base_item(utcnow, RecoveryStatus.INTERVENTION_PENDING),
        RecoveryStatus.INTERVENTION_EXECUTED,
    )
    assert result.applied is True
    assert result.item.status == RecoveryStatus.INTERVENTION_EXECUTED


def test_intervention_executed_to_recovered(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(
        base_item(utcnow, RecoveryStatus.INTERVENTION_EXECUTED),
        RecoveryStatus.RECOVERED,
    )
    assert result.applied is True
    assert result.item.status == RecoveryStatus.RECOVERED


def test_intervention_executed_to_failed(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(
        base_item(utcnow, RecoveryStatus.INTERVENTION_EXECUTED),
        RecoveryStatus.FAILED,
    )
    assert result.applied is True
    assert result.item.status == RecoveryStatus.FAILED


def test_failed_to_queued_is_allowed(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(
        base_item(utcnow, RecoveryStatus.FAILED),
        RecoveryStatus.QUEUED,
    )
    assert result.applied is True
    assert result.item.status == RecoveryStatus.QUEUED


def test_diagnosed_to_escalated(utcnow):
    sm = DefaultStateMachine()
    result = sm.transition(
        base_item(utcnow, RecoveryStatus.DIAGNOSED),
        RecoveryStatus.ESCALATED,
    )
    assert result.applied is True
    assert result.item.status == RecoveryStatus.ESCALATED


def test_recovered_is_terminal(utcnow):
    sm = DefaultStateMachine()
    item = base_item(utcnow, RecoveryStatus.RECOVERED)
    result = sm.transition(item, RecoveryStatus.QUEUED)
    assert result.applied is False
    assert "terminal" in result.reason


def test_stopped_is_terminal(utcnow):
    sm = DefaultStateMachine()
    item = base_item(utcnow, RecoveryStatus.STOPPED)
    result = sm.transition(item, RecoveryStatus.DIAGNOSED)
    assert result.applied is False
    assert "terminal" in result.reason


def test_escalated_is_terminal(utcnow):
    sm = DefaultStateMachine()
    item = base_item(utcnow, RecoveryStatus.ESCALATED)
    result = sm.transition(item, RecoveryStatus.QUEUED)
    assert result.applied is False


def test_invalid_transition_raises(utcnow):
    sm = DefaultStateMachine()
    with pytest.raises(InvalidTransitionError, match="Illegal transition"):
        sm.transition(base_item(utcnow), RecoveryStatus.RECOVERED)


def test_detected_to_recovered_raises(utcnow):
    sm = DefaultStateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.transition(base_item(utcnow), RecoveryStatus.RECOVERED)


def test_queued_to_recovered_raises(utcnow):
    sm = DefaultStateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.transition(base_item(utcnow, RecoveryStatus.QUEUED), RecoveryStatus.RECOVERED)


def test_is_terminal_true_for_recovered(utcnow):
    sm = DefaultStateMachine()
    assert sm.is_terminal(base_item(utcnow, RecoveryStatus.RECOVERED)) is True


def test_is_terminal_true_for_stopped(utcnow):
    sm = DefaultStateMachine()
    assert sm.is_terminal(base_item(utcnow, RecoveryStatus.STOPPED)) is True


def test_is_terminal_false_for_detected(utcnow):
    sm = DefaultStateMachine()
    assert sm.is_terminal(base_item(utcnow)) is False


def test_can_transition_returns_false_for_terminal(utcnow):
    sm = DefaultStateMachine()
    assert sm.can_transition(base_item(utcnow, RecoveryStatus.RECOVERED), RecoveryStatus.QUEUED) is False


def test_can_transition_returns_true_for_legal(utcnow):
    sm = DefaultStateMachine()
    assert sm.can_transition(base_item(utcnow), RecoveryStatus.DIAGNOSED) is True


def test_can_transition_returns_false_for_illegal(utcnow):
    sm = DefaultStateMachine()
    assert sm.can_transition(base_item(utcnow), RecoveryStatus.RECOVERED) is False
