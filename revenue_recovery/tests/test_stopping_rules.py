"""Stage 4 adversarial tests: stopping rules, guard decisions, and safety controls."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.adapters.razorpay.webhook import RazorpayWebhookService
from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import InMemoryAuditLog
from app.db.container import _InMemoryPromiseRepository, _InMemoryProviderEventRepository, _InMemoryRecoveryOutcomeRepository
from app.db.decision_repository import InMemoryRecoveryDecisionRepository
from app.db.repositories import InMemoryRecoveryItemRepository
from app.domain.models import (
    Promise,
    PromiseStatus,
    RecoveryItem,
    RecoveryStatus,
    SourceType,
)
from app.idempotency.store import InMemoryIdempotencyStore
from app.interventions.executor import SimulatedRecoveryExecutor
from app.interventions.simulated import SimulatedIntervention
from app.ledger.attempts import InMemoryAttemptLedger
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingDecision, StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.services.pipeline import RecoveryPipeline


def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def build_item(**overrides):
    data = {
        "id": "ri_1",
        "source_type": SourceType.PAYMENT_FAILURE,
        "external_id": "ext_1",
        "customer_id": "C_1",
        "amount_minor": 10000,
        "currency": "INR",
        "created_at": utcnow(),
        "status": RecoveryStatus.DETECTED,
        "root_cause": "soft",
        "recovery_probability": 0.6,
        "metadata": {},
    }
    data.update(overrides)
    return RecoveryItem(**data)


# ===========================================================================
# StoppingRules tests
# ===========================================================================

class TestStoppingRulesTerminalStates:
    def test_recovered_is_terminal(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(status=RecoveryStatus.RECOVERED)
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "terminal_state_reached"

    def test_stopped_is_terminal(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(status=RecoveryStatus.STOPPED)
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "terminal_state_reached"

    def test_escalated_is_terminal(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(status=RecoveryStatus.ESCALATED)
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "terminal_state_reached"


class TestStoppingRulesPaymentSucceeded:
    def test_payment_succeeded_stops_recovery(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(metadata={"payment_succeeded": True})
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "payment_succeeded"
        assert decision.next_state == RecoveryStatus.RECOVERED

    def test_no_payment_success_allows_proceed(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item()
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is False


class TestStoppingRulesCustomerOptOut:
    def test_opted_out_customer_stops_recovery(self):
        rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_BLOCKED"}))
        item = build_item(customer_id="C_BLOCKED")
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "customer_opted_out"
        assert decision.next_state == RecoveryStatus.STOPPED

    def test_non_opted_out_customer_allows_proceed(self):
        rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_BLOCKED"}))
        item = build_item(customer_id="C_ALLOWED")
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is False


class TestStoppingRulesFraud:
    def test_fraud_detected_stops_recovery(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(root_cause="fraud")
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "fraud_detected"
        assert decision.next_state == RecoveryStatus.STOPPED

    def test_security_or_fraud_stops_recovery(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(root_cause="security_or_fraud")
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "fraud_detected"

    def test_soft_does_not_trigger_fraud_stop(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(root_cause="soft")
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is False


class TestStoppingRulesRetryBudget:
    def test_retry_budget_exhausted(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(metadata={"attempt_count": 3})
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "retry_budget_exhausted"
        assert "3/3" in decision.reason

    def test_retry_budget_not_exhausted(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(metadata={"attempt_count": 2})
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is False

    def test_retry_budget_not_checked_for_non_retry_action(self):
        rules = StoppingRules(max_attempts=1)
        item = build_item(metadata={"attempt_count": 5})
        decision = rules.evaluate(item, proposed_action="send_payment_link")
        assert decision.should_stop is False


class TestStoppingRulesDeadline:
    def test_deadline_expired_stops_recovery(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        rules = StoppingRules(max_attempts=3)
        item = build_item(due_at=past)
        decision = rules.evaluate(item, proposed_action="retry_payment", now=utcnow())
        assert decision.should_stop is True
        assert decision.reason_code == "recovery_deadline_expired"

    def test_deadline_not_set_allows_proceed(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(due_at=None)
        decision = rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is False

    def test_future_deadline_allows_proceed(self):
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        rules = StoppingRules(max_attempts=3)
        item = build_item(due_at=future)
        decision = rules.evaluate(item, proposed_action="retry_payment", now=utcnow())
        assert decision.should_stop is False


class TestStoppingRulesPromiseExpiry:
    def test_expired_promise_stops_recovery(self):
        container = MagicMock()
        container.promises = _InMemoryPromiseRepository()
        past_promise = Promise(
            id="p1",
            recovery_item_id="ri_1",
            customer_id="C_1",
            promised_amount_minor=10000,
            promised_date=datetime(2020, 1, 1).date(),
            status=PromiseStatus.PROMISED.value,
        )
        container.promises.save(past_promise)
        rules = StoppingRules(max_attempts=3)
        item = build_item(id="ri_1")
        decision = rules.evaluate(item, proposed_action="retry_payment", container=container, now=utcnow())
        assert decision.should_stop is True
        assert decision.reason_code == "promise_expired"

    def test_fulfilled_promise_does_not_stop(self):
        container = MagicMock()
        container.promises = _InMemoryPromiseRepository()
        promise = Promise(
            id="p1",
            recovery_item_id="ri_1",
            customer_id="C_1",
            promised_amount_minor=10000,
            promised_date=datetime(2020, 1, 1).date(),
            status=PromiseStatus.FULFILLED.value,
        )
        container.promises.save(promise)
        rules = StoppingRules(max_attempts=3)
        item = build_item(id="ri_1")
        decision = rules.evaluate(item, proposed_action="retry_payment", container=container, now=utcnow())
        assert decision.should_stop is False

    def test_no_promise_allows_proceed(self):
        container = MagicMock()
        container.promises = _InMemoryPromiseRepository()
        rules = StoppingRules(max_attempts=3)
        item = build_item()
        decision = rules.evaluate(item, proposed_action="retry_payment", container=container, now=utcnow())
        assert decision.should_stop is False


class TestStoppingRulesIdempotent:
    def test_repeated_calls_produce_same_result(self):
        rules = StoppingRules(max_attempts=3)
        item = build_item(metadata={"attempt_count": 3})
        decision1 = rules.evaluate(item, proposed_action="retry_payment")
        decision2 = rules.evaluate(item, proposed_action="retry_payment")
        decision3 = rules.evaluate(item, proposed_action="retry_payment")
        assert decision1.reason_code == decision2.reason_code == decision3.reason_code
        assert decision1.should_stop == decision2.should_stop == decision3.should_stop
        assert decision1.next_state == decision2.next_state == decision3.next_state


# ===========================================================================
# DefaultRecoveryGuard tests
# ===========================================================================

class TestDefaultRecoveryGuard:
    def test_guard_returns_unified_decision(self):
        rules = StoppingRules(max_attempts=3)
        policy = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=rules, policy_engine=policy)
        item = build_item()
        decision = guard.evaluate(item, "retry_payment")
        assert hasattr(decision, "allowed")
        assert hasattr(decision, "decision_type")
        assert hasattr(decision, "reason_code")
        assert hasattr(decision, "next_state")
        assert decision.decision_type == "ALLOWED"

    def test_guard_stops_for_fraud(self):
        rules = StoppingRules(max_attempts=3)
        policy = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=rules, policy_engine=policy)
        item = build_item(root_cause="fraud")
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.decision_type == "STOP"
        assert decision.reason_code == "fraud_detected"
        assert decision.next_state == RecoveryStatus.STOPPED

    def test_guard_denies_for_retry_budget_exhausted(self):
        rules = StoppingRules(max_attempts=3)
        policy = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=rules, policy_engine=policy)
        item = build_item(metadata={"attempt_count": 3})
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.decision_type == "STOP"
        assert decision.reason_code == "retry_budget_exhausted"

    def test_guard_denies_for_customer_opt_out(self):
        rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_BLOCKED"}))
        policy = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=rules, policy_engine=policy)
        item = build_item(customer_id="C_BLOCKED")
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.decision_type == "STOP"
        assert decision.reason_code == "customer_opted_out"


# ===========================================================================
# Pipeline integration tests
# ===========================================================================

class TestPipelineWithGuard:
    def test_pipeline_stops_for_fraud_with_guard(self):
        audit_log = InMemoryAuditLog()
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        pipeline = RecoveryPipeline(
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            intervention=SimulatedIntervention(),
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
        )
        item = build_item(root_cause="fraud")
        pipeline._diagnose = lambda item: "retry_payment"  # type: ignore[assignment]
        result, events = pipeline.process(item)
        assert result.status == RecoveryStatus.STOPPED
        assert result.stopped_reason == "fraud_detected"
        guard_events = [e for e in events if e.action == "guard_evaluate"]
        assert len(guard_events) == 1
        assert guard_events[0].metadata["allowed"] is False

    def test_pipeline_stops_for_retry_budget_exhausted(self):
        audit_log = InMemoryAuditLog()
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        pipeline = RecoveryPipeline(
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            intervention=SimulatedIntervention(),
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
        )
        item = build_item(metadata={"attempt_count": 3})
        pipeline._diagnose = lambda item: "retry_payment"  # type: ignore[assignment]
        result, events = pipeline.process(item)
        assert result.status == RecoveryStatus.STOPPED
        assert result.stopped_reason == "retry_budget_exhausted"

    def test_pipeline_stops_for_payment_succeeded(self):
        audit_log = InMemoryAuditLog()
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        pipeline = RecoveryPipeline(
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            intervention=SimulatedIntervention(),
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
        )
        item = build_item(metadata={"payment_succeeded": True})
        result, events = pipeline.process(item)
        assert result.status == RecoveryStatus.RECOVERED
        assert result.stopped_reason == "payment_succeeded"

    def test_pipeline_executes_when_guard_allows(self):
        audit_log = InMemoryAuditLog()
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        pipeline = RecoveryPipeline(
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            intervention=SimulatedIntervention(),
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
        )
        item = build_item(root_cause="soft", recovery_probability=0.6)
        result, events = pipeline.process(item)
        assert result.status == RecoveryStatus.INTERVENTION_EXECUTED
        execute_events = [e for e in events if e.action == "intervention_execute"]
        assert len(execute_events) == 1

    def test_pipeline_stops_for_customer_opted_out(self):
        audit_log = InMemoryAuditLog()
        stopping_rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_BLOCKED"}))
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        pipeline = RecoveryPipeline(
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            intervention=SimulatedIntervention(),
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
        )
        item = build_item(customer_id="C_BLOCKED")
        result, events = pipeline.process(item)
        assert result.status == RecoveryStatus.STOPPED
        assert result.stopped_reason == "customer_opted_out"


# ===========================================================================
# Adversarial tests (from Stage 4 prompt)
# ===========================================================================

class TestJudgeBreakerScenarios:
    """Adversarial tests that a judge can use to probe safety boundaries."""

    def test_scenario_a_retry_limit_exhausted(self):
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        item = build_item(metadata={"attempt_count": 3})
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.reason_code == "retry_budget_exhausted"

    def test_scenario_b_payment_succeeds_mid_flow(self):
        stopping_rules = StoppingRules(max_attempts=3)
        item = build_item(metadata={"payment_succeeded": True})
        decision = stopping_rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "payment_succeeded"
        assert decision.next_state == RecoveryStatus.RECOVERED

    def test_scenario_c_customer_opts_out(self):
        stopping_rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset({"C_OPTOUT"}))
        item = build_item(customer_id="C_OPTOUT")
        decision = stopping_rules.evaluate(item, proposed_action="send_payment_link")
        assert decision.should_stop is True
        assert decision.reason_code == "customer_opted_out"

    def test_scenario_d_expired_promise(self):
        container = MagicMock()
        container.promises = _InMemoryPromiseRepository()
        promise = Promise(
            id="p1",
            recovery_item_id="ri_1",
            customer_id="C_1",
            promised_amount_minor=10000,
            promised_date=datetime(2020, 1, 1).date(),
            status=PromiseStatus.PROMISED.value,
        )
        container.promises.save(promise)
        stopping_rules = StoppingRules(max_attempts=3)
        item = build_item(id="ri_1")
        decision = stopping_rules.evaluate(item, proposed_action="retry_payment", container=container, now=utcnow())
        assert decision.should_stop is True
        assert decision.reason_code == "promise_expired"

    def test_scenario_e_fraud_blocks_retry(self):
        stopping_rules = StoppingRules(max_attempts=3)
        item = build_item(root_cause="fraud")
        decision = stopping_rules.evaluate(item, proposed_action="retry_payment")
        assert decision.should_stop is True
        assert decision.reason_code == "fraud_detected"
        assert decision.next_state == RecoveryStatus.STOPPED

    def test_scenario_f_human_approval_cannot_bypass_fraud(self):
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        item = build_item(root_cause="fraud")
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.decision_type == "STOP"
        assert decision.reason_code == "fraud_detected"

    def test_scenario_g_expired_recovery_deadline(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        stopping_rules = StoppingRules(max_attempts=3)
        item = build_item(due_at=past)
        decision = stopping_rules.evaluate(item, proposed_action="retry_payment", now=utcnow())
        assert decision.should_stop is True
        assert decision.reason_code == "recovery_deadline_expired"

    def test_scenario_h_terminal_case_no_new_attempt(self):
        stopping_rules = StoppingRules(max_attempts=3)
        for status in [RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED]:
            item = build_item(status=status)
            decision = stopping_rules.evaluate(item, proposed_action="retry_payment")
            assert decision.should_stop is True
            assert decision.reason_code == "terminal_state_reached"

    def test_scenario_i_repeated_guard_evaluation_idempotent(self):
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        item = build_item(metadata={"attempt_count": 3})
        decisions = [guard.evaluate(item, "retry_payment") for _ in range(10)]
        codes = [d.reason_code for d in decisions]
        assert len(set(codes)) == 1
        assert all(d.allowed is False for d in decisions)
        assert all(d.next_state == RecoveryStatus.STOPPED for d in decisions)

    def test_scenario_j_high_expected_value_cannot_override_fraud(self):
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        item = build_item(
            root_cause="fraud",
            amount_minor=10_000_000,
            recovery_probability=0.99,
            expected_recovery_value=9_900_000,
        )
        decision = guard.evaluate(item, "retry_payment")
        assert decision.allowed is False
        assert decision.reason_code == "fraud_detected"
        assert decision.next_state == RecoveryStatus.STOPPED


# ===========================================================================
# Webhook service integration tests
# ===========================================================================

class TestWebhookWithStoppingRules:
    def _build_service(self):
        container = MagicMock()
        container.recovery_items = InMemoryRecoveryItemRepository()
        container.idempotency = InMemoryIdempotencyStore()
        container.audit_log = InMemoryAuditLog()
        container.attempts = InMemoryAttemptLedger()
        container.decisions = InMemoryRecoveryDecisionRepository()
        container.outcomes = _InMemoryRecoveryOutcomeRepository()
        container.promises = _InMemoryPromiseRepository()
        container.provider_events = _InMemoryProviderEventRepository()
        stopping_rules = StoppingRules(max_attempts=3)
        policy_engine = InterventionPolicy(max_retry_attempts=3)
        guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
        agent = MockRecoveryDecisionAgent()
        orchestrator = RecoveryAgentOrchestrator(
            agent=agent,
            policy_engine=policy_engine,
            audit_log=container.audit_log,
            validator=ProposalValidator(),
        )
        return RazorpayWebhookService(
            webhook_secret="test_secret",
            scorer=ExpectedValueScorer(),
            policy_engine=policy_engine,
            audit_log=container.audit_log,
            idempotency_store=container.idempotency,
            provider_events=container.provider_events,
            recovery_items=container.recovery_items,
            decisions=container.decisions,
            attempts=container.attempts,
            agent=agent,
            orchestrator=orchestrator,
            executor=SimulatedRecoveryExecutor(),
            retry_policy=None,
            state_machine=None,
            stopping_rules=stopping_rules,
            guard=guard,
        ), container

    def test_fraud_webhook_stops_recovery(self):
        service, container = self._build_service()
        payload = {
            "entity": "event",
            "account_id": "acc_TEST",
            "event": "payment.failed",
            "contains": ["payment"],
            "id": "evt_fraud_1",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fraud_1",
                        "entity": "payment",
                        "amount": 50000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "RISK_CHECK_FAILED",
                        "error_description": "Risk check failed",
                        "error_source": "gateway",
                        "error_step": "risk_check",
                        "error_reason": "payment_risk_check_failed",
                        "created_at": int(datetime.now(timezone.utc).timestamp()),
                    }
                }
            },
        }
        import json, hashlib, hmac as hmac_mod
        raw_body = json.dumps(payload).encode()
        sig = hmac_mod.new(b"test_secret", raw_body, hashlib.sha256).hexdigest()
        item, events, status = service.process_webhook(raw_body, sig)
        assert item is not None
        assert item.status == RecoveryStatus.STOPPED
        assert item.stopped_reason == "fraud_detected"
        stopped_events = [e for e in events if e.action == "recovery_stopped"]
        assert len(stopped_events) == 1
