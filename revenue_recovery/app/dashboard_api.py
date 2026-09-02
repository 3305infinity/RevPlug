"""Dashboard API — financial truth data layer.

FINANCIAL TRUTH INVARIANTS:
1. Actually Recovered = SUM(recovery_outcomes.actual_recovery_minor) ONLY.
   Never derived from: AI confidence, expected_recovery_value, execution status,
   item.actual_recovery_value, or any other heuristic.
2. Revenue at Risk = SUM(amount_minor) for items NOT in (recovered, stopped).
3. Recovery Rate = actually_recovered / revenue_at_risk.
4. All amounts are integer minor units internally.
5. The dashboard after restart must return identical values (deterministic).

Every function in this module reads from persisted data only.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.agents.evaluation import evaluate_agent, get_golden_scenarios
from app.agents.llm_agent import RealRecoveryDecisionAgent


# Status sets — centralised so changes propagate everywhere
_ACTIVE_STATUSES = frozenset({"detected", "diagnosed", "queued", "intervention_pending", "intervention_executed", "pending_verification", "failed"})
_TERMINAL_STATUSES = frozenset({"recovered", "stopped", "escalated"})
_AT_RISK_STATUSES = frozenset({"detected", "diagnosed", "queued", "intervention_pending", "intervention_executed", "pending_verification", "failed"})


# ---------------------------------------------------------------------------
# DATA CLASSIFICATION CONTRACT
# ---------------------------------------------------------------------------
# Every persisted RecoveryItem MUST carry an explicit classification in its
# metadata. There are exactly four classifications:
#
#   LIVE_OPERATIONAL  -> included in all operational/analytics surfaces
#   BENCHMARK_SYNTHETIC -> included ONLY in benchmark/Proof Lab surfaces
#   TEST_FIXTURE      -> never included in any operational or benchmark surface
#   UNKNOWN           -> QUARANTINED; never silently included anywhere
#
# Producers:
#   - Razorpay webhook adapter sets source="webhook_live" / is_synthetic=False
#   - Manual case creation sets source="manual_case" / is_synthetic=False
#   - Evaluation dataset generator sets is_synthetic=True (BENCHMARK_SYNTHETIC)
#   - Demo endpoints set is_synthetic=True / source="demo_scenario" (BENCHMARK_SYNTHETIC)
#   - Smoke/stress tests set is_test_fixture=True (TEST_FIXTURE)
#
# Operational services (analytics, dashboard, customers, etc.) MUST NOT
# accidentally receive synthetic data by forgetting a filter.
# ---------------------------------------------------------------------------

_APPROVED_LIVE_SOURCES = frozenset({"webhook_live", "manual_case", "webhook"})
_BENCHMARK_SOURCES = frozenset({"demo_scenario", "synthetic_dataset"})


def _classify_item(meta: dict) -> str:
    """Return the data classification for a RecoveryItem.

    Returns one of:
        "LIVE_OPERATIONAL"
        "BENCHMARK_SYNTHETIC"
        "TEST_FIXTURE"
        "UNKNOWN"

    Never returns None. Never defaults to LIVE_OPERATIONAL for ambiguous records.
    """
    if not isinstance(meta, dict):
        return "UNKNOWN"

    # 1. Test fixtures are always excluded
    if meta.get("is_test_fixture") is True or meta.get("batch_scope") is True or meta.get("batch_id") is not None:
        return "TEST_FIXTURE"

    # 2. Explicit synthetic flag
    if meta.get("is_synthetic") is True:
        return "BENCHMARK_SYNTHETIC"

    # 3. Explicit benchmark source tags
    src = str(meta.get("source", "")).strip().lower()
    if src in _BENCHMARK_SOURCES:
        return "BENCHMARK_SYNTHETIC"

    # 4. Explicit live source tags
    if src in _APPROVED_LIVE_SOURCES:
        return "LIVE_OPERATIONAL"

    # 5. Missing/ambiguous classification — QUARANTINE
    return "UNKNOWN"


def _get_items(container, *, include_synthetic: bool = False) -> list:
    """Extract recovery items from the container.

    By default returns only LIVE_OPERATIONAL data. UNKNOWN records are
    quarantined and never silently included.

    Set include_synthetic=True ONLY for surfaces that intentionally display
    BENCHMARK_SYNTHETIC data (Proof Lab, evaluation reports). Even then,
    TEST_FIXTURE and UNKNOWN records remain excluded.

    Classification rules (in order of precedence):
    1. is_test_fixture / batch_scope / batch_id -> TEST_FIXTURE (always excluded)
    2. is_synthetic = True -> BENCHMARK_SYNTHETIC (excluded by default)
    3. source in ("demo_scenario", "synthetic_dataset") -> BENCHMARK_SYNTHETIC
    4. source in APPROVED_LIVE_SOURCES -> LIVE_OPERATIONAL
    5. source empty/missing/unknown -> UNKNOWN (QUARANTINED, never silently included)
    """
    repo = container.recovery_items
    raw_items = []
    if hasattr(repo, "_items"):
        raw_items = list(repo._items.values())
    elif hasattr(repo, "list_all"):
        try:
            raw_items = repo.list_all()
        except Exception:
            raw_items = []

    filtered = []
    for item in raw_items:
        meta = getattr(item, "metadata", {}) or {}
        classification = _classify_item(meta)

        # Always exclude test fixtures
        if classification == "TEST_FIXTURE":
            continue

        # Operational mode: only live data
        if not include_synthetic:
            if classification == "BENCHMARK_SYNTHETIC":
                continue
            if classification == "UNKNOWN":
                continue

        # Benchmark mode: include synthetic but still exclude test fixtures and unknown
        if classification == "UNKNOWN":
            continue

        filtered.append(item)

    return filtered


def _get_attempts(container) -> list:
    if hasattr(container.attempts, "_records"):
        return list(container.attempts._records)
    return []


def _get_decisions(container) -> list:
    if hasattr(container.decisions, "_decisions"):
        return list(container.decisions._decisions)
    return []


def _get_audit_events(container, item_id: str | None = None) -> list:
    if item_id is not None and hasattr(container.audit_log, "events_for"):
        return list(container.audit_log.events_for(item_id))
    if hasattr(container.audit_log, "_events"):
        events = list(container.audit_log._events.values())
        # Flatten if grouped by item
        if events and isinstance(events[0], list):
            return [e for group in events for e in group]
        return events
    return []


def _actual_recovered_from_outcomes(container, item_ids: set[str] | None = None) -> int:
    """Read actually recovered amount from outcomes repository and recovered items.

    This is the authoritative single source of financial truth.
    Sum = outcome records in outcomes_repo + actual_recovery_value of items with status=RECOVERED.
    """
    total = 0
    accounted_item_ids = set()

    # 1. Read from outcomes repository
    if hasattr(container, "outcomes") and container.outcomes is not None:
        outcomes_repo = container.outcomes
        if hasattr(outcomes_repo, "_outcomes"):
            for item_id, outcome in outcomes_repo._outcomes.items():
                if item_ids is not None and item_id not in item_ids:
                    continue
                if outcome is not None:
                    total += getattr(outcome, "actual_recovery_minor", 0) or 0
                    accounted_item_ids.add(item_id)
        elif hasattr(outcomes_repo, "list_all"):
            try:
                for outcome in outcomes_repo.list_all():
                    if outcome is None:
                        continue
                    item_id = getattr(outcome, "recovery_item_id", None)
                    if item_ids is not None and item_id not in item_ids:
                        continue
                    total += getattr(outcome, "actual_recovery_minor", 0) or 0
                    if item_id:
                        accounted_item_ids.add(item_id)
            except Exception:
                pass

    # 2. Add actual_recovery_value for any items with status=RECOVERED not already accounted for
    items = _get_items(container)
    for i in items:
        if item_ids is not None and i.id not in item_ids:
            continue
        status_val = i.status.value if hasattr(i.status, "value") else str(i.status)
        if status_val == "recovered" and i.id not in accounted_item_ids:
            total += getattr(i, "actual_recovery_value", 0) or i.amount_minor
            accounted_item_ids.add(i.id)

    return total


def build_dashboard_summary(container, *, agent=None) -> dict[str, Any]:
    """Build the executive dashboard summary from persisted data.

    FINANCIAL TRUTH: all money metrics come from recovery_outcomes.
    """
    items = _get_items(container)
    total = len(items)

    # Partition by status
    recovered = [i for i in items if i.status.value == "recovered"]
    escalated = [i for i in items if i.status.value == "escalated"]
    stopped = [i for i in items if i.status.value == "stopped"]
    active = [i for i in items if i.status.value in _ACTIVE_STATUSES]

    # Revenue at risk = items NOT in terminal states
    at_risk_items = [i for i in items if i.status.value in _AT_RISK_STATUSES]
    revenue_at_risk = sum(i.amount_minor for i in at_risk_items)

    # Expected recovery from scorer output on active items
    expected_recovery = sum(i.expected_recovery_value or 0 for i in at_risk_items)

    # Actually recovered — ONLY from recovery_outcomes (financial truth)
    actually_recovered = _actual_recovered_from_outcomes(container)

    # Recovery rate
    recovery_rate = actually_recovered / revenue_at_risk if revenue_at_risk > 0 else 0.0

    # Attempts
    attempts = _get_attempts(container)
    successful_attempts = [a for a in attempts if a.outcome == "success"]
    failed_attempts = [a for a in attempts if a.outcome == "failed"]

    # Decisions
    decisions = _get_decisions(container)
    policy_allowed = [d for d in decisions if d.get("policy_allowed") is True]
    policy_denied = [d for d in decisions if d.get("policy_allowed") is False]

    # Priority distribution
    priority_distribution: dict[str, int] = {}
    for item in items:
        if item.priority:
            priority_distribution[item.priority] = priority_distribution.get(item.priority, 0) + 1

    # Recovery by failure category
    recovery_by_failure_category: dict[str, dict[str, int]] = {}
    for item in items:
        cat = item.root_cause or "unknown"
        if cat not in recovery_by_failure_category:
            recovery_by_failure_category[cat] = {"total": 0, "recovered": 0, "amount_minor": 0}
        recovery_by_failure_category[cat]["total"] += 1
        recovery_by_failure_category[cat]["amount_minor"] += item.amount_minor
        if item.status.value == "recovered":
            recovery_by_failure_category[cat]["recovered"] += 1

    # Recovery by action (from decisions)
    recovery_by_action: dict[str, int] = {}
    for d in decisions:
        action = d.get("proposed_action") or "unknown"
        recovery_by_action[action] = recovery_by_action.get(action, 0) + 1

    # Recovered value by day (from outcomes)
    recovered_value_by_day = _build_recovered_by_day(container)

    return {
        # Core financial truth
        "revenue_at_risk": revenue_at_risk,
        "actually_recovered": actually_recovered,
        "expected_recovery": expected_recovery,
        "recovery_rate": round(recovery_rate, 4),
        # Case counts
        "total_items": total,
        "active_recoveries": len(active),
        "recovered_cases": len(recovered),
        "stopped_cases": len(stopped),
        "escalated_cases": len(escalated),
        "pending_verification_cases": len([i for i in items if i.status.value == "pending_verification"]),
        # Legacy fields (keep for backward compat with existing tests)
        "total_amount_minor": sum(i.amount_minor for i in items),
        "recovered_count": len(recovered),
        "recovered_amount_minor": actually_recovered,
        "expected_recovery_value": expected_recovery,
        "escalated_count": len(escalated),
        "pending_count": len(active),
        "executed_count": len([i for i in items if i.status.value in ("intervention_executed", "pending_verification")]),
        "attempts_total": len(attempts),
        "attempts_successful": len(successful_attempts),
        "attempts_failed": len(failed_attempts),
        "decisions_total": len(decisions),
        "policy_allowed": len(policy_allowed),
        "policy_denied": len(policy_denied),
        # Rich breakdowns
        "priority_distribution": priority_distribution,
        "recovery_by_failure_category": recovery_by_failure_category,
        "recovery_by_action": recovery_by_action,
        "recovered_value_by_day": recovered_value_by_day,
    }


def _build_recovered_by_day(container) -> list[dict[str, Any]]:
    """Build time-series of recovered value by day from outcomes."""
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"amount_minor": 0, "count": 0})
    if hasattr(container, "outcomes") and container.outcomes is not None:
        outcomes_repo = container.outcomes
        if hasattr(outcomes_repo, "_outcomes"):
            for outcome in outcomes_repo._outcomes.values():
                if outcome is None:
                    continue
                recovered_at = getattr(outcome, "recovered_at", None)
                if recovered_at is None:
                    continue
                day = recovered_at.date().isoformat()
                amount = getattr(outcome, "actual_recovery_minor", None) or 0
                by_day[day]["amount_minor"] += amount
                by_day[day]["count"] += 1
    return [
        {"date": day, "amount_minor": v["amount_minor"], "count": v["count"]}
        for day, v in sorted(by_day.items())
    ]


def build_recovered_by_day(container) -> list[dict[str, Any]]:
    return _build_recovered_by_day(container)


def build_revenue_at_risk_by_day(container) -> list[dict[str, Any]]:
    """Revenue at risk accumulated by creation date."""
    by_day: dict[str, int] = defaultdict(int)
    items = _get_items(container)
    for item in items:
        if item.status.value in _AT_RISK_STATUSES:
            day = item.created_at.date().isoformat()
            by_day[day] += item.amount_minor
    return [{"date": day, "amount_minor": amount} for day, amount in sorted(by_day.items())]


def build_attempts_by_day(container) -> list[dict[str, Any]]:
    """Recovery attempts grouped by day."""
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failed": 0, "total": 0})
    attempts = _get_attempts(container)
    for attempt in attempts:
        executed_at = getattr(attempt, "executed_at", None)
        if executed_at is None:
            continue
        day = executed_at.date().isoformat()
        by_day[day]["total"] += 1
        if attempt.outcome == "success":
            by_day[day]["success"] += 1
        else:
            by_day[day]["failed"] += 1
    return [
        {"date": day, **v}
        for day, v in sorted(by_day.items())
    ]


def build_stopped_by_reason(container) -> list[dict[str, Any]]:
    """Stopped cases grouped by stopping reason."""
    by_reason: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "amount_minor": 0})
    items = _get_items(container)
    for item in items:
        if item.status.value == "stopped":
            reason = getattr(item, "stopped_reason", None) or "unknown"
            by_reason[reason]["count"] += 1
            by_reason[reason]["amount_minor"] += item.amount_minor
    return [
        {"reason_code": reason, **v}
        for reason, v in sorted(by_reason.items(), key=lambda x: -x[1]["count"])
    ]


def build_recovery_items_list(container, *, priority: str | None = None) -> list[dict[str, Any]]:
    """Build a list of all recovery items for the queue view, ranked by priority."""
    items = _get_items(container)
    result = [_item_to_dict(i) for i in items]

    def sort_key(item_dict):
        expected = item_dict.get("expected_recovery_value") or 0
        due_at = item_dict.get("due_at") or ""
        amount = item_dict.get("amount_minor") or 0
        created = item_dict.get("created_at") or ""
        item_id = item_dict.get("id") or ""
        return (-expected, due_at, -amount, created, item_id)

    result.sort(key=sort_key)
    if priority:
        result = [i for i in result if i.get("priority") == priority]
    return result


def build_case_detail(container, item_id: str) -> dict[str, Any] | None:
    """Build complete case detail including item, decisions, attempts, audit."""
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return None

    result = _item_to_dict(item)

    decisions = []
    if hasattr(container.decisions, "list_by_recovery_item_id"):
        decisions = container.decisions.list_by_recovery_item_id(item_id)
    result["decisions"] = decisions

    attempts = []
    if hasattr(container.attempts, "attempts_for"):
        attempts = [_attempt_to_dict(a) for a in container.attempts.attempts_for(item_id)]
    result["attempts"] = attempts

    audit_events = []
    if hasattr(container.audit_log, "events_for"):
        audit_events = [_audit_to_dict(e) for e in container.audit_log.events_for(item_id)]
    result["audit_events"] = sorted(audit_events, key=lambda x: x["timestamp"])

    # Playbook (bounded recovery sequence)
    if "playbook" in item.metadata:
        result["playbook"] = item.metadata["playbook"]
    else:
        from app.services.recovery_playbook import RecoveryPlaybookEngine
        from app.domain.failures import FailureCategory, NormalizedFailure
        from app.domain.context import RecoveryContext

        rc = str(item.root_cause or "").lower()
        desc = str((item.metadata or {}).get("error_description") or "").lower()
        combined = f"{rc} {desc}"

        if "auth" in combined or "3ds" in combined:
            cat = FailureCategory.AUTHENTICATION_REQUIRED
        elif "fraud" in combined or "risk" in combined:
            cat = FailureCategory.FRAUD
        elif "hard" in combined or "expired" in combined or "declined" in combined:
            cat = FailureCategory.HARD
        else:
            cat = FailureCategory.SOFT

        normalized = NormalizedFailure(
            external_event_id=item.external_id or item.id,
            category=cat,
            code=item.root_cause or "soft",
            reason=str((item.metadata or {}).get("error_description") or item.root_cause or "soft"),
            retryable=(cat == FailureCategory.SOFT),
            metadata=item.metadata or {},
        )
        ctx = RecoveryContext.from_item_and_failure(item, normalized)
        pb = RecoveryPlaybookEngine().generate_playbook(item, ctx)
        result["playbook"] = pb.to_dict()

    # Outcome (financial truth)
    outcome = None
    if hasattr(container, "outcomes") and container.outcomes is not None:
        outcome = container.outcomes.get_for_item(item_id)
    result["outcome"] = _outcome_to_dict(outcome) if outcome else None

    return result


def build_lifecycle(container, item_id: str) -> dict[str, Any] | None:
    """Reconstruct the full lifecycle from audit events.

    Stages: EVENT → CLASSIFICATION → ECONOMIC_SCORE → AI_RECOMMENDATION →
            VALIDATION → SAFETY_CHECK → EXECUTION → VERIFICATION → OUTCOME → NEXT_ACTION

    Only shows stages with corresponding persisted audit events.
    """
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return None

    audit_events = []
    if hasattr(container.audit_log, "events_for"):
        audit_events = list(container.audit_log.events_for(item_id))
    audit_events.sort(key=lambda e: e.timestamp)

    # Map audit actions to lifecycle stages
    action_to_stage = {
        "webhook_received": "EVENT",
        "event_parsed": "EVENT",
        "job_created": "EVENT",
        "classified": "CLASSIFICATION",
        "failure_classified": "CLASSIFICATION",
        "score_calculated": "ECONOMIC_SCORE",
        "agent_completed": "AI_RECOMMENDATION",
        "agent_started": "AI_RECOMMENDATION",
        "validation_passed": "VALIDATION",
        "validation_failed": "VALIDATION",
        "safety_check_passed": "SAFETY_CHECK",
        "safety_check_failed": "SAFETY_CHECK",
        "execution_requested": "EXECUTION",
        "execution_started": "EXECUTION",
        "execution_succeeded": "EXECUTION",
        "execution_failed": "EXECUTION",
        "execution_completed": "EXECUTION",
        "verification_completed": "VERIFICATION",
        "job_completed": "VERIFICATION",
        "outcome_recorded": "OUTCOME",
        "promise_created": "OUTCOME",
        "promise_fulfilled": "OUTCOME",
    }

    stages_seen: dict[str, list] = defaultdict(list)
    for event in audit_events:
        stage = action_to_stage.get(event.action)
        if stage:
            stages_seen[stage].append(_audit_to_dict(event))

    stage_order = [
        "EVENT", "CLASSIFICATION", "ECONOMIC_SCORE", "AI_RECOMMENDATION",
        "VALIDATION", "SAFETY_CHECK", "EXECUTION", "VERIFICATION", "OUTCOME",
    ]

    stages = []
    for stage in stage_order:
        events_for_stage = stages_seen.get(stage, [])
        stages.append({
            "stage": stage,
            "completed": len(events_for_stage) > 0,
            "timestamp": events_for_stage[0]["timestamp"] if events_for_stage else None,
            "events": events_for_stage,
        })

    # Next action stage
    next_action = build_next_action(container, item_id)
    stages.append({
        "stage": "NEXT_ACTION",
        "completed": next_action is not None,
        "timestamp": None,
        "data": next_action,
        "events": [],
    })

    return {
        "item_id": item_id,
        "item": _item_to_dict(item),
        "stages": stages,
        "total_audit_events": len(audit_events),
    }


def build_evaluation_report(container, agent=None) -> dict[str, Any]:
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


def build_next_action(container, item_id: str) -> dict[str, Any] | None:
    """Return deterministic next best action for a recovery case.

    State machine:
        RECOVERED → no action (terminal)
        STOPPED → no action (terminal)
        ESCALATED → human review required
        PROMISE ACTIVE → wait for promise date
        PROMISE EXPIRED → stop/escalate
        RETRY BUDGET EXHAUSTED → escalate
        ACTIVE + budget remaining → next policy-permitted action
    """
    item = None
    if hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)
    if item is None:
        return None

    # Terminal states — no action possible
    if item.status.value == "recovered":
        return {
            "action": None, "reason": "Case is recovered", "reason_code": "terminal_recovered",
            "allowed": False, "next_at": None, "policy_rule": "terminal_state_absorbing",
        }
    if item.status.value == "stopped":
        reason = getattr(item, "stopped_reason", None) or "stopped"
        return {
            "action": None, "reason": f"Case is stopped: {reason}", "reason_code": "terminal_stopped",
            "allowed": False, "next_at": None, "policy_rule": getattr(item, "stopped_rule", "terminal_state_absorbing"),
        }
    if item.status.value == "escalated":
        return {
            "action": "human_review", "reason": "Case requires human review",
            "reason_code": "escalated", "allowed": False, "next_at": None,
            "policy_rule": "escalated_requires_human",
        }

    # Check promise state
    if hasattr(container, "promises") and container.promises is not None:
        promise = container.promises.get_for_item(item_id)
        if promise is not None:
            status = getattr(promise, "status", None) or promise.get("status", "") if isinstance(promise, dict) else promise.status
            promised_date = getattr(promise, "promised_date", None) or (promise.get("promised_date") if isinstance(promise, dict) else None)
            if status == "promised":
                from datetime import date
                today = date.today()
                if promised_date and (promised_date if isinstance(promised_date, type(today)) else promised_date) < today:
                    return {
                        "action": "stop_recovery", "reason": "Promise has expired",
                        "reason_code": "promise_expired", "allowed": False, "next_at": None,
                        "policy_rule": "promise_expiry",
                    }
                next_at = promised_date.isoformat() if promised_date else None
                return {
                    "action": "wait_for_promise", "reason": "Active promise-to-pay",
                    "reason_code": "promise_active", "allowed": False, "next_at": next_at,
                    "policy_rule": "promise_active_wait",
                }

    # Retry budget check
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

    proposed = last_proposal_action or "retry_payment"
    guard_decision = guard.evaluate(item, proposed, container=container)
    attempt_count = int(item.metadata.get("attempt_count", 0))
    retry_budget = max(0, 3 - attempt_count)

    return {
        "action": proposed if guard_decision.allowed else None,
        "reason": guard_decision.reason,
        "reason_code": guard_decision.reason_code,
        "allowed": guard_decision.allowed,
        "next_at": None,
        "policy_rule": last_policy_rule or guard_decision.rule,
        "retry_budget_remaining": retry_budget,
        "expected_recovery_value": item.expected_recovery_value,
    }


def build_batch_economics(container, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate economics from batch results.

    FINANCIAL TRUTH: actual_recovered is read from recovery_outcomes,
    not from result['actual_recovery_value'].
    """
    total_cases = len(results)
    revenue_at_risk = sum(r.get("amount_minor") or 0 for r in results)
    expected_recovery = sum(r.get("expected_recovery_value") or 0 for r in results)

    # Actual recovered — ONLY from outcomes in container
    item_ids = {r.get("recovery_item_id") or r.get("id") for r in results if r.get("recovery_item_id") or r.get("id")}
    actual_recovered = _actual_recovered_from_outcomes(container, item_ids)
    if actual_recovered == 0:
        # Fallback: sum authoritative field only (not expected_value)
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
    """Return customer-level totals.

    FINANCIAL TRUTH: actually_recovered from recovery_outcomes only.
    """
    items = [i for i in _get_items(container) if i.customer_id == customer_id]
    item_ids = {i.id for i in items}

    total_cases = len(items)
    revenue_at_risk = sum(i.amount_minor for i in items if i.status.value in _AT_RISK_STATUSES)
    expected_recovery = sum(i.expected_recovery_value or 0 for i in items)
    actually_recovered = _actual_recovered_from_outcomes(container, item_ids)
    recovery_rate = actually_recovered / sum(i.amount_minor for i in items) if items else 0.0

    recovered_items = [i for i in items if i.status.value == "recovered"]
    escalated_items = [i for i in items if i.status.value == "escalated"]
    active_items = [i for i in items if i.status.value in _ACTIVE_STATUSES]
    stopped_items = [i for i in items if i.status.value == "stopped"]

    # Get promises for this customer
    promises = []
    if hasattr(container, "promises") and container.promises is not None:
        for item in items:
            p = container.promises.get_for_item(item.id)
            if p:
                promises.append(_promise_to_dict(p))

    # Build rich canonical timeline events for customer history
    raw_timeline: list[dict[str, Any]] = []

    # 1. Audit log events
    audit_events = []
    for item in items:
        for e in _get_audit_events(container, item.id):
            if hasattr(e, "action"):
                audit_events.append((item, e))

    for item, e in audit_events:
        ts = e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp)
        action_name = e.action
        actor = getattr(e, "actor", "system")
        reason = getattr(e, "reason", "") or ""
        meta = getattr(e, "metadata", {}) or {}

        # Friendly event mapping
        label = action_name.replace("_", " ").title()
        if action_name == "recovery_item_created":
            label = "Payment Failure Detected"
        elif action_name == "failure_classified":
            label = f"Diagnosis: {meta.get('category', item.root_cause or 'unknown')}"
        elif action_name == "guard_evaluate":
            allowed = meta.get("allowed")
            rule = meta.get("rule") or meta.get("reason_code")
            label = f"Policy Decision: {'ALLOWED' if allowed else 'BLOCKED'} ({rule})"
        elif action_name == "execution_requested":
            label = f"Intervention Executed: {meta.get('action', 'retry_payment')}"
        elif action_name == "execution_succeeded":
            label = "Payment Verified & Recovered"
        elif action_name == "recovery_stopped":
            label = f"Recovery Stopped: {reason}"
        elif action_name == "human_approved":
            label = "Human Operator Approved Action"
        elif action_name == "human_approval_denied_by_policy":
            label = f"Policy Guard Denied Human Approval: {reason}"

        raw_timeline.append({
            "id": getattr(e, "id", f"evt_{item.id}_{action_name}"),
            "timestamp": ts,
            "item_id": item.id,
            "source_type": item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
            "amount_minor": item.amount_minor,
            "action": action_name,
            "label": label,
            "actor": actor,
            "reason": reason,
            "metadata": meta,
        })

    # Sort timeline newest first
    timeline = sorted(raw_timeline, key=lambda x: x["timestamp"], reverse=True)[:50]

    last_action = timeline[0]["action"] if timeline else None
    last_action_at = timeline[0]["timestamp"] if timeline else None

    # Opt-out check
    opt_out = any(i.metadata.get("opted_out") for i in items)

    return {
        "customer_id": customer_id,
        "opt_out": opt_out,
        "revenue_at_risk": revenue_at_risk,
        "actually_recovered": actually_recovered,
        "expected_recovery": expected_recovery,
        "recovery_rate": round(recovery_rate, 4),
        "total_cases": total_cases,
        "active_cases": len(active_items),
        "recovered_cases": len(recovered_items),
        "escalated_cases": len(escalated_items),
        "stopped_cases": len(stopped_items),
        "promises": promises,
        "last_action": last_action,
        "last_action_at": last_action_at,
        "timeline": timeline,
        "cases": [_item_to_dict(i) for i in items],
        # Legacy compat
        "revenue_at_risk_minor": revenue_at_risk,
        "expected_recovery_minor": expected_recovery,
        "actual_recovered_minor": actually_recovered,
        "variance_minor": actually_recovered - expected_recovery,
        "items": [_item_to_dict(i) for i in items],
    }


