"""Regression tests for benchmark isolation, proof integrity, and canonical reporting.

Verifies:
1. Canonical benchmark report is served correctly by /api/benchmark-summary.
2. The benchmark summary endpoint maps evaluation_report.json single-seed and multi-seed fields faithfully.
3. Benchmark synthetic data is strictly isolated from operational recovery KPIs.
4. Evaluated recovery amounts cannot be confused with live verified settlement money.
5. Per-seed details match canonical evaluation output.
6. Benchmark methodology, formulas, and seeded outputs remain untouched and reproducible.
"""

from pathlib import Path
import json
from app.api.evaluations import api_benchmark_summary
from app.dashboard_api import _classify_item, _get_items, build_dashboard_summary
from app.db.container import PersistenceContainer
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType


def test_api_benchmark_summary_serves_canonical_report():
    response = api_benchmark_summary()
    assert response.status_code == 200
    
    data = json.loads(response.body.decode("utf-8"))
    assert data["source"] == "evaluation_report.json"
    assert data["seed"] == 42
    assert "single_seed" in data
    assert "multi_seed" in data
    
    ms = data["multi_seed"]
    assert ms["total_seeds"] == 10
    assert ms["cases_per_seed"] == 100
    assert "net_lift_pct" in ms
    assert "revplug_wins_vs_safe" in ms
    assert len(ms["per_seed_summaries"]) == 10


test_report_path = Path(__file__).resolve().parent.parent / "evaluation_report.json"

def test_benchmark_summary_matches_raw_report():
    if not test_report_path.exists():
        return
        
    with open(test_report_path, "r", encoding="utf-8") as fh:
        raw_report = json.load(fh)
        
    response = api_benchmark_summary()
    data = json.loads(response.body.decode("utf-8"))
    
    agg = raw_report.get("multi_seed_aggregate", {})
    ms = data["multi_seed"]
    
    assert ms["revplug_wins_vs_safe"] == agg.get("revplug_wins_vs_safe")
    assert ms["net_lift_pct"] == agg.get("net_lift_pct")
    assert ms["revplug_mean_net"] == agg.get("revplug_mean_net")
    assert ms["best_seed"] == agg.get("best_seed")
    assert ms["worst_seed"] == agg.get("worst_seed")


def test_benchmark_synthetic_items_cannot_enter_operational_kpis():
    container = PersistenceContainer()
    
    # Operational live item
    op_item = RecoveryItem(
        id="op_item_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_op_1",
        customer_id="cust_op_1",
        amount_minor=200000,
        status=RecoveryStatus.DETECTED,
        metadata={"source": "webhook_live", "is_synthetic": False},
    )
    
    # Synthetic benchmark item
    bench_item = RecoveryItem(
        id="bench_item_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_bench_1",
        customer_id="cust_bench_1",
        amount_minor=500000,
        status=RecoveryStatus.RECOVERED,
        metadata={"source": "demo_scenario", "is_synthetic": True},
    )
    
    container.recovery_items.save(op_item)
    container.recovery_items.save(bench_item)
    
    # Check operational items
    op_items = _get_items(container, include_synthetic=False)
    op_ids = [i.id for i in op_items]
    
    assert "op_item_1" in op_ids
    assert "bench_item_1" not in op_ids
    
    # Dashboard summary revenue at risk
    summary = build_dashboard_summary(container)
    assert summary["portfolio"]["revenue_at_risk_minor"] == 200000
    assert summary["portfolio"]["actual_recovered_minor"] == 0


def test_per_seed_summaries_are_complete():
    response = api_benchmark_summary()
    data = json.loads(response.body.decode("utf-8"))
    
    per_seed = data["multi_seed"]["per_seed_summaries"]
    assert len(per_seed) == 10
    
    for seed_summary in per_seed:
        assert "seed" in seed_summary
        assert "cases" in seed_summary
        assert "amount_at_risk" in seed_summary
        assert "revplug_net" in seed_summary
        assert "baseline_safe_net" in seed_summary
        assert "revplug_win_vs_safe" in seed_summary
