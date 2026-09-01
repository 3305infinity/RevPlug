"""Tests for Closed-Loop Outcome Memory, Prediction vs Reality Calibration, and Finance Recovery Analytics."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.scoring.memory import RecoveryMemoryStore
from app.services.strategy_analytics import StrategyAnalyticsService
from app.main import app


def test_outcome_memory_store_records_and_updates_priors():
    """Verifies RecoveryMemoryStore records closed-loop outcomes and updates channel priors."""
    store = RecoveryMemoryStore()
    mem = store.get_memory("cust_test_101")

    # Record historical attempt outcome
    mem.record_historical_attempt("send_payment_link", success=True, recovered_minor=500000)
    mem.record_historical_attempt("send_payment_link", success=True, recovered_minor=500000)

    assert mem.channel_stats["send_payment_link"].total_attempts == 2
    assert mem.channel_stats["send_payment_link"].success_rate == 1.0
    assert mem.preferred_channel == "send_payment_link"

    evidence = mem.format_evidence_summary()
    assert any("send_payment_link" in e for e in evidence)


def test_strategy_analytics_report_contains_kpis_and_lost_reasons():
    """Verifies StrategyAnalyticsService calculates financial KPIs, calibration metrics, and revenue lost reasons."""
    container = app.state.container
    svc = StrategyAnalyticsService(container)

    report = svc.generate_report()
    data = report.to_dict()

    assert "financial_kpis" in data
    assert data["financial_kpis"]["cost_per_recovered_rupee"] >= 0
    assert "calibration_metrics" in data
    assert len(data["calibration_metrics"]["prediction_vs_reality_samples"]) > 0
    assert "revenue_lost_reasons" in data
    assert any(r["reason_code"] == "fraud_risk_block" for r in data["revenue_lost_reasons"])


def test_strategy_analytics_api_endpoint():
    """Verifies GET /api/strategy-analytics returns financial KPIs, calibration scores, and lost reasons."""
    client = TestClient(app)

    resp = client.get("/api/strategy-analytics")
    assert resp.status_code == 200
    data = resp.json()

    assert "financial_kpis" in data
    assert "calibration_metrics" in data
    assert "revenue_lost_reasons" in data
