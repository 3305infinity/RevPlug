import time
from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container, get_webhook_service, get_webhook_secret
from app.db.container import PersistenceContainer
from app.adapters.razorpay import RazorpayWebhookService

router = APIRouter()

@router.post("/api/demo/reset")
def api_demo_reset(container: PersistenceContainer = Depends(get_container)):
    """Reset operational data and re-seed canonical video demo state."""
    from app.dashboard_api import seed_demo_state
    seed_demo_state(container)
    return {"status": "success", "message": "Reset and seeded canonical demo cases."}

@router.post("/api/demo/purge-batch-items")
def api_purge_batch_items(container: PersistenceContainer = Depends(get_container)):
    """Purge all synthetic batch/benchmark items sitting in the primary recovery store."""
    count = container.purge_batch_items()
    return {"status": "success", "purged_count": count, "message": f"Purged {count} batch-scoped synthetic items."}

@router.post("/api/demo/purge-poisoned-names")
def api_purge_poisoned_names(container: PersistenceContainer = Depends(get_container)):
    """Scan persisted RecoveryItems and set customer_name = None for any matching banned enterprise names."""
    count = container.purge_poisoned_customer_names()
    return {"status": "success", "poisoned_names_cleared": count, "message": f"Cleared {count} poisoned customer names."}

@router.post("/api/demo/purge-unapproved-items")
def api_purge_unapproved_items(container: PersistenceContainer = Depends(get_container)):
    """Purge all unapproved load/stress/test items not in the approved live source list."""
    stats = container.purge_unapproved_items()
    return {"status": "success", **stats}

@router.get("/api/demo/datasets")
def api_demo_datasets() -> list[dict[str, Any]]:
    from app.datasets.synthetic import list_datasets
    import dataclasses
    return [dataclasses.asdict(d) for d in list_datasets()]

@router.post("/api/demo/datasets/{label}/run")
def api_run_dataset(label: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.datasets.synthetic import load_dataset
    try:
        items = load_dataset(label)
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
        
    if not hasattr(container, "batches") or container.batches is None:
        return JSONResponse(status_code=500, content={"error": "Batch repository not configured"})
        
    from app.services.batch_service import BatchService
    from app.scoring.expected_value import ExpectedValueScorer
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
        scorer=ExpectedValueScorer(),
    )
    
    batch = batch_svc.create_batch(
        name=f"Synthetic Dataset: {label}",
        items=items,
        dataset_label=label,
        is_synthetic=True,
    )
    
    enqueued = batch_svc.enqueue_batch(batch.batch_id, container.jobs)
    
    return JSONResponse(status_code=201, content={
        "status": "started",
        "batch_id": batch.batch_id,
        "items_created": len(items),
        "jobs_enqueued": enqueued,
    })