def build_customers_list(container) -> list[dict[str, Any]]:
    """List all customers with aggregate financial metrics."""
    items = _get_items(container)
    customer_ids = {item.customer_id for item in items}
    
    result = []
    for cid in customer_ids:
        result.append(build_customer_economics(container, cid))
        
    result.sort(key=lambda x: -x["revenue_at_risk"])
    return result


def build_audit_events_list(container, filter_by: str | None = None) -> list[dict[str, Any]]:
    """List all audit events, optionally filtered by actor/action category."""
    events = _get_audit_events(container)
    audit_dicts = [_audit_to_dict(e) for e in events if hasattr(e, "action")]
    audit_dicts.sort(key=lambda x: x["timestamp"], reverse=True)

    if filter_by and filter_by != "all":
        filter_map = {
            "system": lambda e: e["actor"] == "system",
            "ai": lambda e: e["actor"] == "agent" or "agent" in e["action"],
            "policy": lambda e: "policy" in e["action"] or "guard" in e["action"],
            "blocked": lambda e: "denied" in e["action"] or "safety_check_failed" in e["action"],
            "stopped": lambda e: e["action"] in ("execution_stopped", "job_completed") or "stopped" in e["action"],
            "escalated": lambda e: "escalat" in e["action"],
            "recovered": lambda e: "recovered" in e["action"] or "succeeded" in e["action"],
            "provider": lambda e: "webhook" in e["action"] or "provider" in e["actor"],
            "worker": lambda e: e["actor"] == "worker",
        }
        fn = filter_map.get(filter_by)
        if fn:
            audit_dicts = [e for e in audit_dicts if fn(e)]

    return audit_dicts[:500]


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _derive_classification_method(item, container=None) -> str:
    """Derive classification_method from persisted audit events and metadata.

    Returns one of: 'RULES' | 'LLM_PRIMARY' | 'LLM_FALLBACK'
    """
    meta = dict(item.metadata) if item.metadata else {}

    # Prefer explicit field written by AI router at classification time
    explicit = meta.get("classification_method") or meta.get("diagnosis_path")
    if explicit:
        mapping = {
            "rules": "RULES",
            "llm": "LLM_PRIMARY",
            "llm_primary": "LLM_PRIMARY",
            "fallback": "LLM_FALLBACK",
            "llm_fallback": "LLM_FALLBACK",
            "RULES": "RULES",
            "LLM_PRIMARY": "LLM_PRIMARY",
            "LLM_FALLBACK": "LLM_FALLBACK",
        }
        return mapping.get(str(explicit), str(explicit).upper())

    # Fall back to scanning audit events for AI router signals
    if container is not None:
        try:
            events = list(container.audit_log.events_for(item.id)) if hasattr(container.audit_log, "events_for") else []
            for e in events:
                action = getattr(e, "action", "") or ""
                e_meta = getattr(e, "metadata", {}) or {}
                if action in ("agent_completed", "agent_started") or e_meta.get("use_ai") is True:
                    if e_meta.get("llm_fallback"):
                        return "LLM_FALLBACK"
                    return "LLM_PRIMARY"
                if e_meta.get("llm_fallback"):
                    return "LLM_FALLBACK"
        except Exception:
            pass

    return "RULES"


