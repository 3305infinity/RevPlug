import json
d = json.load(open('evaluation_report.json'))
revplug = d.get('revplug', {})
print(f"revplug.eligible_cases from JSON: {revplug.get('eligible_cases')}")
print(f"revplug.cases_evaluated: {revplug.get('cases_evaluated')}")
print(f"revplug.no_action_cases: {revplug.get('no_action_cases')}")
print(f"revplug.policy_stop_cases: {revplug.get('policy_stop_cases')}")
print(f"revplug.total_amount_at_risk: {revplug.get('total_amount_at_risk')}")

totalCases = revplug.get('cases_evaluated', 50)
totalAtRisk = revplug.get('total_amount_at_risk', 0)
no_action = revplug.get('no_action_cases', 0)
policy_stop = revplug.get('policy_stop_cases', 0)

eligible_wrong = totalCases - no_action - policy_stop
opp_wrong = eligible_wrong * (totalAtRisk / max(1, totalCases))

eligible_fixed = totalCases - no_action
opp_fixed = eligible_fixed * (totalAtRisk / max(1, totalCases))

print(f"\nCurrent (wrong): eligibleCases = {totalCases} - {no_action} - {policy_stop} = {eligible_wrong}")
print(f"Actionable Opportunity (wrong) = {eligible_wrong} * {totalAtRisk}/{totalCases} = {opp_wrong} = Rs{opp_wrong/100:.2f}")
print(f"\nFixed: eligibleCases = {totalCases} - {no_action} = {eligible_fixed}")
print(f"Actionable Opportunity (fixed) = {eligible_fixed} * {totalAtRisk}/{totalCases} = {opp_fixed} = Rs{opp_fixed/100:.2f}")
