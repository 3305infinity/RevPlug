"""Tests for Business Case Creation/Ingestion, Event-Driven Operations, Customer Signals, and Systemic Incidents."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.systemic_detector import SystemicLeakDetector
from app.main import app


def test_business_recovery_case_creation_endpoint():
    """Verifies POST /api/recovery-items/create ingests real business data and creates a persisted RecoveryItem."""
    client = TestClient(app)

    payload = {
        "customer_id": "cust_enterprise_882",
        "customer_name": "Globex Solutions",
        "amount_minor": 1250000,
        "currency": "INR",
        "event_type": "subscription_payment_failed",
        "failure_reason": "payment_timed_out",
        "payment_method": "upi",
        "reference_id": "inv_globex_991",
        "consent_opt_out": False,
        "fraud_risk": False,
    }

    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()

    assert data["customer_id"] == "cust_enterprise_882"
    assert data["amount_minor"] == 1250000
    assert data["status"] in ["queued", "detected", "intervention_pending"]
    assert data["priority"] == "CRITICAL"


def test_safety_shield_blocks_opted_out_cases_on_creation():
    """Verifies consent opt-out creates a STOPPED recovery item immediately."""
    client = TestClient(app)

    payload = {
        "customer_id": "cust_opted_out_909",
        "customer_name": "Opted Out Client",
        "amount_minor": 500000,
        "currency": "INR",
        "event_type": "payment_failed",
        "failure_reason": "payment_timed_out",
        "payment_method": "card",
        "reference_id": "inv_opt_882",
        "consent_opt_out": True,
        "fraud_risk": False,
    }

    resp = client.post("/api/recovery-items/create", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()

    assert data["status"] == "stopped"
    assert "opt-out" in data["stopped_reason"].lower()


def test_systemic_leak_detector_identifies_cluster_spikes():
    """Verifies SystemicLeakDetector detects payment failure clusters above baseline."""
    detector = SystemicLeakDetector()

    items = [
        RecoveryItem(
            id=f"sys_item_{i}",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"ext_{i}",
            customer_id=f"cust_{i}",
            amount_minor=499900,
            currency="INR",
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            root_cause="payment_timed_out",
            metadata={"method": "upi"},
        )
        for i in range(5)
    ]

    incidents = detector.detect_incidents(items, window_minutes=60)
    assert len(incidents) > 0
    inc = incidents[0]
    assert inc.payment_method == "upi"
    assert inc.multiplier >= 2.0