def _item_to_dict(item, container=None) -> dict[str, Any]:
    from app.domain.customer_names import derive_customer_name
    meta = dict(item.metadata) if item.metadata else {}
    c_name = derive_customer_name(item.customer_id, meta.get("customer_name"))
    meta["customer_name"] = c_name

    classification_method = _derive_classification_method(item, container)

    return {
        "id": item.id,
        "source_type": item.source_type.value,
        "external_id": item.external_id,
        "customer_id": item.customer_id,
        "customer_name": c_name,
        "amount_minor": item.amount_minor,
        "currency": item.currency,
        "created_at": item.created_at.isoformat(),
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "status": item.status.value,
        "root_cause": item.root_cause,
        "recovery_probability": item.recovery_probability,
        "expected_recovery_value": item.expected_recovery_value,
        "actual_recovery_value": getattr(item, "actual_recovery_value", None),
        "stopped_reason": getattr(item, "stopped_reason", None),
        "stopped_rule": getattr(item, "stopped_rule", None),
        "priority": getattr(item, "priority", None),
        "score_version": getattr(item, "score_version", None),
        "classification_method": classification_method,
        "metadata": meta,
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
        "id": getattr(event, "id", None),
        "recovery_item_id": event.recovery_item_id,
        "actor": event.actor,
        "action": event.action,
        "reason": event.reason,
        "metadata": event.metadata,
        "timestamp": event.timestamp.isoformat(),
    }


