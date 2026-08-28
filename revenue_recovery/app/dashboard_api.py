from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.evaluation import evaluate_agent, get_golden_scenarios
from app.agents.llm_agent import RealRecoveryDecisionAgent


def build_dashboard_summary(container, *, agent=None) -> dict[str, Any]:
    """Build the executive dashboard summary from persisted data."""
    # Collect all recovery items
    items = []
    if hasattr(container.recovery_items, "_items"):
        items = list(container.recovery_items._items.values())

    total = len(items)
    recovered = [i for i in items if i.status.value == "recovered"]
    escalated = [i for i in items if i.status.value == "escalated"]
    pending = [i for i in items if i.status.value in ("detected", "diagnosed", "queued", "intervention_pending")]
    executed = [i for i in items if i.status.value in ("intervention_executed", "recovered", "failed")]

    total_amount = sum(i.amount_minor for i in items)
    recovered_amount = sum(i.amount_minor for i in recovered)
    expected_value = sum(i.expected_recovery_value or 0 for i in items)

    # Collect attempts
    attempts = []
    if hasattr(container.attempts, "_records"):
        attempts = list(container.attempts._records)

    successful_attempts = [a for a in attempts if a.outcome == "success"]
    failed_attempts = [a for a in attempts if a.outcome == "failed"]

    # Collect decisions
    decisions = []
    if hasattr(container.decisions, "_decisions"):
        decisions = list(container.decisions._decisions)

    policy_allowed = [d for d in decisions if d.get("policy_allowed") is True]
    policy_denied = [d for d in decisions if d.get("policy_allowed") is False]

    recovery_rate = len(recovered) / total if total > 0 else 0.0

    return {
        "total_items": total,
        "total_amount_minor": total_amount,
        "recovered_count": len(recovered),
        "recovered_amount_minor": recovered_amount,
        "expected_recovery_value": expected_value,
        "recovery_rate": round(recovery_rate, 4),
        "escalated_count": len(escalated),
        "pending_count": len(pending),
        "executed_count": len(executed),
        "attempts_total": len(attempts),
        "attempts_successful": len(successful_attempts),
        "attempts_failed": len(failed_attempts),
        "decisions_total": len(decisions),
        "policy_allowed": len(policy_allowed),
        "policy_denied": len(policy_denied),
    }


def build_recovery_items_list(container) -> list[dict[str, Any]]:
    """Build a list of all recovery items for the queue view."""
    items = []
    if hasattr(container.recovery_items, "_items"):
        for item in container.recovery_items._items.values():
            items.append(_item_to_dict(item))
    return sorted(items, key=lambda x: x["created_at"], reverse=True)


def build_case_detail(container, item_id: str) -> dict[str, Any] | None:
    """Build complete case detail including item, decisions, attempts, audit."""
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)

    if item is None:
        return None

    result = _item_to_dict(item)

    # Add decisions
    decisions = []
    if hasattr(container.decisions, "list_by_recovery_item_id"):
        decisions = container.decisions.list_by_recovery_item_id(item_id)
    result["decisions"] = decisions

    # Add attempts
    attempts = []
    if hasattr(container.attempts, "attempts_for"):
        attempts = [_attempt_to_dict(a) for a in container.attempts.attempts_for(item_id)]
    result["attempts"] = attempts

    # Add audit events
    audit_events = []
    if hasattr(container.audit_log, "events_for"):
        audit_events = [_audit_to_dict(e) for e in container.audit_log.events_for(item_id)]
    result["audit_events"] = sorted(audit_events, key=lambda x: x["timestamp"])

    return result


def build_evaluation_report(container, agent=None) -> dict[str, Any]:
    """Run the golden-scenario evaluation and return results."""
    if agent is None:
        agent = RealRecoveryDecisionAgent()

    report = evaluate_agent(agent)
    return {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": report.pass_rate,
        "results": [
            {
                "scenario_name": r.scenario_name,
                "passed": r.passed,
                "proposal_action": r.proposal_action,
                "proposal_confidence": r.proposal_confidence,
                "expected_action": r.expected_action,
                "issues": r.issues,
            }
            for r in report.results
        ],
    }


def _item_to_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_type": item.source_type.value,
        "external_id": item.external_id,
        "customer_id": item.customer_id,
        "amount_minor": item.amount_minor,
        "currency": item.currency,
        "created_at": item.created_at.isoformat(),
        "status": item.status.value,
        "root_cause": item.root_cause,
        "recovery_probability": item.recovery_probability,
        "expected_recovery_value": item.expected_recovery_value,
        "metadata": item.metadata,
    }


def _attempt_to_dict(record) -> dict[str, Any]:
    return {
        "recovery_item_id": record.recovery_item_id,
        "attempt_number": record.attempt_number,
        "action": record.action,
        "executed_at": record.executed_at.isoformat() if record.executed_at else None,
        "outcome": record.outcome,
        "failure_reason": record.failure_reason,
        "metadata": record.metadata,
    }


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
