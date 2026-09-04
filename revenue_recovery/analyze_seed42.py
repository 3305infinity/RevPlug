import json
from pathlib import Path
from collections import Counter

p = Path('evaluation_report.json')
data = json.loads(p.read_text())
per_case = data.get('per_case', [])

# Category breakdown
cats = Counter()
correct = 0
for case in per_case:
    cat = case.get('failure_category')
    cats[cat] += 1
    r = case.get('revplug', {})
    proposed = r.get('proposed_action')
    gt = case.get('ground_truth') or {}
    acceptable = gt.get('acceptable_actions') or [gt.get('correct_action')]
    if proposed in acceptable:
        correct += 1

print('Category distribution (seed 42):')
for cat, count in sorted(cats.items()):
    print(f'  {cat}: {count}')

print(f'\nProposal accuracy: {correct}/{len(per_case)} ({correct/len(per_case)*100:.1f}%)')

# Check what actions were proposed for each category
cat_actions = {}
for case in per_case:
    cat = case.get('failure_category')
    r = case.get('revplug', {})
    proposed = r.get('proposed_action')
    if cat not in cat_actions:
        cat_actions[cat] = Counter()
    cat_actions[cat][proposed] += 1

print('\nActions proposed by category:')
for cat in sorted(cat_actions.keys()):
    print(f'  {cat}: {dict(cat_actions[cat])}')

# Compare with ground truth
print('\nGround truth vs proposed:')
for case in per_case[:10]:
    gt = case.get('ground_truth') or {}
    r = case.get('revplug', {})
    match = 'OK' if r.get('proposed_action') in (gt.get('acceptable_actions') or [gt.get('correct_action')]) else 'MISMATCH'
    print(f'  {case.get("case_id")}: cat={case.get("failure_category")}, correct={gt.get("correct_action")}, proposed={r.get("proposed_action")}, match={match}')
