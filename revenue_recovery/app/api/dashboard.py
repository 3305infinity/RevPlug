from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer

router = APIRouter()

def _validate_program_config(updates: dict[str, Any]) -> list[str]:
    errors = []
    for program_key, program_config in updates.items():
        if not isinstance(program_config, dict):
            continue
        if "max_retry_attempts" in program_config:
            val = program_config["max_retry_attempts"]
            if not isinstance(val, int) or val > 10:
                errors.append(f"{program_key}: max_retry_attempts must be <= 10, got {val}")
            if not isinstance(val, int) or val < 1:
                errors.append(f"{program_key}: max_retry_attempts must be >= 1, got {val}")
        if "allowed_actions" in program_config:
            actions = program_config["allowed_actions"]
            if isinstance(actions, list) and "retry_payment" in actions:
                if "fraud" in program_key.lower():
                    errors.append(f"{program_key}: retry_payment is not allowed for fraud program")
        if "confidence_threshold" in program_config:
            val = program_config["confidence_threshold"]
            if isinstance(val, (int, float)) and val < 0.5:
                errors.append(f"{program_key}: confidence_threshold must be >= 0.5, got {val}")
    return errors

def _make_item_stub_from_dict(item) -> Any:
    from datetime import datetime, timezone
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    if isinstance(item, RecoveryItem):
        return item
    return RecoveryItem(
        id=item.get("id", "") if isinstance(item, dict) else "",
        source_type=SourceType(item.get("source_type", "payment_failure")) if isinstance(item, dict) else SourceType.PAYMENT_FAILURE,
        external_id=item.get("external_id", "") if isinstance(item, dict) else "",
        customer_id=item.get("customer_id", "") if isinstance(item, dict) else "",
        amount_minor=item.get("amount_minor", 0) if isinstance(item, dict) else 0,
        currency=item.get("currency", "INR") if isinstance(item, dict) else "INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus(item.get("status", "detected")) if isinstance(item, dict) else RecoveryStatus.DETECTED,
        root_cause=item.get("root_cause") if isinstance(item, dict) else None,
        metadata=item.get("metadata", {}) if isinstance(item, dict) else {},
    )

def _audit_to_dict(event) -> dict[str, Any]:
    return {
        "id": event.id,
        "recovery_item_id": event.recovery_item_id,
        "actor": event.actor,
        "action": event.action,
        "reason": event.reason,
        "metadata": event.metadata,
        "timestamp": event.timestamp.isoformat(),
    }

