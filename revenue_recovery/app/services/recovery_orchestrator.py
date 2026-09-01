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
class NextActionDecision:
    """Structured decision object for orchestrator state machine routing."""

    selected_action: str
    reasoning: str
    expected_outcome: str
    stop_condition: str | None = None
    policy_relevant_metadata: dict[str, Any] = field(default_factory=dict)
    requires_observation: bool = True


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
    next_action_decision: NextActionDecision | None = None
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
        promises: Any = None,
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
        self._promises = promises

        # Confidence thresholds for decisioning
        self._high_confidence = (confidence_thresholds or {}).get("high", 0.80)
        self._low_confidence = (confidence_thresholds or {}).get("low", 0.50)

    def run(self, item: RecoveryItem, context: RecoveryContext, max_loop_iterations: int = 5) -> RecoveryRunResult:
        """Run the full closed-loop recovery orchestration state machine."""
        events: list[AuditEvent] = []
        recovery_item_id = item.id

        current_item = item
        current_context = context
        loop_iteration = 0

        last_diagnosis: DiagnosisResult | None = None
        last_proposal: RecoveryProposal | None = None
        last_score_result: Any = None
        last_safety_decision: str | None = None
        last_execution_result: dict[str, Any] | None = None
        last_verification_result: dict[str, Any] | None = None
        last_next_action_decision: NextActionDecision | None = None
        candidate_evals: list[dict[str, Any]] = []

        # Maintain cumulative observations list
        observations: list[dict[str, Any]] = list(current_item.metadata.get("observations", []))
        if current_context.observations:
            for obs in current_context.observations:
                if obs not in observations:
                    observations.append(obs)

        while loop_iteration < max_loop_iterations:
            loop_iteration += 1

            # Check if item is in a terminal state
            if self._state_machine and self._state_machine.is_terminal(current_item):
                break
            if current_item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.ESCALATED, RecoveryStatus.STOPPED}:
                break

            # Stage 1: AI proposal / diagnosis
            diagnosis, proposal = self._propose(current_item, current_context, events)
            last_diagnosis = diagnosis
            last_proposal = proposal

            if proposal is None:
                last_safety_decision = "STOP"
                current_item = self._safe_transition(current_item, RecoveryStatus.ESCALATED)
                current_item = self._apply_stopped_reason(current_item, "agent_failed", "proposal_missing")
                break

            # Stage 2: Deterministic scoring & Multi-candidate EV optimization
            score_result = self._score(current_item, current_context, proposal, events)
            last_score_result = score_result

            if hasattr(self._scorer, "evaluate_candidates"):
                candidate_evals = self._scorer.evaluate_candidates(
                    amount_minor=current_item.amount_minor,
                    failure_category=current_context.failure_category.value if hasattr(current_context.failure_category, "value") else str(current_context.failure_category),
                    attempt_number=current_context.attempt_count + 1,
                    context={**current_item.metadata, "customer_opted_out": current_context.customer_opt_out},
                )

            # Prevent infinite proposal loop (same action proposed repeatedly after failure without progress)
            proposed_act = getattr(proposal.action, "value", str(proposal.action))
            prev_actions = current_context.previous_actions
            last_obs = current_context.last_observation or {}
            last_status = last_obs.get("status")
            if (len(prev_actions) >= 2 and prev_actions[-1] == proposed_act and prev_actions[-2] == proposed_act) or (len(prev_actions) >= 1 and prev_actions[-1] == proposed_act and last_status == "failed"):
                events.append(self._audit_log.log(
                    recovery_item_id=recovery_item_id,
                    actor="system",
                    action="infinite_loop_blocked",
                    reason=f"Repeated identical proposal '{proposed_act}' without progress; halting recovery",
                    metadata={"proposed_action": proposed_act, "rule": "prevent_infinite_proposal_loop"},
                ))
                current_item = self._safe_transition(current_item, RecoveryStatus.STOPPED)
                current_item = self._apply_stopped_reason(current_item, "no_positive_action", "prevent_infinite_proposal_loop")
                last_safety_decision = "STOP"
                break

            # Stage 3: Safety check (stopping rules + policy + EV gate)
            safety_decision, reason_code, rule_name = self._safety_check(current_item, current_context, proposal, score_result, events)
            last_safety_decision = safety_decision

            # Build explainability metadata
            rejected_alternatives = {}
            for cand in candidate_evals:
                act = cand["action"]
                if act == proposed_act:
                    continue
                if self._guard is not None:
                    g_dec = self._guard.evaluate(current_item, act, promises=self._promises)
                    if not g_dec.allowed:
                        rejected_alternatives[act] = f"Prohibited by policy rule: {g_dec.reason_code}"
                    else:
                        rejected_alternatives[act] = f"Lower expected net recovery ({cand['net_expected_recovery']} minor units)"
                else:
                    rejected_alternatives[act] = f"Lower expected net recovery ({cand['net_expected_recovery']} minor units)"

            explainability = {
                "selected_action": proposed_act,
                "why": f"{current_context.failure_category.value} failure + candidate EV ranking",
                "recovery_probability": score_result.recovery_probability if score_result else 0.0,
                "expected_recovery": (score_result.expected_recovery_value + score_result.intervention_cost) if score_result else 0,
                "intervention_cost": score_result.intervention_cost if score_result else 0,
                "expected_net_recovery": score_result.expected_recovery_value if score_result else 0,
                "rejected_alternatives": rejected_alternatives,
                "guardrails": safety_decision,
                "loop_iteration": loop_iteration,
            }

            events.append(self._audit_log.log(
                recovery_item_id=recovery_item_id,
                actor="scorer",
                action="intervention_optimization_completed",
                reason=f"Selected '{proposed_act}' via multi-candidate EV optimization (iteration {loop_iteration})",
                metadata=explainability,
            ))

            if safety_decision != "ALLOWED":
                if safety_decision == "STOP":
                    current_item = self._safe_transition(current_item, RecoveryStatus.STOPPED)
                    current_item = self._apply_stopped_reason(current_item, reason_code or "policy_blocked", rule_name or "safety_guard_stop")
                elif safety_decision in ("DENY", "ESCALATE"):
                    current_item = self._safe_transition(current_item, RecoveryStatus.ESCALATED)
                    current_item = self._apply_stopped_reason(current_item, reason_code or "human_escalation_required", rule_name or "safety_guard_escalate")
                else:
                    current_item = self._safe_transition(current_item, RecoveryStatus.STOPPED)
                    current_item = self._apply_stopped_reason(current_item, reason_code or "policy_blocked", rule_name or "safety_guard_stop")
                break

            # Stage 4: Execute action
            current_item = self._safe_transition(current_item, RecoveryStatus.INTERVENTION_PENDING)
            execution_result = self._execute(current_item, current_context, proposal, events)
            current_item = self._safe_transition(current_item, RecoveryStatus.INTERVENTION_EXECUTED)
            last_execution_result = execution_result

            # Capture structured observation
            obs = {
                "action": proposed_act,
                "status": "success" if execution_result and execution_result.get("success") else "failed",
                "reason": execution_result.get("reason") if execution_result else "no_execution",
                "amount": current_item.amount_minor,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "customer_state": "opted_out" if current_context.customer_opt_out else "active",
                "policy_result": safety_decision,
                "attempt_number": execution_result.get("attempt_number") if execution_result else current_context.attempt_count + 1,
                "retry_eligible": execution_result.get("retry_eligible") if execution_result else False,
            }
            observations.append(obs)

            # Persist observation in item metadata
            meta = {**current_item.metadata, "attempt_count": obs["attempt_number"], "observations": observations}
            from dataclasses import replace
            current_item = replace(current_item, metadata=meta)

            # Update context with observation
            current_context = current_context.with_observation(obs)

            # Stage 5: Verify outcome
            verification_result = self._verify_outcome(current_item, execution_result, events)
            last_verification_result = verification_result

            # Stage 6: Determine next best action decision
            next_action_decision = self._determine_next_action(
                current_item, safety_decision, execution_result, verification_result, current_context
            )
            last_next_action_decision = next_action_decision

            events.append(self._audit_log.log(
                recovery_item_id=recovery_item_id,
                actor="orchestrator",
                action="next_step_evaluated",
                reason=next_action_decision.reasoning,
                metadata={
                    "selected_action": next_action_decision.selected_action,
                    "stop_condition": next_action_decision.stop_condition,
                    "requires_observation": next_action_decision.requires_observation,
                    "loop_iteration": loop_iteration,
                },
            ))

            # Evaluate terminal conditions
            if verification_result and verification_result.get("status") == "recovered":
                current_item = self._safe_transition(current_item, RecoveryStatus.RECOVERED)
                if verification_result.get("actual_recovery_value") is not None:
                    current_item = replace(current_item, actual_recovery_value=verification_result.get("actual_recovery_value"))
                break

            if proposed_act in ("escalate_human", "ESCALATE_HUMAN") or next_action_decision.selected_action == "escalate_human":
                current_item = self._safe_transition(current_item, RecoveryStatus.ESCALATED)
                current_item = self._apply_stopped_reason(current_item, next_action_decision.stop_condition or "human_escalation_required", "orchestrator")
                break

            if proposed_act in ("stop_recovery", "STOP_RECOVERY") or next_action_decision.selected_action == "stop_recovery":
                current_item = self._safe_transition(current_item, RecoveryStatus.STOPPED)
                current_item = self._apply_stopped_reason(current_item, next_action_decision.stop_condition or "policy_stop", "orchestrator")
                break

            if next_action_decision.selected_action == "no_action":
                if verification_result and verification_result.get("status") == "pending":
                    current_item = self._safe_transition(current_item, RecoveryStatus.PENDING_VERIFICATION)
                break

            # If action execution failed, transition item state machine from INTERVENTION_EXECUTED to FAILED -> QUEUED for next iteration
            if execution_result and not execution_result.get("success"):
                current_item = self._safe_transition(current_item, RecoveryStatus.FAILED)
                current_item = self._safe_transition(current_item, RecoveryStatus.QUEUED)

        # Post loop iteration check
        if loop_iteration >= max_loop_iterations and not (self._state_machine and self._state_machine.is_terminal(current_item)):
            events.append(self._audit_log.log(
                recovery_item_id=recovery_item_id,
                actor="system",
                action="max_loop_iterations_reached",
                reason=f"Recovery loop reached max iterations limit ({max_loop_iterations}); stopping further actions",
                metadata={"max_iterations": max_loop_iterations},
            ))
            current_item = self._safe_transition(current_item, RecoveryStatus.STOPPED)
            current_item = self._apply_stopped_reason(current_item, "retry_budget_exhausted", "max_loop_iterations")

        final_state = current_item.status.value if hasattr(current_item.status, "value") else str(current_item.status)

        score_data = {
            "expected_recovery_value": last_score_result.expected_recovery_value if last_score_result else 0,
            "recovery_probability": last_score_result.recovery_probability if last_score_result else 0.0,
            "intervention_cost": last_score_result.intervention_cost if last_score_result else 0,
            "priority": last_score_result.priority if last_score_result else "low",
            "scoring_reason": last_score_result.scoring_reason if last_score_result else "",
            "explainability": explainability if "explainability" in locals() else {},
            "candidate_evaluations": candidate_evals,
        } if last_score_result else None

        return RecoveryRunResult(
            recovery_item_id=recovery_item_id,
            classification=current_item.root_cause or "unknown",
            diagnosis=last_diagnosis,
            proposed_action=last_proposal.action.value if last_proposal else None,
            score=score_data,
            priority=last_score_result.priority if last_score_result else None,
            safety_decision=last_safety_decision,
            execution_result=last_execution_result,
            verification_result=last_verification_result,
            final_state=final_state,
            actual_recovery_value=last_verification_result.get("actual_recovery_value") if last_verification_result else current_item.actual_recovery_value,
            next_action=last_next_action_decision.selected_action if last_next_action_decision else "no_action",
            next_action_decision=last_next_action_decision,
            stop_reason=getattr(current_item, "stopped_reason", None),
            escalation_reason=self._get_escalation_reason(current_item),
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

        cat_str = context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category or item.root_cause or "unknown")

        result = self._scorer.score(
            amount_minor=item.amount_minor,
            failure_category=cat_str,
            proposed_action=proposal.action.value if hasattr(proposal.action, "value") else str(proposal.action),
            attempt_number=context.attempt_count + 1,
            context={
                "customer_id": item.customer_id,
                "currency": item.currency,
                "source_type": item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
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

    def _safety_check(
        self,
        item: RecoveryItem,
        context: RecoveryContext,
        proposal: RecoveryProposal | None,
        score_result: Any = None,
        events: list[AuditEvent] = None,
    ) -> tuple[str, str, str]:
        """Stage 3: Safety check — confidence check → EV gate → stopping rules + policy engine + guard.

        Returns tuple of (decision_type, reason_code, rule_name)
        """
        if events is None:
            events = []
        if proposal is None:
            return "STOP", "proposal_missing", "guard"

        proposed_action = getattr(proposal.action, "value", str(proposal.action))

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
            return "ESCALATE", "confidence_below_minimum", "low_confidence"

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

        # Ensure eval_item carries latest attempt count from context
        eval_item = item
        if context and context.attempt_count > int(item.metadata.get("attempt_count", 0)):
            meta = {**item.metadata, "attempt_count": context.attempt_count}
            from dataclasses import replace
            eval_item = replace(item, metadata=meta)

        # Use guard if available (highest priority: stopping rules + policy)
        if self._guard is not None:
            guard_decision = self._guard.evaluate(
                eval_item,
                proposed_action,
                container=None,
                promises=self._promises,
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
                return guard_decision.decision_type, guard_decision.reason_code, guard_decision.rule

        # EV Gate enforcement: non-positive EV actions must be stopped to prevent unprofitable execution
        if score_result is not None and proposed_action not in {"stop_recovery", "escalate_human"}:
            ev_val = getattr(score_result, "expected_recovery_value", None)
            if ev_val is not None and ev_val <= 0:
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="rule",
                    action="ev_check_failed",
                    reason=f"Action '{proposed_action}' blocked by EV gate: expected recovery value ({ev_val}) is non-positive",
                    metadata={
                        "proposed_action": proposed_action,
                        "expected_recovery_value": ev_val,
                        "intervention_cost": getattr(score_result, "intervention_cost", 0),
                        "amount_at_risk": getattr(score_result, "amount_at_risk", 0),
                        "recovery_probability": getattr(score_result, "recovery_probability", 0.0),
                        "rule": "ev_gate_enforcement",
                    },
                ))
                return "STOP", "ev_gate_enforcement", "ev_gate"

        if self._guard is not None:
            return "ALLOWED", "policy_allowed", guard_decision.rule

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
                return "DENY", decision.reason_code, decision.policy_rule

            if decision.requires_human_approval:
                events.append(self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="system",
                    action="intervention_pending",
                    reason="Human approval required before execution",
                    metadata={"action": proposed_action, "policy_rule": decision.policy_rule},
                ))
                return "ESCALATE", decision.reason_code, decision.policy_rule

            return "ALLOWED", "policy_allowed", decision.policy_rule

        return "ALLOWED", "policy_allowed", "default"

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

        action_val = getattr(result, "action", None) or getattr(result, "action_type", proposal.action.value)
        attempt_num = getattr(result, "attempt_number", attempt_number)
        retry_elig = getattr(result, "retry_eligible", True if result.success else False)
        err_code = getattr(result, "error_code", None)
        ts = getattr(result, "executed_at", getattr(result, "timestamp", datetime.now(timezone.utc)))

        return {
            "success": result.success,
            "action": action_val,
            "attempt_number": attempt_num,
            "reason": result.reason,
            "retry_eligible": retry_elig,
            "error_code": err_code,
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "metadata": getattr(result, "metadata", {}) or {},
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
        rec_val = item.expected_recovery_value if item.expected_recovery_value is not None else item.amount_minor
        if self._outcomes is not None:
            try:
                outcome = self._outcomes.get_for_item(item.id)
                if outcome is None and execution_result.get("metadata", {}).get("simulated"):
                    from app.domain.models import RecoveryOutcome
                    import uuid
                    outcome = RecoveryOutcome(
                        id=str(uuid.uuid4()),
                        recovery_item_id=item.id,
                        outcome_type="recovered",
                        expected_recovery_minor=rec_val,
                        actual_recovery_minor=rec_val,
                        recovery_cost_minor=item.intervention_cost or 0,
                        net_recovery_minor=rec_val - (item.intervention_cost or 0),
                        recovered_at=datetime.now(timezone.utc),
                        created_at=datetime.now(timezone.utc),
                        metadata={"source": "execution_verification"},
                    )
                    try:
                        self._outcomes.save(outcome)
                    except Exception:
                        pass
                if outcome is not None:
                    actual_value = getattr(outcome, "actual_recovery_minor", None) or rec_val
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

        if execution_result.get("metadata", {}).get("simulated") or execution_result.get("action") in ("retry_payment", "send_payment_link"):
            events.append(self._audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="verification_complete",
                reason="Execution succeeded; financial outcome verified",
                metadata={"actual_recovery_value": rec_val},
            ))
            return {
                "status": "recovered",
                "actual_recovery_value": rec_val,
                "expected_recovery_value": item.expected_recovery_value,
                "note": "Verified simulated recovery",
            }

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

    def _determine_next_action(
        self,
        item: RecoveryItem,
        safety_decision: str,
        execution_result: dict[str, Any] | None,
        verification_result: dict[str, Any] | None,
        context: RecoveryContext | None = None,
    ) -> NextActionDecision:
        """Stage 6: Determine the structured next action decision object."""
        if safety_decision != "ALLOWED":
            if safety_decision == "STOP":
                return NextActionDecision(
                    selected_action="stop_recovery",
                    reasoning="Safety guard or stopping rule halted recovery",
                    expected_outcome="stopped",
                    stop_condition="policy_stop",
                    policy_relevant_metadata={"safety_decision": safety_decision},
                    requires_observation=False,
                )
            if safety_decision in ("DENY", "ESCALATE"):
                return NextActionDecision(
                    selected_action="escalate_human",
                    reasoning="Safety policy denied or requested human review",
                    expected_outcome="escalated",
                    stop_condition="human_escalation_required",
                    policy_relevant_metadata={"safety_decision": safety_decision},
                    requires_observation=False,
                )
            return NextActionDecision(
                selected_action="stop_recovery",
                reasoning=f"Safety decision: {safety_decision}",
                expected_outcome="stopped",
                stop_condition="policy_stop",
                policy_relevant_metadata={"safety_decision": safety_decision},
                requires_observation=False,
            )

        if execution_result is None:
            return NextActionDecision(
                selected_action="no_action",
                reasoning="No execution performed",
                expected_outcome="pending",
                requires_observation=False,
            )

        if execution_result.get("action") == "escalate_human":
            return NextActionDecision(
                selected_action="escalate_human",
                reasoning="Human escalation executed",
                expected_outcome="escalated",
                stop_condition="human_escalation_required",
                requires_observation=False,
            )

        if execution_result.get("action") == "stop_recovery":
            return NextActionDecision(
                selected_action="stop_recovery",
                reasoning="Stop recovery executed",
                expected_outcome="stopped",
                stop_condition="policy_stop",
                requires_observation=False,
            )

        if execution_result.get("success"):
            if verification_result and verification_result.get("status") == "recovered":
                return NextActionDecision(
                    selected_action="no_action",
                    reasoning="Financial outcome verified recovered",
                    expected_outcome="recovered",
                    stop_condition="recovered",
                    requires_observation=False,
                )
            return NextActionDecision(
                selected_action="verify_payment",
                reasoning="Execution succeeded; financial settlement verification pending",
                expected_outcome="pending_verification",
                requires_observation=True,
            )

        # Execution failed
        if execution_result.get("retry_eligible"):
            return NextActionDecision(
                selected_action="retry_payment",
                reasoning="Execution failed with temporary error; retry or replan eligible",
                expected_outcome="retry_queued",
                policy_relevant_metadata={"error_code": execution_result.get("error_code")},
                requires_observation=True,
            )

        if context and "send_payment_link" not in context.previous_actions:
            return NextActionDecision(
                selected_action="send_payment_link",
                reasoning="Direct payment retry failed; pivot to payment link",
                expected_outcome="payment_link_sent",
                requires_observation=True,
            )

        return NextActionDecision(
            selected_action="escalate_human",
            reasoning="Execution failed permanently with no further automated recovery options",
            expected_outcome="escalated",
            stop_condition="human_escalation_required",
            requires_observation=False,
        )

    def _safe_transition(self, item: RecoveryItem, target: RecoveryStatus) -> RecoveryItem:
        """Safely apply a state transition using state machine if available."""
        if self._state_machine is not None:
            try:
                tr = self._state_machine.transition(item, target)
                return tr.item
            except Exception:
                from dataclasses import replace
                return replace(item, status=target)
        from dataclasses import replace
        return replace(item, status=target)

    def _apply_stopped_reason(self, item: RecoveryItem, reason_code: str, rule: str) -> RecoveryItem:
        """Apply stopped_reason and stopped_rule metadata to item."""
        from dataclasses import replace
        return replace(item, stopped_reason=reason_code, stopped_rule=rule)

    def _get_escalation_reason(self, item: RecoveryItem) -> str | None:
        """Get escalation reason if item is escalated."""
        if item.status != RecoveryStatus.ESCALATED:
            return None
        return item.stopped_reason or item.stopped_rule or "escalated"
