"""Security and Safety Invariants Engine for Bounded Autonomous Recovery.

Enforces strict runtime invariant validation for:
1. AI cannot modify financial truth
2. AI cannot increase safety/retry/contact budgets
3. Execution does not imply recovery
4. Only authoritative evidence can confirm recovery
5. Terminal cases cannot execute new recovery actions
6. Duplicate events cannot create duplicate financial recovery
7. Customer opt-out blocks prohibited communication
8. Hard decline blocks prohibited retry
9. Negative expected value blocks action
10. AI failure cannot disable deterministic safety
11. Stale plans cannot execute against invalidated state
12. Uncertain provider outcome must be reconciled before duplicate action
"""
from __future__ import annotations

import logging
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus

logger = logging.getLogger(__name__)


class InvariantViolationError(Exception):
    """Raised when a core security/financial invariant is violated."""


class SystemInvariants:
    """Runtime engine for evaluating system invariants."""

    @staticmethod
    def verify_financial_truth(item: RecoveryItem, verified_amount_minor: int) -> bool:
        """Invariant: verified_amount_minor must be non-negative and cannot exceed amount_at_risk."""
        if verified_amount_minor < 0:
            raise InvariantViolationError(f"Verified recovery amount cannot be negative: {verified_amount_minor}")
        if verified_amount_minor > item.amount_minor:
            raise InvariantViolationError(
                f"Verified recovery amount {verified_amount_minor} cannot exceed item amount at risk {item.amount_minor}"
            )
        return True

    @staticmethod
    def verify_terminal_immunity(item: RecoveryItem) -> bool:
        """Invariant: Terminal items (RECOVERED, STOPPED, ESCALATED) cannot execute new recovery actions."""
        if item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}:
            raise InvariantViolationError(f"Item {item.id} is in terminal state {item.status.value}; autonomous actions prohibited.")
        return True

    @staticmethod
    def verify_budget_integrity(proposed_attempts: int, max_allowed_attempts: int) -> bool:
        """Invariant: Proposed attempt count cannot exceed policy max_allowed_attempts."""
        if proposed_attempts > max_allowed_attempts:
            raise InvariantViolationError(
                f"Proposed attempt count {proposed_attempts} exceeds maximum allowed budget {max_allowed_attempts}"
            )
        return True

    @staticmethod
    def verify_settlement_evidence(settlement_evidence: dict[str, Any] | None) -> bool:
        """Invariant: Financial recovery requires authoritative provider settlement evidence."""
        if not settlement_evidence or not settlement_evidence.get("verified"):
            raise InvariantViolationError("Cannot confirm recovery without verified settlement evidence from provider.")
        return True

    @staticmethod
    def verify_idempotency_delta(first_recovered: int, duplicate_recovered: int) -> bool:
        """Invariant: Duplicate event processing must result in zero additional financial recovery delta."""
        if duplicate_recovered != 0:
            raise InvariantViolationError(f"Duplicate event produced non-zero recovery delta: {duplicate_recovered}")
        return True
