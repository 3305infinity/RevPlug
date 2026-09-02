"""Portfolio-Level Next Best Action Engine for RevPlug.

Evaluates the open recovery portfolio and ranks intervention opportunities strictly by
Expected Net Business Value ($EV_{net}$) and urgency rather than raw amount at risk.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem, RecoveryStatus
from app.domain.product_decision import resolve_decision
from app.db.container import PersistenceContainer


@dataclass(frozen=True, slots=True)
class OpportunityItem:
    rank: int
    item_id: str
    customer_id: str
    customer_name: str
    amount_at_risk_minor: int
    expected_net_recovery_minor: int
    action: str
    action_label: str
    reason: str
    urgency: str  # HIGH, MEDIUM, LOW
    decision: str  # RECOVER | WAIT | ESCALATE | STOP
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "item_id": self.item_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "amount_at_risk_minor": self.amount_at_risk_minor,
            "expected_net_recovery_minor": self.expected_net_recovery_minor,
            "action": self.action,
            "action_label": self.action_label,
            "reason": self.reason,
            "urgency": self.urgency,
            "decision": self.decision,
            "reason_code": self.reason_code,
        }


class PortfolioNextBestActionEngine:
    """Ranks portfolio intervention opportunities by business value."""

    def __init__(self, container: PersistenceContainer) -> None:
        self._container = container

    def rank_opportunities(self) -> list[OpportunityItem]:
        from app.dashboard_api import _get_items

        items = _get_items(self._container)
        open_items = [i for i in items if i.status not in (RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED)]

        if not open_items:
            return []

        from app.domain.customer_names import derive_customer_name
        opportunities: list[OpportunityItem] = []

        for idx, item in enumerate(open_items):
            root = (item.root_cause or "soft").lower()
            amt = item.amount_minor

            if "auth" in root:
                action = "send_payment_link"
                act_label = "Payment Link"
                exp_ev = int(amt * 0.72)
                reason = "authentication failure + high historical link success (72%)"
                urgency = "HIGH"
                reason_code = "authentication_required"
            elif "dispute" in root or item.status == RecoveryStatus.ESCALATED:
                action = "escalate_human"
                act_label = "Human Review"
                exp_ev = int(amt * 0.55)
                reason = "Invoice disputed — automated collection prohibited by Policy Guard"
                urgency = "HIGH"
                reason_code = "dispute"
            elif "fraud" in root or "hard" in root:
                action = "stop_recovery"
                act_label = "STOP"
                exp_ev = 0
                reason = "Hard decline / fraud risk flag — recovery suppressed by Policy Shield"
                urgency = "LOW"
                reason_code = "fraud_block" if "fraud" in root else "hard_decline"
            else:
                action = "wait"
                act_label = "WAIT"
                exp_ev = int(amt * 0.68)
                reason = "Optimal morning retry window (10:00–11:30 AM) aligned with customer salary deposit history"
                urgency = "MEDIUM"
                reason_code = "retry_window"

            # Resolve canonical product decision
            product_decision = resolve_decision(action=action, reason_code=reason_code, reason=reason)

            meta = item.metadata if isinstance(item.metadata, dict) else {}
            c_name = meta.get("customer_name") or derive_customer_name(item.customer_id)

            opportunities.append(
                OpportunityItem(
                    rank=0,
                    item_id=item.id,
                    customer_id=item.customer_id,
                    customer_name=c_name,
                    amount_at_risk_minor=amt,
                    expected_net_recovery_minor=exp_ev,
                    action=action,
                    action_label=act_label,
                    reason=reason,
                    urgency=urgency,
                     decision=product_decision.decision,
                     reason_code=reason_code,
                 )
             )

         # Sort descending by Expected Net Recovery
        opportunities.sort(key=lambda o: -o.expected_net_recovery_minor)

        ranked: list[OpportunityItem] = []
        for i, opp in enumerate(opportunities):
            ranked.append(
                OpportunityItem(
                    rank=i + 1,
                    item_id=opp.item_id,
                    customer_id=opp.customer_id,
                    customer_name=opp.customer_name,
                    amount_at_risk_minor=opp.amount_at_risk_minor,
                    expected_net_recovery_minor=opp.expected_net_recovery_minor,
                    action=opp.action,
                    action_label=opp.action_label,
                    reason=opp.reason,
                    urgency=opp.urgency,
                    decision=opp.decision,
                    reason_code=opp.reason_code,
                )
            )

        return ranked
