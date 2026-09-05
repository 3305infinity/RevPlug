"""Policy Simulator API endpoints.

Provides a preview-only interface for evaluating proposed policy changes
against live opportunities. No live policy is modified.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.policy_simulator import PolicySimulatorService
from app.api.deps import get_container

router = APIRouter(prefix="/api/policy-simulator", tags=["policy-simulator"])


class PolicySimulatorPreviewRequest(BaseModel):
    """Request to preview a proposed policy change."""

    proposed_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Proposed policy fields to overlay on current policy.",
    )
    opportunity_ids: list[str] | None = Field(
        default=None,
        description="Optional list of specific opportunity IDs to evaluate.",
    )


class PolicySimulatorPreviewResponse(BaseModel):
    """Response from a policy simulation preview."""

    simulation_id: str
    timestamp: str
    current_policy_version: str
    proposed_policy_version: str
    opportunities_evaluated: int
    unevaluable_count: int
    unchanged_count: int
    changed_count: int
    current_distribution: dict[str, int]
    proposed_distribution: dict[str, int]
    current_expected_recovery_minor: int
    proposed_expected_recovery_minor: int
    expected_recovery_delta_minor: int
    current_revenue_at_risk_minor: int
    proposed_revenue_at_risk_minor: int
    current_policy_violations: int
    proposed_policy_violations: int
    safety_conflicts: list[dict[str, Any]]
    scope: str
    opportunity_ids: list[str]
    unevaluable_ids: list[str]
    decision_diffs: list[dict[str, Any]]
    error: str | None = None


class PolicyConfigSnapshotResponse(BaseModel):
    """Current active policy snapshot."""

    version: str
    updated_at: str
    updated_by: str
    max_retries: int
    max_contacts_per_24h: int
    min_expected_net_ev_minor: int
    max_intervention_cost_minor: int
    cooldown_retry_minutes: int
    allowed_channels: list[str]
    allowed_payment_methods: list[str]
    escalation_thresholds_minor: int
    failure_categories_blocked: list[str]
    systemic_suppression_threshold_pct: float
    preview_summary: dict[str, Any] | None = None


class PolicyValidationError(BaseModel):
    """Structured validation error for proposed policy."""

    field: str
    message: str
    value: Any


@router.get("/current", response_model=PolicyConfigSnapshotResponse)
def api_policy_simulator_current() -> PolicyConfigSnapshotResponse:
    """Return the current active policy snapshot for the simulator."""
    from app.services.policy_config_service import PolicyConfigStore

    store = PolicyConfigStore.get_instance()
    config = store.get_config()
    return PolicyConfigSnapshotResponse(
        version=config.version,
        updated_at=config.updated_at,
        updated_by=config.updated_by,
        max_retries=config.max_retries,
        max_contacts_per_24h=config.max_contacts_per_24h,
        min_expected_net_ev_minor=config.min_expected_net_ev_minor,
        max_intervention_cost_minor=config.max_intervention_cost_minor,
        cooldown_retry_minutes=config.cooldown_retry_minutes,
        allowed_channels=config.allowed_channels,
        allowed_payment_methods=config.allowed_payment_methods,
        escalation_thresholds_minor=config.escalation_thresholds_minor,
        failure_categories_blocked=config.failure_categories_blocked,
        systemic_suppression_threshold_pct=config.systemic_suppression_threshold_pct,
        preview_summary=getattr(config, "preview_summary", None),
    )


def _validate_proposed_policy(payload: dict[str, Any]) -> list[PolicyValidationError]:
    """Validate proposed policy fields against schema constraints."""
    errors: list[PolicyValidationError] = []
    allowed_fields = {
        "max_retries", "max_contacts_per_24h", "min_expected_net_ev_minor",
        "max_intervention_cost_minor", "cooldown_retry_minutes", "allowed_channels",
        "allowed_payment_methods", "escalation_thresholds_minor", "failure_categories_blocked",
        "systemic_suppression_threshold_pct",
    }
    for field_name, value in payload.items():
        if field_name not in allowed_fields:
            errors.append(PolicyValidationError(
                field=field_name,
                message=f"Unknown policy field: {field_name}",
                value=value,
            ))
    return errors


@router.post("/preview", response_model=PolicySimulatorPreviewResponse)
def api_policy_simulator_preview(
    payload: PolicySimulatorPreviewRequest,
    container: Any = Depends(get_container),
) -> PolicySimulatorPreviewResponse:
    """Preview how a proposed policy change would affect recovery decisions.

    This endpoint does NOT modify live policy. It evaluates the proposed
    policy against the current opportunity set and returns decision diffs.
    """
    validation_errors = _validate_proposed_policy(payload.proposed_policy)
    if validation_errors:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail={"validation_errors": [e.model_dump() for e in validation_errors]})

    service = PolicySimulatorService()
    result = service.preview_policy_change(
        payload.proposed_policy,
        opportunity_ids=payload.opportunity_ids,
        container=container,
    )

    return PolicySimulatorPreviewResponse(
        simulation_id=result.simulation_id,
        timestamp=result.timestamp,
        current_policy_version=result.current_policy_version,
        proposed_policy_version=result.proposed_policy_version,
        opportunities_evaluated=result.opportunities_evaluated,
        unevaluable_count=result.unevaluable_count,
        unchanged_count=result.unchanged_count,
        changed_count=result.changed_count,
        current_distribution=result.current_distribution,
        proposed_distribution=result.proposed_distribution,
        current_expected_recovery_minor=result.current_expected_recovery_minor,
        proposed_expected_recovery_minor=result.proposed_expected_recovery_minor,
        expected_recovery_delta_minor=result.expected_recovery_delta_minor,
        current_revenue_at_risk_minor=result.current_revenue_at_risk_minor,
        proposed_revenue_at_risk_minor=result.proposed_revenue_at_risk_minor,
        current_policy_violations=result.current_policy_violations,
        proposed_policy_violations=result.proposed_policy_violations,
        safety_conflicts=result.safety_conflicts,
        scope=result.scope,
        opportunity_ids=result.opportunity_ids,
        unevaluable_ids=result.unevaluable_ids,
        decision_diffs=[
            {
                "opportunity_id": d.opportunity_id,
                "changed": d.changed,
                "change_type": d.change_type,
                "policy_rule_responsible": d.policy_rule_responsible,
                "current": {
                    "decision_type": d.current.decision_type,
                    "allowed": d.current.allowed,
                    "reason_code": d.current.reason_code,
                    "reason": d.current.reason,
                    "rule": d.current.rule,
                    "proposed_action": d.current.proposed_action,
                    "next_state": d.current.next_state,
                    "safety_context": d.current.safety_context,
                },
                "proposed": {
                    "decision_type": d.proposed.decision_type,
                    "allowed": d.proposed.allowed,
                    "reason_code": d.proposed.reason_code,
                    "reason": d.proposed.reason,
                    "rule": d.proposed.rule,
                    "proposed_action": d.proposed.proposed_action,
                    "next_state": d.proposed.next_state,
                    "safety_context": d.proposed.safety_context,
                },
                "financial_context": d.financial_context,
                "safety_context": d.safety_context,
            }
            for d in result.decision_diffs
        ],
        error=result.error,
    )
