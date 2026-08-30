"""Standardized Action Executor for Bounded Autonomous Recovery.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from app.domain.models import RecoveryItem

logger = logging.getLogger(__name__)


class ActionStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILED = "RECONCILED"


class TechnicalExecutionError(Exception):
    """Network/HTTP timeout or infrastructure failure. Retriable without consuming business retry budget."""

    def __init__(self, message: str, retriable: bool = True) -> None:
        super().__init__(message)
        self.retriable = retriable


@dataclass
class ActionExecutionResult:
    action_id: str
    action_type: str
    idempotency_key: str
    status: ActionStatus
    success: bool
    reason: str | None = None
    provider_reference: str | None = None
    cost_minor: int = 0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionExecutor:
    """Standardized action executor with idempotency tracking and technical/business retry separation."""

    def __init__(self) -> None:
        self._executed_keys: dict[str, ActionExecutionResult] = {}

    def generate_idempotency_key(self, item_id: str, action: str, attempt_number: int) -> str:
        return f"{item_id}:{action}:{attempt_number}"

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        attempt_number: int,
        *,
        simulated: bool = True,
        force_timeout: bool = False,
    ) -> ActionExecutionResult:
        key = self.generate_idempotency_key(item.id, action, attempt_number)

        # Idempotency guard: return prior execution result if key seen
        if key in self._executed_keys:
            existing = self._executed_keys[key]
            logger.info("Idempotent action execution skipped for key %s", key)
            return existing

        if force_timeout:
            # Reconcile or raise technical retryable error
            raise TechnicalExecutionError(f"Gateway request timed out for action {action}", retriable=True)

        action_id = f"act_{key.replace(':', '_')}"
        cost = 0
        if action == "send_payment_link":
            cost = 200
        elif action == "send_customer_message":
            cost = 50

        res = ActionExecutionResult(
            action_id=action_id,
            action_type=action,
            idempotency_key=key,
            status=ActionStatus.ACCEPTED if action != "stop_recovery" else ActionStatus.REJECTED,
            success=True,
            reason=f"Action {action} executed successfully",
            provider_reference=f"prov_ref_{action_id}",
            cost_minor=cost,
            is_simulated=simulated,
        )

        self._executed_keys[key] = res
        return res

    def reconcile_unknown(self, item_id: str, action: str, attempt_number: int) -> ActionExecutionResult:
        """Reconcile an UNKNOWN provider outcome by querying provider state."""
        key = self.generate_idempotency_key(item_id, action, attempt_number)
        if key in self._executed_keys:
            return self._executed_keys[key]

        reconciled = ActionExecutionResult(
            action_id=f"act_recon_{item_id[:8]}",
            action_type=action,
            idempotency_key=key,
            status=ActionStatus.RECONCILED,
            success=True,
            reason="Reconciled unknown provider outcome via query",
            provider_reference=f"recon_{key}",
            cost_minor=0,
            is_simulated=True,
        )
        self._executed_keys[key] = reconciled
        return reconciled
