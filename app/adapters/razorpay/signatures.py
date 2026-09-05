from __future__ import annotations

import hashlib
import hmac


class RazorpaySignatureError(ValueError):
    """Raised when Razorpay webhook signature verification fails."""


def verify_razorpay_signature(
    raw_body: bytes,
    signature_header: str | None,
    secret: str,
) -> None:
    """Verify a Razorpay webhook signature against the raw request body.

    Razorpay computes: HMAC-SHA256(webhook_secret, raw_body)
    and sends the hex digest in the X-Razorpay-Signature header.

    Args:
        raw_body: The unmodified request body bytes.
        signature_header: Value of the X-Razorpay-Signature header.
        secret: The webhook secret configured in the Razorpay dashboard.

    Raises:
        RazorpaySignatureError: If the signature is missing, empty, or does not match.
    """
    if not raw_body:
        raise RazorpaySignatureError("Request body is empty")
    if not secret:
        raise RazorpaySignatureError("Webhook secret is not configured")
    if not signature_header or not signature_header.strip():
        raise RazorpaySignatureError("Missing X-Razorpay-Signature header")

    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header.strip()):
        raise RazorpaySignatureError("Signature mismatch")
