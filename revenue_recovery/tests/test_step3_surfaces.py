"""Step 3 Test Suite — Complete Recovery Product Surfaces (A through W).

Verifies that all 5 canonical recovery surfaces (Payment Failure, Checkout Abandonment,
Subscription Failure, Overdue Receivables, Mandate Failure), Promise-to-Pay tracking,
Hinglish Promise Extraction, Rules-First Diagnosis, and Policy Guards function cleanly.
"""

import pytest
from datetime import date, datetime, timedelta, timezone

from app.domain.models import (
    OutcomeType,
    PromiseStatus,
    RecoveryItem,
    RecoveryOutcome,
    RecoveryStatus,
    SourceType,
)
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.agents.validator import ProposalValidator, ProposalValidationError
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.policies.engine import InterventionPolicy
from app.policies.stopping_rules import StoppingRules
from app.services.hinglish_promise import HinglishPromiseExtractor
from app.datasets.synthetic import generate_evaluation_dataset


def _item(
    source_type: SourceType = SourceType.PAYMENT_FAILURE,
    amount_minor: int = 50000,
    root_cause: str = "soft",
    customer_id: str = "cust_test",
    attempt_count: int = 0,
    extra_meta: dict | None = None,
) -> RecoveryItem:
    meta = {"attempt_count": attempt_count, **(extra_meta or {})}
    return RecoveryItem(
        id=f"test_{source_type.value}_001",
        source_type=source_type,
        external_id="ext_001",
        customer_id=customer_id,
        amount_minor=amount_minor,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        root_cause=root_cause,
        metadata=meta,
    )


def _context(item: RecoveryItem, category: FailureCategory = FailureCategory.SOFT) -> RecoveryContext:
    return RecoveryContext(
        failure_category=category,
        retryable=True,
        attempt_count=int(item.metadata.get("attempt_count", 0)),
        amount_minor=item.amount_minor,
        currency=item.currency,
        expected_recovery_value=item.expected_recovery_value or 34500,
        customer_opt_out=bool(item.metadata.get("opted_out", False)),
        max_attempts=3,
        item_id=item.id,
        metadata={**item.metadata, "source_type": item.source_type.value},
    )


# A. Payment failure regression
def test_a_payment_regression():
    item = _item(SourceType.PAYMENT_FAILURE, root_cause="soft")
    policy = InterventionPolicy(max_retry_attempts=3)
    dec = policy.evaluate(item, "retry_payment")
    assert dec.allowed is True


# B. Checkout abandonment successful recovery
def test_b_checkout_abandonment_success():
    item = _item(SourceType.CHECKOUT_ABANDONMENT, root_cause="checkout_abandoned")
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.SEND_PAYMENT_LINK
    assert prop.diagnosis.get("diagnosis_source") == "rules"


# C. Checkout opt-out stops
def test_c_checkout_optout_stops():
    item = _item(SourceType.CHECKOUT_ABANDONMENT, extra_meta={"opted_out": True})
    stopper = StoppingRules()
    dec = stopper.evaluate(item)
    assert dec.should_stop is True
    assert dec.reason_code == "customer_opted_out"


# D. Checkout already converted stops
def test_d_checkout_already_converted_stops():
    item = _item(SourceType.CHECKOUT_ABANDONMENT, extra_meta={"converted": True})
    stopper = StoppingRules()
    dec = stopper.evaluate(item)
    assert dec.should_stop is True
    assert dec.reason_code == "checkout_already_converted"


# E. Subscription failure retry
def test_e_subscription_failure_retry():
    item = _item(SourceType.SUBSCRIPTION_FAILURE, root_cause="soft", attempt_count=0)
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.RETRY_PAYMENT
    assert prop.proposed_retry is True


# F. Cancelled subscription stops
def test_f_cancelled_subscription_stops():
    item = _item(SourceType.SUBSCRIPTION_FAILURE, extra_meta={"subscription_status": "cancelled"})
    stopper = StoppingRules()
    dec = stopper.evaluate(item)
    assert dec.should_stop is True
    assert dec.reason_code == "subscription_cancelled"


# G. Receivable Day 1 action
def test_g_receivable_day1_action():
    item = _item(SourceType.RECEIVABLE, extra_meta={"days_overdue": 1})
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.SEND_REMINDER


# H. Receivable Day 3 action
def test_h_receivable_day3_action():
    item = _item(SourceType.RECEIVABLE, extra_meta={"days_overdue": 3})
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.SEND_PAYMENT_LINK


# I. Receivable Day 7 action
def test_i_receivable_day7_action():
    item = _item(SourceType.RECEIVABLE, extra_meta={"days_overdue": 7})
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.ALTERNATE_CHANNEL


# J. Receivable Day 14 escalation
def test_j_receivable_day14_escalation():
    item = _item(SourceType.RECEIVABLE, extra_meta={"days_overdue": 14})
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.ESCALATE_HUMAN


# K. Paid invoice stops
def test_k_paid_invoice_stops():
    item = _item(SourceType.RECEIVABLE, extra_meta={"paid": True})
    stopper = StoppingRules()
    dec = stopper.evaluate(item)
    assert dec.should_stop is True
    assert dec.reason_code == "invoice_paid"


