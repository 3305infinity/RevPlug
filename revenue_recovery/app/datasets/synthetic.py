"""Deterministic synthetic datasets for RevPlug demonstrations.

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
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType


# Metadata key that marks items as synthetic — checked before any outcome recording
SYNTHETIC_MARKER = "is_synthetic"
SYNTHETIC_VALUE = True
EVALUATION_DATASET_VERSION = "v2-counterfactual"


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


# ---------------------------------------------------------------------------
# Evaluation Dataset — seeded, diverse, deterministic
# ---------------------------------------------------------------------------

def generate_evaluation_dataset(count: int = 50, seed: int = 42) -> list[RecoveryItem]:
    """Generate a seeded deterministic evaluation dataset for batch comparison.

    Given the same (count, seed), the output is always identical — enabling
    reproducible evaluation comparisons between RevPlug and the baseline.

    Dataset coverage (distributed across 'count' items):
    - Soft failures (retryable, various attempt counts)
    - Hard failures (non-retryable)
    - Fraud/risk failures (must stop)
    - Auth-required failures
    - Unknown/ambiguous failures
    - Low-value opportunities
    - High-value opportunities
    - Retry-budget-exhausted cases (attempt_count = max)
    - Opted-out customers
    - Promise-to-pay scenarios (active and expired)

    All items are tagged is_synthetic=True.

    Args:
        count: Number of cases to generate (1–500).
        seed: RNG seed for determinism.

    Returns:
        List of RecoveryItem instances, always identical for the same inputs.
    """
    import random as _random

    rng = _random.Random(seed)
    count = max(1, min(count, 500))

    # ---- Failure category distribution weights ----
    # These weights control how many of each category appear.
    # Kept stable so the same seed always produces the same ratios.
    CATEGORIES = [
        # (category_key, weight, retryable, [attempt_choices])
        ("soft",                     30, True,  [0, 1]),
        ("hard",                     15, False, [0, 1]),
        ("authentication_required",  10, False, [0]),
        ("fraud",                     8, False, [0]),
        ("soft_exhausted",            8, True,  [3, 4]),
        ("soft_optout",               5, True,  [0, 1]),
        ("soft_promise_active",      7, True,  [0]),
        ("soft_promise_expired",     7, True,  [1]),
        ("checkout_abandonment",     10, False, [0]),
        ("subscription_failure",     10, True,  [0, 1]),
        ("overdue_receivable",       10, False, [0]),
        ("mandate_failure",          8,  True,  [0, 1]),
    ]

    # Build weighted pool
    pool = []
    for entry in CATEGORIES:
        cat, weight, retryable, _ = entry
        pool.extend([entry] * weight)

    items = []
    opted_out_customers: set[str] = set()

    for i in range(count):
        entry = pool[rng.randint(0, len(pool) - 1)]
        root_cause, _, retryable, attempt_choices = entry

        # Resolve actual root cause and source_type for the item
        actual_root_cause = root_cause
        source_type = SourceType.PAYMENT_FAILURE

        if root_cause == "soft_exhausted":
            actual_root_cause = "soft"
        elif root_cause == "soft_optout":
            actual_root_cause = "soft"
        elif root_cause in ("soft_promise_active", "soft_promise_expired"):
            actual_root_cause = "soft"
        elif root_cause == "checkout_abandonment":
            source_type = SourceType.CHECKOUT_ABANDONMENT
            actual_root_cause = "checkout_abandoned"
        elif root_cause == "subscription_failure":
            source_type = SourceType.SUBSCRIPTION_FAILURE
            actual_root_cause = "soft"
        elif root_cause == "overdue_receivable":
            source_type = SourceType.RECEIVABLE
            actual_root_cause = "invoice_overdue"
        elif root_cause == "mandate_failure":
            source_type = SourceType.MANDATE_FAILURE
            actual_root_cause = "mandate_failed"

        attempt_count = rng.choice(attempt_choices)

        low_amounts = [100, 150, 200, 250, 500]           # < ₹5
        mid_amounts = [5000, 10000, 25000, 50000]          # ₹50–₹500
        high_amounts = [100000, 250000, 500000, 1000000]   # ₹1000–₹10000
        all_amounts = low_amounts * 2 + mid_amounts * 6 + high_amounts * 2
        amount_minor = rng.choice(all_amounts)

        if root_cause == "soft_optout":
            cust_id = f"optout_cust_{i % 3 + 1}"
            opted_out_customers.add(cust_id)
        else:
            cust_id = f"eval_cust_{rng.randint(1, 20)}"

        status = RecoveryStatus.DETECTED
        item_id = f"eval_{seed}_{i:04d}"

        extra: dict = {}
        if root_cause == "soft_optout":
            extra["customer_opted_out"] = True
        if root_cause == "soft_promise_active":
            from datetime import date, timedelta
            promise_date = date.today() + timedelta(days=rng.randint(1, 7))
            extra["promise_date"] = promise_date.isoformat()
            extra["promise_status"] = "promised"
        if root_cause == "soft_promise_expired":
            from datetime import date, timedelta
            promise_date = date.today() - timedelta(days=rng.randint(1, 14))
            extra["promise_date"] = promise_date.isoformat()
            extra["promise_status"] = "expired"
        if root_cause in ("fraud",):
            extra["fraud_flag"] = True
        if source_type == SourceType.RECEIVABLE:
            extra["days_overdue"] = rng.choice([1, 3, 7, 14])
            extra["invoice_id"] = f"INV-{1000 + i}"
        if source_type == SourceType.CHECKOUT_ABANDONMENT:
            extra["checkout_stage"] = "payment_method"
            extra["checkout_age_minutes"] = rng.choice([30, 120, 1440, 15000])
        if source_type == SourceType.MANDATE_FAILURE:
            extra["mandate_id"] = f"man_{100 + i}"
            extra["retry_eligible"] = rng.choice([True, False])

        # Determine ground-truth labels deterministically according to recovery policy
        gt_true_root_cause = actual_root_cause
        gt_correct_action = "retry_payment"
        gt_acceptable_actions = ["retry_payment"]
        gt_recoverable = True
        gt_acceptable_contact = True
        gt_should_escalate = False
        gt_should_stop = False

        if root_cause in ("fraud", "soft_optout", "soft_promise_active"):
            gt_correct_action = "stop_recovery"
            gt_acceptable_actions = ["stop_recovery", "no_action"]
            gt_recoverable = False
            gt_acceptable_contact = False
            gt_should_stop = True
        elif root_cause == "soft_exhausted":
            gt_correct_action = "send_payment_link"
            gt_acceptable_actions = ["send_payment_link", "stop_recovery", "escalate_human"]
            gt_recoverable = False
            gt_should_stop = True
        elif root_cause == "hard":
            if attempt_count >= 2:
                gt_correct_action = "escalate_human"
                gt_acceptable_actions = ["escalate_human", "stop_recovery"]
                gt_should_escalate = True
            else:
                gt_correct_action = "send_payment_link"
                gt_acceptable_actions = ["send_payment_link", "escalate_human"]
        elif root_cause == "authentication_required":
            gt_correct_action = "send_payment_link"
            gt_acceptable_actions = ["send_payment_link", "send_customer_message"]
        elif root_cause == "checkout_abandonment":
            age_mins = extra.get("checkout_age_minutes", 30)
            if age_mins > 10080:  # >7 days
                gt_correct_action = "stop_recovery"
                gt_acceptable_actions = ["stop_recovery"]
                gt_should_stop = True
                gt_recoverable = False
            else:
                gt_correct_action = "send_payment_link"
                gt_acceptable_actions = ["send_payment_link"]
        elif root_cause == "overdue_receivable":
            days = extra.get("days_overdue", 1)
            if days < 3:
                gt_correct_action = "send_reminder"
                gt_acceptable_actions = ["send_reminder"]
            elif days < 7:
                gt_correct_action = "send_payment_link"
                gt_acceptable_actions = ["send_payment_link"]
            elif days < 14:
                gt_correct_action = "alternate_channel"
                gt_acceptable_actions = ["alternate_channel"]
            else:
                gt_correct_action = "escalate_human"
                gt_acceptable_actions = ["escalate_human"]
                gt_should_escalate = True
        elif root_cause == "mandate_failure":
            if extra.get("retry_eligible", True) and attempt_count < 3:
                gt_correct_action = "retry_payment"
                gt_acceptable_actions = ["retry_payment"]
            else:
                gt_correct_action = "send_payment_link"
                gt_acceptable_actions = ["send_payment_link"]

        gt_rng = random.Random(f"counterfactual_{seed}_{item_id}_{amount_minor}")
        action_outcomes = _generate_counterfactual_outcomes(gt_rng, amount_minor, root_cause, gt_recoverable)

        ground_truth = {
            "dataset_version": EVALUATION_DATASET_VERSION,
            "true_root_cause": gt_true_root_cause,
            "correct_action": gt_correct_action,
            "acceptable_actions": gt_acceptable_actions,
            "recoverable": gt_recoverable,
            "expected_recovery": amount_minor if gt_recoverable else 0,
            "acceptable_contact": gt_acceptable_contact,
            "should_escalate": gt_should_escalate,
            "should_stop": gt_should_stop,
            "action_outcomes": action_outcomes,
        }

        items.append(_make_item(
            item_id=item_id,
            source_type=source_type,
            amount_minor=amount_minor,
            root_cause=actual_root_cause,
            status=status,
            attempt_count=attempt_count,
            recovery_probability=0.0,
            expected_recovery_value=0,
            created_at=_utc(days_ago=rng.randint(0, 30)),
            customer_id=cust_id,
            dataset_label=f"eval_seed{seed}",
            extra_metadata={
                **extra,
                "customer_opted_out": root_cause == "soft_optout",
                "eval_seed": seed,
                "eval_index": i,
                "original_category": root_cause,
                "source_type": source_type.value,
                "ground_truth": ground_truth,
            },
        ))

    return items


def generate_synthetic_cases(count: int = 50, seed: int = 42, failure_mix: dict[str, float] | None = None) -> list[RecoveryItem]:
    """Alias for generate_evaluation_dataset for synthetic case generation."""
    items = generate_evaluation_dataset(count=count, seed=seed)
    if failure_mix and "authentication_required" in failure_mix:
        # Filter/override for specific failure mix test
        res = []
        for it in items:
            from dataclasses import replace
            meta = {**it.metadata, "original_category": "authentication_required"}
            res.append(replace(it, root_cause="authentication_required", metadata=meta))
        return res
    if failure_mix and "fraud" in failure_mix:
        res = []
        for it in items:
            from dataclasses import replace
            meta = {**it.metadata, "original_category": "fraud", "customer_opted_out": False, "fraud_flag": True}
            res.append(replace(it, root_cause="fraud", metadata=meta))
        return res
    return items


def _generate_counterfactual_outcomes(
    gt_rng: Any,
    amount_minor: int,
    root_cause: str,
    gt_recoverable: bool,
) -> dict[str, Any]:
    """Generate a deterministic, pre-rolled counterfactual action-outcome table.
    
    This table models the underlying environment ONCE per case so that both
    Baseline and RevPlug evaluate against the EXACT SAME ground truth.
    """
    is_safe = gt_recoverable and root_cause not in ("fraud", "soft_optout", "soft_promise_active", "disputed_invoice")

    # Retry success probabilities by root cause
    if not is_safe:
        r1_p, r2_p, r3_p = 0.0, 0.0, 0.0
    elif root_cause in ("soft", "insufficient_funds", "soft_decline", "mandate_failure"):
        r1_p, r2_p, r3_p = 0.25, 0.40, 0.20
    elif root_cause in ("authentication_required", "3ds_failed"):
        r1_p, r2_p, r3_p = 0.05, 0.05, 0.00
    elif root_cause in ("expired_card", "card_update_required", "hard_decline", "hard"):
        r1_p, r2_p, r3_p = 0.00, 0.00, 0.00
    elif root_cause in ("overdue_receivable", "checkout_abandonment"):
        r1_p, r2_p, r3_p = 0.10, 0.10, 0.00
    else:
        r1_p, r2_p, r3_p = 0.20, 0.20, 0.10

    r1_succ = (gt_rng.random() < r1_p)
    r2_succ = (gt_rng.random() < r2_p)
    r3_succ = (gt_rng.random() < r3_p)

    # Payment link success
    if not is_safe:
        link_p = 0.0
    elif root_cause in ("authentication_required", "3ds_failed", "expired_card", "card_update_required"):
        link_p = 0.85
    elif root_cause in ("soft", "insufficient_funds", "soft_decline", "hard", "checkout_abandonment"):
        link_p = 0.80
    elif root_cause == "overdue_receivable":
        link_p = 0.70
    else:
        link_p = 0.60

    # Reminder success
    if not is_safe:
        rem_p = 0.0
    elif root_cause in ("overdue_receivable", "soft_promise_expired"):
        rem_p = 0.75
    elif root_cause in ("checkout_abandonment", "soft"):
        rem_p = 0.50
    else:
        rem_p = 0.30

    # Alternate channel success
    if not is_safe:
        alt_p = 0.0
    elif root_cause in ("overdue_receivable", "authentication_required"):
        alt_p = 0.80
    elif root_cause in ("soft", "hard"):
        alt_p = 0.65
    else:
        alt_p = 0.40

    # Message success
    msg_p = 0.60 if is_safe else 0.0
    # Offer discount success
    disc_p = 0.80 if (is_safe and root_cause in ("overdue_receivable", "checkout_abandonment")) else 0.0

    link_succ = (gt_rng.random() < link_p)
    rem_succ = (gt_rng.random() < rem_p)
    alt_succ = (gt_rng.random() < alt_p)
    msg_succ = (gt_rng.random() < msg_p)
    disc_succ = (gt_rng.random() < disc_p)

    return {
        "retry_payment": {
            "attempts": {
                "1": {"success": r1_succ, "actual_recovery_minor": amount_minor if r1_succ else 0, "cost_minor": 500},
                "2": {"success": r2_succ, "actual_recovery_minor": amount_minor if r2_succ else 0, "cost_minor": 500},
                "3": {"success": r3_succ, "actual_recovery_minor": amount_minor if r3_succ else 0, "cost_minor": 500},
            }
        },
        "send_payment_link": {
            "success": link_succ,
            "actual_recovery_minor": amount_minor if link_succ else 0,
            "cost_minor": 200,
        },
        "send_reminder": {
            "success": rem_succ,
            "actual_recovery_minor": amount_minor if rem_succ else 0,
            "cost_minor": 100,
        },
        "alternate_channel": {
            "success": alt_succ,
            "actual_recovery_minor": amount_minor if alt_succ else 0,
            "cost_minor": 300,
        },
        "send_customer_message": {
            "success": msg_succ,
            "actual_recovery_minor": amount_minor if msg_succ else 0,
            "cost_minor": 150,
        },
        "offer_discount": {
            "success": disc_succ,
            "actual_recovery_minor": int(amount_minor * 0.9) if disc_succ else 0,
            "cost_minor": 500,
        },
        "stop_recovery": {
            "success": False,
            "actual_recovery_minor": 0,
            "cost_minor": 0,
        },
        "escalate_human": {
            "success": False,
            "actual_recovery_minor": 0,
            "cost_minor": 1000,
        },
    }


def lookup_counterfactual_outcome(
    ground_truth: dict[str, Any],
    action: str,
    attempt_number: int = 1,
) -> tuple[bool, int, int]:
    """Lookup the counterfactual outcome for an action from the shared ground truth table.

    Returns:
        (success, actual_recovery_minor, cost_minor)
    """
    outcomes_table = ground_truth.get("action_outcomes", {})
    if action == "retry_payment":
        retry_info = outcomes_table.get("retry_payment", {}).get("attempts", {})
        att_str = str(min(attempt_number, 3))
        res = retry_info.get(att_str, {"success": False, "actual_recovery_minor": 0, "cost_minor": 500})
        return bool(res["success"]), int(res["actual_recovery_minor"]), int(res["cost_minor"])
    
    act_res = outcomes_table.get(action)
    if isinstance(act_res, dict):
        return bool(act_res.get("success", False)), int(act_res.get("actual_recovery_minor", 0)), int(act_res.get("cost_minor", 0))
    
    return False, 0, 0


def get_golden_evaluation_dataset() -> list[RecoveryItem]:
    """Create a tiny hand-verifiable golden benchmark dataset (5 canonical cases)."""
    cases = []
    # Case 1: ₹1,000 soft failure -> retry_1 succeeds
    gt1 = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "true_root_cause": "soft",
        "correct_action": "retry_payment",
        "acceptable_actions": ["retry_payment"],
        "recoverable": True,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": True, "actual_recovery_minor": 100000, "cost_minor": 500},
                    "2": {"success": True, "actual_recovery_minor": 100000, "cost_minor": 500},
                    "3": {"success": True, "actual_recovery_minor": 100000, "cost_minor": 500},
                }
            },
            "send_payment_link": {"success": True, "actual_recovery_minor": 100000, "cost_minor": 200},
            "stop_recovery": {"success": False, "actual_recovery_minor": 0, "cost_minor": 0},
            "escalate_human": {"success": False, "actual_recovery_minor": 0, "cost_minor": 1000},
        }
    }
    cases.append(_make_item(
        item_id="eval_golden_0001",
        source_type=SourceType.PAYMENT_FAILURE,
        amount_minor=100000,
        root_cause="soft",
        status=RecoveryStatus.DETECTED,
        attempt_count=0,
        recovery_probability=0.7,
        expected_recovery_value=70000,
        created_at=_utc(0),
        customer_id="cust_g1",
        dataset_label="golden",
        extra_metadata={"eval_seed": 42, "eval_index": 0, "ground_truth": gt1},
    ))

    # Case 2: ₹2,000 soft failure -> retry_1 fails, retry_2 fails, payment_link succeeds
    gt2 = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "true_root_cause": "soft",
        "correct_action": "send_payment_link",
        "acceptable_actions": ["send_payment_link"],
        "recoverable": True,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "2": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "3": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                }
            },
            "send_payment_link": {"success": True, "actual_recovery_minor": 200000, "cost_minor": 200},
            "stop_recovery": {"success": False, "actual_recovery_minor": 0, "cost_minor": 0},
            "escalate_human": {"success": False, "actual_recovery_minor": 0, "cost_minor": 1000},
        }
    }
    cases.append(_make_item(
        item_id="eval_golden_0002",
        source_type=SourceType.PAYMENT_FAILURE,
        amount_minor=200000,
        root_cause="soft",
        status=RecoveryStatus.DETECTED,
        attempt_count=0,
        recovery_probability=0.4,
        expected_recovery_value=80000,
        created_at=_utc(0),
        customer_id="cust_g2",
        dataset_label="golden",
        extra_metadata={"eval_seed": 42, "eval_index": 1, "ground_truth": gt2},
    ))

    # Case 3: ₹500 soft failure -> unrecoverable / all actions fail
    gt3 = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "true_root_cause": "soft",
        "correct_action": "stop_recovery",
        "acceptable_actions": ["stop_recovery", "no_action"],
        "recoverable": False,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "2": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "3": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                }
            },
            "send_payment_link": {"success": False, "actual_recovery_minor": 0, "cost_minor": 200},
            "stop_recovery": {"success": False, "actual_recovery_minor": 0, "cost_minor": 0},
            "escalate_human": {"success": False, "actual_recovery_minor": 0, "cost_minor": 1000},
        }
    }
    cases.append(_make_item(
        item_id="eval_golden_0003",
        source_type=SourceType.PAYMENT_FAILURE,
        amount_minor=50000,
        root_cause="soft",
        status=RecoveryStatus.DETECTED,
        attempt_count=0,
        recovery_probability=0.0,
        expected_recovery_value=0,
        created_at=_utc(0),
        customer_id="cust_g3",
        dataset_label="golden",
        extra_metadata={"eval_seed": 42, "eval_index": 2, "ground_truth": gt3},
    ))

    # Case 4: ₹5,000 fraud failure -> must stop (safety rule)
    gt4 = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "true_root_cause": "fraud",
        "correct_action": "stop_recovery",
        "acceptable_actions": ["stop_recovery"],
        "recoverable": False,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "2": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "3": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                }
            },
            "send_payment_link": {"success": False, "actual_recovery_minor": 0, "cost_minor": 200},
            "stop_recovery": {"success": False, "actual_recovery_minor": 0, "cost_minor": 0},
            "escalate_human": {"success": False, "actual_recovery_minor": 0, "cost_minor": 1000},
        }
    }
    cases.append(_make_item(
        item_id="eval_golden_0004",
        source_type=SourceType.PAYMENT_FAILURE,
        amount_minor=500000,
        root_cause="fraud",
        status=RecoveryStatus.DETECTED,
        attempt_count=0,
        recovery_probability=0.0,
        expected_recovery_value=0,
        created_at=_utc(0),
        customer_id="cust_g4",
        dataset_label="golden",
        extra_metadata={"fraud_flag": True, "eval_seed": 42, "eval_index": 3, "ground_truth": gt4},
    ))

    # Case 5: ₹10,000 active promise -> must stop
    gt5 = {
        "dataset_version": EVALUATION_DATASET_VERSION,
        "true_root_cause": "soft",
        "correct_action": "stop_recovery",
        "acceptable_actions": ["stop_recovery"],
        "recoverable": False,
        "action_outcomes": {
            "retry_payment": {
                "attempts": {
                    "1": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "2": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                    "3": {"success": False, "actual_recovery_minor": 0, "cost_minor": 500},
                }
            },
            "send_payment_link": {"success": False, "actual_recovery_minor": 0, "cost_minor": 200},
            "stop_recovery": {"success": False, "actual_recovery_minor": 0, "cost_minor": 0},
            "escalate_human": {"success": False, "actual_recovery_minor": 0, "cost_minor": 1000},
        }
    }
    from datetime import date, timedelta
    p_date = (date.today() + timedelta(days=5)).isoformat()
    cases.append(_make_item(
        item_id="eval_golden_0005",
        source_type=SourceType.PAYMENT_FAILURE,
        amount_minor=1000000,
        root_cause="soft",
        status=RecoveryStatus.DETECTED,
        attempt_count=0,
        recovery_probability=0.0,
        expected_recovery_value=0,
        created_at=_utc(0),
        customer_id="cust_g5",
        dataset_label="golden",
        extra_metadata={"promise_date": p_date, "promise_status": "promised", "eval_seed": 42, "eval_index": 4, "ground_truth": gt5},
    ))

    return cases


def get_opted_out_customers(items: list[RecoveryItem]) -> frozenset[str]:
    """Return the set of opted-out customer IDs from an evaluation dataset."""
    return frozenset(
        item.customer_id
        for item in items
        if item.metadata.get("customer_opted_out")
    )

