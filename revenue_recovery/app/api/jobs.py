from typing import Any
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer

router = APIRouter()

@router.get("/api/jobs")
def api_list_jobs(container: PersistenceContainer = Depends(get_container)) -> list[dict[str, Any]]:
    """List recovery jobs. Does not expose secrets or raw payment payloads."""
    job_repo = getattr(container, "jobs", None)
    if job_repo is None:
        return []
    jobs = job_repo.list_jobs(limit=100)
    return [j.to_dict() for j in jobs]

@router.get("/api/jobs/{job_id}")
def api_get_job(job_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get details for a specific recovery job."""
    job_repo = getattr(container, "jobs", None)
    if job_repo is None:
        return JSONResponse(status_code=404, content={"error": "Job queue not available"})
    job = job_repo.get_job(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return JSONResponse(status_code=200, content=job.to_dict())

@router.get("/api/recovery/{item_id}/next-action")
def api_recovery_next_action(item_id: str, container: PersistenceContainer = Depends(get_container)) -> Response:
    """Get the deterministic next best action for a recovery item (worker perspective)."""
    from app.policies.engine import InterventionPolicy
    from app.policies.guard import DefaultRecoveryGuard
    from app.policies.stopping_rules import StoppingRules as _SR

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
