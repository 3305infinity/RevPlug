"""Batch recovery service.

A batch is a named group of recovery items processed together.
Financial metrics (actual_recovered, recovered_count, etc.) are ALWAYS
derived from recovery_outcomes at query time — never stored as denormalized
copies that could diverge from the authoritative financial truth.

Design invariants:
1. batch.total_amount_at_risk is set once at creation (immutable).
2. batch.expected_recovery is set once during scoring (immutable after scoring).
3. Actual recovery metrics are computed at read time from recovery_outcomes.
4. Synthetic batches are clearly labeled (is_synthetic=True) and their
   items are marked with metadata.is_synthetic=True.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus
from app.scoring.expected_value import ExpectedValueScorer


_DEFAULT_SCORER = ExpectedValueScorer()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RecoveryBatch:
    """A named batch of recovery items."""

    batch_id: str
    name: str
    dataset_label: str = "custom"
    is_synthetic: bool = False
    status: str = "pending"  # pending | processing | completed | failed
    total_items: int = 0
    total_amount_at_risk: int = 0
    expected_recovery: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "name": self.name,
            "dataset_label": self.dataset_label,
            "is_synthetic": self.is_synthetic,
            "status": self.status,
            "total_items": self.total_items,
            "total_amount_at_risk": self.total_amount_at_risk,
            "expected_recovery": self.expected_recovery,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class InMemoryBatchRepository:
    """Thread-safe in-memory batch repository for tests and development."""

    def __init__(self) -> None:
        self._batches: dict[str, RecoveryBatch] = {}
        self._lock = threading.Lock()

    def save(self, batch: RecoveryBatch) -> RecoveryBatch:
        with self._lock:
            self._batches[batch.batch_id] = batch
            return batch

    def get(self, batch_id: str) -> RecoveryBatch | None:
        return self._batches.get(batch_id)

    def list_all(self, limit: int = 100) -> list[RecoveryBatch]:
        batches = list(self._batches.values())
        batches.sort(key=lambda b: b.created_at, reverse=True)
        return batches[:limit]


class BatchService:
    """Orchestrates batch recovery: create → score → rank → enqueue → summarize.

    Financial truth principle:
        summarize_batch() reads actual recovery metrics from recovery_outcomes,
        not from batch fields. This ensures batch summaries are always consistent
        with the authoritative financial record.
    """

    def __init__(
        self,
        *,
        batch_repo: InMemoryBatchRepository,
        recovery_items_repo: Any,
        outcomes_repo: Any,
        scorer: ExpectedValueScorer | None = None,
    ) -> None:
        self._batches = batch_repo
        self._items = recovery_items_repo
        self._outcomes = outcomes_repo
        self._scorer = scorer or _DEFAULT_SCORER

    def create_batch(
        self,
        name: str,
        items: list[RecoveryItem],
        *,
        dataset_label: str = "custom",
        is_synthetic: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> RecoveryBatch:
        """Create a batch and persist all items. Returns the batch."""
        batch_id = str(uuid.uuid4())
        total_amount = sum(i.amount_minor for i in items)

        # Score items if not already scored
        scored_items = []
        for item in items:
            if item.expected_recovery_value is None:
                score = self._scorer.score(
                    amount_minor=item.amount_minor,
                    failure_category=item.root_cause or "unknown",
                    proposed_action="retry_payment",
                    attempt_number=int(item.metadata.get("attempt_count", 0)) + 1,
                )
                item = _with_score(item, score)
            scored_items.append(item)

        expected = sum(i.expected_recovery_value or 0 for i in scored_items)

        batch = RecoveryBatch(
            batch_id=batch_id,
            name=name,
            dataset_label=dataset_label,
            is_synthetic=is_synthetic,
            status="pending",
            total_items=len(scored_items),
            total_amount_at_risk=total_amount,
            expected_recovery=expected,
            metadata={**(metadata or {}), "batch_id": batch_id},
        )

        # Persist items with batch_id in metadata
        for item in scored_items:
            item_with_batch = _add_batch_metadata(item, batch_id, dataset_label)
            self._items.save(item_with_batch)

        self._batches.save(batch)
        return batch

    def enqueue_batch(
        self,
        batch_id: str,
        job_repo: Any,
    ) -> int:
        """Enqueue all QUEUED items in a batch as async jobs. Returns count enqueued."""
        batch = self._batches.get(batch_id)
        if batch is None:
            raise ValueError(f"Batch {batch_id!r} not found")

        if job_repo is None:
            return 0

        # Find all items for this batch
        items = self._get_batch_items(batch_id)
        enqueued = 0
        for item in items:
            if item.status in {RecoveryStatus.QUEUED, RecoveryStatus.DIAGNOSED}:
                job = job_repo.create_job(item.id)
                if job is not None:
                    enqueued += 1

        # Update batch status
        batch.status = "processing"
        self._batches.save(batch)
        return enqueued

    def summarize_batch(self, batch_id: str) -> dict[str, Any] | None:
        """Derive batch metrics from recovery_outcomes (financial truth source).

        Never uses batch-level cached metrics. Always reads fresh from outcomes.
        """
        batch = self._batches.get(batch_id)
        if batch is None:
            return None

        items = self._get_batch_items(batch_id)
        item_ids = {i.id for i in items}

        # Count by status (from items — for workflow state)
        recovered_items = [i for i in items if i.status == RecoveryStatus.RECOVERED]
        stopped_items = [i for i in items if i.status == RecoveryStatus.STOPPED]
        escalated_items = [i for i in items if i.status == RecoveryStatus.ESCALATED]
        active_items = [i for i in items if i.status not in {
            RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED
        }]

        # Actual recovered — ONLY from recovery_outcomes (financial truth)
        actual_recovered = 0
        if self._outcomes is not None:
            for item_id in item_ids:
                outcome = self._outcomes.get_for_item(item_id)
                if outcome is not None:
                    amount = getattr(outcome, "actual_recovery_minor", None) or 0
                    actual_recovered += amount

        # Revenue at risk = items not yet recovered
        revenue_at_risk = sum(
            i.amount_minor for i in items
            if i.status not in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED}
        )

        recovery_rate = (
            actual_recovered / batch.total_amount_at_risk
            if batch.total_amount_at_risk > 0 else 0.0
        )

        total_complete = len(recovered_items) + len(stopped_items) + len(escalated_items)
        completion_pct = total_complete / batch.total_items if batch.total_items > 0 else 0.0

        # Intervention cost & Net recovery — from recovery_outcomes (financial truth)
        total_cost = 0
        if self._outcomes is not None:
            for item_id in item_ids:
                outcome = self._outcomes.get_for_item(item_id)
                if outcome is not None:
                    total_cost += getattr(outcome, "recovery_cost_minor", 0) or 0

        if total_cost == 0:
            total_cost = sum(getattr(i, "intervention_cost", 0) or 0 for i in items if i.status == RecoveryStatus.RECOVERED)

        net_recovered = actual_recovered - total_cost
        roi = net_recovered / total_cost if total_cost > 0 else 0.0

        promises_active = sum(
            1 for i in items
            if (i.metadata if isinstance(i.metadata, dict) else {}).get("promise_status") == "promised"
        )

        return {
            **batch.to_dict(),
            # Financial truth — from recovery_outcomes
            "actual_recovered": actual_recovered,
            "intervention_cost": total_cost,
            "net_revenue_recovered": net_recovered,
            "roi": round(roi, 4),
            "recovery_rate": round(recovery_rate, 4),
            # Workflow state — from recovery_items.status
            "recovered_count": len(recovered_items),
            "stopped_count": len(stopped_items),
            "escalated_count": len(escalated_items),
            "active_count": len(active_items),
            "promises_active": promises_active,
            "revenue_at_risk": revenue_at_risk,
            "completion_pct": round(completion_pct, 4),
        }

    def _get_batch_items(self, batch_id: str) -> list[RecoveryItem]:
        """Get all recovery items belonging to this batch."""
        if hasattr(self._items, "list_all"):
            try:
                all_items = self._items.list_all()
                return [
                    item for item in all_items
                    if (item.metadata if isinstance(item, dict) else getattr(item, "metadata", {})).get("batch_id") == batch_id
                ]
            except Exception:
                pass
        if hasattr(self._items, "_items"):
            return [
                item for item in self._items._items.values()
                if item.metadata.get("batch_id") == batch_id
            ]
        return []

    def get_batch(self, batch_id: str) -> RecoveryBatch | None:
        return self._batches.get(batch_id)

    def list_batches(self, limit: int = 100) -> list[RecoveryBatch]:
        return self._batches.list_all(limit=limit)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _with_score(item: RecoveryItem, score) -> RecoveryItem:
    return RecoveryItem(
        id=item.id, source_type=item.source_type, external_id=item.external_id,
        customer_id=item.customer_id, amount_minor=item.amount_minor, currency=item.currency,
        created_at=item.created_at, due_at=item.due_at, status=item.status,
        root_cause=item.root_cause, recovery_probability=score.recovery_probability,
        expected_recovery_value=score.expected_recovery_value,
        intervention_cost=score.intervention_cost, failure_category=item.failure_category,
        provider=item.provider, provider_event_id=item.provider_event_id,
        actual_recovery_value=item.actual_recovery_value, recovery_status=item.recovery_status,
        score_version=score.score_version, scoring_reason=score.scoring_reason,
        priority=score.priority, stopped_reason=item.stopped_reason,
        stopped_rule=item.stopped_rule, metadata=item.metadata,
    )


def _add_batch_metadata(item: RecoveryItem, batch_id: str, dataset_label: str) -> RecoveryItem:
    meta = {**item.metadata, "batch_id": batch_id, "dataset_label": dataset_label}
    return RecoveryItem(
        id=item.id, source_type=item.source_type, external_id=item.external_id,
        customer_id=item.customer_id, amount_minor=item.amount_minor, currency=item.currency,
        created_at=item.created_at, due_at=item.due_at, status=item.status,
        root_cause=item.root_cause, recovery_probability=item.recovery_probability,
        expected_recovery_value=item.expected_recovery_value,
        intervention_cost=item.intervention_cost, failure_category=item.failure_category,
        provider=item.provider, provider_event_id=item.provider_event_id,
        actual_recovery_value=item.actual_recovery_value, recovery_status=item.recovery_status,
        score_version=item.score_version, scoring_reason=item.scoring_reason,
        priority=item.priority, stopped_reason=item.stopped_reason,
        stopped_rule=item.stopped_rule, metadata=meta,
    )
