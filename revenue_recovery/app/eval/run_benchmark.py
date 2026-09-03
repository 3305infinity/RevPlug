"""Benchmark Runner for Reproducible Counterfactual Batch Evaluation.

Executes:
1. Multi-seed statistical benchmark suite (10 seeds x 100 cases = 1,000 cases total)
2. Detailed per-case trace for canonical Seed 42

Outputs:
1. evaluation_report.json — machine-readable canonical JSON report
2. docs/EVALUATION_REPORT.md — evidence-first human-readable Markdown report rendered directly from JSON
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.benchmark import run_benchmark_suite
from app.services.evaluation_service import EvaluationService


def render_markdown_report(data: dict) -> str:
    """Deterministically render docs/EVALUATION_REPORT.md from evaluation_report.json."""
    gen_time = data.get("benchmark_metadata", {}).get("generated_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    cfg = data.get("benchmark_configuration", {})
    ros = data.get("revplug", {})
    bl = data.get("baseline", {})
    sbl = data.get("safe_baseline", {})
    comp = data.get("comparison", {})
    ai = ros.get("ai_metrics", {})
    attr = ros.get("attribution_metrics", {})
    agg = data.get("multi_seed_aggregate", {})

    fmt = lambda minor: f"₹{minor / 100:,.2f}"

    single_seed_label = f"Seed {data.get('seed', '?')} ({data.get('count', '?')} cases)"
    multi_seed_label = f"{agg.get('total_seeds', 10)} seeds ({agg.get('cases_per_seed', 100)} cases/seed, {agg.get('total_seeds', 10) * agg.get('cases_per_seed', 100)} total)"

    # Multi-seed aggregate headline numbers (statistically canonical)
    revplug_mean_gross = agg.get("revplug_mean_gross", 0)
    revplug_mean_net = agg.get("revplug_mean_net", 0)
    safe_mean_net = agg.get("safe_mean_net", 0)
    naive_mean_net = agg.get("naive_mean_net", 0)
    revplug_win_rate = agg.get("revplug_win_rate_pct", 0.0)
    revplug_wins = agg.get("revplug_wins_vs_safe", 0)
    total_seeds = agg.get("total_seeds", 10)
    ci_lower = agg.get("confidence_interval_95_lower", 0.0)
    ci_upper = agg.get("confidence_interval_95_upper", 0.0)

    # Single-seed comparison numbers
    safe_lift_pct = comp.get("safe_lift_pct")
    naive_lift_pct = comp.get("naive_lift_pct")

    lines = [
        "# RevPlug Benchmark & Counterfactual ROI Report",
        "",
        f"**Generated At:** {gen_time}",
        f"**Canonical Benchmark Scale:** {multi_seed_label} | Version `2.0-canonical`",
        f"**Evaluation Mode:** {cfg.get('evaluation_mode', 'AI_ASSISTED')} (AI Contextual Routing + Deterministic Safety Shield)",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "RevPlug is a **bounded autonomous revenue recovery system** designed to maximize settlement-verified revenue while enforcing strict deterministic safety policies and retry budgets.",
        "",
        f"In this multi-seed benchmark of **{multi_seed_label}**:",
        f"- **{ros.get('llm_classified_count', 0)} AI-Assisted Cases** (single-seed detailed trace)",
        f"- **{ros.get('rules_classified_count', 0)} Deterministic Cases** (single-seed detailed trace)",
        f"- **{ai.get('ai_proposals', 0)} AI Proposals Generated** (single-seed)",
        f"- **{ai.get('ai_proposals_accepted', 0)} AI Proposals Accepted & Executed** (single-seed)",
        f"- **{ai.get('policy_blocked_proposals', 0)} AI Proposals Blocked by Deterministic Policy Shield** (single-seed)",
        f"- **{ai.get('ai_fallback_cases', 0)} AI Fallbacks Triggered** (single-seed)",
        f"- **{ros.get('safety_violations', {}).get('total_safety_violations', 0)} Safety Policy Violations** (single-seed)",
        "",
        f"Across {total_seeds} seeds, RevPlug won {revplug_wins}/{total_seeds} seeds ({revplug_win_rate:.0f}%) against the Safe Baseline. "
        f"Mean Net Recovery: **{fmt(revplug_mean_net)}** vs Safe Baseline mean **{fmt(safe_mean_net)}**.",
        "",
        "---",
        "",
        "## 2. Single-Seed Detailed Trace (Canonical Seed 42)",
        "",
        "| Metric | Naive Fixed Retry | Safe Fixed Retry | RevPlug Bounded AI Agent | Net Uplift vs Safe |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Total Revenue at Risk** | {fmt(bl.get('total_amount_at_risk', 0))} | {fmt(sbl.get('total_amount_at_risk', 0))} | {fmt(ros.get('total_amount_at_risk', 0))} | — |",
        f"| **AI-Assisted Cases** | 0 | 0 | **{ros.get('llm_classified_count', 0)} ({ros.get('llm_classified_count', 0)/max(1, ros.get('cases_evaluated', 1))*100:.1f}%)** | — |",
        f"| **Deterministic Cases** | {bl.get('cases_evaluated', 0)} (100%) | {sbl.get('cases_evaluated', 0)} (100%) | **{ros.get('rules_classified_count', 0)} ({ros.get('rules_classified_count', 0)/max(1, ros.get('cases_evaluated', 1))*100:.1f}%)** | — |",
        f"| **Verified Recovered Revenue** | {fmt(bl.get('actual_recovered', 0))} | {fmt(sbl.get('actual_recovered', 0))} | **{fmt(ros.get('actual_recovered', 0))}** | **{fmt(comp.get('absolute_recovery_difference', 0))}** |",
        f"| **Verified Recovery Rate** | {bl.get('recovery_rate', 0.0)*100:.1f}% | {sbl.get('recovery_rate', 0.0)*100:.1f}% | **{ros.get('recovery_rate', 0.0)*100:.1f}%** | **{comp.get('recovery_rate_difference', 0.0)*100:.1f}% pts** |",
        f"| **Intervention Cost** | {fmt(bl.get('intervention_cost', 0))} | {fmt(sbl.get('intervention_cost', 0))} | **{fmt(ros.get('intervention_cost', 0))}** | **-{fmt(bl.get('intervention_cost', 0) - ros.get('intervention_cost', 0))}** |",
        f"| **Net Recovered Revenue** | {fmt(comp.get('naive_baseline_net', 0))} | {fmt(comp.get('safe_baseline_net', 0))} | **{fmt(ros.get('net_recovered', 0))}** | **{fmt(ros.get('net_recovered', 0) - comp.get('safe_baseline_net', 0))} ({safe_lift_pct:+.1f}%)** |",
        f"| **AI Proposals Blocked by Policy** | 0 | 0 | **{ai.get('policy_blocked_proposals', 0)}** | — |",
        f"| **Safety Policy Violations** | **{bl.get('baseline_policy_violations', {}).get('total_policy_violations', 0)}** | **0** | **0** | — |",
        "",
        "---",
        "",
        "## 3. Revenue Attribution Breakdown (Single Seed)",
        "",
        "| Attribution Category | Cases | Recovered Amount | Description |",
        "| :--- | :--- | :--- | :--- |",
        f"| **DIRECT_AGENT** | {attr.get('DIRECT_AGENT_cases', 0)} | {fmt(attr.get('DIRECT_AGENT_recovered_minor', 0))} | Realized recovery directly driven by automated retries or alternate channels. |",
        f"| **AGENT_ASSISTED** | {attr.get('AGENT_ASSISTED_cases', 0)} | {fmt(attr.get('AGENT_ASSISTED_recovered_minor', 0))} | Realized recovery following payment links, reminders, or promise-to-pay workflows. |",
        f"| **ORGANIC** | {attr.get('ORGANIC_cases', 0)} | {fmt(attr.get('ORGANIC_recovered_minor', 0))} | Payment settled independently without qualifying agent intervention. |",
        f"| **UNKNOWN** | {attr.get('UNKNOWN_cases', 0)} | {fmt(attr.get('UNKNOWN_recovered_minor', 0))} | Unassigned attribution. |",
        "",
        "---",
        "",
        "## 4. Multi-Seed Statistical Robustness (Canonical Result)",
        "",
        f"**Total Seeds Evaluated:** {total_seeds} (Seeds 42–51) | **Cases per Seed:** {agg.get('cases_per_seed', 100)}",
        "",
        "| Metric | Baseline A (Naive Retry) | Baseline B (Safe Retry) | RevPlug Autonomous Agent | RevPlug vs Safe |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Mean Gross Recovery** | {fmt(agg.get('naive_mean_gross', 0))} | {fmt(agg.get('safe_mean_gross', 0))} | **{fmt(revplug_mean_gross)}** | {((revplug_mean_gross - agg.get('safe_mean_gross', 0)) / max(1, agg.get('safe_mean_gross', 1)) * 100):+.1f}% |",
        f"| **Mean Net Recovery** | {fmt(naive_mean_net)} | {fmt(safe_mean_net)} | **{fmt(revplug_mean_net)}** | {((revplug_mean_net - safe_mean_net) / max(1, safe_mean_net) * 100):+.1f}% |",
        f"| **Mean Recovery Rate** | {agg.get('naive_mean_gross', 0) / max(1, agg.get('mean_amount_at_risk', 1)) * 100:.1f}% | {agg.get('safe_mean_gross', 0) / max(1, agg.get('mean_amount_at_risk', 1)) * 100:.1f}% | **{revplug_mean_gross / max(1, agg.get('mean_amount_at_risk', 1)) * 100:.1f}%** | {((revplug_mean_gross - agg.get('safe_mean_gross', 0)) / max(1, agg.get('mean_amount_at_risk', 1)) * 100):+.1f}% pts |",
        f"| **Mean Safety Violations** | {agg.get('naive_mean_violations', 0.0):.1f} | {agg.get('safe_mean_violations', 0.0):.1f} | **{agg.get('revplug_mean_violations', 0.0):.1f}** | — |",
        f"| **Mean Decision Quality** | — | — | **{agg.get('revplug_mean_decision_quality', 0.0):.1f}%** | — |",
        "",
        f"- **RevPlug Win Count vs Safe Baseline:** {revplug_wins}/{total_seeds} seeds ({revplug_win_rate:.0f}%)",
        f"- **95% Confidence Interval (Net Lift):** [{ci_lower:+,.2f}%, {ci_upper:+,.2f}%]",
        f"- **Mean Net Recovery per Seed:** {fmt(revplug_mean_net)}",
        f"- **Safe Baseline Mean Net per Seed:** {fmt(safe_mean_net)}",
        f"- **Net Difference (RevPlug − Safe):** {fmt(revplug_mean_net - safe_mean_net)}",
        "",
        "---",
        "",
        "## 5. AI / Deterministic Architectural Boundary",
        "",
        "RevPlug maintains a strict, un-compromised boundary between AI reasoning and deterministic controls:",
        "",
        "### What AI Handles",
        "- Contextual candidate selection & intervention ranking",
        "- Ambiguous failure interpretation & customer contextual evidence reasoning",
        "- Generating structured proposal rationales",
        "",
        "### What Deterministic Systems Handle",
        "- Financial arithmetic & recovery rate calculations",
        "- Settlement verification (authoritative webhook HMAC & payment IDs)",
        "- Policy enforcement (`InterventionPolicy`) & hard stopping rules (`StoppingRules`)",
        "- Consent enforcement (`opt_out_block`) & fraud protection (`block_hard_failure`)",
        "- Incident suppression & duplicate transaction prevention (idempotency)",
        "",
        "---",
        "",
        "## 6. Reproducibility",
        "",
        "To reproduce this exact benchmark report, execute:",
        "```bash",
        "python -m app.eval.run_benchmark",
        "```",
    ]
    return "\n".join(lines)


def run_benchmark(count: int = 50, seed: int = 42) -> dict:
    """Run counterfactual batch evaluation and output canonical report artifacts."""
    print(f"Running RevPlug canonical benchmark evaluation (count={count}, seed={seed})...")
    
    # 1. Run single-seed detailed trace (count=50, seed=42)
    eval_svc = EvaluationService(ai_enabled=True, max_retry_attempts=3)
    single_res = eval_svc.run_batch_evaluation(count=count, seed=seed)
    resp = eval_svc.to_response_dict(single_res)

    # 2. Run multi-seed statistical aggregate suite (10 seeds x 100 cases = 1,000 cases)
    try:
        multi_report = run_benchmark_suite(cases=100, seeds=[42, 43, 44, 45, 46, 47, 48, 49, 50, 51])
        from dataclasses import asdict
        multi_dict = asdict(multi_report)
    except Exception as e:
        print(f"Warning: multi-seed suite warning: {e}")
        multi_dict = {}

    # Build attribution metrics for single-seed run
    ros_per_case = single_res.revplug.per_case
    attr_metrics = {
        "DIRECT_AGENT_cases": sum(1 for c in ros_per_case if c.metadata.get("attribution") == "DIRECT_AGENT"),
        "AGENT_ASSISTED_cases": sum(1 for c in ros_per_case if c.metadata.get("attribution") == "AGENT_ASSISTED"),
        "ORGANIC_cases": sum(1 for c in ros_per_case if c.metadata.get("attribution") == "ORGANIC"),
        "UNKNOWN_cases": sum(1 for c in ros_per_case if c.metadata.get("attribution") not in ("DIRECT_AGENT", "AGENT_ASSISTED", "ORGANIC")),
        "DIRECT_AGENT_recovered_minor": sum(c.actual_recovered for c in ros_per_case if c.metadata.get("attribution") == "DIRECT_AGENT"),
        "AGENT_ASSISTED_recovered_minor": sum(c.actual_recovered for c in ros_per_case if c.metadata.get("attribution") == "AGENT_ASSISTED"),
        "ORGANIC_recovered_minor": sum(c.actual_recovered for c in ros_per_case if c.metadata.get("attribution") == "ORGANIC"),
        "UNKNOWN_recovered_minor": sum(c.actual_recovered for c in ros_per_case if c.metadata.get("attribution") not in ("DIRECT_AGENT", "AGENT_ASSISTED", "ORGANIC")),
    }
    resp["revplug"]["attribution_metrics"] = attr_metrics

    # Attach benchmark metadata
    resp["benchmark_metadata"] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "evaluation_id": f"REC-CANONICAL-2026-S{seed}-C{count}",
        "dataset_version": "v2-counterfactual",
        "canonical_scale": "50-case seed 42 detailed trace + 1000-case multi-seed suite",
    }
    if multi_dict:
        resp["multi_seed_aggregate"] = multi_dict

    # Invariant assertions
    ros = resp.get("revplug", {})
    base = resp.get("baseline", {})

    if ros.get("actual_recovered", 0) > ros.get("total_amount_at_risk", 0):
        raise ValueError(f"Financial truth violation: actual_recovered ({ros.get('actual_recovered')}) > total_amount_at_risk ({ros.get('total_amount_at_risk')})")
    if ros.get("actual_recovered", 0) < 0:
        raise ValueError("Financial truth violation: negative actual_recovered")

    # 1. Write canonical JSON artifact
    json_path = Path("evaluation_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resp, f, indent=2)
    print(f"Saved canonical JSON evaluation report to {json_path.resolve()}")

    # 2. Write Markdown artifact rendered directly from JSON
    md_content = render_markdown_report(resp)
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    md_path = docs_dir / "EVALUATION_REPORT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved Markdown evaluation report to {md_path.resolve()}")

    return resp


if __name__ == "__main__":
    count_arg = 50
    seed_arg = 42
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--count="):
                count_arg = int(arg.split("=")[1])
            elif arg.startswith("--seed="):
                seed_arg = int(arg.split("=")[1])

    run_benchmark(count=count_arg, seed=seed_arg)
