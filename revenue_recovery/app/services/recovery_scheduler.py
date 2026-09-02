"""Recovery scheduler for tracking WAIT decisions and enforcing timing constraints.

Tracks:
- wait_count per item (max 3)
- max_wait_horizon_days (max 30 days)
- last_wait_reason and last_scheduled_for

Auto-ESCALATEs when:
- wait_count >= max_wait_count (3)
- scheduled_for > now + max_wait_horizon_days (30 days)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import RecoveryItem
from app.domain.timing_signals import TimingEvaluation


@dataclass
class SchedulerWaitRecord:
    item_id: str
    wait_count: int
    last_wait_reason: str | None
    last_scheduled_for: datetime | None
    last_evaluated_at: datetime
    wait_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "wait_count": self.wait_count,
            "last_wait_reason": self.last_wait_reason,
            "last_scheduled_for": self.last_scheduled_for.isoformat() if self.last_scheduled_for else None,
            "last_evaluated_at": self.last_evaluated_at.isoformat() if self.last_evaluated_at else None,
            "wait_history": self.wait_history,
        }


class RecoveryScheduler:
    """Tracks wait decisions and enforces timing constraints.

    Constraints:
        - max_wait_count: Maximum number of WAIT decisions per item (default 3)
        - max_wait_horizon_days: Maximum days into the future a wait can be scheduled (default 30)

    Auto-escalates when either constraint is breached.
    """

    DEFAULT_MAX_WAIT_COUNT: int = 3
    DEFAULT_MAX_WAIT_HORIZON_DAYS: int = 30

    def __init__(
        self,
        *,
        max_wait_count: int = DEFAULT_MAX_WAIT_COUNT,
        max_wait_horizon_days: int = DEFAULT_MAX_WAIT_HORIZON_DAYS,
    ) -> None:
        self._max_wait_count = max_wait_count
        self._max_wait_horizon_days = max_wait_horizon_days
        self._wait_records: dict[str, SchedulerWaitRecord] = {}

    @property
    def max_wait_count(self) -> int:
        return self._max_wait_count

    @property
    def max_wait_horizon_days(self) -> int:
        return self._max_wait_horizon_days

    def get_wait_record(self, item_id: str) -> SchedulerWaitRecord | None:
        return self._wait_records.get(item_id)

    def evaluate_wait_eligibility(
        self,
        item: RecoveryItem,
        proposed_evaluation: TimingEvaluation,
        *,
        now: datetime | None = None,
    ) -> tuple[bool, SchedulerWaitRecord, str | None]:
        """Evaluate whether a WAIT decision is eligible under scheduler constraints.

        Returns:
            Tuple of (eligible, updated_record, escalation_reason)
            If escalation_reason is non-None, WAIT is not allowed and case should ESCALATE.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        existing = self._wait_records.get(item.id)

        wait_count = existing.wait_count if existing else 0
        last_wait_reason = existing.last_wait_reason if existing else None
        last_scheduled_for = existing.last_scheduled_for if existing else None

        scheduled_for = proposed_evaluation.scheduled_for

        if wait_count >= self._max_wait_count:
            new_record = SchedulerWaitRecord(
                item_id=item.id,
                wait_count=wait_count,
                last_wait_reason=last_wait_reason,
                last_scheduled_for=last_scheduled_for,
                last_evaluated_at=now,
                wait_history=existing.wait_history if existing else [],
            )
            self._wait_records[item.id] = new_record
            return (
                False,
                new_record,
                f"Maximum wait count ({self._max_wait_count}) reached. Item auto-escalated.",
            )

        if scheduled_for is not None:
            horizon_cutoff = now + timedelta(days=self._max_wait_horizon_days)
            if scheduled_for > horizon_cutoff:
                new_record = SchedulerWaitRecord(
                    item_id=item.id,
                    wait_count=wait_count,
                    last_wait_reason=last_wait_reason,
                    last_scheduled_for=last_scheduled_for,
                    last_evaluated_at=now,
                    wait_history=existing.wait_history if existing else [],
                )
                self._wait_records[item.id] = new_record
                return (
                    False,
                    new_record,
                    f"Requested wait horizon ({scheduled_for.date()}) exceeds maximum ({self._max_wait_horizon_days} days). Item auto-escalated.",
                )

        return (True, existing or SchedulerWaitRecord(
            item_id=item.id,
            wait_count=0,
            last_wait_reason=None,
            last_scheduled_for=None,
            last_evaluated_at=now,
        ), None)

    def record_wait(
        self,
        item: RecoveryItem,
        evaluation: TimingEvaluation,
        *,
        now: datetime | None = None,
    ) -> SchedulerWaitRecord:
        """Record a WAIT decision and return the updated wait record."""
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        existing = self._wait_records.get(item.id)
        wait_count = (existing.wait_count if existing else 0) + 1

        new_history_entry = {
            "wait_count": wait_count,
            "reason_code": evaluation.reason_code,
            "reason": evaluation.reason,
            "scheduled_for": evaluation.scheduled_for.isoformat() if evaluation.scheduled_for else None,
            "evaluated_at": now.isoformat(),
            "timing_decision": evaluation.timing_decision,
        }

        new_record = SchedulerWaitRecord(
            item_id=item.id,
            wait_count=wait_count,
            last_wait_reason=evaluation.reason_code,
            last_scheduled_for=evaluation.scheduled_for,
            last_evaluated_at=now,
            wait_history=(existing.wait_history if existing else []) + [new_history_entry],
        )
        self._wait_records[item.id] = new_record
        return new_record

    def reset_wait(self, item_id: str) -> bool:
        """Reset wait tracking for an item (e.g., on RECOVER or STOP)."""
        if item_id in self._wait_records:
            del self._wait_records[item_id]
            return True
        return False

    def get_wait_summary(self, item_id: str) -> dict[str, Any]:
        """Get a summary of wait tracking for an item."""
        record = self._wait_records.get(item_id)
        if record is None:
            return {
                "item_id": item_id,
                "wait_count": 0,
                "wait_remaining": self._max_wait_count,
                "at_max_waits": False,
                "last_wait_reason": None,
                "last_scheduled_for": None,
                "max_wait_count": self._max_wait_count,
                "max_wait_horizon_days": self._max_wait_horizon_days,
                "wait_history": [],
            }
        return {
            "item_id": record.item_id,
            "wait_count": record.wait_count,
            "wait_remaining": max(0, self._max_wait_count - record.wait_count),
            "at_max_waits": record.wait_count >= self._max_wait_count,
            "last_wait_reason": record.last_wait_reason,
            "last_scheduled_for": record.last_scheduled_for.isoformat() if record.last_scheduled_for else None,
            "max_wait_count": self._max_wait_count,
            "max_wait_horizon_days": self._max_wait_horizon_days,
            "wait_history": record.wait_history,
        }
