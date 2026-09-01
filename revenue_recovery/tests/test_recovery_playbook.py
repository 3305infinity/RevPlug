"""Tests for Bounded Recovery Playbook Engine."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.services.recovery_playbook import RecoveryPlaybookEngine, RecoveryPlaybook
from app.policies.engine import InterventionPolicy


def test_playbook_generation_authentication_required():
    """Verifies authentication_required failure category generates bounded pivot sequence."""
    engine = RecoveryPlaybookEngine()
    item = RecoveryItem(
        id="item_pb_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_pb_1",
        customer_id="cust_101",
        amount_minor=500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="authentication_required",
    )
    ctx = RecoveryContext(
        failure_category=FailureCategory.AUTHENTICATION_REQUIRED,
        item_id=item.id,
        amount_minor=500000,
    )

    pb = engine.generate_playbook(item, ctx)

    assert pb.recovery_item_id == item.id
    assert pb.failure_category == "authentication_required"
    assert "Authentication" in pb.strategy_name
    assert len(pb.steps) >= 5
    assert pb.steps[0].action == "diagnose"
    assert pb.steps[1].action == "wait"
    assert pb.steps[2].action == "send_payment_link"
    assert pb.budget_remaining_minor > 0
    assert len(pb.stop_conditions) >= 4


def test_playbook_step_advance_on_observation():
    """Verifies playbook advances step status dynamically on observation re-evaluation."""
    engine = RecoveryPlaybookEngine()
    policy = InterventionPolicy()

    item = RecoveryItem(
        id="item_pb_2",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_pb_2",
        customer_id="cust_202",
        amount_minor=1000000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause="soft",
    )
    ctx = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        item_id=item.id,
        amount_minor=1000000,
    )

    pb = engine.generate_playbook(item, ctx)
    assert pb.current_step.action == "retry_payment"

    # Simulate execution failure
    obs_fail = {"action": "retry_payment", "success": False, "reason": "insufficient_funds"}
    updated_pb = engine.advance_playbook(pb, obs_fail, item, policy)

    assert updated_pb.status == "ACTIVE"
    assert updated_pb.current_step.action in ("send_payment_link", "alternate_channel")
    assert updated_pb.budget_used_minor > 0


def test_playbook_completion_on_verified_recovery():
    """Verifies successful payment observation completes the playbook immediately."""
    engine = RecoveryPlaybookEngine()
    item = RecoveryItem(
        id="item_pb_3",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_pb_3",
        customer_id="cust_303",
        amount_minor=750000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.INTERVENTION_EXECUTED,
        root_cause="soft",
    )
    ctx = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        item_id=item.id,
        amount_minor=750000,
    )

    pb = engine.generate_playbook(item, ctx)
    obs_success = {"action": "send_payment_link", "success": True, "outcome": "recovered"}

    updated_pb = engine.advance_playbook(pb, obs_success, item)

    assert updated_pb.status == "COMPLETED_RECOVERED"
    assert updated_pb.expected_remaining_recovery_minor == 0
