"""Shared enterprise customer naming utilities for RevPlug."""
from __future__ import annotations

import hashlib

REALISTIC_ENTERPRISE_NAMES = [
    "Swiggy Enterprise Logistics",
    "Zomato Merchant Solutions",
    "Acme Global Pvt Ltd",
    "Flipkart Merchant Services",
    "Reliance Retail Tech",
    "Paytm Business Solutions",
    "InMobi Media Pvt Ltd",
    "Razorpay Enterprise Direct",
    "PhonePe Merchant Pay",
    "Freshworks SaaS Client",
]


def derive_customer_name(customer_id: str, customer_name: str | None = None) -> str:
    """Return customer_name if non-empty; otherwise deterministically map customer_id to a believable name."""
    if customer_name and str(customer_name).strip():
        return str(customer_name).strip()
    if not customer_id:
        return REALISTIC_ENTERPRISE_NAMES[0]
    idx = int(hashlib.md5(str(customer_id).encode("utf-8")).hexdigest(), 16) % len(REALISTIC_ENTERPRISE_NAMES)
    return REALISTIC_ENTERPRISE_NAMES[idx]
