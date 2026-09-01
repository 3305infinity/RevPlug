"""Tests for Customer 360 Recovery Profile Aggregator & API Endpoint."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.db.container import create_persistence_container
from app.datasets.synthetic import load_dataset
from app.services.customer_recovery_profile import CustomerRecoveryProfileService
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.agents.prompt_builder import RecoveryPromptBuilder
from app.main import app


def test_customer_recovery_profile_aggregator_service():
    """Verifies profile service calculates lifetime economics, contact fatigue, and channel rates accurately."""
    container = create_persistence_container("memory")
    items = load_dataset("healthy_soft")
    for item in items:
        container.recovery_items.save(item)

    cust_id = items[0].customer_id
    service = CustomerRecoveryProfileService(container)
    profile = service.get_profile(cust_id)

    assert profile.customer_id == cust_id
    assert profile.total_lifetime_revenue_minor > 0
    assert profile.customer_value_tier in ("HIGH", "MEDIUM", "LOW")
    assert len(profile.channel_performance) == 4
    assert profile.contact_fatigue["daily_limit"] == 2


def test_customer_recovery_profile_api_endpoint():
    """Verifies GET /api/customers/{customer_id}/recovery-profile endpoint returns 200 with valid schema."""
    client = TestClient(app)

    # Seed data into app container
    container = app.state.container
    items = load_dataset("healthy_soft")
    for item in items:
        container.recovery_items.save(item)

    resp_list = client.get("/api/customers")
    assert resp_list.status_code == 200
    custs = resp_list.json()
    assert len(custs) > 0

    target_cust = custs[0]["customer_id"]
    resp_prof = client.get(f"/api/customers/{target_cust}/recovery-profile")
    assert resp_prof.status_code == 200
    data = resp_prof.json()

    assert data["customer_id"] == target_cust
    assert "total_lifetime_revenue_minor" in data
    assert "current_amount_at_risk_minor" in data
    assert "channel_performance" in data
    assert "contact_fatigue" in data


def test_agent_prompt_builder_includes_customer_profile():
    """Verifies RecoveryPromptBuilder injects Customer 360 profile section into context prompt."""
    builder = RecoveryPromptBuilder()
    ctx = RecoveryContext(
        failure_category=FailureCategory.AUTHENTICATION_REQUIRED,
        item_id="item_test_101",
        customer_profile={
            "customer_value_tier": "HIGH",
            "total_lifetime_revenue_minor": 2500000,
            "actually_recovered_lifetime_minor": 1800000,
            "historical_recovery_rate": 0.72,
            "current_subscription_state": "Active",
            "contact_fatigue": {"contacts_today": 1, "fatigue_risk": "LOW"},
            "channel_performance": [
                {"channel_name": "Payment Link", "success_rate_pct": 72.0},
                {"channel_name": "Auto Retry", "success_rate_pct": 31.0},
            ],
        },
    )

    prompt = builder.build_ranking_prompt(ctx, ["send_payment_link", "retry_payment"])

    assert "CUSTOMER 360 HISTORICAL RECOVERY PROFILE" in prompt
    assert "Customer Value Tier: HIGH" in prompt
    assert "Historical Recovery Rate: 72.0%" in prompt
    assert "Payment Link: 72.0%" in prompt
