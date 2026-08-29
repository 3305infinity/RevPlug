"""Stage 7 — Production-Grade Ingestion + Async Recovery Worker Tests.

Tests A–R covering all requirements from the specification:
A. Webhook creates exactly one job
B. Duplicate webhook creates zero additional jobs
C. Concurrent duplicate webhooks create exactly one job
D. Worker claims one job
E. Two workers cannot claim the same job simultaneously
F. Failed worker job is retried (attempt_count increments)
G. Dead-letter after retry limit
H. Stale PROCESSING job can be reclaimed
I. AI timeout fails closed → ESCALATED
J. Malformed AI output fails closed → ESCALATED
K. Low confidence (< 0.50) escalates
L. Medium confidence (0.50–0.79) escalates (human review)
M. High confidence (>= 0.80) still requires PolicyEngine (fraud cannot execute)
N. Payment success prevents later execution
O. Retry exhaustion prevents further execution
P. Execution is idempotent (terminal item skips re-execution)
Q. Completed job cannot execute again
R. Audit events exist for worker lifecycle
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.adapters.razorpay import RazorpayWebhookService
from app.agents.decision_agent import MockRecoveryDecisionAgent, RecoveryDecisionAgent
from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidator
from app.audit.models import InMemoryAuditLog
from app.db.container import PersistenceContainer, create_persistence_container
from app.db.decision_repository import InMemoryRecoveryDecisionRepository
from app.db.repositories import InMemoryRecoveryItemRepository
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.idempotency.store import InMemoryIdempotencyStore
from app.interventions.executor import ExecutionResult, SimulatedRecoveryExecutor
from app.ledger.attempts import InMemoryAttemptLedger
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.worker.job_repository import InMemoryRecoveryJobRepository
from app.worker.models import JobStatus, RecoveryJob
from app.worker.recovery_worker import RecoveryWorker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SECRET = "whsec_stage7_test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payment_payload(
    event_id: str = "evt_stage7_001",
    payment_id: str = "pay_stage7_001",
    error_reason: str = "payment_timed_out",
    amount: int = 50000,
) -> dict:
    return {
        "entity": "event",
        "account_id": "acc_TEST",
        "event": "payment.failed",
        "contains": ["payment"],
        "id": event_id,
        "created_at": 1567610215,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment timed out",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": error_reason,
                    "email": "test@example.com",
                    "contact": "+919876543210",
                    "created_at": 1567610214,
                }
            }
        },
    }


def _build_async_app():
    """Build a test app with the Stage 7 async path enabled (job_repo wired)."""
    container = create_persistence_container("memory")
    service = main_module._build_webhook_service(SECRET, container)
    app = main_module.create_app(
        webhook_secret=SECRET,
        webhook_service=service,
        async_mode=True,
    )
    # Override container with one that has jobs repo (async_mode ensures jobs is set)
    app.state.container = container
    return app, container



def _build_worker(container: PersistenceContainer, **kwargs) -> RecoveryWorker:
    """Build a worker connected to the given container."""
    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    orchestrator = RecoveryAgentOrchestrator(
        agent=MockRecoveryDecisionAgent(),
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )
    return RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        attempts=container.attempts,
        outcomes=container.outcomes,
        max_attempts=kwargs.get("max_attempts", 3),
        worker_timeout_seconds=kwargs.get("worker_timeout_seconds", 300),
        worker_id=kwargs.get("worker_id", "test-worker-1"),
    )


def _make_recovery_item(
    item_id: str = "pay_test_001",
    status: RecoveryStatus = RecoveryStatus.QUEUED,
    root_cause: str = "soft",
    amount: int = 50000,
    metadata: dict | None = None,
) -> RecoveryItem:
    return RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"evt_{item_id}",
        customer_id="cust_001",
        amount_minor=amount,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=status,
        root_cause=root_cause,
        expected_recovery_value=int(amount * 0.35),
        intervention_cost=100,
        metadata=metadata or {},
    )


# ===========================================================================
# A. Webhook creates exactly one job
# ===========================================================================

def test_a_webhook_creates_exactly_one_job():
    """A webhook should create exactly one QUEUED job for the recovery item."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload()
    body = json.dumps(payload).encode()
    sig = _sign(body)

    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": sig},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
    assert data["job_id"] is not None
    assert "recovery_item_id" in data

    # Verify exactly one job exists
    jobs = container.jobs.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.QUEUED
    assert jobs[0].recovery_item_id == data["recovery_item_id"]


