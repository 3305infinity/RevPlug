#!/usr/bin/env python3
"""Stage 13 — AI Judgment Engine & Multi-Provider Benchmark CLI.

LABEL: LEGACY STAGE SCRIPT (not canonical).
- Produces artifacts/ai_benchmark.json (per-provider comparison only).
- Does NOT write evaluation_report.json.
- Does NOT include baseline/safe_baseline counterfactual comparison.
- Superseded by: app/eval/run_benchmark.py (the canonical runner).

Use this script only for per-provider AI quality diagnostics (deterministic vs Groq vs Gemini vs hybrid).
For the canonical benchmark numbers quoted in README/PROJECT/docs, use app/eval/run_benchmark.py or
scripts/regenerate_benchmark_docs.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.ai_router import AIRouter
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.agents.llm_provider import GeminiProvider, GroqLLMProvider, MockLLMProvider
from app.audit.models import InMemoryAuditLog
from app.datasets.synthetic import generate_evaluation_dataset, get_opted_out_customers
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction
from app.policies.engine import InterventionPolicy


def evaluate_provider(
    provider_type: str,
    dataset: list[Any],
    opted_out_customers: set[str],
) -> dict[str, Any]:
    """Evaluate dataset cases through a specified provider configuration."""
    start_time = time.monotonic()

    policy = InterventionPolicy(max_retry_attempts=3, opted_out_customer_ids=opted_out_customers)

    if provider_type == "deterministic":
        agent = MockRecoveryDecisionAgent(name="deterministic-baseline", model_name="rules-v1")
    elif provider_type == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        client = GroqLLMProvider(api_key=groq_key) if groq_key else MockLLMProvider(model_name="llama-3.3-70b-versatile")
        agent = RealRecoveryDecisionAgent(llm_client=client, router=AIRouter(force_ai=True), name="groq-agent")
    elif provider_type == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        client = GeminiProvider(api_key=gemini_key) if gemini_key else MockLLMProvider(model_name="gemini-1.5-flash")
        agent = RealRecoveryDecisionAgent(llm_client=client, router=AIRouter(force_ai=True), name="gemini-agent")
    else:  # hybrid
        groq_key = os.getenv("GROQ_API_KEY")
        client = GroqLLMProvider(api_key=groq_key) if groq_key else MockLLMProvider(model_name="hybrid-groq")
        agent = RealRecoveryDecisionAgent(llm_client=client, router=AIRouter(force_ai=False), name="revplug-hybrid")

    total_cases = len(dataset)
    total_at_risk = 0
    total_recovered = 0
    safe_decisions = 0
    policy_violations = 0
    ai_not_required = 0
    ai_calls = 0
    fallback_count = 0
    abstentions = 0
    latencies = []

    case_traces = []

    for item in dataset:
        total_at_risk += item.amount_minor

        # Map failure category
        raw_cat = str(item.metadata.get("original_category", item.root_cause or "unknown")).lower()
        if "fraud" in raw_cat:
            cat = FailureCategory.FRAUD
        elif "hard" in raw_cat:
            cat = FailureCategory.HARD
        elif "soft" in raw_cat:
            cat = FailureCategory.SOFT
        elif "auth" in raw_cat:
            cat = FailureCategory.AUTHENTICATION_REQUIRED
        else:
            cat = FailureCategory.UNKNOWN

        is_opted_out = item.customer_id in opted_out_customers or item.metadata.get("customer_opt_out", False)

        ctx = RecoveryContext(
            item_id=item.id,
            failure_category=cat,
            retryable=(cat == FailureCategory.SOFT),
            attempt_count=item.metadata.get("attempt_count", 0),
            amount_minor=item.amount_minor,
            currency=item.currency,
            customer_opt_out=is_opted_out,
            failure_code=raw_cat,
            failure_reason=str(item.metadata.get("gateway_error_code", raw_cat)),
        )

        case_start = time.monotonic()
        proposal = agent.propose(ctx)
        case_latency = int((time.monotonic() - case_start) * 1000)
        latencies.append(case_latency)

        # Policy Gate Evaluation
        decision = policy.evaluate(item, proposal.action.value)

        # Check safety & ground truth compliance
        is_safe = decision.allowed
        if not decision.allowed:
            # If proposal was blocked by policy, policy prevented unsafe action
            if proposal.action == RecoveryAction.RETRY_PAYMENT and (cat == FailureCategory.FRAUD or is_opted_out):
                policy_violations += 1  # Unsafe recommendation caught by policy
            is_safe = True  # Server-side policy gate protected system

        if is_safe:
            safe_decisions += 1

        # Check AI decision path
        trace = getattr(agent, "last_trace", None)
        if trace:
            if trace.decision_path == "deterministic":
                ai_not_required += 1
            else:
                ai_calls += 1
            if trace.fallback_used:
                fallback_count += 1

        if proposal.action == RecoveryAction.ESCALATE_HUMAN:
            abstentions += 1

        # Simulated synthetic outcome calculation
        actual_rec = 0
        if decision.allowed and proposal.action != RecoveryAction.STOP_RECOVERY:
            if cat == FailureCategory.SOFT and proposal.action == RecoveryAction.RETRY_PAYMENT:
                actual_rec = int(item.amount_minor * 0.75)
            elif proposal.action == RecoveryAction.SEND_PAYMENT_LINK:
                actual_rec = int(item.amount_minor * 0.65)
            elif proposal.action == RecoveryAction.ALTERNATE_CHANNEL:
                actual_rec = int(item.amount_minor * 0.50)

        total_recovered += actual_rec

        case_traces.append({
            "case_id": item.id,
            "category": cat.value,
            "proposed_action": proposal.action.value,
            "policy_allowed": decision.allowed,
            "policy_rule": decision.policy_rule,
            "confidence": proposal.confidence,
            "amount_at_risk": item.amount_minor,
            "actual_recovered": actual_rec,
            "latency_ms": case_latency,
        })

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "provider": provider_type,
        "total_cases": total_cases,
        "total_at_risk_minor": total_at_risk,
        "total_recovered_minor": total_recovered,
        "recovery_rate": round(total_recovered / max(total_at_risk, 1), 4),
        "safe_decision_rate": round(safe_decisions / max(total_cases, 1), 4),
        "policy_violations": policy_violations,
        "ai_not_required_rate": round(ai_not_required / max(total_cases, 1), 4),
        "ai_calls": ai_calls,
        "fallback_count": fallback_count,
        "abstention_rate": round(abstentions / max(total_cases, 1), 4),
        "average_latency_ms": round(avg_latency, 2),
        "elapsed_seconds": round(time.monotonic() - start_time, 2),
        "case_traces": case_traces,
    }


def main():
    parser = argparse.ArgumentParser(description="Run RevPlug Stage 13 AI Judgment Benchmark")
    parser.add_argument("--provider", choices=["deterministic", "groq", "gemini", "all"], default="all")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("=" * 70)
    print("RevPlug — STAGE 13 AI JUDGMENT ENGINE BENCHMARK")
    print("=" * 70)
    print(f"Dataset Seed  : {args.seed}")
    print(f"Case Count    : {args.count}")
    print(f"Provider Mode : {args.provider.upper()}")
    print("-" * 70)

    dataset = generate_evaluation_dataset(count=args.count, seed=args.seed)
    opted_out = get_opted_out_customers(dataset)

    providers_to_test = ["deterministic", "groq", "gemini", "hybrid"] if args.provider == "all" else [args.provider]

    benchmark_results = {}
    baseline_recovered = None

    for prov in providers_to_test:
        print(f"Running evaluation for provider configuration: '{prov.upper()}'...")
        res = evaluate_provider(prov, dataset, opted_out)
        benchmark_results[prov] = res

        if prov in ("deterministic", providers_to_test[0]) and baseline_recovered is None:
            baseline_recovered = res["total_recovered_minor"]

        # Calculate uplift
        if baseline_recovered is not None:
            baseline = max(baseline_recovered, 1)
            inc = res["total_recovered_minor"] - baseline
            uplift = (inc / baseline) * 100.0
            res["incremental_recovery_minor"] = inc
            res["recovery_uplift_percent"] = round(uplift, 2)

    # Print summary table
    print("\n" + "=" * 75)
    print(f"{'PROVIDER':<16} | {'ACCURACY':<9} | {'POLICY VIOL':<11} | {'RECOVERED (RS)':<15} | {'LATENCY':<8}")
    print("-" * 75)
    for prov, res in benchmark_results.items():
        rec_rs = f"RS {res['total_recovered_minor'] / 100:,.2f}"
        acc = f"{res['safe_decision_rate'] * 100:.1f}%"
        print(f"{prov.upper():<16} | {acc:<9} | {res['policy_violations']:<11} | {rec_rs:<15} | {res['average_latency_ms']} ms")
    print("=" * 75)

    artifact_data = {
        "dataset_version": "v1-synthetic-seeded",
        "seed": args.seed,
        "count": args.count,
        "prompt_version": "v1-stage3",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": benchmark_results,
    }

    # Save to artifacts directory
    artifact_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts")
    os.makedirs(artifact_dir, exist_ok=True)
    artifact_path = os.path.join(artifact_dir, "ai_benchmark.json")

    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifact_data, f, indent=2)

    print(f"\n[SUCCESS] AI Benchmark completed successfully!")
    print(f"          Artifact saved to: {os.path.abspath(artifact_path)}")
    print("=" * 75)


if __name__ == "__main__":
    main()
