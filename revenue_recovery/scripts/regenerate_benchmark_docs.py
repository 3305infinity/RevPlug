#!/usr/bin/env python3
"""Regenerate docs/EVALUATION_REPORT.md from evaluation_report.json.

evaluation_report.json is the single source of truth for all benchmark numbers.
This script reads it and re-renders the Markdown report without re-running
the evaluation. It is the ONLY sanctioned way to update docs/EVALUATION_REPORT.md.

Usage:
    python scripts/regenerate_benchmark_docs.py
    python scripts/regenerate_benchmark_docs.py --json-path /path/to/evaluation_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent          # inner revenue_recovery/ (has app/ package)
CANONICAL_JSON_PATH = REPO_ROOT.parent / "evaluation_report.json"  # outer repo root


def load_report(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def render_markdown(data: dict) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app.eval.run_benchmark import render_markdown_report
        return render_markdown_report(data)
    finally:
        if str(REPO_ROOT) in sys.path:
            sys.path.remove(str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate docs/EVALUATION_REPORT.md from evaluation_report.json")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=CANONICAL_JSON_PATH,
        help="Path to evaluation_report.json (default: canonical outer repo root)",
    )
    parser.add_argument(
        "--docs-path",
        type=Path,
        default=REPO_ROOT / "docs" / "EVALUATION_REPORT.md",
        help="Output Markdown path (default: <repo_root>/docs/EVALUATION_REPORT.md)",
    )
    args = parser.parse_args()

    json_path = args.json_path.resolve()
    if not json_path.is_file():
        print(f"ERROR: evaluation_report.json not found at {json_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading canonical report from: {json_path}")
    data = load_report(json_path)

    # Update generated_at timestamp so the doc always reflects when it was last rendered
    data.setdefault("benchmark_metadata", {})["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    data.setdefault("benchmark_metadata", {})["doc_regenerated_at"] = datetime.now(timezone.utc).isoformat()

    md_content = render_markdown(data)

    docs_path = args.docs_path.resolve()
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(md_content, encoding="utf-8")
    print(f"Saved Markdown evaluation report to: {docs_path}")

    # Print headline numbers for CI / human verification
    ros = data.get("revplug", {})
    bl = data.get("baseline", {})
    comp = data.get("comparison", {})
    agg = data.get("multi_seed_aggregate", {})
    print("\n--- Headline Numbers (from evaluation_report.json) ---")
    print(f"  Evaluation ID   : {data.get('evaluation_id')}")
    print(f"  Seed / Count    : {data.get('seed')} / {data.get('count')}")
    print(f"  Dataset version : {data.get('dataset', {}).get('dataset_version', '?')}")
    print(f"  [Single-Seed]   : RevPlug net Rs.{ros.get('net_recovered', 0)/100:,.2f}  "
          f"(rate {ros.get('recovery_rate', 0)*100:.1f}%)  "
          f"violations={ros.get('safety_violations', {}).get('total_safety_violations', 0)}")
    print(f"  [Multi-Seed]    : RevPlug {agg.get('revplug_wins_vs_safe', 0)}/{agg.get('total_seeds', 10)} seeds  "
          f"mean net Rs.{agg.get('revplug_mean_net', 0)/100:,.2f}  "
          f"95% CI [{agg.get('confidence_interval_95_lower', 0)/100:+,.2f}, {agg.get('confidence_interval_95_upper', 0)/100:+,.2f}]")


if __name__ == "__main__":
    main()
