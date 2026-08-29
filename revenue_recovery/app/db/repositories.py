from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType


class RecoveryItemRepository(Protocol):
    """Persistence boundary for RecoveryItem."""

    def save(self, item: RecoveryItem) -> None:
        ...

    def get(self, item_id: str) -> RecoveryItem | None:
        ...

    def update_status(self, item_id: str, status: RecoveryStatus) -> None:
        ...

    def delete_synthetic_data(self) -> int:
        ...


class InMemoryRecoveryItemRepository:
    """In-memory RecoveryItem repository for unit tests and local development."""

    def __init__(self) -> None:
        self._items: dict[str, RecoveryItem] = {}

    def save(self, item: RecoveryItem) -> None:
        self._items[item.id] = item

    def get(self, item_id: str) -> RecoveryItem | None:
        return self._items.get(item_id)

    def update_status(self, item_id: str, status: RecoveryStatus) -> None:
        existing = self._items.get(item_id)
        if existing:
            self._items[item_id] = existing.__class__(
                id=existing.id,
                source_type=existing.source_type,
                external_id=existing.external_id,
                customer_id=existing.customer_id,
                amount_minor=existing.amount_minor,
                currency=existing.currency,
                created_at=existing.created_at,
                due_at=existing.due_at,
                status=status,
                root_cause=existing.root_cause,
                recovery_probability=existing.recovery_probability,
                expected_recovery_value=existing.expected_recovery_value,
                metadata=existing.metadata,
            )

    def delete_synthetic_data(self) -> int:
        to_delete = [
            k for k, v in self._items.items() 
            if v.metadata and v.metadata.get("is_synthetic") is True
        ]
        for k in to_delete:
            del self._items[k]
        return len(to_delete)
