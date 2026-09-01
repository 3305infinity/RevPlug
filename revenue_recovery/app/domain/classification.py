"""Canonical Domain Classification for Failure Reasons and Root Causes."""
from __future__ import annotations

from typing import Any

CANONICAL_FAILURE_MAPPINGS = {
    # Soft / Gateway Timeout / Network
    "soft_gateway_timeout": "SOFT_GATEWAY_TIMEOUT",
    "gateway_timeout": "SOFT_GATEWAY_TIMEOUT",
    "payment_timed_out": "SOFT_GATEWAY_TIMEOUT",
    "network_error": "SOFT_GATEWAY_TIMEOUT",
    "gateway_error": "SOFT_GATEWAY_TIMEOUT",

    # Authentication / Authorization
    "authentication_required": "AUTHENTICATION_REQUIRED",
    "auth_required": "AUTHENTICATION_REQUIRED",
    "3ds_failed": "AUTHENTICATION_REQUIRED",
    "otp_expired": "AUTHENTICATION_REQUIRED",
    "customer_abandoned_auth": "AUTHENTICATION_REQUIRED",

    # Insufficient Funds
    "insufficient_funds": "INSUFFICIENT_FUNDS",
    "low_balance": "INSUFFICIENT_FUNDS",

    # Hard / Expired Card
    "expired_card": "HARD_EXPIRED_CARD",
    "card_expired": "HARD_EXPIRED_CARD",
    "hard_decline": "HARD_EXPIRED_CARD",
    "invalid_card": "HARD_EXPIRED_CARD",
    "account_closed": "HARD_EXPIRED_CARD",

    # Fraud & Security
    "fraud_flagged": "FRAUD_BLOCK",
    "fraud_risk": "FRAUD_BLOCK",
    "security_or_fraud": "FRAUD_BLOCK",
    "risk_block": "FRAUD_BLOCK",

    # Consent & Opt-Out
    "customer_opt_out": "CONSENT_BLOCK",
    "opt_out": "CONSENT_BLOCK",
    "no_consent": "CONSENT_BLOCK",

    # Dispute / Chargeback
    "invoice_disputed": "DISPUTE_RAISED",
    "disputed": "DISPUTE_RAISED",
    "chargeback": "DISPUTE_RAISED",

    # Checkout Abandonment
    "checkout_abandoned": "CHECKOUT_ABANDONMENT",
    "cart_abandoned": "CHECKOUT_ABANDONMENT",
}


def classify_root_cause(reason: str | None, context: dict[str, Any] | None = None) -> str:
    """Map any incoming failure reason or event string into a canonical root cause code.
    
    Returns a standard code or UNCLASSIFIED with explicit reason if unknown.
    """
    if not reason:
        return "UNCLASSIFIED: Missing failure reason"

    cleaned = str(reason).strip().lower()

    if cleaned in CANONICAL_FAILURE_MAPPINGS:
        return CANONICAL_FAILURE_MAPPINGS[cleaned]

    # Partial keyword matching fallback
    if "opt_out" in cleaned or "consent" in cleaned:
        return "CONSENT_BLOCK"
    if "fraud" in cleaned or "risk" in cleaned:
        return "FRAUD_BLOCK"
    if "auth" in cleaned or "3ds" in cleaned or "otp" in cleaned:
        return "AUTHENTICATION_REQUIRED"
    if "timeout" in cleaned or "gateway" in cleaned or "network" in cleaned:
        return "SOFT_GATEWAY_TIMEOUT"
    if "fund" in cleaned or "balance" in cleaned:
        return "INSUFFICIENT_FUNDS"
    if "expire" in cleaned or "hard" in cleaned:
        return "HARD_EXPIRED_CARD"
    if "disput" in cleaned or "chargeback" in cleaned:
        return "DISPUTE_RAISED"
    if "abandon" in cleaned:
        return "CHECKOUT_ABANDONMENT"

    return f"UNCLASSIFIED: {reason}"
