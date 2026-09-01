"""Shared neutral customer naming utilities for RevPlug."""
from __future__ import annotations

import hashlib
import re

_RAW_CODE_PATTERN = re.compile(r"^(Customer|Acme Corporation|cust)_?\d*$", re.IGNORECASE)


def derive_customer_name(customer_id: str, customer_name: str | None = None) -> str:
    """Return customer_name if valid; otherwise derive a neutral synthetic display identifier.
    
    Never fabricates or maps customer IDs to real enterprise names.
    """
    if customer_name and str(customer_name).strip():
        name_str = str(customer_name).strip()
        if not _RAW_CODE_PATTERN.match(name_str) and not name_str.startswith("cust_"):
            return name_str

    if not customer_id or not str(customer_id).strip():
        return "Evaluation Customer #1001"

    clean_id = str(customer_id).strip()

    # Extract numeric suffix if available (e.g. cust_demo_pivot_101 -> 101)
    num_match = re.search(r"(\d{3,})$", clean_id)
    if num_match:
        return f"Evaluation Customer #{num_match.group(1)}"

    # Deterministic hex hash label
    hash_hex = hashlib.md5(clean_id.encode("utf-8")).hexdigest()[:6].upper()
    return f"Customer #{hash_hex}"
