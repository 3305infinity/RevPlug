from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    recovery_item_id: str
    actor: str
    action: str
    reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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
    ) -> AuditEvent:
        event = AuditEvent(
            id=self._next_id(),
            recovery_item_id=recovery_item_id,
            actor=actor,
            action=action,
            reason=reason,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def events_for(self, recovery_item_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.recovery_item_id == recovery_item_id]

    def _next_id(self) -> str:
        return f"audit_{len(self._events) + 1}"
