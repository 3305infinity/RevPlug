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
from app.policies.guard import DefaultRecoveryGuard
from app.policies.retry import DefaultRetryPolicy
from app.policies.stopping_rules import StoppingRules
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
            outcomes=_InMemoryRecoveryOutcomeRepository(),
            promises=_InMemoryPromiseRepository(),
            provider_events=_InMemoryProviderEventRepository(),
        )
    agent = _build_agent()
    stopping_rules = StoppingRules(max_attempts=3)
    orchestrator = RecoveryAgentOrchestrator(
        agent=agent,
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )
    guard = DefaultRecoveryGuard(
        stopping_rules=stopping_rules,
        policy_engine=InterventionPolicy(max_retry_attempts=3),
    )
    return RazorpayWebhookService(
        webhook_secret=secret,
        scorer=ExpectedValueScorer(),
        policy_engine=InterventionPolicy(max_retry_attempts=3),
        audit_log=container.audit_log,
        idempotency_store=container.idempotency,
        provider_events=container.provider_events,
        recovery_items=container.recovery_items,
        decisions=container.decisions,
        attempts=container.attempts,
        agent=agent,
        orchestrator=orchestrator,
        executor=SimulatedRecoveryExecutor(),
        retry_policy=DefaultRetryPolicy(max_attempts=3),
        state_machine=DefaultStateMachine(),
        stopping_rules=stopping_rules,
        guard=guard,
        outcomes=container.outcomes,
        promises=container.promises,
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

        # Check whether async job queue is available for this app instance.
        # When job_repo is present (Stage 7 mode): fast-accept, enqueue, return immediately.
        # When job_repo is absent (legacy / test mode): synchronous path (unchanged behaviour).
        container = _get_container(target_app)
        job_repo = getattr(container, "jobs", None)

        if job_repo is not None:
            # ── ASYNC FAST-ACCEPT PATH ──────────────────────────────────────
            # Stage 1: verify signature (raw body, before any parsing)
            from app.adapters.razorpay.signatures import (
                RazorpaySignatureError as _SigErr,
                verify_razorpay_signature,
            )
            try:
                verify_razorpay_signature(raw_body, x_razorpay_signature, service._webhook_secret)
            except _SigErr:
                return JSONResponse(
                    status_code=400,
                    content={"status": "rejected", "reason": "signature_verification_failed"},
                )

            # Stage 2: parse event
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

            # Stage 3: durable provider_event insert (idempotent)
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

            # Stage 4: duplicate detection
            if not is_new_event:
                return JSONResponse(
                    status_code=200,
                    content={"status": "duplicate", "provider_event_id": provider_event_id},
                )

            # Stage 5: classify + create recovery item (for immediate prioritization)
            from app.adapters.razorpay.classifier import RazorpayFailureClassifier
            from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
            classifier = RazorpayFailureClassifier()
            normalized = classifier.classify(razorpay_failure)
            item = service._build_recovery_item(razorpay_failure, normalized)
            item = service._safe_transition(item, RecoveryStatus.DIAGNOSED)

            # Score immediately so item is prioritized in the dashboard
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

            # Stage 6: enqueue recovery job
            job = job_repo.create_job(item.id)

            # Emit audit event
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

            # Stage 7: return immediately with job reference
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

    # ── Stage 7: Worker Observability Endpoints ─────────────────────────────

    @target_app.get("/api/jobs")
    def api_list_jobs() -> list[dict[str, Any]]:
        """List recovery jobs. Does not expose secrets or raw payment payloads."""
        container = _get_container(target_app)
        job_repo = getattr(container, "jobs", None)
        if job_repo is None:
            return []
        jobs = job_repo.list_jobs(limit=100)
        return [j.to_dict() for j in jobs]

    @target_app.get("/api/jobs/{job_id}")
    def api_get_job(job_id: str) -> Response:
        """Get details for a specific recovery job."""
        container = _get_container(target_app)
        job_repo = getattr(container, "jobs", None)
        if job_repo is None:
            return JSONResponse(status_code=404, content={"error": "Job queue not available"})
        job = job_repo.get_job(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        return JSONResponse(status_code=200, content=job.to_dict())

    @target_app.get("/api/recovery/{item_id}/next-action")
    def api_recovery_next_action(item_id: str) -> Response:
        """Get the deterministic next best action for a recovery item (worker perspective)."""
        from app.policies.engine import InterventionPolicy
        from app.policies.guard import DefaultRecoveryGuard
        from app.policies.stopping_rules import StoppingRules as _SR

        container = _get_container(target_app)
        item = None
        if hasattr(container.recovery_items, "get"):
            item = container.recovery_items.get(item_id)
        if item is None:
            return JSONResponse(status_code=404, content={"error": "Item not found"})

        stopping_rules = _SR(max_attempts=3)
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

        # Get job info for this item if available
        job_repo = getattr(container, "jobs", None)
        job_info = None
        if job_repo is not None:
            job = job_repo.get_job_for_item(item_id)
            if job is not None:
                job_info = {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "attempt_count": job.attempt_count,
                    "last_error": job.last_error,
                }

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
            "job": job_info,
        }
        return JSONResponse(status_code=200, content=response)

    # -----------------------------------------------------------------------
    # Stage 8: Financial Truth, Batches, Customers, Promises, Time-Series
    # -----------------------------------------------------------------------

    @target_app.post("/api/promises")
    async def api_create_promise(request: Request) -> Response:
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
            
        container = _get_container(target_app)
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
            
        # Log audit event
        container.audit_log.log(
            recovery_item_id=item_id,
            actor="agent",
            action="promise_created",
            reason=f"Promise-to-pay recorded for {amount} minor units by {promised_date_str}",
            metadata={"promise_id": promise.id, "amount_minor": amount, "promised_date": promised_date_str},
        )
            
        from app.dashboard_api import _promise_to_dict
        return JSONResponse(status_code=201, content=_promise_to_dict(promise))

    @target_app.get("/api/promises")
    def api_list_promises() -> list[dict[str, Any]]:
        """List all promises."""
        container = _get_container(target_app)
        if hasattr(container.promises, "list_all"):
            promises = container.promises.list_all()
        else:
            promises = []
        from app.dashboard_api import _promise_to_dict
        return [_promise_to_dict(p) for p in promises]

    @target_app.get("/api/promises/{promise_id}")
    def api_get_promise(promise_id: str) -> Response:
        """Get a single promise by ID."""
        container = _get_container(target_app)
        if hasattr(container.promises, "get"):
            promise = container.promises.get(promise_id)
            if promise:
                from app.dashboard_api import _promise_to_dict
                return JSONResponse(status_code=200, content=_promise_to_dict(promise))
        return JSONResponse(status_code=404, content={"error": "Promise not found"})

    @target_app.post("/api/promises/{promise_id}/fulfill")
    def api_fulfill_promise(promise_id: str) -> Response:
        """Fulfill a promise, generating a RecoveryOutcome (financial truth)."""
        container = _get_container(target_app)
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
            
        # Update status
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if hasattr(container.promises, "update_status"):
            updated = container.promises.update_status(promise_id, "fulfilled", fulfilled_at=now)
            if updated:
                promise = updated
                
        # Generate financial truth Outcome
        if container.outcomes:
            from app.domain.models import RecoveryOutcome
            outcome = RecoveryOutcome(
                recovery_item_id=item_id,
                outcome_type="recovered",
                expected_recovery_minor=amount,
                actual_recovery_minor=amount,
                recovery_cost_minor=0,
                net_recovery_minor=amount,
                recovered_at=now,
            )
            container.outcomes.save(outcome)
            
            # Transition item to recovered
            item = container.recovery_items.get(item_id) if hasattr(container.recovery_items, "get") else None
            if item:
                from app.domain.models import RecoveryStatus
                from app.domain.transitions import DefaultStateMachine
                sm = DefaultStateMachine()
                res = sm.transition(item, RecoveryStatus.RECOVERED)
                if res.applied:
                    container.recovery_items.save(res.item)
                    
        # Log audit
        container.audit_log.log(
            recovery_item_id=item_id,
            actor="system",
            action="promise_fulfilled",
            reason=f"Promise fulfilled, recovered {amount}",
            metadata={"promise_id": promise_id, "amount_minor": amount},
        )
        
        from app.dashboard_api import _promise_to_dict
        return JSONResponse(status_code=200, content=_promise_to_dict(promise))

    @target_app.post("/api/promises/{promise_id}/break")
    async def api_break_promise(promise_id: str, request: Request) -> Response:
        """Mark a promise as broken."""
        import json
        body = await request.body()
        reason = "Payment not received by promised date"
        if body:
            try:
                payload = json.loads(body)
                reason = payload.get("reason", reason)
            except json.JSONDecodeError:
                pass
                
        container = _get_container(target_app)
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
                metadata={"break_reason": reason},
                expired_at=now
            )
            if updated:
                promise = updated
                
        item_id = promise.recovery_item_id if not isinstance(promise, dict) else promise.get("recovery_item_id")
        
        # Log audit
        container.audit_log.log(
            recovery_item_id=item_id,
            actor="system",
            action="promise_broken",
            reason=f"Promise broken: {reason}",
            metadata={"promise_id": promise_id, "break_reason": reason},
        )
        
        from app.dashboard_api import _promise_to_dict
        return JSONResponse(status_code=200, content=_promise_to_dict(promise))

    @target_app.get("/api/customers")
    def api_list_customers() -> list[dict[str, Any]]:
        from app.dashboard_api import build_customers_list
        return build_customers_list(_get_container(target_app))

    @target_app.get("/api/customers/{customer_id}")
    def api_get_customer(customer_id: str) -> Response:
        from app.dashboard_api import build_customer_economics
        container = _get_container(target_app)
        data = build_customer_economics(container, customer_id)
        if not data.get("total_cases"):
            return JSONResponse(status_code=404, content={"error": "Customer not found"})
        return JSONResponse(status_code=200, content=data)

    @target_app.get("/api/recovery-items/{item_id}/lifecycle")
    def api_lifecycle(item_id: str) -> Response:
        """Get the full reconstructed lifecycle for an item."""
        from app.dashboard_api import build_lifecycle
        container = _get_container(target_app)
        data = build_lifecycle(container, item_id)
        if not data:
            return JSONResponse(status_code=404, content={"error": "Item not found"})
        return JSONResponse(status_code=200, content=data)

    @target_app.get("/api/time-series/recovered-by-day")
    def api_ts_recovered() -> list[dict[str, Any]]:
        from app.dashboard_api import build_recovered_by_day
        return build_recovered_by_day(_get_container(target_app))

    @target_app.get("/api/time-series/revenue-at-risk-by-day")
    def api_ts_risk() -> list[dict[str, Any]]:
        from app.dashboard_api import build_revenue_at_risk_by_day
        return build_revenue_at_risk_by_day(_get_container(target_app))

    @target_app.get("/api/time-series/attempts-by-day")
    def api_ts_attempts() -> list[dict[str, Any]]:
        from app.dashboard_api import build_attempts_by_day
        return build_attempts_by_day(_get_container(target_app))

    @target_app.get("/api/time-series/stopped-by-reason")
    def api_ts_stopped() -> list[dict[str, Any]]:
        from app.dashboard_api import build_stopped_by_reason
        return build_stopped_by_reason(_get_container(target_app))

    @target_app.post("/api/demo/reset")
    def api_demo_reset():
        """Reset all synthetic data for a clean demo state."""
        container = _get_container(target_app)
        count = container.reset_demo_data()
        return {"status": "success", "message": f"Deleted {count} synthetic items and their related data."}

    @target_app.get("/api/demo/datasets")
    def api_demo_datasets() -> list[dict[str, Any]]:
        from app.datasets.synthetic import list_datasets
        import dataclasses
        return [dataclasses.asdict(d) for d in list_datasets()]

    @target_app.post("/api/demo/datasets/{label}/run")
    def api_run_dataset(label: str) -> Response:
        from app.datasets.synthetic import load_dataset
        try:
            items = load_dataset(label)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": str(e)})
            
        container = _get_container(target_app)
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

    @target_app.post("/api/batches")
    async def api_create_batch(request: Request) -> Response:
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
            
        container = _get_container(target_app)
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

    @target_app.get("/api/batches")
    def api_list_batches() -> list[dict[str, Any]]:
        container = _get_container(target_app)
        if not hasattr(container, "batches") or container.batches is None:
            return []
            
        from app.services.batch_service import BatchService
        batch_svc = BatchService(
            batch_repo=container.batches,
            recovery_items_repo=container.recovery_items,
            outcomes_repo=container.outcomes,
        )
        return [batch_svc.summarize_batch(b.batch_id) for b in batch_svc.list_batches()]

    @target_app.get("/api/batches/{batch_id}")
    def api_get_batch(batch_id: str) -> Response:
        container = _get_container(target_app)
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

    @target_app.post("/api/batches/{batch_id}/enqueue")
    def api_enqueue_batch(batch_id: str) -> Response:
        container = _get_container(target_app)
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
        response_body: dict[str, Any] = {
            "status": status,
            "recovery_item_id": item.id if item else None,
            "audit_event_count": len(audit_events),
        }
        if item is not None:
            # Mark as synthetic for easy demo reset
            container = _get_container(target_app)
            if hasattr(container.recovery_items, "get"):
                db_item = container.recovery_items.get(item.id)
                if db_item:
                    db_item.metadata["is_synthetic"] = True
                    container.recovery_items.save(db_item)
                    
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

    # Human-in-the-loop review endpoints

    @target_app.get("/api/reviews/pending")
    def api_reviews_pending() -> list[dict[str, Any]]:
        """Get all cases pending human review (escalated status)."""
        from app.dashboard_api import build_recovery_items_list
        container = _get_container(target_app)
        all_items = build_recovery_items_list(container)
        return [i for i in all_items if i["status"] in ("escalated", "failed")]

    @target_app.get("/api/customers/{customer_id}")
    def api_customer_detail(customer_id: str) -> Response:
        """Get all recovery cases for a specific customer."""
        from app.dashboard_api import build_recovery_items_list
        container = _get_container(target_app)
        all_items = build_recovery_items_list(container)
        customer_items = [i for i in all_items if i.get("customer_id") == customer_id]
        if not customer_items:
            return JSONResponse(status_code=404, content={"error": "Customer not found"})
        total_at_risk = sum(i["amount_minor"] for i in customer_items if i["status"] not in ("recovered", "stopped"))
        total_recovered = sum(i["amount_minor"] for i in customer_items if i["status"] == "recovered")
        return JSONResponse(status_code=200, content={
            "customer_id": customer_id,
            "cases": customer_items,
            "total_cases": len(customer_items),
            "revenue_at_risk": total_at_risk,
            "recovered": total_recovered,
        })

    @target_app.get("/api/programs/config")
    def api_programs_config() -> dict[str, Any]:
        """Get current program configuration."""
        container = _get_container(target_app)
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

    @target_app.get("/api/controls")
    def api_controls() -> dict[str, Any]:
        """Get active recovery controls / safety configuration."""
        return {
            "max_payment_retries": 3,
            "customer_opt_out": "Enabled",
            "fraud_retry_protection": "Enabled",
            "recovery_deadline": "24h",
            "promise_expiry_protection": "Enabled",
            "policy_enforcement": "Mandatory",
            "human_override": "Disabled",
        }

    @target_app.put("/api/programs/config")
    async def api_update_program_config(request: Request) -> Response:
        """Update program configuration with safety validation."""
        import json
        body = await request.body()
        try:
            updates = json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        validation_errors = _validate_program_config(updates)
        if validation_errors:
            return JSONResponse(status_code=400, content={"errors": validation_errors})
        container = _get_container(target_app)
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

    @target_app.get("/api/audit-events")
    def api_audit_events(filter: str = "all") -> list[dict[str, Any]]:
        """Get all audit events across all recovery items, optionally filtered."""
        from app.dashboard_api import build_audit_events_list
        container = _get_container(target_app)
        return build_audit_events_list(container, filter_by=filter)

    @target_app.get("/api/provider-events/{provider_event_id}")
    def api_provider_event(provider_event_id: str) -> Response:
        """Get a provider event by ID for diagnostic purposes."""
        container = _get_container(target_app)
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

    @target_app.post("/api/demo/batch-payment-failures")
    async def api_batch_payment_failures(request: Request) -> Response:
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
        secret = _get_secret(target_app)
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
            sig = hmac_mod.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
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
                # Mark as synthetic
                container = _get_container(target_app)
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

    @target_app.post("/api/demo/dataset")
    async def api_demo_dataset(request: Request) -> Response:
        """Run a deterministic demo dataset of 15 mixed scenarios."""
        import json, hashlib, hmac as hmac_mod
        from datetime import datetime, timezone

        body = await request.body()
        payload = {}
        if body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        seed = int(payload.get("seed", 42))
        container = _get_container(target_app)
        secret = _get_secret(target_app)

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
                sig = hmac_mod.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

                if scenario_type == "opted_out":
                    svc = _build_webhook_service(secret, container)
                    svc._stopping_rules._opted_out_customer_ids = frozenset({svc._default_customer_id})
                    item, _, status = svc.process_webhook(raw_body, sig)
                elif scenario_type == "retry_exhausted":
                    svc = _build_webhook_service(secret, container)
                    svc._stopping_rules._max_attempts = 0
                    item, _, status = svc.process_webhook(raw_body, sig)
                elif scenario_type == "deadline_expired":
                    svc = _build_webhook_service(secret, container)
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
                    svc = _build_webhook_service(secret, container)
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

    @target_app.get("/api/next-action/{item_id}")
    def api_next_action(item_id: str) -> Response:
        """Get the deterministic next best action for a recovery case."""
        container = _get_container(target_app)
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
    async_mode: bool = False,
) -> FastAPI:
    """Build a fresh FastAPI app with a pre-configured webhook service.

    Args:
        webhook_secret: The Razorpay webhook HMAC secret.
        webhook_service: Optional pre-built webhook service.
        async_mode: If True, enable Stage 7 async job queue (fast-accept webhook +
                    job enqueue). If False (default), use the synchronous path so
                    existing tests are not affected.
    """
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
    if not async_mode:
        # Null out jobs so the webhook handler uses the synchronous path.
        # This preserves backward compatibility for all pre-Stage-7 tests.
        container.jobs = None
    fresh.state.container = container
    fresh.state.webhook_secret = webhook_secret
    service = webhook_service or _build_webhook_service(webhook_secret, container)
    if webhook_service is not None and hasattr(webhook_service, "container"):
        fresh.state.container = webhook_service.container
        if not async_mode:
            fresh.state.container.jobs = None
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


