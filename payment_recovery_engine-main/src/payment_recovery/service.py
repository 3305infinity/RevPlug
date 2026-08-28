from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .models import PolicyDecision, StripeFailure
from .policy import RecoveryPolicy
from .signatures import SignatureVerificationError, verify_stripe_signature
from .state_machine import RecoveryStore, TransitionResult
from .stripe_adapter import failure_from_payment_intent, normalize_stripe_failure

app = FastAPI(title="Payment Recovery Policy Engine", version="0.1.0")
policy = RecoveryPolicy()
store = RecoveryStore()


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str | None = None
    decline_code: str | None = None
    advice_code: str | None = None
    network_advice_code: str | None = None
    attempts_completed: int = Field(ge=0)
    occurred_at: datetime


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "policy_version": "2026-08-09"}


@app.post("/v1/decisions/stripe")
def decide(request: DecisionRequest) -> dict[str, object]:
    normalized = normalize_stripe_failure(
        StripeFailure(
            error_code=request.error_code,
            decline_code=request.decline_code,
            advice_code=request.advice_code,
            network_advice_code=request.network_advice_code,
        )
    )
    return asdict(
        policy.decide(
            normalized,
            attempts_completed=request.attempts_completed,
            occurred_at=request.occurred_at,
        )
    )


@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, object]:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="webhook signing secret is not configured")
    raw_body = await request.body()
    try:
        verify_stripe_signature(raw_body, stripe_signature or "", secret)
    except SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc
    try:
        result, decision = process_stripe_event(event)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_result(event, raw_body, result, decision)


def process_stripe_event(
    event: dict[str, object],
) -> tuple[TransitionResult, PolicyDecision | None]:
    event_id = _required_string(event, "id")
    event_type = _required_string(event, "type")
    data = event.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("object"), dict):
        raise ValueError("event.data.object must be an object")
    payment_intent = data["object"]
    payment_intent_id = _required_string(payment_intent, "id")

    if event_type == "payment_intent.payment_failed":
        occurred_at = datetime.fromtimestamp(_event_timestamp(event), tz=UTC)
        existing = store.get(payment_intent_id)
        attempts = existing.attempts_completed if existing else 0
        normalized = normalize_stripe_failure(failure_from_payment_intent(payment_intent))
        decision = policy.decide(normalized, attempts_completed=attempts, occurred_at=occurred_at)
        return store.apply_failure(event_id, payment_intent_id, decision), decision
    if event_type == "payment_intent.succeeded":
        return store.mark_recovered(event_id, payment_intent_id), None
    if event_type == "payment_intent.canceled":
        return store.cancel(event_id, payment_intent_id), None
    raise ValueError(f"unsupported Stripe event type: {event_type}")


def _event_timestamp(event: dict[str, object]) -> int:
    value = event.get("created")
    if not isinstance(value, int) or value < 0:
        raise ValueError("event.created must be a non-negative integer")
    return value


def _required_string(document: dict[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _serialize_result(
    event: dict[str, object],
    raw_body: bytes,
    result: TransitionResult,
    decision: PolicyDecision | None,
) -> dict[str, object]:
    data = event.get("data")
    payment_intent = data.get("object", {}) if isinstance(data, dict) else {}
    if not isinstance(payment_intent, dict):
        payment_intent = {}
    provider_failure = failure_from_payment_intent(payment_intent)
    serialized = {
        "event_id": event["id"],
        "event_type": {
            "payment_intent.payment_failed": "payment_failed",
            "payment_intent.succeeded": "payment_succeeded",
            "payment_intent.canceled": "payment_canceled",
        }[event["type"]],
        "payment_intent_id": result.case.payment_intent_id,
        "customer_id": payment_intent.get("customer"),
        "customer_email": payment_intent.get("receipt_email"),
        "amount_minor": payment_intent.get("amount", 0),
        "currency": payment_intent.get("currency", "USD"),
        "provider_failure_code": provider_failure.decline_code
        or provider_failure.error_code
        or "unknown",
        "payload_sha256": hashlib.sha256(raw_body).hexdigest(),
        "applied": result.applied,
        "duplicate": result.duplicate,
        "notification_required": result.notification_required,
        "case": asdict(result.case),
    }
    if decision:
        serialized["decision"] = asdict(decision)
    return serialized
