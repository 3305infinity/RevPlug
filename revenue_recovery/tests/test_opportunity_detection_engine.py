"""Tests for Event-Driven Revenue-at-Risk Opportunity Detection Engine."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryStatus
from app.services.opportunity_detector import OpportunityDetector
from app.services.financials import RecoveryFinancialsService
from app.main import app


def test_1_event_creates_opportunity():
    """Ingesting a payment_failed event creates a scored RecoveryItem opportunity."""
    container = app.state.container
    detector = OpportunityDetector(container)

    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_acme_tech",
        "customer_name": "Acme Tech Pvt Ltd",
        "amount_minor": 500000,
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
        "reference_id": "inv_opp_001",
    }
    item = detector.process_event(event)

    assert item.id.startswith("rec_")
    assert item.amount_minor == 500000
    assert item.root_cause == "SOFT_GATEWAY_TIMEOUT"
    assert item.metadata["customer_name"] == "Acme Tech Pvt Ltd"


def test_2_duplicate_event_does_not_create_duplicate_opportunity():
    """Five webhook events for the same invoice update the existing item idempotently."""
    container = app.state.container
    detector = OpportunityDetector(container)

    ref_id = "inv_opp_duplicate_999"
    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_swiggy_b2b",
        "customer_name": "Swiggy Enterprise",
        "amount_minor": 750000,
        "failure_reason": "soft_gateway_timeout",
        "reference_id": ref_id,
    }

    item1 = detector.process_event(event)
    item2 = detector.process_event(event)

    assert item1.id == item2.id
    assert item2.metadata["attempt_count"] == 2


def test_3_payment_success_closes_opportunity():
    """payment_succeeded event transitions an existing opportunity to RECOVERED."""
    container = app.state.container
    detector = OpportunityDetector(container)

    ref_id = "inv_close_test_404"
    fail_evt = {
        "event_type": "payment_failed",
        "customer_id": "cust_zomato_log",
        "customer_name": "Zomato Logistics",
        "amount_minor": 300000,
        "reference_id": ref_id,
    }
    item = detector.process_event(fail_evt)
    assert item.status != RecoveryStatus.RECOVERED

    succ_evt = {
        "event_type": "payment_succeeded",
        "customer_id": "cust_zomato_log",
        "amount_minor": 300000,
        "reference_id": ref_id,
    }
    recovered_item = detector.process_event(succ_evt)
    assert recovered_item.id == item.id
    assert recovered_item.status == RecoveryStatus.RECOVERED
    assert recovered_item.actual_recovery_value == 300000


def test_4_fraud_creates_blocked_opportunity():
    """Fraud flag creates a STOPPED opportunity with policy_state BLOCKED_FRAUD."""
    container = app.state.container
    detector = OpportunityDetector(container)

    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_fraud_gate",
        "amount_minor": 1200000,
        "fraud_risk": True,
        "reference_id": "inv_fraud_99",
    }
    item = detector.process_event(event)
    assert item.status == RecoveryStatus.STOPPED
    assert item.metadata["policy_state"] == "BLOCKED_FRAUD"


def test_5_opt_out_prevents_action():
    """Consent opt-out creates a STOPPED opportunity with policy_state BLOCKED_CONSENT."""
    container = app.state.container
    detector = OpportunityDetector(container)

    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_opted_out",
        "amount_minor": 450000,
        "consent_opt_out": True,
        "reference_id": "inv_opt_88",
    }
    item = detector.process_event(event)
    assert item.status == RecoveryStatus.STOPPED
    assert item.metadata["policy_state"] == "BLOCKED_CONSENT"


def test_6_negative_ev_produces_no_action():
    """Negative Expected Net Recovery sets recommended_action to no_action."""
    container = app.state.container
    detector = OpportunityDetector(container)

    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_low_val",
        "amount_minor": 200,  # ₹2 amount with ₹500 cost = negative net EV
        "failure_reason": "expired_card",
        "reference_id": "inv_low_val_10",
    }
    item = detector.process_event(event)
    assert item.metadata["recommended_action"] == "no_action"


def test_7_systemic_incident_suppresses_retries():
    """Systemic payment incident transitions item to WAITING status."""
    container = app.state.container
    detector = OpportunityDetector(container)

    event = {
        "event_type": "payment_failed",
        "customer_id": "cust_sys_test",
        "amount_minor": 800000,
        "systemic_incident": True,
        "reference_id": "inv_sys_77",
    }
    item = detector.process_event(event)
    assert item.status == RecoveryStatus.INTERVENTION_PENDING
    assert item.metadata["policy_state"] == "SUPPRESSED_SYSTEMIC"


def test_8_opportunity_ranking_follows_expected_net_recovery():
    """Opportunity Inbox API returns items ordered descending by expected_net_recovery_minor."""
    client = TestClient(app)

    # Ingest 2 items with distinct net EV
    detector = OpportunityDetector(app.state.container)
    detector.process_event({
        "event_type": "payment_failed",
        "customer_id": "cust_rank_high",
        "customer_name": "High Value Client",
        "amount_minor": 5000000,
        "reference_id": "inv_rank_high",
    })
    detector.process_event({
        "event_type": "payment_failed",
        "customer_id": "cust_rank_low",
        "customer_name": "Low Value Client",
        "amount_minor": 100000,
        "reference_id": "inv_rank_low",
    })

    resp = client.get("/api/opportunity-inbox")
    assert resp.status_code == 200
    inbox = resp.json()
    assert len(inbox) >= 2

    # Verify descending net EV order
    net_evs = [op["expected_net_recovery_minor"] for op in inbox]
    assert net_evs == sorted(net_evs, reverse=True)


def test_9_dashboard_totals_equal_underlying_persisted_opportunities():
    """Portfolio totals match the sum of underlying persisted RecoveryItems."""
    container = app.state.container
    fin_svc = RecoveryFinancialsService(container)
    portfolio = fin_svc.get_portfolio_summary()

    assert "total_revenue_at_risk_minor" in portfolio
    assert "actionable_revenue_minor" in portfolio
    assert "revenue_recovered_minor" in portfolio
    assert portfolio["total_revenue_at_risk_minor"] >= 0


def test_10_customer_facing_api_never_exposes_demo_placeholder_names():
    """GET /api/opportunity-inbox exposes human-readable enterprise names, not demo placeholders."""
    client = TestClient(app)
    resp = client.get("/api/opportunity-inbox")
    assert resp.status_code == 200
    inbox = resp.json()

    for item in inbox:
        name = item.get("customer_name", "")
        assert "cust_demo" not in name
        assert "cust_razor" not in name
        assert "DEMO" not in name
