from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.domain.models import Promise, PromiseStatus, RecoveryItem


class PromiseService:
    """Manages promise-to-pay lifecycle.

    Integrates with StoppingRules so expired promises stop recovery.
    """

    def create_promise(
        self,
        item_id: str,
        customer_id: str,
        promised_amount_minor: int,
        promised_date: date,
        metadata: dict[str, Any] | None = None,
    ) -> Promise:
        """Create a new promise-to-pay."""
        return Promise(
            id=f"promise_{item_id}",
            recovery_item_id=item_id,
            customer_id=customer_id,
            promised_amount_minor=promised_amount_minor,
            promised_date=promised_date,
            status=PromiseStatus.PROMISED.value,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

    def active_promise(self, item_id: str, promises_repo: Any) -> Promise | None:
        """Get the active promise for an item, if any."""
        if promises_repo is None:
            return None
        data = promises_repo.get_for_item(item_id)
        if data is None:
            return None
        if isinstance(data, Promise):
            if data.status == PromiseStatus.PROMISED.value:
                return data
            return None
        if isinstance(data, dict):
            if data.get("status") == PromiseStatus.PROMISED.value:
                return Promise(
                    id=data.get("id", ""),
                    recovery_item_id=data.get("recovery_item_id", item_id),
                    customer_id=data.get("customer_id", ""),
                    promised_amount_minor=data.get("promised_amount_minor", 0),
                    promised_date=data.get("promised_date", date.today()),
                    status=data.get("status", PromiseStatus.PROMISED.value),
                    created_at=data.get("created_at"),
                    fulfilled_at=data.get("fulfilled_at"),
                    expired_at=data.get("expired_at"),
                    metadata=data.get("metadata", {}),
                )
        return None

    def check_expired(self, promise: Promise, now: datetime | None = None) -> bool:
        """Check if an active promise has expired."""
        if promise is None or promise.promised_date is None:
            return False
        check_date = now.date() if now else datetime.now(timezone.utc).date()
        return promise.promised_date < check_date

    def fulfill(self, item_id: str, promises_repo: Any) -> Promise | None:
        """Mark a promise as fulfilled."""
        if promises_repo is None:
            return None
        data = promises_repo.get_for_item(item_id)
        if data is None:
            return None
        if isinstance(data, Promise):
            fulfilled = Promise(
                id=data.id,
                recovery_item_id=data.recovery_item_id,
                customer_id=data.customer_id,
                promised_amount_minor=data.promised_amount_minor,
                promised_date=data.promised_date,
                status=PromiseStatus.FULFILLED.value,
                created_at=data.created_at,
                fulfilled_at=datetime.now(timezone.utc),
                expired_at=data.expired_at,
                metadata=data.metadata,
            )
            promises_repo.save(fulfilled)
            return fulfilled
        if isinstance(data, dict):
            data["status"] = PromiseStatus.FULFILLED.value
            data["fulfilled_at"] = datetime.now(timezone.utc).isoformat()
            promises_repo.save(data)
            return None
        return None

    def break_promise(self, item_id: str, reason: str, promises_repo: Any) -> Promise | None:
        """Mark a promise as broken."""
        if promises_repo is None:
            return None
        data = promises_repo.get_for_item(item_id)
        if data is None:
            return None
        if isinstance(data, Promise):
            broken = Promise(
                id=data.id,
                recovery_item_id=data.recovery_item_id,
                customer_id=data.customer_id,
                promised_amount_minor=data.promised_amount_minor,
                promised_date=data.promised_date,
                status=PromiseStatus.BROKEN.value,
                created_at=data.created_at,
                fulfilled_at=data.fulfilled_at,
                expired_at=data.expired_at,
                metadata={**data.metadata, "break_reason": reason},
            )
            promises_repo.save(broken)
            return broken
        if isinstance(data, dict):
            data["status"] = PromiseStatus.BROKEN.value
            data["metadata"] = {**data.get("metadata", {}), "break_reason": reason}
            promises_repo.save(data)
            return None
        return None
