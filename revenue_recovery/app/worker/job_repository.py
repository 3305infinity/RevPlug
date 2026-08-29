"""Recovery job repository: protocol, in-memory, and Postgres implementations.

The in-memory implementation uses a threading.Lock for safe concurrent claiming
in tests that exercise concurrent worker scenarios.

The Postgres implementation uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so
multiple worker processes never claim the same job.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from app.worker.models import JobStatus, RecoveryJob, TERMINAL_JOB_STATUSES


class RecoveryJobRepository(Protocol):
    """Persistence boundary for RecoveryJob."""

    def create_job(
        self,
        recovery_item_id: str,
        *,
        max_attempts: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> RecoveryJob:
        """Create a new QUEUED job. Returns None if an active job already exists."""
        ...

    def claim_next_job(
        self,
        worker_id: str,
        *,
        worker_timeout_seconds: int = 300,
    ) -> RecoveryJob | None:
        """Atomically claim the next available job for this worker.

        Also reclaims stale PROCESSING jobs where locked_at + timeout < now.
        Returns None if no job is available.
        """
        ...

    def mark_completed(self, job_id: str) -> None:
        ...

    def mark_failed(
        self,
        job_id: str,
        error: str,
        *,
        retry_delay_seconds: int = 0,
    ) -> None:
        """Mark job as FAILED. If retries remain, re-queue as QUEUED after delay."""
        ...

    def mark_dead_letter(self, job_id: str, reason: str) -> None:
        ...

    def get_job(self, job_id: str) -> RecoveryJob | None:
        ...

    def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[RecoveryJob]:
        ...

    def get_job_for_item(self, recovery_item_id: str) -> RecoveryJob | None:
        """Return the most recent job for a recovery item."""
        ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryRecoveryJobRepository:
    """Thread-safe in-memory job repository for tests and development.

    Uses a threading.Lock to replicate the ``FOR UPDATE SKIP LOCKED``
    semantics of the Postgres implementation. This allows concurrent-worker
    tests to exercise true mutual exclusion.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, RecoveryJob] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        recovery_item_id: str,
        *,
        max_attempts: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> RecoveryJob | None:
        """Create a new QUEUED job.

        Returns None (without creating) if an active (QUEUED or PROCESSING)
        job already exists for this recovery_item_id, matching the Postgres
        unique partial index semantics.
        """
        with self._lock:
            # Enforce unique active job per item (mirrors Postgres partial unique index)
            for job in self._jobs.values():
                if (
                    job.recovery_item_id == recovery_item_id
                    and job.status in (JobStatus.QUEUED, JobStatus.PROCESSING)
                ):
                    return None
            job = RecoveryJob(
                job_id=str(uuid.uuid4()),
                recovery_item_id=recovery_item_id,
                status=JobStatus.QUEUED,
                max_attempts=max_attempts,
                metadata=metadata or {},
            )
            self._jobs[job.job_id] = job
            return job

    def claim_next_job(
        self,
        worker_id: str,
        *,
        worker_timeout_seconds: int = 300,
    ) -> RecoveryJob | None:
        """Atomically claim the next available job.

        Priority:
        1. Stale PROCESSING jobs (locked_at + timeout < now) — crash recovery
        2. QUEUED jobs where available_at <= now
        """
        now = _utcnow()
        timeout_delta = timedelta(seconds=worker_timeout_seconds)

        with self._lock:
            # First: reclaim stale PROCESSING jobs (crash recovery)
            for job in self._jobs.values():
                if (
                    job.status == JobStatus.PROCESSING
                    and job.locked_at is not None
                    and (now - job.locked_at) > timeout_delta
                ):
                    job.status = JobStatus.PROCESSING
                    job.locked_at = now
                    job.locked_by = worker_id
                    return job

            # Second: pick next QUEUED job
            candidates = [
                j for j in self._jobs.values()
                if j.status == JobStatus.QUEUED and j.available_at <= now
            ]
            if not candidates:
                return None

            # FIFO within available jobs
            job = min(candidates, key=lambda j: j.available_at)
            job.status = JobStatus.PROCESSING
            job.locked_at = now
            job.locked_by = worker_id
            job.attempt_count += 1
            return job

    def mark_completed(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = _utcnow()
                job.locked_at = None

    def mark_failed(
        self,
        job_id: str,
        error: str,
        *,
        retry_delay_seconds: int = 0,
    ) -> None:
        """Mark failed. If retries remain, re-queue; otherwise dead-letter."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.last_error = error
            job.locked_at = None
            job.locked_by = None

            if job.attempt_count >= job.max_attempts:
                job.status = JobStatus.DEAD_LETTER
            else:
                job.status = JobStatus.QUEUED
                job.available_at = _utcnow() + timedelta(seconds=retry_delay_seconds)

    def mark_dead_letter(self, job_id: str, reason: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.DEAD_LETTER
                job.last_error = reason
                job.locked_at = None
                job.locked_by = None

    def get_job(self, job_id: str) -> RecoveryJob | None:
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[RecoveryJob]:
        jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def get_job_for_item(self, recovery_item_id: str) -> RecoveryJob | None:
        matches = [
            j for j in self._jobs.values()
            if j.recovery_item_id == recovery_item_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda j: j.created_at)
