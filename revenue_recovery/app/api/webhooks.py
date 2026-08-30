from typing import Any
from fastapi import APIRouter, Header, Request, Response, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_container, get_webhook_service, get_webhook_secret
from app.db.container import PersistenceContainer
from app.adapters.razorpay import RazorpayWebhookService, RazorpaySignatureError, RazorpayEventError

router = APIRouter()

@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    container: PersistenceContainer = Depends(get_container),
    service: RazorpayWebhookService = Depends(get_webhook_service),
    webhook_secret: str = Depends(get_webhook_secret),
) -> Response:
    raw_body = await request.body()
    
    # Check whether async job queue is available for this app instance.
    job_repo = getattr(container, "jobs", None)

    if job_repo is not None:
        # ── ASYNC FAST-ACCEPT PATH ──────────────────────────────────────
        from app.adapters.razorpay.signatures import (
            RazorpaySignatureError as _SigErr,
            verify_razorpay_signature,
        )
        try:
            verify_razorpay_signature(raw_body, x_razorpay_signature, webhook_secret)
        except _SigErr:
            return JSONResponse(
                status_code=400,
                content={"status": "rejected", "reason": "signature_verification_failed"},
            )

        from app.adapters.razorpay.events import parse_razorpay_event
        try:
            razorpay_failure = parse_razorpay_event(raw_body)
        except Exception:
            return JSONResponse(
                status_code=422,
                content={"status": "rejected", "reason": "event_parse_failed"},
            )

        provider = "razorpay"
        provider_event_id = razorpay_failure.razorpay_event_id

        from datetime import datetime, timezone as _tz
        from app.domain.models import ProviderEvent
        received_at = datetime.now(_tz.utc)
        import uuid
        candidate = ProviderEvent(
            id=str(uuid.uuid4()),
            provider=provider,
            provider_event_id=provider_event_id,
            received_at=received_at,
            event_type="payment.failed",
            raw_payload={
                "razorpay_event_id": razorpay_failure.razorpay_event_id,
                "razorpay_payment_id": razorpay_failure.razorpay_payment_id,
                "amount_minor": razorpay_failure.amount_minor,
                "currency": razorpay_failure.currency,
            },
            processing_status="pending",
        )

        provider_events = getattr(container, "provider_events", None)
        is_new_event = True
        if provider_events is not None:
            is_new_event, _ = provider_events.try_insert(candidate)

        if not is_new_event:
            return JSONResponse(
                status_code=200,
                content={"status": "duplicate", "provider_event_id": provider_event_id},
            )

        from app.adapters.razorpay.classifier import RazorpayFailureClassifier
        from app.domain.models import RecoveryStatus
        classifier = RazorpayFailureClassifier()
        normalized = classifier.classify(razorpay_failure)
        item = service._build_recovery_item(razorpay_failure, normalized)
        item = service._safe_transition(item, RecoveryStatus.DIAGNOSED)

        score_result = service._score(
            item=item,
            failure_category=normalized.category.value,
            proposed_action="retry_payment",
            attempt_number=0,
        )
        item = service._apply_score(item, score_result)

        if container.recovery_items is not None:
            container.recovery_items.save(item)

        if provider_events is not None:
            provider_events.mark_processed(
                provider=provider,
                provider_event_id=provider_event_id,
                recovery_item_id=item.id,
            )

        job = job_repo.create_job(item.id)

        try:
            container.audit_log.log(
                recovery_item_id=item.id,
                actor="system",
                action="job_created",
                reason="Recovery job enqueued for async worker",
                metadata={
                    "job_id": job.job_id if job else None,
                    "provider_event_id": provider_event_id,
                },
            )
        except Exception:
            pass

        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "provider_event_id": provider_event_id,
                "recovery_item_id": item.id,
                "job_id": job.job_id if job else None,
            },
        )

    # ── LEGACY SYNCHRONOUS PATH (used by all pre-Stage-7 tests) ────────
    try:
        item, audit_events, status = service.process_webhook(
            raw_body=raw_body,
            signature_header=x_razorpay_signature,
        )
    except RazorpaySignatureError:
        return JSONResponse(
            status_code=400,
            content={"status": "rejected", "reason": "signature_verification_failed"},
        )
    except RazorpayEventError:
        return JSONResponse(
            status_code=422,
            content={"status": "rejected", "reason": "event_parse_failed"},
        )

    response_body: dict[str, Any] = {
        "status": status,
        "audit_event_count": len(audit_events),
    }
    if item is not None:
        response_body["recovery_item_id"] = item.id
        response_body["failure_category"] = item.root_cause
        response_body["expected_recovery_value"] = item.expected_recovery_value
        response_body["recovery_status"] = item.status.value
        response_body["stopped_reason"] = getattr(item, "stopped_reason", None)
        response_body["stopped_rule"] = getattr(item, "stopped_rule", None)
        proposal = service.last_proposal
        decision = service.last_decision
        if proposal is not None:
            response_body["proposed_action"] = proposal.action.value
            response_body["agent_confidence"] = proposal.confidence
            response_body["agent_model"] = proposal.model_name
        if decision is not None:
            response_body["policy_allowed"] = decision.allowed
            response_body["policy_rule"] = decision.policy_rule
        execution = service.last_execution
        if execution is not None:
            response_body["execution_status"] = "succeeded" if execution.success else "failed"
            response_body["attempt_number"] = execution.attempt_number
        retry = service.last_retry
        if retry is not None:
            response_body["retry_scheduled"] = retry.allowed
            response_body["next_attempt_at"] = retry.next_attempt_at.isoformat() if retry.next_attempt_at else None
        escalation = service.last_escalation
        if escalation is not None:
            response_body["escalation_reason"] = escalation.reason.value

    return JSONResponse(status_code=200, content=response_body)
