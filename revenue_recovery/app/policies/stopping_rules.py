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
        "active_promise_pauses_recovery",
        "checkout_already_converted",
        "subscription_cancelled",
        "invoice_paid",
        "invoice_disputed",
        "invoice_written_off",
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

        # Rule 1: payment_succeeded / invoice_paid / checkout_converted (highest priority)
        if self._is_payment_succeeded(item) or item.metadata.get("paid") is True or item.metadata.get("invoice_paid") is True or item.metadata.get("converted") is True or item.metadata.get("checkout_converted") is True:
            return StoppingDecision(
                should_stop=True,
                reason_code="payment_succeeded" if self._is_payment_succeeded(item) else ("invoice_paid" if item.metadata.get("paid") or item.metadata.get("invoice_paid") else "checkout_already_converted"),
                reason="Payment succeeded or converted externally. No further recovery actions permitted.",
                next_state=RecoveryStatus.RECOVERED,
                rule="payment_success_is_terminal",
            )

        # Rule 2: customer_opted_out
        if self._is_customer_opted_out(item) or item.metadata.get("opted_out") is True:
            return StoppingDecision(
                should_stop=True,
                reason_code="customer_opted_out",
                reason="Customer opted out of recovery communications",
                next_state=RecoveryStatus.STOPPED,
                rule="opt_out_is_terminal",
            )

        # Rule 2b: subscription_cancelled / invoice_disputed / invoice_written_off
        if item.metadata.get("cancelled") is True or item.metadata.get("subscription_status") == "cancelled":
            return StoppingDecision(
                should_stop=True,
                reason_code="subscription_cancelled",
                reason="Subscription cancelled by customer",
                next_state=RecoveryStatus.STOPPED,
                rule="subscription_cancelled",
            )
        if item.metadata.get("disputed") is True:
            return StoppingDecision(
                should_stop=True,
                reason_code="invoice_disputed",
                reason="Invoice disputed by customer",
                next_state=RecoveryStatus.STOPPED,
                rule="invoice_disputed",
            )
        if item.metadata.get("written_off") is True:
            return StoppingDecision(
                should_stop=True,
                reason_code="invoice_written_off",
                reason="Invoice written off",
                next_state=RecoveryStatus.STOPPED,
                rule="invoice_written_off",
            )

        # Rule 2c: active_promise
        promise_repo = promises or (getattr(container, "promises", None) if container is not None else None)
        if promise_repo is not None and self._has_active_promise(item, promises=promise_repo, now=now):
            return StoppingDecision(
                should_stop=True,
                reason_code="active_promise_pauses_recovery",
                reason="Active Promise-to-Pay exists; ordinary recovery actions paused",
                next_state=RecoveryStatus.STOPPED,
                rule="active_promise_pauses_recovery",
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
        return (
            item.customer_id in self._opted_out_customer_ids
            or item.metadata.get("opted_out") is True
            or item.metadata.get("customer_opted_out") is True
        )

    def _is_fraud_detected(self, item: RecoveryItem) -> bool:
        return (
            item.root_cause in {"fraud", "security_or_fraud"}
            or item.metadata.get("fraud_flag") is True
            or item.metadata.get("is_fraud") is True
        )

    def _is_retry_budget_exhausted(self, item: RecoveryItem) -> bool:
        attempt_count = self._get_attempt_count(item)
        return attempt_count >= self._max_attempts

    def _get_attempt_count(self, item: RecoveryItem) -> int:
        return int(item.metadata.get("attempt_count", 0))

    def _is_recovery_deadline_expired(self, item: RecoveryItem, *, now: datetime) -> bool:
        checkout_age = item.metadata.get("checkout_age_minutes")
        if checkout_age is not None and isinstance(checkout_age, (int, float)) and checkout_age > 10080:
            return True
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
        promise = promises.get_for_item(item.id) if promises is not None else None
        if promise is None and item.metadata.get("promise_status"):
            status = item.metadata.get("promise_status", "")
            due_at = item.metadata.get("promise_date")
            promise = {"status": status, "due_at": due_at}
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

    def _has_active_promise(
        self,
        item: RecoveryItem,
        *,
        promises: Any,
        now: datetime,
    ) -> bool:
        promise = promises.get_for_item(item.id) if promises is not None else None
        if promise is None and item.metadata.get("promise_status"):
            status = item.metadata.get("promise_status", "")
            due_at = item.metadata.get("promise_date")
            promise = {"status": status, "due_at": due_at}
        if promise is None:
            return False
        status = promise.get("status", "") if isinstance(promise, dict) else getattr(promise, "status", "")
        if status in {PromiseStatus.PROMISED.value, "active", "PROMISED"}:
            # Ensure it is not expired
            return not self._is_promise_expired(item, promises=promises, now=now)
        return False
