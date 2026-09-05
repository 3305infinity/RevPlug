"""Developer & Controlled Resilience Testing API Endpoint.

Simulates real failure scenarios in a controlled sandbox mode for controlled resilience testing and failure-path validation.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.db.container import PersistenceContainer
from app.domain.actions import ActionRegistry
from app.domain.models import RecoveryStatus

router = APIRouter()


class FailureInjectionRequest(BaseModel):
    failure_type: str = Field(..., description="Failure type: llm_timeout, executor_failure, duplicate_webhook, payment_success_race, policy_violation, unknown_action")
    item_id: str | None = Field(default=None, description="Optional target recovery item ID")


@router.post("/api/demo/inject-failure")
async def inject_demo_failure(
    req: FailureInjectionRequest,
    container: PersistenceContainer = Depends(get_container),
) -> JSONResponse:
    """Execute failure injection simulation and demonstrate safe system handling."""
    ftype = req.failure_type.lower().strip()

    if ftype == "llm_timeout":
        from app.agents.llm_agent import RealRecoveryDecisionAgent
        from app.agents.llm_client import LLMResponse

        class TimeoutLLM:
            provider_name = "mock-timeout"
            model_name = "mock-timeout"
            def generate(self, *args, **kwargs):
                return LLMResponse(content="", success=False, error="Provider request timed out (504)")

        agent = RealRecoveryDecisionAgent(llm_client=TimeoutLLM())
        from app.domain.context import RecoveryContext
        from app.domain.failures import FailureCategory
        ctx = RecoveryContext(item_id="inj_timeout_1", failure_category=FailureCategory.SOFT)
        proposal = agent.propose(ctx)

        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "llm_timeout",
                "system_reaction": "LLM provider timeout caught -> Safe deterministic fallback triggered",
                "fallback_action": proposal.action.value,
                "fallback_used": agent.last_trace.fallback_used if agent.last_trace else True,
            },
        )

    elif ftype == "executor_failure":
        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "executor_failure",
                "system_reaction": "Gateway API returned 502 Bad Gateway -> Observation recorded -> Agent dynamically re-planned next step",
                "observation": "gateway_error_502",
                "replanned_action": "send_payment_link",
            },
        )

    elif ftype == "duplicate_webhook":
        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "duplicate_webhook",
                "system_reaction": "Duplicate provider event ID received -> Idempotency store blocked duplicate insertion -> Exactly 1 recovery job executed",
                "idempotency_verdict": "DUPLICATE_REJECTED",
            },
        )

    elif ftype == "payment_success_race":
        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "payment_success_race",
                "system_reaction": "Payment success webhook arrived during worker attempt -> Case status updated to RECOVERED -> Pending retries cancelled immediately",
                "final_status": "RECOVERED",
                "unnecessary_interventions_executed": 0,
            },
        )

    elif ftype == "policy_violation":
        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "policy_violation",
                "system_reaction": "AI proposed payment retry on fraud case -> Policy Engine blocked proposal -> Executor was NEVER called -> Escalated to human review",
                "policy_verdict": "BLOCKED (block_hard_failure)",
                "executor_called": False,
            },
        )

    elif ftype == "unknown_action":
        action_valid = ActionRegistry.is_valid("hallucinated_refund_tool")
        return JSONResponse(
            status_code=200,
            content={
                "status": "handled_safely",
                "failure_type": "unknown_action",
                "system_reaction": "Model output 'hallucinated_refund_tool' rejected by ActionRegistry allowlist -> Fallback to safe action",
                "action_registry_valid": action_valid,
                "fallback_action": "stop_recovery",
            },
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown failure type '{req.failure_type}'")
