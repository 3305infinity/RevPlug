from datetime import datetime, timezone

import pytest

from app.audit.models import InMemoryAuditLog
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.interventions.simulated import SimulatedIntervention
from app.policies.engine import InterventionPolicy, PolicyDecision
from app.scoring.expected_value import ExpectedValueScorer
from app.services.pipeline import RecoveryPipeline


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def build_item(utcnow, **overrides):
    data = {
        "id": "ri_1",
        "source_type": SourceType.PAYMENT_FAILURE,
        "external_id": "ext_1",
        "customer_id": "C_1",
        "amount_minor": 10000,
        "currency": "INR",
        "created_at": utcnow,
        "status": RecoveryStatus.DETECTED,
        "root_cause": "temporary_processing",
        "recovery_probability": 0.4,
        "metadata": {},
    }
    data.update(overrides)
    return RecoveryItem(**data)


def test_pipeline_scores_and_queues_item(utcnow):
    audit_log = InMemoryAuditLog()
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=InterventionPolicy(max_retry_attempts=2),
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    item = build_item(utcnow, recovery_probability=0.6)
    result, events = pipeline.process(item)
    assert result.status == RecoveryStatus.INTERVENTION_EXECUTED
    assert result.expected_recovery_value == 6000


def test_pipeline_blocks_hard_failure_retry(utcnow):
    audit_log = InMemoryAuditLog()
    policy = InterventionPolicy(max_retry_attempts=3)
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=policy,
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    item = build_item(utcnow, root_cause="hard_decline", recovery_probability=0.1)
    # Force the diagnose step to propose retry so we can verify policy blocks it
    pipeline._diagnose = lambda item: "retry_payment"  # type: ignore[assignment]
    result, events = pipeline.process(item)
    assert result.status == RecoveryStatus.QUEUED
    policy_events = [e for e in events if e.action == "policy_evaluate"]
    assert len(policy_events) == 1
    assert policy_events[0].metadata["allowed"] is False
    assert policy_events[0].metadata["policy_rule"] == "block_hard_failure"


def test_pipeline_requires_human_approval_for_exhausted_retry(utcnow):
    audit_log = InMemoryAuditLog()
    policy = InterventionPolicy(max_retry_attempts=1)
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=policy,
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    item = build_item(utcnow, metadata={"attempt_count": 1})
    pipeline._diagnose = lambda item: "retry_payment"  # type: ignore[assignment]
    result, events = pipeline.process(item)
    assert result.status == RecoveryStatus.QUEUED
    pending_events = [e for e in events if e.action == "intervention_pending"]
    assert len(pending_events) == 1
    assert "Human approval required" in pending_events[0].reason


def test_pipeline_executes_allowed_intervention(utcnow):
    audit_log = InMemoryAuditLog()
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=InterventionPolicy(max_retry_attempts=2),
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    item = build_item(utcnow, recovery_probability=0.6)
    result, events = pipeline.process(item)
    assert result.status == RecoveryStatus.INTERVENTION_EXECUTED
    execute_events = [e for e in events if e.action == "intervention_execute"]
    assert len(execute_events) == 1
    assert execute_events[0].metadata["success"] is True


def test_pipeline_blocks_unknown_action(utcnow):
    audit_log = InMemoryAuditLog()
    policy = InterventionPolicy(max_retry_attempts=2)
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=policy,
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    pipeline._diagnose = lambda item: "mystery_action"  # type: ignore[assignment]
    item = build_item(utcnow, recovery_probability=0.4)
    result, events = pipeline.process(item)
    policy_events = [e for e in events if e.action == "policy_evaluate"]
    assert len(policy_events) == 1
    assert policy_events[0].metadata["allowed"] is False
    assert policy_events[0].metadata["policy_rule"] == "default_deny"


def test_pipeline_opted_out_customer_is_not_contacted(utcnow):
    audit_log = InMemoryAuditLog()
    policy = InterventionPolicy(opted_out_customer_ids=frozenset({"C_BLOCKED"}))
    pipeline = RecoveryPipeline(
        scorer=ExpectedValueScorer(),
        policy_engine=policy,
        intervention=SimulatedIntervention(),
        audit_log=audit_log,
    )
    item = build_item(utcnow, customer_id="C_BLOCKED", recovery_probability=0.4)
    result, events = pipeline.process(item)
    policy_events = [e for e in events if e.action == "policy_evaluate"]
    assert len(policy_events) == 1
    assert policy_events[0].metadata["allowed"] is False
    assert policy_events[0].metadata["policy_rule"] == "opt_out_block"
