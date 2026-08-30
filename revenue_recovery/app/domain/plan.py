"""Explicit Recovery Plan Data Structure for Bounded Autonomous Orchestration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RecoveryPlan:
    """Explicit multi-step recovery plan with deterministic autonomy bounds."""

    case_id: str
    plan_id: str
    version: int = 1
    diagnosis: str = ""
    objective: str = "maximize_recovery_value"
    ordered_actions: list[str] = field(default_factory=list)
    current_step_index: int = 0
    max_steps: int = 3
    max_payment_retries: int = 3
    max_contact_attempts: int = 2
    max_total_cost_minor: int = 2000
    workflow_ttl_seconds: int = 86400
    stop_conditions: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def next_action(self) -> str | None:
        if self.current_step_index < len(self.ordered_actions):
            return self.ordered_actions[self.current_step_index]
        return None

    @property
    def ordered_steps(self) -> list[Any]:
        from dataclasses import dataclass
        @dataclass(frozen=True)
        class Step:
            action: str
        return [Step(action=a) for a in self.ordered_actions]

    def next_step(self) -> Any | None:
        if self.current_step_index < len(self.ordered_actions):
            from dataclasses import dataclass
            @dataclass(frozen=True)
            class Step:
                action: str
            return Step(action=self.ordered_actions[self.current_step_index])
        return None

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.workflow_ttl_seconds

    @property
    def is_completed(self) -> bool:
        return self.current_step_index >= len(self.ordered_actions) or self.current_step_index >= self.max_steps
