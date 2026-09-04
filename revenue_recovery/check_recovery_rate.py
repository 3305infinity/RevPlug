import json
from pathlib import Path

p = Path('evaluation_report.json')
data = json.loads(p.read_text())
ros = data.get('revplug', {})

print('recovery_rate:', ros.get('recovery_rate'))
print('recovered_count:', ros.get('recovered_count'))
print('total_amount_at_risk:', ros.get('total_amount_at_risk'))
print('actual_recovered:', ros.get('actual_recovered'))

# Check per_case
per_case = data.get('per_case', [])
print('per_case count:', len(per_case))
for case in per_case[:5]:
    print(f"  {case.get('case_id')}: outcome={case.get('revplug', {}).get('outcome')}, recovered={case.get('revplug', {}).get('actual_recovered')}")
