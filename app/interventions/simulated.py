from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class InterventionResult:
    success: bool
    message: str
    side_effects: dict[str, object] | None = None


class Intervention(Protocol):
    """Executes a proposed recovery action."""

    def execute(self, item: RecoveryItem, context: dict[str, object]) -> InterventionResult:
        ...


class SimulatedIntervention:
    """Safe no-op intervention for testing and local development.

    Does not call any external API, move money, or send messages.
    """

    def execute(self, item: RecoveryItem, context: dict[str, object]) -> InterventionResult:
        action = context.get("action", "unknown")
        return InterventionResult(
            success=True,
            message=f"Simulated execution of '{action}' for item {item.id}",
            side_effects={"simulated": True, "action": action},
        )
