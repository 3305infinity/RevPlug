from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.validator import ProposalValidationError, ProposalValidator
from app.audit.models import AuditEvent, AuditLog
from app.domain.context import RecoveryContext
from app.domain.proposals import RecoveryProposal
from app.policies.engine import PolicyDecision, PolicyEngine


@dataclass(frozen=True, slots=True)
class AgentOrchestratorResult:
    """Result of the agent → validator → policy pipeline."""

    proposal: RecoveryProposal
    policy_decision: PolicyDecision
    audit_events: list[AuditEvent]
    executed: bool = False


class RecoveryAgentOrchestrator:
    """Orchestrates the agentic recovery decision flow.

    Flow:
        agent.propose()
            ↓
        validator.validate()
            ↓
        policy_engine.evaluate()
            ↓
        (if allowed) execution boundary

    The agent NEVER bypasses the policy engine.
    """

    def __init__(
        self,
        *,
        agent: RecoveryDecisionAgent | None = None,
        policy_engine: PolicyEngine,
        audit_log: AuditLog,
        validator: ProposalValidator | None = None,
    ) -> None:
        self._agent = agent or MockRecoveryDecisionAgent()
        self._policy_engine = policy_engine
        self._audit_log = audit_log
        self._validator = validator or ProposalValidator()

    def decide(self, context: RecoveryContext) -> AgentOrchestratorResult:
        """Run the full agent → validator → policy pipeline."""
        from app.audit.models import EventType
        from app.services.trace_service import compute_context_hash

        audit_events: list[AuditEvent] = []
        c_hash = compute_context_hash(context)

        # Audit: context created
        audit_events.append(self._audit_log.log(
            recovery_item_id=context.item_id,
            actor="system",
            action="agent_context_created",
            reason="Recovery context captured for agent",
            metadata={
                "event_type": EventType.CONTEXT_CAPTURED,
                "category": context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category),
                "attempt_count": context.attempt_count,
                "context_hash": c_hash,
            },
            event_type=EventType.CONTEXT_CAPTURED,
            context_hash=c_hash,
        ))

        # Stage 1: Agent proposes
        proposal = self._agent.propose(context)
        last_tr = getattr(self._agent, "last_trace", None)
        fallback_used = getattr(last_tr, "fallback_used", False) if last_tr else False

        audit_events.append(self._audit_log.log(
            recovery_item_id=context.item_id,
            actor="ai" if getattr(proposal, "model_name", "") not in ("mock", "deterministic-mock", "deterministic-rules") else "system",
            action="agent_proposal_created",
            reason=f"AI proposed {proposal.action.value}" if not fallback_used else f"Fallback proposed {proposal.action.value}",
            metadata={
                "event_type": EventType.AI_RECOMMENDATION_CREATED,
                "action": proposal.action.value,
                "confidence": proposal.confidence,
                "model": proposal.model_name,
                "agent": self._agent.name,
                "fallback_used": fallback_used,
                "context_hash": c_hash,
            },
            event_type=EventType.AI_RECOMMENDATION_CREATED,
            source=proposal.model_name,
            context_hash=c_hash,
        ))

        if fallback_used:
            audit_events.append(self._audit_log.log(
                recovery_item_id=context.item_id,
                actor="system",
                action="fallback_triggered",
                reason=getattr(last_tr, "validation_error", "AI fallback triggered"),
                metadata={"event_type": EventType.FALLBACK_USED, "context_hash": c_hash},
                event_type=EventType.FALLBACK_USED,
                context_hash=c_hash,
            ))

        # Stage 2: Validate proposal
        try:
            self._validator.validate(proposal, context)
        except ProposalValidationError as exc:
            audit_events.append(self._audit_log.log(
                recovery_item_id=context.item_id,
                actor="system",
                action="agent_proposal_rejected",
                reason=str(exc),
                metadata={
                    "event_type": EventType.APPROVAL_REJECTED,
                    "action": proposal.action.value,
                    "error": str(exc),
                    "reason_code": "proposal_validation_failed",
                },
                event_type=EventType.APPROVAL_REJECTED,
                reason_code="proposal_validation_failed",
            ))
            # Fail closed: return a denied policy decision
            return AgentOrchestratorResult(
                proposal=proposal,
                policy_decision=PolicyDecision(
                    allowed=False,
                    requires_human_approval=True,
                    reason=f"Proposal validation failed: {exc}",
                    policy_rule="proposal_validation_failed",
                    action=proposal.action.value,
                ),
                audit_events=audit_events,
            )

        # Stage 3: Policy evaluation
        policy_decision = self._policy_engine.evaluate(
            _make_item_stub(context), proposal.action.value
        )
        audit_events.append(self._audit_log.log(
            recovery_item_id=context.item_id,
            actor="rule",
            action="policy_evaluate",
            reason=policy_decision.reason,
            metadata={
                "event_type": EventType.POLICY_EVALUATED,
                "source": "deterministic_policy",
                "proposed_action": proposal.action.value,
                "allowed": policy_decision.allowed,
                "requires_human_approval": policy_decision.requires_human_approval,
                "policy_rule": policy_decision.policy_rule,
                "reason_code": policy_decision.reason_code or policy_decision.policy_rule,
            },
            event_type=EventType.POLICY_EVALUATED,
            source="deterministic_policy",
            reason_code=policy_decision.reason_code or policy_decision.policy_rule,
        ))

        return AgentOrchestratorResult(
            proposal=proposal,
            policy_decision=policy_decision,
            audit_events=audit_events,
        )


def _make_item_stub(context: RecoveryContext):
    """Create a minimal RecoveryItem-like object for policy evaluation.

    The existing PolicyEngine.evaluate() expects a RecoveryItem. We build
    a lightweight stub from the context for this purpose.

    IMPORTANT: customer_id MUST be propagated from context so that the
    opted_out_customer_ids check in InterventionPolicy fires correctly.
    """
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType

    return RecoveryItem(
        id=context.item_id or "agent-context",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="",
        customer_id=context.customer_id or "razorpay_customer",
        amount_minor=context.amount_minor,
        currency=context.currency,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause=context.failure_category.value,
        recovery_probability=context.expected_recovery_value / context.amount_minor if context.amount_minor > 0 and context.expected_recovery_value else None,
        metadata={"attempt_count": context.attempt_count},
    )
