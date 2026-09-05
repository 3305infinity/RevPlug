from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.domain.models import RecoveryItem


class EventType:
    CASE_CREATED = "CASE_CREATED"
    CONTEXT_CAPTURED = "CONTEXT_CAPTURED"
    DIAGNOSIS_CREATED = "DIAGNOSIS_CREATED"
    CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
    AI_RECOMMENDATION_CREATED = "AI_RECOMMENDATION_CREATED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    SAFETY_EVALUATED = "SAFETY_EVALUATED"
    DECISION_MADE = "DECISION_MADE"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_ACCEPTED = "EXECUTION_ACCEPTED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    SETTLEMENT_RECEIVED = "SETTLEMENT_RECEIVED"
    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"
    FALLBACK_USED = "FALLBACK_USED"
    DUPLICATE_WEBHOOK_SKIPPED = "DUPLICATE_WEBHOOK_SKIPPED"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    recovery_item_id: str
    actor: str
    action: str
    reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""
    source: str = ""
    reason_code: str = ""
    context_hash: str = ""
    correlation_id: str = ""


class AuditLog(Protocol):
    """Append-only audit log for recovery item lifecycle events."""

    def log(
        self,
        recovery_item_id: str,
        actor: str,
        action: str,
        reason: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AuditEvent:
        ...

    def events_for(self, recovery_item_id: str) -> list[AuditEvent]:
        ...


class InMemoryAuditLog:
    """In-memory append-only audit log.

    Append-only is enforced by interface: no update or delete methods exist.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def log(
        self,
        recovery_item_id: str,
        actor: str,
        action: str,
        reason: str | None = None,
        metadata: dict[str, object] | None = None,
        event_type: str = "",
        source: str = "",
        reason_code: str = "",
        context_hash: str = "",
        correlation_id: str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            id=self._next_id(),
            recovery_item_id=recovery_item_id,
            actor=actor,
            action=action,
            reason=reason,
            metadata=metadata or {},
            event_type=event_type or metadata.get("event_type", "") if metadata else "",
            source=source or metadata.get("source", "") if metadata else "",
            reason_code=reason_code or metadata.get("reason_code", "") if metadata else "",
            context_hash=context_hash or metadata.get("context_hash", "") if metadata else "",
            correlation_id=correlation_id or metadata.get("correlation_id", "") if metadata else "",
        )
        self._events.append(event)
        return event

    def events_for(self, recovery_item_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.recovery_item_id == recovery_item_id]

    def append(self, event: AuditEvent) -> AuditEvent:
        """Append a pre-constructed audit event (used for tombstone events during clear)."""
        self._events.append(event)
        return event

    def _next_id(self) -> str:
        return f"audit_{len(self._events) + 1}"
