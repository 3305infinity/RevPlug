"""Deterministic synthetic datasets for RecoverOS demonstrations.

IMPORTANT: All items in this module are clearly labeled as synthetic/demo data.
They are NOT real customer payments and must never be reported as actual
recovered revenue in production dashboards.

All datasets use fixed seeds so the same dataset label always produces
identical item IDs, amounts, and metadata — making test assertions stable.

Datasets:
    A (healthy_soft)         — 20 soft failures, high recovery probability
    B (mixed)                — 30 items across all failure categories
    C (fraud_heavy)          — 15 items, majority fraud, very low recovery
    D (retry_exhaustion)     — 20 items with attempt_count at max
    E (enterprise_receivables) — 25 receivable items, enterprise amounts
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType


# Metadata key that marks items as synthetic — checked before any outcome recording
SYNTHETIC_MARKER = "is_synthetic"
SYNTHETIC_VALUE = True


def _stable_id(prefix: str, n: int) -> str:
    """Generate a stable, deterministic item ID from prefix + index."""
    raw = f"{prefix}_{n:04d}"
    digest = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _utc(days_ago: int = 0) -> datetime:
    base = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    return base - timedelta(days=days_ago)


def _make_item(
    item_id: str,
    source_type: SourceType,
    amount_minor: int,
    root_cause: str,
    status: RecoveryStatus,
    attempt_count: int,
    recovery_probability: float,
    expected_recovery_value: int,
    created_at: datetime,
    customer_id: str,
    dataset_label: str,
    extra_metadata: dict[str, Any] | None = None,
) -> RecoveryItem:
    metadata: dict[str, Any] = {
        SYNTHETIC_MARKER: SYNTHETIC_VALUE,
        "dataset_label": dataset_label,
        "attempt_count": attempt_count,
        **(extra_metadata or {}),
    }
    return RecoveryItem(
        id=item_id,
        source_type=source_type,
        external_id=f"evt_{item_id}",
        customer_id=customer_id,
        amount_minor=amount_minor,
        currency="INR",
        created_at=created_at,
        status=status,
        root_cause=root_cause,
        recovery_probability=recovery_probability,
        expected_recovery_value=expected_recovery_value,
        intervention_cost=100,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Dataset A — Healthy Soft Failures
# ---------------------------------------------------------------------------

def dataset_a_healthy_soft() -> list[RecoveryItem]:
    """20 soft payment failures, high recovery rate, minimal fraud."""
    label = "healthy_soft"
    items = []
    amounts = [50000, 75000, 100000, 125000, 150000,
               200000, 250000, 300000, 350000, 400000,
               45000, 60000, 80000, 110000, 175000,
               225000, 275000, 320000, 380000, 420000]
    statuses = [
        RecoveryStatus.QUEUED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.INTERVENTION_PENDING,
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.INTERVENTION_EXECUTED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED,
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.INTERVENTION_PENDING,
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED,
    ]
    for i, (amount, status) in enumerate(zip(amounts, statuses)):
        item_id = _stable_id("syn_a", i)
        prob = 0.65 + (i % 5) * 0.05
        ev = int(amount * prob * 0.9)
        items.append(_make_item(
            item_id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            amount_minor=amount,
            root_cause="soft",
            status=status,
            attempt_count=i % 2,
            recovery_probability=min(prob, 0.95),
            expected_recovery_value=ev,
            created_at=_utc(days_ago=30 - i),
            customer_id=f"cust_a_{i % 5 + 1}",
            dataset_label=label,
        ))
    return items


# ---------------------------------------------------------------------------
# Dataset B — Mixed Failures
# ---------------------------------------------------------------------------

def dataset_b_mixed() -> list[RecoveryItem]:
    """30 items across soft/hard/auth/fraud categories, realistic distribution."""
    label = "mixed"
    categories = (
        ["soft"] * 14 +
        ["hard"] * 7 +
        ["authentication_required"] * 6 +
        ["fraud"] * 3
    )
    amounts = [
        50000, 75000, 100000, 150000, 200000, 250000, 300000,
        125000, 175000, 225000, 350000, 400000, 80000, 60000,
        500000, 750000, 300000, 200000, 400000, 600000, 350000,
        150000, 200000, 250000, 100000, 175000,
        800000, 1000000, 500000,
    ][:30]
    statuses = [
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.ESCALATED,
        RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.QUEUED,
        RecoveryStatus.RECOVERED, RecoveryStatus.INTERVENTION_PENDING, RecoveryStatus.RECOVERED,
        RecoveryStatus.QUEUED, RecoveryStatus.ESCALATED, RecoveryStatus.RECOVERED,
        RecoveryStatus.QUEUED, RecoveryStatus.STOPPED,
        RecoveryStatus.ESCALATED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED,
        RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED,
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.STOPPED,
        RecoveryStatus.INTERVENTION_PENDING, RecoveryStatus.ESCALATED,
        RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED, RecoveryStatus.STOPPED,
    ][:30]
    items = []
    for i, (amount, root_cause, status) in enumerate(zip(amounts, categories, statuses)):
        item_id = _stable_id("syn_b", i)
        if root_cause == "soft":
            prob, ev_factor = 0.55, 0.5
        elif root_cause == "authentication_required":
            prob, ev_factor = 0.30, 0.25
        elif root_cause == "hard":
            prob, ev_factor = 0.08, 0.05
        else:  # fraud
            prob, ev_factor = 0.0, 0.0
        ev = int(amount * ev_factor)
        items.append(_make_item(
            item_id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            amount_minor=amount,
            root_cause=root_cause,
            status=status,
            attempt_count=i % 3,
            recovery_probability=prob,
            expected_recovery_value=ev,
            created_at=_utc(days_ago=60 - i * 2),
            customer_id=f"cust_b_{i % 8 + 1}",
            dataset_label=label,
        ))
    return items


# ---------------------------------------------------------------------------
# Dataset C — Fraud Heavy
# ---------------------------------------------------------------------------

def dataset_c_fraud_heavy() -> list[RecoveryItem]:
    """15 items, majority fraud. Very low overall recovery rate."""
    label = "fraud_heavy"
    categories = ["fraud"] * 10 + ["hard"] * 3 + ["soft"] * 2
    amounts = [200000, 500000, 750000, 1000000, 300000,
               450000, 600000, 800000, 350000, 250000,
               400000, 600000, 200000, 100000, 150000]
    items = []
    for i, (amount, root_cause) in enumerate(zip(amounts, categories)):
        item_id = _stable_id("syn_c", i)
        if root_cause == "fraud":
            prob, ev, status = 0.0, 0, RecoveryStatus.STOPPED
        elif root_cause == "hard":
            prob, ev, status = 0.05, int(amount * 0.03), RecoveryStatus.ESCALATED
        else:
            prob, ev, status = 0.60, int(amount * 0.55), RecoveryStatus.QUEUED
        items.append(_make_item(
            item_id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            amount_minor=amount,
            root_cause=root_cause,
            status=status,
            attempt_count=0,
            recovery_probability=prob,
            expected_recovery_value=ev,
            created_at=_utc(days_ago=45 - i * 3),
            customer_id=f"cust_c_{i % 4 + 1}",
            dataset_label=label,
            extra_metadata={"fraud_flag": root_cause == "fraud"},
        ))
    return items


# ---------------------------------------------------------------------------
# Dataset D — Retry Exhaustion
# ---------------------------------------------------------------------------

def dataset_d_retry_exhaustion() -> list[RecoveryItem]:
    """20 items all with attempt_count=3 (max). All should be stopped/escalated."""
    label = "retry_exhaustion"
    amounts = [50000, 75000, 100000, 125000, 150000,
               60000, 80000, 110000, 140000, 170000,
               200000, 90000, 130000, 160000, 190000,
               220000, 55000, 85000, 115000, 145000]
    items = []
    for i, amount in enumerate(amounts):
        item_id = _stable_id("syn_d", i)
        status = RecoveryStatus.STOPPED if i % 3 != 0 else RecoveryStatus.ESCALATED
        items.append(_make_item(
            item_id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            amount_minor=amount,
            root_cause="soft",
            status=status,
            attempt_count=3,  # Always at max
            recovery_probability=0.10,
            expected_recovery_value=int(amount * 0.08),
            created_at=_utc(days_ago=90 - i * 4),
            customer_id=f"cust_d_{i % 5 + 1}",
            dataset_label=label,
            extra_metadata={"stopped_reason": "retry_budget_exhausted"},
        ))
    return items


# ---------------------------------------------------------------------------
# Dataset E — Enterprise Receivables
# ---------------------------------------------------------------------------

def dataset_e_enterprise_receivables() -> list[RecoveryItem]:
    """25 enterprise receivable items with larger amounts, mixed outcomes."""
    label = "enterprise_receivables"
    amounts = [
        5000000, 7500000, 10000000, 2500000, 4000000,
        6000000, 8000000, 3000000, 9000000, 1500000,
        3500000, 5500000, 7000000, 1000000, 4500000,
        6500000, 2000000, 8500000, 3250000, 4750000,
        5250000, 6750000, 9500000, 1250000, 7250000,
    ]
    statuses = [
        RecoveryStatus.RECOVERED, RecoveryStatus.QUEUED, RecoveryStatus.ESCALATED,
        RecoveryStatus.RECOVERED, RecoveryStatus.INTERVENTION_PENDING, RecoveryStatus.RECOVERED,
        RecoveryStatus.STOPPED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.ESCALATED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.STOPPED, RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED,
        RecoveryStatus.INTERVENTION_PENDING, RecoveryStatus.RECOVERED, RecoveryStatus.ESCALATED,
        RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED,
        RecoveryStatus.QUEUED, RecoveryStatus.RECOVERED, RecoveryStatus.ESCALATED,
        RecoveryStatus.QUEUED,
    ]
    items = []
    for i, (amount, status) in enumerate(zip(amounts, statuses)):
        item_id = _stable_id("syn_e", i)
        prob = 0.65 if status == RecoveryStatus.RECOVERED else 0.40
        ev = int(amount * prob)
        items.append(_make_item(
            item_id=item_id,
            source_type=SourceType.RECEIVABLE,
            amount_minor=amount,
            root_cause="overdue",
            status=status,
            attempt_count=i % 2,
            recovery_probability=prob,
            expected_recovery_value=ev,
            created_at=_utc(days_ago=120 - i * 4),
            customer_id=f"cust_e_{i % 6 + 1}",
            dataset_label=label,
            extra_metadata={"days_overdue": 30 + i * 3, "invoice_id": f"inv_{item_id}"},
        ))
    return items


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DATASETS: dict[str, tuple[str, callable]] = {
    "healthy_soft": ("Dataset A — Healthy Soft Failures (20 items)", dataset_a_healthy_soft),
    "mixed": ("Dataset B — Mixed Failures (30 items)", dataset_b_mixed),
    "fraud_heavy": ("Dataset C — Fraud Heavy (15 items)", dataset_c_fraud_heavy),
    "retry_exhaustion": ("Dataset D — Retry Exhaustion (20 items)", dataset_d_retry_exhaustion),
    "enterprise_receivables": ("Dataset E — Enterprise Receivables (25 items)", dataset_e_enterprise_receivables),
}


@dataclass
class DatasetInfo:
    label: str
    description: str
    item_count: int
    is_synthetic: bool = True


def list_datasets() -> list[DatasetInfo]:
    """Return metadata about all available synthetic datasets."""
    infos = []
    for label, (description, factory) in DATASETS.items():
        items = factory()
        infos.append(DatasetInfo(
            label=label,
            description=description,
            item_count=len(items),
        ))
    return infos


def load_dataset(label: str) -> list[RecoveryItem]:
    """Load a named synthetic dataset. Raises ValueError for unknown labels."""
    if label not in DATASETS:
        raise ValueError(f"Unknown dataset label {label!r}. Available: {list(DATASETS)}")
    _, factory = DATASETS[label]
    return factory()


def assert_synthetic(item: RecoveryItem) -> None:
    """Raise AssertionError if item is not marked synthetic — safety guard."""
    if not item.metadata.get(SYNTHETIC_MARKER):
        raise AssertionError(
            f"Item {item.id} is not marked as synthetic. "
            "Do not process real customer items through synthetic dataset APIs."
        )