@router.get("/api/dashboard/summary")
def api_dashboard_summary(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    from app.dashboard_api import build_dashboard_summary
    return build_dashboard_summary(container)

@router.get("/api/recovery-items")
def api_recovery_items(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_recovery_items_list
    return build_recovery_items_list(container)

@router.get("/api/recovery-items/{item_id}")
def api_recovery_item_detail(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.dashboard_api import build_case_detail
    detail = build_case_detail(container, item_id)
    if detail is None:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return JSONResponse(status_code=200, content=detail)

@router.get("/api/customers")
def api_list_customers(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_customers_list
    return build_customers_list(container)

@router.get("/api/customers/{customer_id}")
def api_customer_detail(customer_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.dashboard_api import build_customer_economics
    data = build_customer_economics(container, customer_id)
    if not data.get("total_cases"):
        return JSONResponse(status_code=404, content={"error": "Customer not found"})
    return JSONResponse(status_code=200, content=data)

@router.get("/api/recovery-items/{item_id}/lifecycle")
def api_lifecycle(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.dashboard_api import build_lifecycle
    data = build_lifecycle(container, item_id)
    if not data:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return JSONResponse(status_code=200, content=data)

@router.get("/api/time-series/recovered-by-day")
def api_ts_recovered(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_recovered_by_day
    return build_recovered_by_day(container)

@router.get("/api/time-series/revenue-at-risk-by-day")
def api_ts_risk(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_revenue_at_risk_by_day
    return build_revenue_at_risk_by_day(container)

@router.get("/api/time-series/attempts-by-day")
def api_ts_attempts(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_attempts_by_day
    return build_attempts_by_day(container)

@router.get("/api/time-series/stopped-by-reason")
def api_ts_stopped(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_stopped_by_reason
    return build_stopped_by_reason(container)

@router.get("/api/reviews/pending")
def api_reviews_pending(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_recovery_items_list
    all_items = build_recovery_items_list(container)
    return [i for i in all_items if i["status"] in ("escalated", "failed")]

@router.get("/api/programs/config")
def api_programs_config(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    config = getattr(container, "_program_config", None)
    if config is None:
        config = {
            "payment_failure": {
                "enabled": True,
                "max_retry_attempts": 3,
                "escalation_threshold": 0.5,
                "min_amount_minor": 100,
                "allowed_actions": ["retry_payment", "send_payment_link", "escalate_human", "stop_recovery"],
            },
            "checkout_abandonment": {"enabled": False},
            "subscription_failure": {"enabled": False},
            "overdue_invoice": {"enabled": False},
        }
        container._program_config = config
    return config

@router.get("/api/controls")
def api_controls() -> dict[str, Any]:
    return {
        "max_payment_retries": 3,
        "customer_opt_out": "Enabled",
        "fraud_retry_protection": "Enabled",
        "recovery_deadline": "24h",
        "promise_expiry_protection": "Enabled",
        "policy_enforcement": "Mandatory",
        "human_override": "Disabled",
    }

@router.put("/api/programs/config")
async def api_update_program_config(request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    import json
    body = await request.body()
    try:
        updates = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    validation_errors = _validate_program_config(updates)
    if validation_errors:
        return JSONResponse(status_code=400, content={"errors": validation_errors})
    config = getattr(container, "_program_config", None)
    if config is None:
        config = {
            "payment_failure": {
                "enabled": True,
                "max_retry_attempts": 3,
                "escalation_threshold": 0.5,
                "min_amount_minor": 100,
                "allowed_actions": ["retry_payment", "send_payment_link", "escalate_human", "stop_recovery"],
            },
            "checkout_abandonment": {"enabled": False},
            "subscription_failure": {"enabled": False},
            "overdue_invoice": {"enabled": False},
        }
    for key, value in updates.items():
        if key in config:
            config[key].update(value)
    container._program_config = config
    container.audit_log.log(
        recovery_item_id="program_config",
        actor="human",
        action="program_config_updated",
        reason="Program configuration updated",
        metadata={"updates": updates},
    )
    return JSONResponse(status_code=200, content={"status": "updated", "config": config})

@router.post("/api/recovery-items/{item_id}/approve")
async def api_approve_item(item_id: str, request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    body = await request.body()
    payload = {}
    if body:
        import json
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    action = payload.get("action", "escalate_human")

    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)

    if item is None:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    stub = _make_item_stub_from_dict(item)
    # Evaluate guard with QUEUED status on stub so terminal_state_absorbing does not
    # short-circuit evaluation of actual business rules (payment succeeded, opt-out, promise, fraud)
    from app.domain.models import RecoveryStatus
    stub = stub.__class__(
        id=item.id,
        source_type=item.source_type,
        external_id=item.external_id,
        customer_id=item.customer_id,
        amount_minor=item.amount_minor,
        currency=item.currency,
        created_at=item.created_at,
        due_at=item.due_at,
        status=RecoveryStatus.QUEUED,
        root_cause=item.root_cause,
        recovery_probability=item.recovery_probability,
        expected_recovery_value=item.expected_recovery_value,
        intervention_cost=item.intervention_cost,
        failure_category=item.failure_category,
        provider=item.provider,
        provider_event_id=item.provider_event_id,
        actual_recovery_value=item.actual_recovery_value,
        recovery_status=item.recovery_status,
        score_version=item.score_version,
        scoring_reason=item.scoring_reason,
        priority=item.priority,
        stopped_reason=item.stopped_reason,
        stopped_rule=item.stopped_rule,
        metadata=item.metadata,
    )

    from app.policies.engine import InterventionPolicy
    from app.policies.stopping_rules import StoppingRules
    from app.policies.guard import DefaultRecoveryGuard

    opted_out = set()
    if hasattr(container.recovery_items, "list_all"):
        try:
            for it in container.recovery_items.list_all():
                it_dict = it if isinstance(it, dict) else (it.__dict__ if hasattr(it, "__dict__") else {})
                meta = it_dict.get("metadata") or {}
                if meta.get("customer_opted_out"):
                    cid = it_dict.get("customer_id")
                    if cid:
                        opted_out.add(cid)
        except Exception:
            pass

    policy = InterventionPolicy(max_retry_attempts=3, opted_out_customer_ids=frozenset(opted_out))
    stopping_rules = StoppingRules(max_attempts=3, opted_out_customer_ids=frozenset(opted_out))
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy)

    guard_decision = guard.evaluate(
        stub,
        action,
        container=container,
        promises=getattr(container, "promises", None),
    )

    if guard_decision.allowed:
        container.audit_log.log(
            recovery_item_id=item_id, actor="human", action="human_approved",
            reason=f"Human approved action: {action}",
            metadata={"action": action, "policy_rule": guard_decision.rule, "reason_code": guard_decision.reason_code},
        )
        return JSONResponse(status_code=200, content={
            "status": "approved", "action": action,
            "policy_rule": guard_decision.rule,
            "reason_code": guard_decision.reason_code,
            "message": f"Action '{action}' approved by human and safety guard",
        })
    else:
        container.audit_log.log(
            recovery_item_id=item_id, actor="human", action="human_approval_denied_by_safety",
            reason=f"Human approved '{action}' but safety guard blocked: {guard_decision.reason}",
            metadata={"action": action, "policy_rule": guard_decision.rule, "reason_code": guard_decision.reason_code, "decision_type": guard_decision.decision_type},
        )
        return JSONResponse(status_code=200, content={
            "status": "denied_by_policy", "action": action,
            "policy_rule": guard_decision.rule,
            "reason_code": guard_decision.reason_code,
            "decision_type": guard_decision.decision_type,
            "message": f"Action '{action}' blocked by safety guard: {guard_decision.reason}",
        })

@router.post("/api/recovery-items/{item_id}/reject")
async def api_reject_item(item_id: str, request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)

    if item is None:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    from app.domain.models import RecoveryStatus
    from app.domain.transitions import DefaultStateMachine
    sm = DefaultStateMachine()
    result = sm.transition(item, RecoveryStatus.STOPPED)
    if result.applied:
        container.recovery_items.save(result.item)

    container.audit_log.log(
        recovery_item_id=item_id, actor="human", action="human_rejected",
        reason="Human rejected the recovery case", metadata={},
    )
    return JSONResponse(status_code=200, content={
        "status": "rejected", "message": f"Recovery case {item_id} stopped by human",
    })

@router.get("/api/recovery-items/{item_id}/agent-trace")
def api_agent_trace(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    events = []
    if hasattr(container.audit_log, "events_for"):
        events = [
            _audit_to_dict(e) for e in container.audit_log.events_for(item_id)
        ]
    return JSONResponse(status_code=200, content={"item_id": item_id, "agent_events": events})

@router.get("/api/recovery-items/{item_id}/audit-trail")
def api_audit_trail(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get complete, chronologically ordered audit trail for a recovery item."""
    events = []
    if hasattr(container.audit_log, "events_for"):
        events = [_audit_to_dict(e) for e in container.audit_log.events_for(item_id)]
    return JSONResponse(status_code=200, content={
        "item_id": item_id,
        "total_events": len(events),
        "timeline": events,
    })

@router.get("/api/audit-events")
def api_audit_events(filter: str = "all", container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_audit_events_list
    return build_audit_events_list(container, filter_by=filter)

@router.get("/api/provider-events/{provider_event_id}")
def api_provider_event(provider_event_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    provider_events = getattr(container, "provider_events", None)
    if provider_events is None:
        return JSONResponse(status_code=404, content={"error": "Provider events not available"})
    event = provider_events.get_by_provider_event("razorpay", provider_event_id)
    if event is None:
        return JSONResponse(status_code=404, content={"error": "Provider event not found"})
    return JSONResponse(status_code=200, content={
        "provider": event.provider,
        "provider_event_id": event.provider_event_id,
        "event_type": event.event_type,
        "processing_status": event.processing_status,
        "received_at": event.received_at.isoformat() if event.received_at else None,
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "recovery_item_id": event.recovery_item_id,
        "error_message": event.error_message,
    })

@router.get("/api/next-action/{item_id}")
def api_next_action(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    from app.policies.engine import InterventionPolicy
    from app.policies.guard import DefaultRecoveryGuard
    from app.policies.stopping_rules import StoppingRules

    stopping_rules = StoppingRules(max_attempts=3)
    policy_engine = InterventionPolicy(max_retry_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)

    decisions = []
    if hasattr(container.decisions, "list_by_recovery_item_id"):
        decisions = container.decisions.list_by_recovery_item_id(item_id)

    last_proposal_action = None
    last_policy_rule = None
    if decisions:
        last = decisions[-1]
        last_proposal_action = last.get("proposed_action")
        last_policy_rule = last.get("policy_rule")

    guard_decision = guard.evaluate(item, last_proposal_action or "retry_payment", container=container)
    attempt_count = int(item.metadata.get("attempt_count", 0))
    retry_budget = max(0, 3 - attempt_count)

    response = {
        "item_id": item_id,
        "current_status": item.status.value,
        "next_action": last_proposal_action,
        "reason": guard_decision.reason,
        "safety_decision": guard_decision.decision_type,
        "policy_rule": last_policy_rule or guard_decision.rule,
        "stopping_rule": guard_decision.reason_code if not guard_decision.allowed else "none",
        "expected_recovery_value": item.expected_recovery_value,
        "retry_budget_remaining": retry_budget,
    }
    return JSONResponse(status_code=200, content=response)
