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


# ---------------------------------------------------------------------------
# DATA CLASSIFICATION CONTRACT — REGRESSION ASSERTIONS
# ---------------------------------------------------------------------------
# These tests guard the LIVE vs BENCHMARK vs UNKNOWN boundary.
# They are intentionally placed in this file (batch isolation) because the
# data classification contract is the strongest possible version of batch
# isolation: not just "batch items don't pollute", but "only explicitly
# classified live data enters operational surfaces".
# ---------------------------------------------------------------------------

def test_synthetic_records_cannot_enter_operational_inbox():
    """BENCHMARK_SYNTHETIC records must NOT appear in live operational surfaces."""
    from app.dashboard_api import _get_items
    container = create_persistence_container("memory")
    detector = OpportunityDetector(container)

    synth_item = RecoveryItem(
        id="synth_inbox_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_synth_inbox_001",
        customer_id="cust_synth_inbox_001",
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={"is_synthetic": True, "source": "synthetic_dataset"},
    )
    container.recovery_items.save(synth_item)

    # _get_items (operational) must exclude synthetic data
    live_items = _get_items(container)
    assert all(i.metadata.get("is_synthetic") is not True for i in live_items), (
        "REGRESSION: Synthetic item leaked into _get_items()"
    )

    # Opportunity inbox must also exclude synthetic data
    opportunities = detector.list_opportunities()
    assert all(o.id != "synth_inbox_001" for o in opportunities), (
        "REGRESSION: Synthetic item leaked into opportunity inbox"
    )


def test_unknown_records_cannot_enter_operational_inbox():
    """UNKNOWN records (missing classification) must NOT appear in operational surfaces."""
    from app.dashboard_api import _get_items
    container = create_persistence_container("memory")
    detector = OpportunityDetector(container)

    unknown_item = RecoveryItem(
        id="unknown_inbox_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_unknown_inbox_001",
        customer_id="cust_unknown_inbox_001",
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={},  # No source, no is_synthetic — UNKNOWN
    )
    container.recovery_items.save(unknown_item)

    live_items = _get_items(container)
    assert all(i.id != "unknown_inbox_001" for i in live_items), (
        "REGRESSION: UNKNOWN item leaked into _get_items()"
    )

    opportunities = detector.list_opportunities()
    assert all(o.id != "unknown_inbox_001" for o in opportunities), (
        "REGRESSION: UNKNOWN item leaked into opportunity inbox"
    )


def test_live_records_appear_in_operational_inbox():
    """Explicitly-classified LIVE records MUST appear in operational surfaces."""
    from app.dashboard_api import _get_items
    container = create_persistence_container("memory")
    detector = OpportunityDetector(container)

    live_item = RecoveryItem(
        id="live_inbox_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_live_inbox_001",
        customer_id="cust_live_inbox_001",
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={"source": "manual_case", "is_synthetic": False},
    )
    container.recovery_items.save(live_item)

    live_items = _get_items(container)
    assert any(i.id == "live_inbox_001" for i in live_items), (
        "REGRESSION: Live item missing from _get_items()"
    )

    opportunities = detector.list_opportunities()
    assert any(o.id == "live_inbox_001" for o in opportunities), (
        "REGRESSION: Live item missing from opportunity inbox"
    )


def test_test_fixtures_excluded_from_operational_inbox():
    """TEST_FIXTURE records (batch items, is_test_fixture=True) must NOT enter operational surfaces."""
    from app.dashboard_api import _get_items
    container = create_persistence_container("memory")
    detector = OpportunityDetector(container)

    fixture_item = RecoveryItem(
        id="fixture_inbox_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fixture_inbox_001",
        customer_id="cust_fixture_inbox_001",
        amount_minor=50000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={"is_test_fixture": True, "source": "manual_case"},
    )
    container.recovery_items.save(fixture_item)

    live_items = _get_items(container)
    assert all(i.id != "fixture_inbox_001" for i in live_items), (
        "REGRESSION: Test fixture item leaked into _get_items()"
    )

    opportunities = detector.list_opportunities()
    assert all(o.id != "fixture_inbox_001" for o in opportunities), (
        "REGRESSION: Test fixture item leaked into opportunity inbox"
    )


def test_synthetic_records_dont_contaminate_financial_totals():
    """BENCHMARK_SYNTHETIC records must NOT affect live financial aggregates."""
    from app.dashboard_api import build_dashboard_summary
    container = create_persistence_container("memory")

    # 1 live item with ₹1000 amount
    live_item = RecoveryItem(
        id="fin_live_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fin_live_001",
        customer_id="cust_fin_live_001",
        amount_minor=100000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={"source": "manual_case", "is_synthetic": False},
    )
    container.recovery_items.save(live_item)

    baseline_summary = build_dashboard_summary(container)
    baseline_risk = baseline_summary["revenue_at_risk"]

    # 1 synthetic item with ₹9,999,999 amount (10K x larger)
    synth_item = RecoveryItem(
        id="fin_synth_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fin_synth_001",
        customer_id="cust_fin_synth_001",
        amount_minor=999999900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
        metadata={"is_synthetic": True, "source": "synthetic_dataset"},
    )
    container.recovery_items.save(synth_item)

    after_summary = build_dashboard_summary(container)
    assert after_summary["revenue_at_risk"] == baseline_risk, (
        f"REGRESSION: Synthetic item contaminated financial totals. "
        f"Before: {baseline_risk}, After: {after_summary['revenue_at_risk']}"
    )


def test_classify_item_returns_four_canonical_classes():
    """_classify_item must return exactly one of the 4 canonical classifications."""
    from app.dashboard_api import _classify_item

    assert _classify_item({"is_synthetic": True}) == "BENCHMARK_SYNTHETIC"
    assert _classify_item({"source": "synthetic_dataset"}) == "BENCHMARK_SYNTHETIC"
    assert _classify_item({"source": "demo_scenario"}) == "BENCHMARK_SYNTHETIC"
    assert _classify_item({"source": "webhook_live", "is_synthetic": False}) == "LIVE_OPERATIONAL"
    assert _classify_item({"source": "manual_case", "is_synthetic": False}) == "LIVE_OPERATIONAL"
    assert _classify_item({"source": "webhook", "is_synthetic": False}) == "LIVE_OPERATIONAL"
    assert _classify_item({"is_test_fixture": True}) == "TEST_FIXTURE"
    assert _classify_item({"batch_scope": True}) == "TEST_FIXTURE"
    assert _classify_item({"batch_id": "x"}) == "TEST_FIXTURE"
    assert _classify_item({}) == "UNKNOWN"
    assert _classify_item({"source": "unknown_source"}) == "UNKNOWN"
    assert _classify_item({"is_synthetic": False}) == "UNKNOWN"
