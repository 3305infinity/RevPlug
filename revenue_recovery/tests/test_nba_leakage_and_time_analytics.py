"""Tests for Time-to-Recovery Analytics, Revenue Leakage, and Portfolio Next Best Action Engine."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.time_to_recovery import TimeToRecoveryAnalytics
from app.services.revenue_leakage import RevenueLeakageAnalytics
from app.services.portfolio_nba import PortfolioNextBestActionEngine
from app.db.container import create_persistence_container
from app.main import app


def test_time_to_recovery_analytics():
    """Verifies time-to-recovery metrics calculation."""
    container = create_persistence_container("memory")
    analytics = TimeToRecoveryAnalytics(container)

    report = analytics.generate_report()

    assert report.median_time_to_recovery_display == "2h 14m"
    assert report.p90_time_to_recovery_display == "18h 42m"
    assert "Attempt 1" in report.recovery_by_attempt
    assert report.recovery_by_attempt["Attempt 1"] == 31.0
    assert "<1h" in report.recovery_by_time_window


def test_revenue_leakage_analytics():
    """Verifies revenue leakage categorized breakdown and policy recommendations."""
    container = create_persistence_container("memory")
    from app.datasets.synthetic import load_dataset
    from app.domain.models import RecoveryItem
    raw_items = load_dataset("mixed") + load_dataset("enterprise_receivables")
    items = []
    for item in raw_items:
        meta = dict(item.metadata)
        meta["is_synthetic"] = False
        meta["source"] = "manual_case"
        items.append(RecoveryItem(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=item.status,
            root_cause=item.root_cause,
            recovery_probability=item.recovery_probability,
            expected_recovery_value=item.expected_recovery_value,
            intervention_cost=item.intervention_cost,
            failure_category=item.failure_category,
            provider=item.provider,
            provider_event_id=item.provider_event_id,
            actual_recovery_value=item.actual_recovery_value,
            recovery_status=item.recovery_status,
            score_version=item.score_version,
            scoring_reason=item.scoring_reason,
            priority=item.priority,
            stopped_reason=item.stopped_reason,
            stopped_rule=item.stopped_rule,
            metadata=meta,
        ))
    for item in items:
        container.recovery_items.save(item)

    analytics = RevenueLeakageAnalytics(container)
    report = analytics.generate_report()

    assert report.total_revenue_at_risk_minor > 0
    assert len(report.categories) >= 5

    auth_cat = next(c for c in report.categories if c["category_id"] == "authentication_required")
    assert auth_cat["category_label"] == "Authentication Required"
    assert auth_cat["recovery_rate_pct"] >= 0
    assert "Evaluate recovery workflow rules" in auth_cat["recommended_policy_change"]


def test_portfolio_next_best_action_engine_ranking():
    """Verifies portfolio NBA engine ranks opportunities by expected net recovery."""
    container = create_persistence_container("memory")

    item1 = RecoveryItem(
        id="nba_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_nba_1",
        customer_id="cust_nba_1",
        amount_minor=1000000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="authentication_required",
        metadata={"source": "manual_case", "is_synthetic": False},
    )
    item2 = RecoveryItem(
        id="nba_2",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_nba_2",
        customer_id="cust_nba_2",
        amount_minor=2000000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="fraud",
        metadata={"source": "manual_case", "is_synthetic": False},
    )
    container.recovery_items.save(item1)
    container.recovery_items.save(item2)

    engine = PortfolioNextBestActionEngine(container)
    opportunities = engine.rank_opportunities()

    assert len(opportunities) >= 2
    assert opportunities[0].rank == 1
    # Auth item with high EV should rank higher than fraud item with 0 EV
    assert opportunities[0].expected_net_recovery_minor > opportunities[-1].expected_net_recovery_minor


def test_analytics_and_nba_api_endpoints():
    """Verifies GET /api/analytics/time-to-recovery, /api/analytics/revenue-leakage, and /api/portfolio/next-best-actions endpoints."""
    client = TestClient(app)

    # Seed data into app container — mark as live operational data
    from app.datasets.synthetic import load_dataset
    from app.domain.models import RecoveryItem
    container = app.state.container
    raw_items = load_dataset("healthy_soft")
    for item in raw_items:
        meta = dict(item.metadata)
        meta["is_synthetic"] = False
        meta["source"] = "manual_case"
        live_item = RecoveryItem(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=item.status,
            root_cause=item.root_cause,
            recovery_probability=item.recovery_probability,
            expected_recovery_value=item.expected_recovery_value,
            intervention_cost=item.intervention_cost,
            failure_category=item.failure_category,
            provider=item.provider,
            provider_event_id=item.provider_event_id,
            actual_recovery_value=item.actual_recovery_value,
            recovery_status=item.recovery_status,
            score_version=item.score_version,
            scoring_reason=item.scoring_reason,
            priority=item.priority,
            stopped_reason=item.stopped_reason,
            stopped_rule=item.stopped_rule,
            metadata=meta,
        )
        container.recovery_items.save(live_item)

    resp_ttr = client.get("/api/analytics/time-to-recovery")
    assert resp_ttr.status_code == 200
    ttr_data = resp_ttr.json()
    assert "median_time_to_recovery_display" in ttr_data

    resp_leak = client.get("/api/analytics/revenue-leakage")
    assert resp_leak.status_code == 200
    leak_data = resp_leak.json()
    assert "total_revenue_at_risk_minor" in leak_data
    assert "categories" in leak_data

    resp_nba = client.get("/api/portfolio/next-best-actions")
    assert resp_nba.status_code == 200
    nba_data = resp_nba.json()
    assert isinstance(nba_data, list)
    assert len(nba_data) >= 1
