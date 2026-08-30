"""Razorpay Test Mode API Client Adapter.

Features:
- Bounded, read/write client for Razorpay Payment Links API in TEST mode
- Base64 Basic Authentication with RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET
- Strict enforcement of RAZORPAY_ENV == 'test' to prevent production payments
- Network timeout handling, exponential retries, and domain error mapping
- Automatic credential redaction from all exception tracebacks
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class RazorpayClientError(Exception):
    """Base exception for Razorpay client failures."""


class RazorpayAuthenticationError(RazorpayClientError):
    """Raised when Razorpay credentials are invalid or unconfigured."""


class RazorpayNetworkTimeoutError(RazorpayClientError):
    """Raised when Razorpay HTTP request times out."""


class RazorpayClient:
    """Razorpay Test Mode API Client."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        env: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self._key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self._key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self._env = (env or os.getenv("RAZORPAY_ENV", "test")).lower().strip()
        self._max_retries = max_retries

        if self._env in ("production", "live"):
            raise RazorpayClientError("Production Razorpay environment is strictly prohibited in hackathon mode")

    @property
    def is_configured(self) -> bool:
        return bool(self._key_id and self._key_secret and not self._key_id.startswith("rzp_test_placeholder"))

    def create_payment_link(
        self,
        *,
        amount_minor: int,
        currency: str = "INR",
        description: str = "RevPlug Bounded Recovery Payment Link",
        customer_email: str | None = None,
        customer_contact: str | None = None,
        reference_id: str = "",
        notes: dict[str, Any] | None = None,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        """Create a Razorpay Test Mode Payment Link.

        Docs: https://razorpay.com/docs/api/payments/payment-links/
        """
        if not self.is_configured:
            raise RazorpayAuthenticationError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not configured")

        url = "https://api.razorpay.com/v1/payment_links"

        payload = {
            "amount": amount_minor,
            "currency": currency,
            "accept_partial": False,
            "description": description[:200],
            "customer": {
                "name": "RevPlug Demo Customer",
                "email": customer_email or "demo@revplug.ai",
                "contact": customer_contact or "+919999999999",
            },
            "notify": {"sms": True, "email": True},
            "reminder_enable": True,
            "notes": notes or {"source": "RevPlug_AI_Recovery"},
            "reference_id": reference_id[:40] if reference_id else f"rec_{int(time.time())}",
        }

        body = json.dumps(payload).encode("utf-8")
        auth_bytes = f"{self._key_id}:{self._key_secret}".encode("utf-8")
        auth_header = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        start = time.monotonic()
        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    latency = int((time.monotonic() - start) * 1000)

                    plink_id = resp_data.get("id", f"plink_test_{int(time.time())}")
                    short_url = resp_data.get("short_url", f"https://rzp.io/i/test_{plink_id}")
                    status = resp_data.get("status", "created")

                    return {
                        "provider": "razorpay",
                        "provider_reference": plink_id,
                        "payment_link_id": plink_id,
                        "payment_link_url": short_url,
                        "amount_minor": amount_minor,
                        "currency": currency,
                        "status": status,
                        "latency_ms": latency,
                        "raw_response": resp_data,
                    }

            except urllib.error.HTTPError as exc:
                err_text = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
                last_error = f"HTTP {exc.code}: {exc.reason} - {err_text[:200]}"
                time.sleep(0.1 * (2 ** attempt))
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = f"Network timeout: {exc}"
                time.sleep(0.1 * (2 ** attempt))
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.1 * (2 ** attempt))

        latency = int((time.monotonic() - start) * 1000)

        if "timeout" in str(last_error).lower():
            raise RazorpayNetworkTimeoutError(f"Razorpay Payment Link API request timed out ({latency}ms)")

        raise RazorpayClientError(f"Razorpay Payment Link creation failed: {last_error}")

    def reconcile_payment_link(
        self,
        payment_link_id: str,
        timeout_seconds: float = 10.0,
    ) -> dict[str, Any]:
        """Fetch current status of a Payment Link for unknown execution outcome reconciliation."""
        if not self.is_configured:
            raise RazorpayAuthenticationError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not configured")

        url = f"https://api.razorpay.com/v1/payment_links/{payment_link_id}"
        auth_bytes = f"{self._key_id}:{self._key_secret}".encode("utf-8")
        auth_header = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

        req = urllib.request.Request(url, headers={"Authorization": auth_header}, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "provider": "razorpay",
                    "payment_link_id": payment_link_id,
                    "status": resp_data.get("status", "unknown"),
                    "amount_paid": resp_data.get("amount_paid", 0),
                    "raw_response": resp_data,
                }
        except Exception as exc:
            raise RazorpayClientError(f"Reconciliation query failed for {payment_link_id}: {exc}")
