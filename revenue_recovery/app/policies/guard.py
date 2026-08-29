from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.models import RecoveryItem, RecoveryStatus


@dataclass(frozen=True, slots=True)
class RecoveryGuardDecision:
    """Unified safety decision combining stopping rules and policy engine.

    This is the single decision object that controls whether recovery
    proceeds. It is used by the pipeline, webhook handler, and frontend.

    Fields:
        allowed: Whether the proposed action is permitted.
        decision_type: Human-readable classification: ALLOWED, STOP, DENY, ESCALATE.
        reason_code: Stable machine-readable reason (e.g. "retry_budget_exhausted").
        reason: Human-readable explanation.
        rule: The specific rule that produced this decision.
        next_state: The RecoveryStatus to transition to if this decision is applied.
        stopping_decision: The underlying StoppingDecision, if stopping rules matched.
        policy_decision: The underlying PolicyDecision, if policy was evaluated.
    """

    allowed: bool
    decision_type: str
    reason_code: str
    reason: str
    rule: str
    next_state: RecoveryStatus
    stopping_decision: object | None = None
    policy_decision: object | None = None


class RecoveryGuard(Protocol):
    """Evaluates whether a recovery action is allowed, combining stopping rules
    and policy engine into a single deterministic decision."""

    def evaluate(
        self,
        item: RecoveryItem,
        proposed_action: str,
        *,
        container=None,
        promises=None,
        now=None,
    ) -> RecoveryGuardDecision:
        ...


class DefaultRecoveryGuard:
    """Deterministic guard that evaluates stopping rules first, then policy engine.

    Flow:
        1. Evaluate stopping rules (highest priority)
        2. If not stopped, evaluate policy engine
        3. Return unified RecoveryGuardDecision
    """

    def __init__(
        self,
        stopping_rules: "StoppingRules",
        policy_engine: "PolicyEngine",
    ) -> None:
        self._stopping_rules = stopping_rules
        self._policy_engine = policy_engine

    def evaluate(
        self,
        item: RecoveryItem,
        proposed_action: str,
        *,
        container=None,
        promises=None,
        now=None,
    ) -> RecoveryGuardDecision:
        # Stage 1: stopping rules (highest priority, cannot be overridden)
        stopping = self._stopping_rules.evaluate(
            item,
            proposed_action=proposed_action,
            container=container,
            promises=promises,
            now=now,
        )
        if stopping.should_stop:
            return RecoveryGuardDecision(
                allowed=False,
                decision_type="STOP",
                reason_code=stopping.reason_code,
                reason=stopping.reason,
                rule=stopping.rule,
                next_state=stopping.next_state,
                stopping_decision=stopping,
            )

        # Stage 2: policy engine
        policy = self._policy_engine.evaluate(item, proposed_action)

        if not policy.allowed:
            return RecoveryGuardDecision(
                allowed=False,
                decision_type="DENY",
                reason_code=getattr(policy, "reason_code", policy.policy_rule),
                reason=policy.reason,
                rule=policy.policy_rule,
                next_state=RecoveryStatus.STOPPED,
                policy_decision=policy,
            )

        if policy.requires_human_approval:
            return RecoveryGuardDecision(
                allowed=False,
                decision_type="ESCALATE",
                reason_code=getattr(policy, "reason_code", policy.policy_rule),
                reason=policy.reason,
                rule=policy.policy_rule,
                next_state=RecoveryStatus.ESCALATED,
                policy_decision=policy,
            )

        return RecoveryGuardDecision(
            allowed=True,
            decision_type="ALLOWED",
            reason_code="policy_allowed",
            reason=policy.reason,
            rule=policy.policy_rule,
            next_state=item.status,
            policy_decision=policy,
        )
