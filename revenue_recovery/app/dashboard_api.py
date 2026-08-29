from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.evaluation import evaluate_agent, get_golden_scenarios
from app.agents.llm_agent import RealRecoveryDecisionAgent


def build_dashboard_summary(container, *, agent=None) -> dict[str, Any]:
    """Build the executive dashboard summary from persisted data."""
    items = []
    if hasattr(container.recovery_items, "_items"):
        items = list(container.recovery_items._items.values())

    total = len(items)
    recovered = [i for i in items if i.status.value == "recovered"]
    escalated = [i for i in items if i.status.value == "escalated"]
    pending = [i for i in items if i.status.value in ("detected", "diagnosed", "queued", "intervention_pending")]
    executed = [i for i in items if i.status.value in ("intervention_executed", "recovered", "failed")]

    total_amount = sum(i.amount_minor for i in items)
    recovered_amount = sum(i.actual_recovery_value or i.amount_minor for i in recovered)
    expected_value = sum(i.expected_recovery_value or 0 for i in items)

    attempts = []
    if hasattr(container.attempts, "_records"):
        attempts = list(container.attempts._records)

    successful_attempts = [a for a in attempts if a.outcome == "success"]
    failed_attempts = [a for a in attempts if a.outcome == "failed"]

    decisions = []
    if hasattr(container.decisions, "_decisions"):
        decisions = list(container.decisions._decisions)

    policy_allowed = [d for d in decisions if d.get("policy_allowed") is True]
    policy_denied = [d for d in decisions if d.get("policy_allowed") is False]

    recovery_rate = len(recovered) / total if total > 0 else 0.0

    priority_distribution: dict[str, int] = {}
    for item in items:
        if item.priority:
            priority_distribution[item.priority] = priority_distribution.get(item.priority, 0) + 1

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
        "priority_distribution": priority_distribution,
    }


def build_recovery_items_list(container, *, priority: str | None = None) -> list[dict[str, Any]]:
    """Build a list of all recovery items for the queue view, ranked by priority."""
    items = []
    if hasattr(container.recovery_items, "_items"):
        items = [_item_to_dict(i) for i in container.recovery_items._items.values()]
    elif hasattr(container.recovery_items, "get"):
        # PostgreSQL-backed: fall back to empty list (API routes handle DB queries)
        pass

    # Deterministic ranking: expected_recovery_value DESC, then tie breakers
    def sort_key(item_dict):
        expected = item_dict.get("expected_recovery_value") or 0
        due_at = item_dict.get("due_at") or ""
        amount = item_dict.get("amount_minor") or 0
        created = item_dict.get("created_at") or ""
        item_id = item_dict.get("id") or ""
        return (
            -expected,
            due_at,
            -amount,
            created,
            item_id,
        )

    items.sort(key=sort_key)

    if priority:
        items = [i for i in items if i.get("priority") == priority]

    return items


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
        "actual_recovery_value": getattr(item, "actual_recovery_value", None),
        "stopped_reason": getattr(item, "stopped_reason", None),
        "stopped_rule": getattr(item, "stopped_rule", None),
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


def build_next_action(container, item_id: str) -> dict[str, Any] | None:
    """Return next best action data for a recovery case."""
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return None

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

    return {
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


def build_batch_economics(container, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate expected vs actual, variance, recovery rate from batch results."""
    total_cases = len(results)
    revenue_at_risk = sum(r.get("amount_minor") or 0 for r in results)
    expected_recovery = sum(r.get("expected_recovery_value") or 0 for r in results)
    actual_recovered = sum(r.get("actual_recovery_value") or 0 for r in results)
    variance = actual_recovered - expected_recovery
    recovery_rate = actual_recovered / revenue_at_risk if revenue_at_risk > 0 else 0.0
    automated = sum(1 for r in results if r.get("status") == "recovered")
    escalated = sum(1 for r in results if r.get("status") == "escalated")
    stopped = sum(1 for r in results if r.get("status") == "stopped")
    return {
        "total_cases": total_cases,
        "revenue_at_risk_minor": revenue_at_risk,
        "expected_recovery_minor": expected_recovery,
        "actual_recovered_minor": actual_recovered,
        "recovery_rate": round(recovery_rate, 4),
        "automated_count": automated,
        "escalated_count": escalated,
        "stopped_count": stopped,
        "variance_minor": variance,
    }


def build_customer_economics(container, customer_id: str) -> dict[str, Any]:
    """Return customer-level totals with proper variance tracking."""
    items = []
    if hasattr(container.recovery_items, "_items"):
        items = [i for i in container.recovery_items._items.values() if i.customer_id == customer_id]

    total_cases = len(items)
    revenue_at_risk = sum(i.amount_minor for i in items)
    recovered_items = [i for i in items if i.status.value == "recovered"]
    actual_recovered = sum(i.actual_recovery_value or i.amount_minor for i in recovered_items)
    expected_recovery = sum(i.expected_recovery_value or 0 for i in items)
    variance = actual_recovered - expected_recovery
    recovery_rate = actual_recovered / revenue_at_risk if revenue_at_risk > 0 else 0.0
    return {
        "customer_id": customer_id,
        "total_cases": total_cases,
        "revenue_at_risk_minor": revenue_at_risk,
        "expected_recovery_minor": expected_recovery,
        "actual_recovered_minor": actual_recovered,
        "recovery_rate": round(recovery_rate, 4),
        "variance_minor": variance,
        "items": [_item_to_dict(i) for i in items],
    }
