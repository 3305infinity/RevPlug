import sys
from tests.test_customer_profile_aggregation import (
    test_customer_profile_scenario_1_active_pending_case,
    test_customer_profile_scenario_2_recovered_case,
    test_customer_profile_scenario_3_stopped_case,
    test_customer_profile_scenario_4_historical_only_no_active,
)

def run():
    print("Executing customer profile aggregation regression tests...")

    print("\n1. Testing Scenario 1 — Active Pending Case...")
    try:
        test_customer_profile_scenario_1_active_pending_case()
        print("  ✓ PASS: Active pending case profile verified (Amount at Risk = ₹4,999, Status = Active Exposure).")
    except Exception as e:
        print(f"  ✗ FAIL Scenario 1: {e}")
        raise e

    print("\n2. Testing Scenario 2 — Recovered Case...")
    try:
        test_customer_profile_scenario_2_recovered_case()
        print("  ✓ PASS: Recovered case profile verified (At Risk = ₹0, Status = Settled & Clear, Last Failed preserved).")
    except Exception as e:
        print(f"  ✗ FAIL Scenario 2: {e}")
        raise e

    print("\n3. Testing Scenario 3 — Stopped Case...")
    try:
        test_customer_profile_scenario_3_stopped_case()
        print("  ✓ PASS: Stopped case profile verified (At Risk = ₹0, Status = No Active Exposure, Last Failed preserved).")
    except Exception as e:
        print(f"  ✗ FAIL Scenario 3: {e}")
        raise e

    print("\n4. Testing Scenario 4 — Historical Only (No Active Exposure)...")
    try:
        test_customer_profile_scenario_4_historical_only_no_active()
        print("  ✓ PASS: Historical-only profile verified (At Risk = ₹0, Active Cases = 0, Status = No Active Exposure, No Recovery Pressure).")
    except Exception as e:
        print(f"  ✗ FAIL Scenario 4: {e}")
        raise e

    print("\nALL CUSTOMER PROFILE AGGREGATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run()
