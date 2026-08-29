"""Integration tests for PostgreSQL persistence.

These tests require a running PostgreSQL instance. They are skipped when
DATABASE_URL is not configured or the database is unreachable.

To run these tests locally:

    docker compose up -d
    python scripts/init_db.py
    $env:DATABASE_URL = "postgresql://recovery:recovery_dev_password@localhost:5432/recovery_engine"
    python -m pytest tests/test_postgres_integration.py -v
"""
from __future__ import annotations

import os
import uuid

import pytest

from app.db.session import create_connection, get_database_url


def _db_available() -> bool:
    """Check if PostgreSQL is reachable."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        conn = create_connection()
        conn.fetchone("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="DATABASE_URL not configured or PostgreSQL unreachable")


@pytest.fixture
def db_conn():
    """Provide a clean database connection for each test."""
    conn = create_connection()
    # Clean up test data before each test.
    conn._conn.execute("DELETE FROM audit_log")
    conn._conn.execute("DELETE FROM attempts")
    conn._conn.execute("DELETE FROM idempotency_keys")
    conn._conn.execute("DELETE FROM recovery_items")
    conn._conn.commit()
    yield conn
    # Rollback any uncommitted changes.
    conn._conn.rollback()


# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------

class TestDatabaseConfiguration:
    def test_get_database_url_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
        from app.db.session import get_database_url
        assert get_database_url() == "postgresql://user:pass@host:5432/db"

    def test_get_database_url_from_pg_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("PGUSER", "testuser")
        monkeypatch.setenv("PGPASSWORD", "testpass")
        monkeypatch.setenv("PGHOST", "testhost")
        monkeypatch.setenv("PGPORT", "5433")
        monkeypatch.setenv("PGDATABASE", "testdb")
        from app.db.session import get_database_url
        assert get_database_url() == "postgresql://testuser:testpass@testhost:5433/testdb"

    def test_connection_works(self, db_conn):
        row = db_conn.fetchone("SELECT 1 AS result")
        assert row["result"] == 1


# ---------------------------------------------------------------------------
# RecoveryItemRepository
# ---------------------------------------------------------------------------

class TestPostgresRecoveryItemRepository:
    def test_save_and_get(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_test_001",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_test_001",
            customer_id="cust_001",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
            recovery_probability=0.35,
            expected_recovery_value=17500,
            metadata={"error_code": "TEST_CODE"},
        )
        repo.save(item)
        fetched = repo.get("ri_test_001")
        assert fetched is not None
        assert fetched.id == "ri_test_001"
        assert fetched.amount_minor == 50000
        assert fetched.status == RecoveryStatus.DETECTED

    def test_update_status(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_test_002",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_test_002",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        )
        repo.save(item)
        repo.update_status("ri_test_002", RecoveryStatus.QUEUED)
        fetched = repo.get("ri_test_002")
        assert fetched.status == RecoveryStatus.QUEUED

    def test_get_nonexistent_returns_none(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        repo = PostgresRecoveryItemRepository(db_conn)
        assert repo.get("does_not_exist") is None

    def test_save_upsert(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_test_003",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_test_003",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        )
        repo.save(item)
        # Save again with updated status — should upsert.
        item2 = RecoveryItem(
            id="ri_test_003",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_test_003",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.QUEUED,
        )
        repo.save(item2)
        fetched = repo.get("ri_test_003")
        assert fetched.status == RecoveryStatus.QUEUED


# ---------------------------------------------------------------------------
# IdempotencyRepository
# ---------------------------------------------------------------------------

class TestPostgresIdempotencyStore:
    def test_has_processed_false_initially(self, db_conn):
        from app.db.postgres_repositories import PostgresIdempotencyStore
        store = PostgresIdempotencyStore(db_conn)
        assert store.has_processed("evt_001") is False

    def test_mark_processed_then_has_processed_true(self, db_conn):
        from app.db.postgres_repositories import PostgresIdempotencyStore
        store = PostgresIdempotencyStore(db_conn)
        store.mark_processed("evt_001")
        assert store.has_processed("evt_001") is True

    def test_duplicate_mark_processed_does_not_raise(self, db_conn):
        from app.db.postgres_repositories import PostgresIdempotencyStore
        store = PostgresIdempotencyStore(db_conn)
        store.mark_processed("evt_002")
        # Second call should not raise (idempotent).
        store.mark_processed("evt_002")
        assert store.has_processed("evt_002") is True

    def test_different_keys_are_independent(self, db_conn):
        from app.db.postgres_repositories import PostgresIdempotencyStore
        store = PostgresIdempotencyStore(db_conn)
        store.mark_processed("evt_003")
        assert store.has_processed("evt_003") is True
        assert store.has_processed("evt_004") is False


# ---------------------------------------------------------------------------
# AuditLogRepository
# ---------------------------------------------------------------------------

class TestPostgresAuditLog:
    def _seed_item(self, db_conn, item_id: str) -> None:
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        repo.save(RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"evt_{item_id}",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        ))

    def test_log_and_retrieve(self, db_conn):
        from app.db.postgres_repositories import PostgresAuditLog
        self._seed_item(db_conn, "ri_001")
        log = PostgresAuditLog(db_conn)
        log.log("ri_001", "system", "test_action", reason="test reason", metadata={"key": "value"})
        events = log.events_for("ri_001")
        assert len(events) == 1
        assert events[0].action == "test_action"
        assert events[0].reason == "test reason"

    def test_events_are_isolated_by_recovery_item_id(self, db_conn):
        from app.db.postgres_repositories import PostgresAuditLog
        self._seed_item(db_conn, "ri_001")
        self._seed_item(db_conn, "ri_002")
        log = PostgresAuditLog(db_conn)
        log.log("ri_001", "system", "action_1")
        log.log("ri_002", "system", "action_2")
        assert len(log.events_for("ri_001")) == 1
        assert len(log.events_for("ri_002")) == 1
        assert log.events_for("ri_001")[0].action == "action_1"


# ---------------------------------------------------------------------------
# AttemptRepository
# ---------------------------------------------------------------------------

class TestPostgresAttemptLedger:
    def _seed_item(self, db_conn, item_id: str) -> None:
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        repo.save(RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=f"evt_{item_id}",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        ))

    def test_record_and_retrieve(self, db_conn):
        from app.db.postgres_repositories import PostgresAttemptLedger
        from app.ledger.attempts import AttemptRecord
        self._seed_item(db_conn, "ri_001")
        ledger = PostgresAttemptLedger(db_conn)
        record = AttemptRecord(
            recovery_item_id="ri_001",
            attempt_number=1,
            action="retry_payment",
            outcome="success",
        )
        ledger.record(record)
        attempts = ledger.attempts_for("ri_001")
        assert len(attempts) == 1
        assert attempts[0].attempt_number == 1
        assert attempts[0].outcome == "success"

    def test_unique_constraint_on_attempt_number(self, db_conn):
        from app.db.postgres_repositories import PostgresAttemptLedger
        from app.ledger.attempts import AttemptRecord
        import psycopg
        self._seed_item(db_conn, "ri_001")
        ledger = PostgresAttemptLedger(db_conn)
        ledger.record(AttemptRecord(recovery_item_id="ri_001", attempt_number=1, action="retry"))
        with pytest.raises(Exception):  # UniqueViolation
            ledger.record(AttemptRecord(recovery_item_id="ri_001", attempt_number=1, action="retry"))


# ---------------------------------------------------------------------------
# Persistence container
# ---------------------------------------------------------------------------

class TestPersistenceContainer:
    def test_create_memory_container(self):
        from app.db.container import create_persistence_container
        container = create_persistence_container("memory")
        assert container.recovery_items is not None
        assert container.idempotency is not None
        assert container.audit_log is not None
        assert container.attempts is not None

    def test_create_postgres_container(self, db_conn):
        from app.db.container import create_persistence_container
        container = create_persistence_container("postgres")
        assert container.recovery_items is not None
        assert container.idempotency is not None

    def test_unknown_mode_raises(self):
        from app.db.container import create_persistence_container
        with pytest.raises(ValueError, match="Unknown PERSISTENCE_MODE"):
            create_persistence_container("unknown_mode")


# ---------------------------------------------------------------------------
# Canonical recovery_items fields
# ---------------------------------------------------------------------------

class TestCanonicalRecoveryItem:
    def test_save_and_get_with_canonical_fields(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_canon_001",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_razorpay_001",
            customer_id="cust_001",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            failure_category="soft",
            provider="razorpay",
            provider_event_id="evt_razorpay_001",
            expected_recovery_value=17500,
            metadata={"error_code": "BAD_REQUEST_ERROR", "error_source": "bank"},
        )
        repo.save(item)
        fetched = repo.get("ri_canon_001")
        assert fetched is not None
        assert fetched.external_id == "evt_razorpay_001"
        assert fetched.failure_category == "soft"
        assert fetched.provider == "razorpay"
        assert fetched.provider_event_id == "evt_razorpay_001"
        assert fetched.expected_recovery_value == 17500
        assert fetched.metadata["error_code"] == "BAD_REQUEST_ERROR"

    def test_update_status_only(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_canon_002",
            source_type=SourceType.CHECKOUT_ABANDONMENT,
            external_id="evt_002",
            customer_id="cust_002",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        )
        repo.save(item)
        repo.update_status("ri_canon_002", RecoveryStatus.QUEUED)
        fetched = repo.get("ri_canon_002")
        assert fetched.status == RecoveryStatus.QUEUED


# ---------------------------------------------------------------------------
# Recovery outcomes
# ---------------------------------------------------------------------------

class TestRecoveryOutcomeRepository:
    def test_save_and_get_outcome(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository, PostgresRecoveryOutcomeRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
        from datetime import datetime, timezone

        item_repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_out_001",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_out_001",
            customer_id="cust_001",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.RECOVERED,
        )
        item_repo.save(item)

        outcome_repo = PostgresRecoveryOutcomeRepository(db_conn)
        outcome = RecoveryOutcome(
            id="out_001",
            recovery_item_id="ri_out_001",
            outcome_type="recovered",
            expected_recovery_minor=17500,
            actual_recovery_minor=50000,
            recovery_cost_minor=500,
            net_recovery_minor=49500,
            recovered_at=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
        )
        outcome_repo.save(outcome)
        fetched = outcome_repo.get_for_item("ri_out_001")
        assert fetched is not None
        assert fetched.outcome_type == "recovered"
        assert fetched.actual_recovery_minor == 50000
        assert fetched.recovery_cost_minor == 500
        assert fetched.net_recovery_minor == 49500

    def test_outcome_upsert(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository, PostgresRecoveryOutcomeRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
        from datetime import datetime, timezone

        item_repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_out_002",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_out_002",
            customer_id="cust_001",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.FAILED,
        )
        item_repo.save(item)

        outcome_repo = PostgresRecoveryOutcomeRepository(db_conn)
        outcome1 = RecoveryOutcome(
            id="out_002",
            recovery_item_id="ri_out_002",
            outcome_type="failed",
            expected_recovery_minor=5000,
            actual_recovery_minor=0,
            recovery_cost_minor=200,
        )
        outcome_repo.save(outcome1)

        outcome2 = RecoveryOutcome(
            id="out_002",
            recovery_item_id="ri_out_002",
            outcome_type="partially_recovered",
            expected_recovery_minor=5000,
            actual_recovery_minor=3000,
            recovery_cost_minor=200,
        )
        outcome_repo.save(outcome2)
        fetched = outcome_repo.get_for_item("ri_out_002")
        assert fetched.outcome_type == "partially_recovered"
        assert fetched.actual_recovery_minor == 3000


# ---------------------------------------------------------------------------
# Promises
# ---------------------------------------------------------------------------

class TestPromiseRepository:
    def test_save_and_get_promise(self, db_conn):
        from app.db.postgres_repositories import PostgresRecoveryItemRepository, PostgresPromiseRepository
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, Promise
        from datetime import datetime, date, timezone

        item_repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_prom_001",
            source_type=SourceType.RECEIVABLE,
            external_id="evt_prom_001",
            customer_id="cust_001",
            amount_minor=20000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.QUEUED,
        )
        item_repo.save(item)

        promise_repo = PostgresPromiseRepository(db_conn)
        promise = Promise(
            id="prom_001",
            recovery_item_id="ri_prom_001",
            customer_id="cust_001",
            promised_amount_minor=20000,
            promised_date=date(2026, 9, 1),
            status="promised",
        )
        promise_repo.save(promise)
        fetched = promise_repo.get_for_item("ri_prom_001")
        assert fetched is not None
        assert fetched.promised_amount_minor == 20000
        assert fetched.status == "promised"


# ---------------------------------------------------------------------------
# Provider events
# ---------------------------------------------------------------------------

class TestProviderEventRepository:
    def test_save_and_get_event(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="evt_prov_001",
            provider="razorpay",
            provider_event_id="evt_razorpay_dup_test",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"payment": {"entity": {"id": "pay_001"}}},
            processing_status="pending",
        )
        repo.save(event)
        fetched = repo.get_by_provider_event("razorpay", "evt_razorpay_dup_test")
        assert fetched is not None
        assert fetched.event_type == "payment.failed"

    def test_duplicate_event_is_ignored(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="evt_prov_002",
            provider="razorpay",
            provider_event_id="evt_razorpay_dup_002",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_002"},
        )
        repo.save(event)
        repo.save(event)  # Second save should not raise
        events = db_conn.fetchall(
            "SELECT * FROM provider_events WHERE provider = %s AND provider_event_id = %s",
            ("razorpay", "evt_razorpay_dup_002"),
        )
        assert len(events) == 1

    def test_mark_processed(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="evt_prov_003",
            provider="razorpay",
            provider_event_id="evt_razorpay_mark",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_003"},
        )
        repo.save(event)
        repo.mark_processed("razorpay", "evt_razorpay_mark", recovery_item_id="ri_001")
        fetched = repo.get_by_provider_event("razorpay", "evt_razorpay_mark")
        assert fetched.processing_status == "processed"
        assert fetched.recovery_item_id == "ri_001"


# ---------------------------------------------------------------------------
# Audit immutability
# ---------------------------------------------------------------------------

class TestAuditImmutability:
    def test_audit_log_is_immutable_via_trigger(self, db_conn):
        db_conn._conn.execute("DELETE FROM audit_log")
        db_conn._conn.commit()
        db_conn._conn.execute(
            "INSERT INTO audit_log (recovery_item_id, actor, action) VALUES (%s, %s, %s)",
            ("ri_immut_001", "system", "test"),
        )
        db_conn._conn.commit()
        with pytest.raises(Exception):
            db_conn._conn.execute(
                "UPDATE audit_log SET action = %s WHERE recovery_item_id = %s",
                ("hacked", "ri_immut_001"),
            )
            db_conn._conn.commit()


# ---------------------------------------------------------------------------
# Recovery item relationships
# ---------------------------------------------------------------------------

class TestRecoveryItemRelationships:
    def test_item_with_attempts_and_outcome(self, db_conn):
        from app.db.postgres_repositories import (
            PostgresRecoveryItemRepository,
            PostgresAttemptLedger,
            PostgresRecoveryOutcomeRepository,
        )
        from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
        from app.ledger.attempts import AttemptRecord
        from datetime import datetime, timezone

        item_repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_rel_001",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_rel_001",
            customer_id="cust_001",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.RECOVERED,
        )
        item_repo.save(item)

        ledger = PostgresAttemptLedger(db_conn)
        ledger.record(AttemptRecord(recovery_item_id="ri_rel_001", attempt_number=1, action="retry_payment", outcome="failed"))
        ledger.record(AttemptRecord(recovery_item_id="ri_rel_001", attempt_number=2, action="send_reminder", outcome="success"))

        outcome_repo = PostgresRecoveryOutcomeRepository(db_conn)
        outcome = RecoveryOutcome(
            id="out_rel_001",
            recovery_item_id="ri_rel_001",
            outcome_type="recovered",
            expected_recovery_minor=17500,
            actual_recovery_minor=50000,
            recovery_cost_minor=500,
        )
        outcome_repo.save(outcome)

        item = item_repo.get("ri_rel_001")
        assert item is not None
        assert item.status == RecoveryStatus.RECOVERED

        attempts = ledger.attempts_for("ri_rel_001")
        assert len(attempts) == 2
        assert attempts[0].attempt_number == 1
        assert attempts[1].attempt_number == 2

        outcome = outcome_repo.get_for_item("ri_rel_001")
        assert outcome.outcome_type == "recovered"
        assert outcome.actual_recovery_minor == 50000


# ---------------------------------------------------------------------------
# Provider event idempotency and concurrency
# ---------------------------------------------------------------------------

class TestProviderEventIdempotency:
    def test_try_insert_new_event_returns_true(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="pe_concurrent_001",
            provider="razorpay",
            provider_event_id="evt_concurrent_001",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_001"},
        )
        is_new, fetched = repo.try_insert(event)
        assert is_new is True
        assert fetched is not None
        assert fetched.provider_event_id == "evt_concurrent_001"

    def test_try_insert_duplicate_returns_false(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="pe_concurrent_002",
            provider="razorpay",
            provider_event_id="evt_concurrent_002",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_002"},
        )
        repo.try_insert(event)
        is_new, fetched = repo.try_insert(event)
        assert is_new is False
        assert fetched is not None
        assert fetched.provider_event_id == "evt_concurrent_002"

    def test_concurrent_try_insert_only_one_row(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository
        from app.domain.models import ProviderEvent
        from datetime import datetime, timezone
        import threading

        repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="pe_concurrent_003",
            provider="razorpay",
            provider_event_id="evt_concurrent_003",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_003"},
        )
        results = []

        def insert_event():
            is_new, fetched = repo.try_insert(event)
            results.append(is_new)

        threads = [threading.Thread(target=insert_event) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        new_count = sum(1 for r in results if r is True)
        assert new_count == 1, f"Expected exactly 1 new insert, got {new_count}"

        rows = db_conn.fetchall(
            "SELECT * FROM provider_events WHERE provider = %s AND provider_event_id = %s",
            ("razorpay", "evt_concurrent_003"),
        )
        assert len(rows) == 1

    def test_provider_event_linked_to_recovery_item(self, db_conn):
        from app.db.postgres_repositories import PostgresProviderEventRepository, PostgresRecoveryItemRepository
        from app.domain.models import ProviderEvent, RecoveryItem, RecoveryStatus, SourceType
        from datetime import datetime, timezone

        item_repo = PostgresRecoveryItemRepository(db_conn)
        item = RecoveryItem(
            id="ri_link_001",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_link_001",
            customer_id="cust_001",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
        )
        item_repo.save(item)

        event_repo = PostgresProviderEventRepository(db_conn)
        event = ProviderEvent(
            id="pe_link_001",
            provider="razorpay",
            provider_event_id="evt_link_001",
            received_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
            event_type="payment.failed",
            raw_payload={"id": "pay_001"},
            recovery_item_id="ri_link_001",
            processing_status="processed",
        )
        event_repo.save(event)
        event_repo.mark_processed("razorpay", "evt_link_001", recovery_item_id="ri_link_001")
        fetched = event_repo.get_by_provider_event("razorpay", "evt_link_001")
        assert fetched.processing_status == "processed"
        assert fetched.recovery_item_id == "ri_link_001"
