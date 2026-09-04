import json
from pathlib import Path

p = Path('evaluation_report.json')
data = json.loads(p.read_text())
ros = data.get('revplug', {})

print('total_amount_at_risk:', ros.get('total_amount_at_risk'))
print('actual_recovered:', ros.get('actual_recovered'))
print('recovery_rate:', ros.get('recovery_rate'))
print('recovered_count:', ros.get('recovered_count'))
print('cases_evaluated:', ros.get('cases_evaluated'))

# Check per_case for a few examples
per_case = data.get('per_case', [])
for case in per_case[:5]:
    r = case.get('revplug', {})
    print(f"  {case.get('case_id')}: cat={case.get('failure_category')}, proposed={r.get('proposed_action')}, outcome={r.get('outcome')}, recovered={r.get('actual_recovered')}")
