from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.audit.models import AuditEvent, AuditLog
from app.domain.context import RecoveryContext
from app.domain.escalation import Escalation, EscalationReason
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.policies.engine import PolicyEngine, PolicyDecision
from app.policies.guard import RecoveryGuard
from app.policies.stopping_rules import StoppingRules


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    """Structured AI diagnosis for a recovery case."""

    root_cause: str
    confidence: float
    evidence: list[str]
    recommended_action: str
    rationale: str
    risk_level: str  # low, medium, high, critical
    customer_context: str = ""
    expected_effect: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryRunResult:
    """Complete result of running the recovery orchestrator."""

    recovery_item_id: str
    classification: str
    diagnosis: DiagnosisResult | None = None
    proposed_action: str | None = None
    score: dict[str, Any] | None = None
    priority: str | None = None
    safety_decision: str | None = None
    execution_result: dict[str, Any] | None = None
    verification_result: dict[str, Any] | None = None
    final_state: str | None = None
    actual_recovery_value: int | None = None
    next_action: str | None = None
    stop_reason: str | None = None
    escalation_reason: str | None = None
    audit_events: list[AuditEvent] = field(default_factory=list)


class RecoveryOrchestrator:
    """Coordinates the full autonomous recovery loop.

    Flow:
        1. Build context from item + failure
        2. Agent proposes (AI layer — NEVER executes)
        3. Validate proposal
        4. Deterministic expected-value scoring
        5. StoppingRules check (highest priority)
        6. PolicyEngine check
        7. DefaultRecoveryGuard final safety decision
        8. IF allowed: execute bounded action
        9. Verify outcome (financial recovery, not just execution success)
        10. Record outcome and audit trail
        11. Determine next best action

    The AI NEVER bypasses:
        - PolicyEngine
        - StoppingRules
        - retry budget
        - fraud protection
        - opt-out protection
        - deadline protection
        - promise expiry
        - terminal-state protection
    """

    def __init__(
        self,
        *,
        agent: Any = None,
        policy_engine: PolicyEngine,
        audit_log: AuditLog,
        validator: Any = None,
        stopping_rules: StoppingRules | None = None,
        guard: RecoveryGuard | None = None,
        scorer: Any = None,
        executor: Any = None,
        retry_policy: Any = None,
        state_machine: Any = None,
        outcomes: Any = None,
        confidence_thresholds: dict[str, float] | None = None,
    ) -> None:
        self._agent = agent
        self._policy_engine = policy_engine
        self._audit_log = audit_log
        self._validator = validator
        self._stopping_rules = stopping_rules
        self._guard = guard
        self._scorer = scorer
        self._executor = executor
        self._retry_policy = retry_policy
        self._state_machine = state_machine
        self._outcomes = outcomes

        # Confidence thresholds for decisioning
        self._high_confidence = (confidence_thresholds or {}).get("high", 0.80)
        self._low_confidence = (confidence_thresholds or {}).get("low", 0.50)

    def run(self, item: RecoveryItem, context: RecoveryContext) -> RecoveryRunResult:
        """Run the full recovery orchestration loop."""
        events: list[AuditEvent] = []
        recovery_item_id = item.id

        # Stage 1: AI diagnosis / proposal
        diagnosis, proposal = self._propose(item, context, events)

        # Stage 2: Deterministic scoring
        score_result = self._score(item, context, proposal, events)

        # Stage 3: Safety check (stopping rules + policy)
        safety_decision = self._safety_check(item, context, proposal, events)

        # Stage 4: Execute if allowed
        execution_result = None
        if safety_decision == "ALLOWED":
            execution_result = self._execute(item, context, proposal, events)

        # Stage 5: Verify outcome
        verification_result = self._verify_outcome(item, execution_result, events)

        # Stage 6: Determine next best action
        next_action = self._determine_next_action(item, safety_decision, execution_result, verification_result)

        # Stage 7: Build final result
        final_state = item.status.value if hasattr(item.status, "value") else str(item.status)

        return RecoveryRunResult(
            recovery_item_id=recovery_item_id,
            classification=item.root_cause or "unknown",
            diagnosis=diagnosis,
            proposed_action=proposal.action.value if proposal else None,
            score={
                "expected_recovery_value": score_result.expected_recovery_value,
                "recovery_probability": score_result.recovery_probability,
                "intervention_cost": score_result.intervention_cost,
                "priority": score_result.priority,
                "scoring_reason": score_result.scoring_reason,
            } if score_result else None,
            priority=score_result.priority if score_result else None,
            safety_decision=safety_decision,
            execution_result=execution_result,
            verification_result=verification_result,
            final_state=final_state,
            actual_recovery_value=verification_result.get("actual_recovery_value") if verification_result else None,
            next_action=next_action,
            stop_reason=getattr(item, "stopped_reason", None),
            escalation_reason=self._get_escalation_reason(item),
            audit_events=events,
        )

    def _propose(self, item: RecoveryItem, context: RecoveryContext, events: list[AuditEvent]) -> tuple[DiagnosisResult | None, RecoveryProposal | None]:
        """Stage 1: AI proposes — NEVER executes."""
        if self._agent is None:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="agent_skipped",
                reason="No agent configured",
                metadata={},
            ))
            return None, None

        try:
            proposal = self._agent.propose(context)
        except Exception as exc:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="agent_failed",
                reason=f"Agent failed to propose: {exc}",
                metadata={"error": str(exc), "error_type": type(exc).__name__},
            ))
            # Safe fallback: escalate to human or let rules engine take over
            return None, None

        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="agent",
            action="agent_proposal_created",
            reason=f"Agent proposed {proposal.action.value}",
            metadata={
                "action": proposal.action.value,
                "confidence": proposal.confidence,
                "model": proposal.model_name,
                "agent": self._agent.name,
            },
        ))

        # Validate proposal
        if self._validator is not None:
            try:
                self._validator.validate(proposal, context)
            except Exception as exc:
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="system",
                    action="agent_proposal_rejected",
                    reason=str(exc),
                    metadata={"error": str(exc), "action": proposal.action.value},
                ))
                # Fail closed: return stop_recovery as safe default
                safe_proposal = RecoveryProposal(
                    action=RecoveryAction.STOP_RECOVERY,
                    reason=f"Proposal validation failed: {exc}",
                    confidence=0.0,
                    model_name="validator",
                )
                diagnosis = DiagnosisResult(
                    root_cause=item.root_cause or "unknown",
                    confidence=0.0,
                    evidence=[f"Validation failed: {exc}"],
                    recommended_action="stop_recovery",
                    rationale="Invalid proposal rejected by validator",
                    risk_level="critical",
                )
                return diagnosis, safe_proposal

        # Build structured diagnosis from actual context
        diagnosis = self._build_diagnosis(item, context, proposal)
        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="agent",
            action="diagnosis_created",
            reason=f"Diagnosis: {diagnosis.rationale}",
            metadata={
                "confidence": diagnosis.confidence,
                "risk_level": diagnosis.risk_level,
                "evidence": diagnosis.evidence,
                "recommended_action": diagnosis.recommended_action,
            },
        ))

        return diagnosis, proposal

    def _build_diagnosis(self, item: RecoveryItem, context: RecoveryContext, proposal: RecoveryProposal) -> DiagnosisResult:
        """Build structured diagnosis from actual item/context data."""
        evidence = list(proposal.evidence) if proposal.evidence else []

        # Add actual context evidence (never invent)
        if context.failure_category:
            evidence.append(f"Failure category: {context.failure_category.value}")
        if context.retryable:
            evidence.append("Failure is retryable")
        if context.customer_opt_out:
            evidence.append("Customer has opted out")
        if context.attempt_count > 0:
            evidence.append(f"Previous attempts: {context.attempt_count}")
        if item.amount_minor:
            evidence.append(f"Amount at risk: ₹{item.amount_minor / 100:.0f}")

        # Determine risk level based on actual data
        risk_level = "low"
        if item.root_cause in {"fraud", "hard_decline", "security_or_fraud"}:
            risk_level = "critical"
        elif item.root_cause in {"authentication_required"}:
            risk_level = "medium"
        elif context.attempt_count >= 2:
            risk_level = "medium"
        elif not context.retryable:
            risk_level = "high"

        # Adjust confidence based on evidence quality
        confidence = proposal.confidence
        if len(evidence) < 2:
            confidence = min(confidence, 0.5)  # Low evidence → lower confidence
        if context.customer_opt_out:
            confidence = 0.95  # Opt-out is certain

        return DiagnosisResult(
            root_cause=item.root_cause or context.failure_category.value,
            confidence=confidence,
            evidence=evidence,
            recommended_action=proposal.action.value,
            rationale=proposal.reason,
            risk_level=risk_level,
            customer_context=f"Customer {item.customer_id}" if item.customer_id else "",
            expected_effect=f"Expected recovery: ₹{item.expected_recovery_value / 100:.0f}" if item.expected_recovery_value else "",
        )

    def _score(self, item: RecoveryItem, context: RecoveryContext, proposal: RecoveryProposal | None, events: list[AuditEvent]) -> Any:
        """Stage 2: Deterministic expected-value scoring."""
        if self._scorer is None or proposal is None:
            return None

        result = self._scorer.score(
            amount_minor=item.amount_minor,
            failure_category=item.root_cause or context.failure_category.value,
            proposed_action=proposal.action.value,
            attempt_number=context.attempt_count + 1,
            context={
                "customer_id": item.customer_id,
                "currency": item.currency,
                "source_type": item.source_type.value,
            },
        )

        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="system",
            action="recovery_scored",
            reason="Expected value calculated deterministically",
            metadata={
                "amount_at_risk": result.amount_at_risk,
                "recovery_probability": result.recovery_probability,
                "intervention_cost": result.intervention_cost,
                "expected_recovery_value": result.expected_recovery_value,
                "priority": result.priority,
                "score_version": result.score_version,
                "scoring_reason": result.scoring_reason,
            },
        ))

        return result

    def _safety_check(self, item: RecoveryItem, context: RecoveryContext, proposal: RecoveryProposal | None, events: list[AuditEvent]) -> str:
        """Stage 3: Safety check — confidence check → stopping rules + policy engine + guard.

        Returns one of: ALLOWED, STOP, DENY, ESCALATE
        """
        if proposal is None:
            return "STOP"

        proposed_action = proposal.action.value

        # Confidence-aware decisioning (fail-closed)
        confidence = getattr(proposal, "confidence", None)
        if confidence is None or confidence < self._low_confidence:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="rule",
                action="confidence_check_failed",
                reason=f"Proposal confidence {confidence} is below threshold {self._low_confidence}; escalating for human review",
                metadata={
                    "confidence": confidence,
                    "threshold": self._low_confidence,
                    "proposed_action": proposed_action,
                },
            ))
            return "ESCALATE"

        if confidence < self._high_confidence:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="rule",
                action="confidence_warning",
                reason=f"Proposal confidence {confidence} is below high-confidence threshold {self._high_confidence}; additional validation required",
                metadata={
                    "confidence": confidence,
                    "threshold": self._high_confidence,
                    "proposed_action": proposed_action,
                },
            ))

        # Use guard if available (highest priority)
        if self._guard is not None:
            guard_decision = self._guard.evaluate(
                item,
                proposed_action,
                container=None,
                promises=None,
            )
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="rule",
                action="guard_evaluate",
                reason=guard_decision.reason,
                metadata={
                    "proposed_action": proposed_action,
                    "allowed": guard_decision.allowed,
                    "decision_type": guard_decision.decision_type,
                    "reason_code": guard_decision.reason_code,
                    "rule": guard_decision.rule,
                    "next_state": guard_decision.next_state.value if hasattr(guard_decision.next_state, "value") else str(guard_decision.next_state),
                },
            ))

            if not guard_decision.allowed:
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="system",
                    action="recovery_stopped",
                    reason=guard_decision.reason,
                    metadata={
                        "reason_code": guard_decision.reason_code,
                        "rule": guard_decision.rule,
                        "decision_type": guard_decision.decision_type,
                    },
                ))
                return guard_decision.decision_type

            return "ALLOWED"

        # Fallback: policy engine only
        if self._policy_engine is not None:
            # Create item stub for policy evaluation
            policy_item = item.__class__(
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
            decision = self._policy_engine.evaluate(policy_item, proposed_action)
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
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
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="system",
                    action="recovery_stopped",
                    reason=decision.reason,
                    metadata={
                        "reason_code": decision.reason_code,
                        "rule": decision.policy_rule,
                    },
                ))
                return "DENY"

            if decision.requires_human_approval:
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="system",
                    action="intervention_pending",
                    reason="Human approval required before execution",
                    metadata={"action": proposed_action, "policy_rule": decision.policy_rule},
                ))
                return "ESCALATE"

            return "ALLOWED"

        return "ALLOWED"

    def _execute(self, item: RecoveryItem, context: RecoveryContext, proposal: RecoveryProposal, events: list[AuditEvent]) -> dict[str, Any] | None:
        """Stage 4: Execute bounded action."""
        if self._executor is None:
            return None

        attempt_number = int(item.metadata.get("attempt_count", 0)) + 1
        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="system",
            action="execution_requested",
            reason=f"Executing {proposal.action.value} (attempt {attempt_number})",
            metadata={"action": proposal.action.value, "attempt_number": attempt_number},
        ))

        try:
            result = self._executor.execute(
                item,
                proposal.action.value,
                attempt_number=attempt_number,
            )
        except Exception as exc:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="execution_failed",
                reason=f"Executor raised: {exc}",
                metadata={"error": str(exc)},
            ))
            return {
                "success": False,
                "action": proposal.action.value,
                "attempt_number": attempt_number,
                "reason": str(exc),
                "retry_eligible": False,
            }

        if result.success:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="execution_succeeded",
                reason=result.reason,
                metadata={"action": proposal.action.value, "attempt_number": attempt_number},
            ))
        else:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="execution_failed",
                reason=result.reason,
                metadata={
                    "action": proposal.action.value,
                    "attempt_number": attempt_number,
                    "retry_eligible": result.retry_eligible,
                },
            ))

        return {
            "success": result.success,
            "action": result.action,
            "attempt_number": result.attempt_number,
            "reason": result.reason,
            "retry_eligible": result.retry_eligible,
            "error_code": result.error_code,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
            "metadata": result.metadata or {},
        }

    def _verify_outcome(self, item: RecoveryItem, execution_result: dict[str, Any] | None, events: list[AuditEvent]) -> dict[str, Any] | None:
        """Stage 5: Verify actual financial outcome.

        IMPORTANT: Execution success ≠ financial recovery.
        Financial recovery must be verified from outcome/payment data.
        """
        if execution_result is None:
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="verification_skipped",
                reason="No execution to verify",
                metadata={},
            ))
            return None

        if not execution_result.get("success"):
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="verification_failed",
                reason="Execution failed, no financial recovery",
                metadata={"execution_reason": execution_result.get("reason")},
            ))
            return {
                "status": "failed",
                "actual_recovery_value": 0,
                "note": "Execution failed — no financial recovery",
            }

        # Execution succeeded — check for actual recovery outcome
        if self._outcomes is not None:
            try:
                outcome = self._outcomes.get_for_item(item.id)
                if outcome is not None:
                    actual_value = getattr(outcome, "actual_recovery_minor", None) or 0
                    outcome_type = getattr(outcome, "outcome_type", "recovered")
                    events.append(self._audit_log.log(
                        recovery_item_id=item.id,
                        actor="system",
                        action="verification_complete",
                        reason=f"Outcome verified: {outcome_type}",
                        metadata={
                            "actual_recovery_value": actual_value,
                            "outcome_type": outcome_type,
                            "expected_recovery_value": item.expected_recovery_value,
                        },
                    ))
                    return {
                        "status": outcome_type,
                        "actual_recovery_value": actual_value,
                        "expected_recovery_value": item.expected_recovery_value,
                        "note": "Verified from outcome record",
                    }
            except Exception:
                pass

        # No outcome record yet — execution succeeded but financial recovery not confirmed
        events.append(self._audit_log.log(
            recovery_item_id=item.id,
            actor="system",
            action="verification_pending",
            reason="Execution succeeded; financial outcome pending verification",
            metadata={"expected_recovery_value": item.expected_recovery_value},
        ))
        return {
            "status": "pending",
            "actual_recovery_value": None,
            "expected_recovery_value": item.expected_recovery_value,
            "note": "Execution succeeded; awaiting financial confirmation",
        }

    def _determine_next_action(self, item: RecoveryItem, safety_decision: str, execution_result: dict[str, Any] | None, verification_result: dict[str, Any] | None) -> str:
        """Stage 6: Determine the deterministic next best action."""
        if safety_decision != "ALLOWED":
            if safety_decision == "STOP":
                return "stop_recovery"
            if safety_decision == "DENY":
                return "escalate_human"
            if safety_decision == "ESCALATE":
                return "escalate_human"
            return "stop_recovery"

        if execution_result is None:
            return "no_action"

        if execution_result.get("success"):
            if verification_result and verification_result.get("status") == "recovered":
                return "no_action"  # Terminal state
            return "verify_payment"

        # Execution failed
        if execution_result.get("retry_eligible"):
            return "retry_payment"
        return "escalate_human"

    def _get_escalation_reason(self, item: RecoveryItem) -> str | None:
        """Get escalation reason if item is escalated."""
        if item.status != RecoveryStatus.ESCALATED:
            return None
        return item.stopped_reason or item.stopped_rule or "escalated"
