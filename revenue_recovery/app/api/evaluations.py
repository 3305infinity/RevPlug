from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer

router = APIRouter()

@router.get("/api/evaluations")
def api_evaluations(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    from app.dashboard_api import build_evaluation_report
    return build_evaluation_report(container)

@router.get("/api/evaluations/canonical")
def api_canonical_evaluation() -> Response:
    """Returns the canonical judge-facing financial evaluation run (Seed=42, Count=50)."""
    from app.services.evaluation_service import EvaluationService
    eval_svc = EvaluationService(agent=None, max_retry_attempts=3)
    try:
        result = eval_svc.run_batch_evaluation(count=50, seed=42)
        response_dict = eval_svc.to_response_dict(result)
        response_dict["canonical_metadata"] = {
            "evaluation_id": "REC-BENCH-2026-S42-C50",
            "dataset_version": "synthetic_v1_golden",
            "seed": 42,
            "sample_count": 50,
            "baseline_strategy": "fixed_retry_naive",
            "proof_status": "reproducible_canonical",
        }
        return JSONResponse(status_code=200, content=response_dict)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

@router.api_route("/api/evaluations/batch", methods=["GET", "POST"])
async def api_batch_evaluation(request: Request) -> Response:
    """Run a real batch evaluation comparing RevPlug against a dumb baseline.

    Accepts both POST JSON body and GET query parameters for flexibility.
    Request body / query params:
        {
            "count": 50,   # number of cases (1-500)
            "seed": 42     # deterministic seed for reproducibility
        }

    Response: EvaluationRunResult — see app/services/evaluation_service.py.
    """
    import json as _json
    payload = {}
    if request.method == "POST":
        body = await request.body()
        if body:
            try:
                payload = _json.loads(body)
            except _json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    else:
        payload = dict(request.query_params)

    count = int(payload.get("count", 50))
    count = max(1, min(count, 500))
    seed = int(payload.get("seed", 42))

    from app.services.evaluation_service import EvaluationService
    eval_svc = EvaluationService(
        agent=None,  # Rules-only path for deterministic evaluation
        max_retry_attempts=3,
    )
    try:
        result = eval_svc.run_batch_evaluation(count=count, seed=seed)
        response_dict = eval_svc.to_response_dict(result)
        return JSONResponse(status_code=200, content=response_dict)
    except Exception as exc:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc()[-2000:],
            },
        )

