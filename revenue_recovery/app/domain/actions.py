"""Strongly-typed Action Contracts & Allowlisted Action Registry for RevPlug.

Ensures that model outputs are validated against a strict allowlist of registered
domain actions prior to policy checking and execution boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidAction(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    SEND_REMINDER = "send_reminder"
    OFFER_DISCOUNT = "offer_discount"
    ESCALATE_HUMAN = "escalate_human"
    STOP_RECOVERY = "stop_recovery"
    NO_ACTION = "no_action"
    WAIT = "wait"


@dataclass(frozen=True)
class ActionContract:
    name: str
    description: str
    cost_minor: int
    timeout_seconds: int
    retryable: bool
    is_idempotent: bool
    requires_human_approval: bool
    allowed_item_statuses: set[str] = field(default_factory=lambda: {"detected", "diagnosed", "queued", "failed", "pending_verification"})

    def validate_item_state(self, status: str) -> tuple[bool, str]:
        if status in {"recovered", "stopped"}:
            return False, f"Action '{self.name}' not allowed on terminal state '{status}'"
        if status not in self.allowed_item_statuses:
            return False, f"Action '{self.name}' not allowed on state '{status}'"
        return True, "valid"


class ActionRegistry:
    """Centralized allowlist registry for all valid domain actions."""

    _CONTRACTS: dict[str, ActionContract] = {
        ValidAction.RETRY_PAYMENT.value: ActionContract(
            name=ValidAction.RETRY_PAYMENT.value,
            description="Re-present card/token charge to payment gateway",
            cost_minor=500,
            timeout_seconds=30,
            retryable=True,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.SEND_PAYMENT_LINK.value: ActionContract(
            name=ValidAction.SEND_PAYMENT_LINK.value,
            description="Generate and dispatch hosted payment link via email/SMS",
            cost_minor=2500,
            timeout_seconds=60,
            retryable=True,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.SEND_REMINDER.value: ActionContract(
            name=ValidAction.SEND_REMINDER.value,
            description="Dispatch payment reminder notification",
            cost_minor=500,
            timeout_seconds=30,
            retryable=True,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.OFFER_DISCOUNT.value: ActionContract(
            name=ValidAction.OFFER_DISCOUNT.value,
            description="Offer incentive discount for immediate invoice/subscription settlement",
            cost_minor=5000,
            timeout_seconds=60,
            retryable=False,
            is_idempotent=True,
            requires_human_approval=True,
        ),
        ValidAction.ESCALATE_HUMAN.value: ActionContract(
            name=ValidAction.ESCALATE_HUMAN.value,
            description="Escalate recovery case to human operations queue",
            cost_minor=1000,
            timeout_seconds=10,
            retryable=False,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.STOP_RECOVERY.value: ActionContract(
            name=ValidAction.STOP_RECOVERY.value,
            description="Halt all automated recovery interventions permanently",
            cost_minor=0,
            timeout_seconds=5,
            retryable=False,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.NO_ACTION.value: ActionContract(
            name=ValidAction.NO_ACTION.value,
            description="Choose not to act during current evaluation window",
            cost_minor=0,
            timeout_seconds=5,
            retryable=True,
            is_idempotent=True,
            requires_human_approval=False,
        ),
        ValidAction.WAIT.value: ActionContract(
            name=ValidAction.WAIT.value,
            description="Delay intervention for specified observation window",
            cost_minor=0,
            timeout_seconds=5,
            retryable=True,
            is_idempotent=True,
            requires_human_approval=False,
        ),
    }

    @classmethod
    def get(cls, action_name: str) -> ActionContract | None:
        if not action_name:
            return None
        return cls._CONTRACTS.get(action_name.lower().strip())

    @classmethod
    def is_valid(cls, action_name: str) -> bool:
        return cls.get(action_name) is not None

    @classmethod
    def validate_or_fallback(cls, action_name: str, fallback: str = "no_action") -> tuple[str, bool]:
        """Validate action against registry. Return (action, is_valid)."""
        contract = cls.get(action_name)
        if contract is not None:
            return contract.name, True
        return fallback, False
