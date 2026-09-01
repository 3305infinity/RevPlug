"""Tests for Recovery Strategy Analytics, Outcome-Learning Memory & Recovery Attribution Engine."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.strategy_analytics import StrategyAnalyticsService
from app.services.recovery_attribution import RecoveryAttributionEngine, AttributionType
from app.db.container import create_persistence_container
from app.main import app


def test_strategy_analytics_service_report():
    """Verifies strategy analytics service generates strategy performance rows and opportunity signals."""
    container = create_persistence_container("memory")
    service = StrategyAnalyticsService(container)

    report = service.generate_report()

    assert report.total_historical_cases >= 1000
    assert len(report.strategies) >= 3
    assert len(report.opportunity_signals) >= 3

    payment_link_row = next(s for s in report.strategies if s["action"] == "send_payment_link")
    assert payment_link_row["success_rate_pct"] > 30.0
    assert "Payment Link outperforms retry" in report.opportunity_signals[0]


def test_recovery_attribution_engine_causality():
    """Verifies attribution engine distinguishes DIRECT_AGENT vs ORGANIC recovery."""
    container = create_persistence_container("memory")

    # Direct agent recovery item
    item1 = RecoveryItem(
        id="attr_item_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_attr_1",
        customer_id="cust_attr_1",
        amount_minor=500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.RECOVERED,
        actual_recovery_value=500000,
    )
    container.recovery_items.save(item1)

    # Save mock attempt for item 1
    if hasattr(container.attempts, "record"):
        from app.ledger.attempts import AttemptRecord
        attempt = AttemptRecord(
            recovery_item_id=item1.id,
            attempt_number=1,
            action="send_payment_link",
            executed_at=datetime.now(timezone.utc),
            outcome="success",
        )
        container.attempts.record(attempt)

    engine = RecoveryAttributionEngine(container)
    report = engine.analyze_attributions()

    assert report.total_recovered_minor > 0
    assert report.agent_attributed_minor > 0
    assert report.organic_recovered_minor >= 0


def test_analytics_and_attribution_api_endpoints():
    """Verifies GET /api/strategy-analytics and /api/recovery-attribution endpoints."""
    client = TestClient(app)

    resp_strat = client.get("/api/strategy-analytics")
    assert resp_strat.status_code == 200
    strat_data = resp_strat.json()
    assert "strategies" in strat_data
    assert "opportunity_signals" in strat_data

    resp_attr = client.get("/api/recovery-attribution")
    assert resp_attr.status_code == 200
    attr_data = resp_attr.json()
    assert "total_recovered_minor" in attr_data
    assert "agent_attributed_minor" in attr_data
    assert "organic_recovered_minor" in attr_data
