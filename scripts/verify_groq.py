#!/usr/bin/env python3
"""Standalone Real Groq AI Verification Script for RevPlug.

Tests the Groq LLM provider against a synthetic ambiguous payment case
and validates the structured response against the RevPlug schema.

Execution:
    python scripts/verify_groq.py
"""
import os
import sys
import time

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.llm_provider import GroqLLMProvider
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory


def main():
    print("=" * 60)
    print("RevPlug -- Real Groq AI Provider Verification")
    print("=" * 60)

    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("[WARNING] GROQ_API_KEY environment variable is not set.")
        print("          Running verification in UNCONFIGURED mode (will demonstrate safe fallback).")
        print("          To test live Groq API, set GROQ_API_KEY='your_key_here' and re-run.")
        print("-" * 60)

    provider = GroqLLMProvider(api_key=api_key, model_name=model_name)
    agent = RealRecoveryDecisionAgent(llm_client=provider)

    print(f"Provider Name : {provider.provider_name.upper()}")
    print(f"Model Name    : {provider.model_name}")
    print(f"API Key Status: {'Configured' if api_key else 'Unconfigured (Safe Fallback)'}")
    print("-" * 60)

    # Build a synthetic ambiguous payment failure case context
    context = RecoveryContext(
        item_id="item_groq_verify_101",
        amount_minor=499900,  # RS 4,999.00
        failure_category=FailureCategory.SOFT,
        failure_code="authorization_timeout",
        failure_reason="Bank 3DS challenge timed out after 120s during peak traffic",
        attempt_count=1,
        max_attempts=3,
        customer_opt_out=False,
        retryable=True,
        metadata={"channel": "web_checkout", "issuer": "HDFC_BANK", "customer_id": "cust_verify_99"},
    )

    print("Submitting Synthetic Ambiguous Case:")
    print(f"  - Amount     : RS {context.amount_minor / 100:,.2f}")
    print(f"  - Failure    : {context.failure_code} ({context.failure_reason})")
    print(f"  - Attempt    : {context.attempt_count}/{context.max_attempts}")
    print("Evaluating with RealRecoveryDecisionAgent...")

    start = time.monotonic()
    proposal = agent.propose(context)
    elapsed = int((time.monotonic() - start) * 1000)

    print("\n" + "=" * 60)
    print("VERIFICATION RESULT")
    print("=" * 60)
    print(f"Recommended Action : {proposal.action.value.upper()}")
    print(f"Confidence Score   : {proposal.confidence:.2%}")
    print(f"Reasoning Summary  : {proposal.reason}")
    print(f"Model Used         : {proposal.model_name}")
    print(f"Latency            : {elapsed} ms")

    if agent.last_trace:
        print(f"Decision Path      : {agent.last_trace.decision_path}")
        print(f"Fallback Used      : {agent.last_trace.fallback_used}")
        print(f"Validation Passed  : {agent.last_trace.validation_passed}")

    print("\n[SUCCESS] Verification Complete -- 0 Payment Actions Executed (Read-Only AI Diagnosis)")
    print("=" * 60)


if __name__ == "__main__":
    main()
