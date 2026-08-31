"""Provider-Neutral Revenue Event Adapter & Signature Verification for RevPlug.

Parses incoming webhook event payloads into normalized revenue events across all 8 supported event types:
1. payment_failed
2. payment_succeeded
3. payment_requires_action
4. invoice_overdue
5. invoice_paid
6. subscription_payment_failed
7. dispute_created
8. fraud_flagged
"""
from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class EventSignatureError(Exception):
    """Raised when webhook signature verification fails."""
    pass


class EventParseError(Exception):
    """Raised when raw webhook payload cannot be normalized."""
    pass


SUPPORTED_REVENUE_EVENTS = {
    "payment_failed",
    "payment_succeeded",
    "payment_requires_action",
    "invoice_overdue",
    "invoice_paid",
    "subscription_payment_failed",
    "dispute_created",
    "fraud_flagged",
}


@dataclass(frozen=True)
class NormalizedRevenueEvent:
    event_id: str
    event_type: str
    provider: str
    customer_id: str
    amount_minor: int
    currency: str
    failure_reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_success_event(self) -> bool:
        return self.event_type in {"payment_succeeded", "invoice_paid"}


def verify_event_signature(raw_body: bytes, signature_header: str | None, secret: str) -> bool:
    """Cryptographically verify signature header using HMAC-SHA256."""
    if not signature_header or not secret:
        raise EventSignatureError("Missing signature header or webhook secret")
    
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header.strip()):
        raise EventSignatureError("Webhook signature verification failed")
    return True


def parse_normalized_revenue_event(raw_body: bytes, provider: str = "generic") -> NormalizedRevenueEvent:
    """Parse raw bytes into a NormalizedRevenueEvent."""
    try:
        data = json.loads(raw_body)
    except Exception as exc:
        raise EventParseError(f"Invalid JSON payload: {exc}") from exc

    event_id = str(data.get("id") or data.get("event_id") or data.get("razorpay_event_id") or "evt_anon")
    event_type = str(data.get("event") or data.get("event_type") or "payment_failed")

    # Map legacy event names to normalized set if needed
    event_map = {
        "payment.failed": "payment_failed",
        "payment.captured": "payment_succeeded",
        "payment.authorized": "payment_succeeded",
        "invoice.payment_failed": "subscription_payment_failed",
        "invoice.overdue": "invoice_overdue",
        "invoice.paid": "invoice_paid",
    }
    normalized_type = event_map.get(event_type, event_type)

    if normalized_type not in SUPPORTED_REVENUE_EVENTS:
        normalized_type = "payment_failed"

    payload_data = data.get("payload", data)
    payment_obj = payload_data.get("payment", {}).get("entity", payload_data)

    cust_id = str(
        payment_obj.get("customer_id")
        or data.get("customer_id")
        or "cust_anon_default"
    )
    amt_minor = int(payment_obj.get("amount") or payment_obj.get("amount_minor") or data.get("amount_minor") or 0)
    curr = str(payment_obj.get("currency") or data.get("currency") or "INR")
    reason = str(
        payment_obj.get("error_reason")
        or payment_obj.get("failure_reason")
        or data.get("error_reason")
        or "generic_failure"
    )

    metadata = dict(data.get("metadata", {}))
    if normalized_type == "fraud_flagged":
        metadata["fraud_flag"] = True
    elif normalized_type == "dispute_created":
        metadata["disputed"] = True

    return NormalizedRevenueEvent(
        event_id=event_id,
        event_type=normalized_type,
        provider=provider,
        customer_id=cust_id,
        amount_minor=amt_minor,
        currency=curr,
        failure_reason=reason,
        raw_payload=data,
        metadata=metadata,
    )
