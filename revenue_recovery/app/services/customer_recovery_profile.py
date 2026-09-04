"""Customer 360 Recovery Profile Aggregator Service for RevPlug.

Aggregates customer lifetime economics, channel performance, contact fatigue,
open obligations, and payment history directly from authoritative ledgers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.container import PersistenceContainer
from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class ChannelPerformance:
    channel_name: str
    action_key: str
    total_attempts: int
    successful_recoveries: int
    success_rate_pct: float


@dataclass(frozen=True, slots=True)
class ContactFatigueStatus:
    contacts_today: int
    contacts_last_7d: int
    contacts_last_30d: int
    daily_limit: int = 2
    fatigue_risk: str = "LOW"  # LOW, MEDIUM, HIGH


@dataclass(frozen=True, slots=True)
class CurrentIssueSummary:
    item_id: str | None
    amount_minor: int
    root_cause: str
    failure_reason: str
    created_at: str | None
    recommended_action: str
    expected_net_recovery_minor: int


@dataclass(frozen=True, slots=True)
class Customer360RecoveryProfile:
    customer_id: str
    total_lifetime_revenue_minor: int
    current_amount_at_risk_minor: int
    current_expected_recovery_minor: int
    actually_recovered_lifetime_minor: int
    historical_recovery_rate: float
    total_cases_count: int
    failed_payments_count: int
    successful_recovery_count: int
    active_cases_count: int
    customer_value_tier: str  # HIGH, MEDIUM, LOW
    previous_opt_outs: bool
    current_subscription_state: str  # Active, Overdue, Disputed
    payment_methods_used: list[str]
    previous_recovery_actions: list[str]
    channel_performance: list[dict[str, Any]]
    contact_fatigue: dict[str, Any]
    current_issue: dict[str, Any] | None
    outstanding_invoices: list[dict[str, Any]]
    promise_to_pay_history: list[dict[str, Any]]
    recovery_history_timeline: list[dict[str, Any]]
    last_successful_payment_at: str | None
    last_failed_payment_at: str | None
    last_failed_reason: str | None
    # New fields
    customer_decision: str | None
    customer_decision_reason: str | None
    active_opportunities: list[dict[str, Any]]
    intervention_outcomes: list[dict[str, Any]]
    policy_constraints: list[str]
    active_incident_ids: list[str]
    active_incident_count: int
    recovery_pressure_summary: str
    why_this_matters: str
    recovery_status: str = "No Active Exposure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "total_lifetime_revenue_minor": self.total_lifetime_revenue_minor,
            "current_amount_at_risk_minor": self.current_amount_at_risk_minor,
            "current_expected_recovery_minor": self.current_expected_recovery_minor,
            "actually_recovered_lifetime_minor": self.actually_recovered_lifetime_minor,
            "historical_recovery_rate": self.historical_recovery_rate,
            "total_cases_count": self.total_cases_count,
            "failed_payments_count": self.failed_payments_count,
            "successful_recovery_count": self.successful_recovery_count,
            "active_cases_count": self.active_cases_count,
            "customer_value_tier": self.customer_value_tier,
            "previous_opt_outs": self.previous_opt_outs,
            "current_subscription_state": self.current_subscription_state,
            "recovery_status": self.recovery_status,
            "payment_methods_used": self.payment_methods_used,
            "previous_recovery_actions": self.previous_recovery_actions,
            "channel_performance": self.channel_performance,
            "contact_fatigue": self.contact_fatigue,
            "current_issue": self.current_issue,
            "outstanding_invoices": self.outstanding_invoices,
            "promise_to_pay_history": self.promise_to_pay_history,
            "recovery_history_timeline": self.recovery_history_timeline,
            "last_successful_payment_at": self.last_successful_payment_at,
            "last_failed_payment_at": self.last_failed_payment_at,
            "last_failed_reason": self.last_failed_reason,
            "customer_decision": self.customer_decision,
            "customer_decision_reason": self.customer_decision_reason,
            "active_opportunities": self.active_opportunities,
            "intervention_outcomes": self.intervention_outcomes,
            "policy_constraints": self.policy_constraints,
            "active_incident_ids": self.active_incident_ids,
            "active_incident_count": self.active_incident_count,
            "recovery_pressure_summary": self.recovery_pressure_summary,
            "why_this_matters": self.why_this_matters,
        }


class CustomerRecoveryProfileService:
    """Service that builds rich Customer 360 profile from single source of truth repositories."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def get_profile(self, customer_id: str) -> Customer360RecoveryProfile:
        from app.dashboard_api import _get_items, _get_attempts, _get_audit_events, _actual_recovered_from_outcomes, _item_to_dict, _ACTIVE_STATUSES

        all_items = _get_items(self._container)
        items = [i for i in all_items if i.customer_id == customer_id]
        item_ids = {i.id for i in items}

        total_lifetime = sum(i.amount_minor for i in items)
        active_items = [i for i in items if i.status.value in _ACTIVE_STATUSES]
        at_risk = sum(i.amount_minor for i in active_items)

        recovered_items = [i for i in items if i.status.value == "recovered"]
        actually_recovered = _actual_recovered_from_outcomes(self._container, item_ids)
        recovery_rate = round(actually_recovered / total_lifetime, 4) if total_lifetime > 0 else 0.0

        # Customer Value Tier
        if total_lifetime >= 2000000 or actually_recovered >= 1000000:
            value_tier = "HIGH"
        elif total_lifetime >= 500000:
            value_tier = "MEDIUM"
        else:
            value_tier = "LOW"

        # Opt-out & Payment methods
        has_opt_out = any(i.metadata.get("opted_out") for i in items)
        methods = list({str(i.metadata.get("method") or "card").lower() for i in items}) or ["card"]

        # Attempts & Actions
        attempts = []
        if hasattr(self._container.attempts, "attempts_for"):
            for i in items:
                attempts.extend(self._container.attempts.attempts_for(i.id))
        elif hasattr(self._container.attempts, "_records"):
            attempts = [a for a in self._container.attempts._records if a.recovery_item_id in item_ids]

        prev_actions = list({a.action for a in attempts if hasattr(a, "action")})

        # Channel Performance Calculation
        action_stats: dict[str, dict[str, int]] = {
            "send_payment_link": {"total": 0, "success": 0},
            "retry_payment": {"total": 0, "success": 0},
            "send_reminder": {"total": 0, "success": 0},
            "alternate_channel": {"total": 0, "success": 0},
        }

        for a in attempts:
            act = getattr(a, "action", "retry_payment")
            if act not in action_stats:
                action_stats[act] = {"total": 0, "success": 0}
            action_stats[act]["total"] += 1
            if getattr(a, "outcome", "") in ("success", "recovered"):
                action_stats[act]["success"] += 1

        channel_perf = [
            {
                "channel_name": "Payment Link",
                "action_key": "send_payment_link",
                "total_attempts": action_stats["send_payment_link"]["total"],
                "success_rate_pct": round(action_stats["send_payment_link"]["success"] / action_stats["send_payment_link"]["total"] * 100, 1) if action_stats["send_payment_link"]["total"] > 0 else 0.0,
            },
            {
                "channel_name": "Auto Retry",
                "action_key": "retry_payment",
                "total_attempts": action_stats["retry_payment"]["total"],
                "success_rate_pct": round(action_stats["retry_payment"]["success"] / action_stats["retry_payment"]["total"] * 100, 1) if action_stats["retry_payment"]["total"] > 0 else 0.0,
            },
            {
                "channel_name": "Email / SMS",
                "action_key": "send_reminder",
                "total_attempts": action_stats["send_reminder"]["total"],
                "success_rate_pct": round(action_stats["send_reminder"]["success"] / action_stats["send_reminder"]["total"] * 100, 1) if action_stats["send_reminder"]["total"] > 0 else 0.0,
            },
            {
                "channel_name": "Voice / Chat",
                "action_key": "alternate_channel",
                "total_attempts": action_stats["alternate_channel"]["total"],
                "success_rate_pct": round(action_stats["alternate_channel"]["success"] / action_stats["alternate_channel"]["total"] * 100, 1) if action_stats["alternate_channel"]["total"] > 0 else 0.0,
            },
        ]

        # Contact Frequency & Fatigue
        now = datetime.now(timezone.utc)
        t_24h = now - timedelta(days=1)
        t_7d = now - timedelta(days=7)
        t_30d = now - timedelta(days=30)

        outbound_events = []
        for i in items:
            for e in _get_audit_events(self._container, i.id):
                act = getattr(e, "action", "")
                if "execution" in act or "reminder" in act or "link" in act or "message" in act:
                    outbound_events.append(e)

        contacts_24h = sum(1 for e in outbound_events if e.timestamp and (e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=timezone.utc)) >= t_24h)
        contacts_7d = sum(1 for e in outbound_events if e.timestamp and (e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=timezone.utc)) >= t_7d)
        contacts_30d = sum(1 for e in outbound_events if e.timestamp and (e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=timezone.utc)) >= t_30d)

        fatigue_risk = "HIGH" if contacts_24h >= 2 else "MEDIUM" if contacts_24h == 1 else "LOW"

        contact_fatigue = {
            "contacts_today": contacts_24h,
            "contacts_last_7d": contacts_7d,
            "contacts_last_30d": contacts_30d,
            "daily_limit": 2,
            "fatigue_risk": fatigue_risk,
        }

        # Current Issue Summary
        current_issue = None
        if active_items:
            latest = sorted(active_items, key=lambda x: x.created_at or now, reverse=True)[0]
            cat = latest.root_cause or "payment_failure"
            ev_val = latest.expected_recovery_value or int(latest.amount_minor * 0.85)
            rec_act = str(latest.metadata.get("proposed_action") or latest.metadata.get("action") or ("send_payment_link" if "auth" in cat or "hard" in cat else "retry_payment"))
            current_issue = {
                "item_id": latest.id,
                "amount_minor": latest.amount_minor,
                "root_cause": cat,
                "failure_reason": str(latest.metadata.get("error_description") or latest.root_cause or "Payment authorization failure"),
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
                "recommended_action": rec_act,
                "expected_net_recovery_minor": ev_val - 500,
            }

        # Outstanding Invoices
        outstanding = [_item_to_dict(i) for i in active_items]

        # Promises
        promises = []
        if hasattr(self._container, "promises") and self._container.promises is not None:
            for i in items:
                p = self._container.promises.get_for_item(i.id)
                if p:
                    promises.append({
                        "id": getattr(p, "id", f"p_{i.id}"),
                        "item_id": i.id,
                        "amount_minor": getattr(p, "promised_amount_minor", i.amount_minor),
                        "promised_date": getattr(p, "promised_date", None),
                        "status": getattr(p, "status", "promised"),
                    })

        # Recovery Timeline
        timeline = []
        for i in items:
            for e in _get_audit_events(self._container, i.id):
                timeline.append({
                    "id": getattr(e, "id", f"evt_{i.id}"),
                    "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                    "item_id": i.id,
                    "action": e.action,
                    "reason": e.reason or "",
                    "amount_recovered_minor": i.amount_minor if "success" in e.action or "recovered" in e.action else 0,
                })
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)

        # Dates & Last Failed Event (Rule 6: Last Failed shows latest failed event even if case is now terminal)
        sorted_items = sorted(items, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        latest_item = sorted_items[0] if sorted_items else None

        rec_dates = [i.created_at for i in recovered_items if i.created_at]
        last_succ = sorted(rec_dates, reverse=True)[0].isoformat() if rec_dates else None
        last_failed = latest_item.created_at.isoformat() if latest_item and latest_item.created_at else None
        last_reason = latest_item.root_cause if latest_item else None

        # Subscription State
        sub_state = "Disputed" if any(i.metadata.get("disputed") for i in items) else ("Overdue" if active_items else "Active")

        # Recovery Status: Rule 1 — If no open opportunities, do not label customer as actively under recovery pressure
        if active_items:
            if any(i.status.value in {"pending_verification", "intervention_executed"} for i in active_items):
                recovery_status = "Awaiting Verification"
            elif any(i.status.value == "escalated" for i in active_items):
                recovery_status = "Escalated for Review"
            else:
                recovery_status = "Active Exposure"
        elif items:
            if len(recovered_items) == len(items):
                recovery_status = "Settled & Clear"
            else:
                recovery_status = "No Active Exposure"
        else:
            recovery_status = "No Active Exposure"

        # --- New: Customer-level decision ---
        from app.domain.product_decision import resolve_decision
        customer_decision = None
        customer_decision_reason = None
        if active_items:
            # Derive customer-level posture from most common decision across active items
            decision_counts: dict[str, int] = {}
            for ai in active_items:
                meta = ai.metadata if isinstance(ai.metadata, dict) else {}
                pd = resolve_decision(
                    action=meta.get("recommended_action", "wait"),
                    policy_state=meta.get("policy_state"),
                    status=ai.status.value if hasattr(ai.status, "value") else str(ai.status),
                    reason_code=meta.get("reason_code", ""),
                    reason=meta.get("reason", ""),
                )
                decision_counts[pd.decision] = decision_counts.get(pd.decision, 0) + 1
            if decision_counts:
                customer_decision = max(decision_counts, key=decision_counts.get)
                customer_decision_reason = f"Derived from {len(active_items)} active opportunity decisions"

        # --- New: Active opportunities with decisions ---
        active_opps = []
        for ai in active_items:
            meta = ai.metadata if isinstance(ai.metadata, dict) else {}
            pd = resolve_decision(
                action=meta.get("recommended_action", "wait"),
                policy_state=meta.get("policy_state"),
                status=ai.status.value if hasattr(ai.status, "value") else str(ai.status),
                reason_code=meta.get("reason_code", ""),
                reason=meta.get("reason", ""),
            )
            active_opps.append({
                "item_id": ai.id,
                "amount_minor": ai.amount_minor,
                "expected_recovery_minor": ai.expected_recovery_value or 0,
                "decision": pd.decision,
                "selected_action": meta.get("recommended_action"),
                "policy_state": meta.get("policy_state", ""),
                "execution_status": ai.status.value if hasattr(ai.status, "value") else str(ai.status),
                "root_cause": ai.root_cause,
                "incident_affected": meta.get("systemic_suppress", False) or meta.get("policy_state") == "SUPPRESSED_SYSTEMIC",
            })

        # --- New: Intervention outcomes ---
        intervention_outcomes = []
        for action_key, stats in action_stats.items():
            if stats["total"] > 0:
                intervention_outcomes.append({
                    "intervention": action_key,
                    "attempts": stats["total"],
                    "successful": stats["success"],
                    "success_rate_pct": round(stats["success"] / stats["total"] * 100, 1),
                })

        # --- New: Policy constraints ---
        policy_constraints: list[str] = []
        if has_opt_out:
            policy_constraints.append("Customer has opted out — contact blocked by policy")
        if contacts_24h >= 2:
            policy_constraints.append(f"Contact frequency limit reached ({contacts_24h}/2 today)")
        if any(i.metadata.get("policy_state") == "SUPPRESSED_SYSTEMIC" for i in items):
            policy_constraints.append("Some opportunities suppressed by active systemic incident")
        if any(i.metadata.get("fraud_risk") for i in items):
            policy_constraints.append("Fraud risk flag active — recovery blocked")
        if any(i.metadata.get("disputed") for i in items):
            policy_constraints.append("Invoice disputed — requires human review")

        # --- New: Active incident IDs ---
        from app.services.revenue_incident_manager import RevenueIncidentManager
        incident_mgr = RevenueIncidentManager(self._container)
        active_incidents = incident_mgr.detect_incidents()
        customer_incident_ids = []
        for inc in active_incidents:
            if any(iid in inc.affected_opportunity_ids for iid in item_ids):
                customer_incident_ids.append(inc.incident_id)

        # --- New: Recovery pressure summary ---
        pressure_parts = []
        if contacts_24h > 0:
            pressure_parts.append(f"{contacts_24h} contact(s) today")
        if contacts_7d > 0:
            pressure_parts.append(f"{contacts_7d} this week")
        if prev_actions and active_items:
            pressure_parts.append(f"actions tried: {', '.join(prev_actions[:3])}")
        recovery_pressure_summary = "; ".join(pressure_parts) if pressure_parts else "No recent recovery pressure"

        # --- New: Expected recovery total ---
        expected_recovery_total = sum(ai.expected_recovery_value or 0 for ai in active_items)

        # --- New: Why this matters now ---
        why_parts = []
        if at_risk > 0:
            why_parts.append(f"₹{at_risk / 100:,.0f} at risk across {len(active_items)} open opportunity")
        if customer_incident_ids:
            why_parts.append(f"affected by {len(customer_incident_ids)} active incident(s)")
        if contacts_24h >= 2:
            why_parts.append("contact frequency threshold reached")
        if active_items and any(i.expected_recovery_value and i.expected_recovery_value > 0 for i in active_items):
            best = max(active_items, key=lambda x: x.expected_recovery_value or 0)
            why_parts.append(f"best opportunity: ₹{(best.expected_recovery_value or 0) / 100:,.0f} expected recovery")
        why_this_matters = "; ".join(why_parts) if why_parts else "No active recovery concerns"

        return Customer360RecoveryProfile(
            customer_id=customer_id,
            total_lifetime_revenue_minor=total_lifetime,
            current_amount_at_risk_minor=at_risk,
            current_expected_recovery_minor=expected_recovery_total,
            actually_recovered_lifetime_minor=actually_recovered,
            historical_recovery_rate=recovery_rate,
            total_cases_count=len(items),
            failed_payments_count=len(items) - len(recovered_items),
            successful_recovery_count=len(recovered_items),
            active_cases_count=len(active_items),
            customer_value_tier=value_tier,
            previous_opt_outs=has_opt_out,
            current_subscription_state=sub_state,
            recovery_status=recovery_status,
            payment_methods_used=methods,
            previous_recovery_actions=prev_actions,
            channel_performance=channel_perf,
            contact_fatigue=contact_fatigue,
            current_issue=current_issue,
            outstanding_invoices=outstanding,
            promise_to_pay_history=promises,
            recovery_history_timeline=timeline[:30],
            last_successful_payment_at=last_succ,
            last_failed_payment_at=last_failed,
            last_failed_reason=last_reason,
            customer_decision=customer_decision,
            customer_decision_reason=customer_decision_reason,
            active_opportunities=active_opps,
            intervention_outcomes=intervention_outcomes,
            policy_constraints=policy_constraints,
            active_incident_ids=customer_incident_ids,
            active_incident_count=len(customer_incident_ids),
            recovery_pressure_summary=recovery_pressure_summary,
            why_this_matters=why_this_matters,
        )
