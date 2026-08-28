from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.adapters.razorpay.events import RazorpayPaymentFailure, parse_razorpay_event
from app.adapters.razorpay.signatures import RazorpaySignatureError, verify_razorpay_signature
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import AuditEvent, AuditLog
from app.db.decision_repository import RecoveryDecisionRepository
from app.db.repositories import RecoveryItemRepository
from app.domain.context import RecoveryContext
from app.domain.escalation import Escalation, EscalationReason
from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.transitions import DefaultStateMachine, RecoveryStateMachine
from app.idempotency.store import IdempotencyStore
from app.interventions.executor import ExecutionResult, RecoveryExecutor, SimulatedRecoveryExecutor
from app.ledger.attempts import AttemptLedger, AttemptRecord
from app.policies.engine import PolicyEngine, PolicyDecision
from app.policies.retry import DefaultRetryPolicy, RetryPolicy
from app.scoring.expected_value import RecoveryScorer


class RazorpayWebhookService:
    """Processes Razorpay webhooks into a complete safe recovery lifecycle.

    Flow:
        verify signature → parse event → idempotency check → classify failure
        → create RecoveryItem → score → build context → agent proposes
        → validator validates → policy decides → IF allowed: execute
        → attempt ledger → retry decision → state transition → audit
        → IF denied: escalate → audit

    The agent NEVER executes directly. The PolicyEngine is the final gate.
    """

    def __init__(
        self,
        *,
        webhook_secret: str,
        scorer: RecoveryScorer,
        policy_engine: PolicyEngine,
        audit_log: AuditLog,
        idempotency_store: IdempotencyStore,
        recovery_items: RecoveryItemRepository | None = None,
        decisions: RecoveryDecisionRepository | None = None,
        attempts: AttemptLedger | None = None,
        agent: RecoveryDecisionAgent | None = None,
        orchestrator: RecoveryAgentOrchestrator | None = None,
        executor: RecoveryExecutor | None = None,
        retry_policy: RetryPolicy | None = None,
        state_machine: RecoveryStateMachine | None = None,
        default_customer_id: str = "razorpay_customer",
    ) -> None:
        self._webhook_secret = webhook_secret
        self._scorer = scorer
        self._policy_engine = policy_engine
        self._audit_log = audit_log
        self._idempotency_store = idempotency_store
        self._recovery_items = recovery_items
        self._decisions = decisions
        self._attempts = attempts
        self._default_customer_id = default_customer_id
        self._agent = agent or MockRecoveryDecisionAgent()
        self._orchestrator = orchestrator
        self._executor = executor or SimulatedRecoveryExecutor()
        self._retry_policy = retry_policy or DefaultRetryPolicy(max_attempts=3)
        self._state_machine = state_machine or DefaultStateMachine()

    def process_webhook(
        self,
        raw_body: bytes,
        signature_header: str | None,
    ) -> tuple[RecoveryItem | None, list[AuditEvent], str]:
        """Process a Razorpay webhook through the complete recovery lifecycle."""
        events: list[AuditEvent] = []

        # Stage 1: verify signature (raw body, before any parsing)
        try:
            verify_razorpay_signature(raw_body, signature_header, self._webhook_secret)
        except RazorpaySignatureError as exc:
            audit = self._audit_log.log(
                recovery_item_id=None,
                actor="system",
                action="signature_rejected",
                reason=str(exc),
                metadata={"error": str(exc)},
            )
            events.append(audit)
            raise

        events.append(self._audit_log.log(
            recovery_item_id=None,
            actor="system",
            action="signature_verified",
            reason="Webhook signature is valid",
            metadata={},
        ))

        # Stage 2: parse event
        try:
            razorpay_failure = parse_razorpay_event(raw_body)
        except Exception as exc:
            audit = self._audit_log.log(
                recovery_item_id=None,
                actor="system",
                action="parse_failed",
                reason=str(exc),
                metadata={"error": str(exc)},
            )
            events.append(audit)
            raise

        events.append(self._audit_log.log(
            recovery_item_id=None,
            actor="system",
            action="event_parsed",
            reason="Razorpay event parsed",
            metadata={
                "razorpay_event_id": razorpay_failure.razorpay_event_id,
                "razorpay_payment_id": razorpay_failure.razorpay_payment_id,
            },
        ))

        # Stage 3: idempotency check (before any expensive work including agent)
        event_key = razorpay_failure.razorpay_event_id
        if self._idempotency_store.has_processed(event_key):
            events.append(self._audit_log.log(
                recovery_item_id=None,
                actor="system",
                action="duplicate_event_ignored",
                reason="Event already processed",
                metadata={"razorpay_event_id": event_key},
            ))
            return None, events, "duplicate"

        self._idempotency_store.mark_processed(event_key)
        events.append(self._audit_log.log(
            recovery_item_id=None,
            actor="system",
            action="event_idempotency_recorded",
            reason="Event marked as processed",
            metadata={"razorpay_event_id": event_key},
        ))

        # Stage 4: classify failure
        from app.adapters.razorpay.classifier import RazorpayFailureClassifier
        classifier = RazorpayFailureClassifier()
        normalized = classifier.classify(razorpay_failure)

        events.append(self._audit_log.log(
            recovery_item_id=None,
            actor="rule",
            action="failure_classified",
            reason=f"Classified as {normalized.category.value}",
            metadata={
                "category": normalized.category.value,
                "code": normalized.code,
                "retryable": normalized.retryable,
            },
        ))

        # Stage 5: create RecoveryItem and transition to DIAGNOSED
        item = self._build_recovery_item(razorpay_failure, normalized)
        item = self._safe_transition(item, RecoveryStatus.DIAGNOSED)
        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="system",
            action="recovery_item_created",
            reason="RecoveryItem created from webhook",
            metadata={
                "source_type": item.source_type.value,
                "amount_minor": item.amount_minor,
                "currency": item.currency,
            },
        ))

        # Stage 6: score
        scored_item = self._score(item)
        events.append(self._audit_log.log(
            recovery_item_id=scored_item.id,
            actor="system",
            action="score",
            reason="Expected value calculated",
            metadata={"expected_recovery_value": scored_item.expected_recovery_value},
        ))

        # Persist the scored item (with expected_recovery_value)
        if self._recovery_items is not None:
            self._recovery_items.save(scored_item)

        # Stage 7: build context and call agent
        ctx = RecoveryContext.from_item_and_failure(
            scored_item,
            normalized,
            attempt_count=0,
            customer_opt_out=False,
            max_attempts=3,
        )

        orchestrator = self._orchestrator
        if orchestrator is None:
            orchestrator = RecoveryAgentOrchestrator(
                agent=self._agent,
                policy_engine=self._policy_engine,
                audit_log=self._audit_log,
                validator=ProposalValidator(),
            )

        result = orchestrator.decide(ctx)
        events.extend(result.audit_events)

        # Stage 8: execution boundary
        execution_result = None
        escalation = None
        retry_decision = None

        if result.policy_decision.allowed and not result.policy_decision.requires_human_approval:
            # Policy approved — execute
            # Transition: QUEUED → INTERVENTION_PENDING → INTERVENTION_EXECUTED
            scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_PENDING)
            scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_EXECUTED)
            execution_result = self._execute(scored_item, result.proposal.action.value, events)

            if execution_result.success:
                # Success → RECOVERED
                scored_item = self._safe_transition(scored_item, RecoveryStatus.RECOVERED)
            else:
                # Failure → check retry
                retry_decision = self._retry_policy.evaluate(
                    scored_item,
                    category=normalized.category,
                    occurred_at=datetime.now(timezone.utc),
                )
                if retry_decision.allowed:
                    # Schedule retry → back to QUEUED for next attempt
                    scored_item = self._safe_transition(scored_item, RecoveryStatus.QUEUED)
                    events.append(self._audit_log.log(
                        recovery_item_id=scored_item.id,
                        actor="system",
                        action="retry_scheduled",
                        reason=retry_decision.reason,
                        metadata={
                            "attempt_number": retry_decision.attempt_number,
                            "next_attempt_at": retry_decision.next_attempt_at.isoformat() if retry_decision.next_attempt_at else None,
                        },
                    ))
                else:
                    # Retry exhausted → ESCALATE
                    scored_item = self._safe_transition(scored_item, RecoveryStatus.ESCALATED)
                    escalation = Escalation(
                        reason=EscalationReason.RETRY_EXHAUSTED,
                        message=f"Retry exhausted for {scored_item.id}",
                        item_id=scored_item.id,
                    )
                    events.append(self._audit_log.log(
                        recovery_item_id=scored_item.id,
                        actor="system",
                        action="retry_exhausted",
                        reason=escalation.message,
                        metadata={"reason": escalation.reason.value},
                    ))
        else:
            # Policy denied → escalate
            scored_item = self._safe_transition(scored_item, RecoveryStatus.ESCALATED)
            escalation = self._create_escalation(result, scored_item)
            events.append(self._audit_log.log(
                recovery_item_id=scored_item.id,
                actor="system",
                action="execution_denied",
                reason=escalation.message,
                metadata={
                    "reason": escalation.reason.value,
                    "policy_rule": result.policy_decision.policy_rule,
                },
            ))

        # Stage 9: Persist the decision
        final_action = execution_result.action if execution_result and execution_result.success else None
        if self._decisions is not None:
            self._decisions.save_decision(
                result.proposal,
                item_id=scored_item.id,
                agent_name=self._agent.name,
                policy_allowed=result.policy_decision.allowed,
                policy_rule=result.policy_decision.policy_rule,
                policy_reason=result.policy_decision.reason,
                final_action=final_action,
            )

        # Persist final item state
        if self._recovery_items is not None:
            self._recovery_items.save(scored_item)

        # Attach results for response
        self._last_proposal = result.proposal
        self._last_decision = result.policy_decision
        self._last_execution = execution_result
        self._last_escalation = escalation
        self._last_retry = retry_decision

        return scored_item, events, "processed"

    @property
    def last_proposal(self):
        return getattr(self, "_last_proposal", None)

    @property
    def last_decision(self):
        return getattr(self, "_last_decision", None)

    @property
    def last_execution(self):
        return getattr(self, "_last_execution", None)

    @property
    def last_escalation(self):
        return getattr(self, "_last_escalation", None)

    @property
    def last_retry(self):
        return getattr(self, "_last_retry", None)

    def _execute(self, item: RecoveryItem, action: str, events: list[AuditEvent]) -> ExecutionResult:
        """Execute a policy-approved action and record the attempt."""
        attempt_number = int(item.metadata.get("attempt_count", 0)) + 1
        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="system",
            action="execution_requested",
            reason=f"Executing {action} (attempt {attempt_number})",
            metadata={"action": action, "attempt_number": attempt_number},
        ))

        result = self._executor.execute(
            item, action, attempt_number=attempt_number,
        )

        # Record attempt in ledger
        if self._attempts is not None:
            self._attempts.record(AttemptRecord(
                recovery_item_id=item.id,
                attempt_number=attempt_number,
                action=action,
                executed_at=datetime.now(timezone.utc),
                outcome="success" if result.success else "failed",
                failure_reason=result.reason if not result.success else None,
                metadata={
                    "retry_eligible": result.retry_eligible,
                    "error_code": result.error_code,
                },
            ))

        if result.success:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="execution_succeeded",
                reason=result.reason,
                metadata={"action": action, "attempt_number": attempt_number},
            ))
        else:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="execution_failed",
                reason=result.reason,
                metadata={
                    "action": action,
                    "attempt_number": attempt_number,
                    "retry_eligible": result.retry_eligible,
                },
            ))

        return result

    def _create_escalation(self, result, item: RecoveryItem) -> Escalation:
        """Create an appropriate escalation based on the denial reason."""
        category = item.root_cause
        if category == "fraud":
            reason = EscalationReason.FRAUD_DETECTED
            message = f"Fraud-related failure for {item.id}; escalated to human review"
        elif category == "hard":
            reason = EscalationReason.HARD_FAILURE
            message = f"Hard failure for {item.id}; escalated to human review"
        elif category == "authentication_required":
            reason = EscalationReason.AUTHENTICATION_REQUIRED
            message = f"Authentication required for {item.id}; escalated to human review"
        else:
            reason = EscalationReason.POLICY_DENIED
            message = f"Action {result.proposal.action.value} denied by policy for {item.id}"
        return Escalation(reason=reason, message=message, item_id=item.id)

    def _safe_transition(self, item: RecoveryItem, target: RecoveryStatus) -> RecoveryItem:
        """Transition the item state, respecting terminal states."""
        tr = self._state_machine.transition(item, target)
        return tr.item

    def _build_recovery_item(
        self,
        razorpay_failure: RazorpayPaymentFailure,
        normalized: NormalizedFailure,
    ) -> RecoveryItem:
        return RecoveryItem(
            id=razorpay_failure.razorpay_payment_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=razorpay_failure.razorpay_event_id,
            customer_id=self._default_customer_id,
            amount_minor=razorpay_failure.amount_minor,
            currency=razorpay_failure.currency,
            created_at=razorpay_failure.occurred_at,
            status=RecoveryStatus.DETECTED,
            root_cause=normalized.category.value,
            recovery_probability=None,
            metadata={
                "razorpay_payment_id": razorpay_failure.razorpay_payment_id,
                "error_code": normalized.code,
                "error_source": razorpay_failure.error_source,
                "error_step": razorpay_failure.error_step,
                "error_reason": razorpay_failure.error_reason,
                "payment_method": razorpay_failure.payment_method,
            },
        )

    def _score(self, item: RecoveryItem) -> RecoveryItem:
        probability = self._default_probability(item.root_cause)
        value = self._scorer.score(
            RecoveryItem(
                id=item.id,
                source_type=item.source_type,
                external_id=item.external_id,
                customer_id=item.customer_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                created_at=item.created_at,
                due_at=item.due_at,
                status=item.status,
                root_cause=item.root_cause,
                recovery_probability=probability,
                metadata=item.metadata,
            )
        )
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
            recovery_probability=probability,
            expected_recovery_value=value,
            metadata=item.metadata,
        )

    def _default_probability(self, root_cause: str | None) -> float:
        mapping = {
            "soft": 0.35,
            "hard": 0.05,
            "fraud": 0.0,
            "authentication_required": 0.1,
            "unknown": 0.0,
        }
        return mapping.get(root_cause or "unknown", 0.0)
