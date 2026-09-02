"""Event-Driven Revenue-at-Risk Opportunity Detection Engine for RevPlug.

Translates incoming normalized revenue events into prioritized, scored, and policy-governed
RecoveryItem opportunities. Enforces strict idempotency, deterministic eligibility gates,
and Expected Net Recovery (Net EV) priority ranking.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from app.audit.models import InMemoryAuditLog
from app.db.container import PersistenceContainer
from app.domain.classification import classify_root_cause
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.priority import PriorityClassifier

logger = logging.getLogger(__name__)


@dataclass
class OpportunityRecord:
    id: str
    customer_id: str
    customer_name: str
    amount_at_risk_minor: int
    currency: str
    root_cause: str
    priority: str
    recovery_probability: float
    expected_gross_recovery_minor: int
    intervention_cost_minor: int
    expected_net_recovery_minor: int
    recommended_action: str
    reason: str
    policy_state: str
    current_status: str
    created_at: str
    last_event_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "amount_at_risk_minor": self.amount_at_risk_minor,
            "currency": self.currency,
            "root_cause": self.root_cause,
            "priority": self.priority,
            "recovery_probability": self.recovery_probability,
            "expected_gross_recovery_minor": self.expected_gross_recovery_minor,
            "intervention_cost_minor": self.intervention_cost_minor,
            "expected_net_recovery_minor": self.expected_net_recovery_minor,
            "recommended_action": self.recommended_action,
            "reason": self.reason,
            "policy_state": self.policy_state,
            "current_status": self.current_status,
            "created_at": self.created_at,
            "last_event_at": self.last_event_at,
            "metadata": self.metadata,
        }


class OpportunityDetector:
    """Event-Driven Opportunity Detection Engine."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container
        self._scorer = ExpectedValueScorer()
        self._priority_engine = PriorityClassifier()
        self._audit_log = getattr(container, "audit_log", InMemoryAuditLog())

    def process_event(self, event: dict[str, Any]) -> RecoveryItem:
        """Process a normalized revenue event idempotently and update opportunity state.

        Detects revenue at risk, classifies root cause, applies deterministic eligibility gates,
        scores Expected Net Recovery ($EV_{net}$), and updates repository cleanly.
        """
        event_type = str(event.get("event_type", "payment_failed")).lower()
        raw_reason = str(event.get("failure_reason") or event.get("reason") or "payment_timed_out").lower()
        external_id = str(event.get("reference_id") or event.get("invoice_id") or event.get("external_id") or f"ref_{int(time.time())}")
        raw_cust_name = event.get("customer_name")
        customer_name = str(raw_cust_name).strip() if raw_cust_name and str(raw_cust_name).strip() else None
        customer_id = str(event.get("customer_id") or f"cust_anon_{external_id[:8]}").strip()
        amount_minor = int(event.get("amount_minor", 0))
        currency = str(event.get("currency", "INR")).upper()

        consent_opt_out = bool(event.get("consent_opt_out", False))
        fraud_risk = bool(event.get("fraud_risk", False) or "fraud" in raw_reason or "risk" in raw_reason)
        is_dispute = bool("dispute" in event_type or "disput" in raw_reason or "chargeback" in raw_reason)
        is_systemic = bool(event.get("systemic_incident", False) or "gateway_outage" in raw_reason)
        is_success = event_type in ("payment_succeeded", "invoice_paid", "payment_recovered")

        root_cause = classify_root_cause(raw_reason)

        # 1. Check idempotency: find existing RecoveryItem across in-memory or database repos
        items_repo = self._container.recovery_items
        all_items: list[RecoveryItem] = []
        if hasattr(items_repo, "list_all"):
            try:
                all_items = items_repo.list_all()
            except Exception:
                all_items = []
        elif hasattr(items_repo, "_items"):
            all_items = list(items_repo._items.values())

        existing_item: RecoveryItem | None = None
        for item in all_items:
            ext = getattr(item, "external_id", None)
            cust = getattr(item, "customer_id", None)
            amt = getattr(item, "amount_minor", None)
            cause = getattr(item, "root_cause", None)
            status_val = getattr(item, "status", None)
            status_str = status_val.value if hasattr(status_val, "value") else str(status_val)

            if ext == external_id:
                existing_item = item
                break
            if cust == customer_id and (amt == amount_minor or root_cause == cause) and status_str not in ("recovered", "stopped"):
                existing_item = item
                break

        now = datetime.now(timezone.utc)

        # 2. Handle Payment Success Lifecycle Event
        if is_success:
            if existing_item:
                updated_item = replace(
                    existing_item,
                    status=RecoveryStatus.RECOVERED,
                    actual_recovery_value=amount_minor or existing_item.amount_minor,
                )
                items_repo.save(updated_item)
                return updated_item
            else:
                # Create completed item
                item_id = f"rec_{int(time.time())}_{customer_id[-4:] if len(customer_id) >= 4 else customer_id}"
                item = RecoveryItem(
                    id=item_id,
                    source_type=SourceType.PAYMENT_FAILURE,
                    external_id=external_id,
                    customer_id=customer_id,
                    amount_minor=amount_minor,
                    currency=currency,
                    created_at=now,
                    status=RecoveryStatus.RECOVERED,
                    root_cause=root_cause,
                    actual_recovery_value=amount_minor,
                    metadata={
                        "source": "webhook_live",
                        "customer_name": customer_name,
                        "is_synthetic": False,
                    },
                )
                items_repo.save(item)
                return item

        # 3. Score candidates using Expected Value Engine
        attempt_count = int(existing_item.metadata.get("attempt_count", 1)) if existing_item else 1
        candidates = self._scorer.evaluate_candidates(
            amount_minor=amount_minor,
            failure_category=root_cause,
            attempt_number=attempt_count,
        )
        best_candidate = candidates[0] if candidates else {"action": "send_payment_link", "net_expected_recovery": int(amount_minor * 0.6)}

        prob = best_candidate.get("success_probability", 0.65)
        exp_gross = best_candidate.get("expected_recovery", int(amount_minor * prob))
        cost_minor = best_candidate.get("intervention_cost", 500)
        net_ev = best_candidate.get("net_expected_recovery", exp_gross - cost_minor)

        # Priority Engine scoring
        priority_label = self._priority_engine.classify(exp_gross)

        # 4. Deterministic Eligibility Gates & Policy State Determination
        if fraud_risk or root_cause == "FRAUD_BLOCK":
            status = RecoveryStatus.STOPPED
            policy_state = "BLOCKED_FRAUD"
            rec_action = "stop_recovery"
            reason = "High fraud risk signal detected by safety gate"
        elif consent_opt_out or root_cause == "CONSENT_BLOCK":
            status = RecoveryStatus.STOPPED
            policy_state = "BLOCKED_CONSENT"
            rec_action = "stop_recovery"
            reason = "Customer consent opt-out policy shield active"
        elif is_dispute:
            status = RecoveryStatus.ESCALATED
            policy_state = "HUMAN_REVIEW_DISPUTE"
            rec_action = "escalate_human"
            reason = "Invoice disputed by customer — routed to human review"
        elif is_systemic:
            status = RecoveryStatus.INTERVENTION_PENDING
            policy_state = "SUPPRESSED_SYSTEMIC"
            rec_action = "wait_systemic"
            reason = "Systemic gateway outage active — retries suppressed"
        elif net_ev <= 0:
            status = RecoveryStatus.QUEUED
            policy_state = "NEGATIVE_NET_EV"
            rec_action = "no_action"
            reason = "Intervention cost exceeds expected recovery value"
        else:
            status = RecoveryStatus.QUEUED
            policy_state = "ACTIONABLE"
            rec_action = best_candidate.get("action", "send_payment_link")
            reason = f"Ranked #1 for Expected Net Recovery (Net EV: ₹{net_ev // 100:,})"

        # 5. Idempotent Upsert
        if existing_item:
            updated_item = replace(
                existing_item,
                amount_minor=amount_minor or existing_item.amount_minor,
                status=status,
                root_cause=root_cause,
                recovery_probability=prob,
                expected_recovery_value=exp_gross,
                priority=priority_label,
                stopped_reason=reason if status == RecoveryStatus.STOPPED else None,
                metadata={
                    **existing_item.metadata,
                    "customer_name": customer_name,
                    "recommended_action": rec_action,
                    "expected_net_ev_minor": net_ev,
                    "policy_state": policy_state,
                    "reason": reason,
                    "last_event_at": now.isoformat(),
                    "attempt_count": attempt_count + 1,
                    "systemic_suppress": policy_state == "SUPPRESSED_SYSTEMIC",
                },
            )
            items_repo.save(updated_item)
            return updated_item

        # Create new RecoveryItem
        item_id = f"rec_{int(time.time())}_{customer_id[-4:] if len(customer_id) >= 4 else customer_id}"
        item = RecoveryItem(
            id=item_id,
            source_type=SourceType.PAYMENT_FAILURE,
            external_id=external_id,
            customer_id=customer_id,
            amount_minor=amount_minor,
            currency=currency,
            created_at=now,
            status=status,
            root_cause=root_cause,
            recovery_probability=prob,
            expected_recovery_value=exp_gross,
            intervention_cost=cost_minor,
            priority=priority_label,
            stopped_reason=reason if status == RecoveryStatus.STOPPED else None,
            metadata={
                "source": str(event.get("source") or "webhook_live"),
                "customer_name": customer_name,
                "recommended_action": rec_action,
                "expected_net_ev_minor": net_ev,
                "policy_state": policy_state,
                "reason": reason,
                "last_event_at": now.isoformat(),
                "attempt_count": 1,
                "is_synthetic": False,
                "systemic_suppress": policy_state == "SUPPRESSED_SYSTEMIC",
            },
        )
        items_repo.save(item)
        return item

    def list_opportunities(self) -> list[OpportunityRecord]:
        """Return all active revenue opportunities pre-ranked by Expected Net Recovery ($EV_{net}$) descending."""
        from app.dashboard_api import _get_items

        items = _get_items(self._container)
        records: list[OpportunityRecord] = []

        for i in items:
            status_val = i.status.value if hasattr(i.status, "value") else str(i.status)
            meta = i.metadata or {}
            c_name = meta.get("customer_name") or i.customer_id

            net_ev = meta.get("expected_net_ev_minor")
            if net_ev is None:
                net_ev = int((i.expected_recovery_value or i.amount_minor) - (i.intervention_cost or 500))

            cost = i.intervention_cost or 500
            exp_gross = i.expected_recovery_value or i.amount_minor
            prob = i.recovery_probability or 0.65

            rec_action = meta.get("recommended_action") or ("send_payment_link" if "upi" in i.root_cause.lower() else "retry_payment")
            policy_st = meta.get("policy_state") or ("BLOCKED" if status_val == "stopped" else "ACTIONABLE")
            reason_txt = meta.get("reason") or f"Expected Net Recovery: ₹{net_ev // 100:,}"

            rec = OpportunityRecord(
                id=i.id,
                customer_id=i.customer_id,
                customer_name=c_name,
                amount_at_risk_minor=i.amount_minor,
                currency=i.currency,
                root_cause=i.root_cause,
                priority=i.priority or "HIGH",
                recovery_probability=round(prob, 2),
                expected_gross_recovery_minor=exp_gross,
                intervention_cost_minor=cost,
                expected_net_recovery_minor=net_ev,
                recommended_action=rec_action,
                reason=reason_txt,
                policy_state=policy_st,
                current_status=status_val,
                created_at=i.created_at.isoformat() if hasattr(i.created_at, "isoformat") else str(i.created_at),
                last_event_at=meta.get("last_event_at") or (i.created_at.isoformat() if hasattr(i.created_at, "isoformat") else str(i.created_at)),
                metadata=meta,
            )
            records.append(rec)

        # Sort strictly by expected_net_recovery_minor descending
        records.sort(key=lambda r: r.expected_net_recovery_minor, reverse=True)
        return records
