from app.evaluation.benchmark import run_benchmark_suite
from dataclasses import asdict
import json

report = run_benchmark_suite(cases=50, seeds=[42,43,44,45,46,47,48,49,50,51])
result = asdict(report)

print('=== 10-Seed Benchmark Summary ===')
print(f'Total Seeds: {result["total_seeds"]}')
print(f'Cases per Seed: {result["cases_per_seed"]}')
print(f'RevPlug Wins vs Safe: {result["revplug_wins_vs_safe"]}/{result["total_seeds"]} ({result["revplug_win_rate_pct"]:.1f}%)')
print(f'Mean Amount at Risk: Rs.{result["mean_amount_at_risk"]/100:,.2f}')
print()
print('Mean Net Recovery:')
print(f'  Naive Baseline: Rs.{result["naive_mean_net"]/100:,.2f}')
print(f'  Safe Baseline:  Rs.{result["safe_mean_net"]/100:,.2f}')
print(f'  RevPlug:        Rs.{result["revplug_mean_net"]/100:,.2f}')
print()
print(f'Net Lift vs Safe: {result["net_lift_pct"]:+.2f}%')
print(f'Gross Lift vs Safe: {result["gross_lift_pct"]:+.2f}%')
print()
print(f'Mean Decision Quality: {result["revplug_mean_decision_quality"]:.1f}%')
print(f'Mean Safety Violations: {result["revplug_mean_violations"]:.1f}')
print(f'95% CI (Net Lift): [{result["confidence_interval_95_lower"]/100:+,.2f}, {result["confidence_interval_95_upper"]/100:+,.2f}]')
print()
print('Per-Seed Results:')
for s in result['per_seed_summaries']:
    print(f'  Seed {s["seed"]}: RevPlug Net=Rs.{s["revplug_net"]/100:,.2f}, Safe Net=Rs.{s["baseline_safe_net"]/100:,.2f}, DQ={s["decision_quality_score"]:.1f}%')

# Save full result
with open('benchmark_result.json', 'w') as f:
    json.dump(result, f, indent=2, default=str)
print('\nFull result saved to benchmark_result.json')
