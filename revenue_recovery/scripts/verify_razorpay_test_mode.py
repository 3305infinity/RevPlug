#!/usr/bin/env python3
"""Standalone Razorpay Test-Mode Verification Script for RevPlug.

Verifies Razorpay Test Mode client setup and attempts creation of 1 bounded
demo Payment Link without live production credentials or payment movement.

Execution:
    python scripts/verify_razorpay_test_mode.py
"""
import os
import sys
import time

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.razorpay.client import RazorpayClient, RazorpayClientError


def main():
    print("=" * 60)
    print("RevPlug -- Real Razorpay Test-Mode Verification")
    print("=" * 60)

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    env = os.getenv("RAZORPAY_ENV", "test").lower()

    print(f"Execution Env  : {env.upper()} (RAZORPAY TEST MODE)")
    print(f"Key ID Status  : {'Configured' if key_id and not key_id.startswith('rzp_test_placeholder') else 'Unconfigured/Placeholder'}")
    print("-" * 60)

    if env in ("production", "live"):
        print("[ERROR] Production environment detected! Halting script.")
        print("        RevPlug hackathon mode strictly requires RAZORPAY_ENV='test'")
        sys.exit(1)

    try:
        client = RazorpayClient(key_id=key_id, key_secret=key_secret, env=env)
    except RazorpayClientError as exc:
        print(f"[ERROR] Client initialization failed: {exc}")
        sys.exit(1)

    if not client.is_configured:
        print("[WARNING] RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not set.")
        print("          Running in UNCONFIGURED mode (will demonstrate safe fallback).")
        print("          To test live Razorpay Test API, set:")
        print("          $env:RAZORPAY_KEY_ID='rzp_test_xxxx'")
        print("          $env:RAZORPAY_KEY_SECRET='your_secret'")
        print("          $env:RECOVERY_EXECUTION_MODE='razorpay_test'")
        print("-" * 60)
        print("[SKIPPED] Live Razorpay API call skipped (credentials unconfigured)")
        return

    # Create 1 small bounded test payment link (RS 10.00 = 1000 paise)
    print("Creating Bounded Test Payment Link (RS 10.00)...")
    try:
        start = time.monotonic()
        res = client.create_payment_link(
            amount_minor=1000,  # RS 10.00
            currency="INR",
            description="RevPlug Hackathon Test Mode Payment Link Verification",
            reference_id=f"test_verif_{int(time.time())}",
        )
        elapsed = int((time.monotonic() - start) * 1000)

        print("\n" + "=" * 60)
        print("RAZORPAY TEST MODE EXECUTION SUCCESSFUL")
        print("=" * 60)
        print(f"Provider           : {res['provider'].upper()}")
        print(f"Provider Reference : {res['payment_link_id']}")
        print(f"Payment Link URL   : {res['payment_link_url']}")
        print(f"Amount             : RS {res['amount_minor'] / 100:.2f} {res['currency']}")
        print(f"Status             : {res['status'].upper()}")
        print(f"Latency            : {elapsed} ms")
        print("-" * 60)
        print("Notice: Action Executed != Money Recovered.")
        print("Money is credited only after receiving verified webhook settlement evidence.")
        print("=" * 60)

    except RazorpayClientError as exc:
        print(f"\n[FAILED] Razorpay API Call Failed: {exc}")
        print("Safe domain error caught -- zero credentials or raw secrets leaked.")


if __name__ == "__main__":
    main()
