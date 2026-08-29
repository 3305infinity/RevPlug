"""Stage 7 worker domain models.

RecoveryJob and JobStatus are the authoritative data types for the async
recovery job queue. These are intentionally separate from RecoveryItem and
RecoveryStatus — the job tracks the worker's lifecycle, not the recovery case.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Lifecycle states for a recovery job.

    Transitions:
        QUEUED → PROCESSING (worker claims)
        PROCESSING → COMPLETED (success)
        PROCESSING → FAILED (error, retryable)
        PROCESSING → QUEUED (re-queued for retry)
        FAILED → DEAD_LETTER (attempt_count >= max_attempts)
        QUEUED → DEAD_LETTER (manually dead-lettered)
    """

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


# States from which a job cannot be retried automatically
TERMINAL_JOB_STATUSES: frozenset[JobStatus] = frozenset({
    JobStatus.COMPLETED,
    JobStatus.DEAD_LETTER,
})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RecoveryJob:
    """A durable async work item for the recovery worker.

    The worker claims a job, runs the full RecoveryOrchestrator pipeline,
    then marks the job COMPLETED or FAILED. If the worker crashes while
    PROCESSING, the job becomes reclaimable after ``locked_at + worker_timeout``.
    """

    recovery_item_id: str
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    attempt_count: int = 0
    max_attempts: int = 3
    available_at: datetime = field(default_factory=_utcnow)
    locked_at: datetime | None = None
    locked_by: str | None = None
    last_error: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_JOB_STATUSES

    @property
    def can_retry(self) -> bool:
        return (
            self.status not in TERMINAL_JOB_STATUSES
            and self.attempt_count < self.max_attempts
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a safe dict for API responses. No secrets included."""
        return {
            "job_id": self.job_id,
            "recovery_item_id": self.recovery_item_id,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "available_at": self.available_at.isoformat(),
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_by": self.locked_by,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
