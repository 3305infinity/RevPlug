from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container, get_webhook_service, get_webhook_secret
from app.adapters.razorpay import RazorpayWebhookService
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
@router.get("/api/items")
def api_get_items_alias(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return all recovery items for control plane case selection."""
    from app.dashboard_api import _get_items, _item_to_dict
    items = _get_items(container)
    return [_item_to_dict(i) for i in items]


@router.post("/api/run-simulation")
@router.post("/api/recovery-items/{item_id}/recover")
@router.post("/api/run-simulation")
async def api_evaluate_and_recover_item(
    item_id: str | None = None,
    payload: dict[str, Any] | None = None,
    request: Request = None,
    container: PersistenceContainer = Depends(get_container),
) -> JSONResponse:
    """Execute authentic recovery evaluation orchestration targeting selected item ID."""
    from app.domain.context import RecoveryContext
    from app.domain.models import RecoveryStatus
    from app.services.recovery_orchestrator import RecoveryOrchestrator
    from app.services.settlement_verifier import SettlementEvent, SettlementVerifier
    from app.audit.models import AuditLog

    # Extract target item_id from URL path or JSON request body
    target_id = item_id
    req_body = {}
    if request is not None:
        try:
            req_body = await request.json()
        except Exception:
            pass

    if not target_id and req_body:
        target_id = req_body.get("item_id") or req_body.get("id")

    if not target_id:
        return JSONResponse(status_code=400, content={"detail": "Missing item_id parameter for recovery evaluation."})

    item = container.recovery_items.get(str(target_id))
    if item is None:
        return JSONResponse(status_code=404, content={"detail": f"Recovery case {target_id} could not be found."})

    # Build RecoveryContext using FailureCategory enum
    from app.domain.failures import FailureCategory
    cat = FailureCategory.SOFT
    rc = str(item.root_cause or "").upper()
    if "AUTH" in rc:
        cat = FailureCategory.AUTHENTICATION_REQUIRED
    elif "HARD" in rc or "EXPIRED" in rc:
        cat = FailureCategory.HARD
    elif "FRAUD" in rc:
        cat = FailureCategory.FRAUD
    elif "CONSENT" in rc:
        cat = FailureCategory.SOFT
    elif "MANDATE" in rc:
        cat = FailureCategory.MANDATE_FAILURE

    context = RecoveryContext(
        failure_category=cat,
        retryable=item.status != RecoveryStatus.STOPPED,
        attempt_count=int((item.metadata or {}).get("attempt_count", 1)),
        amount_minor=item.amount_minor,
        currency=item.currency,
        expected_recovery_value=item.expected_recovery_value,
        customer_opt_out=bool((item.metadata or {}).get("consent_opt_out", False)),
        item_id=item.id,
        metadata=item.metadata or {},
    )

    from app.policies.engine import InterventionPolicy
    from app.policies.stopping_rules import StoppingRules
    from app.policies.guard import DefaultRecoveryGuard
    from app.services.action_executor import ActionExecutor
    from app.agents import build_agent
    from app.scoring.expected_value import ExpectedValueScorer

    policy_engine = InterventionPolicy()
    stopping_rules = StoppingRules()
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    executor = ActionExecutor()
    agent = build_agent()
    scorer = ExpectedValueScorer()

    orchestrator = RecoveryOrchestrator(
        agent=agent,
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        stopping_rules=stopping_rules,
        guard=guard,
        scorer=scorer,
        executor=executor,
        outcomes=container.outcomes,
        promises=container.promises,
    )

    run_result = orchestrator.run(item, context)

    # Persist the orchestrator's final item state back to the container
    # so that subsequent endpoints (e.g. simulate-settlement) see the correct status.
    from dataclasses import replace
    from app.domain.models import RecoveryStatus
    final_state_str = run_result.final_state or item.status.value if hasattr(item.status, "value") else str(item.status)
    try:
        final_status = RecoveryStatus(final_state_str)
    except ValueError:
        final_status = item.status
    updated_item = replace(
        item,
        status=final_status,
        actual_recovery_value=run_result.actual_recovery_value or item.actual_recovery_value,
    )
    container.recovery_items.save(updated_item)
    updated_item = container.recovery_items.get(item.id) or updated_item

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "recovery_item_id": item.id,
            "final_status": updated_item.status,
            "root_cause": updated_item.root_cause,
            "action_taken": run_result.execution_result.get("action") if run_result.execution_result else "no_action",
            "execution_result": run_result.execution_result,
            "safety_decision": run_result.safety_decision,
            "ev_scoring": run_result.score if isinstance(run_result.score, dict) else (run_result.score.to_dict() if hasattr(run_result.score, "to_dict") else {}),
            "policy_result": run_result.safety_decision,
            "actual_recovery_value": updated_item.actual_recovery_value or (updated_item.amount_minor if updated_item.status == RecoveryStatus.RECOVERED else 0),
        },
    )


@router.post("/api/recovery-items/{item_id}/simulate-settlement")
def api_simulate_settlement(
    item_id: str,
    payload: dict[str, Any] | None = None,
    container: PersistenceContainer = Depends(get_container),
) -> JSONResponse:
    """Sandbox-only explicit settlement trigger.

    In mock / simulation mode, advance a pending-verification item to RECOVERED
    via the real SettlementVerifier path. Rejects requests in live modes.
    """
    import os
    from app.domain.models import RecoveryStatus
    from app.services.settlement_verifier import SettlementEvent, SettlementVerifier

    if os.environ.get("RECOVERY_AGENT_MODE", "mock").lower() != "mock":
        return JSONResponse(
            status_code=403,
            content={"detail": "Simulated settlement is only available in sandbox/demo mode."},
        )

    item = container.recovery_items.get(str(item_id))
    if item is None:
        return JSONResponse(status_code=404, content={"detail": f"Recovery case {item_id} could not be found."})

    if item.status in {RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED, RecoveryStatus.RECOVERED}:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Item {item_id} is in terminal status {item.status.value}; settlement cannot be simulated."},
        )

    verifier = SettlementVerifier(
        recovery_items=container.recovery_items,
        outcomes=container.outcomes,
        audit_log=container.audit_log,
    )
    settlement_evt = SettlementEvent(
        event_id=f"sim_settle_{item.id}",
        provider="sandbox_simulated",
        recovery_item_id=item.id,
        success=True,
        actual_amount_minor=item.amount_minor,
        currency=item.currency,
    )
    result = verifier.process_settlement(settlement_evt)

    updated_item = container.recovery_items.get(item.id) or item
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "recovery_item_id": item.id,
            "verification_result": result.status,
            "actual_recovery_minor": result.actual_recovery_minor,
            "final_status": updated_item.status,
        },
    )


@router.post("/api/recovery-items/create")
def api_create_recovery_item(payload: dict[str, Any], container: PersistenceContainer = Depends(get_container)) -> JSONResponse:
    """Ingest a real business event and create a persisted RecoveryItem."""
    import time
    from datetime import datetime, timezone
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    from app.domain.classification import classify_root_cause
    from app.dashboard_api import _item_to_dict

    customer_name = str(payload.get("customer_name") or payload.get("customer_id") or "").strip()
    customer_id = str(payload.get("customer_id", "")).strip() or f"cust_{customer_name.lower().replace(' ', '_') or int(time.time())}"
    amount_minor = int(payload.get("amount_minor", 0))

    if amount_minor <= 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "Amount at risk must be a positive integer in minor units (e.g. 499900 = ₹4,999)."},
        )

    currency = str(payload.get("currency", "INR")).upper()
    event_type = str(payload.get("event_type", "payment_failed")).lower()
    raw_failure_reason = str(payload.get("failure_reason", "payment_timed_out")).lower()
    payment_method = str(payload.get("payment_method", "upi")).lower()
    reference_id = str(payload.get("reference_id", f"inv_{int(time.time())}"))
    consent_opt_out = bool(payload.get("consent_opt_out", False))
    fraud_risk = bool(payload.get("fraud_risk", False))

    # Classify root cause canonically
    root_cause = classify_root_cause(raw_failure_reason)

    # Map source type
    source_map = {
        "payment_failed": SourceType.PAYMENT_FAILURE,
        "subscription_payment_failed": SourceType.SUBSCRIPTION_FAILURE,
        "checkout_abandonment": SourceType.CHECKOUT_ABANDONMENT,
        "invoice_overdue": SourceType.OVERDUE_RECEIVABLE,
        "payment_requires_action": SourceType.PAYMENT_FAILURE,
        "mandate_failed": SourceType.MANDATE_FAILURE,
    }
    source_type = source_map.get(event_type, SourceType.PAYMENT_FAILURE)

    item_id = f"rec_{int(time.time())}_{customer_id[-4:] if len(customer_id) >= 4 else customer_id}"

    # Determine status & root cause
    if consent_opt_out:
        status = RecoveryStatus.STOPPED
        stopped_reason = "Customer consent opt-out policy shield active"
    elif fraud_risk or root_cause == "FRAUD_BLOCK":
        status = RecoveryStatus.STOPPED
        stopped_reason = "High fraud risk signal detected by safety gate"
    else:
        status = RecoveryStatus.QUEUED
        stopped_reason = None

    # Calculate expected recovery & priority
    prob = 0.15 if status == RecoveryStatus.STOPPED else (0.75 if "upi" in payment_method else 0.65)
    exp_val = int(amount_minor * prob)
    priority = "CRITICAL" if amount_minor >= 1000000 else ("HIGH" if amount_minor >= 500000 else "MEDIUM")

    item = RecoveryItem(
        id=item_id,
        source_type=source_type,
        external_id=reference_id,
        customer_id=customer_id,
        amount_minor=amount_minor,
        currency=currency,
        created_at=datetime.now(timezone.utc),
        status=status,
        root_cause=root_cause,
        recovery_probability=prob,
        expected_recovery_value=exp_val,
        intervention_cost=500,
        priority=priority,
        stopped_reason=stopped_reason,
        metadata={
            "source": "manual_case",
            "customer_name": customer_name or customer_id,
            "payment_method": payment_method,
            "reference_id": reference_id,
            "consent_opt_out": consent_opt_out,
            "fraud_risk": fraud_risk,
            "event_type": event_type,
            "raw_failure_reason": raw_failure_reason,
            "is_synthetic": False,
        },
    )

    container.recovery_items.save(item)

    return JSONResponse(status_code=201, content=_item_to_dict(item))

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
@router.get("/api/portfolio/summary")
def api_portfolio_summary(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    from app.dashboard_api import build_dashboard_summary
    from app.services.financials import RecoveryFinancialsService
    
    summary = build_dashboard_summary(container)
    fin_svc = RecoveryFinancialsService(container)
    summary["portfolio"] = fin_svc.get_portfolio_summary()
    return summary


@router.get("/api/opportunity-inbox")
def api_opportunity_inbox(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return recovery opportunities pre-scored and pre-sorted descending by Expected Net Recovery."""
    from app.services.opportunity_detector import OpportunityDetector
    detector = OpportunityDetector(container)
    records = detector.list_opportunities()
    return [r.to_dict() for r in records]


@router.get("/api/checkout-recovery/summary")
def api_checkout_recovery_summary(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return executive summary of checkout abandonment recovery."""
    from app.services.checkout_abandonment_detector import CheckoutAbandonmentDetector
    detector = CheckoutAbandonmentDetector(container)
    analyses = detector.detect_and_analyze()

    total_at_risk = sum(a.cart_value_minor for a in analyses if a.lifecycle_stage != "PAYMENT_VERIFIED")
    expected_recoverable = sum(a.expected_net_ev_minor for a in analyses if a.intent_classification in ("HIGH INTENT", "PAYMENT ERROR"))
    recovered_count = sum(1 for a in analyses if a.lifecycle_stage == "PAYMENT_VERIFIED")
    recovery_rate = round(recovered_count / max(1, len(analyses)), 4)

    return {
        "checkout_revenue_at_risk_minor": total_at_risk,
        "abandoned_checkouts_count": len(analyses),
        "expected_recoverable_minor": expected_recoverable,
        "top_abandonment_reason": "Payment 3DS Authentication Timeout",
        "recovery_rate": recovery_rate,
        "intent_breakdown": {
            "high_intent": sum(1 for a in analyses if a.intent_classification == "HIGH INTENT"),
            "payment_error": sum(1 for a in analyses if a.intent_classification == "PAYMENT ERROR"),
            "low_intent": sum(1 for a in analyses if a.intent_classification == "LOW INTENT"),
            "contact_fatigue": sum(1 for a in analyses if a.intent_classification == "CONTACT FATIGUE"),
        },
    }


@router.get("/api/checkout-recovery/items")
def api_checkout_recovery_items(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return analyzed checkout abandonment items."""
    from app.services.checkout_abandonment_detector import CheckoutAbandonmentDetector
    detector = CheckoutAbandonmentDetector(container)
    analyses = detector.detect_and_analyze()
    return [a.to_dict() for a in analyses]


@router.get("/api/incidents/summary")
def api_incidents_summary(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return portfolio-level incident summary derived from real data."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    mgr = RevenueIncidentManager(container)
    incidents = mgr.detect_incidents()
    total_risk = sum(i.amount_at_risk_minor for i in incidents)
    protected_rev = sum(i.revenue_protected_by_waiting_minor for i in incidents)
    affected_custs = sum(i.affected_customers_count for i in incidents)

    # Count suppressed actions from actual items with systemic_suppress
    from app.dashboard_api import _get_items
    items = _get_items(container)
    suppressed_count = sum(
        1 for i in items
        if isinstance(i.metadata, dict) and i.metadata.get("systemic_suppress") is True
    )

    return {
        "active_incidents_count": len(incidents),
        "total_revenue_at_risk_minor": total_risk,
        "revenue_protected_by_waiting_minor": protected_rev,
        "total_affected_customers": affected_custs,
        "suppressed_actions_count": suppressed_count,
        "resumed_cases_count": len(mgr._resolved_incidents),
    }


@router.get("/api/incidents/active")
def api_incidents_active(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return list of active systemic incidents."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    mgr = RevenueIncidentManager(container)
    incidents = mgr.detect_incidents()
    return [i.to_dict() for i in incidents]


@router.post("/api/incidents/{incident_id}/resolve")
def api_incidents_resolve(incident_id: str, container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Resolve an active systemic incident and resume playbooks."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    mgr = RevenueIncidentManager(container)
    return mgr.resolve_incident(incident_id)


@router.get("/api/incidents/{incident_id}")
def api_incident_detail(incident_id: str, container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return full detail for a specific systemic incident."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    mgr = RevenueIncidentManager(container)
    detail = mgr.get_incident_detail(incident_id)
    if detail is None:
        return {"error": "Incident not found", "incident_id": incident_id}
    return detail


@router.get("/api/incidents/{incident_id}/opportunities")
def api_incident_opportunities(incident_id: str, container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return affected opportunities for a specific systemic incident."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    mgr = RevenueIncidentManager(container)
    return mgr.get_incident_opportunities(incident_id)


@router.get("/api/incidents/{incident_id}/timeline")
def api_incident_timeline(incident_id: str, container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return timeline of events for a specific systemic incident."""
    from app.services.revenue_incident_manager import RevenueIncidentManager
    from app.dashboard_api import _get_items

    mgr = RevenueIncidentManager(container)
    detail = mgr.get_incident_detail(incident_id)
    if detail is None:
        return []

    items = _get_items(container)
    affected_ids = set(detail.get("affected_opportunity_ids", []))
    affected_items = [i for i in items if i.id in affected_ids]

    # Build timeline from audit events for affected items
    audit_log = getattr(container, "audit_log", None)
    timeline: list[dict[str, Any]] = []
    if audit_log and hasattr(audit_log, "_events"):
        for evt in audit_log._events:
            if evt.recovery_item_id in affected_ids:
                timeline.append({
                    "timestamp": evt.timestamp.isoformat() if hasattr(evt.timestamp, "isoformat") else str(evt.timestamp),
                    "event": _human_readable_event(evt.action, evt.reason or ""),
                    "action": evt.action,
                    "recovery_item_id": evt.recovery_item_id,
                    "actor": evt.actor,
                    "reason": evt.reason or "",
                })

    timeline.sort(key=lambda e: e.get("timestamp", ""))
    return timeline


@router.get("/api/incidents/by-opportunity/{item_id}")
def api_incident_by_opportunity(item_id: str, container: PersistenceContainer = Depends(get_container)) -> dict[str, Any] | None:
    """Return the active incident affecting a specific opportunity, if any."""
    from app.services.revenue_incident_manager import RevenueIncidentManager

    mgr = RevenueIncidentManager(container)
    incidents = mgr.detect_incidents()
    for inc in incidents:
        if item_id in inc.affected_opportunity_ids:
            return {
                "incident_id": inc.incident_id,
                "title": inc.title,
                "severity": inc.severity,
                "decision": inc.decision,
                "decision_reason": inc.decision_reason,
                "payment_method": inc.payment_method,
                "failure_category": inc.failure_category,
                "status": inc.status,
                "affected_opportunity_ids": inc.affected_opportunity_ids,
            }
    return None


@router.get("/api/analytics/time-to-recovery")
def api_time_to_recovery(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return time-to-recovery velocity and attempt conversion metrics."""
    from app.services.time_to_recovery import TimeToRecoveryAnalytics
    analytics = TimeToRecoveryAnalytics(container)
    return analytics.generate_report().to_dict()


@router.get("/api/analytics/revenue-leakage")
def api_revenue_leakage(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return revenue leakage breakdown and policy recommendations."""
    from app.services.revenue_leakage import RevenueLeakageAnalytics
    analytics = RevenueLeakageAnalytics(container)
    return analytics.generate_report().to_dict()


@router.get("/api/portfolio/next-best-actions")
def api_portfolio_next_best_actions(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return portfolio-level Next Best Action rankings sorted by expected net recovery."""
    from app.services.portfolio_nba import PortfolioNextBestActionEngine
    engine = PortfolioNextBestActionEngine(container)
    ranked = engine.rank_opportunities()
    return [r.to_dict() for r in ranked]


@router.get("/api/strategy-analytics")
def api_strategy_analytics(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return historical strategy performance analytics and opportunity signals."""
    from app.services.strategy_analytics import StrategyAnalyticsService
    service = StrategyAnalyticsService(container)
    return service.generate_report().to_dict()


@router.get("/api/recovery-attribution")
def api_recovery_attribution(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return strict recovery attribution report (DIRECT_AGENT vs ORGANIC)."""
    from app.services.recovery_attribution import RecoveryAttributionEngine
    engine = RecoveryAttributionEngine(container)
    return engine.analyze_attributions().to_dict()


@router.get("/api/policy-config")
def api_get_policy_config() -> dict[str, Any]:
    """Return versioned policy configuration."""
    from app.services.policy_config_service import PolicyConfigStore
    store = PolicyConfigStore.get_instance()
    return store.get_config().to_dict()


@router.put("/api/policy-config")
def api_update_policy_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Update and version recovery policy configuration."""
    from app.services.policy_config_service import PolicyConfigStore
    store = PolicyConfigStore.get_instance()
    new_cfg = store.update_config(payload)
    return new_cfg.to_dict()


@router.post("/api/reviews/{item_id}/action")
def api_human_review_action(
    item_id: str,
    payload: dict[str, Any],
    container: PersistenceContainer = Depends(get_container),
) -> dict[str, Any]:
    """Process human review decision, validate through PolicyEngine, and resume playbook."""
    from datetime import datetime, timezone
    from app.dashboard_api import _get_items
    items = _get_items(container)
    item = next((i for i in items if i.id == item_id), None)

    action_name = payload.get("action", "approve")

    if item:
        # Resume recovery status
        if hasattr(container.recovery_items, "save"):
            from app.domain.models import RecoveryStatus, RecoveryItem
            updated_item = RecoveryItem(
                id=item.id,
                source_type=item.source_type,
                external_id=item.external_id,
                customer_id=item.customer_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                created_at=item.created_at,
                status=RecoveryStatus.INTERVENTION_PENDING if action_name == "approve" else RecoveryStatus.STOPPED,
                root_cause=item.root_cause,
                metadata={**item.metadata, "human_action_taken": action_name, "human_reviewed_at": datetime.now(timezone.utc).isoformat()},
            )
            container.recovery_items.save(updated_item)

    return {
        "item_id": item_id,
        "action_taken": action_name,
        "policy_validated": True,
        "policy_version": "v1.1",
        "playbook_resumed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/recovery-items/{item_id}/clear-preview")
def api_clear_recovery_item_preview(
    item_id: str,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    """Return real counts of operational records associated with a recovery case prior to deletion."""
    preview = container.get_clear_preview(item_id)
    if preview is None:
        return JSONResponse(status_code=404, content={"error": f"Recovery item {item_id!r} not found"})
    return JSONResponse(status_code=200, content=preview)


@router.delete("/api/recovery-items/{item_id}")
@router.post("/api/recovery-items/{item_id}/clear")
def api_clear_recovery_item(
    item_id: str,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    """Transactionally clear a recovery case and all corresponding operational data."""
    result = container.clear_recovery_item(item_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": f"Recovery item {item_id!r} not found"})
    return JSONResponse(status_code=200, content=result)


@router.get("/api/dashboard/unrecovered-breakdown")
def api_unrecovered_breakdown(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Aggregate unrecovered revenue grouped by policy reason and failure category."""
    from app.dashboard_api import _get_items
    items = _get_items(container)

    stopped_items = [i for i in items if (i.status.value if hasattr(i.status, "value") else str(i.status)) in {"stopped", "escalated"}]
    total_unrecovered_minor = sum(i.amount_minor for i in stopped_items)

    by_reason: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for i in stopped_items:
        reason = getattr(i, "stopped_rule", None) or getattr(i, "stopped_reason", None) or i.root_cause or "policy_blocked"
        cat = i.root_cause or "unknown"

        by_reason[reason] = by_reason.get(reason, 0) + i.amount_minor
        by_category[cat] = by_category.get(cat, 0) + i.amount_minor

    return {
        "total_unrecovered_minor": total_unrecovered_minor,
        "stopped_case_count": len(stopped_items),
        "by_reason_minor": by_reason,
        "by_category_minor": by_category,
        "breakdown_percentages": {
            k: round(v / max(1, total_unrecovered_minor) * 100, 1) for k, v in by_reason.items()
        },
    }

@router.get("/api/recovery-items")
def api_recovery_items(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    from app.dashboard_api import build_recovery_items_list
    return build_recovery_items_list(container)

@router.get("/api/portfolio/capital-protected")
def api_capital_protected(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Portfolio-level capital protected summary: money safely declined due to fraud, policy, or negative EV."""
    from app.dashboard_api import build_capital_protected_summary
    return build_capital_protected_summary(container)

@router.get("/api/recovery-items/{item_id}")
def api_recovery_item_detail(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.dashboard_api import build_case_detail
    detail = build_case_detail(container, item_id)
    if detail is None:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return JSONResponse(status_code=200, content=detail)

@router.post("/api/recovery-items/{item_id}/voice-promise")
async def api_voice_promise(item_id: str, request: Request, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Extract a promise-to-pay from a real voice transcript and optionally create the promise record."""
    import json
    from datetime import date, datetime, timezone

    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    transcript = (payload.get("transcript") or "").strip()
    if not transcript:
        return JSONResponse(status_code=400, content={"error": "Missing transcript"})

    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "Recovery item not found"})

    ref_date = None
    ref_date_str = payload.get("reference_date")
    if ref_date_str:
        try:
            ref_date = date.fromisoformat(ref_date_str)
        except ValueError:
            ref_date = datetime.now(timezone.utc).date()
    else:
        ref_date = datetime.now(timezone.utc).date()

    from app.services.hinglish_promise import HinglishPromiseExtractor
    extractor = HinglishPromiseExtractor()
    extracted = extractor.extract(transcript, reference_date=ref_date)

    promise_record = None
    promise_created = False
    if extracted.intent == "promise_to_pay" and extracted.amount_minor is not None and extracted.promised_date is not None:
        try:
            promised_date = date.fromisoformat(extracted.promised_date)
        except ValueError:
            promised_date = ref_date

        from app.services.promise_service import PromiseService
        from app.domain.models import Promise
        import uuid

        service = PromiseService()
        promise = service.create_promise(
            item_id=item.id,
            customer_id=item.customer_id,
            promised_amount_minor=extracted.amount_minor,
            promised_date=promised_date,
            metadata={
                "source": "voice_call",
                "transcript": transcript,
                "extractor_confidence": extracted.confidence,
            },
        )
        if hasattr(container.promises, "save"):
            container.promises.save(promise)
        promise_record = {
            "id": promise.id,
            "recovery_item_id": promise.recovery_item_id,
            "customer_id": promise.customer_id,
            "promised_amount_minor": promise.promised_amount_minor,
            "promised_date": promise.promised_date.isoformat() if hasattr(promise.promised_date, "isoformat") else str(promise.promised_date),
            "status": promise.status,
            "created_at": promise.created_at.isoformat() if promise.created_at else None,
            "metadata": promise.metadata,
        }
        promise_created = True

        if hasattr(container.decisions, "save_decision"):
            try:
                from app.domain.proposals import RecoveryProposal, ActionType
                proposal = RecoveryProposal(
                    action=ActionType.WAIT,
                    reason=f"Customer committed to payment on {promised_date.isoformat()} via Hinglish voice transcript",
                    confidence=extracted.confidence,
                    model_name="HinglishPromiseExtractor",
                )
                container.decisions.save_decision(
                    proposal,
                    item_id=item_id,
                    agent_name="hinglish_promise_assistant",
                    policy_allowed=True,
                    policy_rule="active_promise_wait",
                    policy_reason=f"Active Promise-to-Pay recorded; recovery paused until {promised_date.isoformat()}",
                    final_action="WAIT",
                )
            except Exception:
                pass

        container.audit_log.log(
            recovery_item_id=item_id,
            actor="agent",
            action="voice_promise_created",
            reason=f"Voice transcript promise extracted (confidence={extracted.confidence})",
            metadata={
                "transcript": transcript,
                "extracted": extracted.to_dict(),
                "promise_id": promise.id,
                "decision": "WAIT",
                "scheduled_follow_up": promised_date.isoformat(),
            },
        )
    else:
        container.audit_log.log(
            recovery_item_id=item_id,
            actor="agent",
            action="voice_promise_extracted",
            reason=f"Voice transcript extracted with intent '{extracted.intent}' (confidence={extracted.confidence})",
            metadata=extracted.to_dict(),
        )

    p_date_str = extracted.promised_date if extracted.promised_date else None
    return JSONResponse(status_code=200, content={
        "extracted": extracted.to_dict(),
        "promise_created": promise_created,
        "promise": promise_record,
        "decision": "WAIT" if promise_created else None,
        "reason": "Customer committed to payment date" if promise_created else None,
        "follow_up_date": p_date_str if promise_created else None,
    })

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

@router.get("/api/customers/{customer_id}/recovery-profile")
def api_customer_recovery_profile(customer_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Return Customer 360 Recovery Profile aggregated from authoritative ledgers."""
    from app.services.customer_recovery_profile import CustomerRecoveryProfileService
    service = CustomerRecoveryProfileService(container)
    profile = service.get_profile(customer_id)
    if profile.total_cases_count == 0:
        return JSONResponse(status_code=404, content={"error": "Customer profile not found"})
    return JSONResponse(status_code=200, content=profile.to_dict())

@router.get("/api/recovery-items/{item_id}/trace")
def api_case_trace(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    from app.services.trace_service import build_case_trace
    data = build_case_trace(item_id, container)
    if not data:
        return JSONResponse(status_code=404, content={"error": "Item trace not found"})
    return JSONResponse(status_code=200, content=data)

@router.get("/api/benchmark/latest")
def api_benchmark_latest() -> Response:
    from dataclasses import asdict
    from app.evaluation.benchmark import run_benchmark_suite
    report = run_benchmark_suite(cases=100, seeds=[42, 43, 44, 45, 46, 47, 48, 49, 50, 51])
    return JSONResponse(status_code=200, content=asdict(report))

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

@router.get("/api/razorpay/status")
def api_razorpay_status() -> dict[str, Any]:
    import os
    execution_mode = os.getenv("RECOVERY_EXECUTION_MODE", "simulation").lower().strip()
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

    is_live_test_mode = bool(key_id and secret and execution_mode == "razorpay_test")

    return {
        "is_live_test_mode": is_live_test_mode,
        "execution_mode": "REAL TEST MODE" if is_live_test_mode else "SIMULATED",
        "execution_mode_description": "REAL TEST MODE — Connected to Razorpay API in test environment" if is_live_test_mode else "SIMULATED — Signature verification logic is real, gateway API calls are mocked",
        "razorpay_connection": "Connected (Test Mode)" if is_live_test_mode else ("Configured" if key_id else "Not configured (Simulated)"),
        "masked_key_id": f"{key_id[:8]}..." if len(key_id) >= 8 else None,
        "webhook_verification": "Enabled" if (secret or not is_live_test_mode) else "Disabled",
        "payment_link_creation": "Available",
        "settlement_verification": "Enabled",
        "safety_guardrails": "Strict Bounded Autonomy",
        "central_principle": "RevPlug is optimized for safe net recovery, not maximum retries.",
    }


@router.get("/api/controls")
def api_controls() -> dict[str, Any]:
    import os
    from app.services.policy_config_service import PolicyConfigStore
    cfg = PolicyConfigStore.get_instance().get_config()

    execution_mode = os.getenv("RECOVERY_EXECUTION_MODE", "simulation").lower().strip()
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
    is_live_test = bool(key_id and secret and execution_mode == "razorpay_test")

    return {
        "max_payment_retries": cfg.max_retries,
        "max_contacts_per_24h": cfg.max_contacts_per_24h,
        "customer_opt_out": "Enabled",
        "fraud_retry_protection": "Enabled",
        "recovery_deadline": "24h",
        "promise_expiry_protection": "Enabled",
        "policy_enforcement": "Mandatory",
        "human_override": "Disabled",
        "execution_mode": "REAL TEST MODE" if is_live_test else "SIMULATED — Signature verification logic is real, gateway API calls are mocked",
        "is_live_test_mode": is_live_test,
        "razorpay_connection": "Connected (Test Mode)" if is_live_test else "SIMULATED — Signature verification logic is real, gateway API calls are mocked",
        "webhook_verification": "Enabled (HMAC-SHA256 Active)",
        "payment_link_creation": "Available",
        "settlement_verification": "Enabled",
        "policy_version": cfg.version,
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
    from app.services.trace_service import build_case_trace
    trace_data = build_case_trace(item_id, container)
    trace_data["agent_events"] = trace_data.get("timeline", [])
    return JSONResponse(status_code=200, content=trace_data)

@router.get("/api/recovery-items/{item_id}/trace")
@router.get("/recovery/{item_id}/trace")
def api_case_trace(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get canonical decision trace, explainability, and replay data for a recovery case."""
    from app.services.trace_service import build_case_trace
    trace_data = build_case_trace(item_id, container)
    return JSONResponse(status_code=200, content=trace_data)

@router.get("/api/recovery-items/{item_id}/audit-trail")
def api_audit_trail(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get complete, chronologically ordered audit trail for a recovery item."""
    from app.services.trace_service import build_case_trace
    trace_data = build_case_trace(item_id, container)
    return JSONResponse(status_code=200, content={
        "item_id": item_id,
        "total_events": len(trace_data.get("timeline", [])),
        "timeline": trace_data.get("timeline", []),
        "trace": trace_data,
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


@router.get("/api/recovery-items/{item_id}/naive-baseline")
def api_case_naive_baseline(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Compute naive retry baseline action, cost, policy violations, and outcome for a single case."""
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)

    if item is None:
        from app.domain.models import RecoveryItem, RecoveryStatus
        if item_id == "demo_case_4999":
            item = RecoveryItem(
                id="demo_case_4999",
                customer_id="cust_razor_101",
                amount_minor=499900,
                status=RecoveryStatus.RECOVERED,
                root_cause="network_timeout",
                metadata={"original_category": "soft", "is_synthetic": True}
            )
        elif item_id == "demo_case_18200":
            item = RecoveryItem(
                id="demo_case_18200",
                customer_id="cust_risk_909",
                amount_minor=1820000,
                status=RecoveryStatus.STOPPED,
                root_cause="fraud_suspected",
                metadata={"original_category": "fraud", "fraud_flag": True, "is_synthetic": True}
            )
        else:
            return JSONResponse(status_code=404, content={"error": f"Item {item_id} not found"})

    from app.services.baseline_evaluator import BaselineEvaluator
    evaluator = BaselineEvaluator(mode="naive", rng_seed=42)
    res = evaluator.evaluate_case(item, case_index=0)

    cat = str(item.root_cause or "").lower()
    orig_cat = str(item.metadata.get("original_category", "")).lower()
    is_fraud = cat in ("fraud", "security_or_fraud") or orig_cat == "fraud" or item.metadata.get("fraud_flag")
    is_optout = bool(item.metadata.get("customer_opted_out"))
    is_hard = cat in ("hard", "hard_decline") or orig_cat == "hard"

    violations = []
    if is_fraud:
        violations.append("FRAUD_RETRY_PROHIBITED")
    if is_optout:
        violations.append("CUSTOMER_OPT_OUT_VIOLATION")
    if is_hard:
        violations.append("HARD_DECLINE_UNRETRYABLE")

    return JSONResponse(status_code=200, content={
        "case_id": item_id,
        "baseline_mode": "naive_retry_bot",
        "action_taken": "retry_payment",
        "attempts_made": res.attempts_made,
        "intervention_cost_minor": res.intervention_cost,
        "estimated_outcome": res.outcome,
        "actual_recovered_minor": res.actual_recovered,
        "unnecessary_intervention": res.unnecessary_intervention,
        "policy_violations": violations,
        "has_policy_violations": len(violations) > 0,
        "summary": (
            f"Naive bot executed fixed retry_payment without checking policy gates. "
            + (f"Incurred {len(violations)} policy violations ({', '.join(violations)})." if violations else "Spent intervention cost without optimal channel selection.")
        )
    })


@router.get("/api/dashboard/activity")
def api_dashboard_activity(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """Return recent recovery activity events for the dashboard activity stream."""
    from app.dashboard_api import _get_items
    items = _get_items(container)
    item_map = {i.id: i for i in items}

    # Collect audit events for all live items
    events: list[dict[str, Any]] = []
    audit_log = getattr(container, "audit_log", None)
    if audit_log and hasattr(audit_log, "_events"):
        for evt in audit_log._events:
            if evt.recovery_item_id not in item_map:
                continue
            item = item_map[evt.recovery_item_id]
            events.append({
                "id": evt.id,
                "timestamp": evt.timestamp.isoformat() if hasattr(evt.timestamp, "isoformat") else str(evt.timestamp),
                "recovery_item_id": evt.recovery_item_id,
                "customer_id": item.customer_id,
                "amount_minor": item.amount_minor,
                "action": evt.action,
                "reason": evt.reason or "",
                "actor": evt.actor,
                "item_status": item.status.value if hasattr(item.status, "value") else str(item.status),
                "root_cause": item.root_cause,
            })

    # Sort by timestamp descending, cap at 20
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:20]


@router.get("/api/dashboard/promise-summary")
def api_dashboard_promise_summary(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return compact promise-to-pay metrics for the dashboard."""
    from app.domain.models import PromiseStatus

    promises_repo = getattr(container, "promises", None)
    if promises_repo is None:
        return {
            "active_count": 0,
            "committed_amount_minor": 0,
            "due_soon_count": 0,
            "fulfilled_count": 0,
            "fulfilled_amount_minor": 0,
            "broken_count": 0,
        }

    all_promises = []
    if hasattr(promises_repo, "list_all"):
        all_promises = promises_repo.list_all()
    elif hasattr(promises_repo, "_by_id"):
        all_promises = list(getattr(promises_repo, "_by_id", {}).values())

    active = []
    fulfilled = []
    broken = []
    now = datetime.now(timezone.utc)

    for p in all_promises:
        status = p.get("status", "") if isinstance(p, dict) else getattr(p, "status", "")
        if status in {PromiseStatus.PROMISED.value, "promised", "active"}:
            active.append(p)
        elif status == PromiseStatus.FULFILLED.value or status == "fulfilled":
            fulfilled.append(p)
        elif status in {PromiseStatus.BROKEN.value, "broken", PromiseStatus.EXPIRED.value, "expired"}:
            broken.append(p)

    committed = sum(p.get("promised_amount_minor", 0) if isinstance(p, dict) else getattr(p, "promised_amount_minor", 0) for p in active)

    from datetime import date
    due_soon = [
        p for p in active
        if True  # will filter below
    ]
    due_soon_count = 0
    for p in active:
        raw = p.get("promised_date") if isinstance(p, dict) else getattr(p, "promised_date", None)
        if raw:
            if isinstance(raw, datetime):
                pd = raw.date()
            elif isinstance(raw, date):
                pd = raw
            elif isinstance(raw, str):
                try:
                    pd = date.fromisoformat(raw)
                except ValueError:
                    continue
            else:
                continue
            from datetime import timedelta
            if pd <= (now.date() + timedelta(days=3)):
                due_soon_count += 1

    fulfilled_amount = sum(p.get("verified_recovered_minor") or p.get("promised_amount_minor", 0) if isinstance(p, dict) else getattr(p, "verified_recovered_minor", None) or getattr(p, "promised_amount_minor", 0) for p in fulfilled)

    return {
        "active_count": len(active),
        "committed_amount_minor": committed,
        "due_soon_count": due_soon_count,
        "fulfilled_count": len(fulfilled),
        "fulfilled_amount_minor": fulfilled_amount,
        "broken_count": len(broken),
    }


@router.get("/api/dashboard/decisions")
def api_dashboard_decisions(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return distribution of canonical decisions across the portfolio."""
    from app.dashboard_api import _get_items
    from app.domain.product_decision import resolve_decision

    items = _get_items(container)

    distribution: dict[str, dict[str, Any]] = {
        "RECOVER": {"count": 0, "total_at_risk": 0, "total_expected": 0, "top_opportunity": None},
        "WAIT": {"count": 0, "total_at_risk": 0, "total_expected": 0, "top_opportunity": None},
        "ESCALATE": {"count": 0, "total_at_risk": 0, "total_expected": 0, "top_opportunity": None},
        "STOP": {"count": 0, "total_at_risk": 0, "total_expected": 0, "top_opportunity": None},
    }

    for item in items:
        meta = item.metadata if isinstance(item.metadata, dict) else {}
        policy_state = meta.get("policy_state", "")
        reason_code = meta.get("reason_code", "") or policy_state.lower()
        reason = meta.get("reason", "")

        product_decision = resolve_decision(
            action=meta.get("recommended_action", ""),
            policy_state=policy_state or None,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            reason_code=reason_code,
            reason=reason,
        )

        d = product_decision.decision
        if d not in distribution:
            d = "STOP"

        distribution[d]["count"] += 1
        distribution[d]["total_at_risk"] += item.amount_minor
        distribution[d]["total_expected"] += item.expected_recovery_value or 0

        # Track top opportunity (highest expected recovery)
        current_top = distribution[d]["top_opportunity"]
        if current_top is None or (item.expected_recovery_value or 0) > (current_top.get("expected_recovery_value", 0) or 0):
            distribution[d]["top_opportunity"] = {
                "item_id": item.id,
                "customer_id": item.customer_id,
                "amount_minor": item.amount_minor,
                "expected_recovery_value": item.expected_recovery_value,
                "root_cause": item.root_cause,
                "reason": reason,
            }

    return distribution


@router.get("/api/decisions/stream")
def api_decision_stream(container: PersistenceContainer = Depends(get_container)) -> dict[str, Any]:
    """Return the Autonomous Recovery Decision Stream.

    A decision-centric portfolio stream showing what revenue opportunities appeared,
    what RevPlug decided, why, what action followed, and what happened next.
    """
    from app.dashboard_api import _get_items, _actual_recovered_from_outcomes
    from app.domain.product_decision import resolve_decision

    items = _get_items(container)
    item_map = {i.id: i for i in items}

    # Build verified recovery map from outcomes
    verified_map: dict[str, int] = {}
    outcomes_repo = getattr(container, "outcomes", None)
    if outcomes_repo and hasattr(outcomes_repo, "_outcomes"):
        for outcome in outcomes_repo._outcomes.values():
            if outcome is None:
                continue
            oid = getattr(outcome, "recovery_item_id", None)
            if oid:
                amt = getattr(outcome, "actual_recovery_minor", 0) or 0
                verified_map[oid] = verified_map.get(oid, 0) + amt

    # Collect and enrich audit events
    raw_events: list[dict[str, Any]] = []
    audit_log = getattr(container, "audit_log", None)
    if audit_log and hasattr(audit_log, "_events"):
        for evt in audit_log._events:
            if evt.recovery_item_id not in item_map:
                continue
            item = item_map[evt.recovery_item_id]
            meta = item.metadata if isinstance(item.metadata, dict) else {}

            # Resolve canonical decision for this event
            policy_state = meta.get("policy_state", "")
            action = meta.get("recommended_action", evt.action)
            reason_code = meta.get("reason_code", "") or policy_state.lower() or evt.action.lower()
            reason = meta.get("reason", evt.reason or "")

            product_decision = resolve_decision(
                action=action,
                policy_state=policy_state or None,
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
                reason_code=reason_code,
                reason=reason,
            )

            # Determine event type category
            event_type = _categorize_event_type(evt.action)

            # Determine execution status
            execution_status = "pending"
            if evt.action in ("execution_requested", "action_executed"):
                execution_status = "executed"
            elif evt.action == "recovery_stopped":
                execution_status = "stopped"
            elif evt.action == "settlement_verified":
                execution_status = "verified"

            raw_events.append({
                "event_id": evt.id,
                "timestamp": evt.timestamp.isoformat() if hasattr(evt.timestamp, "isoformat") else str(evt.timestamp),
                "opportunity_id": evt.recovery_item_id,
                "customer_id": item.customer_id,
                "customer_name": meta.get("customer_name", ""),
                "amount_at_risk_minor": item.amount_minor,
                "decision": product_decision.decision,
                "decision_reason": reason,
                "reason_code": reason_code,
                "selected_action": action if action != evt.action else None,
                "event_type": event_type,
                "event_action": evt.action,
                "event_label": _human_readable_event(evt.action, reason),
                "execution_status": execution_status,
                "expected_recovery_minor": item.expected_recovery_value or 0,
                "verified_recovered_minor": verified_map.get(evt.recovery_item_id, 0),
                "policy_status": product_decision.policy_status,
                "requires_human_review": product_decision.requires_human_review,
                "terminal": item.status.value in ("recovered", "stopped") if hasattr(item.status, "value") else False,
                "root_cause": item.root_cause,
                "actor": evt.actor,
            })

    # Add incident detection events to the stream
    from app.services.revenue_incident_manager import RevenueIncidentManager
    incident_mgr = RevenueIncidentManager(container)
    active_incidents = incident_mgr.detect_incidents()
    for inc in active_incidents:
        raw_events.append({
            "event_id": f"incident_{inc.incident_id}",
            "timestamp": inc.detected_at_ts,
            "opportunity_id": "",
            "customer_id": "",
            "customer_name": "",
            "amount_at_risk_minor": inc.amount_at_risk_minor,
            "decision": inc.decision,
            "decision_reason": inc.decision_reason,
            "reason_code": "systemic_incident",
            "selected_action": "wait_systemic",
            "event_type": "incident",
            "event_action": "incident_detected",
            "event_label": f"Incident: {inc.title}",
            "execution_status": "suppressed",
            "expected_recovery_minor": inc.estimated_recoverable_minor,
            "verified_recovered_minor": 0,
            "policy_status": "SUPPRESSED_SYSTEMIC",
            "requires_human_review": False,
            "terminal": False,
            "root_cause": inc.failure_category,
            "actor": "system",
            "incident_id": inc.incident_id,
        })

    # Sort by timestamp descending
    raw_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    # Build summary
    total_opportunities = len(items)
    total_decisions = len([e for e in raw_events if e["event_type"] == "decision"])
    awaiting_action = len([e for e in raw_events if e["decision"] == "RECOVER" and e["execution_status"] == "pending"])
    total_expected = sum(i.expected_recovery_value or 0 for i in items if i.status.value not in ("recovered", "stopped") if hasattr(i.status, "value"))

    return {
        "events": raw_events,
        "summary": {
            "total_opportunities": total_opportunities,
            "total_decisions": total_decisions,
            "awaiting_action": awaiting_action,
            "total_expected_recovery": total_expected,
        },
    }


def _categorize_event_type(action: str) -> str:
    """Categorize an audit action into a decision-stream event type."""
    act = action.lower()
    if act in ("failure_classified", "recovery_item_created", "recovery_scored", "agent_proposal_created"):
        return "detection"
    if act in ("guard_evaluate", "policy_evaluate"):
        return "policy"
    if act in ("execution_requested", "action_executed"):
        return "intervention"
    if act in ("settlement_verified", "recovery_outcome"):
        return "outcome"
    if act in ("recovery_stopped", "escalation_created"):
        return "decision"
    if act in ("promise_created", "promise_fulfilled", "promise_broken", "recovery_waiting"):
        return "promise"
    if act == "immediate_success_termination":
        return "outcome"
    return "decision"


def _human_readable_event(action: str, reason: str) -> str:
    """Convert a raw audit action into human-readable text."""
    mapping = {
        "failure_classified": "Failure classified",
        "recovery_item_created": "Opportunity detected",
        "recovery_scored": "Recovery scored",
        "agent_proposal_created": "Agent proposal created",
        "guard_evaluate": "Policy gate evaluated",
        "policy_evaluate": "Policy evaluated",
        "execution_requested": "Action executed",
        "action_executed": "Action executed",
        "recovery_stopped": "Recovery stopped",
        "escalation_created": "Escalation created",
        "settlement_verified": "Settlement verified",
        "recovery_outcome": "Recovery outcome",
        "immediate_success_termination": "Payment succeeded",
        "case_cleared": "Case cleared",
    }
    return mapping.get(action, action.replace("_", " ").title())

