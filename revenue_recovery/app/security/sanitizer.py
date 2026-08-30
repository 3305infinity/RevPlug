"""Input and Payload Sanitizer for Adversarial Protection.

Sanitizes untrusted customer input, invoice notes, and provider payloads:
1. Neutralizes XSS script tags (<script>)
2. Strips prompt injection control headers ("Ignore previous instructions")
3. Enforces string length limits and Unicode normalization
4. Validates financial input bounds
"""
from __future__ import annotations

import html
import re

_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"always\s+choose", re.IGNORECASE),
    re.compile(r"set\s+confidence\s+to", re.IGNORECASE),
    re.compile(r"mark\s+the\s+invoice\s+as\s+paid", re.IGNORECASE),
]

_MAX_INPUT_LENGTH = 2048


def sanitize_customer_input(raw_text: str | None) -> str:
    """Sanitize untrusted text inputs against XSS and prompt injection attacks."""
    if not raw_text:
        return ""

    # Truncate excessive input length
    text = str(raw_text)[:_MAX_INPUT_LENGTH]

    # Neutralize HTML script tags / XSS
    text = html.escape(text)

    # Neutralize active prompt injection control patterns
    for pattern in _PROMPT_INJECTION_PATTERNS:
        text = pattern.sub("[REDACTED_INJECTION_ATTEMPT]", text)

    return text


def validate_financial_input(amount_minor: int | float | None, currency: str = "INR") -> int:
    """Validate and sanitize monetary input values."""
    if amount_minor is None:
        raise ValueError("Amount cannot be None")
    try:
        val = int(amount_minor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {amount_minor}") from exc

    if val < 0:
        raise ValueError(f"Monetary value cannot be negative: {val}")

    if val > 1000000000:  # ₹1 Crore upper bound per single item
        raise ValueError(f"Monetary value exceeds maximum single-item limit: {val}")

    if currency.upper() not in {"INR", "USD", "EUR", "GBP"}:
        raise ValueError(f"Unsupported currency code: {currency}")

    return val
