"""Tests for Stage 11 — Real Razorpay Test-Mode Recovery Execution & Webhooks."""

from datetime import datetime, timezone
import json
import os
from unittest.mock import MagicMock, patch
import pytest

from app.adapters.razorpay.client import (
    RazorpayAuthenticationError,
    RazorpayClient,
    RazorpayClientError,
    RazorpayNetworkTimeoutError,
)
from app.adapters.razorpay.signatures import RazorpaySignatureError, verify_razorpay_signature
from app.domain.models import RecoveryItem, SourceType
from app.interventions.executor import (
    ExecutionResult,
    RazorpayRecoveryExecutor,
    SimulatedRecoveryExecutor,
    get_executor,
)


def test_razorpay_client_unconfigured():
    client = RazorpayClient(key_id="", key_secret="")
    assert not client.is_configured
    with pytest.raises(RazorpayAuthenticationError):
        client.create_payment_link(amount_minor=1000)


def test_razorpay_client_prohibits_production():
    with pytest.raises(RazorpayClientError, match="Production"):
        RazorpayClient(key_id="rzp_live_123", key_secret="secret", env="production")


@patch("urllib.request.urlopen")
def test_razorpay_client_create_payment_link_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "id": "plink_test_999",
        "short_url": "https://rzp.io/i/test999",
        "status": "created",
        "amount": 499900,
        "currency": "INR",
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = RazorpayClient(key_id="rzp_test_123", key_secret="secret_123", env="test")
    res = client.create_payment_link(amount_minor=499900, currency="INR")

    assert res["provider"] == "razorpay"
    assert res["payment_link_id"] == "plink_test_999"
    assert res["payment_link_url"] == "https://rzp.io/i/test999"
    assert res["status"] == "created"


def test_executor_mode_routing_simulation():
    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "simulation"}):
        executor = get_executor()
        assert isinstance(executor, SimulatedRecoveryExecutor)


def test_executor_mode_routing_razorpay_test():
    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        executor = get_executor()
        assert isinstance(executor, RazorpayRecoveryExecutor)


@patch("urllib.request.urlopen")
def test_razorpay_executor_real_execution(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "id": "plink_rec_101",
        "short_url": "https://rzp.io/i/rec101",
        "status": "created",
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = RazorpayClient(key_id="rzp_test_valid", key_secret="secret_valid")
    executor = RazorpayRecoveryExecutor(razorpay_client=client)

    item = RecoveryItem(
        id="item_rec_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_rec_101",
        customer_id="cust_1",
        amount_minor=499900,
        currency="INR",
        created_at=datetime.now(timezone.utc),
    )

    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        result = executor.execute(item, "send_payment_link", attempt_number=1)

    assert result.success
    assert result.metadata["simulated"] is False
    assert result.metadata["provider"] == "razorpay"
    assert result.metadata["provider_reference"] == "plink_rec_101"
    assert result.metadata["customer_action_url"] == "https://rzp.io/i/rec101"


@patch("urllib.request.urlopen")
def test_razorpay_executor_unknown_outcome_on_timeout(mock_urlopen):
    mock_urlopen.side_effect = TimeoutError("Connection timed out")

    client = RazorpayClient(key_id="rzp_test_valid", key_secret="secret_valid")
    executor = RazorpayRecoveryExecutor(razorpay_client=client)

    item = RecoveryItem(
        id="item_timeout_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_timeout_101",
        customer_id="cust_1",
        amount_minor=100000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
    )

    with patch.dict(os.environ, {"RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        result = executor.execute(item, "send_payment_link", attempt_number=1)

    assert not result.success
    assert result.error_code == "EXECUTION_UNKNOWN"
    assert result.metadata["reconciliation_required"] is True


def test_verify_signature_valid():
    import hashlib
    import hmac
    secret = "webhook_secret_123"
    raw_body = b'{"event":"payment_link.paid","payload":{}}'
    sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

    # Should not raise exception
    verify_razorpay_signature(raw_body, sig, secret)


def test_verify_signature_invalid():
    secret = "webhook_secret_123"
    raw_body = b'{"event":"payment_link.paid"}'
    with pytest.raises(RazorpaySignatureError):
        verify_razorpay_signature(raw_body, "bad_signature", secret)


@pytest.mark.live_razorpay
def test_live_razorpay_api_call():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or key_id.startswith("rzp_test_placeholder"):
        pytest.skip("RAZORPAY_KEY_ID not configured")

    client = RazorpayClient(key_id=key_id, key_secret=key_secret)
    res = client.create_payment_link(amount_minor=1000, description="Live Pytest Verification")
    assert res["status"] == "created"
    assert res["payment_link_url"].startswith("http")
