from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer

router = APIRouter()

@router.post("/api/promises")
async def api_create_promise(request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Create a new promise-to-pay."""
    import json
    from datetime import date
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
    item_id = payload.get("item_id")
    customer_id = payload.get("customer_id")
    amount = payload.get("amount_minor")
    promised_date_str = payload.get("promised_date")
    
    if not all([item_id, customer_id, amount, promised_date_str]):
        return JSONResponse(status_code=400, content={"error": "Missing required fields"})
        
    try:
        promised_date = date.fromisoformat(promised_date_str)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid date format, use YYYY-MM-DD"})
        
    from app.services.promise_service import PromiseService
    service = PromiseService()
    promise = service.create_promise(
        item_id=item_id,
        customer_id=customer_id,
        promised_amount_minor=amount,
        promised_date=promised_date,
        metadata=payload.get("metadata", {}),
    )
    if container.promises:
        container.promises.save(promise)
        
    container.audit_log.log(
        recovery_item_id=item_id,
        actor="agent",
        action="promise_created",
        reason=f"Promise-to-pay recorded for {amount} minor units by {promised_date_str}",
        metadata={"promise_id": promise.id, "amount_minor": amount, "promised_date": promised_date_str},
    )
        
    from app.dashboard_api import _promise_to_dict
    return JSONResponse(status_code=201, content=_promise_to_dict(promise))

@router.get("/api/promises")
def api_list_promises(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """List all promises."""
    if hasattr(container.promises, "list_all"):
        promises = container.promises.list_all()
    else:
        promises = []
    from app.dashboard_api import _promise_to_dict
    return [_promise_to_dict(p) for p in promises]

@router.get("/api/promises/{promise_id}")
def api_get_promise(promise_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get a single promise by ID."""
    if hasattr(container.promises, "get"):
        promise = container.promises.get(promise_id)
        if promise:
            from app.dashboard_api import _promise_to_dict
            return JSONResponse(status_code=200, content=_promise_to_dict(promise))
    return JSONResponse(status_code=404, content={"error": "Promise not found"})

@router.get("/api/promises/by-item/{item_id}")
def api_get_promise_by_item(item_id: str, active: bool = False, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get the active promise for a recovery item."""
    if not hasattr(container.promises, "get_for_item"):
        return JSONResponse(status_code=404, content={"error": "Promises not configured"})
    promise = container.promises.get_for_item(item_id)
    if not promise:
        return JSONResponse(status_code=404, content={"error": "No promise found for this opportunity"})
    from app.dashboard_api import _promise_to_dict
    from app.domain.models import PromiseStatus
    p_dict = _promise_to_dict(promise)
    if active and p_dict.get("status") not in {PromiseStatus.PROMISED.value, "promised", "active"}:
        return JSONResponse(status_code=404, content={"error": "No active promise found for this opportunity"})
    return JSONResponse(status_code=200, content=p_dict)

@router.post("/api/promises/{promise_id}/fulfill")
def api_fulfill_promise(promise_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Fulfill a promise, generating a RecoveryOutcome (financial truth)."""
    if not hasattr(container.promises, "get"):
        return JSONResponse(status_code=500, content={"error": "Promises not configured"})
        
    promise = container.promises.get(promise_id)
    if not promise:
        return JSONResponse(status_code=404, content={"error": "Promise not found"})
        
    item_id = promise.recovery_item_id if not isinstance(promise, dict) else promise.get("recovery_item_id")
    amount = promise.promised_amount_minor if not isinstance(promise, dict) else promise.get("promised_amount_minor")
    status = promise.status if not isinstance(promise, dict) else promise.get("status")
    
    if status != "promised":
        return JSONResponse(status_code=400, content={"error": f"Promise is {status}, cannot fulfill"})
        
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if hasattr(container.promises, "update_status"):
        updated = container.promises.update_status(
            promise_id, "fulfilled",
            fulfilled_at=now,
            metadata={"verified_recovered_minor": amount},
        )
        if updated:
            promise = updated

    if container.outcomes:
        from app.domain.models import RecoveryOutcome
        outcome = RecoveryOutcome(
            id=str(promise_id) + "_outcome",
            recovery_item_id=item_id,
            outcome_type="recovered",
            expected_recovery_minor=amount,
            actual_recovery_minor=amount,
            recovery_cost_minor=0,
            net_recovery_minor=amount,
            recovered_at=now,
            metadata={"source": "promise_fulfillment", "promise_id": promise_id},
        )
        container.outcomes.save(outcome)
        
    container.audit_log.log(
        recovery_item_id=item_id,
        actor="system",
        action="promise_fulfilled",
        reason=f"Promise fulfilled, recovered {amount}",
        metadata={"promise_id": promise_id, "amount": amount},
    )
        
    from app.dashboard_api import _promise_to_dict
    return JSONResponse(status_code=200, content=_promise_to_dict(promise))

@router.post("/api/promises/{promise_id}/break")
async def api_break_promise(promise_id: str, request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    import json
    body = await request.body()
    reason = "Payment not received by promised date"
    if body:
        try:
            payload = json.loads(body)
            reason = payload.get("reason", reason)
        except json.JSONDecodeError:
            pass
            
    if not hasattr(container.promises, "get"):
        return JSONResponse(status_code=500, content={"error": "Promises not configured"})
        
    promise = container.promises.get(promise_id)
    if not promise:
        return JSONResponse(status_code=404, content={"error": "Promise not found"})
        
    status = promise.status if not isinstance(promise, dict) else promise.get("status")
    if status != "promised":
        return JSONResponse(status_code=400, content={"error": f"Promise is {status}, cannot break"})
        
    if hasattr(container.promises, "update_status"):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        updated = container.promises.update_status(
            promise_id,
            "broken",
            metadata={"break_reason": reason, "broken_at": now.isoformat()},
            expired_at=now
        )
        if updated:
            promise = updated
            
    item_id = promise.recovery_item_id if not isinstance(promise, dict) else promise.get("recovery_item_id")
    
    container.audit_log.log(
        recovery_item_id=item_id,
        actor="system",
        action="promise_broken",
        reason=f"Promise broken: {reason}",
        metadata={"promise_id": promise_id, "break_reason": reason},
    )
    
    from app.dashboard_api import _promise_to_dict
    return JSONResponse(status_code=200, content=_promise_to_dict(promise))


@router.post("/api/promises/extract")
async def api_extract_hinglish_promise(request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Extract structured promise-to-pay intent from Hinglish customer text."""
    import json
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    text = payload.get("text", "")
    item_id = payload.get("item_id")

    from app.services.hinglish_promise import HinglishPromiseExtractor
    extractor = HinglishPromiseExtractor()
    extracted = extractor.extract(text)

    if item_id:
        container.audit_log.log(
            recovery_item_id=item_id,
            actor="agent",
            action="promise_extracted",
            reason=f"Hinglish promise extracted with intent '{extracted.intent}' (confidence={extracted.confidence})",
            metadata=extracted.to_dict(),
        )

    return JSONResponse(status_code=200, content=extracted.to_dict())
