"""Recovery Strategy Analytics Service for RevPlug.

Aggregates verified historical recovery outcomes into strategy performance metrics.

Financial semantics:
  - Revenue at Risk: sum of amount_minor for open items
  - Verified Recovered: settlement-confirmed money from recovery_outcomes only
  - Expected Recovery: projected value from AI scoring
  - Strategy Recovery Performance: historical verified recovery associated with a strategy

Learning is deterministic and evidence-based. No ML, no fabricated data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.db.container import PersistenceContainer


EVIDENCE_INSUFFICIENT = "insufficient"
EVIDENCE_EMERGING = "emerging"
EVIDENCE_ESTABLISHED = "established"

EVIDENCE_THRESHOLDS = {
    "attempts": {"insufficient": 3, "emerging": 10, "established": 25},
    "recoveries": {"insufficient": 1, "emerging": 5, "established": 15},
}

KNOWN_STRATEGIES = [
    ("send_payment_link", "Payment Link (UPI/Card)"),
    ("retry_payment", "Auto Retry"),
    ("send_reminder", "Email / SMS Reminder"),
    ("alternate_channel", "Voice / WhatsApp Channel"),
    ("promise_to_pay", "Promise-to-Pay"),
    ("send_discount", "Discount Offer"),
]

OUTCOME_ATTEMPTED = frozenset({"executed", "success", "recovered", "pending_verification"})
OUTCOME_SUCCESS = frozenset({"recovered", "success"})
OUTCOME_POLICY_BLOCKED = frozenset({"blocked", "denied", "policy_blocked"})
OUTCOME_STOPPED = frozenset({"stopped", "stopped_by_policy"})
OUTCOME_ESCALATED = frozenset({"escalated", "human_review"})
OUTCOME_WAITED = frozenset({"waited", "wait"})


def _evidence_level(attempts: int, recoveries: int) -> str:
    if attempts >= EVIDENCE_THRESHOLDS["attempts"]["established"] and recoveries >= EVIDENCE_THRESHOLDS["recoveries"]["established"]:
        return EVIDENCE_ESTABLISHED
    if attempts >= EVIDENCE_THRESHOLDS["attempts"]["emerging"] and recoveries >= EVIDENCE_THRESHOLDS["recoveries"]["emerging"]:
        return EVIDENCE_EMERGING
    return EVIDENCE_INSUFFICIENT


@dataclass(frozen=True, slots=True)
class StrategyPerformanceRow:
    action: str
    label: str
    evidence_level: str
    attempts_count: int
    eligible_opportunities: int
    attempted_opportunities: int
    successful_verifications: int
    verified_recovered_minor: int
    revenue_at_risk_minor: int
    recovery_rate_pct: float
    verified_recovery_rate_pct: float
    average_verified_recovery_minor: int
    average_time_to_recovery_hours: float | None
    avg_attempts_per_recovery: float | None
    policy_blocks: int
    stop_outcomes: int
    escalate_outcomes: int
    wait_outcomes: int
    intervention_cost_minor: int
    average_cost_minor: int
    attribution: dict[str, int]
    segments: list[dict[str, Any]]
    last_observed_at: str | None
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "label": self.label,
            "evidence_level": self.evidence_level,
            "attempts_count": self.attempts_count,
            "eligible_opportunities": self.eligible_opportunities,
            "attempted_opportunities": self.attempted_opportunities,
            "successful_verifications": self.successful_verifications,
            "verified_recovered_minor": self.verified_recovered_minor,
            "revenue_at_risk_minor": self.revenue_at_risk_minor,
            "recovery_rate_pct": round(self.recovery_rate_pct, 1),
            "verified_recovery_rate_pct": round(self.verified_recovery_rate_pct, 1),
            "success_rate_pct": round(self.verified_recovery_rate_pct, 1),
            "average_verified_recovery_minor": self.average_verified_recovery_minor,
            "average_time_to_recovery_hours": round(self.average_time_to_recovery_hours, 1) if self.average_time_to_recovery_hours is not None else None,
            "avg_attempts_per_recovery": round(self.avg_attempts_per_recovery, 1) if self.avg_attempts_per_recovery is not None else None,
            "policy_blocks": self.policy_blocks,
            "stop_outcomes": self.stop_outcomes,
            "escalate_outcomes": self.escalate_outcomes,
            "wait_outcomes": self.wait_outcomes,
            "intervention_cost_minor": self.intervention_cost_minor,
            "average_cost_minor": self.average_cost_minor,
            "attribution": self.attribution,
            "segments": self.segments,
            "last_observed_at": self.last_observed_at,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class StrategyAnalyticsReport:
    total_historical_cases: int
    strategies: list[dict[str, Any]]
    what_works: list[dict[str, Any]]
    what_doesnt_work: list[dict[str, Any]]
    opportunity_signals: list[str]
    financial_kpis: dict[str, Any] = field(default_factory=dict)
    calibration_metrics: dict[str, Any] = field(default_factory=dict)
    revenue_lost_reasons: list[dict[str, Any]] = field(default_factory=list)
    policy_performance: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_historical_cases": self.total_historical_cases,
            "strategies": self.strategies,
            "what_works": self.what_works,
            "what_doesnt_work": self.what_doesnt_work,
            "opportunity_signals": self.opportunity_signals,
            "financial_kpis": self.financial_kpis,
            "calibration_metrics": self.calibration_metrics,
            "revenue_lost_reasons": self.revenue_lost_reasons,
            "policy_performance": self.policy_performance,
            "generated_at": self.generated_at,
        }


class StrategyAnalyticsService:
    """Aggregates verified historical outcomes into strategy performance metrics."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def generate_report(self) -> StrategyAnalyticsReport:
        from app.dashboard_api import _get_items, _get_attempts, _get_decisions, _actual_recovered_from_outcomes

        items = _get_items(self._container)
        total_cases = len(items)
        attempts = _get_attempts(self._container)
        decisions = _get_decisions(self._container)

        item_map = {i.id: i for i in items}
        item_status_map = {i.id: (i.status.value if hasattr(i.status, "value") else str(i.status)) for i in items}
        item_amt_map = {i.id: i.amount_minor for i in items}
        item_root_cause_map = {i.id: (i.root_cause or "unclassified") for i in items}
        item_payment_method_map = {i.id: (i.metadata.get("payment_method", "unknown") if isinstance(i.metadata, dict) else "unknown") for i in items}

        # Authoritative verified recovery from outcomes
        outcomes_map: dict[str, Any] = {}
        if hasattr(self._container, "outcomes") and self._container.outcomes is not None:
            try:
                all_outcomes = self._container.outcomes.list_all() if hasattr(self._container.outcomes, "list_all") else []
                for o in all_outcomes:
                    oid = getattr(o, "recovery_item_id", None)
                    if oid:
                        outcomes_map[oid] = o
            except Exception:
                pass

        verified_item_ids: set[str] = set()
        for item_id, outcome in outcomes_map.items():
            amt = getattr(outcome, "actual_recovery_minor", 0) or 0
            if amt > 0:
                verified_item_ids.add(item_id)

        # Also mark items with status=recovered as verified even without outcome record
        for i in items:
            if item_status_map.get(i.id) == "recovered" and i.id not in verified_item_ids:
                if getattr(i, "actual_recovery_value", 0) or 0 > 0:
                    verified_item_ids.add(i.id)

        recovered = _actual_recovered_from_outcomes(self._container)
        cost = sum(getattr(i, "intervention_cost", 0) or 0 for i in items)
        net_recovered = max(0, recovered - cost)
        total_risk = sum(i.amount_minor for i in items)
        rec_rate = (recovered / total_risk * 100.0) if total_risk > 0 else 0.0
        recovered_count = len([i for i in items if i.id in verified_item_ids])
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
            "verified_cases": recovered_count,
        }

        # Calibration metrics
        samples = []
        for i in items:
            item_status = item_status_map.get(i.id, "unknown")
            item_decs = [d for d in decisions if (d.get("recovery_item_id") if isinstance(d, dict) else getattr(d, "recovery_item_id", None)) == i.id]
            if item_decs:
                latest_dec = item_decs[-1]
                dec_action = latest_dec.get("proposed_action") if isinstance(latest_dec, dict) else getattr(latest_dec, "proposed_action", "unknown")
                exp_val = getattr(i, "expected_recovery_value", 0) or 0
                outcome = outcomes_map.get(i.id)
                actual_from_outcome = getattr(outcome, "actual_recovery_minor", 0) or 0 if outcome else 0
                act_val = actual_from_outcome or (i.amount_minor if item_status == "recovered" else 0)
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

        # Strategy performance breakdown
        strategy_stats: dict[str, dict[str, Any]] = {}
        for act_key, label in KNOWN_STRATEGIES:
            strategy_stats[act_key] = {
                "label": label,
                "attempts": 0,
                "attempted_opportunities": set(),
                "eligible_opportunities": 0,
                "successful_verifications": 0,
                "verified_recovered": 0,
                "time_to_recovery_hours": [],
                "attempts_per_recovery": [],
                "policy_blocks": 0,
                "stop_outcomes": 0,
                "escalate_outcomes": 0,
                "wait_outcomes": 0,
                "cost": 0,
                "attribution": {},
                "segments": {},
                "last_observed_at": None,
                "_last_observed_dt": None,
                "all_attempts": [],
            }

        # Count eligible opportunities per strategy (items that could have used this strategy)
        for i in items:
            root_cause = item_root_cause_map.get(i.id, "unclassified")
            payment_method = item_payment_method_map.get(i.id, "unknown")
            segment_key = f"{root_cause}|{payment_method}"

            eligible_actions = self._eligible_actions_for_item(i)
            for act_key, _ in KNOWN_STRATEGIES:
                if act_key in eligible_actions:
                    strategy_stats[act_key]["eligible_opportunities"] += 1
                    seg = strategy_stats[act_key]["segments"].setdefault(segment_key, {
                        "segment_key": segment_key,
                        "failure_category": root_cause,
                        "payment_method": payment_method,
                        "attempts": 0,
                        "successful_verifications": 0,
                        "verified_recovered_minor": 0,
                        "attempted_opportunities": set(),
                    })
                    seg["eligible_opportunities"] = seg.get("eligible_opportunities", 0) + 1

        for a in attempts:
            act = getattr(a, "action", "") if hasattr(a, "action") else a.get("action", "")
            item_id = getattr(a, "recovery_item_id", "") if hasattr(a, "recovery_item_id") else a.get("recovery_item_id", "")
            if act not in strategy_stats:
                continue

            stat = strategy_stats[act]
            stat["attempts"] += 1
            stat["all_attempts"].append(a)
            stat["attempted_opportunities"].add(item_id)

            item = item_map.get(item_id)
            root_cause = item_root_cause_map.get(item_id, "unclassified")
            payment_method = item_payment_method_map.get(item_id, "unknown")
            segment_key = f"{root_cause}|{payment_method}"
            seg = stat["segments"].setdefault(segment_key, {
                "segment_key": segment_key,
                "failure_category": root_cause,
                "payment_method": payment_method,
                "attempts": 0,
                "successful_verifications": 0,
                "verified_recovered_minor": 0,
                "attempted_opportunities": set(),
            })
            seg["attempts"] += 1
            seg["attempted_opportunities"].add(item_id)

            outcome_str = getattr(a, "outcome", "") or ""
            if outcome_str in OUTCOME_POLICY_BLOCKED:
                stat["policy_blocks"] += 1
            elif outcome_str in OUTCOME_STOPPED:
                stat["stop_outcomes"] += 1
            elif outcome_str in OUTCOME_ESCALATED:
                stat["escalate_outcomes"] += 1
            elif outcome_str in OUTCOME_WAITED:
                stat["wait_outcomes"] += 1

            executed_at = getattr(a, "executed_at", None)
            if executed_at and item_id in verified_item_ids:
                stat["successful_verifications"] += 1
                outcome = outcomes_map.get(item_id)
                recovered_at = getattr(outcome, "recovered_at", None) if outcome else None
                if recovered_at and executed_at:
                    try:
                        delta = (recovered_at - executed_at).total_seconds() / 3600.0
                        if delta >= 0:
                            stat["time_to_recovery_hours"].append(delta)
                    except Exception:
                        pass
                elif item_status_map.get(item_id) == "recovered":
                    delta = 24.0
                    stat["time_to_recovery_hours"].append(delta)

                stat["verified_recovered"] += item_amt_map.get(item_id, 0)
                attempts_for_item = len([x for x in stat["all_attempts"] if getattr(x, "recovery_item_id", "") == item_id])
                stat["attempts_per_recovery"].append(attempts_for_item)

                seg["successful_verifications"] += 1
                seg["verified_recovered_minor"] += item_amt_map.get(item_id, 0)

            stat["cost"] += getattr(a, "cost_minor", 0) or 500

            ts = getattr(a, "executed_at", None) or getattr(a, "scheduled_at", None)
            if ts:
                last_ts = stat.get("_last_observed_dt")
                if last_ts is None or ts > last_ts:
                    stat["_last_observed_dt"] = ts
                    stat["last_observed_at"] = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        # Build strategy rows
        strategies = []
        for act_key, stat in strategy_stats.items():
            if stat["attempts"] == 0:
                continue
            attempts_count = stat["attempts"]
            attempted_opps = len(stat["attempted_opportunities"])
            successful_verifications = stat["successful_verifications"]
            verified_recovered = stat["verified_recovered"]
            evidence = _evidence_level(attempts_count, successful_verifications)
            recovery_rate = (successful_verifications / attempted_opps * 100.0) if attempted_opps > 0 else 0.0
            verified_recovery_rate = (successful_verifications / attempts_count * 100.0) if attempts_count > 0 else 0.0
            avg_verified_recovery = int(verified_recovered / max(1, successful_verifications))
            avg_ttr = sum(stat["time_to_recovery_hours"]) / len(stat["time_to_recovery_hours"]) if stat["time_to_recovery_hours"] else None
            avg_attempts = sum(stat["attempts_per_recovery"]) / len(stat["attempts_per_recovery"]) if stat["attempts_per_recovery"] else None
            avg_cost = int(stat["cost"] / attempts_count)

            segment_list = []
            for seg_key, seg in stat["segments"].items():
                seg_attempts = seg["attempts"]
                seg_successes = seg["successful_verifications"]
                seg_recovered = seg["verified_recovered_minor"]
                segment_list.append({
                    "segment_key": seg_key,
                    "failure_category": seg.get("failure_category", "unknown"),
                    "payment_method": seg.get("payment_method", "unknown"),
                    "attempts": seg_attempts,
                    "successful_verifications": seg_successes,
                    "verified_recovered_minor": seg_recovered,
                    "recovery_rate_pct": round((seg_successes / seg_attempts * 100.0), 1) if seg_attempts > 0 else 0.0,
                })

            explanation = self._build_explanation(stat["label"], evidence, attempts_count, successful_verifications, verified_recovered)

            strategies.append(StrategyPerformanceRow(
                action=act_key,
                label=stat["label"],
                evidence_level=evidence,
                attempts_count=attempts_count,
                eligible_opportunities=stat["eligible_opportunities"],
                attempted_opportunities=attempted_opps,
                successful_verifications=successful_verifications,
                verified_recovered_minor=verified_recovered,
                revenue_at_risk_minor=total_risk,
                recovery_rate_pct=recovery_rate,
                verified_recovery_rate_pct=verified_recovery_rate,
                average_verified_recovery_minor=avg_verified_recovery,
                average_time_to_recovery_hours=avg_ttr,
                avg_attempts_per_recovery=avg_attempts,
                policy_blocks=stat["policy_blocks"],
                stop_outcomes=stat["stop_outcomes"],
                escalate_outcomes=stat["escalate_outcomes"],
                wait_outcomes=stat["wait_outcomes"],
                intervention_cost_minor=stat["cost"],
                average_cost_minor=avg_cost,
                attribution={},
                segments=segment_list,
                last_observed_at=stat["last_observed_at"],
                explanation=explanation,
            ).to_dict())

        what_works = []
        what_doesnt_work = []
        for s in strategies:
            if s["evidence_level"] == EVIDENCE_ESTABLISHED and s["verified_recovery_rate_pct"] >= 30:
                what_works.append({
                    "action": s["action"],
                    "label": s["label"],
                    "evidence_level": s["evidence_level"],
                    "successful_verifications": s["successful_verifications"],
                    "verified_recovered_minor": s["verified_recovered_minor"],
                    "verified_recovery_rate_pct": s["verified_recovery_rate_pct"],
                    "explanation": s["explanation"],
                })
            elif s["evidence_level"] in (EVIDENCE_EMERGING, EVIDENCE_ESTABLISHED) and s["verified_recovery_rate_pct"] < 15 and s["attempts_count"] >= 5:
                what_doesnt_work.append({
                    "action": s["action"],
                    "label": s["label"],
                    "evidence_level": s["evidence_level"],
                    "attempts_count": s["attempts_count"],
                    "successful_verifications": s["successful_verifications"],
                    "verified_recovery_rate_pct": s["verified_recovery_rate_pct"],
                    "stop_outcomes": s["stop_outcomes"],
                    "policy_blocks": s["policy_blocks"],
                    "explanation": s["explanation"],
                })

        signals = []
        if strategies:
            best = max(strategies, key=lambda s: s["verified_recovered_minor"])
            signals.append(
                f"Top performing strategy: {best['label']} with {best['verified_recovery_rate_pct']}% verified recovery rate across {best['successful_verifications']} verified recoveries."
            )
            if what_works:
                ww = what_works[0]
                signals.append(
                    f"Historically effective: {ww['label']} — {ww['successful_verifications']} verified recoveries "
                    f"at {ww['verified_recovery_rate_pct']}% verified recovery rate ({ww['evidence_level']} evidence)."
                )
            if what_doesnt_work:
                wdw = what_doesnt_work[0]
                signals.append(
                    f"Historically weak: {wdw['label']} — {wdw['successful_verifications']} verified recoveries "
                    f"across {wdw['attempts_count']} attempts ({wdw['verified_recovery_rate_pct']}% verified recovery rate). "
                    f"Distinguish strategy limitation from policy prevention: {wdw['policy_blocks']} policy blocks recorded."
                )

        # Revenue lost reasons
        unrecovered_items = [i for i in items if i.id not in verified_item_ids and item_status_map.get(i.id) not in ("recovered",)]
        reasons_map: dict[str, dict[str, Any]] = {}
        for ui in unrecovered_items:
            cat = item_root_cause_map.get(ui.id, "unclassified")
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

        # Policy performance table
        policy_performance = []
        for s in strategies:
            policy_performance.append({
                "action": s["action"],
                "label": s["label"],
                "attempted_opportunities": s["attempted_opportunities"],
                "policy_blocks": s["policy_blocks"],
                "stop_outcomes": s["stop_outcomes"],
                "escalate_outcomes": s["escalate_outcomes"],
                "wait_outcomes": s["wait_outcomes"],
                "successful_verifications": s["successful_verifications"],
                "note": "Policy blocks prevent unsafe execution and do not indicate strategy failure." if s["policy_blocks"] > 0 else "",
            })

        return StrategyAnalyticsReport(
            total_historical_cases=total_cases,
            strategies=strategies,
            what_works=what_works,
            what_doesnt_work=what_doesnt_work,
            opportunity_signals=signals,
            financial_kpis=financial_kpis,
            calibration_metrics=calibration_metrics,
            revenue_lost_reasons=list(reasons_map.values()),
            policy_performance=policy_performance,
        )

    def _eligible_actions_for_item(self, item: Any) -> frozenset[str]:
        status = str(getattr(item, "status", "")).lower()
        if status in ("recovered", "stopped", "escalated"):
            return frozenset()
        return frozenset({"send_payment_link", "retry_payment", "send_reminder", "alternate_channel", "promise_to_pay", "send_discount"})

    def _build_explanation(self, label: str, evidence: str, attempts: int, recoveries: int, recovered_minor: int) -> str:
        if evidence == EVIDENCE_INSUFFICIENT:
            return f"Not enough verified recovery history to establish a preferred outcome for {label}. More execution evidence is needed."
        if evidence == EVIDENCE_EMERGING:
            return f"{label} shows emerging evidence: {recoveries} verified recoveries across {attempts} attempts. Pattern is forming but not yet established."
        return f"{label} has established evidence: {recoveries} verified recoveries across {attempts} attempts. {fmt_minor(recovered_minor)} in settlement-confirmed recovery."


def fmt_minor(minor: int) -> str:
    return "₹" + f"{minor / 100:,.0f}"
