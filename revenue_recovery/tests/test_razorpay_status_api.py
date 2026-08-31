"""Tests for Razorpay Operational Integration Status API."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_razorpay_status_api_simulation_mode(client):
    """Verifies /api/razorpay/status returns SIMULATED mode when credentials are missing."""
    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "simulation", "RAZORPAY_KEY_ID": ""}):
        resp = client.get("/api/razorpay/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_mode"] == "SIMULATED"
    assert data["razorpay_connection"] == "Not configured"
    assert data["webhook_verification"] in ("Enabled", "Disabled")
    assert data["payment_link_creation"] == "Available"
    assert data["settlement_verification"] == "Enabled"
    assert "optimized for safe net recovery" in data["central_principle"]


def test_razorpay_status_api_test_mode(client):
    """Verifies /api/razorpay/status returns REAL TEST MODE when configured."""
    env = {
        "RECOVERY_EXECUTION_MODE": "razorpay_test",
        "RAZORPAY_KEY_ID": "rzp_test_key_12345678",
        "RAZORPAY_WEBHOOK_SECRET": "secret_999",
    }
    with patch.dict(os.environ, env):
        resp = client.get("/api/razorpay/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_mode"] == "REAL TEST MODE"
    assert data["razorpay_connection"] == "Connected"
    assert data["masked_key_id"] == "rzp_test..."
    assert data["webhook_verification"] == "Enabled"


def test_razorpay_status_api_never_exposes_secrets(client):
    """Verifies secrets are strictly absent from status API response."""
    env = {
        "RECOVERY_EXECUTION_MODE": "razorpay_test",
        "RAZORPAY_KEY_ID": "rzp_test_key_12345678",
        "RAZORPAY_KEY_SECRET": "super_secret_private_key_xyz",
        "RAZORPAY_WEBHOOK_SECRET": "super_secret_webhook_key_abc",
    }
    with patch.dict(os.environ, env):
        resp = client.get("/api/razorpay/status")

    assert resp.status_code == 200
    raw = resp.text
    assert "super_secret_private_key_xyz" not in raw
    assert "super_secret_webhook_key_abc" not in raw
