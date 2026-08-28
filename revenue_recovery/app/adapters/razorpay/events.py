from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class RazorpayEventError(ValueError):
    """Raised when a Razorpay event cannot be parsed."""


@dataclass(frozen=True, slots=True)
class RazorpayPaymentFailure:
    """Razorpay-specific payment failure details.

    This is an adapter-internal representation. It is NOT a domain model.
    """

    razorpay_event_id: str
    razorpay_payment_id: str
    amount_minor: int
    currency: str
    error_code: str | None
    error_description: str | None
    error_source: str | None
    error_step: str | None
    error_reason: str | None
    payment_method: str | None
    occurred_at: datetime
    raw_payload: dict[str, Any]


def _get_nested(payload: dict[str, Any], *keys: str) -> Any:
    """Safely traverse nested dicts."""
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def parse_razorpay_event(raw_body: bytes) -> RazorpayPaymentFailure:
    """Parse a Razorpay webhook payload into a structured representation.

    Currently supports only the payment.failed event type.

    Args:
        raw_body: The raw request body bytes.

    Returns:
        RazorpayPaymentFailure with extracted fields.

    Raises:
        RazorpayEventError: If the payload is malformed or not a payment.failed event.
    """
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RazorpayEventError("Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise RazorpayEventError("Payload must be a JSON object")

    event_type = payload.get("event")
    if event_type != "payment.failed":
        raise RazorpayEventError(
            f"Unsupported event type: {event_type!r}. Only 'payment.failed' is supported."
        )

    razorpay_event_id = payload.get("id")
    if not razorpay_event_id or not isinstance(razorpay_event_id, str):
        raise RazorpayEventError("Missing or invalid event id")

    payment_entity = _get_nested(payload, "payload", "payment", "entity")
    if not isinstance(payment_entity, dict):
        raise RazorpayEventError("Missing payload.payment.entity")

    payment_id = payment_entity.get("id")
    if not payment_id or not isinstance(payment_id, str):
        raise RazorpayEventError("Missing or invalid payment id")

    amount_minor = payment_entity.get("amount", 0)
    if not isinstance(amount_minor, int):
        raise RazorpayEventError("Payment amount must be an integer")

    currency = payment_entity.get("currency", "")
    if not isinstance(currency, str) or len(currency) != 3:
        raise RazorpayEventError("Currency must be a 3-letter code")

    occurred_at = _parse_iso_timestamp(payment_entity.get("created_at"))
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)

    return RazorpayPaymentFailure(
        razorpay_event_id=razorpay_event_id,
        razorpay_payment_id=payment_id,
        amount_minor=amount_minor,
        currency=currency,
        error_code=payment_entity.get("error_code"),
        error_description=payment_entity.get("error_description"),
        error_source=payment_entity.get("error_source"),
        error_step=payment_entity.get("error_step"),
        error_reason=payment_entity.get("error_reason"),
        payment_method=payment_entity.get("method"),
        occurred_at=occurred_at,
        raw_payload=payload,
    )
