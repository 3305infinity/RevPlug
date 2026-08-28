from __future__ import annotations

import os
import time
from typing import Any

from fastapi import FastAPI, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.razorpay import (
    RazorpayEventError,
    RazorpaySignatureError,
    RazorpayWebhookService,
)
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.llm_agent import RealRecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import InMemoryAuditLog
from app.db.container import PersistenceContainer, create_persistence_container
from app.db.decision_repository import InMemoryRecoveryDecisionRepository
from app.db.repositories import InMemoryRecoveryItemRepository
from app.domain.transitions import DefaultStateMachine
from app.idempotency.store import InMemoryIdempotencyStore
from app.interventions.executor import SimulatedRecoveryExecutor
from app.ledger.attempts import InMemoryAttemptLedger
from app.policies.engine import InterventionPolicy
from app.policies.retry import DefaultRetryPolicy
from app.scoring.expected_value import ExpectedValueScorer


# Default app for `uvicorn app.main:app` — routes are always registered
# so that `app.routes` includes /webhooks/razorpay.
app = FastAPI(title="Recovery Engine", version="0.1.0")


def _build_agent():
    """Build the recovery decision agent based on RECOVERY_AGENT_MODE env var.

    Modes:
        mock (default): deterministic mock agent, no API key needed
        llm: real LLM-backed agent with fallback to mock
    """
    mode = os.environ.get("RECOVERY_AGENT_MODE", "mock").lower()
    if mode == "llm":
        # Use DeterministicLLMClient as default; replace with real provider when configured
        from app.agents.llm_client import DeterministicLLMClient
        return RealRecoveryDecisionAgent(
            llm_client=DeterministicLLMClient(),
            fallback_agent=MockRecoveryDecisionAgent(),
            name="real-agent",
        )
    return MockRecoveryDecisionAgent()


def _build_webhook_service(
    secret: str,
    container: PersistenceContainer | None = None,
) -> RazorpayWebhookService:
    """Build a RazorpayWebhookService with the given persistence container."""
    if container is None:
        container = PersistenceContainer(
            recovery_items=InMemoryRecoveryItemRepository(),
            idempotency=InMemoryIdempotencyStore(),
            audit_log=InMemoryAuditLog(),
            attempts=InMemoryAttemptLedger(),
            decisions=InMemoryRecoveryDecisionRepository(),
        )
    agent = _build_agent()
    orchestrator = RecoveryAgentOrchestrator(
        agent=agent,
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )
    return RazorpayWebhookService(
        webhook_secret=secret,
        scorer=ExpectedValueScorer(),
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=container.audit_log,
        idempotency_store=container.idempotency,
        recovery_items=container.recovery_items,
        decisions=container.decisions,
        attempts=container.attempts,
        agent=agent,
        orchestrator=orchestrator,
        executor=SimulatedRecoveryExecutor(),
        retry_policy=DefaultRetryPolicy(max_attempts=3),
        state_machine=DefaultStateMachine(),
    )


