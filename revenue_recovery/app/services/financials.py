"""Canonical Recovery Financials Service for RevPlug.

Provides ONE single source of truth for all financial totals (at-risk, verified recovered, net recovered, intervention cost).
"""
from __future__ import annotations

from typing import Any
from app.db.container import PersistenceContainer


class RecoveryFinancialsService:
    """Calculates canonical financial metrics from persisted RecoveryItems and RecoveryOutcomes."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def get_canonical_financials(self) -> dict[str, Any]:
        """Calculates authoritative total_at_risk, verified_recovered, net_recovered, and intervention_cost."""
        from app.dashboard_api import _get_items, _actual_recovered_from_outcomes

        items = _get_items(self._container)
        total_at_risk = sum(i.amount_minor for i in items) if items else 0

        # Verified recovered comes strictly from outcomes + items in status RECOVERED
        verified_recovered = _actual_recovered_from_outcomes(self._container)

        intervention_cost = 0
        pending_verification = 0
        intentionally_stopped = 0
        stopped_breakdown = {
            "hard_decline": 0,
            "fraud": 0,
            "opt_out": 0,
            "promise_active": 0,
            "negative_ev": 0,
            "human_review": 0,
        }

        for item in items:
            status_str = item.status.value if hasattr(item.status, "value") else str(item.status)
            cost = getattr(item, "intervention_cost", 500) or 500
            if status_str in ("intervention_executed", "pending_verification"):
                pending_verification += item.amount_minor
                intervention_cost += cost
            elif status_str == "recovered":
                intervention_cost += cost
            elif status_str in ("stopped", "escalated"):
                intentionally_stopped += item.amount_minor
                reason = (getattr(item, "stopped_reason", "") or item.metadata.get("stopped_reason") or "").lower()
                root = (item.root_cause or "").lower()

                if "fraud" in reason or "fraud" in root:
                    stopped_breakdown["fraud"] += item.amount_minor
                elif "opt" in reason or "consent" in reason:
                    stopped_breakdown["opt_out"] += item.amount_minor
                elif "hard" in reason or "hard" in root:
                    stopped_breakdown["hard_decline"] += item.amount_minor
                elif "promise" in reason or "promise" in root:
                    stopped_breakdown["promise_active"] += item.amount_minor
                elif "ev" in reason or "negative" in reason or status_str == "escalated":
                    if status_str == "escalated":
                        stopped_breakdown["human_review"] += item.amount_minor
                    else:
                        stopped_breakdown["negative_ev"] += item.amount_minor
                else:
                    stopped_breakdown["negative_ev"] += item.amount_minor

        net_recovered = verified_recovered - intervention_cost
        recovery_rate_pct = round((verified_recovered / total_at_risk * 100.0), 1) if total_at_risk > 0 else 0.0

        return {
            "total_at_risk_minor": total_at_risk,
            "verified_recovered_minor": verified_recovered,
            "net_recovered_minor": net_recovered,
            "intervention_cost_minor": intervention_cost,
            "pending_verification_minor": pending_verification,
            "intentionally_stopped_minor": intentionally_stopped,
            "stopped_breakdown_minor": stopped_breakdown,
            "recovery_rate_pct": recovery_rate_pct,
            "total_cases_count": len(items),
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Calculates portfolio-level metrics matching requirement 11."""
        from app.dashboard_api import _get_items, _actual_recovered_from_outcomes

        items = _get_items(self._container)
        total_at_risk = sum(i.amount_minor for i in items)
        recovered = _actual_recovered_from_outcomes(self._container)

        actionable = 0
        waiting_policy = 0
        intentionally_not_pursued = 0
        available_net_ev = 0
        high_priority_count = 0

        for i in items:
            status_str = i.status.value if hasattr(i.status, "value") else str(i.status)
            meta = i.metadata or {}
            net_ev = meta.get("expected_net_ev_minor")
            if net_ev is None:
                net_ev = int((i.expected_recovery_value or i.amount_minor) - (i.intervention_cost or 500))

            if i.priority in ("CRITICAL", "HIGH"):
                high_priority_count += 1

            if status_str == "recovered":
                pass
            elif status_str in ("stopped", "escalated"):
                waiting_policy += i.amount_minor
            elif status_str == "waiting":
                waiting_policy += i.amount_minor
            elif meta.get("recommended_action") == "no_action" or net_ev <= 0:
                intentionally_not_pursued += i.amount_minor
            else:
                actionable += i.amount_minor
                if net_ev > 0:
                    available_net_ev += net_ev

        return {
            "total_revenue_at_risk_minor": total_at_risk,
            "actionable_revenue_minor": actionable,
            "revenue_waiting_policy_minor": waiting_policy,
            "revenue_recovered_minor": recovered,
            "revenue_intentionally_not_pursued_minor": intentionally_not_pursued,
            "available_expected_net_ev_minor": available_net_ev,
            "high_priority_opportunities_count": high_priority_count,
        }