@router.post("/api/demo/payment-failure")
async def api_demo_payment_failure(
    request: Request,
    container: PersistenceContainer = Depends(get_container),
    service: RazorpayWebhookService = Depends(get_webhook_service),
    webhook_secret: str = Depends(get_webhook_secret)
) -> Response:
    import json
    import hashlib
    import hmac as hmac_mod
    body = await request.body()
    payload = {}
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    event_id = payload.get("event_id", f"evt_demo_{int(time.time())}")
    payment_id = payload.get("payment_id", f"pay_demo_{int(time.time())}")
    error_reason = payload.get("error_reason", "payment_timed_out")

    from app.domain.customer_names import derive_customer_name
    customer_id = payload.get("customer_id", "razorpay_customer")
    customer_name = derive_customer_name(customer_id, payload.get("customer_name"))

    razorpay_payload = {
        "entity": "event",
        "account_id": "acc_DEMO",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": event_id,
        "customer_id": customer_id,
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "customer_id": customer_id,
                    "amount": payload.get("amount_minor", 50000),
                    "currency": payload.get("currency", "INR"),
                    "status": "failed",
                    "method": payload.get("method", "card"),
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": payload.get("error_description", "Payment failed"),
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": error_reason,
                    "created_at": int(time.time()),
                }
            }
        },
    }
    raw_body = json.dumps(razorpay_payload).encode()
    sig = hmac_mod.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    item, audit_events, status = service.process_webhook(raw_body, sig)
    response_body: dict[str, Any] = {
        "status": status,
        "recovery_item_id": item.id if item else None,
        "customer_name": customer_name,
        "audit_event_count": len(audit_events),
    }
    if item is not None:
        if hasattr(container.recovery_items, "get"):
            db_item = container.recovery_items.get(item.id)
            if db_item:
                db_item.metadata["source"] = "demo_scenario"
                db_item.metadata["is_synthetic"] = True
                db_item.metadata["customer_name"] = customer_name
                if isinstance(payload.get("metadata"), dict):
                    db_item.metadata.update(payload["metadata"])
                if payload.get("event_type"):
                    db_item.metadata["event_type"] = payload["event_type"]
                if payload.get("customer_id"):
                    db_item = db_item.__class__(
                        id=db_item.id,
                        source_type=db_item.source_type,
                        external_id=db_item.external_id,
                        customer_id=str(payload["customer_id"]).strip(),
                        amount_minor=db_item.amount_minor,
                        currency=db_item.currency,
                        created_at=db_item.created_at,
                        due_at=db_item.due_at,
                        status=db_item.status,
                        root_cause=db_item.root_cause,
                        recovery_probability=db_item.recovery_probability,
                        expected_recovery_value=db_item.expected_recovery_value,
                        intervention_cost=db_item.intervention_cost,
                        failure_category=db_item.failure_category,
                        provider=db_item.provider,
                        provider_event_id=db_item.provider_event_id,
                        actual_recovery_value=db_item.actual_recovery_value,
                        recovery_status=db_item.recovery_status,
                        score_version=db_item.score_version,
                        scoring_reason=db_item.scoring_reason,
                        priority=db_item.priority,
                        stopped_reason=db_item.stopped_reason,
                        stopped_rule=db_item.stopped_rule,
                        metadata=db_item.metadata,
                    )
                container.recovery_items.save(db_item)
                item = db_item
                
        response_body["failure_category"] = item.root_cause
        response_body["expected_recovery_value"] = item.expected_recovery_value
        response_body["actual_recovery_value"] = item.actual_recovery_value or (item.expected_recovery_value if item.status.value == "recovered" else 0)
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


@router.post("/api/demo/hinglish-recovery")
async def api_demo_hinglish_recovery(
    request: Request,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    """Run Hinglish customer voice/chat promise extraction scenario."""
    import json
    body = await request.body()
    payload = json.loads(body) if body else {}
    text = payload.get("text", "Haan kal tak payment clear kar dunga ₹15,000")

    from app.services.hinglish_promise import HinglishPromiseExtractor
    extractor = HinglishPromiseExtractor()
    extracted = extractor.extract(text)

    from datetime import datetime, timezone
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    import uuid
    item_id = f"it_hinglish_{uuid.uuid4().hex[:8]}"

    item = RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"ext_{item_id}",
        customer_id=payload.get("customer_id", "cust_hinglish_101"),
        amount_minor=extracted.amount_minor or 1500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.INTERVENTION_PENDING,
        root_cause="hinglish_promise_active",
        expected_recovery_value=extracted.amount_minor or 1500000,
        actual_recovery_value=0,
        metadata={
            "source": "demo_scenario",
            "hinglish_text": text,
            "extracted_intent": extracted.intent,
            "promised_date": extracted.promised_date,
            "extraction_confidence": extracted.confidence,
            "is_synthetic": True,
        },
    )
    container.recovery_items.save(item)

    if extracted.promised_date and hasattr(container, "promises") and container.promises is not None:
        from app.services.promise_to_pay import PromiseToPayTracker
        tracker = PromiseToPayTracker()
        tracker.create_promise(item, item.amount_minor, extracted.promised_date, notes=f"Hinglish chat: '{text}'")

    return JSONResponse(
        status_code=200,
        content={
            "status": "promise_captured",
            "recovery_item_id": item.id,
            "hinglish_text": text,
            "extracted_intent": extracted.intent,
            "promised_date": extracted.promised_date,
            "extraction_confidence": extracted.confidence,
            "recommended_action": "wait_for_promise",
            "policy_rule": "promise_active_wait",
        },
    )


