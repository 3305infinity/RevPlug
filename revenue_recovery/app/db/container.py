from __future__ import annotations

import os
from dataclasses import dataclass

from app.audit.models import AuditLog, InMemoryAuditLog
from app.db.decision_repository import (
    InMemoryRecoveryDecisionRepository,
    RecoveryDecisionRepository,
)
from app.db.postgres_repositories import (
    PostgresAuditLog,
    PostgresAttemptLedger,
    PostgresIdempotencyStore,
    PostgresProviderEventRepository,
    PostgresPromiseRepository,
    PostgresRecoveryItemRepository,
    PostgresRecoveryOutcomeRepository,
)
from app.db.repositories import InMemoryRecoveryItemRepository, RecoveryItemRepository
from app.db.session import PostgresConnection, create_connection
from app.idempotency.store import IdempotencyStore, InMemoryIdempotencyStore
from app.ledger.attempts import AttemptLedger, InMemoryAttemptLedger


@dataclass
class PersistenceContainer:
    """Holds all persistence dependencies for the application."""

    recovery_items: RecoveryItemRepository
    idempotency: IdempotencyStore
    audit_log: AuditLog
    attempts: AttemptLedger
    decisions: RecoveryDecisionRepository
    outcomes: "RecoveryOutcomeRepository"
    promises: "PromiseRepository"
    provider_events: "ProviderEventRepository"


def create_persistence_container(mode: str | None = None) -> PersistenceContainer:
    """Create a persistence container based on the configured mode.

    Args:
        mode: "memory" or "postgres". If None, reads PERSISTENCE_MODE env var,
              defaulting to "memory".
    """
    if mode is None:
        mode = os.environ.get("PERSISTENCE_MODE", "memory")

    if mode == "memory":
        return PersistenceContainer(
            recovery_items=InMemoryRecoveryItemRepository(),
            idempotency=InMemoryIdempotencyStore(),
            audit_log=InMemoryAuditLog(),
            attempts=InMemoryAttemptLedger(),
            decisions=InMemoryRecoveryDecisionRepository(),
            outcomes=_InMemoryRecoveryOutcomeRepository(),
            promises=_InMemoryPromiseRepository(),
            provider_events=_InMemoryProviderEventRepository(),
        )

    if mode == "postgres":
        conn = create_connection()
        from app.db.postgres_repositories import PostgresRecoveryDecisionRepository
        return PersistenceContainer(
            recovery_items=PostgresRecoveryItemRepository(conn),
            idempotency=PostgresIdempotencyStore(conn),
            audit_log=PostgresAuditLog(conn),
            attempts=PostgresAttemptLedger(conn),
            decisions=PostgresRecoveryDecisionRepository(conn),
            outcomes=PostgresRecoveryOutcomeRepository(conn),
            promises=PostgresPromiseRepository(conn),
            provider_events=PostgresProviderEventRepository(conn),
        )

    raise ValueError(f"Unknown PERSISTENCE_MODE: {mode!r}. Use 'memory' or 'postgres'.")


# ---------------------------------------------------------------------------
# In-memory implementations for new canonical repositories
# ---------------------------------------------------------------------------

class _InMemoryRecoveryOutcomeRepository:
    """In-memory outcome repository for unit tests and local development."""

    def __init__(self) -> None:
        self._outcomes: dict[str, dict] = {}

    def save(self, outcome) -> None:
        self._outcomes[outcome.recovery_item_id] = outcome

    def get_for_item(self, recovery_item_id: str):
        from app.domain.models import RecoveryOutcome
        data = self._outcomes.get(recovery_item_id)
        return data


class _InMemoryPromiseRepository:
    """In-memory promise repository for unit tests and local development."""

    def __init__(self) -> None:
        self._promises: dict[str, dict] = {}

    def save(self, promise) -> None:
        self._promises[promise.recovery_item_id] = promise

    def get_for_item(self, recovery_item_id: str):
        data = self._promises.get(recovery_item_id)
        return data


class _InMemoryProviderEventRepository:
    """In-memory provider event repository for unit tests and local development."""

    def __init__(self) -> None:
        self._events: dict[str, dict] = {}

    def _store_key(self, provider: str, provider_event_id: str) -> str:
        return f"{provider}:{provider_event_id}"

    def try_insert(self, event) -> tuple[bool, object]:
        store_key = self._store_key(event.provider, event.provider_event_id)
        if store_key in self._events:
            return False, self._dict_to_event(self._events[store_key])
        self._events[store_key] = self._event_to_dict(event)
        return True, event

    def save(self, event) -> None:
        store_key = self._store_key(event.provider, event.provider_event_id)
        if store_key not in self._events:
            self._events[store_key] = self._event_to_dict(event)

    def get_by_provider_event(self, provider: str, provider_event_id: str):
        data = self._events.get(self._store_key(provider, provider_event_id))
        return self._dict_to_event(data) if data else None

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        store_key = self._store_key(provider, provider_event_id)
        data = self._events.get(store_key)
        if data:
            data["processing_status"] = "processed"
            data["processed_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            data["recovery_item_id"] = recovery_item_id

    def _event_to_dict(self, event) -> dict:
        return {
            "id": event.id,
            "provider": event.provider,
            "provider_event_id": event.provider_event_id,
            "received_at": event.received_at,
            "event_type": event.event_type,
            "raw_payload": event.raw_payload,
            "processing_status": event.processing_status,
            "processed_at": event.processed_at,
            "recovery_item_id": event.recovery_item_id,
            "error_message": event.error_message,
            "metadata": event.metadata,
        }

    def _dict_to_event(self, data: dict):
        from app.domain.models import ProviderEvent
        return ProviderEvent(
            id=data["id"],
            provider=data["provider"],
            provider_event_id=data["provider_event_id"],
            received_at=data["received_at"],
            event_type=data["event_type"],
            raw_payload=data["raw_payload"],
            processing_status=data.get("processing_status", "pending"),
            processed_at=data.get("processed_at"),
            recovery_item_id=data.get("recovery_item_id"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Protocols for new repositories
# ---------------------------------------------------------------------------

class RecoveryOutcomeRepository:
    """Persistence boundary for RecoveryOutcome."""

    def save(self, outcome) -> None:
        ...

    def get_for_item(self, recovery_item_id: str):
        ...


class PromiseRepository:
    """Persistence boundary for Promise."""

    def save(self, promise) -> None:
        ...

    def get_for_item(self, recovery_item_id: str):
        ...


class ProviderEventRepository:
    """Persistence boundary for ProviderEvent."""

    def try_insert(self, event) -> tuple[bool, object]:
        ...

    def save(self, event) -> None:
        ...

    def get_by_provider_event(self, provider: str, provider_event_id: str):
        ...

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        ...