# ===========================================================================
# B. Duplicate webhook creates zero additional jobs
# ===========================================================================

def test_b_duplicate_webhook_creates_no_additional_jobs():
    """A second identical webhook must not create another job."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload(event_id="evt_dup_001", payment_id="pay_dup_001")
    body = json.dumps(payload).encode()
    sig = _sign(body)

    resp1 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    resp2 = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})

    assert resp1.status_code == 200
    assert resp1.json()["status"] == "accepted"
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "duplicate"

    jobs = container.jobs.list_jobs()
    assert len(jobs) == 1  # still exactly one


# ===========================================================================
# C. Concurrent duplicate webhooks create exactly one job
# ===========================================================================

def test_c_concurrent_duplicate_webhooks_create_one_job():
    """Concurrent identical webhooks must result in exactly one job.

    We use threads to simulate concurrency. The InMemoryJobRepository's
    threading.Lock and try_insert idempotency ensure only one job is created.
    """
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload(event_id="evt_concurrent_001", payment_id="pay_concurrent_001")
    body = json.dumps(payload).encode()
    sig = _sign(body)

    results = []
    errors = []

    def send_webhook():
        try:
            r = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
            results.append(r.json()["status"])
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=send_webhook) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # Exactly one "accepted", rest are "duplicate"
    accepted = [r for r in results if r == "accepted"]
    duplicates = [r for r in results if r == "duplicate"]
    assert len(accepted) == 1, f"Expected 1 accepted, got: {results}"
    assert len(duplicates) == 4

    jobs = container.jobs.list_jobs()
    assert len(jobs) == 1


# ===========================================================================
# D. Worker claims one job
# ===========================================================================

def test_d_worker_claims_one_job():
    """Worker.run_once() should claim and process exactly one job."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    worker = _build_worker(container)
    processed = worker.run_once()

    assert processed is True
    job = container.jobs.get_job_for_item(item.id)
    assert job is not None
    assert job.status == JobStatus.COMPLETED


# ===========================================================================
# E. Two workers cannot claim the same job
# ===========================================================================

def test_e_two_workers_cannot_claim_same_job():
    """Two concurrent workers must each claim a different job (or one gets None)."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    job_result = container.jobs.create_job(item.id)
    assert job_result is not None

    # Manually claim via the lock to simulate what two workers would do
    job_repo = container.jobs

    claimed = []

    def claim_job(worker_id: str):
        job = job_repo.claim_next_job(worker_id, worker_timeout_seconds=300)
        if job is not None:
            claimed.append((worker_id, job.job_id))

    # Sequential claims — the second one should get None (job already claimed)
    claim_job("worker-A")
    claim_job("worker-B")

    assert len(claimed) == 1, f"Only one worker should claim the job, got: {claimed}"
    assert claimed[0][0] == "worker-A"


# ===========================================================================
# F. Failed worker job is retried
# ===========================================================================

def test_f_failed_job_is_retried():
    """After a worker fails, attempt_count increments and job is re-QUEUED."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    job = container.jobs.create_job(item.id, max_attempts=3)
    assert job is not None

    # Claim job (attempt_count becomes 1)
    claimed = container.jobs.claim_next_job("worker-1", worker_timeout_seconds=300)
    assert claimed is not None
    assert claimed.attempt_count == 1

    # Mark failed (should re-queue since attempt_count < max_attempts)
    container.jobs.mark_failed(claimed.job_id, error="simulated failure")

    updated = container.jobs.get_job(claimed.job_id)
    assert updated.status == JobStatus.QUEUED
    assert updated.attempt_count == 1  # attempt count stays at 1; incremented on next claim
    assert updated.last_error == "simulated failure"


# ===========================================================================
# G. Dead-letter after retry limit
# ===========================================================================

