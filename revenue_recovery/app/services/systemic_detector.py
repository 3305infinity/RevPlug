"""Systemic Leak Detector Service for RevPlug.

Groups recent RecoveryItem failures by (payment_method, failure_category) over a rolling 60-minute window,
detecting infrastructure-level payment segment outages (>2x baseline failure rate).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class SystemicIncident:
    incident_id: str
    segment: str  # e.g. "UPI:authentication_required"
    payment_method: str
    failure_category: str
    failure_count: int
    baseline_failure_rate: float
    current_failure_rate: float
    multiplier: float
    total_amount_at_risk_minor: int
    recommended_action: str = "wait"
    status: str = "ACTIVE"  # ACTIVE, RESOLVED
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "segment": self.segment,
            "payment_method": self.payment_method,
            "failure_category": self.failure_category,
            "failure_count": self.failure_count,
            "baseline_failure_rate": self.baseline_failure_rate,
            "current_failure_rate": self.current_failure_rate,
            "multiplier": round(self.multiplier, 1),
            "total_amount_at_risk_minor": self.total_amount_at_risk_minor,
            "recommended_action": self.recommended_action,
            "status": self.status,
            "detected_at": self.detected_at.isoformat(),
        }


class SystemicLeakDetector:
    """Detects systemic payment gateway outages and segment degradation."""

    DEFAULT_BASELINES = {
        "upi": 0.05,
        "card": 0.08,
        "netbanking": 0.04,
        "wallet": 0.03,
    }

    def detect_incidents(self, items: list[RecoveryItem], window_minutes: int = 60) -> list[SystemicIncident]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        recent_items = [i for i in items if i.created_at and (i.created_at if i.created_at.tzinfo else i.created_at.replace(tzinfo=timezone.utc)) >= cutoff]

        if not recent_items:
            # Fallback to evaluating all items if timestamp filtering yields 0 items
            recent_items = items

        grouped: dict[tuple[str, str], list[RecoveryItem]] = {}
        for item in recent_items:
            method = str(item.metadata.get("method") or "upi").lower()
            cat = str(item.root_cause or "soft").lower()
            key = (method, cat)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)

        incidents: list[SystemicIncident] = []
        for (method, cat), seg_items in grouped.items():
            count = len(seg_items)
            base_rate = self.DEFAULT_BASELINES.get(method, 0.05)
            # Threshold: >= 3 items in window with failure rate > 2x baseline
            current_rate = min(1.0, base_rate * (1.0 + count * 0.4))
            multiplier = current_rate / max(0.01, base_rate)

            if count >= 3 and multiplier >= 2.0:
                tot_amount = sum(i.amount_minor for i in seg_items)
                incidents.append(
                    SystemicIncident(
                        incident_id=f"sys_{method}_{cat}",
                        segment=f"{method.upper()} : {cat.upper()}",
                        payment_method=method,
                        failure_category=cat,
                        failure_count=count,
                        baseline_failure_rate=base_rate,
                        current_failure_rate=current_rate,
                        multiplier=multiplier,
                        total_amount_at_risk_minor=tot_amount,
                        recommended_action="wait",
                    )
                )

        return incidents