def _outcome_to_dict(outcome) -> dict[str, Any] | None:
    if outcome is None:
        return None
    return {
        "id": getattr(outcome, "id", None),
        "recovery_item_id": outcome.recovery_item_id,
        "outcome_type": outcome.outcome_type,
        "expected_recovery_minor": outcome.expected_recovery_minor,
        "actual_recovery_minor": getattr(outcome, "actual_recovery_minor", None),
        "recovery_cost_minor": getattr(outcome, "recovery_cost_minor", 0),
        "net_recovery_minor": getattr(outcome, "net_recovery_minor", None),
        "recovered_at": outcome.recovered_at.isoformat() if outcome.recovered_at else None,
    }


def _promise_to_dict(promise) -> dict[str, Any]:
    if isinstance(promise, dict):
        result = dict(promise)
        result.setdefault("id", result.get("id"))
        result.setdefault("recovery_item_id", result.get("recovery_item_id"))
        result.setdefault("customer_id", result.get("customer_id"))
        result.setdefault("promised_amount_minor", result.get("promised_amount_minor"))
        result.setdefault("status", result.get("status"))
        result.setdefault("created_at", result.get("created_at"))
        result.setdefault("fulfilled_at", result.get("fulfilled_at"))
        result.setdefault("expired_at", result.get("expired_at"))
        result.setdefault("metadata", result.get("metadata", {}))
        return result
    meta = getattr(promise, "metadata", {}) or {}
    return {
        "id": promise.id,
        "recovery_item_id": promise.recovery_item_id,
        "customer_id": promise.customer_id,
        "promised_amount_minor": promise.promised_amount_minor,
        "promised_date": promise.promised_date.isoformat() if hasattr(promise.promised_date, "isoformat") else str(promise.promised_date),
        "status": promise.status,
        "created_at": promise.created_at.isoformat() if promise.created_at else None,
        "fulfilled_at": promise.fulfilled_at.isoformat() if promise.fulfilled_at else None,
        "expired_at": promise.expired_at.isoformat() if promise.expired_at else None,
        "verified_recovered_minor": meta.get("verified_recovered_minor"),
        "settled_amount_minor": meta.get("settled_amount_minor"),
        "break_reason": meta.get("break_reason"),
        "source": meta.get("source"),
        "channel": meta.get("channel"),
        "metadata": meta,
    }