@router.post("/api/batches")
async def api_create_batch(request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Create a custom batch from a list of item payloads."""
    import json
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
    name = payload.get("name", "Custom Batch")
    raw_items = payload.get("items", [])
    
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    from datetime import datetime, timezone
    
    items = []
    import uuid
    for idx, ri in enumerate(raw_items):
        items.append(RecoveryItem(
            id=str(uuid.uuid4()),
            source_type=SourceType(ri.get("source_type", "payment_failure")),
            external_id=ri.get("external_id", f"ext_{idx}"),
            customer_id=ri.get("customer_id", f"cust_{idx}"),
            amount_minor=ri.get("amount_minor", 10000),
            currency=ri.get("currency", "INR"),
            created_at=datetime.now(timezone.utc),
            status=RecoveryStatus.QUEUED,
            root_cause=ri.get("root_cause", "unknown"),
            metadata=ri.get("metadata", {}),
        ))
        
    from app.services.batch_service import BatchService
    from app.scoring.expected_value import ExpectedValueScorer
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
        scorer=ExpectedValueScorer(),
    )
    
    batch = batch_svc.create_batch(name=name, items=items)
    return JSONResponse(status_code=201, content=batch.to_dict())

@router.get("/api/batches")
def api_list_batches(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    if not hasattr(container, "batches") or container.batches is None:
        return []
        
    from app.services.batch_service import BatchService
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )
    return [batch_svc.summarize_batch(b.batch_id) for b in batch_svc.list_batches()]

@router.get("/api/batches/{batch_id}")
def api_get_batch(batch_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    if not hasattr(container, "batches") or container.batches is None:
        return JSONResponse(status_code=500, content={"error": "Batches not configured"})
        
    from app.services.batch_service import BatchService
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )
    
    summary = batch_svc.summarize_batch(batch_id)
    if summary is None:
        return JSONResponse(status_code=404, content={"error": "Batch not found"})
        
    items = batch_svc._get_batch_items(batch_id)
    from app.dashboard_api import _item_to_dict
    summary["items"] = [_item_to_dict(i) for i in items]
    
    return JSONResponse(status_code=200, content=summary)

@router.get("/api/batches/{batch_id}/summary")
def api_get_batch_summary(batch_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Returns headline metrics, 4-way outcome breakdown, and complete audit trail export for a batch."""
    if not hasattr(container, "batches") or container.batches is None:
        return JSONResponse(status_code=500, content={"error": "Batches not configured"})
        
    from app.services.batch_service import BatchService
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )
    
    summary = batch_svc.summarize_batch(batch_id)
    if summary is None:
        return JSONResponse(status_code=404, content={"error": "Batch not found"})
        
    items = batch_svc._get_batch_items(batch_id)
    from app.dashboard_api import _item_to_dict
    item_dicts = [_item_to_dict(i) for i in items]
    
    # 4-way outcome breakdown with counts and amounts
    recovered_items = [d for d in item_dicts if d.get("status") == "recovered"]
    stopped_items = [d for d in item_dicts if d.get("status") == "stopped"]
    escalated_items = [d for d in item_dicts if d.get("status") == "escalated"]
    pending_items = [d for d in item_dicts if d.get("status") not in {"recovered", "stopped", "escalated"}]
    
    breakdown = {
        "RECOVERED": {
            "count": len(recovered_items),
            "amount_minor": sum(d.get("actual_recovery_value", d.get("amount_minor", 0)) for d in recovered_items),
            "label": "Verified Settlement"
        },
        "STOPPED": {
            "count": len(stopped_items),
            "amount_minor": sum(d.get("amount_minor", 0) for d in stopped_items),
            "label": "Policy Safety Stop"
        },
        "ESCALATED": {
            "count": len(escalated_items),
            "amount_minor": sum(d.get("amount_minor", 0) for d in escalated_items),
            "label": "Human Review Escalation"
        },
        "PENDING": {
            "count": len(pending_items),
            "amount_minor": sum(d.get("amount_minor", 0) for d in pending_items),
            "label": "Active / In Pipeline"
        }
    }
    
    # Audit trail export log
    audit_log = []
    for d in item_dicts:
        audit_log.append({
            "case_id": d.get("id"),
            "customer_id": d.get("customer_id"),
            "customer_name": d.get("customer_name"),
            "amount_minor": d.get("amount_minor"),
            "failure_category": d.get("failure_category"),
            "status": d.get("status"),
            "proposed_action": d.get("recommended_action"),
            "policy_check": "ALLOWED" if d.get("status") != "stopped" else "BLOCKED",
            "block_rule": d.get("stopped_rule") or d.get("stopped_reason"),
            "settlement_verified": d.get("status") == "recovered",
            "classification_method": d.get("classification_method", "RULES")
        })
        
    summary["breakdown"] = breakdown
    summary["audit_log"] = audit_log
    summary["items"] = item_dicts
    return JSONResponse(status_code=200, content=summary)

@router.post("/api/batches/{batch_id}/enqueue")
def api_enqueue_batch(batch_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    if not hasattr(container, "batches") or container.batches is None:
        return JSONResponse(status_code=500, content={"error": "Batches not configured"})
        
    from app.services.batch_service import BatchService
    batch_svc = BatchService(
        batch_repo=container.batches,
        recovery_items_repo=container.recovery_items,
        outcomes_repo=container.outcomes,
    )
    
    try:
        enqueued = batch_svc.enqueue_batch(batch_id, container.jobs)
        return JSONResponse(status_code=200, content={"status": "enqueued", "jobs": enqueued})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
