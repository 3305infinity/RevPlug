from __future__ import annotations

from datetime import datetime
from typing import Any

from app.audit.models import AuditLog, AuditEvent
from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryStatus
from app.domain.transitions import (
    DefaultStateMachine,
    InvalidTransitionError,
    RecoveryStateMachine,
    TransitionResult,
)
from app.idempotency.store import IdempotencyStore
from app.interventions.simulated import Intervention, InterventionResult
from app.ledger.attempts import AttemptLedger, AttemptRecord
from app.policies.engine import PolicyEngine, PolicyDecision
from app.policies.guard import DefaultRecoveryGuard, RecoveryGuard
from app.policies.retry import RetryPolicy
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer, ScoreResult


class RecoveryPipeline:
    """Coordinates the deterministic recovery stages.

    Pipeline stages when optional dependencies are provided:
        event -> idempotency check -> normalize/classify -> state transition ->
        score -> policy decision -> retry policy -> intervene -> attempt ledger ->
        state transition -> audit

    Without optional dependencies, behaves as the original simple pipeline.
    """

    def __init__(
        self,
        *,
        scorer: RecoveryScorer,
        policy_engine: PolicyEngine,
        intervention: Intervention,
        audit_log: AuditLog,
        idempotency_store: IdempotencyStore | None = None,
        state_machine: RecoveryStateMachine | None = None,
        retry_policy: RetryPolicy | None = None,
        attempt_ledger: AttemptLedger | None = None,
        stopping_rules: StoppingRules | None = None,
        guard: RecoveryGuard | None = None,
    ) -> None:
        self._scorer = scorer
        self._policy_engine = policy_engine
        self._intervention = intervention
        self._audit_log = audit_log
        self._idempotency_store = idempotency_store
        self._state_machine = state_machine or DefaultStateMachine()
        self._retry_policy = retry_policy
        self._attempt_ledger = attempt_ledger
        self._stopping_rules = stopping_rules
        if guard is not None:
            self._guard = guard
        elif stopping_rules is not None:
            self._guard = DefaultRecoveryGuard(
                stopping_rules=stopping_rules,
                policy_engine=policy_engine,
            )
        else:
            self._guard = None

    def process(self, item: RecoveryItem, context: dict[str, object] | None = None) -> tuple[RecoveryItem, list[AuditEvent]]:
        """Run the recovery pipeline on a single item.

        Returns the updated item and all audit events produced during this run.
        """
        context = context or {}
        events: list[AuditEvent] = []
        current = item

        # Stage 1: diagnose (deterministic action selection before scoring)
        proposed_action = self._diagnose(current)
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="diagnose",
            reason=f"Proposed action: {proposed_action}",
            metadata={"proposed_action": proposed_action},
        ))

        # Stage 2: deterministic expected-value scoring (LLM never determines the score)
        score_result = self._score(
            item=current,
            failure_category=current.root_cause or "unknown",
            proposed_action=proposed_action,
            attempt_number=int(current.metadata.get("attempt_count", 0)),
        )
        current = self._apply_score(current, score_result)
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="recovery_scored",
            reason="Expected value calculated deterministically",
            metadata={
                "amount_at_risk": score_result.amount_at_risk,
                "recovery_probability": score_result.recovery_probability,
                "intervention_cost": score_result.intervention_cost,
                "expected_recovery_value": score_result.expected_recovery_value,
                "priority": score_result.priority,
                "score_version": score_result.score_version,
                "scoring_reason": score_result.scoring_reason,
            },
        ))

        # Stage 3: guard decision (stopping rules + policy engine)
        if self._guard is not None:
            guard_decision = self._guard.evaluate(
                current,
                proposed_action,
                container=None,
            )
            events.append(self._audit_log.log(
                recovery_item_id=current.id,
                actor="rule",
                action="guard_evaluate",
                reason=guard_decision.reason,
                metadata={
                    "proposed_action": proposed_action,
                    "allowed": guard_decision.allowed,
                    "decision_type": guard_decision.decision_type,
                    "reason_code": guard_decision.reason_code,
                    "rule": guard_decision.rule,
                    "next_state": guard_decision.next_state.value,
                },
            ))

            if not guard_decision.allowed:
                final_status = guard_decision.next_state
                if final_status != current.status:
                    tr = self._state_machine.transition(current, final_status)
                    if tr.applied:
                        current = tr.item
                        current = current.__class__(
                            id=current.id,
                            source_type=current.source_type,
                            external_id=current.external_id,
                            customer_id=current.customer_id,
                            amount_minor=current.amount_minor,
                            currency=current.currency,
                            created_at=current.created_at,
                            due_at=current.due_at,
                            status=final_status,
                            root_cause=current.root_cause,
                            recovery_probability=current.recovery_probability,
                            expected_recovery_value=current.expected_recovery_value,
                            intervention_cost=current.intervention_cost,
                            failure_category=current.failure_category,
                            provider=current.provider,
                            provider_event_id=current.provider_event_id,
                            actual_recovery_value=current.actual_recovery_value,
                            recovery_status=current.recovery_status,
                            score_version=current.score_version,
                            scoring_reason=current.scoring_reason,
                            priority=current.priority,
                            stopped_reason=guard_decision.reason_code,
                            stopped_rule=guard_decision.rule,
                            metadata=current.metadata,
                        )
                events.append(self._audit_log.log(
                    recovery_item_id=current.id,
                    actor="system",
                    action="recovery_stopped",
                    reason=guard_decision.reason,
                    metadata={
                        "reason_code": guard_decision.reason_code,
                        "rule": guard_decision.rule,
                        "next_state": final_status.value,
                    },
                ))
                return current, events
        else:
            # Fallback to policy-only evaluation if no guard is configured
            decision = self._policy_engine.evaluate(current, proposed_action)
            events.append(self._audit_log.log(
                recovery_item_id=current.id,
                actor="rule",
                action="policy_evaluate",
                reason=decision.reason,
                metadata={
                    "proposed_action": proposed_action,
                    "allowed": decision.allowed,
                    "requires_human_approval": decision.requires_human_approval,
                    "policy_rule": decision.policy_rule,
                    "reason_code": decision.reason_code,
                },
            ))

            if not decision.allowed:
                final_status = RecoveryStatus.STOPPED
                tr = self._state_machine.transition(current, final_status)
                if tr.applied:
                    current = tr.item
                    current = current.__class__(
                        id=current.id,
                        source_type=current.source_type,
                        external_id=current.external_id,
                        customer_id=current.customer_id,
                        amount_minor=current.amount_minor,
                        currency=current.currency,
                        created_at=current.created_at,
                        due_at=current.due_at,
                        status=final_status,
                        root_cause=current.root_cause,
                        recovery_probability=current.recovery_probability,
                        expected_recovery_value=current.expected_recovery_value,
                        intervention_cost=current.intervention_cost,
                        failure_category=current.failure_category,
                        provider=current.provider,
                        provider_event_id=current.provider_event_id,
                        actual_recovery_value=current.actual_recovery_value,
                        recovery_status=current.recovery_status,
                        score_version=current.score_version,
                        scoring_reason=current.scoring_reason,
                        priority=current.priority,
                        stopped_reason=decision.reason_code,
                        stopped_rule=decision.policy_rule,
                        metadata=current.metadata,
                    )
                events.append(self._audit_log.log(
                    recovery_item_id=current.id,
                    actor="system",
                    action="recovery_stopped",
                    reason=decision.reason,
                    metadata={
                        "reason_code": decision.reason_code,
                        "rule": decision.policy_rule,
                    },
                ))
                return current, events

            if decision.requires_human_approval:
                events.append(self._audit_log.log(
                    recovery_item_id=current.id,
                    actor="system",
                    action="intervention_pending",
                    reason="Human approval required before execution",
                    metadata={"action": proposed_action, "policy_rule": decision.policy_rule},
                ))
                return current, events

        # Stage 4: execute approved intervention (both guard and fallback paths)
        attempt_number = int(current.metadata.get("attempt_count", 0)) + 1
        result = self._intervention.execute(current, {"action": proposed_action, **context})
        current = self._apply_outcome(current, result)
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="intervention_execute",
            reason=result.message,
            metadata={"action": proposed_action, "success": result.success, "side_effects": result.side_effects},
        ))

        # Stage 5: attempt ledger
        if self._attempt_ledger is not None:
            attempt = AttemptRecord(
                recovery_item_id=current.id,
                attempt_number=attempt_number,
                action=proposed_action,
                executed_at=datetime.utcnow(),
                outcome="success" if result.success else "failed",
                metadata=result.side_effects or {},
            )
            self._attempt_ledger.record(attempt)
            events.append(self._audit_log.log(
                recovery_item_id=current.id,
                actor="system",
                action="attempt_recorded",
                reason=f"Attempt {attempt_number} recorded",
                metadata={"attempt_number": attempt_number, "action": proposed_action},
            ))

        # Stage 6: final audit
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="pipeline_complete",
            reason="Recovery pipeline stage complete",
            metadata={"final_status": current.status.value},
        ))

        return current, events

    def _score(
        self,
        item: RecoveryItem,
        failure_category: str,
        proposed_action: str,
        attempt_number: int = 0,
    ) -> ScoreResult:
        """Deterministically score a recovery item."""
        return self._scorer.score(
            amount_minor=item.amount_minor,
            failure_category=failure_category,
            proposed_action=proposed_action,
            attempt_number=attempt_number + 1,
            context={
                "customer_id": item.customer_id,
                "currency": item.currency,
                "source_type": item.source_type.value,
            },
        )

    def _apply_score(self, item: RecoveryItem, score_result: ScoreResult) -> RecoveryItem:
        """Apply scoring results to a RecoveryItem."""
        return item.__class__(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=RecoveryStatus.QUEUED,
            root_cause=item.root_cause,
            recovery_probability=score_result.recovery_probability,
            expected_recovery_value=score_result.expected_recovery_value,
            intervention_cost=score_result.intervention_cost,
            failure_category=item.failure_category,
            provider=item.provider,
            provider_event_id=item.provider_event_id,
            actual_recovery_value=item.actual_recovery_value,
            recovery_status=item.recovery_status,
            score_version=score_result.score_version,
            scoring_reason=score_result.scoring_reason,
            priority=score_result.priority,
            metadata=item.metadata,
        )

    def _diagnose(self, item: RecoveryItem) -> str:
        if item.root_cause in {"hard_decline", "fraud", "authentication_required", "security_or_fraud"}:
            return "escalate_human"
        if item.recovery_probability is not None and item.recovery_probability >= 0.5:
            return "retry_payment"
        if item.source_type.value == "checkout_abandonment":
            return "send_payment_link"
        if item.source_type.value == "receivable":
            return "send_reminder"
        return "escalate_human"

    def _apply_outcome(self, item: RecoveryItem, result: InterventionResult) -> RecoveryItem:
        status = RecoveryStatus.INTERVENTION_EXECUTED if result.success else RecoveryStatus.FAILED
        return item.__class__(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=status,
            root_cause=item.root_cause,
            recovery_probability=item.recovery_probability,
            expected_recovery_value=item.expected_recovery_value,
            metadata={**item.metadata, "last_intervention_message": result.message},
        )
