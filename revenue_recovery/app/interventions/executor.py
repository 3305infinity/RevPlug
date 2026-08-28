from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of a recovery execution attempt."""

    success: bool
    action: str
    attempt_number: int
    reason: str
    retry_eligible: bool = False
    error_code: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)


class RecoveryExecutor(Protocol):
    """Executes a policy-approved recovery action.

    The executor ONLY receives actions that have already been approved by
    the PolicyEngine. It must NEVER bypass or second-guess policy decisions.
    """

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        *,
        attempt_number: int,
        scenario: str | None = None,
    ) -> ExecutionResult:
        ...


class SimulatedRecoveryExecutor:
    """Deterministic simulated executor for testing and local development.

    Does NOT call any external API, move money, or send messages.

    Scenarios:
        "success"           → execution succeeds
        "temporary_failure" → execution fails but retry is eligible
        "permanent_failure" → execution fails and no retry is possible
        None                → defaults to "success"
    """

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        *,
        attempt_number: int,
        scenario: str | None = None,
    ) -> ExecutionResult:
        scenario = scenario or "success"

        if scenario == "success":
            return ExecutionResult(
                success=True,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated recovery succeeded for {item.id}",
                retry_eligible=False,
                metadata={"simulated": True, "scenario": scenario},
            )

        if scenario == "temporary_failure":
            return ExecutionResult(
                success=False,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated temporary failure for {item.id}; retry eligible",
                retry_eligible=True,
                error_code="temporary_failure",
                metadata={"simulated": True, "scenario": scenario},
            )

        if scenario == "permanent_failure":
            return ExecutionResult(
                success=False,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated permanent failure for {item.id}; no retry possible",
                retry_eligible=False,
                error_code="permanent_failure",
                metadata={"simulated": True, "scenario": scenario},
            )

        # Unknown scenario defaults to success (safe default).
        return ExecutionResult(
            success=True,
            action=action,
            attempt_number=attempt_number,
            reason=f"Simulated recovery succeeded for {item.id} (unknown scenario '{scenario}')",
            retry_eligible=False,
            metadata={"simulated": True, "scenario": scenario},
        )