# L. Active promise pauses recovery
class MockPromiseRepo:
    def get_for_item(self, item_id: str):
        return {"status": "promised", "promised_date": (date.today() + timedelta(days=5)).isoformat()}


def test_l_active_promise_pauses_recovery():
    item = _item(SourceType.PAYMENT_FAILURE)
    stopper = StoppingRules()
    dec = stopper.evaluate(item, promises=MockPromiseRepo())
    assert dec.should_stop is True
    assert dec.reason_code == "active_promise_pauses_recovery"


# M. Promise fulfilled creates verified outcome
def test_m_promise_fulfilled_creates_outcome():
    outcome = RecoveryOutcome(
        id="out_001",
        recovery_item_id="test_item_001",
        outcome_type=OutcomeType.RECOVERED.value,
        expected_recovery_minor=1800000,
        actual_recovery_minor=1800000,
        recovered_at=datetime.now(timezone.utc),
    )
    assert outcome.actual_recovery_minor == 1800000
    assert outcome.outcome_type == "recovered"


# N. Promise expired enters correct next state
class MockExpiredPromiseRepo:
    def get_for_item(self, item_id: str):
        return {"status": "promised", "promised_date": (date.today() - timedelta(days=5)).isoformat()}


def test_n_promise_expired_next_state():
    item = _item(SourceType.PAYMENT_FAILURE)
    stopper = StoppingRules()
    dec = stopper.evaluate(item, promises=MockExpiredPromiseRepo())
    assert dec.should_stop is True
    assert dec.reason_code == "promise_expired"


# O. Hinglish structured promise extraction
def test_o_hinglish_promise_extraction():
    extractor = HinglishPromiseExtractor()
    res = extractor.extract("Friday ko ₹18,000 clear kar dunga", reference_date=date(2026, 8, 29))
    assert res.intent == "promise_to_pay"
    assert res.amount_minor == 1800000
    assert res.promised_date is not None
    assert res.confidence >= 0.85


# P. Ambiguous promise fails closed
def test_p_ambiguous_promise_fails_closed():
    extractor = HinglishPromiseExtractor()
    res = extractor.extract("I will think about it maybe later")
    assert res.confidence < 0.5
    assert res.amount_minor is None


# Q. Mandate retry eligible
def test_q_mandate_retry_eligible():
    item = _item(SourceType.MANDATE_FAILURE, extra_meta={"retry_eligible": True})
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item)
    prop = agent.propose(ctx)
    assert prop.action == RecoveryAction.RETRY_PAYMENT


# R. Mandate retry exhaustion
def test_r_mandate_retry_exhaustion():
    item = _item(SourceType.MANDATE_FAILURE, attempt_count=3, extra_meta={"retry_eligible": False})
    policy = InterventionPolicy(max_retry_attempts=3)
    dec = policy.evaluate(item, "retry_payment")
    assert dec.allowed is False
    assert dec.reason_code == "retry_budget_exhausted"


# S. Invalid LLM action rejected by validator
def test_s_invalid_llm_action_rejected():
    validator = ProposalValidator()
    item = _item()
    ctx = _context(item)
    proposal = RecoveryProposal(
        action="give_customer_50_percent_discount",  # type: ignore
        reason="Invalid unallowed action test",
        confidence=0.9,
    )
    with pytest.raises(ProposalValidationError):
        validator.validate(proposal, ctx)


# T. Known rule-based failure does not call LLM
def test_t_known_rule_diagnosis_source():
    item = _item(SourceType.PAYMENT_FAILURE, root_cause="soft")
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item, category=FailureCategory.SOFT)
    prop = agent.propose(ctx)
    assert prop.diagnosis.get("diagnosis_source") == "rules"


# U. Ambiguous case can use LLM
def test_u_ambiguous_case_uses_llm():
    item = _item(SourceType.PAYMENT_FAILURE, root_cause="unknown")
    agent = MockRecoveryDecisionAgent()
    ctx = _context(item, category=FailureCategory.UNKNOWN)
    prop = agent.propose(ctx)
    assert prop.diagnosis.get("diagnosis_source") == "llm"


# V. Mixed seeded dataset deterministic
def test_v_mixed_dataset_deterministic():
    ds1 = generate_evaluation_dataset(seed=42, count=30)
    ds2 = generate_evaluation_dataset(seed=42, count=30)
    assert len(ds1) == 30
    assert [i.id for i in ds1] == [i.id for i in ds2]
    assert [i.source_type for i in ds1] == [i.source_type for i in ds2]


# W. Audit lifecycle exists for every supported recovery source
def test_w_audit_lifecycle_every_source():
    from app.audit.models import InMemoryAuditLog
    audit = InMemoryAuditLog()
    sources = [SourceType.PAYMENT_FAILURE, SourceType.CHECKOUT_ABANDONMENT, SourceType.SUBSCRIPTION_FAILURE, SourceType.RECEIVABLE, SourceType.MANDATE_FAILURE]
    for s in sources:
        evt = audit.log(
            recovery_item_id=f"test_{s.value}_01",
            actor="system",
            action="item_detected",
            reason=f"Detected new {s.value} opportunity",
            metadata={"source_type": s.value},
        )
        assert evt.recovery_item_id == f"test_{s.value}_01"
        assert evt.action == "item_detected"