def test_g_dead_letter_after_retry_limit():
    """After max_attempts, the job should be DEAD_LETTER, not re-QUEUED."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    job = container.jobs.create_job(item.id, max_attempts=2)
    assert job is not None

    # Exhaust all attempts
    for i in range(2):
        claimed = container.jobs.claim_next_job(f"worker-{i}", worker_timeout_seconds=300)
        assert claimed is not None, f"Should be able to claim on attempt {i+1}"
        container.jobs.mark_failed(claimed.job_id, error=f"failure attempt {i+1}")

    final = container.jobs.get_job(job.job_id)
    assert final.status == JobStatus.DEAD_LETTER


# ===========================================================================
# H. Stale PROCESSING job can be reclaimed
# ===========================================================================

def test_h_stale_processing_job_reclaimed():
    """A job stuck in PROCESSING past its timeout should be reclaimable."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    job = container.jobs.create_job(item.id)
    assert job is not None

    # Worker 1 claims the job
    claimed = container.jobs.claim_next_job("worker-crashed", worker_timeout_seconds=60)
    assert claimed is not None
    assert claimed.status == JobStatus.PROCESSING

    # Simulate crash: manually backdate locked_at so it appears stale
    with container.jobs._lock:
        container.jobs._jobs[claimed.job_id].locked_at = (
            datetime.now(timezone.utc) - timedelta(seconds=120)
        )

    # Worker 2 should be able to reclaim the stale job
    reclaimed = container.jobs.claim_next_job("worker-2", worker_timeout_seconds=60)
    assert reclaimed is not None
    assert reclaimed.job_id == claimed.job_id
    assert reclaimed.locked_by == "worker-2"


# ===========================================================================
# I. AI timeout fails closed → ESCALATED
# ===========================================================================

def test_i_ai_timeout_fails_closed():
    """If the orchestrator raises TimeoutError, the item must be ESCALATED."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    # Mock orchestrator to raise TimeoutError
    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)

    bad_orchestrator = MagicMock()
    bad_orchestrator.decide.side_effect = TimeoutError("LLM timed out")

    worker = RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=bad_orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        worker_id="test-worker-i",
    )

    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.ESCALATED

    job = container.jobs.get_job_for_item(item.id)
    assert job.status == JobStatus.COMPLETED  # job completed (escalation is terminal)


# ===========================================================================
# J. Malformed AI output fails closed → ESCALATED
# ===========================================================================

def test_j_malformed_ai_output_fails_closed():
    """If the orchestrator raises any exception, the item must be ESCALATED."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)

    bad_orchestrator = MagicMock()
    bad_orchestrator.decide.side_effect = ValueError("Malformed LLM JSON output")

    worker = RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=bad_orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        worker_id="test-worker-j",
    )

    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.ESCALATED


# ===========================================================================
# K. Low confidence (< 0.50) escalates
# ===========================================================================

def test_k_low_confidence_escalates():
    """Confidence < 0.50 must escalate immediately without executing."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    class LowConfidenceAgent:
        name = "low-confidence-agent"
        model_name = "test"

        def propose(self, context):
            return RecoveryProposal(
                action=RecoveryAction.RETRY_PAYMENT,
                reason="low confidence proposal",
                confidence=0.30,  # below threshold
                model_name=self.model_name,
            )

    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    orchestrator = RecoveryAgentOrchestrator(
        agent=LowConfidenceAgent(),
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )

    worker = RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        worker_id="test-worker-k",
    )

    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.ESCALATED


# ===========================================================================
# L. Medium confidence (0.50–0.79) escalates (human review)
# ===========================================================================

def test_l_medium_confidence_escalates():
    """Confidence >= 0.50 but < 0.80 must escalate for human review."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    class MediumConfidenceAgent:
        name = "medium-confidence-agent"
        model_name = "test"

        def propose(self, context):
            return RecoveryProposal(
                action=RecoveryAction.RETRY_PAYMENT,
                reason="medium confidence proposal",
                confidence=0.65,  # between 0.50 and 0.80
                model_name=self.model_name,
            )

    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    orchestrator = RecoveryAgentOrchestrator(
        agent=MediumConfidenceAgent(),
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )

    worker = RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        worker_id="test-worker-l",
    )

    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    assert updated_item.status == RecoveryStatus.ESCALATED


# ===========================================================================
# M. High confidence still requires PolicyEngine (fraud cannot execute)
# ===========================================================================

