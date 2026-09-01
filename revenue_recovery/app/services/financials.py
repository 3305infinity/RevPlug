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
        from app.dashboard_api import _get_items

        items = _get_items(self._container)
        total_at_risk = sum(i.amount_minor for i in items) if items else 0

        # Calculate verified recovered strictly from items with RECOVERED status or RecoveryOutcome records
        verified_recovered = 0
        intervention_cost = 0

        for item in items:
            intervention_cost += getattr(item, "intervention_cost", 500) or 500
            if item.status == "recovered":
                verified_recovered += getattr(item, "actual_recovery_value", 0) or item.amount_minor
            elif getattr(item, "actual_recovery_value", 0):
                verified_recovered += getattr(item, "actual_recovery_value", 0)

        net_recovered = max(0, verified_recovered - intervention_cost)
        recovery_rate_pct = round((verified_recovered / total_at_risk * 100.0), 1) if total_at_risk > 0 else 0.0

        return {
            "total_at_risk_minor": total_at_risk,
            "verified_recovered_minor": verified_recovered,
            "net_recovered_minor": net_recovered,
            "intervention_cost_minor": intervention_cost,
            "recovery_rate_pct": recovery_rate_pct,
            "total_cases_count": len(items),
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Calculates portfolio-level metrics matching requirement 11."""
        from app.dashboard_api import _get_items

        items = _get_items(self._container)
        total_at_risk = sum(i.amount_minor for i in items)

        actionable = 0
        waiting_policy = 0
        recovered = 0
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
                recovered += getattr(i, "actual_recovery_value", 0) or i.amount_minor
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
