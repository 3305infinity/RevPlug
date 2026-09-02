"""Timing intelligence API endpoints for WAIT decision support.

Provides:
- GET /api/timing/{item_id} — Full timing evaluation for an item
- GET /api/timing/{item_id}/signals — Raw timing signals for an item
- POST /api/timing/{item_id}/reschedule — Reschedule a WAIT decision
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer
from app.domain.timing_signals import TimingEvaluation
from app.services.timing_evaluator import TimingEvaluator
from app.services.recovery_scheduler import RecoveryScheduler

router = APIRouter()


def _parse_item_id(item_id: str) -> str:
    return item_id.strip()


@router.get("/api/timing/{item_id}")
async def api_get_timing_evaluation(
    item_id: str,
    request: Request,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    item_id = _parse_item_id(item_id)

    item = container.recovery_items.get_by_id(item_id) if hasattr(container, "recovery_items") else None
    if item is None:
        return JSONResponse(status_code=404, content={"error": f"Item {item_id} not found"})

    promises = None
    if hasattr(container, "promises"):
        promises = container.promises

    recent_incidents: list[dict[str, Any]] = []
    if hasattr(container, "incidents"):
        try:
            incidents = container.incidents.list_all() if hasattr(container.incidents, "list_all") else []
            for inc in incidents:
                if isinstance(inc, dict) and inc.get("item_id") == item_id:
                    recent_incidents.append(inc)
        except Exception:
            pass

    evaluator = TimingEvaluator()

    scheduler = RecoveryScheduler()
    wait_record = scheduler.get_wait_record(item_id)
    wait_count = wait_record.wait_count if wait_record else 0
    last_wait_reason = wait_record.last_wait_reason if wait_record else None
    last_scheduled_for = wait_record.last_scheduled_for if wait_record else None

    evaluation = evaluator.evaluate(
        item=item,
        container=container,
        promises=promises,
        recent_incidents=recent_incidents if recent_incidents else None,
        wait_count=wait_count,
        last_wait_reason=last_wait_reason,
        last_scheduled_for=last_scheduled_for,
    )

    eligible, _, escalation_reason = scheduler.evaluate_wait_eligibility(item, evaluation)

    result = evaluation.to_dict()
    result["wait_eligible"] = eligible
    result["escalation_reason"] = escalation_reason
    result["scheduler"] = scheduler.get_wait_summary(item_id)

    return JSONResponse(content=result)


@router.get("/api/timing/{item_id}/signals")
async def api_get_timing_signals(
    item_id: str,
    request: Request,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    item_id = _parse_item_id(item_id)

    item = container.recovery_items.get_by_id(item_id) if hasattr(container, "recovery_items") else None
    if item is None:
        return JSONResponse(status_code=404, content={"error": f"Item {item_id} not found"})

    promises = None
    if hasattr(container, "promises"):
        promises = container.promises

    recent_incidents: list[dict[str, Any]] = []
    if hasattr(container, "incidents"):
        try:
            incidents = container.incidents.list_all() if hasattr(container.incidents, "list_all") else []
            for inc in incidents:
                if isinstance(inc, dict) and inc.get("item_id") == item_id:
                    recent_incidents.append(inc)
        except Exception:
            pass

    evaluator = TimingEvaluator()
    scheduler = RecoveryScheduler()
    wait_record = scheduler.get_wait_record(item_id)

    evaluation = evaluator.evaluate(
        item=item,
        container=container,
        promises=promises,
        recent_incidents=recent_incidents if recent_incidents else None,
        wait_count=wait_record.wait_count if wait_record else 0,
        last_wait_reason=wait_record.last_wait_reason if wait_record else None,
        last_scheduled_for=wait_record.last_scheduled_for if wait_record else None,
    )

    return JSONResponse(content={
        "item_id": item_id,
        "signals": [s.to_dict() for s in evaluation.signals],
        "evaluated_at": evaluation.evaluated_at.isoformat() if evaluation.evaluated_at else None,
    })


@router.post("/api/timing/{item_id}/reschedule")
async def api_reschedule_wait(
    item_id: str,
    request: Request,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    item_id = _parse_item_id(item_id)

    item = container.recovery_items.get_by_id(item_id) if hasattr(container, "recovery_items") else None
    if item is None:
        return JSONResponse(status_code=404, content={"error": f"Item {item_id} not found"})

    import json
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    requested_scheduled_for_str = payload.get("scheduled_for")
    if not requested_scheduled_for_str:
        return JSONResponse(status_code=400, content={"error": "scheduled_for is required"})

    try:
        requested_scheduled_for = datetime.fromisoformat(requested_scheduled_for_str.replace("Z", "+00:00"))
        if requested_scheduled_for.tzinfo is None:
            requested_scheduled_for = requested_scheduled_for.replace(tzinfo=timezone.utc)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid scheduled_for format. Use ISO format."})

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=30)
    if requested_scheduled_for > horizon:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Requested scheduled_for ({requested_scheduled_for.isoformat()}) exceeds maximum horizon of 30 days.",
                "max_horizon_days": 30,
            },
        )

    from datetime import timedelta as td
    if requested_scheduled_for <= now:
        return JSONResponse(
            status_code=400,
            content={"error": "scheduled_for must be in the future"},
        )

    promises = None
    if hasattr(container, "promises"):
        promises = container.promises

    evaluator = TimingEvaluator()

    scheduler = RecoveryScheduler()
    wait_record = scheduler.get_wait_record(item_id)

    evaluation = evaluator.evaluate(
        item=item,
        container=container,
        promises=promises,
        wait_count=wait_record.wait_count if wait_record else 0,
        last_wait_reason=wait_record.last_wait_reason if wait_record else None,
        last_scheduled_for=wait_record.last_scheduled_for if wait_record else None,
    )

    new_evaluation = TimingEvaluation(
        item_id=item.id,
        timing_decision=evaluation.timing_decision,
        reason_code=evaluation.reason_code,
        reason=f"Rescheduled to {requested_scheduled_for.strftime('%d %b %Y %H:%M')} by operator request. {evaluation.reason}",
        scheduled_for=requested_scheduled_for,
        signals=evaluation.signals,
        evidence=evaluation.evidence + [f"Rescheduled by operator to {requested_scheduled_for.isoformat()}"],
        confidence=0.95,
        policy_status="OPERATOR_OVERRIDE",
        wait_count=evaluation.wait_count,
        blocked_until=requested_scheduled_for,
    )

    scheduler.record_wait(item, new_evaluation)

    container.audit_log.log(
        recovery_item_id=item_id,
        actor="operator",
        action="wait_rescheduled",
        reason=f"WAIT rescheduled to {requested_scheduled_for.isoformat()} by operator request",
        metadata={
            "previous_scheduled_for": (wait_record.last_scheduled_for.isoformat() if wait_record and wait_record.last_scheduled_for else None),
            "new_scheduled_for": requested_scheduled_for.isoformat(),
            "previous_wait_count": wait_record.wait_count if wait_record else 0,
            "new_wait_count": new_evaluation.wait_count,
        },
    )

    return JSONResponse(content={
        "item_id": item_id,
        "rescheduled": True,
        "evaluation": new_evaluation.to_dict(),
        "scheduler": scheduler.get_wait_summary(item_id),
    })
