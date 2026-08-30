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
    PostgresRecoveryJobRepository,
)
from app.worker.job_repository import InMemoryRecoveryJobRepository
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
    users: "object | None" = None
    sessions: "object | None" = None
    jobs: "object | None" = None  # RecoveryJobRepository (Stage 7 async worker)
    batches: "object | None" = None  # InMemoryBatchRepository (Stage 8 batch recovery)

    def reset_demo_data(self) -> int:
        """Permanently deletes all synthetic data marked for demos."""
        # 1. PostgreSQL mode
        if hasattr(self.recovery_items, "_conn"):
            conn = getattr(self.recovery_items, "_conn")
            with conn._conn.cursor() as cur:
                cur.execute("SELECT id FROM recovery_items WHERE metadata->>'is_synthetic' = 'true'")
                rows = cur.fetchall()
                if not rows:
                    return 0
                item_ids = tuple(row[0] for row in rows)

                cur.execute("DELETE FROM recovery_outcomes WHERE recovery_item_id IN %s", (item_ids,))
                cur.execute("DELETE FROM promises WHERE recovery_item_id IN %s", (item_ids,))
                cur.execute("DELETE FROM audit_log WHERE recovery_item_id IN %s", (item_ids,))
                cur.execute("DELETE FROM attempts WHERE recovery_item_id IN %s", (item_ids,))
                cur.execute("DELETE FROM recovery_decisions WHERE recovery_item_id IN %s", (item_ids,))
                cur.execute("DELETE FROM recovery_items WHERE id IN %s", (item_ids,))
                conn._conn.commit()
                return len(item_ids)

        # 2. In-Memory mode
        count = 0
        if hasattr(self.recovery_items, "_items"):
            items_repo = getattr(self.recovery_items, "_items")
            synthetic_ids = {k for k, v in items_repo.items() if v.metadata and v.metadata.get("is_synthetic") is True}
            count = len(synthetic_ids)
            for k in synthetic_ids:
                del items_repo[k]
            
            # Clean dependent in-memory stores
            if hasattr(self.audit_log, "_events"):
                events = getattr(self.audit_log, "_events")
                events[:] = [e for e in events if e.recovery_item_id not in synthetic_ids]
            if hasattr(self.attempts, "_records"):
                records = getattr(self.attempts, "_records")
                records[:] = [r for r in records if r.recovery_item_id not in synthetic_ids]
            if hasattr(self.outcomes, "_outcomes"):
                outcomes = getattr(self.outcomes, "_outcomes")
                for k in synthetic_ids:
                    outcomes.pop(k, None)
            if hasattr(self.promises, "_by_item"):
                promises_by_item = getattr(self.promises, "_by_item")
                promises_by_id = getattr(self.promises, "_by_id")
                for k in synthetic_ids:
                    p = promises_by_item.pop(k, None)
                    if p:
                        if isinstance(p, dict):
                            promises_by_id.pop(p.get("id"), None)
                        else:
                            promises_by_id.pop(p.id, None)

        return count


