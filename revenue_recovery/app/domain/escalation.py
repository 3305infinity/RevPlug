from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EscalationReason(StrEnum):
    POLICY_DENIED = "policy_denied"
    FRAUD_DETECTED = "fraud_detected"
    HARD_FAILURE = "hard_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
    INVALID_PROPOSAL = "invalid_proposal"
    OPT_OUT = "opt_out"
    AUTHENTICATION_REQUIRED = "authentication_required"


@dataclass(frozen=True, slots=True)
class Escalation:
    """Structured escalation outcome."""

    reason: EscalationReason
    message: str
    item_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
