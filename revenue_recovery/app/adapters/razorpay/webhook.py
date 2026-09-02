from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.adapters.razorpay.events import (
    RazorpayPaymentFailure,
    RazorpayPaymentSuccess,
    parse_razorpay_event,
    parse_razorpay_settlement_event,
)
from app.adapters.razorpay.signatures import RazorpaySignatureError, verify_razorpay_signature
from app.services.settlement_verifier import SettlementEvent, SettlementVerifier
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import AuditEvent, AuditLog
from app.db.decision_repository import RecoveryDecisionRepository
from app.db.repositories import RecoveryItemRepository
from app.domain.context import RecoveryContext
from app.domain.escalation import Escalation, EscalationReason
from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction
from app.domain.transitions import DefaultStateMachine, RecoveryStateMachine
from app.idempotency.store import IdempotencyStore
from app.interventions.executor import ExecutionResult, RecoveryExecutor, SimulatedRecoveryExecutor
from app.ledger.attempts import AttemptLedger, AttemptRecord
from app.policies.engine import PolicyEngine, PolicyDecision
from app.policies.guard import DefaultRecoveryGuard, RecoveryGuard
from app.policies.retry import DefaultRetryPolicy, RetryPolicy
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer, ScoreResult


class RazorpayWebhookService:
    """Processes Razorpay webhooks through a durable, idempotent recovery lifecycle.

    Flow:
        verify signature → parse event → persist provider event (idempotent)
        → if duplicate: return early
        → classify failure → create RecoveryItem → score → agent proposes
        → validator validates → policy decides → IF allowed: execute
        → attempt ledger → retry decision → state transition → audit
        → IF denied: escalate → audit
        → mark provider event processed with recovery_item_id

    The database provider_events table is the source of truth for idempotency.
    """

    def __init__(
        self,
        *,
        webhook_secret: str,
        scorer: RecoveryScorer,
        policy_engine: PolicyEngine,
        audit_log: AuditLog,
        idempotency_store: IdempotencyStore,
        provider_events: Any = None,
        recovery_items: RecoveryItemRepository | None = None,
        decisions: RecoveryDecisionRepository | None = None,
        attempts: AttemptLedger | None = None,
        agent: RecoveryDecisionAgent | None = None,
        orchestrator: RecoveryAgentOrchestrator | None = None,
        executor: RecoveryExecutor | None = None,
        retry_policy: RetryPolicy | None = None,
        state_machine: RecoveryStateMachine | None = None,
        stopping_rules: StoppingRules | None = None,
        guard: RecoveryGuard | None = None,
        outcomes: Any = None,
        promises: Any = None,
        default_customer_id: str = "razorpay_customer",
    ) -> None:
        self._webhook_secret = webhook_secret
        self._scorer = scorer
        self._policy_engine = policy_engine
        self._audit_log = audit_log
        self._idempotency_store = idempotency_store
        self._provider_events = provider_events
        self._recovery_items = recovery_items
        self._decisions = decisions
        self._attempts = attempts
        self._outcomes = outcomes
        self._promises = promises
        self._default_customer_id = default_customer_id
        self._agent = agent or MockRecoveryDecisionAgent()
        self._orchestrator = orchestrator
        self._executor = executor or SimulatedRecoveryExecutor()
        self._retry_policy = retry_policy or DefaultRetryPolicy(max_attempts=3)
        self._state_machine = state_machine or DefaultStateMachine()
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

    @property
    def container(self) -> Any:
        """Expose underlying repositories as a container-like namespace for route helpers."""

        class _ServiceContainer:
            pass

        c = _ServiceContainer()
        c.recovery_items = self._recovery_items
        c.decisions = self._decisions
        c.attempts = self._attempts
        c.outcomes = self._outcomes
        c.promises = self._promises
        c.provider_events = self._provider_events
        c.idempotency = self._idempotency_store
        c.audit_log = self._audit_log
        return c

    def process_webhook(
        self,
        raw_body: bytes,
        signature_header: str | None,
    ) -> tuple[RecoveryItem | None, list[AuditEvent], str]:
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
        import json
        raw_event_type = ""
        try:
            parsed_json = json.loads(raw_body)
            if isinstance(parsed_json, dict):
                raw_event_type = parsed_json.get("event", "")
        except Exception:
            pass

        settlement_types = {"payment.captured", "payment.authorized", "payment_link.paid", "order.paid"}
        if raw_event_type in settlement_types:
            try:
                settlement_data = parse_razorpay_settlement_event(raw_body)
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

            provider = "razorpay"
            provider_event_id = settlement_data.razorpay_event_id
            received_at = datetime.now(timezone.utc)

            provider_event = None
            is_new_event = False
            if self._provider_events is not None:
                import uuid
                from app.domain.models import ProviderEvent
                candidate = ProviderEvent(
                    id=str(uuid.uuid4()),
                    provider=provider,
                    provider_event_id=provider_event_id,
                    received_at=received_at,
                    event_type=settlement_data.event_type,
                    raw_payload=settlement_data.raw_payload,
                    processing_status="pending",
                )
                is_new_event, provider_event = self._provider_events.try_insert(candidate)
            else:
                is_new_event = True

            if not is_new_event and provider_event is not None:
                from app.audit.models import EventType
                events.append(self._audit_log.log(
                    recovery_item_id=provider_event.recovery_item_id,
                    actor="system",
                    action="duplicate_event_ignored",
                    reason="Provider event already processed",
                    metadata={
                        "event_type": EventType.DUPLICATE_WEBHOOK_SKIPPED,
                        "provider": provider,
                        "provider_event_id": provider_event_id,
                    },
                    event_type=EventType.DUPLICATE_WEBHOOK_SKIPPED,
                    correlation_id=provider_event_id,
                ))
                return None, events, "duplicate"

            target_item = None
            if settlement_data.recovery_item_id and self._recovery_items is not None:
                target_item = self._recovery_items.get(settlement_data.recovery_item_id)

            if not target_item:
                events.append(self._audit_log.log(
                    recovery_item_id=settlement_data.recovery_item_id or settlement_data.payment_link_id,
                    actor="settlement_verifier",
                    action="settlement_unmatched",
                    reason="Could not correlate Razorpay settlement event to a RecoveryItem",
                    metadata={"provider_event_id": provider_event_id, "payment_link_id": settlement_data.payment_link_id},
                ))
                return None, events, "unmatched"

            st_event = SettlementEvent(
                event_id=settlement_data.razorpay_event_id,
                provider="razorpay",
                recovery_item_id=target_item.id,
                success=True,
                actual_amount_minor=settlement_data.amount_minor,
                currency=settlement_data.currency,
                settled_at=settlement_data.occurred_at,
                metadata={
                    "razorpay_payment_id": settlement_data.razorpay_payment_id,
                    "payment_link_id": settlement_data.payment_link_id,
                    "event_type": settlement_data.event_type,
                },
            )
            sv = SettlementVerifier(
                recovery_items=self._recovery_items,
                outcomes=self._outcomes,
                audit_log=self._audit_log,
                state_machine=self._state_machine,
            )
            res = sv.process_settlement(st_event)

            if self._provider_events is not None:
                self._provider_events.mark_processed(
                    provider=provider,
                    provider_event_id=provider_event_id,
                    recovery_item_id=target_item.id,
                )

            updated_item = self._recovery_items.get(target_item.id) if self._recovery_items is not None else target_item
            return updated_item, events, res.status

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

        # Stage 3: durable provider event idempotency (database is source of truth)
        provider = "razorpay"
        provider_event_id = razorpay_failure.razorpay_event_id
        received_at = datetime.now(timezone.utc)

        provider_event = None
        is_new_event = False
        if self._provider_events is not None:
            import uuid
            from app.domain.models import ProviderEvent
            candidate = ProviderEvent(
                id=str(uuid.uuid4()),
                provider=provider,
                provider_event_id=provider_event_id,
                received_at=received_at,
                event_type="payment.failed",
                raw_payload={
                    "razorpay_event_id": razorpay_failure.razorpay_event_id,
                    "razorpay_payment_id": razorpay_failure.razorpay_payment_id,
                    "amount_minor": razorpay_failure.amount_minor,
                    "currency": razorpay_failure.currency,
                },
                processing_status="pending",
            )
            is_new_event, provider_event = self._provider_events.try_insert(candidate)
            if is_new_event:
                events.append(self._audit_log.log(
                    recovery_item_id=None,
                    actor="system",
                    action="provider_event_recorded",
                    reason="Provider event persisted for durable idempotency",
                    metadata={
                        "provider": provider,
                        "provider_event_id": provider_event_id,
                        "event_type": "payment.failed",
                    },
                ))
        else:
            is_new_event = True

        if not is_new_event and provider_event is not None:
            from app.audit.models import EventType
            events.append(self._audit_log.log(
                recovery_item_id=provider_event.recovery_item_id,
                actor="system",
                action="duplicate_event_ignored",
                reason="Provider event already processed",
                metadata={
                    "event_type": EventType.DUPLICATE_WEBHOOK_SKIPPED,
                    "provider": provider,
                    "provider_event_id": provider_event_id,
                    "recovery_item_id": provider_event.recovery_item_id,
                },
                event_type=EventType.DUPLICATE_WEBHOOK_SKIPPED,
                correlation_id=provider_event_id,
            ))
            return None, events, "duplicate"

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

        if self._recovery_items is not None:
            self._recovery_items.save(item)

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

        # Stage 6: build context and call agent (before scoring, so score can use proposed action)
        ctx = RecoveryContext.from_item_and_failure(
            item,
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

        # Stage 7: deterministic expected-value scoring (LLM never determines the score)
        score_result = self._score(
            item=item,
            failure_category=normalized.category.value,
            proposed_action=result.proposal.action.value,
            attempt_number=0,
        )
        scored_item = self._apply_score(item, score_result)
        events.append(self._audit_log.log(
            recovery_item_id=scored_item.id,
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

        if self._recovery_items is not None:
            self._recovery_items.save(scored_item)

        # Stage 8: guard evaluation before execution
        execution_result = None
        escalation = None
        retry_decision = None
        guard_decision = None

        if self._guard is not None:
            guard_decision = self._guard.evaluate(
                scored_item,
                result.proposal.action.value,
                container=None,
                promises=self._promises,
            )
            events.append(self._audit_log.log(
                recovery_item_id=scored_item.id,
                actor="rule",
                action="guard_evaluate",
                reason=guard_decision.reason,
                metadata={
                    "proposed_action": result.proposal.action.value,
                    "allowed": guard_decision.allowed,
                    "decision_type": guard_decision.decision_type,
                    "reason_code": guard_decision.reason_code,
                    "rule": guard_decision.rule,
                    "next_state": guard_decision.next_state.value,
                },
            ))

            if not guard_decision.allowed:
                final_status = guard_decision.next_state
                scored_item = self._safe_transition(scored_item, final_status)
                scored_item = scored_item.__class__(
                    id=scored_item.id,
                    source_type=scored_item.source_type,
                    external_id=scored_item.external_id,
                    customer_id=scored_item.customer_id,
                    amount_minor=scored_item.amount_minor,
                    currency=scored_item.currency,
                    created_at=scored_item.created_at,
                    due_at=scored_item.due_at,
                    status=final_status,
                    root_cause=scored_item.root_cause,
                    recovery_probability=scored_item.recovery_probability,
                    expected_recovery_value=scored_item.expected_recovery_value,
                    intervention_cost=scored_item.intervention_cost,
                    failure_category=scored_item.failure_category,
                    provider=scored_item.provider,
                    provider_event_id=scored_item.provider_event_id,
                    actual_recovery_value=scored_item.actual_recovery_value,
                    recovery_status=scored_item.recovery_status,
                    score_version=scored_item.score_version,
                    scoring_reason=scored_item.scoring_reason,
                    priority=scored_item.priority,
                    stopped_reason=guard_decision.reason_code,
                    stopped_rule=guard_decision.rule,
                    metadata=scored_item.metadata,
                )
                if final_status == RecoveryStatus.ESCALATED:
                    escalation = self._create_escalation(result, scored_item)
                events.append(self._audit_log.log(
                    recovery_item_id=scored_item.id,
                    actor="system",
                    action="recovery_stopped",
                    reason=guard_decision.reason,
                    metadata={
                        "reason_code": guard_decision.reason_code,
                        "rule": guard_decision.rule,
                        "decision_type": guard_decision.decision_type,
                    },
                ))
            else:
                # Guard allowed — execute
                scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_PENDING)
                scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_EXECUTED)
                execution_result = self._execute(scored_item, result.proposal.action.value, events)
                if execution_result.success:
                    if result.proposal.action == RecoveryAction.STOP_RECOVERY or str(result.proposal.action.value) == "stop_recovery":
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.STOPPED)
                        scored_item = scored_item.__class__(
                            id=scored_item.id,
                            source_type=scored_item.source_type,
                            external_id=scored_item.external_id,
                            customer_id=scored_item.customer_id,
                            amount_minor=scored_item.amount_minor,
                            currency=scored_item.currency,
                            created_at=scored_item.created_at,
                            due_at=scored_item.due_at,
                            status=RecoveryStatus.STOPPED,
                            root_cause=scored_item.root_cause,
                            recovery_probability=scored_item.recovery_probability,
                            expected_recovery_value=scored_item.expected_recovery_value,
                            intervention_cost=scored_item.intervention_cost,
                            failure_category=scored_item.failure_category,
                            provider=scored_item.provider,
                            provider_event_id=scored_item.provider_event_id,
                            actual_recovery_value=0,
                            recovery_status=scored_item.recovery_status,
                            score_version=scored_item.score_version,
                            scoring_reason=scored_item.scoring_reason,
                            priority=scored_item.priority,
                            stopped_reason=guard_decision.reason_code,
                            stopped_rule=guard_decision.rule,
                            metadata=scored_item.metadata,
                        )
                    else:
                        # Execution succeeded -> PENDING_VERIFICATION
                        # Recovery is recognized ONLY after authoritative settlement verification
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.PENDING_VERIFICATION)
                        scored_item = scored_item.__class__(
                            id=scored_item.id,
                            source_type=scored_item.source_type,
                            external_id=scored_item.external_id,
                            customer_id=scored_item.customer_id,
                            amount_minor=scored_item.amount_minor,
                            currency=scored_item.currency,
                            created_at=scored_item.created_at,
                            due_at=scored_item.due_at,
                            status=RecoveryStatus.PENDING_VERIFICATION,
                            root_cause=scored_item.root_cause,
                            recovery_probability=scored_item.recovery_probability,
                            expected_recovery_value=scored_item.expected_recovery_value,
                            intervention_cost=scored_item.intervention_cost,
                            failure_category=scored_item.failure_category,
                            provider=scored_item.provider,
                            provider_event_id=scored_item.provider_event_id,
                            actual_recovery_value=0,
                            recovery_status=scored_item.recovery_status,
                            score_version=scored_item.score_version,
                            scoring_reason=scored_item.scoring_reason,
                            priority=scored_item.priority,
                            metadata=scored_item.metadata,
                        )
                else:
                    retry_decision = self._retry_policy.evaluate(
                        scored_item,
                        category=normalized.category,
                        occurred_at=datetime.now(timezone.utc),
                    )
                    if retry_decision.allowed:
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.FAILED)
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
            # Fallback to original policy-only logic
            if result.policy_decision.allowed and not result.policy_decision.requires_human_approval:
                scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_PENDING)
                scored_item = self._safe_transition(scored_item, RecoveryStatus.INTERVENTION_EXECUTED)
                execution_result = self._execute(scored_item, result.proposal.action.value, events)

                if execution_result.success:
                    if result.proposal.action == RecoveryAction.STOP_RECOVERY:
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.STOPPED)
                    elif result.proposal.action == RecoveryAction.ESCALATE_HUMAN:
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.ESCALATED)
                    else:
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.PENDING_VERIFICATION)
                        scored_item = scored_item.__class__(
                            id=scored_item.id,
                            source_type=scored_item.source_type,
                            external_id=scored_item.external_id,
                            customer_id=scored_item.customer_id,
                            amount_minor=scored_item.amount_minor,
                            currency=scored_item.currency,
                            created_at=scored_item.created_at,
                            due_at=scored_item.due_at,
                            status=RecoveryStatus.PENDING_VERIFICATION,
                            root_cause=scored_item.root_cause,
                            recovery_probability=scored_item.recovery_probability,
                            expected_recovery_value=scored_item.expected_recovery_value,
                            intervention_cost=scored_item.intervention_cost,
                            failure_category=scored_item.failure_category,
                            provider=scored_item.provider,
                            provider_event_id=scored_item.provider_event_id,
                            recovery_status=scored_item.recovery_status,
                            score_version=scored_item.score_version,
                            scoring_reason=scored_item.scoring_reason,
                            priority=scored_item.priority,
                            stopped_reason=scored_item.stopped_reason,
                            stopped_rule=scored_item.stopped_rule,
                            metadata=scored_item.metadata,
                        )
                else:
                    retry_decision = self._retry_policy.evaluate(
                        scored_item,
                        category=normalized.category,
                        occurred_at=datetime.now(timezone.utc),
                    )
                    if retry_decision.allowed:
                        scored_item = self._safe_transition(scored_item, RecoveryStatus.FAILED)
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

        if self._recovery_items is not None:
            self._recovery_items.save(scored_item)

        # Stage 10: mark provider event as processed, linking to recovery item
        if self._provider_events is not None and is_new_event:
            self._provider_events.mark_processed(
                provider=provider,
                provider_event_id=provider_event_id,
                recovery_item_id=scored_item.id,
            )
            events.append(self._audit_log.log(
                recovery_item_id=scored_item.id,
                actor="system",
                action="provider_event_linked",
                reason="Provider event linked to recovery item",
                metadata={
                    "provider": provider,
                    "provider_event_id": provider_event_id,
                    "recovery_item_id": scored_item.id,
                },
            ))

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
        tr = self._state_machine.transition(item, target)
        return tr.item

    def _build_recovery_item(
        self,
        razorpay_failure: RazorpayPaymentFailure,
        normalized: NormalizedFailure,
    ) -> RecoveryItem:
        import uuid
        from app.domain.customer_names import derive_customer_name
        extracted_cust = razorpay_failure.customer_id or self._default_customer_id
        derived_name = derive_customer_name(extracted_cust, getattr(razorpay_failure, "customer_name", None))
        # Detect smoke/stress test sources
        is_smoke = (
            "smoke" in razorpay_failure.razorpay_event_id.lower()
            or "smoke" in razorpay_failure.razorpay_payment_id.lower()
            or (isinstance(razorpay_failure.raw_payload, dict) and isinstance(razorpay_failure.raw_payload.get("notes"), dict) and razorpay_failure.raw_payload.get("notes", {}).get("source") == "smoke_test")
        )
        source_tag = "smoke_test" if is_smoke else "webhook_live"

        return RecoveryItem(
            id=razorpay_failure.razorpay_payment_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=razorpay_failure.razorpay_event_id,
            customer_id=extracted_cust,
            amount_minor=razorpay_failure.amount_minor,
            currency=razorpay_failure.currency,
            created_at=razorpay_failure.occurred_at,
            status=RecoveryStatus.DETECTED,
            root_cause=normalized.category.value,
            recovery_probability=None,
            metadata={
                "source": source_tag,
                "is_synthetic": is_smoke,
                "is_test_fixture": is_smoke,
                "customer_name": derived_name,
                "razorpay_payment_id": razorpay_failure.razorpay_payment_id,
                "error_code": normalized.code,
                "error_source": razorpay_failure.error_source,
                "error_step": razorpay_failure.error_step,
                "error_reason": razorpay_failure.error_reason,
                "payment_method": razorpay_failure.payment_method,
            },
        )

    def _score(
        self,
        item: RecoveryItem,
        failure_category: str,
        proposed_action: str,
        attempt_number: int = 0,
    ) -> ScoreResult:
        """Deterministically score a recovery item.

        The LLM never determines this score. It is calculated purely from
        amount, failure category, proposed action, and attempt number.
        """
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

    def _default_probability(self, root_cause: str | None) -> float:
        mapping = {
            "soft": 0.35,
            "hard": 0.05,
            "fraud": 0.0,
            "authentication_required": 0.1,
            "unknown": 0.0,
        }
        return mapping.get(root_cause or "unknown", 0.0)

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

    def _default_probability(self, root_cause: str | None) -> float:
        mapping = {
            "soft": 0.35,
            "hard": 0.05,
            "fraud": 0.0,
            "authentication_required": 0.1,
            "unknown": 0.0,
        }
        return mapping.get(root_cause or "unknown", 0.0)