def create_persistence_container(mode: str | None = None) -> PersistenceContainer:
    """Create a persistence container based on the configured mode.

    Args:
        mode: "memory" or "postgres". If None, reads PERSISTENCE_MODE env var,
              defaulting to "memory".
    """
    if mode is None:
        mode = os.environ.get("PERSISTENCE_MODE", "postgres")

    if mode == "memory":
        from app.services.batch_service import InMemoryBatchRepository
        return PersistenceContainer(
            recovery_items=InMemoryRecoveryItemRepository(),
            idempotency=InMemoryIdempotencyStore(),
            audit_log=InMemoryAuditLog(),
            attempts=InMemoryAttemptLedger(),
            decisions=InMemoryRecoveryDecisionRepository(),
            outcomes=_InMemoryRecoveryOutcomeRepository(),
            promises=_InMemoryPromiseRepository(),
            provider_events=_InMemoryProviderEventRepository(),
            users=_InMemoryUserRepository(),
            sessions=_InMemorySessionRepository(),
            jobs=InMemoryRecoveryJobRepository(),
            batches=InMemoryBatchRepository(),
        )

    if mode == "postgres":
        conn = create_connection()
        from app.db.postgres_repositories import (
            PostgresRecoveryDecisionRepository,
            PostgresUserRepository,
            PostgresSessionRepository,
        )
        return PersistenceContainer(
            recovery_items=PostgresRecoveryItemRepository(conn),
            idempotency=PostgresIdempotencyStore(conn),
            audit_log=PostgresAuditLog(conn),
            attempts=PostgresAttemptLedger(conn),
            decisions=PostgresRecoveryDecisionRepository(conn),
            outcomes=PostgresRecoveryOutcomeRepository(conn),
            promises=PostgresPromiseRepository(conn),
            provider_events=PostgresProviderEventRepository(conn),
            users=PostgresUserRepository(conn),
            sessions=PostgresSessionRepository(conn),
            jobs=PostgresRecoveryJobRepository(conn),
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
    """In-memory promise repository — full CRUD for Stage 8 promise lifecycle."""

    def __init__(self) -> None:
        self._by_item: dict[str, object] = {}   # item_id → Promise
        self._by_id: dict[str, object] = {}     # promise_id → Promise

    def save(self, promise) -> None:
        if isinstance(promise, dict):
            item_id = promise.get("recovery_item_id", "")
            promise_id = promise.get("id", "")
        else:
            item_id = promise.recovery_item_id
            promise_id = promise.id
        self._by_item[item_id] = promise
        if promise_id:
            self._by_id[promise_id] = promise

    def get_for_item(self, recovery_item_id: str):
        return self._by_item.get(recovery_item_id)

    def get(self, promise_id: str):
        """Get promise by its own ID."""
        return self._by_id.get(promise_id)

    def list_all(self) -> list:
        """List all promises."""
        return list(self._by_id.values())

    def list_by_item(self, item_id: str) -> list:
        p = self._by_item.get(item_id)
        return [p] if p is not None else []

    def list_by_customer(self, customer_id: str) -> list:
        result = []
        for promise in self._by_id.values():
            p_cust = getattr(promise, "customer_id", None) or (promise.get("customer_id") if isinstance(promise, dict) else None)
            if p_cust == customer_id:
                result.append(promise)
        return result

    def update_status(self, promise_id: str, status: str, **extra) -> object | None:
        """Update promise status and extra fields. Returns updated promise."""
        from app.domain.models import Promise
        promise = self._by_id.get(promise_id)
        if promise is None:
            return None
        if isinstance(promise, Promise):
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            updated = Promise(
                id=promise.id,
                recovery_item_id=promise.recovery_item_id,
                customer_id=promise.customer_id,
                promised_amount_minor=promise.promised_amount_minor,
                promised_date=promise.promised_date,
                status=status,
                created_at=promise.created_at,
                fulfilled_at=extra.get("fulfilled_at", promise.fulfilled_at),
                expired_at=extra.get("expired_at", promise.expired_at),
                metadata={**promise.metadata, **extra.get("metadata", {})},
            )
            self.save(updated)
            return updated
        return None


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


class _InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, object] = {}

    def create_user(self, email: str, password_hash: str, full_name: str):
        import uuid
        from datetime import datetime, timezone
        from app.domain.auth import User
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self._users[user.id] = user
        return user

    def get_by_email(self, email: str):
        clean_email = email.lower().strip()
        for u in self._users.values():
            if u.email.lower() == clean_email:
                return u
        return None

    def get_by_id(self, user_id: str):
        return self._users.get(user_id)


class _InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, object] = {}

    def create_session(self, user_id: str, *, expires_in_seconds: int = 86400 * 7):
        import secrets
        from datetime import datetime, timedelta, timezone
        from app.domain.auth import UserSession
        token = secrets.token_hex(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        sess = UserSession(
            session_token=token,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
        )
        self._sessions[token] = sess
        return sess

    def get_session(self, session_token: str):
        from datetime import datetime, timezone
        if not session_token:
            return None
        sess = self._sessions.get(session_token)
        if not sess:
            return None
        if sess.expires_at < datetime.now(timezone.utc):
            self.delete_session(session_token)
            return None
        return sess

    def delete_session(self, session_token: str) -> None:
        self._sessions.pop(session_token, None)


    def get_by_provider_event(self, provider: str, provider_event_id: str):
        ...

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        ...
