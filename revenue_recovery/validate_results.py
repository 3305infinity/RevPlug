import json
from pathlib import Path

p = Path('evaluation_report.json')
data = json.loads(p.read_text())
agg = data.get('multi_seed_aggregate', {})

# Check financial invariants
print('=== Financial Invariant Checks ===')
print(f"total_amount_at_risk mean: {agg.get('mean_amount_at_risk')}")
print(f"revplug_mean_gross: {agg.get('revplug_mean_gross')}")
print(f"revplug_mean_net: {agg.get('revplug_mean_net')}")
print(f"safe_mean_gross: {agg.get('safe_mean_gross')}")
print(f"safe_mean_net: {agg.get('safe_mean_net')}")

# Per-case checks
per_case = data.get('per_case', [])
violations = 0
for case in per_case:
    r = case.get('revplug', {})
    aar = case.get('amount_at_risk', 0)
    rec = r.get('actual_recovered', 0)
    if rec > aar:
        violations += 1
        print(f'VIOLATION: {case.get("case_id")} recovered {rec} > {aar}')

print(f'Per-case recovery > amount_at_risk violations: {violations}')
print(f'Total cases checked: {len(per_case)}')

# Check decision quality
ros = data.get('revplug', {})
print()
print('Decision Quality:', ros.get('decision_quality'))
