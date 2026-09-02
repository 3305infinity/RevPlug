"""Recovery Policy Configuration & Versioning Service for RevPlug.

Allows business operators to configure recovery policy constraints, tracks policy versioning,
and generates live policy preview data. LLMs are strictly forbidden from modifying policy rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class PolicyConfig:
    version: str = "v1.0"
    max_retries: int = 2
    max_contacts_per_24h: int = 2
    min_expected_net_ev_minor: int = 10000  # ₹100
    max_intervention_cost_minor: int = 500000  # ₹5,000
    cooldown_retry_minutes: int = 120
    allowed_channels: list[str] = field(default_factory=lambda: ["email", "sms", "whatsapp", "payment_link"])
    allowed_payment_methods: list[str] = field(default_factory=lambda: ["card", "upi", "netbanking", "bank_transfer"])
    escalation_thresholds_minor: int = 5000000  # ₹50,000
    failure_categories_blocked: list[str] = field(default_factory=lambda: ["fraud", "hard_decline", "account_closed"])
    systemic_suppression_threshold_pct: float = 25.0
    # Incident detection thresholds
    incident_min_affected_opportunities: int = 3
    incident_min_distinct_customers: int = 2
    incident_min_revenue_at_risk_minor: int = 100000  # ₹1,000
    incident_concentration_multiplier: float = 2.0
    incident_detection_window_minutes: int = 60
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_by: str = "operator_admin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "max_retries": self.max_retries,
            "max_contacts_per_24h": self.max_contacts_per_24h,
            "min_expected_net_ev_minor": self.min_expected_net_ev_minor,
            "max_intervention_cost_minor": self.max_intervention_cost_minor,
            "cooldown_retry_minutes": self.cooldown_retry_minutes,
            "allowed_channels": self.allowed_channels,
            "allowed_payment_methods": self.allowed_payment_methods,
            "escalation_thresholds_minor": self.escalation_thresholds_minor,
            "failure_categories_blocked": self.failure_categories_blocked,
            "systemic_suppression_threshold_pct": self.systemic_suppression_threshold_pct,
            "incident_min_affected_opportunities": self.incident_min_affected_opportunities,
            "incident_min_distinct_customers": self.incident_min_distinct_customers,
            "incident_min_revenue_at_risk_minor": self.incident_min_revenue_at_risk_minor,
            "incident_concentration_multiplier": self.incident_concentration_multiplier,
            "incident_detection_window_minutes": self.incident_detection_window_minutes,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "preview_summary": {
                "max_retries": self.max_retries,
                "max_contacts": f"{self.max_contacts_per_24h} / 24h",
                "min_net_ev": f"₹{self.min_expected_net_ev_minor / 100:,.0f}",
                "hard_decline": "BLOCKED" if "hard_decline" in self.failure_categories_blocked else "ALLOWED",
                "fraud_recovery": "BLOCKED" if "fraud" in self.failure_categories_blocked else "ALLOWED",
                "dispute_collection": "HUMAN ONLY",
                "incident_detection": f"{self.incident_min_affected_opportunities}+ ops, {self.incident_concentration_multiplier}x concentration",
            },
        }


class PolicyConfigStore:
    """In-memory singleton store for versioned operator policy config."""

    _instance: PolicyConfigStore | None = None

    def __init__(self) -> None:
        self._current_config = PolicyConfig()
        self._history: list[PolicyConfig] = [self._current_config]

    @classmethod
    def get_instance(cls) -> PolicyConfigStore:
        if cls._instance is None:
            cls._instance = PolicyConfigStore()
        return cls._instance

    def get_config(self) -> PolicyConfig:
        return self._current_config

    def update_config(self, updates: dict[str, Any], updated_by: str = "operator_admin") -> PolicyConfig:
        # Increment version e.g. v1.0 -> v1.1
        try:
            curr_num = float(self._current_config.version.replace("v", ""))
            next_ver = f"v{curr_num + 0.1:.1f}"
        except Exception:
            next_ver = "v1.1"

        new_config = PolicyConfig(
            version=next_ver,
            max_retries=updates.get("max_retries", self._current_config.max_retries),
            max_contacts_per_24h=updates.get("max_contacts_per_24h", self._current_config.max_contacts_per_24h),
            min_expected_net_ev_minor=updates.get("min_expected_net_ev_minor", self._current_config.min_expected_net_ev_minor),
            max_intervention_cost_minor=updates.get("max_intervention_cost_minor", self._current_config.max_intervention_cost_minor),
            cooldown_retry_minutes=updates.get("cooldown_retry_minutes", self._current_config.cooldown_retry_minutes),
            allowed_channels=updates.get("allowed_channels", self._current_config.allowed_channels),
            allowed_payment_methods=updates.get("allowed_payment_methods", self._current_config.allowed_payment_methods),
            escalation_thresholds_minor=updates.get("escalation_thresholds_minor", self._current_config.escalation_thresholds_minor),
            failure_categories_blocked=updates.get("failure_categories_blocked", self._current_config.failure_categories_blocked),
            systemic_suppression_threshold_pct=updates.get("systemic_suppression_threshold_pct", self._current_config.systemic_suppression_threshold_pct),
            incident_min_affected_opportunities=updates.get("incident_min_affected_opportunities", self._current_config.incident_min_affected_opportunities),
            incident_min_distinct_customers=updates.get("incident_min_distinct_customers", self._current_config.incident_min_distinct_customers),
            incident_min_revenue_at_risk_minor=updates.get("incident_min_revenue_at_risk_minor", self._current_config.incident_min_revenue_at_risk_minor),
            incident_concentration_multiplier=updates.get("incident_concentration_multiplier", self._current_config.incident_concentration_multiplier),
            incident_detection_window_minutes=updates.get("incident_detection_window_minutes", self._current_config.incident_detection_window_minutes),
            updated_at=datetime.now(timezone.utc).isoformat(),
            updated_by=updated_by,
        )

        self._current_config = new_config
        self._history.append(new_config)
        return new_config

    def get_history(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._history]
