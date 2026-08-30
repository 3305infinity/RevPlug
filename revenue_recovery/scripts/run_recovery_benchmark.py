#!/usr/bin/env python3
"""Stage 14 — Recovery Economics & Batch Simulation CLI.

Executes a canonical 100-case recovery evaluation batch over fixed seed 42.
Measures financial recovery, baseline counterfactual comparison, safety stopping rules,
and operational economics. Generates machine-readable JSON & CSV benchmark artifacts.

Usage:
    python scripts/run_recovery_benchmark.py --size 100 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.evaluation_service import EvaluationService


def main():
    parser = argparse.ArgumentParser(description="Run RevPlug Stage 14 Recovery Economics Benchmark")
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("=" * 75)
    print("RevPlug — STAGE 14 RECOVERY ECONOMICS & BATCH BENCHMARK")
    print("=" * 75)
    print(f"Batch Size : {args.size}")
    print(f"Seed       : {args.seed}")
    print("-" * 75)

    eval_service = EvaluationService(ai_enabled=True, policy_mode="B_ai_assisted")
    start = time.monotonic()
    result = eval_service.run_batch_evaluation(count=args.size, seed=args.seed)
    elapsed = round(time.monotonic() - start, 2)

    revplug = result.revplug
    baseline = result.baseline
    comp = result.comparison

    gross_at_risk = revplug.total_amount_at_risk
    baseline_rec = baseline.actual_recovered
    revplug_rec = revplug.actual_recovered
    inc_rec = comp.absolute_recovery_difference
    uplift_pct = comp.relative_improvement * 100.0 if comp.relative_improvement is not None else 0.0

    print("\n--- RECOVERY ECONOMICS RESULTS ---")
    print(f"Total Amount at Risk         : RS {gross_at_risk / 100:,.2f}")
    print(f"Baseline Recovered           : RS {baseline_rec / 100:,.2f} ({baseline.recovery_rate * 100:.2f}%)")
    print(f"RevPlug Verified Recovered   : RS {revplug_rec / 100:,.2f} ({revplug.recovery_rate * 100:.2f}%)")
    print(f"Incremental Money Recovered  : RS {inc_rec / 100:,.2f}")
    print(f"Recovery Uplift              : +{uplift_pct:.2f}%")
    print(f"Execution Time               : {elapsed} seconds")

    print("\n--- SAFETY & STOPPING RULES ---")
    print(f"Opt-out Stops                : {revplug.safety_violations.get('opt_out_contact_violations', 0)} / {len(get_opted_out_customers(generate_evaluation_dataset(args.size, args.seed)))} opted out")
    print(f"Fraud Stops                  : {revplug.safety_violations.get('fraud_retry_violations', 0)} violations (0 unsafe retries permitted)")
    print(f"Total Policy Safety Stops    : {revplug.stopped_count}")
    print(f"Human Escalations            : {revplug.escalated_count}")
    print(f"Total Safety Violations      : {revplug.safety_violations.get('total_safety_violations', 0)}")

    print("\n--- FINANCIAL INVARIANT VERIFICATION ---")
    invariant_passed = (0 <= revplug_rec <= gross_at_risk)
    print(f"Invariant (0 <= Recovered <= At Risk): {'PASS' if invariant_passed else 'FAIL'}")

    artifact_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts")
    os.makedirs(artifact_dir, exist_ok=True)

    # 1. Write JSON artifact
    json_path = os.path.join(artifact_dir, "recovery_benchmark.json")
    benchmark_data = {
        "dataset_version": "v1-stage14-batch",
        "seed": args.seed,
        "batch_size": args.size,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gross_at_risk_minor": gross_at_risk,
        "baseline_recovered_minor": baseline_rec,
        "revplug_recovered_minor": revplug_rec,
        "incremental_recovered_minor": inc_rec,
        "recovery_uplift_percent": round(uplift_pct, 2),
        "revplug_recovery_rate": round(revplug.recovery_rate, 4),
        "baseline_recovery_rate": round(baseline.recovery_rate, 4),
        "stopped_count": revplug.stopped_count,
        "escalated_count": revplug.escalated_count,
        "safety_violations": revplug.safety_violations.get("total_safety_violations", 0),
        "per_case_summary": result.per_case,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    # 2. Write CSV export artifact
    csv_path = os.path.join(artifact_dir, "recovery_benchmark.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id",
            "failure_category",
            "amount_at_risk_rs",
            "revplug_action",
            "policy_result",
            "actual_recovered_rs",
            "stop_reason",
            "escalation_reason",
        ])
        for c in result.per_case:
            writer.writerow([
                c.get("case_id", ""),
                c.get("failure_category", ""),
                f"{c.get('amount_at_risk', 0) / 100:.2f}",
                c.get("proposed_action", ""),
                c.get("safety_decision", ""),
                f"{c.get('actual_recovered', 0) / 100:.2f}",
                c.get("stop_reason", ""),
                c.get("escalation_reason", ""),
            ])

    print(f"\n[SUCCESS] Stage 14 Batch Benchmark Complete!")
    print(f"          JSON Artifact: {os.path.abspath(json_path)}")
    print(f"          CSV Artifact : {os.path.abspath(csv_path)}")
    print("=" * 75)


if __name__ == "__main__":
    from app.datasets.synthetic import generate_evaluation_dataset, get_opted_out_customers
    main()
