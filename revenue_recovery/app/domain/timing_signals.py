"""Timing signal and evaluation domain models for autonomous WAIT decisions.

These models provide structured, evidence-based timing intelligence that
determines when WAIT is the optimal decision and for how long to wait.
All timing is subordinate to stopping rules, safety, and policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class TimingSignalType(StrEnum):
    ACTIVE_PROMISE = "ACTIVE_PROMISE"
    RECENT_ATTEMPT = "RECENT_ATTEMPT"
    CONTACT_LIMIT_WINDOW = "CONTACT_LIMIT_WINDOW"
    SYSTEMIC_INCIDENT = "SYSTEMIC_INCIDENT"
    HISTORICAL_SUCCESS_WINDOW = "HISTORICAL_SUCCESS_WINDOW"
    PAYMENT_PATTERN = "PAYMENT_PATTERN"
    RETRY_COOLDOWN = "RETRY_COOLDOWN"
    NO_TIMING_ADVANTAGE = "NO_TIMING_ADVANTAGE"
    INSUFFICIENT_TIMING_DATA = "INSUFFICIENT_TIMING_DATA"


@dataclass(frozen=True, slots=True)
class TimingSignal:
    signal_type: TimingSignalType
    active: bool
    reason_code: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    policy_status: str = "EVIDENCE_BASED"
    blocked_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type.value if isinstance(self.signal_type, StrEnum) else self.signal_type,
            "active": self.active,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "policy_status": self.policy_status,
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class TimingEvaluation:
    item_id: str
    timing_decision: str
    reason_code: str
    reason: str
    scheduled_for: datetime | None = None
    signals: list[TimingSignal] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    policy_status: str = "EVIDENCE_BASED"
    wait_count: int = 0
    max_wait_count: int = 3
    max_wait_horizon_days: int = 30
    blocked_until: datetime | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def wait_remaining(self) -> int:
        return max(0, self.max_wait_count - self.wait_count)

    @property
    def at_max_waits(self) -> bool:
        return self.wait_count >= self.max_wait_count

    @property
    def horizon_exceeded(self) -> bool:
        if self.scheduled_for is None:
            return False
        from datetime import timedelta
        horizon = datetime.now(timezone.utc) + timedelta(days=self.max_wait_horizon_days)
        return self.scheduled_for > horizon

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "timing_decision": self.timing_decision,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "signals": [s.to_dict() for s in self.signals],
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "policy_status": self.policy_status,
            "wait_count": self.wait_count,
            "max_wait_count": self.max_wait_count,
            "max_wait_horizon_days": self.max_wait_horizon_days,
            "wait_remaining": self.wait_remaining,
            "at_max_waits": self.at_max_waits,
            "horizon_exceeded": self.horizon_exceeded,
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "metadata": self.metadata,
        }


TIMING_REASON_CODES = frozenset({
    "active_promise_wait",
    "recent_contact_cooldown",
    "contact_frequency_limit",
    "systemic_incident_window",
    "historical_payment_window",
    "retry_cooldown_active",
    "no_timing_advantage",
    "insufficient_timing_data",
    "max_waits_exceeded",
    "max_horizon_exceeded",
    "timing_evaluation_unavailable",
})

TIMING_DECISIONS = frozenset({"WAIT", "RECOVER", "ESCALATE", "STOP"})
