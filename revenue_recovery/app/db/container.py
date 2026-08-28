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
    PostgresRecoveryItemRepository,
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
        )

    raise ValueError(f"Unknown PERSISTENCE_MODE: {mode!r}. Use 'memory' or 'postgres'.")
