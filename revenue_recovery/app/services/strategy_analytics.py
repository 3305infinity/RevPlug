"""Recovery Strategy Analytics Service for RevPlug.

Groups historical completed outcomes by failure category, payment method, intervention,
and channel to generate inspectable strategy performance tables and automated opportunity signals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.db.container import PersistenceContainer


@dataclass(frozen=True, slots=True)
class StrategyPerformanceRow:
    action: str
    label: str
    attempts_count: int
    recovered_amount_minor: int
    success_rate_pct: float
    average_cost_minor: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "label": self.label,
            "attempts_count": self.attempts_count,
            "recovered_amount_minor": self.recovered_amount_minor,
            "success_rate_pct": round(self.success_rate_pct, 1),
            "average_cost_minor": self.average_cost_minor,
        }


@dataclass(frozen=True, slots=True)
class StrategyAnalyticsReport:
    total_historical_cases: int
    strategies: list[dict[str, Any]]
    opportunity_signals: list[str]
    financial_kpis: dict[str, Any] = field(default_factory=dict)
    calibration_metrics: dict[str, Any] = field(default_factory=dict)
    revenue_lost_reasons: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_historical_cases": self.total_historical_cases,
            "strategies": self.strategies,
            "opportunity_signals": self.opportunity_signals,
            "financial_kpis": self.financial_kpis,
            "calibration_metrics": self.calibration_metrics,
            "revenue_lost_reasons": self.revenue_lost_reasons,
            "generated_at": self.generated_at,
        }


class StrategyAnalyticsService:
    """Aggregates completed outcomes into strategy performance metrics."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def generate_report(self) -> StrategyAnalyticsReport:
        from app.dashboard_api import _get_items, _get_attempts, _get_decisions, _actual_recovered_from_outcomes

        items = _get_items(self._container)
        total_cases = len(items)

        if total_cases == 0:
            return StrategyAnalyticsReport(
                total_historical_cases=0,
                strategies=[],
                opportunity_signals=[],
                financial_kpis={
                    "total_revenue_at_risk_minor": 0,
                    "revenue_recovered_minor": 0,
                    "net_revenue_recovered_minor": 0,
                    "recovery_rate_pct": 0.0,
                    "average_recovery_per_case_minor": 0,
                    "intervention_cost_minor": 0,
                    "cost_per_recovered_rupee": 0.0,
                },
                calibration_metrics={
                    "mean_absolute_error_pct": 0.0,
                    "calibration_ratio": 0.0,
                    "brier_score": 0.0,
                    "prediction_vs_reality_samples": [],
                },
                revenue_lost_reasons=[],
            )

        # Compute aggregate financial metrics from persisted records
        total_risk = sum(i.amount_minor for i in items)
        recovered = _actual_recovered_from_outcomes(self._container)
        cost = sum(getattr(i, "intervention_cost", 0) or 0 for i in items)
        net_recovered = max(0, recovered - cost)
        rec_rate = (recovered / total_risk * 100.0) if total_risk > 0 else 0.0
        recovered_count = len([i for i in items if (hasattr(i.status, "value") and i.status.value == "recovered") or str(getattr(i, "status", "")) == "recovered"])
        avg_recovery = int(recovered / max(1, recovered_count)) if recovered_count > 0 else 0
        cost_per_rupee = round(cost / recovered, 2) if recovered > 0 else 0.0

        financial_kpis = {
            "total_revenue_at_risk_minor": total_risk,
            "revenue_recovered_minor": recovered,
            "net_revenue_recovered_minor": net_recovered,
            "recovery_rate_pct": round(rec_rate, 1),
            "average_recovery_per_case_minor": avg_recovery,
            "intervention_cost_minor": cost,
            "cost_per_recovered_rupee": cost_per_rupee,
        }

        # Calibration metrics from actual decisions vs outcomes
        decisions = _get_decisions(self._container)
        samples = []
        for i in items:
            item_status = i.status.value if hasattr(i.status, "value") else str(i.status)
            item_decs = [d for d in decisions if (d.get("recovery_item_id") if isinstance(d, dict) else getattr(d, "recovery_item_id", None)) == i.id]
            if item_decs:
                latest_dec = item_decs[-1]
                dec_action = latest_dec.get("proposed_action") if isinstance(latest_dec, dict) else getattr(latest_dec, "proposed_action", "unknown")
                exp_val = getattr(i, "expected_recovery_value", 0) or 0
                act_val = getattr(i, "actual_recovery_value", 0) or (i.amount_minor if item_status == "recovered" else 0)
                err_pct = round(abs(exp_val - act_val) / max(1, exp_val) * 100.0, 1) if exp_val > 0 else 0.0
                samples.append({
                    "case_id": i.id,
                    "action": dec_action,
                    "expected_recovery_minor": exp_val,
                    "actual_recovery_minor": act_val,
                    "prediction_error_pct": err_pct,
                    "outcome": item_status,
                })

        calibration_metrics = {
            "mean_absolute_error_pct": round(sum(s["prediction_error_pct"] for s in samples) / max(1, len(samples)), 1) if samples else None,
            "calibration_ratio": round(sum(s["actual_recovery_minor"] for s in samples) / max(1, sum(s["expected_recovery_minor"] for s in samples)), 2) if samples and sum(s["expected_recovery_minor"] for s in samples) > 0 else None,
            "brier_score": None,
            "prediction_vs_reality_samples": samples[:10],
        }
        # Brier score requires probability predictions paired with binary outcomes.
        # Not computed here because the current EV model outputs expected values, not probabilities.
        # Return null rather than invent a value.

        # Revenue Lost Reasons Breakdown from non-recovered items
        unrecovered_items = [i for i in items if (i.status.value if hasattr(i.status, "value") else str(i.status)) in ("stopped", "failed", "escalated")]
        reasons_map: dict[str, dict[str, Any]] = {}
        for ui in unrecovered_items:
            cat = ui.root_cause or "unclassified"
            if cat not in reasons_map:
                reasons_map[cat] = {
                    "reason_code": cat,
                    "reason_label": cat.replace("_", " ").title(),
                    "lost_amount_minor": 0,
                    "cases_count": 0,
                    "actionable_recommendation": f"Inspect policy rules for {cat.replace('_', ' ')}",
                }
            reasons_map[cat]["lost_amount_minor"] += ui.amount_minor
            reasons_map[cat]["cases_count"] += 1

        revenue_lost_reasons = list(reasons_map.values())

        # Strategy performance breakdown from attempts
        attempts = _get_attempts(self._container)
        strategy_stats: dict[str, dict[str, Any]] = {
            "send_payment_link": {"label": "Payment Link (UPI/Card)", "attempts": 0, "recovered": 0, "successes": 0, "cost": 0},
            "retry_payment": {"label": "Auto Retry", "attempts": 0, "recovered": 0, "successes": 0, "cost": 0},
            "send_reminder": {"label": "Email / SMS Reminder", "attempts": 0, "recovered": 0, "successes": 0, "cost": 0},
            "alternate_channel": {"label": "Voice / WhatsApp Channel", "attempts": 0, "recovered": 0, "successes": 0, "cost": 0},
        }

        item_status_map = {i.id: (i.status.value if hasattr(i.status, "value") else str(i.status)) for i in items}
        item_amt_map = {i.id: i.amount_minor for i in items}

        for a in attempts:
            act = getattr(a, "action", "") if hasattr(a, "action") else a.get("action", "")
            item_id = getattr(a, "recovery_item_id", "") if hasattr(a, "recovery_item_id") else a.get("recovery_item_id", "")
            if act in strategy_stats:
                strategy_stats[act]["attempts"] += 1
                strategy_stats[act]["cost"] += getattr(a, "cost_minor", 0) or 500
                if item_status_map.get(item_id) == "recovered" or getattr(a, "outcome", "") in ("success", "recovered"):
                    strategy_stats[act]["successes"] += 1
                    strategy_stats[act]["recovered"] += item_amt_map.get(item_id, 0)

        strategies = []
        for act_key, stat in strategy_stats.items():
            if stat["attempts"] > 0:
                strategies.append(
                    StrategyPerformanceRow(
                        action=act_key,
                        label=stat["label"],
                        attempts_count=stat["attempts"],
                        recovered_amount_minor=stat["recovered"],
                        success_rate_pct=round((stat["successes"] / stat["attempts"]) * 100.0, 1),
                        average_cost_minor=int(stat["cost"] / stat["attempts"]),
                    ).to_dict()
                )

        signals = []
        if strategies:
            best_strat = max(strategies, key=lambda s: s["success_rate_pct"])
            signals.append(f"Top performing strategy: {best_strat['label']} with {best_strat['success_rate_pct']}% success rate across {best_strat['attempts_count']} attempts.")

        return StrategyAnalyticsReport(
            total_historical_cases=total_cases,
            strategies=strategies,
            opportunity_signals=signals,
            financial_kpis=financial_kpis,
            calibration_metrics=calibration_metrics,
            revenue_lost_reasons=revenue_lost_reasons,
        )

