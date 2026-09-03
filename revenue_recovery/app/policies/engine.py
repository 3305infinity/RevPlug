from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    requires_human_approval: bool
    reason: str
    policy_rule: str
    action: str
    reason_code: str = ""
    decision_type: str = ""

    def __post_init__(self) -> None:
        if not self.reason_code:
            object.__setattr__(self, "reason_code", self.policy_rule)
        if not self.decision_type:
            if not self.allowed:
                object.__setattr__(self, "decision_type", "DENY")
            elif self.requires_human_approval:
                object.__setattr__(self, "decision_type", "ESCALATE")
            else:
                object.__setattr__(self, "decision_type", "ALLOWED")


class PolicyEngine(Protocol):
    """Decides whether a proposed intervention is permitted."""

    def evaluate(self, item: RecoveryItem, proposed_action: str) -> PolicyDecision:
        ...


class InterventionPolicy:
    """Deterministic policy engine with basic safety rules.

    Rules implemented:
    1. Hard / fraud / authentication-type failures cannot be automatically retried.
    2. Retry count cannot exceed a configurable maximum.
    3. Any discount above a configurable autonomous limit requires human approval.
    4. An opted-out customer cannot receive an outbound communication.
    5. Unknown / unsafe actions are blocked by default.
    """

    def __init__(
        self,
        *,
        max_retry_attempts: int = 3,
        autonomous_discount_minor: int = 0,
        opted_out_customer_ids: frozenset[str] = frozenset(),
    ) -> None:
        if max_retry_attempts < 0:
            raise ValueError("max_retry_attempts must be non-negative")
        if autonomous_discount_minor < 0:
            raise ValueError("autonomous_discount_minor must be non-negative")
        self._max_retry_attempts = max_retry_attempts
        self._autonomous_discount_minor = autonomous_discount_minor
        self._opted_out_customer_ids = opted_out_customer_ids

    def evaluate(self, item: RecoveryItem, proposed_action: str) -> PolicyDecision:
        if proposed_action != "stop_recovery" and item.status.value in {"recovered", "stopped"}:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason=f"Recovery item is in terminal state '{item.status.value}'",
                policy_rule="terminal_state_block",
                action=proposed_action,
                reason_code="terminal_state",
            )

        if proposed_action != "stop_recovery" and item.customer_id in self._opted_out_customer_ids:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason="Customer has opted out of automated communication",
                policy_rule="opt_out_block",
                action=proposed_action,
                reason_code="customer_opted_out",
            )

        if proposed_action == "retry_payment" and item.metadata.get("systemic_suppress"):
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason="Systemic payment segment outage detected — individual retries suppressed in favor of WAIT",
                policy_rule="systemic_incident_suppress",
                action=proposed_action,
                reason_code="systemic_incident_active",
            )

        if proposed_action == "retry_payment":
            return self._evaluate_retry(item)
        if proposed_action == "send_discount":
            return self._evaluate_discount(item)
        if proposed_action in {"send_reminder", "send_customer_message", "send_payment_link", "alternate_channel", "promise_to_pay", "escalate_human"}:
            return self._evaluate_outbound(item, proposed_action)
        if proposed_action == "stop_recovery":
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason="Stopping recovery is always permitted",
                policy_rule="allow_stop",
                action=proposed_action,
                reason_code="policy_allowed",
            )

        return PolicyDecision(
            allowed=False,
            requires_human_approval=False,
            reason=f"Unknown or unsafe action: {proposed_action}",
            policy_rule="default_deny",
            action=proposed_action,
            reason_code="policy_blocked",
        )

    def _evaluate_retry(self, item: RecoveryItem) -> PolicyDecision:
        attempt_count = int(item.metadata.get("attempt_count", 0))
        if attempt_count >= self._max_retry_attempts:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Retry budget exhausted ({attempt_count}/{self._max_retry_attempts})",
                policy_rule="retry_limit",
                action="retry_payment",
                reason_code="retry_budget_exhausted",
            )

        root_cause = (item.root_cause or "").lower()
        source_type = (item.metadata.get("source_type") or "").lower()
        blocked_causes = {"hard", "hard_decline", "fraud", "authentication_required", "security_or_fraud"}
        if root_cause in blocked_causes:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Root cause '{item.root_cause}' blocks automatic retry",
                policy_rule="block_hard_failure",
                action="retry_payment",
                reason_code="fraud_detected" if root_cause in {"fraud", "security_or_fraud"} else "policy_blocked",
            )

        if source_type == "mandate_failure" or root_cause == "mandate_failed":
            rep_count = int(item.metadata.get("representation_count", 0))
            max_reps = int(item.metadata.get("max_representations", 3))
            if rep_count >= max_reps:
                return PolicyDecision(
                    allowed=False,
                    requires_human_approval=True,
                    reason=f"Mandate representation budget exhausted ({rep_count}/{max_reps}). Re-registration required.",
                    policy_rule="mandate_representation_limit",
                    action="retry_payment",
                    reason_code="mandate_exhausted",
                )

        return PolicyDecision(
            allowed=True,
            requires_human_approval=False,
            reason="Retry is within budget and root cause permits it",
            policy_rule="allow_retry",
            action="retry_payment",
        )

    def _evaluate_discount(self, item: RecoveryItem) -> PolicyDecision:
        discount_minor = int(item.metadata.get("discount_minor", 0))
        if discount_minor > self._autonomous_discount_minor:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Discount {discount_minor} exceeds autonomous limit {self._autonomous_discount_minor}",
                policy_rule="discount_ceiling",
                action="send_discount",
                reason_code="policy_blocked",
            )
        return PolicyDecision(
            allowed=True,
            requires_human_approval=False,
            reason="Discount is within autonomous limit",
            policy_rule="allow_discount",
            action="send_discount",
            reason_code="policy_allowed",
        )

    def _evaluate_outbound(self, item: RecoveryItem, proposed_action: str) -> PolicyDecision:
        recent_contacts = int(item.metadata.get("recent_contact_count", 0))
        if recent_contacts >= 2:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason="Contact frequency limit reached (2 contacts within 24h window)",
                policy_rule="contact_frequency_limit",
                action=proposed_action,
                reason_code="CONTACT_FREQUENCY_LIMIT",
            )

        attempt_count = int(item.metadata.get("contact_attempt_count", 0))
        max_contacts = int(item.metadata.get("max_contacts", 5))
        if attempt_count >= max_contacts:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Contact budget exhausted ({attempt_count}/{max_contacts})",
                policy_rule="contact_limit",
                action=proposed_action,
                reason_code="retry_budget_exhausted",
            )
        return PolicyDecision(
            allowed=True,
            requires_human_approval=False,
            reason="Contact is within budget",
            policy_rule="allow_outbound",
            action=proposed_action,
            reason_code="policy_allowed",
        )
