import json
from pathlib import Path

p = Path('evaluation_report.json')
data = json.loads(p.read_text())
agg = data.get('multi_seed_aggregate', {})

print('=== Multi-Seed Results ===')
print(f"total_seeds: {agg.get('total_seeds')}")
print(f"cases_per_seed: {agg.get('cases_per_seed')}")
print(f"revplug_wins_vs_safe: {agg.get('revplug_wins_vs_safe')}")
print(f"revplug_win_rate_pct: {agg.get('revplug_win_rate_pct')}")
print(f"revplug_mean_net: {agg.get('revplug_mean_net')}")
print(f"safe_mean_net: {agg.get('safe_mean_net')}")
print(f"revplug_mean_decision_quality: {agg.get('revplug_mean_decision_quality')}")
print(f"revplug_mean_violations: {agg.get('revplug_mean_violations')}")

# Single seed
ros = data.get('revplug', {})
print()
print('=== Single Seed 42 ===')
print(f"actual_recovered: {ros.get('actual_recovered')}")
print(f"net_recovered: {ros.get('net_recovered')}")
print(f"recovery_rate: {ros.get('recovery_rate')}")
print(f"safety_violations: {ros.get('safety_violations', {}).get('total_safety_violations')}")
