"""Policy Simulator Service for RevPlug.

Evaluates how proposed policy changes would affect recovery decisions
without modifying live policy or executing any actions.

Design:
  Current Policy  ->  Existing PolicyEngine + StoppingRules + RecoveryGuard  ->  Current Decision
  Proposed Policy ->  Same PolicyEngine + StoppingRules + RecoveryGuard       ->  Proposed Decision
  Compare results ->  Decision diff + financial impact + safety impact

No second decision engine. No ML. No execution.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus
from app.policies.engine import InterventionPolicy, PolicyEngine, PolicyDecision
from app.policies.guard import DefaultRecoveryGuard, RecoveryGuardDecision
from app.policies.stopping_rules import StoppingRules
from app.services.policy_config_service import PolicyConfig, PolicyConfigStore


@dataclass(frozen=True, slots=True)
class SimulatedDecision:
    """Policy evaluation result for a single opportunity."""

    opportunity_id: str
    decision_type: str  # ALLOWED | DENY | ESCALATE | WAIT | STOP
    allowed: bool
    reason_code: str
    reason: str
    rule: str
    proposed_action: str | None = None
    next_state: str | None = None
    safety_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionDiff:
    """Difference between current and proposed policy decisions."""

    opportunity_id: str
    changed: bool
    current: SimulatedDecision
    proposed: SimulatedDecision
    change_type: str  # e.g. "RECOVER -> WAIT"
    policy_rule_responsible: str
    financial_context: dict[str, Any] = field(default_factory=dict)
    safety_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PolicySimulationResult:
    """Complete result of a policy simulation run."""

    simulation_id: str
    timestamp: str
    current_policy_version: str
    proposed_policy_version: str
    opportunities_evaluated: int
    unevaluable_count: int
    unchanged_count: int
    changed_count: int
    decision_diffs: list[DecisionDiff]

    # Decision distribution
    current_distribution: dict[str, int] = field(default_factory=dict)
    proposed_distribution: dict[str, int] = field(default_factory=dict)

    # Financial impact (expected recovery, not verified)
    current_expected_recovery_minor: int = 0
    proposed_expected_recovery_minor: int = 0
    expected_recovery_delta_minor: int = 0

    # Revenue at risk
    current_revenue_at_risk_minor: int = 0
    proposed_revenue_at_risk_minor: int = 0

    # Safety impact
    current_policy_violations: int = 0
    proposed_policy_violations: int = 0
    safety_conflicts: list[dict[str, Any]] = field(default_factory=list)

    # Scope
    scope: str = "current_portfolio"
    opportunity_ids: list[str] = field(default_factory=list)
    unevaluable_ids: list[str] = field(default_factory=list)

    error: str | None = None


def _get_canonical_action(item: RecoveryItem) -> str | None:
    """Return the canonical proposed_action for policy evaluation."""
    meta = getattr(item, "metadata", {}) or {}
    proposed = meta.get("proposed_action") or meta.get("action") or meta.get("recommended_action")
    if not proposed and item.status.value not in {"recovered", "stopped"}:
        proposed = "send_payment_link" if "auth" in str(item.root_cause).lower() or "timeout" in str(item.root_cause).lower() else "retry_payment"
    return str(proposed) if proposed else None


def _build_guard(
    policy_config: PolicyConfig,
    opted_out_customers: frozenset[str] = frozenset(),
) -> DefaultRecoveryGuard:
    """Build a guard from a policy configuration."""
    stopping_rules = StoppingRules(
        max_attempts=policy_config.max_retries,
        opted_out_customer_ids=opted_out_customers,
    )
    policy_engine = InterventionPolicy(
        max_retry_attempts=policy_config.max_retries,
        opted_out_customer_ids=opted_out_customers,
        max_contacts_per_24h=policy_config.max_contacts_per_24h,
        min_expected_net_ev_minor=policy_config.min_expected_net_ev_minor,
        max_intervention_cost_minor=policy_config.max_intervention_cost_minor,
        escalation_thresholds_minor=policy_config.escalation_thresholds_minor,
        failure_categories_blocked=frozenset(policy_config.failure_categories_blocked or []),
    )
    return DefaultRecoveryGuard(
        stopping_rules=stopping_rules,
        policy_engine=policy_engine,
    )


def _evaluate_item(
    item: RecoveryItem,
    guard: DefaultRecoveryGuard,
    proposed_action: str,
    *,
    now: datetime | None = None,
) -> SimulatedDecision:
    """Evaluate a single opportunity through a guard."""
    if now is None:
        now = datetime.now(timezone.utc)

    decision = guard.evaluate(
        item,
        proposed_action=proposed_action,
        now=now,
    )

    safety: dict[str, Any] = {}
    if getattr(decision, "stopping_decision", None) is not None:
        sd = decision.stopping_decision
        safety["stopping_rule"] = getattr(sd, "rule", None)
        safety["stopping_reason_code"] = getattr(sd, "reason_code", None)
    if getattr(decision, "policy_decision", None) is not None:
        pd = decision.policy_decision
        safety["policy_rule"] = getattr(pd, "policy_rule", None)
        safety["policy_reason_code"] = getattr(pd, "reason_code", None)

    return SimulatedDecision(
        opportunity_id=item.id,
        decision_type=decision.decision_type,
        allowed=decision.allowed,
        reason_code=decision.reason_code,
        reason=decision.reason,
        rule=decision.rule,
        proposed_action=proposed_action,
        next_state=decision.next_state.value if hasattr(decision.next_state, "value") else str(decision.next_state),
        safety_context=safety,
    )


def _decision_to_distribution(diffs: list[DecisionDiff]) -> dict[str, int]:
    """Compute decision distribution from a list of diffs (using proposed decisions)."""
    dist: dict[str, int] = {}
    for d in diffs:
        dt = d.proposed.decision_type if d.changed else d.current.decision_type
        dist[dt] = dist.get(dt, 0) + 1
    return dist


def _count_violations(diffs: list[DecisionDiff], side: str) -> int:
    """Count policy violations in current or proposed decisions."""
    count = 0
    for d in diffs:
        decisions = (d.proposed, d.current) if side == "proposed" else (d.current, d.proposed)
        for dec in decisions:
            if dec.decision_type in {"DENY", "STOP"} and dec.reason_code not in {
                "terminal_state",
                "payment_succeeded",
                "customer_opted_out",
                "fraud_detected",
                "policy_allowed",
            }:
                count += 1
    return count


class PolicySimulatorService:
    """Simulates policy changes against live opportunities."""

    def __init__(self) -> None:
        self._config_store = PolicyConfigStore.get_instance()

    def preview_policy_change(
        self,
        proposed_policy: dict[str, Any],
        *,
        opportunity_ids: list[str] | None = None,
        container: Any | None = None,
    ) -> PolicySimulationResult:
        """Preview how a proposed policy change would affect recovery decisions.

        Args:
            proposed_policy: Partial or full PolicyConfig fields to preview.
            opportunity_ids: Optional list of opportunity IDs to evaluate.
                If omitted, evaluates the current live portfolio.
            container: PersistenceContainer for fetching live opportunities.

        Returns:
            PolicySimulationResult with decision diffs and impact analysis.
        """
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        current_config = self._config_store.get_config()

        # Build proposed config by overlaying changes on current config
        proposed_config = PolicyConfig(
            version=f"{current_config.version} (proposed)",
            max_retries=proposed_policy.get("max_retries", current_config.max_retries),
            max_contacts_per_24h=proposed_policy.get("max_contacts_per_24h", current_config.max_contacts_per_24h),
            min_expected_net_ev_minor=proposed_policy.get("min_expected_net_ev_minor", current_config.min_expected_net_ev_minor),
            max_intervention_cost_minor=proposed_policy.get("max_intervention_cost_minor", current_config.max_intervention_cost_minor),
            cooldown_retry_minutes=proposed_policy.get("cooldown_retry_minutes", current_config.cooldown_retry_minutes),
            allowed_channels=proposed_policy.get("allowed_channels", current_config.allowed_channels),
            allowed_payment_methods=proposed_policy.get("allowed_payment_methods", current_config.allowed_payment_methods),
            escalation_thresholds_minor=proposed_policy.get("escalation_thresholds_minor", current_config.escalation_thresholds_minor),
            failure_categories_blocked=proposed_policy.get("failure_categories_blocked", current_config.failure_categories_blocked),
            systemic_suppression_threshold_pct=proposed_policy.get("systemic_suppression_threshold_pct", current_config.systemic_suppression_threshold_pct),
            incident_min_affected_opportunities=proposed_policy.get("incident_min_affected_opportunities", current_config.incident_min_affected_opportunities),
            incident_min_distinct_customers=proposed_policy.get("incident_min_distinct_customers", current_config.incident_min_distinct_customers),
            incident_min_revenue_at_risk_minor=proposed_policy.get("incident_min_revenue_at_risk_minor", current_config.incident_min_revenue_at_risk_minor),
            incident_concentration_multiplier=proposed_policy.get("incident_concentration_multiplier", current_config.incident_concentration_multiplier),
            incident_detection_window_minutes=proposed_policy.get("incident_detection_window_minutes", current_config.incident_detection_window_minutes),
        )

        current_guard = _build_guard(current_config)
        proposed_guard = _build_guard(proposed_config)

        # Fetch opportunities
        items = self._fetch_opportunities(container, opportunity_ids)

        diffs: list[DecisionDiff] = []
        current_dist: dict[str, int] = {}
        proposed_dist: dict[str, int] = {}
        current_expected = 0
        proposed_expected = 0
        current_rar = 0
        proposed_rar = 0
        safety_conflicts: list[dict[str, Any]] = []
        unevaluable_ids: list[str] = []

        for item in items:
            canonical_action = _get_canonical_action(item)
            if canonical_action is None:
                unevaluable_ids.append(item.id)
                continue

            current_decision = _evaluate_item(item, current_guard, canonical_action)
            proposed_decision = _evaluate_item(item, proposed_guard, canonical_action)

            current_dist[current_decision.decision_type] = current_dist.get(current_decision.decision_type, 0) + 1
            proposed_dist[proposed_decision.decision_type] = proposed_dist.get(proposed_decision.decision_type, 0) + 1

            # Expected recovery comes from item metadata (AI proposal), not settlement
            expected_recovery = int(getattr(item, "expected_recovery_value", 0) or 0)
            current_expected += expected_recovery if current_decision.allowed and current_decision.decision_type == "ALLOWED" else 0
            proposed_expected += expected_recovery if proposed_decision.allowed and proposed_decision.decision_type == "ALLOWED" else 0

            amount_at_risk = int(getattr(item, "amount_minor", 0) or 0)
            current_rar += amount_at_risk if current_decision.decision_type in {"ALLOWED", "ESCALATE", "WAIT"} else 0
            proposed_rar += amount_at_risk if proposed_decision.decision_type in {"ALLOWED", "ESCALATE", "WAIT"} else 0

            changed = (
                current_decision.decision_type != proposed_decision.decision_type
                or current_decision.allowed != proposed_decision.allowed
                or current_decision.reason_code != proposed_decision.reason_code
            )

            if changed:
                # Detect safety conflicts
                if proposed_decision.decision_type in {"DENY", "STOP"} and current_decision.decision_type == "ALLOWED":
                    safety_conflicts.append({
                        "opportunity_id": item.id,
                        "type": "proposed_policy_blocks_legitimate_action",
                        "current_decision": current_decision.decision_type,
                        "proposed_decision": proposed_decision.decision_type,
                        "rule": proposed_decision.rule,
                        "reason": proposed_decision.reason,
                    })
                elif proposed_decision.decision_type == "ALLOWED" and current_decision.decision_type in {"DENY", "STOP"}:
                    # Proposed policy allows something that was blocked — check if it was a safety block
                    if current_decision.reason_code in {
                        "fraud_detected", "customer_opted_out", "terminal_state",
                        "terminal_state_reached", "policy_blocked",
                    }:
                        safety_conflicts.append({
                            "opportunity_id": item.id,
                            "type": "proposed_policy_removes_safety_protection",
                            "current_decision": current_decision.decision_type,
                            "proposed_decision": proposed_decision.decision_type,
                            "rule": current_decision.rule,
                            "reason": current_decision.reason,
                        })

                change_type = f"{current_decision.decision_type} -> {proposed_decision.decision_type}"
                diffs.append(DecisionDiff(
                    opportunity_id=item.id,
                    changed=True,
                    current=current_decision,
                    proposed=proposed_decision,
                    change_type=change_type,
                    policy_rule_responsible=proposed_decision.rule,
                    financial_context={
                        "amount_at_risk_minor": amount_at_risk,
                        "expected_recovery_minor": expected_recovery,
                    },
                    safety_context={
                        "current_rule": current_decision.rule,
                        "proposed_rule": proposed_decision.rule,
                        "current_reason_code": current_decision.reason_code,
                        "proposed_reason_code": proposed_decision.reason_code,
                    },
                ))

        return PolicySimulationResult(
            simulation_id=simulation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_policy_version=current_config.version,
            proposed_policy_version=proposed_config.version,
            opportunities_evaluated=len(items),
            unevaluable_count=len(unevaluable_ids),
            unchanged_count=len(items) - len(diffs) - len(unevaluable_ids),
            changed_count=len(diffs),
            decision_diffs=diffs,
            current_distribution=current_dist,
            proposed_distribution=proposed_dist,
            current_expected_recovery_minor=current_expected,
            proposed_expected_recovery_minor=proposed_expected,
            expected_recovery_delta_minor=proposed_expected - current_expected,
            current_revenue_at_risk_minor=current_rar,
            proposed_revenue_at_risk_minor=proposed_rar,
            current_policy_violations=_count_violations(diffs, "current"),
            proposed_policy_violations=_count_violations(diffs, "proposed"),
            safety_conflicts=safety_conflicts,
            scope="current_portfolio" if opportunity_ids is None else "selected_opportunities",
            opportunity_ids=[i.id for i in items],
            unevaluable_ids=unevaluable_ids,
        )

    def _fetch_opportunities(
        self,
        container: Any | None,
        opportunity_ids: list[str] | None,
    ) -> list[RecoveryItem]:
        """Fetch opportunities for simulation."""
        if opportunity_ids:
            if container is None:
                return []
            repo = getattr(container, "recovery_items", None)
            if repo is None:
                return []
            items = []
            for oid in opportunity_ids:
                item = repo.get(oid)
                if item is not None:
                    items.append(item)
            return items

        # Use current portfolio
        if container is None:
            return []

        repo = container.recovery_items
        items = []
        if hasattr(repo, "_items"):
            raw = list(repo._items.values())
        elif hasattr(repo, "list_all"):
            raw = repo.list_all()
        else:
            raw = []

        for item in raw:
            meta = getattr(item, "metadata", {}) or {}
            classification = _classify_item(meta)
            if classification in ("TEST_FIXTURE", "UNKNOWN"):
                continue
            items.append(item)

        return items


def _classify_item(meta: dict[str, Any]) -> str:
    """Classify item source for simulator boundary."""
    if meta.get("is_test_fixture") or meta.get("batch_scope") or meta.get("batch_id"):
        return "TEST_FIXTURE"
    if meta.get("is_synthetic") or meta.get("source") in ("synthetic_dataset", "demo_scenario"):
        return "BENCHMARK_SYNTHETIC"
    if meta.get("source") in ("webhook_live", "manual_case", "webhook"):
        return "LIVE_OPERATIONAL"
    return "UNKNOWN"
