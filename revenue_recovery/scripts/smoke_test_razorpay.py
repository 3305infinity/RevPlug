"""
Local end-to-end smoke test for the Razorpay webhook endpoint.

Sends a synthetic payment.failed payload to a running FastAPI/Uvicorn server
at http://127.0.0.1:8000/webhooks/razorpay and prints the response.

Usage (PowerShell):

    # 1. Start the server with the same secret the script will use:
    $env:RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

    # 2. In another terminal, run the smoke test:
    python -m scripts.smoke_test_razorpay

    # 3. To override the secret or URL:
    $env:RAZORPAY_WEBHOOK_SECRET = "another_secret"
    $env:SMOKE_TEST_URL = "http://127.0.0.1:9000/webhooks/razorpay"
    python -m scripts.smoke_test_razorpay

Expected output on success:

    HTTP 200
    {"status":"processed","audit_event_count":N,...}

This script:
- Never calls the real Razorpay API
- Uses only synthetic data
- Uses the same HMAC-SHA256 algorithm and payload format as the adapter
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
URL = os.environ.get("SMOKE_TEST_URL", "http://127.0.0.1:8000/webhooks/razorpay")

# Fixed stable synthetic identifiers — deterministic across runs.
EVENT_ID = "evt_smoke_001"
PAYMENT_ID = "pay_smoke_001"
AMOUNT_MINOR = 50000  # 500.00
CURRENCY = "INR"


# ---------------------------------------------------------------------------
# Synthetic Razorpay payment.failed payload
# ---------------------------------------------------------------------------
# This payload uses the exact field names and structure that our adapter
# (app/adapters/razorpay/events.py) expects. Mirrors the official Razorpay
# webhook payload format.

def _build_payload() -> dict[str, object]:
    now = int(datetime.now(timezone.utc).timestamp())
    return {
        "entity": "event",
        "account_id": "acc_SMOKE_TEST",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": EVENT_ID,
        "created_at": now,
        "payload": {
            "payment": {
                "entity": {
                    "id": PAYMENT_ID,
                    "entity": "payment",
                    "amount": AMOUNT_MINOR,
                    "currency": CURRENCY,
                    "status": "failed",
                    "order_id": "order_smoke_001",
                    "invoice_id": None,
                    "international": False,
                    "method": "card",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Smoke test payment",
                    "card_id": None,
                    "bank": "HDFC",
                    "wallet": None,
                    "vpa": None,
                    "email": "smoke.test@example.invalid",
                    "contact": "+910000000000",
                    "notes": {"source": "smoke_test"},
                    "fee": None,
                    "tax": None,
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed (synthetic smoke test)",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_timed_out",
                    "acquirer_data": {"bank_transaction_id": None},
                    "created_at": now,
                }
            }
        },
    }


def _build_hard_payload() -> dict[str, object]:
    """A HARD failure payload for testing the denied path."""
    p = _build_payload()
    p["id"] = "evt_smoke_hard_001"
    p["payload"]["payment"]["entity"]["id"] = "pay_smoke_hard_001"
    p["payload"]["payment"]["entity"]["error_reason"] = "card_declined"
    p["payload"]["payment"]["entity"]["error_description"] = "Card declined by bank"
    return p


# ---------------------------------------------------------------------------
# Signature calculation — matches app/adapters/razorpay/signatures.py
# ---------------------------------------------------------------------------

def _sign(raw_body: bytes, secret: str) -> str:
    """HMAC-SHA256 of the raw body, hex-encoded."""
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _send(payload: dict, label: str) -> int:
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = _sign(raw_body, SECRET)

    print(f"\n{'=' * 66}")
    print(f"  RAZORPAY WEBHOOK SMOKE TEST — {label}")
    print(f"{'=' * 66}")
    print(f"  URL:           {URL}")
    print(f"  Secret source: {'RAZORPAY_WEBHOOK_SECRET env' if os.environ.get('RAZORPAY_WEBHOOK_SECRET') else 'default (test_webhook_secret)'}")
    print(f"  Event ID:      {payload['id']}")
    print(f"  Payment ID:    {payload['payload']['payment']['entity']['id']}")
    print(f"  Amount:        {AMOUNT_MINOR} minor units ({CURRENCY})")
    print(f"  Error reason:  {payload['payload']['payment']['entity']['error_reason']}")
    print(f"  Body bytes:    {len(raw_body)}")
    print(f"  Signature:     {signature[:16]}...")
    print(f"{'-' * 66}")

    try:
        resp = requests.post(
            URL,
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError as exc:
        print(f"HTTP STATUS: connection failed ({exc})")
        print()
        print("Is the server running? Start it with:")
        print('  $env:RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"')
        print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return 1

    print(f"HTTP {resp.status_code}")
    print(resp.text)
    print(f"{'=' * 66}")

    if resp.status_code == 200:
        data = resp.json()
        status = data.get("status")
        if status == "processed":
            print(f"  RESULT: processed — agent proposed {data.get('proposed_action')}, policy={data.get('policy_allowed')}")
            return 0
        if status == "duplicate":
            print("  RESULT: duplicate (event already processed)")
            return 0
    print("  RESULT: not processed")
    return 1


def main() -> int:
    """Send a SOFT (allowed) and HARD (denied) smoke payload."""
    rc1 = _send(_build_payload(), "SOFT FAILURE (expected: retry_payment, allowed)")
    rc2 = _send(_build_hard_payload(), "HARD FAILURE (expected: escalate/send_link, policy-dependent)")
    return rc1 or rc2


if __name__ == "__main__":
    sys.exit(main())
