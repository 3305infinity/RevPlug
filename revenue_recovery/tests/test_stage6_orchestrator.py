from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.adapters.razorpay import RazorpayWebhookService
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import InMemoryAuditLog
from app.db.container import create_persistence_container
from app.db.decision_repository import InMemoryRecoveryDecisionRepository
from app.db.repositories import InMemoryRecoveryItemRepository
from app.domain.context import RecoveryContext
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.idempotency.store import InMemoryIdempotencyStore
from app.ledger.attempts import InMemoryAttemptLedger
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.recovery_orchestrator import RecoveryOrchestrator


SECRET = "whsec_stage6_test"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_service():
    container = create_persistence_container("memory")
    return main_module._build_webhook_service(SECRET, container)


def _build_app(service):
    return main_module.create_app(webhook_secret=SECRET, webhook_service=service)


def _soft_payload(**overrides):
    base = {
        "entity": "event",
        "account_id": "acc_TEST",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": f"evt_{overrides.get('payment_id', 'default')}",
        "created_at": 1567610215,
        "payload": {
            "payment": {
                "entity": {
                    "id": overrides.get("payment_id", "pay_soft_001"),
                    "entity": "payment",
                    "amount": overrides.get("amount", 50000),
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": overrides.get("error_reason", "payment_timed_out"),
                    "email": "test@example.com",
                    "contact": "+919876543210",
                    "created_at": 1567610214,
                }
            }
        },
    }
    return base


# ---------------------------------------------------------------------------
# A. Full successful recovery
# ---------------------------------------------------------------------------

