#!/usr/bin/env python
"""Recovery worker entry point.

Run with:
    python scripts/run_worker.py

Environment variables:
    PERSISTENCE_MODE        memory | postgres (default: memory)
    RAZORPAY_WEBHOOK_SECRET Razorpay webhook secret
    WORKER_ID               Optional worker identifier (default: hostname-PID)
    WORKER_POLL_INTERVAL    Seconds between polls when queue is empty (default: 5)
    WORKER_MAX_ATTEMPTS     Max job retry attempts before dead-lettering (default: 3)
    WORKER_TIMEOUT_SECONDS  Seconds after which a PROCESSING job is considered stale (default: 300)
    RECOVERY_AGENT_MODE     mock | llm (default: mock)

The worker polls the recovery_jobs queue, runs the full RecoveryOrchestrator
pipeline with fail-closed AI behavior, and persists outcomes. It is safe to
run multiple worker processes concurrently.
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure the project root is on the path when running as a script
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("recovery_worker")


def main() -> None:
    from app.adapters.razorpay.webhook import RazorpayWebhookService
    from app.agents.decision_agent import MockRecoveryDecisionAgent
    from app.agents.llm_agent import RealRecoveryDecisionAgent
    from app.agents.orchestrator import RecoveryAgentOrchestrator
    from app.agents.validator import ProposalValidator
    from app.db.container import create_persistence_container
    from app.interventions.executor import SimulatedRecoveryExecutor
    from app.policies.engine import InterventionPolicy
    from app.policies.guard import DefaultRecoveryGuard
    from app.policies.stopping_rules import StoppingRules
    from app.scoring.expected_value import ExpectedValueScorer
    from app.worker.recovery_worker import RecoveryWorker

    persistence_mode = os.environ.get("PERSISTENCE_MODE", "memory")
    logger.info("Starting recovery worker (persistence: %s)", persistence_mode)

    container = create_persistence_container(persistence_mode)

    if container.jobs is None:
        logger.error("Job repository not available in persistence container")
        sys.exit(1)

    # Build agent
    agent_mode = os.environ.get("RECOVERY_AGENT_MODE", "mock").lower()
    if agent_mode == "llm":
        from app.agents.llm_client import DeterministicLLMClient
        agent = RealRecoveryDecisionAgent(
            llm_client=DeterministicLLMClient(),
            fallback_agent=MockRecoveryDecisionAgent(),
            name="real-agent",
        )
    else:
        agent = MockRecoveryDecisionAgent()

    max_attempts = int(os.environ.get("WORKER_MAX_ATTEMPTS", "3"))
    worker_timeout = int(os.environ.get("WORKER_TIMEOUT_SECONDS", "300"))
    poll_interval = float(os.environ.get("WORKER_POLL_INTERVAL", "5"))
    worker_id = os.environ.get("WORKER_ID")

    policy_engine = InterventionPolicy(max_retry_attempts=max_attempts)
    stopping_rules = StoppingRules(max_attempts=max_attempts)
    guard = DefaultRecoveryGuard(stopping_rules=stopping_rules, policy_engine=policy_engine)

    orchestrator = RecoveryAgentOrchestrator(
        agent=agent,
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
        attempts=container.attempts,
        outcomes=container.outcomes,
        max_attempts=max_attempts,
        worker_timeout_seconds=worker_timeout,
        worker_id=worker_id,
    )

    logger.info(
        "Worker started (id=%s, max_attempts=%d, timeout=%ds, poll=%.1fs)",
        worker._worker_id, max_attempts, worker_timeout, poll_interval,
    )
    worker.run_loop(poll_interval_seconds=poll_interval)


if __name__ == "__main__":
    main()
