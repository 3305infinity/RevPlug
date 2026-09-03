from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class FailureCategory(StrEnum):
    SOFT = "soft"
    HARD = "hard"
    FRAUD = "fraud"
    AUTHENTICATION_REQUIRED = "authentication_required"
    UNKNOWN = "unknown"
    MANDATE_FAILURE = "mandate_failure"


@dataclass(frozen=True, slots=True)
class NormalizedFailure:
    """Provider-neutral normalized failure.

    Adapters translate provider-specific error details into this shape.
    """

    external_event_id: str
    external_payment_id: str | None = None
    category: FailureCategory = FailureCategory.UNKNOWN
    code: str = ""
    reason: str = ""
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
