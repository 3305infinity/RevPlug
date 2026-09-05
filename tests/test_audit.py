from datetime import datetime, timezone

import pytest

from app.audit.models import AuditEvent, InMemoryAuditLog


def test_log_creates_event():
    log = InMemoryAuditLog()
    event = log.log("ri_1", "system", "score", reason="scored", metadata={"value": 100})
    assert event.id == "audit_1"
    assert event.recovery_item_id == "ri_1"
    assert event.actor == "system"
    assert event.action == "score"
    assert event.reason == "scored"
    assert event.metadata == {"value": 100}
    assert isinstance(event.timestamp, datetime)


def test_log_appends_only():
    log = InMemoryAuditLog()
    log.log("ri_1", "system", "a")
    log.log("ri_1", "system", "b")
    log.log("ri_1", "rule", "c")
    assert len(log.events_for("ri_1")) == 3
    assert log.events_for("ri_1")[0].action == "a"
    assert log.events_for("ri_1")[2].action == "c"


def test_events_for_isolates_by_recovery_item_id():
    log = InMemoryAuditLog()
    log.log("ri_1", "system", "a")
    log.log("ri_2", "system", "b")
    assert len(log.events_for("ri_1")) == 1
    assert len(log.events_for("ri_2")) == 1


def test_log_without_metadata():
    log = InMemoryAuditLog()
    event = log.log("ri_1", "system", "test")
    assert event.metadata == {}


def test_log_without_reason():
    log = InMemoryAuditLog()
    event = log.log("ri_1", "system", "test")
    assert event.reason is None


def test_incremental_ids():
    log = InMemoryAuditLog()
    first = log.log("ri_1", "system", "a")
    second = log.log("ri_1", "system", "b")
    assert first.id == "audit_1"
    assert second.id == "audit_2"
