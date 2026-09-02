"""Tests for Payment Method Optimization & Checkout Abandonment Recovery."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.payment_method_optimizer import PaymentMethodOptimizer
from app.services.checkout_abandonment_detector import CheckoutAbandonmentDetector
from app.db.container import create_persistence_container
from app.main import app


def test_payment_method_optimizer_hard_failure_suppression():
    """Verifies payment method optimizer suppresses retries on hard expired card failure."""
    optimizer = PaymentMethodOptimizer()
    item = RecoveryItem(
        id="item_opt_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_opt_1",
        customer_id="cust_opt_1",
        amount_minor=250000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="hard",
        metadata={"method": "card", "error_description": "expired_card"},
    )

    res = optimizer.optimize(item)

    assert res.original_method == "card"
    assert res.selected_method == "upi"
    assert "Hard decline on CARD" in res.switch_reason
    assert res.expected_net_improvement_minor > 0

    # Original card retry candidate should be blocked/suppressed
    card_cand = next(c for c in res.candidates if c["method"] == "card")
    assert card_cand["policy_status"] == "BLOCKED"
    assert card_cand["failure_compatibility"] == 0.0


def test_checkout_abandonment_detector_intent_classification():
    """Verifies checkout abandonment detector classifies high intent vs contact fatigue correctly."""
    container = create_persistence_container("memory")
    now = datetime.now(timezone.utc)

    # Item 1: High Intent
    item1 = RecoveryItem(
        id="chk_1",
        source_type=SourceType.CHECKOUT_ABANDONMENT,
        external_id="ext_chk_1",
        customer_id="cust_chk_1",
        amount_minor=1200000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        metadata={"source": "manual_case", "is_synthetic": False, "is_checkout_abandonment": True, "contacts_today": 0},
    )
    # Item 2: Contact Fatigue
    item2 = RecoveryItem(
        id="chk_2",
        source_type=SourceType.CHECKOUT_ABANDONMENT,
        external_id="ext_chk_2",
        customer_id="cust_chk_2",
        amount_minor=800000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        metadata={"source": "manual_case", "is_synthetic": False, "is_checkout_abandonment": True, "contacts_today": 3},
    )
    container.recovery_items.save(item1)
    container.recovery_items.save(item2)

    detector = CheckoutAbandonmentDetector(container)
    analyses = detector.detect_and_analyze()

    assert len(analyses) >= 2
    a1 = next(a for a in analyses if a.customer_id == "cust_chk_1")
    a2 = next(a for a in analyses if a.customer_id == "cust_chk_2")

    assert a1.intent_classification == "HIGH INTENT"
    assert a1.recommended_action == "send_payment_link"

    assert a2.intent_classification == "CONTACT FATIGUE"
    assert a2.recommended_action == "NO_ACTION"


def test_checkout_recovery_api_endpoints():
    """Verifies GET /api/checkout-recovery/summary and /items endpoints."""
    client = TestClient(app)
    resp_sum = client.get("/api/checkout-recovery/summary")
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert "checkout_revenue_at_risk_minor" in sum_data
    assert "abandoned_checkouts_count" in sum_data
    assert "intent_breakdown" in sum_data

    resp_items = client.get("/api/checkout-recovery/items")
    assert resp_items.status_code == 200
    items_data = resp_items.json()
    assert isinstance(items_data, list)
