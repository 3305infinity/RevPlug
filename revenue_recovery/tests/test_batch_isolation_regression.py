"""Regression test suite for batch isolation and live queue protection.

Verifies that creating batch/benchmark runs does NOT pollute the live operational
recovery queue (/api/opportunity-inbox or _get_items()), while batch-specific queries
continue to access their own items.
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.db.container import create_persistence_container
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.batch_service import BatchService, InMemoryBatchRepository
from app.services.opportunity_detector import OpportunityDetector
from app.scoring.expected_value import ExpectedValueScorer
from app.main import create_app, app as default_app


def test_batch_creation_does_not_pollute_opportunity_inbox():
    """Running create_batch() with N synthetic items MUST NOT change live inbox count."""
    container = create_persistence_container("memory")
    detector = OpportunityDetector(container)

    # Initial live opportunity count
    initial_opportunities = detector.list_opportunities()
    initial_count = len(initial_opportunities)

    # Create a batch with 3 synthetic items
    batch_repo = InMemoryBatchRepository()
    container.batches = batch_repo
    batch_svc = BatchService(
        batch_repo=batch_repo,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
        scorer=ExpectedValueScorer(),
    )

    items = [
        RecoveryItem(
            id=f"batch_item_{i}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"ext_batch_{i}",
            customer_id=f"cust_batch_{i}",
            amount_minor=50000 + (i * 10000),
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            root_cause="soft",
        )
        for i in range(3)
    ]

    batch = batch_svc.create_batch(
        name="Test Benchmark Run",
        items=items,
        dataset_label="benchmark_test",
        is_synthetic=True,
    )

    # 1. Live opportunity inbox count MUST remain unchanged
    after_batch_opportunities = detector.list_opportunities()
    assert len(after_batch_opportunities) == initial_count, (
        f"REGRESSION: Live opportunity inbox polluted by batch creation. "
        f"Expected {initial_count}, got {len(after_batch_opportunities)}"
    )

    # 2. Batch-specific query MUST return the 3 items
    batch_items = batch_svc._get_batch_items(batch.batch_id)
    assert len(batch_items) == 3
    for bi in batch_items:
        assert bi.metadata.get("batch_scope") is True
        assert bi.metadata.get("batch_id") == batch.batch_id


def test_purge_batch_items_clears_synthetic_items():
    """purge_batch_items() purges batch items without wiping non-batch items."""
    container = create_persistence_container("memory")

    # Add 1 live operational item
    live_item = RecoveryItem(
        id="rec_live_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_live_001",
        customer_id="cust_live_001",
        amount_minor=100000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        metadata={"customer_name": "Live Customer Alpha"},
    )
    container.recovery_items.save(live_item)

    # Add 2 batch items via BatchService
    batch_repo = InMemoryBatchRepository()
    container.batches = batch_repo
    batch_svc = BatchService(
        batch_repo=batch_repo,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )

    batch_items = [
        RecoveryItem(
            id=f"rec_batch_purge_{i}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"ext_batch_purge_{i}",
            customer_id=f"cust_batch_purge_{i}",
            amount_minor=200000,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
        )
        for i in range(2)
    ]
    batch_svc.create_batch("Purge Test Batch", batch_items, dataset_label="purge_test")

    # Purge batch items
    purged_count = container.purge_batch_items()
    assert purged_count == 2

    # Live item must still exist
    all_raw = list(container.recovery_items._items.values())
    assert len(all_raw) == 1
    assert all_raw[0].id == "rec_live_001"


def test_purge_batch_endpoint():
    """POST /api/demo/purge-batch-items purges batch synthetic items via API."""
    client = TestClient(default_app)
    resp = client.post("/api/demo/purge-batch-items")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "purged_count" in data
