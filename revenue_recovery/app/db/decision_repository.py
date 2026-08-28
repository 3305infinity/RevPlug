from __future__ import annotations

from typing import Protocol

from app.domain.proposals import RecoveryProposal


class RecoveryDecisionRepository(Protocol):
    """Persistence boundary for recovery decisions."""

    def save_decision(
        self,
        proposal: RecoveryProposal,
        *,
        item_id: str,
        agent_name: str,
        policy_allowed: bool | None = None,
        policy_rule: str | None = None,
        policy_reason: str | None = None,
        final_action: str | None = None,
    ) -> None:
        ...

    def list_by_recovery_item_id(self, item_id: str) -> list[dict]:
        ...


class InMemoryRecoveryDecisionRepository:
    """In-memory recovery decision repository for unit tests."""

    def __init__(self) -> None:
        self._decisions: list[dict] = []

    def save_decision(
        self,
        proposal: RecoveryProposal,
        *,
        item_id: str,
        agent_name: str,
        policy_allowed: bool | None = None,
        policy_rule: str | None = None,
        policy_reason: str | None = None,
        final_action: str | None = None,
    ) -> None:
        self._decisions.append({
            "recovery_item_id": item_id,
            "agent_name": agent_name,
            "model_name": proposal.model_name,
            "proposed_action": proposal.action.value,
            "reason": proposal.reason,
            "confidence": proposal.confidence,
            "customer_message": proposal.customer_message,
            "proposed_retry": proposal.proposed_retry,
            "policy_allowed": policy_allowed,
            "policy_rule": policy_rule,
            "policy_reason": policy_reason,
            "final_action": final_action,
        })

    def list_by_recovery_item_id(self, item_id: str) -> list[dict]:
        return [d for d in self._decisions if d["recovery_item_id"] == item_id]