# ---------------------------------------------------------------------------
# In-memory implementations for new canonical repositories (used in main.py)
# ---------------------------------------------------------------------------

class _InMemoryRecoveryOutcomeRepository:
    def __init__(self) -> None:
        self._outcomes: dict[str, dict] = {}

    def save(self, outcome) -> None:
        self._outcomes[outcome.recovery_item_id] = outcome

    def get_for_item(self, recovery_item_id: str):
        return self._outcomes.get(recovery_item_id)


class _InMemoryPromiseRepository:
    def __init__(self) -> None:
        self._promises: dict[str, dict] = {}

    def save(self, promise) -> None:
        self._promises[promise.recovery_item_id] = promise

    def get_for_item(self, recovery_item_id: str):
        return self._promises.get(recovery_item_id)


class _InMemoryProviderEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, dict] = {}

    def save(self, event) -> None:
        key = (event.provider, event.provider_event_id)
        if key not in self._events:
            self._events[f"{key[0]}:{key[1]}"] = event

    def get_by_provider_event(self, provider: str, provider_event_id: str):
        return self._events.get(f"{provider}:{provider_event_id}")

    def mark_processed(self, provider: str, provider_event_id: str, recovery_item_id: str | None = None) -> None:
        key = f"{provider}:{provider_event_id}"
        event = self._events.get(key)
        if event:
            event.processing_status = "processed"
            event.processed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            event.recovery_item_id = recovery_item_id
