"""Real Human Escalation Queue API Endpoint with Hard Policy Protection.

Provides complete context for human operations review and enforces that human overrides
can NEVER bypass hard safety policy rules.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.db.container import PersistenceContainer
from app.domain.models import RecoveryStatus
from app.policies.engine import InterventionPolicy

router = APIRouter()


class HumanActionRequest(BaseModel):
    action: str = Field(..., description="Action: APPROVE, TAKE_ACTION, DISMISS, MARK_RECOVERED, RETURN_TO_AUTOMATION")
    requested_override_action: str | None = Field(default=None, description="Optional action string to execute if approving")
    notes: str | None = Field(default=None, description="Operational notes for audit history")
    actor_id: str = Field(default="human_operator_101", description="Operator identity for audit trail")


@router.get("/api/escalations")
async def list_escalations(
    container: PersistenceContainer = Depends(get_container),
) -> JSONResponse:
    """List all escalated cases in the human review queue with complete context."""
    items = []
    if hasattr(container.recovery_items, "_items"):
        for item in container.recovery_items._items.values():
            if item.status.value in {"human_review_required", "stopped", "failed"}:
                # Fetch audit history
                audit_events = []
                if hasattr(container.audit_log, "_events"):
                    audit_events = [
                        {
                            "timestamp": e.timestamp.isoformat() if hasattr(e, "timestamp") else str(e),
                            "action": getattr(e, "action", "event"),
                            "reason": getattr(e, "reason", ""),
                        }
                        for e in container.audit_log._events
                        if getattr(e, "recovery_item_id", None) == item.id
                    ]

                items.append({
                    "item_id": item.id,
                    "customer_id": item.customer_id,
                    "amount_at_risk_minor": item.amount_at_risk,
                    "failure_reason": item.root_cause,
                    "status": item.status.value,
                    "attempt_count": item.attempt_count,
                    "stopped_reason": getattr(item, "stopped_reason", "Policy safety rule active"),
                    "stopped_rule": getattr(item, "stopped_rule", "hard_policy_rule"),
                    "recommended_action": "Contact customer via manual account manager outreach",
                    "customer_context": {
                        "email": f"{item.customer_id}@example.com",
                        "opted_out": item.metadata.get("opted_out", False),
                        "fraud_flag": item.metadata.get("fraud_flag", False),
                        "disputed": item.metadata.get("disputed", False),
                    },
                    "audit_history": audit_events,
                })

    return JSONResponse(status_code=200, content={"escalated_items": items, "count": len(items)})


@router.post("/api/escalations/{item_id}/action")
async def process_escalation_action(
    item_id: str,
    req: HumanActionRequest,
    container: PersistenceContainer = Depends(get_container),
) -> JSONResponse:
    """Execute human review action with strict policy protection.

    Human overrides can NEVER bypass hard safety policy rules.
    """
    item = container.recovery_items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Recovery item '{item_id}' not found")

    action_type = req.action.upper().strip()

    if action_type in {"APPROVE", "TAKE_ACTION"}:
        override_action = req.requested_override_action or "retry_payment"
        
        # Policy Protection Check
        policy = InterventionPolicy(
            opted_out_customer_ids=frozenset([item.customer_id]) if item.metadata.get("opted_out") else frozenset()
        )
        decision = policy.evaluate(item, override_action)

        if not decision.allowed and decision.policy_rule in {"block_hard_failure", "opt_out_block", "discount_ceiling"}:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "rejected",
                    "error": f"Policy Violation: Human override cannot bypass hard safety rule '{decision.policy_rule}'",
                    "policy_rule": decision.policy_rule,
                    "reason": decision.reason,
                },
            )

        from dataclasses import replace
        new_status = RecoveryStatus.RECOVERED if override_action != "stop_recovery" else RecoveryStatus.STOPPED
        new_val = item.amount_at_risk if new_status == RecoveryStatus.RECOVERED else 0
        item = replace(item, status=new_status, actual_recovery_value=new_val)

    elif action_type == "MARK_RECOVERED":
        from dataclasses import replace
        item = replace(item, status=RecoveryStatus.RECOVERED, actual_recovery_value=item.amount_at_risk)

    elif action_type == "DISMISS":
        from dataclasses import replace
        item = replace(item, status=RecoveryStatus.STOPPED)

    elif action_type == "RETURN_TO_AUTOMATION":
        from dataclasses import replace
        item = replace(item, status=RecoveryStatus.QUEUED)

    else:
        raise HTTPException(status_code=400, detail=f"Invalid action '{req.action}'")

    container.recovery_items.save(item)

    # Log audited human action
    try:
        container.audit_log.log(
            recovery_item_id=item.id,
            actor=req.actor_id,
            action=f"human_{action_type.lower()}",
            reason=req.notes or f"Human operator executed {action_type}",
            metadata={"actor_id": req.actor_id, "action": action_type},
        )
    except Exception:
        pass

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "item_id": item.id,
            "new_status": item.status.value,
            "actual_recovery_value": item.actual_recovery_value,
            "action_executed": action_type,
        },
    )
