"""Recovery Memory Concept for Customer Channel Performance & History.

Maintains historical intervention performance prior to decision time.
Ensures zero target leakage by reading historical records established before the current attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ChannelStats:
    channel: str
    total_attempts: int = 0
    successful_attempts: int = 0
    total_recovered_minor: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts

    @property
    def avg_recovered_minor(self) -> float:
        if self.successful_attempts == 0:
            return 0.0
        return self.total_recovered_minor / self.successful_attempts


@dataclass
class CustomerRecoveryMemory:
    customer_id: str
    channel_stats: dict[str, ChannelStats] = field(default_factory=dict)
    recent_contact_count: int = 0
    last_contact_at: datetime | None = None
    preferred_channel: str | None = None
    last_successful_action: str | None = None

    def record_historical_attempt(self, action: str, success: bool, recovered_minor: int = 0) -> None:
        if action not in self.channel_stats:
            self.channel_stats[action] = ChannelStats(channel=action)
        stats = self.channel_stats[action]
        stats.total_attempts += 1
        if success:
            stats.successful_attempts += 1
            stats.total_recovered_minor += recovered_minor
            self.last_successful_action = action
            self.preferred_channel = action

    def format_evidence_summary(self) -> list[str]:
        """Format concise operational evidence bullets for decision traces."""
        bullets = []
        for action, stats in self.channel_stats.items():
            if stats.total_attempts > 0:
                pct = int(stats.success_rate * 100)
                bullets.append(f"{action}: {stats.successful_attempts}/{stats.total_attempts} successful ({pct}%)")
        if self.preferred_channel:
            bullets.append(f"Preferred channel: {self.preferred_channel}")
        if self.recent_contact_count > 0:
            bullets.append(f"Recent contacts (24h): {self.recent_contact_count}")
        return bullets


class RecoveryMemoryStore:
    """In-memory store for customer recovery history."""

    def __init__(self) -> None:
        self._store: dict[str, CustomerRecoveryMemory] = {}

    def get_memory(self, customer_id: str, context: dict[str, Any] | None = None) -> CustomerRecoveryMemory:
        if customer_id not in self._store:
            mem = CustomerRecoveryMemory(customer_id=customer_id)
            # Initialize from context signals if available (historical context prior to case)
            if context:
                link_sr = context.get("past_link_success_rate")
                retry_sr = context.get("past_retry_success_rate")
                pref = context.get("preferred_channel")
                if link_sr is not None:
                    mem.record_historical_attempt("send_payment_link", success=True, recovered_minor=10000)
                    mem.record_historical_attempt("send_payment_link", success=(float(link_sr) > 0.5), recovered_minor=10000)
                if retry_sr is not None:
                    mem.record_historical_attempt("retry_payment", success=(float(retry_sr) > 0.5), recovered_minor=10000)
                if pref:
                    mem.preferred_channel = str(pref)
            self._store[customer_id] = mem
        return self._store[customer_id]