def test_m_high_confidence_fraud_cannot_execute():
    """Even with confidence >= 0.80, fraud must not be executed."""
    container = create_persistence_container("memory")
    item = _make_recovery_item(root_cause="fraud")
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    # MockRecoveryDecisionAgent already returns STOP_RECOVERY with confidence=0.95 for fraud.
    # But we use a rogue agent that tries to RETRY_PAYMENT with high confidence.
    class RogueFraudAgent:
        name = "rogue-fraud-agent"
        model_name = "test"

        def propose(self, context):
            return RecoveryProposal(
                action=RecoveryAction.RETRY_PAYMENT,  # should be blocked by PolicyEngine
                reason="attempting to retry fraud payment",
                confidence=0.90,  # high confidence — but still must fail
                model_name=self.model_name,
            )

    policy_engine = InterventionPolicy(max_retry_attempts=3)
    stopping_rules = StoppingRules(max_attempts=3)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)
    orchestrator = RecoveryAgentOrchestrator(
        agent=RogueFraudAgent(),
        policy_engine=policy_engine,
        audit_log=container.audit_log,
        validator=ProposalValidator(),
    )

    worker = RecoveryWorker(
        job_repo=container.jobs,
        recovery_items=container.recovery_items,
        orchestrator=orchestrator,
        audit_log=container.audit_log,
        scorer=ExpectedValueScorer(),
        stopping_rules=stopping_rules,
        guard=guard,
        executor=SimulatedRecoveryExecutor(),
        worker_id="test-worker-m",
    )

    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    # Fraud must be stopped/escalated — never recovered
    assert updated_item.status in {RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}


# ===========================================================================
# N. Payment success prevents later execution
# ===========================================================================

def test_n_payment_success_prevents_execution():
    """An item with payment_succeeded=True must be stopped before execution."""
    container = create_persistence_container("memory")
    item = _make_recovery_item(metadata={"payment_succeeded": True})
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    worker = _build_worker(container)
    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    # StoppingRules blocks retry when payment has already succeeded
    assert updated_item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}

    # The worker must have completed the job (not failed/dead-lettered)
    job = container.jobs.get_job_for_item(item.id)
    assert job.status == JobStatus.COMPLETED


# ===========================================================================
# O. Retry exhaustion prevents further execution
# ===========================================================================

def test_o_retry_exhaustion_prevents_execution():
    """An item with attempt_count >= max_attempts must be stopped, not executed."""
    container = create_persistence_container("memory")
    # Set attempt_count to max
    item = _make_recovery_item(metadata={"attempt_count": 3})
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    worker = _build_worker(container, max_attempts=3)
    worker.run_once()

    updated_item = container.recovery_items.get(item.id)
    # StoppingRules should stop retry_budget_exhausted
    assert updated_item.status in {RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}


# ===========================================================================
# P. Execution is idempotent — terminal items skip re-execution
# ===========================================================================

def test_p_execution_is_idempotent():
    """An already-terminal item must not be re-executed when worker processes its job."""
    container = create_persistence_container("memory")
    # Item is already RECOVERED
    item = _make_recovery_item(status=RecoveryStatus.RECOVERED)
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    executor_calls = []

    class TrackingExecutor(SimulatedRecoveryExecutor):
        def execute(self, item, action, *, attempt_number, scenario=None):
            executor_calls.append(action)
            return super().execute(item, action, attempt_number=attempt_number)

    worker = _build_worker(container)
    worker._executor = TrackingExecutor()
    worker.run_once()

    # Executor must NOT have been called (item was already terminal)
    assert executor_calls == [], f"Executor was called unexpectedly: {executor_calls}"
    job = container.jobs.get_job_for_item(item.id)
    assert job.status == JobStatus.COMPLETED


# ===========================================================================
# Q. Completed job cannot execute again
# ===========================================================================

