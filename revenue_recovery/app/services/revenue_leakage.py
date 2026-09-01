"""Revenue Leakage Analytics Service for RevPlug.

Aggregates unrecovered revenue by failure category, provider, method, and policy guard,
answering "WHERE IS MY MONEY LEAKING?" and "WHAT SHOULD I CHANGE TO STOP THE LEAK?".
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.db.container import PersistenceContainer


@dataclass(frozen=True, slots=True)
class LeakageCategoryRow:
    category_id: str
    category_label: str
    amount_at_risk_minor: int
    recoverable_estimate_minor: int
    actual_recovered_minor: int
    unrecovered_minor: int
    recovery_rate_pct: float
    recommended_policy_change: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_id,
            "category_label": self.category_label,
            "amount_at_risk_minor": self.amount_at_risk_minor,
            "recoverable_estimate_minor": self.recoverable_estimate_minor,
            "actual_recovered_minor": self.actual_recovered_minor,
            "unrecovered_minor": self.unrecovered_minor,
            "recovery_rate_pct": round(self.recovery_rate_pct, 1),
            "recommended_policy_change": self.recommended_policy_change,
        }


@dataclass(frozen=True, slots=True)
class RevenueLeakageReport:
    total_revenue_at_risk_minor: int
    total_unrecovered_minor: int
    categories: list[dict[str, Any]]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_revenue_at_risk_minor": self.total_revenue_at_risk_minor,
            "total_unrecovered_minor": self.total_unrecovered_minor,
            "categories": self.categories,
            "generated_at": self.generated_at,
        }


class RevenueLeakageAnalytics:
    """Aggregates revenue leakage across categories and generates policy change recommendations."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def generate_report(self) -> RevenueLeakageReport:
        from app.dashboard_api import _get_items

        items = _get_items(self._container)
        total_risk = sum(i.amount_minor for i in items)

        if not items:
            return RevenueLeakageReport(
                total_revenue_at_risk_minor=0,
                total_unrecovered_minor=0,
                categories=[],
            )

        cat_groups: dict[str, dict[str, Any]] = {}
        for i in items:
            cat_id = (i.root_cause or "unclassified").lower()
            if cat_id not in cat_groups:
                cat_groups[cat_id] = {
                    "category_id": cat_id,
                    "category_label": cat_id.replace("_", " ").title(),
                    "amount_at_risk_minor": 0,
                    "recoverable_estimate_minor": 0,
                    "actual_recovered_minor": 0,
                    "unrecovered_minor": 0,
                    "recovery_rate_pct": 0.0,
                    "recommended_policy_change": f"Evaluate recovery workflow rules for {cat_id.replace('_', ' ')}",
                }

            status_str = i.status.value if hasattr(i.status, "value") else str(i.status)
            amt = i.amount_minor
            cat_groups[cat_id]["amount_at_risk_minor"] += amt
            exp_val = getattr(i, "expected_recovery_value", 0) or int(amt * 0.7)
            cat_groups[cat_id]["recoverable_estimate_minor"] += exp_val

            if status_str == "recovered":
                rec_val = getattr(i, "actual_recovery_value", 0) or amt
                cat_groups[cat_id]["actual_recovered_minor"] += rec_val
            elif status_str in ("stopped", "failed", "escalated"):
                cat_groups[cat_id]["unrecovered_minor"] += amt

        categories = []
        for g in cat_groups.values():
            risk = g["amount_at_risk_minor"]
            rec = g["actual_recovered_minor"]
            g["recovery_rate_pct"] = round((rec / risk * 100.0), 1) if risk > 0 else 0.0
            categories.append(
                LeakageCategoryRow(
                    category_id=g["category_id"],
                    category_label=g["category_label"],
                    amount_at_risk_minor=g["amount_at_risk_minor"],
                    recoverable_estimate_minor=g["recoverable_estimate_minor"],
                    actual_recovered_minor=g["actual_recovered_minor"],
                    unrecovered_minor=g["unrecovered_minor"],
                    recovery_rate_pct=g["recovery_rate_pct"],
                    recommended_policy_change=g["recommended_policy_change"],
                ).to_dict()
            )

        total_unrecovered = sum(c["unrecovered_minor"] for c in categories)

        return RevenueLeakageReport(
            total_revenue_at_risk_minor=total_risk,
            total_unrecovered_minor=total_unrecovered,
            categories=categories,
        )

