from __future__ import annotations

from typing import Protocol


class IdempotencyStore(Protocol):
    """Tracks which external events have already been processed."""

    def has_processed(self, key: str) -> bool:
        """Return True if the event has already been processed."""
        ...

    def mark_processed(self, key: str) -> None:
        """Record that the event has been processed.

        Raises if the key was already processed.
        """
        ...


class InMemoryIdempotencyStore:
    """In-memory idempotency store for unit tests and single-process deployments.

    Enforces uniqueness: mark_processed raises if the same key is presented twice.
    """

    def __init__(self) -> None:
        self._processed: set[str] = set()

    def has_processed(self, key: str) -> bool:
        return key in self._processed

    def mark_processed(self, key: str) -> None:
        if key in self._processed:
            raise ValueError(f"Event already processed: {key}")
        self._processed.add(key)