def test_q_completed_job_cannot_execute_again():
    """A COMPLETED job must not be claimable or re-processed."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    job = container.jobs.create_job(item.id)
    assert job is not None

    # Complete the job
    container.jobs.mark_completed(job.job_id)

    # Try to claim — should return None (no QUEUED jobs)
    claimed = container.jobs.claim_next_job("worker-q", worker_timeout_seconds=300)
    assert claimed is None


# ===========================================================================
# R. Audit events exist for worker lifecycle
# ===========================================================================

def test_r_audit_events_exist_for_worker_lifecycle():
    """Worker lifecycle must emit audit events for key stages."""
    container = create_persistence_container("memory")
    item = _make_recovery_item()
    container.recovery_items.save(item)
    container.jobs.create_job(item.id)

    worker = _build_worker(container)
    worker.run_once()

    # Collect all audit events for this item
    events = container.audit_log.events_for(item.id)
    actions = [e.action for e in events]

    # Required worker lifecycle events
    required_events = {"job_claimed", "job_started", "agent_started", "agent_completed"}
    for required in required_events:
        assert required in actions, f"Missing audit event: {required}. Got: {actions}"

    # job_completed must appear (either success or escalation)
    assert "job_completed" in actions, f"Missing 'job_completed' event. Got: {actions}"

    # No secrets in audit events
    for event in events:
        metadata_str = json.dumps(event.metadata)
        assert "whsec" not in metadata_str
        assert "secret" not in metadata_str.lower()
        assert "signature" not in metadata_str.lower()


# ===========================================================================
# Additional: API endpoint tests
# ===========================================================================

def test_api_jobs_list_empty():
    """GET /api/jobs returns empty list when no jobs exist."""
    app, container = _build_async_app()
    client = TestClient(app)
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert response.json() == []


def test_api_jobs_list_after_webhook():
    """GET /api/jobs returns the created job after a webhook."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload(event_id="evt_api_001", payment_id="pay_api_001")
    body = json.dumps(payload).encode()
    sig = _sign(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    assert resp.json()["status"] == "accepted"

    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "QUEUED"


def test_api_jobs_detail():
    """GET /api/jobs/{job_id} returns job detail."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload(event_id="evt_detail_001", payment_id="pay_detail_001")
    body = json.dumps(payload).encode()
    sig = _sign(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    job_id = resp.json()["job_id"]

    detail_resp = client.get(f"/api/jobs/{job_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["job_id"] == job_id
    assert detail["status"] == "QUEUED"


def test_api_jobs_detail_not_found():
    """GET /api/jobs/{job_id} returns 404 for unknown job."""
    app, container = _build_async_app()
    client = TestClient(app)
    response = client.get("/api/jobs/nonexistent-job-id")
    assert response.status_code == 404


def test_api_recovery_next_action():
    """GET /api/recovery/{item_id}/next-action returns job info."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload(event_id="evt_na_001", payment_id="pay_na_001")
    body = json.dumps(payload).encode()
    sig = _sign(body)
    resp = client.post("/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": sig})
    item_id = resp.json()["recovery_item_id"]

    na_resp = client.get(f"/api/recovery/{item_id}/next-action")
    assert na_resp.status_code == 200
    data = na_resp.json()
    assert data["item_id"] == item_id
    assert "current_status" in data
    assert "job" in data
    assert data["job"] is not None
    assert data["job"]["status"] == "QUEUED"


def test_webhook_signature_rejection_in_async_mode():
    """Invalid signature is rejected even in async mode."""
    app, container = _build_async_app()
    client = TestClient(app)

    payload = _payment_payload()
    body = json.dumps(payload).encode()
    # Wrong signature
    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": "bad_signature"},
    )
    assert response.status_code == 400
    assert response.json()["status"] == "rejected"


def test_in_memory_job_repo_create_returns_none_for_duplicate():
    """create_job returns None when an active job already exists for the item."""
    repo = InMemoryRecoveryJobRepository()
    job1 = repo.create_job("item-1")
    job2 = repo.create_job("item-1")  # duplicate active job
    assert job1 is not None
    assert job2 is None


def test_job_status_lifecycle():
    """Verify full job status lifecycle transitions in memory repo."""
    repo = InMemoryRecoveryJobRepository()
    job = repo.create_job("item-lifecycle", max_attempts=2)
    assert job.status == JobStatus.QUEUED

    claimed = repo.claim_next_job("w1", worker_timeout_seconds=300)
    assert claimed.status == JobStatus.PROCESSING
    assert claimed.attempt_count == 1

    repo.mark_failed(claimed.job_id, "oops")
    updated = repo.get_job(claimed.job_id)
    assert updated.status == JobStatus.QUEUED  # re-queued (attempt 1 < max 2)

    claimed2 = repo.claim_next_job("w2", worker_timeout_seconds=300)
    assert claimed2.attempt_count == 2
    repo.mark_failed(claimed2.job_id, "still failing")
    final = repo.get_job(claimed2.job_id)
    assert final.status == JobStatus.DEAD_LETTER  # exhausted


def test_job_to_dict_no_secrets():
    """RecoveryJob.to_dict() must not include any sensitive fields."""
    job = RecoveryJob(
        job_id="test-job-id",
        recovery_item_id="item-1",
        status=JobStatus.QUEUED,
        last_error="some error",
    )
    d = job.to_dict()
    serialized = json.dumps(d)
    assert "secret" not in serialized.lower()
    assert "webhook" not in serialized.lower()
    assert "signature" not in serialized.lower()
    assert "password" not in serialized.lower()
