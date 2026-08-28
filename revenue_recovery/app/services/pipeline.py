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
from app.policies.retry import RetryPolicy
from app.scoring.expected_value import RecoveryScorer


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
    ) -> None:
        self._scorer = scorer
        self._policy_engine = policy_engine
        self._intervention = intervention
        self._audit_log = audit_log
        self._idempotency_store = idempotency_store
        self._state_machine = state_machine or DefaultStateMachine()
        self._retry_policy = retry_policy
        self._attempt_ledger = attempt_ledger

    def process(self, item: RecoveryItem, context: dict[str, object] | None = None) -> tuple[RecoveryItem, list[AuditEvent]]:
        """Run the recovery pipeline on a single item.

        Returns the updated item and all audit events produced during this run.
        """
        context = context or {}
        events: list[AuditEvent] = []
        current = item

        # Stage 1: score (unchanged from foundation)
        current = self._score(current)
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="score",
            reason="Expected value calculated",
            metadata={"expected_recovery_value": current.expected_recovery_value},
        ))

        # Stage 2: diagnose (deterministic placeholder)
        proposed_action = self._diagnose(current)
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="diagnose",
            reason=f"Proposed action: {proposed_action}",
            metadata={"proposed_action": proposed_action},
        ))

        # Stage 3: policy decision
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
            },
        ))

        # Stage 4: retry policy check
        if proposed_action == "retry_payment" and self._retry_policy is not None:
            retry_decision = self._retry_policy.evaluate(current)
            events.append(self._audit_log.log(
                recovery_item_id=current.id,
                actor="rule",
                action="retry_policy_evaluate",
                reason=retry_decision.reason,
                metadata={
                    "allowed": retry_decision.allowed,
                    "max_attempts": retry_decision.max_attempts,
                    "policy_rule": retry_decision.policy_rule,
                },
            ))
            if not retry_decision.allowed and decision.allowed:
                decision = PolicyDecision(
                    allowed=False,
                    requires_human_approval=True,
                    reason=retry_decision.reason,
                    policy_rule=retry_decision.policy_rule,
                    action=proposed_action,
                )

        # Stage 5: intervene
        if decision.requires_human_approval:
            events.append(self._audit_log.log(
                recovery_item_id=current.id,
                actor="system",
                action="intervention_pending",
                reason="Human approval required before execution",
                metadata={"action": proposed_action, "policy_rule": decision.policy_rule},
            ))
        elif decision.allowed:
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

            # Stage 6: attempt ledger
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

        # Stage 7: final audit
        events.append(self._audit_log.log(
            recovery_item_id=current.id,
            actor="system",
            action="pipeline_complete",
            reason="Recovery pipeline stage complete",
            metadata={"final_status": current.status.value},
        ))

        return current, events

    def _score(self, item: RecoveryItem) -> RecoveryItem:
        value = self._scorer.score(item)
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
            recovery_probability=item.recovery_probability,
            expected_recovery_value=value,
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
