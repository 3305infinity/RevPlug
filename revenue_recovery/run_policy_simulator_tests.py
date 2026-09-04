import sys
from tests.test_policy_simulator_thresholds import (
    test_policy_simulator_min_expected_net_ev_delta,
    test_policy_simulator_escalation_threshold_delta,
    test_policy_simulator_max_contacts_per_24h_delta,
    test_policy_simulator_max_intervention_cost_delta,
)

def run():
    print("Executing Policy Simulator threshold integration tests...")

    print("\n1. Testing Minimum Expected Net EV Threshold Sensitivity (₹3,750 Net EV -> STOP when threshold = ₹4,000)...")
    try:
        test_policy_simulator_min_expected_net_ev_delta()
        print("  ✓ PASS: Min Expected Net EV threshold verified (ALLOWED -> STOP, Delta = -₹3,750, live policy unmutated).")
    except Exception as e:
        print(f"  ✗ FAIL Test 1: {e}")
        raise e

    print("\n2. Testing Escalation Threshold Sensitivity (₹15,000 Case -> ESCALATE when threshold = ₹10,000)...")
    try:
        test_policy_simulator_escalation_threshold_delta()
        print("  ✓ PASS: Escalation threshold verified (ALLOWED -> ESCALATE).")
    except Exception as e:
        print(f"  ✗ FAIL Test 2: {e}")
        raise e

    print("\n3. Testing Max Contacts per 24h Threshold Sensitivity...")
    try:
        test_policy_simulator_max_contacts_per_24h_delta()
        print("  ✓ PASS: Max contacts per 24h limit verified (ALLOWED -> ESCALATE / CONTACT_FREQUENCY_LIMIT).")
    except Exception as e:
        print(f"  ✗ FAIL Test 3: {e}")
        raise e

    print("\n4. Testing Max Intervention Cost Threshold Sensitivity...")
    try:
        test_policy_simulator_max_intervention_cost_delta()
        print("  ✓ PASS: Max intervention cost gate verified (ALLOWED -> STOP / cost_exceeds_maximum).")
    except Exception as e:
        print(f"  ✗ FAIL Test 4: {e}")
        raise e

    print("\nALL POLICY SIMULATOR THRESHOLD TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run()