@router.post("/api/demo/b2b-promise-to-pay")
async def api_demo_b2b_promise_to_pay(
    request: Request,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    """Run B2B Promise-to-Pay overdue invoice scenario."""
    import json
    body = await request.body()
    payload = json.loads(body) if body else {}
    amount = payload.get("amount_minor", 25000000)

    from datetime import datetime, timezone
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    import uuid
    item_id = f"it_ptp_b2b_{uuid.uuid4().hex[:8]}"

    item = RecoveryItem(
        id=item_id,
        source_type=SourceType.RECEIVABLE,
        external_id=f"inv_b2b_{item_id}",
        customer_id=payload.get("customer_id", "cust_corp_acme"),
        amount_minor=amount,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.INTERVENTION_PENDING,
        root_cause="overdue_receivable",
        expected_recovery_value=int(amount * 0.95),
        actual_recovery_value=0,
        metadata={
            "invoice_number": "INV-2026-884",
            "due_days_ago": 14,
            "promise_date": "2026-12-31",
            "is_synthetic": True,
        },
    )
    container.recovery_items.save(item)

    from app.services.promise_to_pay import PromiseToPayTracker
    tracker = PromiseToPayTracker()
    rec = tracker.create_promise(item, amount, "2026-12-31", notes="Client Accounts Payable promised wire transfer")

    return JSONResponse(
        status_code=200,
        content={
            "status": "promise_recorded",
            "recovery_item_id": item.id,
            "amount_minor": amount,
            "promised_date": "2026-12-31",
            "promise_status": rec.status,
            "recommended_action": "send_reminder",
            "policy_rule": "b2b_receivable_grace_period",
        },
    )

@router.post("/api/demo/batch-payment-failures")
async def api_batch_payment_failures(
    request: Request,
    service: RazorpayWebhookService = Depends(get_webhook_service),
    container: PersistenceContainer = Depends(get_container),
    webhook_secret: str = Depends(get_webhook_secret)
) -> Response:
    """Run multiple synthetic payment failures as a batch."""
    import json, hashlib, hmac as hmac_mod
    body = await request.body()
    payload = {}
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    count = int(payload.get("count", 5))
    count = max(1, min(count, 50))
    error_reason = payload.get("error_reason", "payment_timed_out")
    base_amount = int(payload.get("amount_minor", 50000))
    results = []
    total_recovered = 0
    recovered_count = 0
    escalated_count = 0
    stopped_count = 0

    for i in range(count):
        event_id = f"evt_batch_{int(time.time())}_{i}"
        payment_id = f"pay_batch_{int(time.time())}_{i}"
        amount = base_amount + (i * 1000)
        razorpay_payload = {
            "entity": "event",
            "account_id": "acc_DEMO",
            "event": "payment.failed",
            "contains": ["payment"],
            "id": event_id,
            "created_at": int(time.time()),
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "entity": "payment",
                        "amount": amount,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BATCH_ERROR",
                        "error_description": "Batch simulation",
                        "error_source": "bank",
                        "error_step": "payment_authorization",
                        "error_reason": error_reason,
                        "created_at": int(time.time()),
                    }
                }
            },
        }
        raw_body = json.dumps(razorpay_payload).encode()
        sig = hmac_mod.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        item, _, status = service.process_webhook(raw_body, sig)
        result = {
            "recovery_item_id": item.id if item else None,
            "status": status,
            "failure_category": item.root_cause if item else None,
            "amount_minor": item.amount_minor if item else None,
            "expected_recovery_value": item.expected_recovery_value if item else None,
            "intervention_cost": item.intervention_cost if item else None,
            "recovery_probability": item.recovery_probability if item else None,
            "priority": item.priority if item else None,
            "scoring_reason": item.scoring_reason if item else None,
            "recovery_status": item.status.value if item else None,
            "proposed_action": service.last_proposal.action.value if service.last_proposal else None,
            "agent_confidence": service.last_proposal.confidence if service.last_proposal else None,
            "policy_allowed": service.last_decision.allowed if service.last_decision else None,
            "policy_rule": service.last_decision.policy_rule if service.last_decision else None,
            "execution_status": "succeeded" if service.last_execution and service.last_execution.success else "failed",
        }
        if item:
            if hasattr(container.recovery_items, "get"):
                db_item = container.recovery_items.get(item.id)
                if db_item:
                    db_item.metadata["is_synthetic"] = True
                    container.recovery_items.save(db_item)

            if item.status.value == "recovered":
                recovered_count += 1
                total_recovered += item.expected_recovery_value or 0
            elif item.status.value == "escalated":
                escalated_count += 1
            elif item.status.value == "stopped":
                stopped_count += 1
                
        results.append(result)

    summary = {
        "total_cases": count,
        "recovered_count": recovered_count,
        "recovered_amount_minor": total_recovered,
        "escalated_count": escalated_count,
        "stopped_count": stopped_count,
        "recovery_rate": recovered_count / count if count > 0 else 0,
        "priority_distribution": {
            "CRITICAL": sum(1 for r in results if r.get("priority") == "CRITICAL"),
            "HIGH": sum(1 for r in results if r.get("priority") == "HIGH"),
            "MEDIUM": sum(1 for r in results if r.get("priority") == "MEDIUM"),
            "LOW": sum(1 for r in results if r.get("priority") == "LOW"),
        },
        "ranked_cases": sorted(
            [
                {
                    "recovery_item_id": r.get("recovery_item_id"),
                    "amount_minor": r.get("amount_minor"),
                    "expected_recovery_value": r.get("expected_recovery_value"),
                    "priority": r.get("priority"),
                    "failure_category": r.get("failure_category"),
                    "proposed_action": r.get("proposed_action"),
                }
                for r in results
                if r.get("recovery_item_id")
            ],
            key=lambda x: -(x.get("expected_recovery_value") or 0),
        ),
    }
    return JSONResponse(status_code=200, content={"results": results, "summary": summary})

