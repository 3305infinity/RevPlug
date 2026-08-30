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
    from app.api import webhooks, jobs, promises, dashboard, evaluations, demo, auth
    target_app.include_router(webhooks.router)
    target_app.include_router(jobs.router)
    target_app.include_router(promises.router)
    target_app.include_router(dashboard.router)
    target_app.include_router(evaluations.router)
    target_app.include_router(demo.router)
    target_app.include_router(auth.router)

    @target_app.get("/health")
    def health_check():
        return {"status": "ok"}

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
    # Enable CORS for frontend communication with credentials
    fresh.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
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
    fresh.state.webhook_service = service
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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.container = _container
app.state.webhook_secret = _default_secret
_default_webhook_service = _build_webhook_service(_default_secret, _container)
app.state.webhook_service = _default_webhook_service
_register_routes(app, _default_webhook_service)


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

    def list_all() -> list:
        return list(self._outcomes.values())


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
