"""Promise-to-Pay (PTP) Bounded Workflow Service for B2B Receivables.

Manages customer payment promises, tracks promise expiration dates, and coordinates
automatic re-evaluation when promises are kept or missed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus


@dataclass
class PromiseToPayRecord:
    item_id: str
    customer_id: str
    promised_amount_minor: int
    promise_date: str
    status: str = "AWAITING_PAYMENT"  # AWAITING_PAYMENT, KEPT, MISSED, CANCELLED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class PromiseToPayTracker:
    """In-memory Promise-to-Pay tracking service."""

    def __init__(self) -> None:
        self._promises: dict[str, PromiseToPayRecord] = {}

    def create_promise(
        self,
        item: RecoveryItem,
        promised_amount_minor: int,
        promise_date_str: str,
        notes: str = "Customer promised payment via email outreach",
    ) -> PromiseToPayRecord:
        record = PromiseToPayRecord(
            item_id=item.id,
            customer_id=item.customer_id,
            promised_amount_minor=promised_amount_minor,
            promise_date=promise_date_str,
            status="AWAITING_PAYMENT",
            notes=notes,
        )
        self._promises[item.id] = record
        return record

    def check_promise_status(self, item_id: str, payment_received: bool = False) -> str:
        record = self._promises.get(item_id)
        if not record:
            return "NO_PROMISE"

        if payment_received:
            record.status = "KEPT"
            return "KEPT"

        # Check if promise date has passed
        try:
            p_date = date.fromisoformat(record.promise_date)
            today = date.today()
            if today > p_date:
                record.status = "MISSED"
                return "MISSED"
        except Exception:
            pass

        return record.status

    def get_promise(self, item_id: str) -> PromiseToPayRecord | None:
        return self._promises.get(item_id)
