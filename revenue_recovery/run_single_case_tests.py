import sys
from tests.test_single_case_lifecycle import (
    test_case_a_soft_timeout_lifecycle,
    test_case_b_fraud_signal_blocks_execution,
    test_case_c_customer_promise_to_pay_hold,
)

def run():
    print("Executing single-case lifecycle integration tests...")
    
    print("\n1. Testing CASE A — Soft Gateway Timeout (₹4,999)...")
    try:
        test_case_a_soft_timeout_lifecycle()
        print("  ✓ PASS: Case A lifecycle verified (QUEUED -> EVALUATE -> PENDING_VERIFICATION -> SETTLEMENT VERIFIED -> RECOVERED).")
    except Exception as e:
        print(f"  ✗ FAIL Case A: {e}")
        raise e

    print("\n2. Testing CASE B — Fraud Signal Policy Block...")
    try:
        test_case_b_fraud_signal_blocks_execution()
        print("  ✓ PASS: Case B verified (QUEUED -> EVALUATE -> POLICY BLOCK -> 0 Execution -> STOPPED, Recovery = ₹0).")
    except Exception as e:
        print(f"  ✗ FAIL Case B: {e}")
        raise e

    print("\n3. Testing CASE C — Customer Promise-To-Pay Hold...")
    try:
        test_case_c_customer_promise_to_pay_hold()
        print("  ✓ PASS: Case C verified (Promise recorded -> WAIT/Hold active -> 0 redundant retry -> Recovery = ₹0).")
    except Exception as e:
        print(f"  ✗ FAIL Case C: {e}")
        raise e

    print("\nALL SINGLE-CASE LIFECYCLE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run()
