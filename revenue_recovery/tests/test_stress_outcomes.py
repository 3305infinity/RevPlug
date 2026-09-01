import os
import uuid
import concurrent.futures
from datetime import datetime, timezone
import pytest
from app.db.session import PostgresConnection, create_connection
from app.db.postgres_repositories import PostgresRecoveryOutcomeRepository
from app.domain.models import RecoveryOutcome, OutcomeType
from app.main import create_persistence_container


def _db_available() -> bool:
    """Check if PostgreSQL is reachable."""
    try:
        conn = create_connection()
        conn.fetchone("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unreachable or not configured")

def test_stress_concurrent_outcomes():
    """Ensure race conditions on payment success do not double-count actual_recovered."""
    
    container = create_persistence_container("postgres")
    repo = container.outcomes
    items_repo = container.recovery_items
    
    unique_id = str(uuid.uuid4())
    item_id = f"item_stress_outcome_{unique_id}"
    
    # First, create the recovery item to satisfy foreign key constraint
    from app.domain.models import RecoveryItem, SourceType, RecoveryStatus
    item = RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=unique_id,
        customer_id="cust_123",
        amount_minor=10000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED
    )
    items_repo.save(item)
    
    outcome_to_save = RecoveryOutcome(
        id=unique_id,
        recovery_item_id=item_id,
        outcome_type=OutcomeType.RECOVERED,
        expected_recovery_minor=10000,
        actual_recovery_minor=10000,
        recovery_cost_minor=50,
        recovered_at=datetime.now(timezone.utc)
    )
    
    def save_outcome() -> None:
        # Create a fresh connection for each thread to simulate real concurrent requests
        thread_container = create_persistence_container("postgres")
        thread_repo = thread_container.outcomes
        try:
            thread_repo.save(outcome_to_save)
        except Exception:
            pass
        
    # Fire 10 concurrent requests with the exact same outcome
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(save_outcome) for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # This will raise any exceptions caught in the thread
        
    # Read back from database
    saved_outcome = repo.get_for_item(item_id)
    assert saved_outcome is not None, "Outcome was not saved"
    assert saved_outcome.actual_recovery_minor == 10000, "Actual recovery amount was corrupted"
    
    # Ensure there is exactly 1 record in the list for this item
    all_outcomes = repo.list_all(limit=1000)
    matches = [o for o in all_outcomes if o.recovery_item_id == item_id]
    
    assert len(matches) == 1, f"Expected exactly 1 outcome record, got {len(matches)}!"
    
    print(f"Concurrent outcomes test passed. Exactly 1 outcome recorded with {matches[0].actual_recovery_minor} recovered.")

if __name__ == "__main__":
    test_stress_concurrent_outcomes()
    print("Concurrent outcomes stress test PASS")
