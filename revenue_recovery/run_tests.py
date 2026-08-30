import sys
from tests.test_stress_agent_failures import test_orchestrator_resilience_to_agent_failures
from tests.test_stress_idempotency import test_webhook_idempotency_concurrent

from tests.test_stress_batch import test_stress_large_batch
from tests.test_stress_outcomes import test_stress_concurrent_outcomes

def run():
    print("Running test_orchestrator_resilience_to_agent_failures...")
    try:
        test_orchestrator_resilience_to_agent_failures()
        print("PASS")
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

    print("Running test_webhook_idempotency_concurrent...")
    try:
        test_webhook_idempotency_concurrent()
        print("PASS")
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

    print("Running test_stress_large_batch...")
    try:
        test_stress_large_batch()
        print("PASS")
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
        
    print("Running test_stress_concurrent_outcomes...")
    try:
        test_stress_concurrent_outcomes()
        print("PASS")
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)

if __name__ == "__main__":
    run()
