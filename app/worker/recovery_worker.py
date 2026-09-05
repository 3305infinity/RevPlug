"""Async recovery worker.

Pulls jobs from the queue, runs the full RecoveryOrchestrator pipeline
with fail-closed AI behavior, and persists outcomes.

Fail-closed AI behavior:
    - timeout         → ESCALATED, no execution
    - malformed output → ESCALATED, no execution
    - agent missing   → ESCALATED, no execution
    - confidence < 0.50 → ESCALATED
    - confidence 0.50-0.79 → ESCALATED (human review required)
    - confidence >= 0.80 → pass to StoppingRules + PolicyEngine + RecoveryGuard

Confidence is NOT permission. Final authorization is always:
    StoppingRules + PolicyEngine + RecoveryGuard.

Crash recovery:
    If a worker dies while a job is PROCESSING, the job's locked_at will
    become stale. The next worker to call claim_next_job() will reclaim it.

Idempotency:
    Before executing anything, the worker checks if the recovery item is
    already in a terminal state (RECOVERED, STOPPED, ESCALATED). If so, it
    marks the job COMPLETED without further action.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.orchestrator import RecoveryAgentOrchestrator
from app.agents.validator import ProposalValidationError, ProposalValidator
from app.audit.models import AuditLog
from app.domain.context import RecoveryContext
from app.domain.escalation import Escalation, EscalationReason
from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryStatus
from app.domain.proposals import RecoveryAction
from app.domain.transitions import DefaultStateMachine, RecoveryStateMachine
from app.interventions.executor import ExecutionResult, RecoveryExecutor, SimulatedRecoveryExecutor
from app.ledger.attempts import AttemptLedger, AttemptRecord
from app.policies.engine import PolicyEngine
from app.policies.guard import DefaultRecoveryGuard, RecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.worker.job_repository import InMemoryRecoveryJobRepository, RecoveryJobRepository
from app.worker.models import JobStatus, RecoveryJob

logger = logging.getLogger(__name__)

# Confidence thresholds (fail-closed)
_CONFIDENCE_MINIMUM = 0.50    # below this → ESCALATED immediately
_CONFIDENCE_AUTO_EXECUTE = 0.80  # below this (but >= minimum) → ESCALATED for human review


class RecoveryWorker:
    """Async recovery worker. Pulls one job per call to run_once().

    Usage (single-shot, e.g. in tests):
        worker = RecoveryWorker(...)
        processed = worker.run_once()

    Usage (continuous loop, e.g. in scripts/run_worker.py):
        worker = RecoveryWorker(...)
        worker.run_loop(poll_interval_seconds=5)
    """

    def __init__(
        self,
        *,
        job_repo: RecoveryJobRepository,
        recovery_items,  # RecoveryItemRepository
        orchestrator: RecoveryAgentOrchestrator,
        audit_log: AuditLog,
        scorer: ExpectedValueScorer,
        stopping_rules: StoppingRules,
        guard: RecoveryGuard,
        executor: RecoveryExecutor | None = None,
        attempts: AttemptLedger | None = None,
        outcomes: Any = None,
        state_machine: RecoveryStateMachine | None = None,
        max_attempts: int = 3,
        worker_timeout_seconds: int = 300,
        worker_id: str | None = None,
    ) -> None:
        self._job_repo = job_repo
        self._recovery_items = recovery_items
        self._orchestrator = orchestrator
        self._audit_log = audit_log
        self._scorer = scorer
        self._stopping_rules = stopping_rules
        self._guard = guard
        self._executor = executor or SimulatedRecoveryExecutor()
        self._attempts = attempts
        self._outcomes = outcomes
        self._state_machine = state_machine or DefaultStateMachine()
        self._max_attempts = max_attempts
        self._worker_timeout_seconds = worker_timeout_seconds
        self._worker_id = worker_id or _make_worker_id()

    def run_once(self) -> bool:
        """Claim and process one job. Returns True if a job was processed."""
        job = self._job_repo.claim_next_job(
            self._worker_id,
            worker_timeout_seconds=self._worker_timeout_seconds,
        )
        if job is None:
            return False

        self._emit("job_claimed", job.recovery_item_id, {
            "job_id": job.job_id,
            "attempt_count": job.attempt_count,
            "worker_id": self._worker_id,
        })

        try:
            self._process_job(job)
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Worker error processing job %s: %s", job.job_id, error_msg)
            self._emit("job_failed", job.recovery_item_id, {
                "job_id": job.job_id,
                "error": error_msg,
                "attempt_count": job.attempt_count,
            })
            # Exponential backoff: 30s, 60s, 120s
            delay = min(30 * (2 ** (job.attempt_count - 1)), 120)
            self._job_repo.mark_failed(job.job_id, error_msg, retry_delay_seconds=delay)
        return True

    def run_loop(self, poll_interval_seconds: float = 5.0) -> None:  # pragma: no cover
        """Run continuously. Call this from the worker process entry point."""
        logger.info("Recovery worker %s starting (poll interval: %ss)", self._worker_id, poll_interval_seconds)
        while True:
            try:
                processed = self.run_once()
                if not processed:
                    time.sleep(poll_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Worker %s shutting down", self._worker_id)
                break
            except Exception as exc:
                logger.exception("Unexpected worker loop error: %s", exc)
                time.sleep(poll_interval_seconds)

    # ------------------------------------------------------------------
    # Core processing pipeline
    # ------------------------------------------------------------------

    def _process_job(self, job: RecoveryJob) -> None:
        """Run the full recovery pipeline for one job.

        Audit events are emitted at each stage so operators can trace
        every worker action without reading internal state.
        """
        self._emit("job_started", job.recovery_item_id, {"job_id": job.job_id})

        # 1. Load recovery item
        item = self._recovery_items.get(job.recovery_item_id)
        if item is None:
            raise ValueError(f"Recovery item {job.recovery_item_id!r} not found for job {job.job_id}")

        # 2. Idempotency guard: terminal items skip execution
        if item.status in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.ESCALATED}:
            self._emit("job_completed", item.id, {
                "job_id": job.job_id,
                "reason": f"item already in terminal state: {item.status.value}",
            })
            self._job_repo.mark_completed(job.job_id)
            return

        # 3. Build context for agent
        failure_category_str = item.root_cause or "unknown"
        if failure_category_str == "mandate_failed":
            failure_category = FailureCategory.MANDATE_FAILURE
        else:
            try:
                failure_category = FailureCategory(failure_category_str)
            except ValueError:
                failure_category = FailureCategory.UNKNOWN

        obs_list = list(item.metadata.get("observations", []))
        prev_acts = [o.get("action") for o in obs_list if o.get("action")]

        ctx = RecoveryContext(
            item_id=item.id,
            failure_category=failure_category,
            retryable=(failure_category not in {FailureCategory.FRAUD, FailureCategory.HARD}),
            amount_minor=item.amount_minor,
            currency=item.currency,
            attempt_count=int(item.metadata.get("attempt_count", 0)),
            customer_opt_out=False,
            previous_actions=prev_acts,
            observations=obs_list,
            max_attempts=self._max_attempts,
            expected_recovery_value=item.expected_recovery_value or 0,
        )

        # 4. Agent proposal (fail-closed on any error)
        self._emit("agent_started", item.id, {"job_id": job.job_id})
        try:
            orch_result = self._orchestrator.decide(ctx)
        except TimeoutError as exc:
            self._emit("agent_failed", item.id, {
                "job_id": job.job_id,
                "reason": "agent_timeout",
                "error": str(exc),
            })
            item = self._escalate_item(item, "agent_timeout")
            self._job_repo.mark_completed(job.job_id)
            return
        except Exception as exc:
            self._emit("agent_failed", item.id, {
                "job_id": job.job_id,
                "reason": "agent_error",
                "error": type(exc).__name__,
            })
            item = self._escalate_item(item, "agent_error")
            self._job_repo.mark_completed(job.job_id)
            return

        proposal = orch_result.proposal
        policy_decision = orch_result.policy_decision

        self._emit("agent_completed", item.id, {
            "job_id": job.job_id,
            "action": proposal.action.value,
            "confidence": proposal.confidence,
        })

        # 5. Fail-closed confidence check
        confidence = proposal.confidence or 0.0

        if confidence < _CONFIDENCE_MINIMUM:
            self._emit("validation_failed", item.id, {
                "job_id": job.job_id,
                "reason": "confidence_below_minimum",
                "confidence": confidence,
                "threshold": _CONFIDENCE_MINIMUM,
            })
            item = self._escalate_item(item, "low_confidence")
            self._save_item(item)
            self._job_repo.mark_completed(job.job_id)
            self._emit("job_completed", item.id, {
                "job_id": job.job_id, "outcome": "escalated_low_confidence",
            })
            return

        if confidence < _CONFIDENCE_AUTO_EXECUTE:
            self._emit("validation_failed", item.id, {
                "job_id": job.job_id,
                "reason": "confidence_requires_human_review",
                "confidence": confidence,
                "threshold": _CONFIDENCE_AUTO_EXECUTE,
            })
            item = self._escalate_item(item, "confidence_requires_human_review")
            self._save_item(item)
            self._job_repo.mark_completed(job.job_id)
            self._emit("job_completed", item.id, {
                "job_id": job.job_id, "outcome": "escalated_medium_confidence",
            })
            return

        self._emit("validation_passed", item.id, {
            "job_id": job.job_id,
            "confidence": confidence,
            "action": proposal.action.value,
        })

        # 6. Safety check: StoppingRules + PolicyEngine + RecoveryGuard
        # (even high confidence cannot bypass these)
        guard_decision = self._guard.evaluate(
            item,
            proposal.action.value,
            container=None,
        )

        if not guard_decision.allowed:
            self._emit("safety_check_failed", item.id, {
                "job_id": job.job_id,
                "reason_code": guard_decision.reason_code,
                "rule": guard_decision.rule,
            })
            final_status = guard_decision.next_state
            item = self._safe_transition(item, final_status)
            item = self._apply_stopped_reason(item, guard_decision.reason_code, guard_decision.rule)
            self._save_item(item)
            self._emit("job_completed", item.id, {
                "job_id": job.job_id,
                "outcome": f"stopped:{guard_decision.reason_code}",
            })
            self._job_repo.mark_completed(job.job_id)
            return

        self._emit("safety_check_passed", item.id, {
            "job_id": job.job_id,
            "action": proposal.action.value,
        })

        # 7. Execute
        self._emit("execution_started", item.id, {
            "job_id": job.job_id,
            "action": proposal.action.value,
        })
        item = self._safe_transition(item, RecoveryStatus.INTERVENTION_PENDING)
        item = self._safe_transition(item, RecoveryStatus.INTERVENTION_EXECUTED)

        attempt_number = int(item.metadata.get("attempt_count", 0)) + 1
        exec_result = self._executor.execute(item, proposal.action.value, attempt_number=attempt_number)

        # Record structured observation
        obs = {
            "action": proposal.action.value,
            "status": "success" if exec_result.success else "failed",
            "reason": exec_result.reason,
            "amount": item.amount_minor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt_number": attempt_number,
            "retry_eligible": exec_result.retry_eligible,
        }
        obs_list.append(obs)
        from dataclasses import replace
        item = replace(item, metadata={**item.metadata, "attempt_count": attempt_number, "observations": obs_list})

        if self._attempts is not None:
            self._attempts.record(AttemptRecord(
                recovery_item_id=item.id,
                attempt_number=attempt_number,
                action=proposal.action.value,
                executed_at=datetime.now(timezone.utc),
                outcome="success" if exec_result.success else "failed",
                failure_reason=exec_result.reason if not exec_result.success else None,
                metadata={"retry_eligible": exec_result.retry_eligible},
            ))

        self._emit("execution_completed", item.id, {
            "job_id": job.job_id,
            "action": proposal.action.value,
            "success": exec_result.success,
            "attempt_number": attempt_number,
        })

        # 8. Post-execution state
        if exec_result.success:
            if proposal.action == RecoveryAction.STOP_RECOVERY:
                item = self._safe_transition(item, RecoveryStatus.STOPPED)
            elif proposal.action == RecoveryAction.ESCALATE_HUMAN:
                item = self._safe_transition(item, RecoveryStatus.ESCALATED)
            else:
                # Intervention executed successfully -> PENDING_VERIFICATION
                # Recovery is recognized ONLY after authoritative settlement verification
                item = self._safe_transition(item, RecoveryStatus.PENDING_VERIFICATION)
                self._emit("pending_verification", item.id, {
                    "job_id": job.job_id,
                    "action": proposal.action.value,
                    "attempt_number": attempt_number,
                })
        else:
            # Execution failed
            from app.policies.retry import DefaultRetryPolicy
            retry_policy = DefaultRetryPolicy(max_attempts=self._max_attempts)
            retry_decision = retry_policy.evaluate(
                item,
                category=failure_category,
                occurred_at=datetime.now(timezone.utc),
            )
            if retry_decision.allowed:
                item = self._safe_transition(item, RecoveryStatus.FAILED)
                item = self._safe_transition(item, RecoveryStatus.QUEUED)
                self._emit("verification_completed", item.id, {
                    "job_id": job.job_id, "result": "retry_scheduled",
                })
            else:
                item = self._safe_transition(item, RecoveryStatus.ESCALATED)
                self._emit("verification_completed", item.id, {
                    "job_id": job.job_id, "result": "retry_exhausted_escalated",
                })

        self._save_item(item)

        # 9. Verify (post-execution audit)
        self._emit("verification_completed", item.id, {
            "job_id": job.job_id,
            "final_status": item.status.value,
            "success": exec_result.success,
        })

        # 10. Complete job
        self._emit("job_completed", item.id, {
            "job_id": job.job_id,
            "final_status": item.status.value,
        })
        self._job_repo.mark_completed(job.job_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, action: str, recovery_item_id: str, metadata: dict) -> None:
        """Emit a worker audit event. Never logs secrets or raw payloads."""
        try:
            self._audit_log.log(
                recovery_item_id=recovery_item_id,
                actor="worker",
                action=action,
                reason=f"Worker lifecycle: {action}",
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to emit audit event %s: %s", action, exc)

    def _escalate_item(self, item: RecoveryItem, reason: str) -> RecoveryItem:
        """Transition item to ESCALATED state."""
        item = self._safe_transition(item, RecoveryStatus.ESCALATED)
        self._emit("job_completed", item.id, {"outcome": "escalated", "reason": reason})
        if self._recovery_items is not None:
            self._recovery_items.save(item)
        return item

    def _safe_transition(self, item: RecoveryItem, target: RecoveryStatus) -> RecoveryItem:
        tr = self._state_machine.transition(item, target)
        return tr.item

    def _save_item(self, item: RecoveryItem) -> None:
        if self._recovery_items is not None:
            self._recovery_items.save(item)

    def _apply_stopped_reason(
        self, item: RecoveryItem, reason_code: str, rule: str
    ) -> RecoveryItem:
        return item.__class__(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=item.status,
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
            stopped_reason=reason_code,
            stopped_rule=rule,
            metadata=item.metadata,
        )

    def _apply_actual_recovery(self, item: RecoveryItem) -> RecoveryItem:
        return item.__class__(
            id=item.id,
            source_type=item.source_type,
            external_id=item.external_id,
            customer_id=item.customer_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            created_at=item.created_at,
            due_at=item.due_at,
            status=item.status,
            root_cause=item.root_cause,
            recovery_probability=item.recovery_probability,
            expected_recovery_value=item.expected_recovery_value,
            intervention_cost=item.intervention_cost,
            failure_category=item.failure_category,
            provider=item.provider,
            provider_event_id=item.provider_event_id,
            actual_recovery_value=item.expected_recovery_value,
            recovery_status=item.recovery_status,
            score_version=item.score_version,
            scoring_reason=item.scoring_reason,
            priority=item.priority,
            metadata=item.metadata,
        )

    def _persist_outcome(self, item: RecoveryItem) -> None:
        from app.domain.models import RecoveryOutcome
        recovered_amount = item.expected_recovery_value or 0
        recovery_cost = item.intervention_cost or 0
        import uuid
        outcome = RecoveryOutcome(
            id=str(uuid.uuid4()),
            recovery_item_id=item.id,
            outcome_type="recovered",
            expected_recovery_minor=recovered_amount,
            actual_recovery_minor=recovered_amount,
            recovery_cost_minor=recovery_cost,
            net_recovery_minor=recovered_amount - recovery_cost,
            recovered_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            metadata={"source": "worker_execution"},
        )
        try:
            self._outcomes.save(outcome)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to persist outcome for %s: %s", item.id, exc)


def _make_worker_id() -> str:
    """Generate a unique worker identifier from hostname + PID."""
    import os
    import socket
    return f"{socket.gethostname()}-{os.getpid()}"
