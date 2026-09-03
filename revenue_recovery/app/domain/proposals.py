from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class RecoveryAction(StrEnum):
    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    SEND_REMINDER = "send_reminder"
    SEND_CUSTOMER_MESSAGE = "send_customer_message"
    ALTERNATE_CHANNEL = "alternate_channel"
    PROMISE_TO_PAY = "promise_to_pay"
    ESCALATE_HUMAN = "escalate_human"
    STOP_RECOVERY = "stop_recovery"
    NO_ACTION = "no_action"
    WAIT = "wait"


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """Ranked candidate action with EV breakdown."""

    action: RecoveryAction
    recovery_probability: float
    intervention_cost: int
    gross_expected_recovery: int
    net_expected_recovery: int
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value if isinstance(self.action, RecoveryAction) else str(self.action),
            "recovery_probability": self.recovery_probability,
            "intervention_cost": self.intervention_cost,
            "gross_expected_recovery": self.gross_expected_recovery,
            "net_expected_recovery": self.net_expected_recovery,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class RecoveryProposal:
    """Structured proposal produced by a RecoveryDecisionAgent.

    This is a PROPOSAL only. It must pass validation and policy evaluation
    before any action is executed.
    """

    action: RecoveryAction
    reason: str
    confidence: float
    customer_message: str | None = None
    proposed_retry: bool = False
    retry_metadata: dict[str, Any] = field(default_factory=dict)
    model_name: str = "mock"
    evidence: dict[str, Any] = field(default_factory=dict)
    diagnosis: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    candidates: list[CandidateScore] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.action, str) and not isinstance(self.action, RecoveryAction):
            try:
                object.__setattr__(self, "action", RecoveryAction(self.action))
            except ValueError:
                pass  # String action retained for ProposalValidator to reject with ProposalValidationError
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason is required")
        if len(self.reason) > 2000:
            raise ValueError("reason must be 2000 characters or fewer")
        if self.customer_message and len(self.customer_message) > 4000:
            raise ValueError("customer_message must be 4000 characters or fewer")
