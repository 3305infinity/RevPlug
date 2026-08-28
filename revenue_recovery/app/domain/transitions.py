from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from app.domain.models import RecoveryItem, RecoveryStatus


class InvalidTransitionError(Exception):
    """Raised when a state transition is not permitted."""


@dataclass(frozen=True, slots=True)
class TransitionResult:
    item: RecoveryItem
    applied: bool
    reason: str | None = None


class RecoveryStateMachine(Protocol):
    """Enforces legal state transitions for RecoveryItem."""

    def transition(self, item: RecoveryItem, target: RecoveryStatus) -> TransitionResult:
        ...


# Legal transitions: from -> set of allowed targets
_LEGAL_TRANSITIONS: dict[RecoveryStatus, set[RecoveryStatus]] = {
    RecoveryStatus.DETECTED: {RecoveryStatus.DIAGNOSED, RecoveryStatus.STOPPED},
    RecoveryStatus.DIAGNOSED: {
        RecoveryStatus.QUEUED,
        RecoveryStatus.ESCALATED,
        RecoveryStatus.STOPPED,
    },
    RecoveryStatus.QUEUED: {
        RecoveryStatus.INTERVENTION_PENDING,
        RecoveryStatus.STOPPED,
        RecoveryStatus.ESCALATED,
    },
    RecoveryStatus.INTERVENTION_PENDING: {
        RecoveryStatus.INTERVENTION_EXECUTED,
        RecoveryStatus.ESCALATED,
        RecoveryStatus.STOPPED,
    },
    RecoveryStatus.INTERVENTION_EXECUTED: {
        RecoveryStatus.RECOVERED,
        RecoveryStatus.FAILED,
    },
    RecoveryStatus.FAILED: {RecoveryStatus.QUEUED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED},
    RecoveryStatus.RECOVERED: set(),
    RecoveryStatus.ESCALATED: set(),
    RecoveryStatus.STOPPED: set(),
}

_TERMINAL_STATES: set[RecoveryStatus] = {
    RecoveryStatus.RECOVERED,
    RecoveryStatus.ESCALATED,
    RecoveryStatus.STOPPED,
}


class DefaultStateMachine:
    """Deterministic state machine for RecoveryItem.

    Terminal states cannot be transitioned out of.
    Unknown transitions raise InvalidTransitionError.
    """

    def transition(self, item: RecoveryItem, target: RecoveryStatus) -> TransitionResult:
        if item.status in _TERMINAL_STATES:
            return TransitionResult(
                item=item,
                applied=False,
                reason=f"Cannot transition from terminal state {item.status.value}",
            )

        allowed = _LEGAL_TRANSITIONS.get(item.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Illegal transition: {item.status.value} -> {target.value}"
            )

        updated = replace(item, status=target)
        return TransitionResult(item=updated, applied=True, reason=f"{item.status.value} -> {target.value}")

    def is_terminal(self, item: RecoveryItem) -> bool:
        return item.status in _TERMINAL_STATES

    def can_transition(self, item: RecoveryItem, target: RecoveryStatus) -> bool:
        if item.status in _TERMINAL_STATES:
            return False
        return target in _LEGAL_TRANSITIONS.get(item.status, set())