@router.post("/api/demo/dataset")
async def api_demo_dataset(
    request: Request,
    container: PersistenceContainer = Depends(get_container),
    webhook_secret: str = Depends(get_webhook_secret)
) -> Response:
    """Run a deterministic demo dataset of 15 mixed scenarios."""
    import json, hashlib, hmac as hmac_mod
    from datetime import datetime, timezone
    
    # We must build temporary services for each scenario to modify dependencies like rules
    from app.main import _build_webhook_service

    body = await request.body()
    payload = {}
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    seed = int(payload.get("seed", 42))

    rng = __import__("random").Random(seed)

    def make_payload(event_id, payment_id, error_reason, amount, **kwargs):
        return {
            "entity": "event",
            "account_id": "acc_DEMO",
            "event": "payment.failed",
            "contains": ["payment"],
            "id": event_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "entity": "payment",
                        "amount": amount,
                        "currency": kwargs.get("currency", "INR"),
                        "status": "failed",
                        "method": kwargs.get("method", "card"),
                        "error_code": kwargs.get("error_code", "BAD_REQUEST_ERROR"),
                        "error_description": kwargs.get("error_description", "Payment failed"),
                        "error_source": kwargs.get("error_source", "bank"),
                        "error_step": kwargs.get("error_step", "payment_authorization"),
                        "error_reason": error_reason,
                        "created_at": int(datetime.now(timezone.utc).timestamp()),
                    }
                }
            },
        }

    scenarios = [
        ("gateway_timeout", 3, "gateway_technical_error", 50000),
        ("bank_downtime", 2, "payment_timed_out", 45000),
        ("card_decline", 2, "card_declined", 30000),
        ("auth_required", 1, "authentication_failed", 20000),
        ("fraud", 2, "payment_risk_check_failed", 60000),
        ("opted_out", 1, "payment_timed_out", 35000),
        ("retry_exhausted", 1, "payment_timed_out", 40000),
        ("deadline_expired", 1, "payment_timed_out", 25000),
        ("success_retry", 1, "payment_timed_out", 50000),
        ("failed_retry_link", 1, "payment_timed_out", 35000),
    ]

    results = []
    total_revenue_at_risk = 0
    total_expected_recovery = 0
    total_actual_recovered = 0
    automated_count = 0
    escalated_count = 0
    stopped_count = 0

    for scenario_type, count, error_reason, base_amount in scenarios:
        for i in range(count):
            event_id = f"evt_ds_{seed}_{scenario_type}_{i}"
            payment_id = f"pay_ds_{seed}_{scenario_type}_{i}"
            amount = base_amount + rng.randint(0, 10000)
            total_revenue_at_risk += amount

            payload_data = make_payload(event_id, payment_id, error_reason, amount)
            raw_body = json.dumps(payload_data).encode()
            sig = hmac_mod.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()

            if scenario_type == "opted_out":
                svc = _build_webhook_service(webhook_secret, container)
                svc._stopping_rules._opted_out_customer_ids = frozenset({svc._default_customer_id})
                item, _, status = svc.process_webhook(raw_body, sig)
            elif scenario_type == "retry_exhausted":
                svc = _build_webhook_service(webhook_secret, container)
                svc._stopping_rules._max_attempts = 0
                item, _, status = svc.process_webhook(raw_body, sig)
            elif scenario_type == "deadline_expired":
                svc = _build_webhook_service(webhook_secret, container)
                orig_build = svc._build_recovery_item
                def patched_build(razorpay_failure, normalized):
                    itm = orig_build(razorpay_failure, normalized)
                    return itm.__class__(
                        id=itm.id,
                        source_type=itm.source_type,
                        external_id=itm.external_id,
                        customer_id=itm.customer_id,
                        amount_minor=itm.amount_minor,
                        currency=itm.currency,
                        created_at=itm.created_at,
                        due_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                        status=itm.status,
                        root_cause=itm.root_cause,
                        recovery_probability=itm.recovery_probability,
                        expected_recovery_value=itm.expected_recovery_value,
                        intervention_cost=itm.intervention_cost,
                        failure_category=itm.failure_category,
                        provider=itm.provider,
                        provider_event_id=itm.provider_event_id,
                        actual_recovery_value=itm.actual_recovery_value,
                        recovery_status=itm.recovery_status,
                        score_version=itm.score_version,
                        scoring_reason=itm.scoring_reason,
                        priority=itm.priority,
                        stopped_reason=itm.stopped_reason,
                        stopped_rule=itm.stopped_rule,
                        metadata=itm.metadata,
                    )
                svc._build_recovery_item = patched_build
                item, _, status = svc.process_webhook(raw_body, sig)
                svc._build_recovery_item = orig_build
            else:
                svc = _build_webhook_service(webhook_secret, container)
                if scenario_type == "success_retry":
                    orig_exec = svc._executor
                    class SuccessExecutor(type(orig_exec)):
                        def execute(self, item, action, *, attempt_number, scenario=None):
                            from app.interventions.executor import ExecutionResult
                            return ExecutionResult(
                                success=True,
                                action=action,
                                attempt_number=attempt_number,
                                reason=f"Simulated recovery succeeded for {item.id}",
                                retry_eligible=False,
                                metadata={"simulated": True, "scenario": "success"},
                            )
                    svc._executor = SuccessExecutor()
                elif scenario_type == "failed_retry_link":
                    orig_exec = svc._executor
                    class FailExecutor(type(orig_exec)):
                        def execute(self, item, action, *, attempt_number, scenario=None):
                            from app.interventions.executor import ExecutionResult
                            return ExecutionResult(
                                success=False,
                                action=action,
                                attempt_number=attempt_number,
                                reason=f"Simulated permanent failure for {item.id}",
                                retry_eligible=False,
                                error_code="permanent_failure",
                                metadata={"simulated": True, "scenario": "permanent_failure"},
                            )
                    svc._executor = FailExecutor()
                item, _, status = svc.process_webhook(raw_body, sig)

            if item is None:
                continue

            result = {
                "recovery_item_id": item.id,
                "status": item.status.value,
                "failure_category": item.root_cause,
                "amount_minor": item.amount_minor,
                "expected_recovery_value": item.expected_recovery_value,
                "actual_recovery_value": item.actual_recovery_value,
                "proposed_action": svc.last_proposal.action.value if svc.last_proposal else None,
                "policy_allowed": svc.last_decision.allowed if svc.last_decision else None,
                "stopped_reason": getattr(item, "stopped_reason", None),
            }
            results.append(result)

            total_expected_recovery += item.expected_recovery_value or 0
            total_actual_recovered += item.actual_recovery_value or 0

            if item.status.value == "recovered":
                automated_count += 1
            elif item.status.value == "escalated":
                escalated_count += 1
            elif item.status.value == "stopped":
                stopped_count += 1

    variance = total_actual_recovered - total_expected_recovery
    recovery_rate = total_actual_recovered / total_revenue_at_risk if total_revenue_at_risk > 0 else 0.0

    summary = {
        "total_cases": len(results),
        "revenue_at_risk_minor": total_revenue_at_risk,
        "expected_recovery_minor": total_expected_recovery,
        "actual_recovered_minor": total_actual_recovered,
        "recovery_rate": round(recovery_rate, 4),
        "automated_count": automated_count,
        "escalated_count": escalated_count,
        "stopped_count": stopped_count,
        "variance_minor": variance,
    }
    return JSONResponse(status_code=200, content={"results": results, "summary": summary})