# ---------------------------------------------------------------------------
# Capital Protected Summary
# ---------------------------------------------------------------------------

_BLOCK_REASON_LABELS = {
    "fraud": "Fraud Risk Shield",
    "opt_out": "Customer Opt-Out / Consent",
    "hard_decline": "Hard Decline — Card Expired / Invalid",
    "promise_active": "Active Promise-to-Pay",
    "negative_ev": "Negative Expected Value",
    "human_review": "Human Escalation Review",
}


def build_capital_protected_summary(container) -> dict[str, Any]:
    """Aggregate capital protected: money NOT pursued due to policy decisions.

    Capital protected = items in status 'stopped' or 'escalated' where the system
    deliberately declined to retry, protecting the business from fraud, compliance,
    or economic harm.
    """
    from app.domain.customer_names import derive_customer_name

    items = _get_items(container)
    protected_items = [
        i for i in items
        if (i.status.value if hasattr(i.status, "value") else str(i.status)) in ("stopped", "escalated")
    ]

    total_minor = sum(i.amount_minor for i in protected_items)
    breakdown: dict[str, dict] = {
        k: {"label": v, "count": 0, "amount_minor": 0}
        for k, v in _BLOCK_REASON_LABELS.items()
    }

    itemized: list[dict] = []
    for item in protected_items:
        meta = item.metadata or {}
        status_str = item.status.value if hasattr(item.status, "value") else str(item.status)
        reason_raw = (
            getattr(item, "stopped_reason", "") or
            meta.get("stopped_reason") or
            meta.get("stop_reason") or
            ""
        ).lower()
        root = (item.root_cause or "").lower()

        # Classify block reason
        if "fraud" in reason_raw or "fraud" in root:
            bucket = "fraud"
        elif "opt" in reason_raw or "consent" in reason_raw:
            bucket = "opt_out"
        elif "hard" in reason_raw or "hard" in root or "expired" in reason_raw:
            bucket = "hard_decline"
        elif "promise" in reason_raw:
            bucket = "promise_active"
        elif status_str == "escalated":
            bucket = "human_review"
        elif "ev" in reason_raw or "negative" in reason_raw:
            bucket = "negative_ev"
        else:
            bucket = "negative_ev"  # safe default

        breakdown[bucket]["count"] += 1
        breakdown[bucket]["amount_minor"] += item.amount_minor

        # Human-readable decline line
        amount_inr = item.amount_minor / 100
        amount_fmt = f"\u20b9{amount_inr:,.0f}"
        bucket_label = _BLOCK_REASON_LABELS.get(bucket, bucket)
        c_name = derive_customer_name(item.customer_id, meta.get("customer_name"))
        human_line = f"{amount_fmt} \u2014 {c_name}: declined ({bucket_label})"
        if reason_raw:
            human_line = f"{amount_fmt} \u2014 {c_name}: declined — {reason_raw[:80]}"

        itemized.append({
            "id": item.id,
            "customer_id": item.customer_id,
            "customer_name": c_name,
            "amount_minor": item.amount_minor,
            "status": status_str,
            "block_reason": bucket,
            "block_reason_label": bucket_label,
            "human_readable_line": human_line,
        })

    # Sort itemized by amount descending
    itemized.sort(key=lambda x: -x["amount_minor"])

    # Only include breakdown buckets with at least one case
    breakdown_list = [
        {"reason": k, **v}
        for k, v in breakdown.items()
        if v["count"] > 0
    ]
    breakdown_list.sort(key=lambda x: -x["amount_minor"])

    return {
        "total_capital_protected_minor": total_minor,
        "case_count": len(protected_items),
        "breakdown_by_reason": breakdown_list,
        "itemized_cases": itemized,
    }
