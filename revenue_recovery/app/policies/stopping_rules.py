from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import Promise, PromiseStatus, RecoveryItem, RecoveryStatus

if TYPE_CHECKING:
    from app.db.container import PersistenceContainer


@dataclass(frozen=True, slots=True)
class StoppingDecision:
    should_stop: bool
    reason_code: str
    reason: str
    next_state: RecoveryStatus
    rule: str


class StoppingRules:
    """Centralized deterministic stopping rules for recovery workflows.

    Evaluates whether recovery must halt based on:
    - Payment success
    - Customer opt-out
    - Promise expiry
    - Retry budget exhaustion
    - Recovery deadline expiry
    - Fraud detection
    - Policy blocking (delegated)

    Reason codes are stable and machine-readable for audit events,
    analytics, and frontend display.
    """

    STOP_REASON_CODES = frozenset({
        "payment_succeeded",
        "customer_opted_out",
        "promise_expired",
        "retry_budget_exhausted",
        "recovery_deadline_expired",
        "fraud_detected",
        "policy_blocked",
        "terminal_state_reached",
    })

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        opted_out_customer_ids: frozenset[str] = frozenset(),
    ) -> None:
        if max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        self._max_attempts = max_attempts
        self._opted_out_customer_ids = opted_out_customer_ids

    def evaluate(
        self,
        item: RecoveryItem,
        *,
        proposed_action: str = "retry_payment",
        container: "PersistenceContainer | None" = None,
        promises: "Any | None" = None,
        now: datetime | None = None,
    ) -> StoppingDecision:
        """Evaluate whether recovery must stop for this item.

        Returns the first matching stopping reason in priority order.
        Idempotent: calling repeatedly on the same item yields identical results.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Terminal states are always absorbing
        if item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.ESCALATED, RecoveryStatus.STOPPED}:
            return StoppingDecision(
                should_stop=True,
                reason_code="terminal_state_reached",
                reason=f"Case is in terminal state: {item.status.value}",
                next_state=item.status,
                rule="terminal_state_absorbing",
            )

        # Rule 1: payment_succeeded (highest priority)
        if self._is_payment_succeeded(item):
            return StoppingDecision(
                should_stop=True,
                reason_code="payment_succeeded",
                reason="Payment succeeded externally. No further recovery actions permitted.",
                next_state=RecoveryStatus.RECOVERED,
                rule="payment_success_is_terminal",
            )

        # Rule 2: customer_opted_out
        if self._is_customer_opted_out(item):
            return StoppingDecision(
                should_stop=True,
                reason_code="customer_opted_out",
                reason="Customer opted out of recovery communications",
                next_state=RecoveryStatus.STOPPED,
                rule="opt_out_is_terminal",
            )

        # Rule 3: fraud_detected
        if self._is_fraud_detected(item):
            return StoppingDecision(
                should_stop=True,
                reason_code="fraud_detected",
                reason="Fraud failure category blocks automated recovery",
                next_state=RecoveryStatus.STOPPED,
                rule="fraud_cannot_retry",
            )

        # Rule 4: retry_budget_exhausted
        if proposed_action == "retry_payment" and self._is_retry_budget_exhausted(item):
            return StoppingDecision(
                should_stop=True,
                reason_code="retry_budget_exhausted",
                reason=f"Maximum retry attempts reached ({self._get_attempt_count(item)}/{self._max_attempts})",
                next_state=RecoveryStatus.STOPPED,
                rule="retry_limit",
            )

        # Rule 5: recovery_deadline_expired
        if self._is_recovery_deadline_expired(item, now=now):
            return StoppingDecision(
                should_stop=True,
                reason_code="recovery_deadline_expired",
                reason="Recovery deadline has passed",
                next_state=RecoveryStatus.STOPPED,
                rule="deadline_expiry",
            )

        # Rule 6: promise_expired
        promise_repo = promises or (getattr(container, "promises", None) if container is not None else None)
        if promise_repo is not None and self._is_promise_expired(item, promises=promise_repo, now=now):
            return StoppingDecision(
                should_stop=True,
                reason_code="promise_expired",
                reason="Promise-to-pay has expired without fulfillment",
                next_state=RecoveryStatus.STOPPED,
                rule="promise_expiry",
            )

        # No stopping condition matched
        return StoppingDecision(
            should_stop=False,
            reason_code="none",
            reason="No stopping condition matched; recovery may proceed under policy",
            next_state=item.status,
            rule="no_stop_condition",
        )

    def _is_payment_succeeded(self, item: RecoveryItem) -> bool:
        return item.metadata.get("payment_succeeded") is True

    def _is_customer_opted_out(self, item: RecoveryItem) -> bool:
        return item.customer_id in self._opted_out_customer_ids

    def _is_fraud_detected(self, item: RecoveryItem) -> bool:
        return item.root_cause in {"fraud", "security_or_fraud"}

    def _is_retry_budget_exhausted(self, item: RecoveryItem) -> bool:
        attempt_count = self._get_attempt_count(item)
        return attempt_count >= self._max_attempts

    def _get_attempt_count(self, item: RecoveryItem) -> int:
        return int(item.metadata.get("attempt_count", 0))

    def _is_recovery_deadline_expired(self, item: RecoveryItem, *, now: datetime) -> bool:
        due_at = item.due_at
        if due_at is None:
            return False
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        return now > due_at

    def _is_promise_expired(
        self,
        item: RecoveryItem,
        *,
        promises: Any,
        now: datetime,
    ) -> bool:
        if promises is None:
            return False
        promise = promises.get_for_item(item.id)
        if promise is None:
            return False
        if isinstance(promise, dict):
            status = promise.get("status", "")
            due_at = promise.get("due_at") or promise.get("promised_date")
        else:
            status = promise.status
            due_at = getattr(promise, "due_at", None) or getattr(promise, "promised_date", None)
        if status in {PromiseStatus.FULFILLED.value, PromiseStatus.CANCELLED.value}:
            return False
        if due_at is None:
            return False
        if isinstance(due_at, str):
            due_at = datetime.fromisoformat(due_at)
        if isinstance(due_at, datetime):
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            return now > due_at
        if isinstance(due_at, date) and not isinstance(due_at, datetime):
            return now.date() > due_at
        return False