def _register_routes(
    target_app: FastAPI,
    service: RazorpayWebhookService,
) -> None:
    """Attach the Razorpay webhook and health routes to the given app."""

    @target_app.post("/webhooks/razorpay")
    async def razorpay_webhook(
        request: Request,
        x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    ) -> Response:
        raw_body = await request.body()
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
            # Agent proposal
            proposal = service.last_proposal
            decision = service.last_decision
            if proposal is not None:
                response_body["proposed_action"] = proposal.action.value
                response_body["agent_confidence"] = proposal.confidence
                response_body["agent_model"] = proposal.model_name
            if decision is not None:
                response_body["policy_allowed"] = decision.allowed
                response_body["policy_rule"] = decision.policy_rule
            # Execution outcome
            execution = service.last_execution
            if execution is not None:
                response_body["execution_status"] = "succeeded" if execution.success else "failed"
                response_body["attempt_number"] = execution.attempt_number
            # Retry info
            retry = service.last_retry
            if retry is not None:
                response_body["retry_scheduled"] = retry.allowed
                response_body["next_attempt_at"] = retry.next_attempt_at.isoformat() if retry.next_attempt_at else None
            # Escalation
            escalation = service.last_escalation
            if escalation is not None:
                response_body["escalation_reason"] = escalation.reason.value

        return JSONResponse(status_code=200, content=response_body)

    @target_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Dashboard API endpoints
    @target_app.get("/api/dashboard/summary")
    def api_dashboard_summary() -> dict[str, Any]:
        from app.dashboard_api import build_dashboard_summary
        container = _get_container(target_app)
        return build_dashboard_summary(container)

    @target_app.get("/api/recovery-items")
    def api_recovery_items() -> list[dict[str, Any]]:
        from app.dashboard_api import build_recovery_items_list
        container = _get_container(target_app)
        return build_recovery_items_list(container)

    @target_app.get("/api/recovery-items/{item_id}")
    def api_recovery_item_detail(item_id: str) -> Response:
        from app.dashboard_api import build_case_detail
        container = _get_container(target_app)
        detail = build_case_detail(container, item_id)
        if detail is None:
            return JSONResponse(status_code=404, content={"error": "Item not found"})
        return JSONResponse(status_code=200, content=detail)

    @target_app.get("/api/evaluations")
    def api_evaluations() -> dict[str, Any]:
        from app.dashboard_api import build_evaluation_report
        container = _get_container(target_app)
        return build_evaluation_report(container)

    @target_app.post("/api/demo/payment-failure")
    async def api_demo_payment_failure(request: Request) -> Response:
        """Trigger a deterministic demo failed-payment event."""
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

        # Build a synthetic Razorpay payload
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
        secret = _get_secret(target_app)
        sig = hmac_mod.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        item, audit_events, status = service.process_webhook(raw_body, sig)
        return JSONResponse(status_code=200, content={
            "status": status,
            "recovery_item_id": item.id if item else None,
            "audit_event_count": len(audit_events),
        })

    # Human-in-the-loop review endpoints

    @target_app.get("/api/reviews/pending")
    def api_reviews_pending() -> list[dict[str, Any]]:
        """Get all cases pending human review (escalated status)."""
        from app.dashboard_api import build_recovery_items_list
        container = _get_container(target_app)
        all_items = build_recovery_items_list(container)
        return [i for i in all_items if i["status"] in ("escalated", "failed")]

    @target_app.post("/api/recovery-items/{item_id}/approve")
    async def api_approve_item(item_id: str, request: Request) -> Response:
        """Approve a recovery action. Even human approval must pass through PolicyEngine."""
        body = await request.body()
        payload = {}
        if body:
            import json
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        container = _get_container(target_app)
        action = payload.get("action", "escalate_human")

        item = None
        if hasattr(container.recovery_items, "get"):
            item = container.recovery_items.get(item_id)

        if item is None:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        stub = _make_item_stub_from_dict(item)
        from app.policies.engine import InterventionPolicy
        policy = InterventionPolicy(max_retry_attempts=3)
        decision = policy.evaluate(stub, action)

        if decision.allowed:
            container.audit_log.log(
                recovery_item_id=item_id, actor="human", action="human_approved",
                reason=f"Human approved action: {action}",
                metadata={"action": action, "policy_rule": decision.policy_rule},
            )
            return JSONResponse(status_code=200, content={
                "status": "approved", "action": action,
                "policy_rule": decision.policy_rule,
                "message": f"Action '{action}' approved by human and policy",
            })
        else:
            container.audit_log.log(
                recovery_item_id=item_id, actor="human", action="human_approval_denied_by_policy",
                reason=f"Human approved '{action}' but policy denied: {decision.reason}",
                metadata={"action": action, "policy_rule": decision.policy_rule},
            )
            return JSONResponse(status_code=200, content={
                "status": "denied_by_policy", "action": action,
                "policy_rule": decision.policy_rule,
                "message": f"Action '{action}' denied by policy: {decision.reason}",
            })

    @target_app.post("/api/recovery-items/{item_id}/reject")
    async def api_reject_item(item_id: str, request: Request) -> Response:
        """Reject a recovery case — transitions to STOPPED."""
        container = _get_container(target_app)
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

    @target_app.get("/api/recovery-items/{item_id}/agent-trace")
    def api_agent_trace(item_id: str) -> Response:
        """Get the agent trace for a specific recovery item."""
        container = _get_container(target_app)
        events = []
        if hasattr(container.audit_log, "events_for"):
            events = [
                _audit_to_dict(e) for e in container.audit_log.events_for(item_id)
                if e.actor in ("agent", "system") and "agent" in e.action
            ]
        return JSONResponse(status_code=200, content={"item_id": item_id, "agent_events": events})


def _get_container(app) -> Any:
    """Get the persistence container from app state or module global."""
    if hasattr(app, "state") and hasattr(app.state, "container"):
        return app.state.container
    return _container


def _get_secret(app) -> str:
    """Get the webhook secret from app state or module global."""
    if hasattr(app, "state") and hasattr(app.state, "webhook_secret"):
        return app.state.webhook_secret
    return _default_secret


def _make_item_stub_from_dict(item) -> Any:
    """Create a RecoveryItem stub for policy evaluation."""
    from datetime import datetime, timezone
    from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
    # Handle both dict and RecoveryItem inputs
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


def create_app(
    *,
    webhook_secret: str,
    webhook_service: RazorpayWebhookService | None = None,
) -> FastAPI:
    """Build a fresh FastAPI app with a pre-configured webhook service."""
    fresh = FastAPI(title="Recovery Engine", version="0.1.0")
    # Enable CORS for frontend communication
    fresh.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Create a container for this app instance
    container = create_persistence_container("memory")
    fresh.state.container = container
    fresh.state.webhook_secret = webhook_secret
    service = webhook_service or _build_webhook_service(webhook_secret, container)
    _register_routes(fresh, service)
    return fresh


# Wire the default singleton app for `uvicorn app.main:app`.
_default_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "") or "unconfigured-placeholder-secret"

# Determine persistence mode from environment.
_persistence_mode = os.environ.get("PERSISTENCE_MODE", "memory")
if _persistence_mode == "postgres":
    try:
        _container = create_persistence_container("postgres")
    except Exception:
        _container = create_persistence_container("memory")
else:
    _container = create_persistence_container("memory")

# Enable CORS on the default app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.container = _container
app.state.webhook_secret = _default_secret
_register_routes(app, _build_webhook_service(_default_secret, _container))
