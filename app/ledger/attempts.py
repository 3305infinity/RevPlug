from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    recovery_item_id: str
    attempt_number: int
    action: str
    scheduled_at: datetime | None = None
    executed_at: datetime | None = None
    outcome: str = ""
    failure_reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class AttemptLedger(Protocol):
    """Records recovery attempts."""

    def record(self, record: AttemptRecord) -> AttemptRecord:
        ...

    def attempts_for(self, recovery_item_id: str) -> list[AttemptRecord]:
        ...


class InMemoryAttemptLedger:
    """In-memory attempt ledger for unit tests and local development."""

    def __init__(self) -> None:
        self._records: list[AttemptRecord] = []

    def record(self, record: AttemptRecord) -> AttemptRecord:
        self._records.append(record)
        return record

    def attempts_for(self, recovery_item_id: str) -> list[AttemptRecord]:
        return [r for r in self._records if r.recovery_item_id == recovery_item_id]