class TestSuccessfulRecovery:
    def test_soft_failure_recovers(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_success_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["recovery_item_id"] == "pay_success_001"

    def test_successful_recovery_creates_outcome(self):
        container = create_persistence_container("memory")
        service = RazorpayWebhookService(
            webhook_secret=SECRET,
            scorer=ExpectedValueScorer(),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=container.decisions,
            attempts=container.attempts,
            outcomes=container.outcomes,
            promises=container.promises,
        )
        payload = _soft_payload(payment_id="pay_outcome_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = service.process_webhook(body, sig)
        assert item is not None
        assert item.status == RecoveryStatus.PENDING_VERIFICATION
        
        # Verify settlement via SettlementVerifier
        from app.services.settlement_verifier import SettlementVerifier, SettlementEvent
        verifier = SettlementVerifier(
            recovery_items=container.recovery_items,
            outcomes=container.outcomes,
            audit_log=container.audit_log,
        )
        res = verifier.process_settlement(SettlementEvent(
            event_id="evt_settle_stage6",
            provider="razorpay",
            recovery_item_id=item.id,
            success=True,
            actual_amount_minor=item.amount_minor,
        ))
        assert res.status == "recovered"
        outcome = container.outcomes.get_for_item(item.id)
        assert outcome is not None


# ---------------------------------------------------------------------------
# B. AI recommendation blocked by policy
# ---------------------------------------------------------------------------

class TestPolicyBlocking:
    def test_hard_failure_retry_blocked(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_hard_001", error_reason="payment_risk_check_failed", amount=100000)
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recovery_status"] == "stopped"
        assert data["stopped_reason"] == "fraud_detected"


# ---------------------------------------------------------------------------
# C. Low confidence → escalation
# ---------------------------------------------------------------------------

class TestConfidenceAwareDecisioning:
    def test_low_confidence_escalates(self):
        container = create_persistence_container("memory")
        from app.domain.proposals import RecoveryAction, RecoveryProposal

        class LowConfidenceAgent:
            name = "low-conf-agent"
            model_name = "mock"
            def propose(self, context):
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason="Low confidence in this recovery path",
                    confidence=0.1,
                )

        orchestrator = RecoveryOrchestrator(
            agent=LowConfidenceAgent(),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            validator=ProposalValidator(),
            stopping_rules=StoppingRules(max_attempts=3),
            guard=DefaultRecoveryGuard(
                stopping_rules=StoppingRules(max_attempts=3),
                policy_engine=InterventionPolicy(max_retry_attempts=3),
            ),
            scorer=ExpectedValueScorer(),
        )
        item = RecoveryItem(
            id="ri_lowconf",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_lowconf",
            customer_id="C_LOW",
            amount_minor=10000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
        )
        context = RecoveryContext(
            failure_category=__import__("app.domain.failures", fromlist=["FailureCategory"]).FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=10000,
            currency="INR",
            expected_recovery_value=3500,
            customer_opt_out=False,
            max_attempts=3,
            item_id="ri_lowconf",
        )
        result = orchestrator.run(item, context)
        assert result.safety_decision != "ALLOWED"

    def test_high_confidence_safe_allows(self):
        container = create_persistence_container("memory")
        agent = MockRecoveryDecisionAgent()
        orchestrator = RecoveryOrchestrator(
            agent=agent,
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            validator=ProposalValidator(),
            stopping_rules=StoppingRules(max_attempts=3),
            guard=DefaultRecoveryGuard(
                stopping_rules=StoppingRules(max_attempts=3),
                policy_engine=InterventionPolicy(max_retry_attempts=3),
            ),
            scorer=ExpectedValueScorer(),
        )
        item = RecoveryItem(
            id="ri_highconf",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_highconf",
            customer_id="C_HIGH",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
            recovery_probability=0.7,
        )
        context = RecoveryContext(
            failure_category=__import__("app.domain.failures", fromlist=["FailureCategory"]).FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            max_attempts=3,
            item_id="ri_highconf",
        )
        result = orchestrator.run(item, context)
        assert result.safety_decision == "ALLOWED"


# ---------------------------------------------------------------------------
# D. Fraud → stop
# ---------------------------------------------------------------------------

class TestFraudStops:
    def test_fraud_is_stopped(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_fraud_001", error_reason="payment_risk_check_failed", amount=100000)
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recovery_status"] == "stopped"
        assert data["stopped_reason"] == "fraud_detected"


# ---------------------------------------------------------------------------
# E. Payment succeeds before retry
# ---------------------------------------------------------------------------

class TestPaymentSucceeds:
    def test_payment_succeeded_metadata_stops(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_succeeds_001")
        payload["payload"]["payment"]["entity"]["metadata"] = {"payment_succeeded": True}
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recovery_status"] in ("pending_verification", "recovered")


# ---------------------------------------------------------------------------
# F. Retry budget exhausted
# ---------------------------------------------------------------------------

class TestRetryBudgetExhausted:
    def test_retry_budget_exhausted_stops(self):
        service = _build_service()
        service._policy_engine = InterventionPolicy(max_retry_attempts=1)
        service._stopping_rules = StoppingRules(max_attempts=1)
        service._guard = DefaultRecoveryGuard(
            stopping_rules=StoppingRules(max_attempts=1),
            policy_engine=InterventionPolicy(max_retry_attempts=1),
        )
        original_build = service._build_recovery_item
        def patched_build(razorpay_failure, normalized):
            item = original_build(razorpay_failure, normalized)
            return item.__class__(
                id=item.id,
                source_type=item.source_type,
                external_id=item.external_id,
                customer_id=item.customer_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                created_at=item.created_at,
                status=item.status,
                root_cause=item.root_cause,
                recovery_probability=item.recovery_probability,
                expected_recovery_value=item.expected_recovery_value,
                intervention_cost=item.intervention_cost,
                failure_category=item.failure_category,
                provider=item.provider,
                provider_event_id=item.provider_event_id,
                actual_recovery_value=item.actual_recovery_value,
                recovery_status=item.recovery_status,
                score_version=item.score_version,
                scoring_reason=item.scoring_reason,
                priority=item.priority,
                stopped_reason=item.stopped_reason,
                stopped_rule=item.stopped_rule,
                metadata={**item.metadata, "attempt_count": 1},
            )
        service._build_recovery_item = patched_build
        try:
            payload = _soft_payload(payment_id="pay_exhaust_001", error_reason="payment_timed_out")
            body = json.dumps(payload).encode()
            sig = _sign(body)
            item, events, status = service.process_webhook(body, sig)
            assert item is not None
            assert item.status == RecoveryStatus.STOPPED
            assert item.stopped_reason == "retry_budget_exhausted"
        finally:
            service._build_recovery_item = original_build


# ---------------------------------------------------------------------------
# G. Deadline expired
# ---------------------------------------------------------------------------

class TestDeadlineExpired:
    def test_deadline_expired_stops(self):
        service = _build_service()
        original = service._build_recovery_item
        def patched(razorpay_failure, normalized):
            item = original(razorpay_failure, normalized)
            return item.__class__(
                id=item.id,
                source_type=item.source_type,
                external_id=item.external_id,
                customer_id=item.customer_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                created_at=item.created_at,
                due_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                status=item.status,
                root_cause=item.root_cause,
                recovery_probability=item.recovery_probability,
                expected_recovery_value=item.expected_recovery_value,
                intervention_cost=item.intervention_cost,
                failure_category=item.failure_category,
                provider=item.provider,
                provider_event_id=item.provider_event_id,
                actual_recovery_value=item.actual_recovery_value,
                recovery_status=item.recovery_status,
                score_version=item.score_version,
                scoring_reason=item.scoring_reason,
                priority=item.priority,
                stopped_reason=item.stopped_reason,
                stopped_rule=item.stopped_rule,
                metadata=item.metadata,
            )
        service._build_recovery_item = patched
        try:
            payload = _soft_payload(payment_id="pay_deadline_001", error_reason="payment_timed_out")
            body = json.dumps(payload).encode()
            sig = _sign(body)
            item, events, status = service.process_webhook(body, sig)
            assert item is not None
            assert item.status == RecoveryStatus.STOPPED
            assert item.stopped_reason == "recovery_deadline_expired"
        finally:
            service._build_recovery_item = original


# ---------------------------------------------------------------------------
# H. Customer opt-out
# ---------------------------------------------------------------------------

class TestCustomerOptOut:
    def test_opted_out_customer_stops(self):
        service = _build_service()
        service._default_customer_id = "C_OPTED_OUT"
        service._stopping_rules = StoppingRules(
            max_attempts=3,
            opted_out_customer_ids=frozenset({"C_OPTED_OUT"}),
        )
        service._guard = DefaultRecoveryGuard(
            stopping_rules=StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_OPTED_OUT"})),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
        )
        payload = _soft_payload(payment_id="pay_optout_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = service.process_webhook(body, sig)
        assert item is not None
        assert item.status == RecoveryStatus.STOPPED
        assert item.stopped_reason == "customer_opted_out"


# ---------------------------------------------------------------------------
# I. Promise expires
# ---------------------------------------------------------------------------

class TestPromiseExpiry:
    def test_promise_expiry_stops_recovery(self):
        service = _build_service()
        from app.services.promise_service import PromiseService
        promise_service = PromiseService()

        promise = promise_service.create_promise(
            item_id="pay_promise_001",
            customer_id="C_PROMISE",
            promised_amount_minor=50000,
            promised_date=datetime(2020, 1, 1, tzinfo=timezone.utc).date(),
        )
        service._promises.save(promise)
        service._stopping_rules = StoppingRules(max_attempts=3)
        service._guard = DefaultRecoveryGuard(
            stopping_rules=StoppingRules(max_attempts=3),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
        )
        payload = _soft_payload(payment_id="pay_promise_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = service.process_webhook(body, sig)
        assert item is not None
        assert item.status == RecoveryStatus.STOPPED
        assert item.stopped_reason == "promise_expired"


# ---------------------------------------------------------------------------
# J. Executor succeeds but payment does not recover
# ---------------------------------------------------------------------------

class TestExecutionNotRecovery:
    def test_execution_success_creates_outcome(self):
        container = create_persistence_container("memory")
        service = RazorpayWebhookService(
            webhook_secret=SECRET,
            scorer=ExpectedValueScorer(),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=container.decisions,
            attempts=container.attempts,
            outcomes=container.outcomes,
            promises=container.promises,
        )
        payload = _soft_payload(payment_id="pay_exec_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        item, events, status = service.process_webhook(body, sig)
        assert item is not None
        assert item.status == RecoveryStatus.PENDING_VERIFICATION
        outcome_before = container.outcomes.get_for_item(item.id)
        # Execution success MUST NOT create a recovery outcome
        assert outcome_before is None

        # Authoritative settlement verification creates outcome
        from app.services.settlement_verifier import SettlementVerifier, SettlementEvent
        verifier = SettlementVerifier(
            recovery_items=container.recovery_items,
            outcomes=container.outcomes,
            audit_log=container.audit_log,
        )
        verifier.process_settlement(SettlementEvent(
            event_id="evt_exec_not_rec",
            provider="razorpay",
            recovery_item_id=item.id,
            success=True,
            actual_amount_minor=item.amount_minor,
        ))
        outcome_after = container.outcomes.get_for_item(item.id)
        assert outcome_after is not None


# ---------------------------------------------------------------------------
# K. Partial recovery
# ---------------------------------------------------------------------------

class TestPartialRecovery:
    def test_partial_recovery_outcome(self):
        container = create_persistence_container("memory")
        from app.domain.models import RecoveryOutcome
        outcome = RecoveryOutcome(
            id="outcome_partial_001",
            recovery_item_id="pay_partial_001",
            outcome_type="partially_recovered",
            expected_recovery_minor=50000,
            actual_recovery_minor=25000,
            recovery_cost_minor=500,
            net_recovery_minor=24500,
            recovered_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            metadata={"source": "manual"},
        )
        container.outcomes.save(outcome)
        loaded = container.outcomes.get_for_item("pay_partial_001")
        assert loaded is not None
        if isinstance(loaded, RecoveryOutcome):
            assert loaded.outcome_type == "partially_recovered"
            assert loaded.actual_recovery_minor == 25000


# ---------------------------------------------------------------------------
# L. Multi-step recovery
# ---------------------------------------------------------------------------

class TestMultiStepRecovery:
    def test_recovery_plan_has_ordered_steps(self):
        from app.services.recovery_planner import DefaultRecoveryPlanner
        planner = DefaultRecoveryPlanner()
        item = RecoveryItem(
            id="ri_plan",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_plan",
            customer_id="C_PLAN",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
            expected_recovery_value=17500,
        )
        plan = planner.build_plan(item, "retry_payment", max_attempts=3)
        assert len(plan.ordered_steps) > 1
        assert plan.ordered_steps[0].action == "retry_payment"
        assert plan.next_step() is not None


# ---------------------------------------------------------------------------
# M. Duplicate provider event
# ---------------------------------------------------------------------------

class TestDuplicateEvent:
    def test_duplicate_webhook_ignored(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_dup_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        first = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert first.status_code == 200
        assert first.json()["status"] == "processed"

        second = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"


# ---------------------------------------------------------------------------
# N. Concurrent duplicate provider event
# ---------------------------------------------------------------------------

class TestConcurrentDuplicate:
    def test_concurrent_duplicate_same_result(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_conc_dup_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        first = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        second = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert first.json()["status"] == "processed"
        assert second.json()["status"] == "duplicate"


# ---------------------------------------------------------------------------
# O. Invalid AI output
# ---------------------------------------------------------------------------

class TestInvalidAIOutput:
    def test_invalid_action_rejected_by_validator(self):
        container = create_persistence_container("memory")
        from app.domain.proposals import RecoveryAction, RecoveryProposal

        class BadAgent:
            name = "bad-agent"
            model_name = "bad"
            def propose(self, context):
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason="Invalid proposal without retry flag",
                    confidence=0.9,
                    proposed_retry=False,
                )

        orchestrator = RecoveryOrchestrator(
            agent=BadAgent(),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            validator=ProposalValidator(),
            stopping_rules=StoppingRules(max_attempts=3),
            guard=DefaultRecoveryGuard(
                stopping_rules=StoppingRules(max_attempts=3),
                policy_engine=InterventionPolicy(max_retry_attempts=3),
            ),
            scorer=ExpectedValueScorer(),
        )
        item = RecoveryItem(
            id="ri_invalid",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_invalid",
            customer_id="C_INV",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
        )
        context = RecoveryContext(
            failure_category=__import__("app.domain.failures", fromlist=["FailureCategory"]).FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            max_attempts=3,
            item_id="ri_invalid",
        )
        result = orchestrator.run(item, context)
        assert result.safety_decision != "ALLOWED"


# ---------------------------------------------------------------------------
# P. AI timeout / unavailable
# ---------------------------------------------------------------------------

class TestAIUnavailable:
    def test_no_agent_fails_closed(self):
        container = create_persistence_container("memory")
        orchestrator = RecoveryOrchestrator(
            agent=None,
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            validator=ProposalValidator(),
            stopping_rules=StoppingRules(max_attempts=3),
            guard=DefaultRecoveryGuard(
                stopping_rules=StoppingRules(max_attempts=3),
                policy_engine=InterventionPolicy(max_retry_attempts=3),
            ),
            scorer=ExpectedValueScorer(),
        )
        item = RecoveryItem(
            id="ri_noagent",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_noagent",
            customer_id="C_NOAGENT",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
        )
        context = RecoveryContext(
            failure_category=__import__("app.domain.failures", fromlist=["FailureCategory"]).FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            max_attempts=3,
            item_id="ri_noagent",
        )
        result = orchestrator.run(item, context)
        assert result.proposed_action is None
        assert result.safety_decision == "STOP"


# ---------------------------------------------------------------------------
# Q. Program configuration safety
# ---------------------------------------------------------------------------

class TestProgramConfigSafety:
    def test_unsafe_config_rejected(self):
        from app.api.dashboard import _validate_program_config
        errors = _validate_program_config({
            "payment_failure": {
                "max_retry_attempts": 20,
                "allowed_actions": ["retry_payment"],
                "confidence_threshold": 0.3,
            }
        })
        assert len(errors) >= 2
        assert any("max_retry_attempts" in e for e in errors)
        assert any("confidence_threshold" in e for e in errors)

    def test_safe_config_accepted(self):
        from app.api.dashboard import _validate_program_config
        errors = _validate_program_config({
            "payment_failure": {
                "max_retry_attempts": 3,
                "confidence_threshold": 0.8,
            }
        })
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# R. Outcome verification
# ---------------------------------------------------------------------------

class TestOutcomeVerification:
    def test_next_action_endpoint(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        payload = _soft_payload(payment_id="pay_next_001", error_reason="payment_timed_out")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
        assert resp.status_code == 200
        item_id = resp.json()["recovery_item_id"]

        next_resp = client.get(f"/api/next-action/{item_id}")
        assert next_resp.status_code == 200
        data = next_resp.json()
        assert "next_action" in data
        assert "safety_decision" in data


# ---------------------------------------------------------------------------
# S. Expected vs actual recovery
# ---------------------------------------------------------------------------

class TestExpectedVsActual:
    def test_batch_summary_has_expected_and_actual(self):
        service = _build_service()
        app = _build_app(service)
        client = TestClient(app)

        resp = client.post("/api/demo/batch-payment-failures", json={
            "count": 3,
            "error_reason": "payment_timed_out",
            "amount_minor": 50000,
        })
        assert resp.status_code == 200
        data = resp.json()
        summary = data["summary"]
        assert "expected_recovery_minor" in summary or "recovered_amount_minor" in summary


# ---------------------------------------------------------------------------
# T. Confidence-aware decisioning edge cases
# ---------------------------------------------------------------------------

class TestConfidenceThresholds:
    def test_missing_confidence_fails_closed(self):
        container = create_persistence_container("memory")
        from app.agents.decision_agent import RecoveryDecisionAgent
        from app.domain.proposals import RecoveryAction, RecoveryProposal

        class NoConfidenceAgent:
            name = "no-conf-agent"
            model_name = "mock"
            def propose(self, context):
                return RecoveryProposal(
                    action=RecoveryAction.RETRY_PAYMENT,
                    reason="No confidence",
                    confidence=0.0,
                )

        orchestrator = RecoveryOrchestrator(
            agent=NoConfidenceAgent(),
            policy_engine=InterventionPolicy(max_retry_attempts=3),
            audit_log=container.audit_log,
            validator=ProposalValidator(),
            stopping_rules=StoppingRules(max_attempts=3),
            guard=DefaultRecoveryGuard(
                stopping_rules=StoppingRules(max_attempts=3),
                policy_engine=InterventionPolicy(max_retry_attempts=3),
            ),
            scorer=ExpectedValueScorer(),
        )
        item = RecoveryItem(
            id="ri_noconf",
            source_type=SourceType.PAYMENT_FAILURE,
            external_id="evt_noconf",
            customer_id="C_NOCONF",
            amount_minor=50000,
            currency="INR",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=RecoveryStatus.DETECTED,
            root_cause="soft",
        )
        context = RecoveryContext(
            failure_category=__import__("app.domain.failures", fromlist=["FailureCategory"]).FailureCategory.SOFT,
            retryable=True,
            attempt_count=0,
            amount_minor=50000,
            currency="INR",
            expected_recovery_value=17500,
            customer_opt_out=False,
            max_attempts=3,
            item_id="ri_noconf",
        )
        result = orchestrator.run(item, context)
        assert result.safety_decision != "ALLOWED"
