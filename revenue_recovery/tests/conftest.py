from datetime import datetime, timezone

import pytest

from app.audit.models import AuditEvent, InMemoryAuditLog
from app.domain.events import (
    CheckoutAbandonmentEvent,
    PaymentFailureEvent,
    ReceivableOverdueEvent,
)
from app.domain.models import (
    RecoveryItem,
    RecoveryStatus,
    SourceType,
)
from app.interventions.simulated import SimulatedIntervention
from app.policies.engine import InterventionPolicy, PolicyEngine
from app.scoring.expected_value import ExpectedValueScorer, RecoveryScorer
from app.services.pipeline import RecoveryPipeline


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def audit_log():
    return InMemoryAuditLog()


@pytest.fixture
def scorer():
    return ExpectedValueScorer()


@pytest.fixture
def policy_engine():
    return InterventionPolicy(
        max_retry_attempts=2,
        autonomous_discount_minor=5000,
        opted_out_customer_ids=frozenset({"C_BLOCKED"}),
    )


@pytest.fixture
def intervention():
    return SimulatedIntervention()


@pytest.fixture
def pipeline(scorer, policy_engine, intervention, audit_log):
    return RecoveryPipeline(
        scorer=scorer,
        policy_engine=policy_engine,
        intervention=intervention,
        audit_log=audit_log,
    )


@pytest.fixture
def payment_failure_item(utcnow):
    return RecoveryItem(
        id="ri_001",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_001",
        customer_id="C_1",
        amount_minor=10000,
        currency="INR",
        created_at=utcnow,
        due_at=utcnow,
        status=RecoveryStatus.DETECTED,
        root_cause="temporary_processing",
        recovery_probability=0.4,
    )


@pytest.fixture
def receivable_item(utcnow):
    return RecoveryItem(
        id="ri_002",
        source_type=SourceType.RECEIVABLE,
        external_id="inv_001",
        customer_id="C_2",
        amount_minor=50000,
        currency="INR",
        created_at=utcnow,
        due_at=utcnow,
        status=RecoveryStatus.DETECTED,
        root_cause="overdue",
        recovery_probability=0.25,
        metadata={"days_overdue": 7},
    )


@pytest.fixture
def checkout_item(utcnow):
    return RecoveryItem(
        id="ri_003",
        source_type=SourceType.CHECKOUT_ABANDONMENT,
        external_id="cart_001",
        customer_id="C_3",
        amount_minor=25000,
        currency="INR",
        created_at=utcnow,
        status=RecoveryStatus.DETECTED,
        recovery_probability=0.15,
        metadata={"stage": "checkout_started"},
    )
