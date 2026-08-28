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
        audit_events: list[AuditEvent] = []

        # Audit: context created
        audit_events.append(self._audit_log.log(
            recovery_item_id=context.item_id,
            actor="system",
            action="agent_context_created",
            reason="Recovery context built for agent",
            metadata={
                "category": context.failure_category.value,
                "attempt_count": context.attempt_count,
            },
        ))

        # Stage 1: Agent proposes
        proposal = self._agent.propose(context)
        audit_events.append(self._audit_log.log(
            recovery_item_id=context.item_id,
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
                    "action": proposal.action.value,
                    "error": str(exc),
                },
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
                "proposed_action": proposal.action.value,
                "allowed": policy_decision.allowed,
                "requires_human_approval": policy_decision.requires_human_approval,
                "policy_rule": policy_decision.policy_rule,
            },
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
    """
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType

    return RecoveryItem(
        id=context.item_id or "agent-context",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="",
        customer_id="razorpay_customer",
        amount_minor=context.amount_minor,
        currency=context.currency,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        status=RecoveryStatus.QUEUED,
        root_cause=context.failure_category.value,
        recovery_probability=context.expected_recovery_value / context.amount_minor if context.amount_minor > 0 and context.expected_recovery_value else None,
        metadata={"attempt_count": context.attempt_count},
    )
