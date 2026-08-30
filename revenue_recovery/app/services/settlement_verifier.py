"""Settlement Verifier — Domain-level authoritative financial settlement verification.

INVARIANT: Execution success != recovered revenue.
Actual recovery is recognized ONLY after authoritative settlement verification.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.audit.models import AuditLog
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus
from app.domain.transitions import DefaultStateMachine, RecoveryStateMachine

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SettlementEvent:
    """Authoritative settlement / payment outcome event."""

    event_id: str
    provider: str
    recovery_item_id: str
    success: bool
    actual_amount_minor: int
    currency: str = "INR"
    settled_at: datetime | None = None
    cost_minor: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SettlementVerificationResult:
    """Result of processing a settlement event through the verifier."""

    status: str  # "recovered" | "partially_recovered" | "failed" | "duplicate" | "ignored_terminal" | "quarantined"
    actual_recovery_minor: int
    item_id: str
    outcome_id: str | None = None
    reason: str = ""


class SettlementVerifier:
    """Authoritative verifier of financial settlement outcomes.

    Processes settlement evidence into verified RecoveryOutcome records
    and applies state transitions cleanly. Enforces idempotency and
    prevents over-statement or double-counting of recovered revenue.
    """

    def __init__(
        self,
        *,
        recovery_items: Any,  # RecoveryItemRepository
        outcomes: Any,         # RecoveryOutcomeRepository
        audit_log: AuditLog,
        state_machine: RecoveryStateMachine | None = None,
    ) -> None:
        self._recovery_items = recovery_items
        self._outcomes = outcomes
        self._audit_log = audit_log
        self._state_machine = state_machine or DefaultStateMachine()

    def process_settlement(self, event: SettlementEvent) -> SettlementVerificationResult:
        """Process an authoritative settlement event for a recovery item.

        Guarantees:
        1. Terminal state items (RECOVERED, STOPPED, ESCALATED) do NOT resurrect or double-count.
        2. Duplicate settlement event IDs return 'duplicate' idempotently.
        3. actual_recovery_minor comes strictly from event.actual_amount_minor.
        """
        # 1. Load recovery item
        item = self._recovery_items.get(event.recovery_item_id) if self._recovery_items is not None else None
        if item is None:
            logger.warning("Unmatched settlement event %s for item %s", event.event_id, event.recovery_item_id)
            self._audit_log.log(
                recovery_item_id=event.recovery_item_id,
                actor="settlement_verifier",
                action="settlement_unmatched",
                reason=f"Recovery item '{event.recovery_item_id}' not found",
                metadata={"event_id": event.event_id, "provider": event.provider},
            )
            return SettlementVerificationResult(
                status="quarantined",
                actual_recovery_minor=0,
                item_id=event.recovery_item_id,
                reason="Item not found",
            )

        # 2. Check terminal state invariant
        if item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}:
            self._audit_log.log(
                recovery_item_id=item.id,
                actor="settlement_verifier",
                action="settlement_ignored_terminal",
                reason=f"Item already in terminal state {item.status.value}",
                metadata={"event_id": event.event_id, "status": item.status.value},
            )
            return SettlementVerificationResult(
                status="ignored_terminal",
                actual_recovery_minor=0,
                item_id=item.id,
                reason=f"Item in terminal state {item.status.value}",
            )

        # 3. Idempotency check: has an outcome already been recorded for this item or event?
        existing_outcome = None
        if self._outcomes is not None:
            if hasattr(self._outcomes, "get_for_item"):
                existing_outcome = self._outcomes.get_for_item(item.id)

        if existing_outcome is not None:
            existing_event_id = (existing_outcome.metadata or {}).get("event_id")
            if existing_event_id == event.event_id or existing_outcome.actual_recovery_minor is not None:
                self._audit_log.log(
                    recovery_item_id=item.id,
                    actor="settlement_verifier",
                    action="settlement_duplicate",
                    reason=f"Duplicate settlement event {event.event_id} ignored",
                    metadata={"event_id": event.event_id},
                )
                return SettlementVerificationResult(
                    status="duplicate",
                    actual_recovery_minor=existing_outcome.actual_recovery_minor or 0,
                    item_id=item.id,
                    outcome_id=existing_outcome.id,
                    reason="Duplicate settlement event",
                )

        # 4. Verify settlement outcome
        if event.success and event.actual_amount_minor > 0:
            # Clamped actual recovery: cannot exceed item amount at risk
            actual_amount = min(event.actual_amount_minor, item.amount_minor)
            cost_amount = event.cost_minor if event.cost_minor > 0 else (item.intervention_cost or 0)
            is_partial = actual_amount < item.amount_minor

            outcome_type = "partially_recovered" if is_partial else "recovered"
            target_status = RecoveryStatus.RECOVERED  # Partial or full recovery moves item to RECOVERED

            outcome = RecoveryOutcome(
                id=str(uuid.uuid4()),
                recovery_item_id=item.id,
                outcome_type=outcome_type,
                expected_recovery_minor=item.expected_recovery_value or item.amount_minor,
                actual_recovery_minor=actual_amount,
                recovery_cost_minor=cost_amount,
                net_recovery_minor=actual_amount - cost_amount,
                recovered_at=event.settled_at or datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                metadata={
                    "provider": event.provider,
                    "event_id": event.event_id,
                    "source": "settlement_verifier",
                    "amount_at_risk": item.amount_minor,
                    **event.metadata,
                },
            )

            if self._outcomes is not None:
                self._outcomes.save(outcome)

            # Apply state transition
            if item.status == RecoveryStatus.DETECTED:
                tr_pv = self._state_machine.transition(item, RecoveryStatus.PENDING_VERIFICATION)
                if tr_pv.applied:
                    item = tr_pv.item
            tr = self._state_machine.transition(item, target_status)
            if tr.applied:
                updated_item = tr.item.__class__(
                    id=tr.item.id,
                    source_type=tr.item.source_type,
                    external_id=tr.item.external_id,
                    customer_id=tr.item.customer_id,
                    amount_minor=tr.item.amount_minor,
                    currency=tr.item.currency,
                    created_at=tr.item.created_at,
                    due_at=tr.item.due_at,
                    status=tr.item.status,
                    root_cause=tr.item.root_cause,
                    recovery_probability=tr.item.recovery_probability,
                    expected_recovery_value=tr.item.expected_recovery_value,
                    intervention_cost=tr.item.intervention_cost,
                    failure_category=tr.item.failure_category,
                    provider=tr.item.provider,
                    provider_event_id=tr.item.provider_event_id,
                    actual_recovery_value=actual_amount,
                    recovery_status=tr.item.recovery_status,
                    score_version=tr.item.score_version,
                    scoring_reason=tr.item.scoring_reason,
                    priority=tr.item.priority,
                    stopped_reason=tr.item.stopped_reason,
                    stopped_rule=tr.item.stopped_rule,
                    metadata={**tr.item.metadata, "settled_at": (event.settled_at or datetime.now(timezone.utc)).isoformat()},
                )
                if self._recovery_items is not None:
                    self._recovery_items.save(updated_item)

            self._audit_log.log(
                recovery_item_id=item.id,
                actor="settlement_verifier",
                action="settlement_verified",
                reason=f"Settlement confirmed: {actual_amount} paise recovered ({outcome_type})",
                metadata={
                    "event_id": event.event_id,
                    "actual_recovery_minor": actual_amount,
                    "outcome_type": outcome_type,
                    "cost_minor": cost_amount,
                },
            )

            return SettlementVerificationResult(
                status=outcome_type,
                actual_recovery_minor=actual_amount,
                item_id=item.id,
                outcome_id=outcome.id,
                reason=f"Verified recovery of {actual_amount} paise",
            )
        else:
            # Settlement failed / refused
            tr = self._state_machine.transition(item, RecoveryStatus.FAILED)
            if tr.applied and self._recovery_items is not None:
                self._recovery_items.save(tr.item)

            self._audit_log.log(
                recovery_item_id=item.id,
                actor="settlement_verifier",
                action="settlement_failed",
                reason=f"Settlement failed for event {event.event_id}",
                metadata={"event_id": event.event_id},
            )

            return SettlementVerificationResult(
                status="failed",
                actual_recovery_minor=0,
                item_id=item.id,
                reason="Settlement failed",
            )
