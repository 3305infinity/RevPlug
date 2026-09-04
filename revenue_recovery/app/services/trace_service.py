"""Canonical Decision Trace and Auditability Service for RevPlug.

Provides complete end-to-end lifecycle reconstruction, context snapshot hashing,
AI vs Policy separation, candidate tracking, settlement evidence, and replay capabilities.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.audit.models import AuditEvent, EventType
from app.domain.context import RecoveryContext


def compute_context_hash(context: RecoveryContext | dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a sanitized recovery context."""
    if isinstance(context, RecoveryContext):
        d = {
            "item_id": context.item_id,
            "failure_category": context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category),
            "retryable": context.retryable,
            "attempt_count": context.attempt_count,
            "amount_minor": context.amount_minor,
            "currency": context.currency,
            "customer_opt_out": context.customer_opt_out,
            "failure_code": context.failure_code,
        }
    else:
        d = {k: str(v) for k, v in sorted(context.items()) if "secret" not in k.lower() and "key" not in k.lower()}

    serialized = json.dumps(d, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


@dataclass
class DecisionTrace:
    item_id: str
    status: str
    amount_at_risk_minor: int
    expected_recovery_minor: int
    verified_recovery_minor: int
    intervention_cost_minor: int
    net_recovery_minor: int
    context_snapshot: dict[str, Any]
    diagnosis: dict[str, Any]
    ai_recommendation: dict[str, Any]
    candidate_actions: list[dict[str, Any]]
    policy_evaluations: dict[str, Any]
    safety_decision: dict[str, Any]
    execution: dict[str, Any]
    settlement_evidence: dict[str, Any]
    timeline: list[dict[str, Any]]
    replay_summary: dict[str, Any]
    product_decision: dict[str, Any] = field(default_factory=dict)
    classification_method: str = "RULES"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_case_trace(item_id: str, container: Any) -> dict[str, Any]:
    """Build canonical decision trace from stored audit events & item state."""
    # 1. Fetch item if available
    item = None
    if hasattr(container, "recovery_items") and hasattr(container.recovery_items, "get"):
        item = container.recovery_items.get(item_id)

    # 2. Fetch events
    events: list[AuditEvent] = []
    if hasattr(container, "audit_log") and hasattr(container.audit_log, "events_for"):
        events = container.audit_log.events_for(item_id)

    amount_minor = 0
    if item and hasattr(item, "amount_minor"):
        try:
            amount_minor = int(item.amount_minor)
        except (TypeError, ValueError):
            amount_minor = 0
    currency = item.currency if item else "INR"
    status_str = item.status.value if item and hasattr(item.status, "value") else (str(item.status) if item else "UNKNOWN")

    # Trace variables
    context_snapshot: dict[str, Any] = {
        "version": 1,
        "hash": "",
        "item_id": item_id,
        "failure_category": item.root_cause if item else "unknown",
        "amount_minor": amount_minor,
    }
    diagnosis: dict[str, Any] = {}
    ai_recommendation: dict[str, Any] = {
        "actor": "ai",
        "source": "deterministic_fallback",
        "selected_action": None,
        "confidence": None,
        "fallback_used": False,
        "model": None,
        "prompt_version": None,
    }
    candidate_actions: list[dict[str, Any]] = []
    policy_evaluations: dict[str, Any] = {}
    safety_decision: dict[str, Any] = {"decision": "UNKNOWN", "allowed": False, "reason": "No evaluation recorded"}
    execution: dict[str, Any] = {"status": "NOT_EXECUTED", "executed": False}
    settlement_evidence: dict[str, Any] = {
        "verified": False,
        "verified_amount_minor": 0,
    }
    expected_recovery = 0
    verified_recovery = 0
    intervention_cost = 0
    classification_method = "RULES"

    timeline_dicts = []
    for ev in sorted(events, key=lambda x: getattr(x, "timestamp", datetime.now(timezone.utc))):
        m = ev.metadata or {}
        e_type = ev.event_type or m.get("event_type") or _map_action_to_event_type(ev.action)

        t_entry = {
            "id": ev.id,
            "event_type": e_type,
            "actor": ev.actor,
            "source": ev.source or m.get("source", "system"),
            "action": ev.action,
            "reason": ev.reason,
            "reason_code": ev.reason_code or m.get("reason_code", ""),
            "timestamp": ev.timestamp.isoformat() if hasattr(ev.timestamp, "isoformat") else str(ev.timestamp),
            "metadata": m,
        }
        timeline_dicts.append(t_entry)

        # Parse specific events
        if e_type in (EventType.CONTEXT_CAPTURED, "agent_context_created"):
            ctx_h = ev.context_hash or m.get("context_hash") or compute_context_hash(m)
            context_snapshot.update({
                "hash": ctx_h,
                "category": m.get("category") or m.get("failure_category"),
                "attempt_count": m.get("attempt_count", 0),
            })

        if e_type in (EventType.AI_RECOMMENDATION_CREATED, "agent_proposal_created"):
            act = m.get("action") or m.get("selected_action")
            model_name = m.get("model", "rules")
            # Determine classification method from model used
            if model_name and model_name not in ("mock", "rules", "deterministic"):
                classification_method = "LLM_PRIMARY"
            elif m.get("fallback_used"):
                classification_method = "LLM_FALLBACK"

            ai_recommendation.update({
                "actor": ev.actor,
                "source": ev.source or m.get("model", "llm"),
                "selected_action": act,
                "confidence": m.get("confidence", 0.8),
                "model": model_name,
                "prompt_version": m.get("prompt_version", "v1-stage3"),
                "fallback_used": bool(m.get("fallback_used", False)),
                "user_safe_reasoning": ev.reason or f"Recommended {act}",
                "evidence": m.get("evidence", []),
            })
            # Extract diagnosis from this event
            evidence_list = m.get("evidence", [])
            if isinstance(evidence_list, list):
                evidence_bullets = evidence_list
            else:
                evidence_bullets = []
            diagnosis.update({
                "root_cause": context_snapshot.get("failure_category") or item.root_cause if item else "unknown",
                "confidence": m.get("confidence", 0.0),
                "recommended_action": act,
                "rationale": ev.reason or "",
                "evidence": evidence_bullets,
                "diagnosis_source": "llm" if model_name not in ("mock", "rules", "deterministic") else "rules",
                "risk_level": m.get("risk_level", "medium"),
            })

        if e_type == EventType.CANDIDATES_GENERATED:
            cands = m.get("candidate_actions", [])
            if cands:
                candidate_actions = cands
            # Extract expected recovery from the selected candidate
            if not expected_recovery and cands:
                selected_act = ai_recommendation.get("selected_action")
                for c in cands:
                    if isinstance(c, dict):
                        net_ev = c.get("net_expected_recovery") or c.get("expected_recovery")
                        if c.get("action") == selected_act and net_ev:
                            try:
                                expected_recovery = int(net_ev)
                            except (TypeError, ValueError):
                                pass
                # If still no expected recovery, take from top non-blocked candidate
                if not expected_recovery:
                    for c in cands:
                        if isinstance(c, dict) and c.get("policy_status") != "BLOCKED":
                            net_ev = c.get("net_expected_recovery") or c.get("expected_recovery")
                            if net_ev:
                                try:
                                    expected_recovery = int(net_ev)
                                    break
                                except (TypeError, ValueError):
                                    pass

        if e_type in (EventType.POLICY_EVALUATED, EventType.SAFETY_EVALUATED, "policy_evaluate"):
            p_rule = ev.reason_code or m.get("policy_rule", "allow")
            p_allowed = bool(m.get("allowed", True))
            policy_evaluations = {
                "allowed": p_allowed,
                "policy_rule": p_rule,
                "reason_code": p_rule,
                "reason": ev.reason,
                "requires_human_approval": m.get("requires_human_approval", False),
            }
            safety_decision = {
                "decision": "ALLOWED" if p_allowed else "DENY",
                "allowed": p_allowed,
                "rule": p_rule,
                "reason_code": p_rule,
                "reason": ev.reason,
            }

        if e_type in (EventType.EXECUTION_STARTED, EventType.EXECUTION_ACCEPTED, "intervention_executed"):
            exec_cost = m.get("cost_minor")  # Never default — cost must come from backend
            exec_action = m.get("action") or ai_recommendation.get("selected_action")
            execution.update({
                "status": "EXECUTED",
                "executed": True,
                "action": exec_action,
                "dispatched_at": t_entry["timestamp"],
                "cost_minor": exec_cost,
            })
            if exec_cost is not None:
                intervention_cost = exec_cost

        if e_type in (EventType.SETTLEMENT_RECEIVED, EventType.RECOVERY_CONFIRMED, "settlement_verified", "outcome_verified"):
            verified_amt = m.get("actual_recovery_minor") or m.get("verified_amount_minor") or m.get("actual_recovered") or 0
            settlement_evidence.update({
                "verified": True,
                "verified_amount_minor": verified_amt,
                "method": m.get("verification_method", "webhook_hmac"),
                "provider": m.get("provider", "razorpay"),
                "provider_event_id": m.get("provider_event_id", ""),
                "payment_id": m.get("payment_id", ""),
                "is_simulated": bool(m.get("is_simulated", False)),
                "settlement_timestamp": t_entry["timestamp"],
                "correlation_id": ev.correlation_id or m.get("correlation_id", ""),
            })
            verified_recovery = verified_amt
            # If we still have no expected recovery, use verified as proxy (only for RECOVERED cases)
            if not expected_recovery and verified_recovery:
                expected_recovery = verified_recovery

        if e_type in (EventType.STOPPED, "stopping_rule_triggered"):
            safety_decision.update({
                "decision": "STOP",
                "allowed": False,
                "reason": ev.reason or "Stopped by rule",
                "reason_code": ev.reason_code or m.get("reason_code", "policy_stop"),
            })

        if e_type in (EventType.ESCALATED, "human_escalation_created"):
            safety_decision.update({
                "decision": "ESCALATE",
                "allowed": False,
                "reason": ev.reason or "Escalated for human review",
                "reason_code": ev.reason_code or m.get("reason_code", "escalation_required"),
            })

    # Also check item metadata for expected recovery if still missing
    if not expected_recovery and item:
        ev_from_item = getattr(item, "expected_recovery_value", None)
        if ev_from_item:
            try:
                expected_recovery = int(ev_from_item)
            except (TypeError, ValueError):
                pass

    if not context_snapshot["hash"]:
        context_snapshot["hash"] = compute_context_hash(context_snapshot)

    # Populate diagnosis fallback from item if empty
    if not diagnosis and item:
        diagnosis = {
            "root_cause": item.root_cause or "unknown",
            "confidence": 0.0,
            "recommended_action": ai_recommendation.get("selected_action"),
            "rationale": getattr(item, "stopped_reason", "") or "",
            "evidence": [],
            "diagnosis_source": "rules",
            "risk_level": "medium",
        }

    # --- Build canonical ProductDecision ---
    from app.domain.product_decision import resolve_decision
    action_for_decision = ai_recommendation.get("selected_action") or ""
    policy_state_for_decision = None
    if not safety_decision.get("allowed", True):
        rule = safety_decision.get("reason_code", "") or ""
        if "fraud" in rule.lower():
            policy_state_for_decision = "BLOCKED_FRAUD"
        elif "consent" in rule.lower() or "opt_out" in rule.lower():
            policy_state_for_decision = "BLOCKED_CONSENT"
        elif "dispute" in rule.lower():
            policy_state_for_decision = "HUMAN_REVIEW_DISPUTE"
        elif "systemic" in rule.lower():
            policy_state_for_decision = "SUPPRESSED_SYSTEMIC"

    # Map safety_decision.decision to policy_decision_type
    sd_decision = safety_decision.get("decision", "UNKNOWN")
    policy_decision_type = None
    if sd_decision == "ALLOWED":
        policy_decision_type = "ALLOWED"
    elif sd_decision in ("DENY", "STOP"):
        policy_decision_type = "DENY"
    elif sd_decision == "ESCALATE":
        policy_decision_type = "ESCALATE"

    prod_decision = resolve_decision(
        action=action_for_decision or None,
        policy_state=policy_state_for_decision,
        status=status_str,
        policy_decision_type=policy_decision_type,
        reason_code=safety_decision.get("reason_code", ""),
        reason=safety_decision.get("reason", "") or diagnosis.get("rationale", ""),
        requires_human_review=policy_evaluations.get("requires_human_approval", False),
        scheduled_for=None,
    )

    # Replay summary
    sel_action = ai_recommendation.get("selected_action") or "stop_recovery"
    pol_allowed = safety_decision.get("allowed", False)
    exec_status = execution.get("status", "NOT_EXECUTED")
    rec_verified = settlement_evidence.get("verified", False)

    replay_summary = {
        "what_happened": f"Case {item_id} processed. Status: {status_str}.",
        "what_system_knew": f"Category: {context_snapshot.get('category', 'unknown')}, Amount at risk: ₹{amount_minor / 100:.2f}.",
        "what_ai_inferred": f"AI recommended '{sel_action}' (confidence: {(ai_recommendation.get('confidence') or 0.0):.2f}).",
        "what_policy_allowed": f"Policy decision: {'ALLOWED' if pol_allowed else 'BLOCKED'} ({safety_decision.get('reason_code', 'N/A')}).",
        "what_executed": f"Execution status: {exec_status}.",
        "what_was_recovered": f"Verified recovered revenue: ₹{verified_recovery / 100:.2f} ({'Verified Settlement' if rec_verified else 'Unverified/Pending'}).",
    }

    net_recovery = verified_recovery - intervention_cost

    trace = DecisionTrace(
        item_id=item_id,
        status=status_str,
        amount_at_risk_minor=amount_minor,
        expected_recovery_minor=expected_recovery,
        verified_recovery_minor=verified_recovery,
        intervention_cost_minor=intervention_cost,
        net_recovery_minor=net_recovery,
        context_snapshot=context_snapshot,
        diagnosis=diagnosis,
        ai_recommendation=ai_recommendation,
        candidate_actions=candidate_actions,
        policy_evaluations=policy_evaluations,
        safety_decision=safety_decision,
        execution=execution,
        settlement_evidence=settlement_evidence,
        timeline=timeline_dicts,
        replay_summary=replay_summary,
        product_decision=prod_decision.to_dict(),
        classification_method=classification_method,
    )
    return trace.to_dict()


def _map_action_to_event_type(action: str) -> str:
    mapping = {
        "agent_context_created": EventType.CONTEXT_CAPTURED,
        "agent_proposal_created": EventType.AI_RECOMMENDATION_CREATED,
        "policy_evaluate": EventType.POLICY_EVALUATED,
        "intervention_executed": EventType.EXECUTION_ACCEPTED,
        "outcome_verified": EventType.RECOVERY_CONFIRMED,
        "settlement_verified": EventType.SETTLEMENT_RECEIVED,
        "stopping_rule_triggered": EventType.STOPPED,
        "human_escalation_created": EventType.ESCALATED,
        "fallback_triggered": EventType.FALLBACK_USED,
    }
    return mapping.get(action, action.upper())
