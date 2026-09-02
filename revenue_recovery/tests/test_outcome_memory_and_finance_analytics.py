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
    from app.datasets.synthetic import load_dataset
    from app.domain.proposals import RecoveryProposal, RecoveryAction
    from app.domain.models import RecoveryItem
    container = app.state.container
    raw_items = load_dataset("mixed") + load_dataset("fraud_heavy")
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
        if item.status == RecoveryStatus.RECOVERED:
            container.decisions.save_decision(
                RecoveryProposal(action=RecoveryAction.SEND_PAYMENT_LINK, reason="highest ev", confidence=0.8),
                item_id=item.id,
                agent_name="test",
                policy_allowed=True,
                final_action="send_payment_link",
            )

    svc = StrategyAnalyticsService(container)
    report = svc.generate_report()
    data = report.to_dict()

    assert "financial_kpis" in data
    assert data["financial_kpis"]["cost_per_recovered_rupee"] >= 0
    assert "calibration_metrics" in data
    assert len(data["calibration_metrics"]["prediction_vs_reality_samples"]) > 0
    assert "revenue_lost_reasons" in data
    assert any(r["reason_code"] == "fraud" for r in data["revenue_lost_reasons"])


def test_strategy_analytics_api_endpoint():
    """Verifies GET /api/strategy-analytics returns financial KPIs, calibration scores, and lost reasons."""
    client = TestClient(app)

    resp = client.get("/api/strategy-analytics")
    assert resp.status_code == 200
    data = resp.json()

    assert "financial_kpis" in data
    assert "calibration_metrics" in data
    assert "revenue_lost_reasons" in data
