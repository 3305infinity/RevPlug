from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FailureCategory(StrEnum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_PAYMENT_METHOD = "invalid_payment_method"
    AUTHENTICATION_REQUIRED = "authentication_required"
    SECURITY_OR_FRAUD = "security_or_fraud"
    TEMPORARY_PROCESSING = "temporary_processing"
    HARD_DECLINE = "hard_decline"
    UNKNOWN = "unknown"


class NotificationKind(StrEnum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    UPDATE_PAYMENT_METHOD = "update_payment_method"
    AUTHENTICATE_PAYMENT = "authenticate_payment"
    INTERNAL_SECURITY_REVIEW = "internal_security_review"
    MANUAL_REVIEW = "manual_review"
    RETRIES_EXHAUSTED = "retries_exhausted"


class RecoveryStatus(StrEnum):
    PENDING = "pending"
    ACTION_REQUIRED = "action_required"
    MANUAL_REVIEW = "manual_review"
    RECOVERED = "recovered"
    EXHAUSTED = "exhausted"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class StripeFailure:
    error_code: str | None = None
    decline_code: str | None = None
    advice_code: str | None = None
    network_advice_code: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedFailure:
    category: FailureCategory
    provider_code: str
    advice_code: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    category: FailureCategory
    retry_allowed: bool
    next_retry_at: datetime | None
    max_attempts: int
    notification_required: bool
    notification_kind: NotificationKind | None
    manual_review_required: bool
    reason: str
    policy_version: str = "2026-08-09"
