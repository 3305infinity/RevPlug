from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus
from app.domain.proposals import RecoveryAction


@dataclass(frozen=True, slots=True)
class RecoveryStep:
    """A single step in a multi-step recovery plan."""

    step_number: int
    action: str
    reason: str
    expected_value: int
    policy_status: str  # allowed, denied, pending
    attempt_number: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Bounded multi-step recovery plan.

    The AI can recommend the sequence, but deterministic policy decides
    whether each step is executable. Every step must pass:
        StoppingRules + PolicyEngine + retry budget + deadline + opt-out + fraud checks
    """

    recovery_item_id: str
    ordered_steps: list[RecoveryStep]
    max_attempts: int
    current_step: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def next_step(self) -> RecoveryStep | None:
        """Get the next step to execute, or None if plan is complete."""
        if self.current_step >= len(self.ordered_steps):
            return None
        return self.ordered_steps[self.current_step]

    def advance(self) -> RecoveryPlan:
        """Advance to the next step. Returns a new plan with current_step incremented."""
        next_step_num = self.current_step + 1
        if next_step_num > len(self.ordered_steps):
            return self
        return self.__class__(
            recovery_item_id=self.recovery_item_id,
            ordered_steps=self.ordered_steps,
            max_attempts=self.max_attempts,
            current_step=next_step_num,
            created_at=self.created_at,
            expires_at=self.expires_at,
            metadata=self.metadata,
        )

    def is_complete(self) -> bool:
        """Check if all steps have been attempted."""
        return self.current_step >= len(self.ordered_steps)


class DefaultRecoveryPlanner:
    """Deterministic recovery plan builder.

    Builds a bounded recovery sequence based on failure category and context.
    The sequence is constrained by safety rules at every step.
    """

    _DEFAULT_PLANS: dict[str, list[str]] = {
        "soft": ["retry_payment", "send_payment_link", "send_customer_message", "escalate_human"],
        "hard": ["send_payment_link", "send_customer_message", "escalate_human"],
        "fraud": ["stop_recovery"],
        "authentication_required": ["send_payment_link", "send_customer_message", "escalate_human"],
        "unknown": ["escalate_human"],
    }

    def build_plan(
        self,
        item: RecoveryItem,
        diagnosis_action: str,
        max_attempts: int = 3,
    ) -> RecoveryPlan:
        """Build a recovery plan for the given item and diagnosis."""
        root_cause = item.root_cause or "unknown"
        plan_actions = self._DEFAULT_PLANS.get(root_cause, ["escalate_human"])

        # Ensure diagnosis action is first if it's in the plan
        if diagnosis_action in plan_actions:
            plan_actions.remove(diagnosis_action)
            plan_actions.insert(0, diagnosis_action)

        # Build steps
        steps = []
        for i, action in enumerate(plan_actions[:max_attempts + 1]):
            step = RecoveryStep(
                step_number=i + 1,
                action=action,
                reason=f"Step {i + 1}: {action.replace('_', ' ').title()}",
                expected_value=item.expected_recovery_value or 0,
                policy_status="pending",
                attempt_number=i + 1,
            )
            steps.append(step)

        plan = RecoveryPlan(
            recovery_item_id=item.id,
            ordered_steps=steps,
            max_attempts=max_attempts,
            current_step=0,
            expires_at=item.due_at,
        )
        return plan

    def update_step_status(self, plan: RecoveryPlan, step_index: int, policy_status: str) -> RecoveryPlan:
        """Update the policy status of a specific step."""
        if step_index < 0 or step_index >= len(plan.ordered_steps):
            return plan

        step = plan.ordered_steps[step_index]
        updated_step = RecoveryStep(
            step_number=step.step_number,
            action=step.action,
            reason=step.reason,
            expected_value=step.expected_value,
            policy_status=policy_status,
            attempt_number=step.attempt_number,
            created_at=step.created_at,
            metadata=step.metadata,
        )

        new_steps = list(plan.ordered_steps)
        new_steps[step_index] = updated_step

        return plan.__class__(
            recovery_item_id=plan.recovery_item_id,
            ordered_steps=new_steps,
            max_attempts=plan.max_attempts,
            current_step=plan.current_step,
            created_at=plan.created_at,
            expires_at=plan.expires_at,
            metadata=plan.metadata,
        )
