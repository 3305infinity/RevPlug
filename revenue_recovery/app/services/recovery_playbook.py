"""Bounded Recovery Playbook Engine for RevPlug.

Generates category-specific multi-step bounded playbooks and performs dynamic
re-evaluation at every step (OBSERVE -> RE-EVALUATE -> NET EV -> POLICY CHECK -> DECIDE).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem
from app.domain.context import RecoveryContext
from app.policies.engine import PolicyEngine


@dataclass(slots=True)
class PlaybookStep:
    step_number: int
    name: str
    action: str
    status: str  # PENDING, CURRENT, COMPLETED, FAILED, SKIPPED
    result_summary: str | None = None
    observation: str | None = None
    wait_duration_minutes: int = 0
    estimated_cost_minor: int = 500

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "name": self.name,
            "action": self.action,
            "status": self.status,
            "result_summary": self.result_summary,
            "observation": self.observation,
            "wait_duration_minutes": self.wait_duration_minutes,
            "estimated_cost_minor": self.estimated_cost_minor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlaybookStep:
        return cls(
            step_number=data["step_number"],
            name=data["name"],
            action=data["action"],
            status=data["status"],
            result_summary=data.get("result_summary"),
            observation=data.get("observation"),
            wait_duration_minutes=data.get("wait_duration_minutes", 0),
            estimated_cost_minor=data.get("estimated_cost_minor", 500),
        )


@dataclass(slots=True)
class RecoveryPlaybook:
    playbook_id: str
    recovery_item_id: str
    failure_category: str
    strategy_name: str
    steps: list[PlaybookStep]
    current_step_index: int = 0
    budget_minor: int = 150000  # ₹1,500
    budget_used_minor: int = 0
    budget_remaining_minor: int = 150000
    expected_remaining_recovery_minor: int = 0
    stop_conditions: list[str] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, COMPLETED_RECOVERED, STOPPED_POLICY, ESCALATED
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def steps_remaining(self) -> int:
        return max(0, len(self.steps) - self.current_step_index)

    @property
    def current_step(self) -> PlaybookStep | None:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "recovery_item_id": self.recovery_item_id,
            "failure_category": self.failure_category,
            "strategy_name": self.strategy_name,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "steps_remaining": self.steps_remaining,
            "budget_minor": self.budget_minor,
            "budget_used_minor": self.budget_used_minor,
            "budget_remaining_minor": self.budget_remaining_minor,
            "expected_remaining_recovery_minor": self.expected_remaining_recovery_minor,
            "stop_conditions": self.stop_conditions,
            "status": self.status,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecoveryPlaybook:
        steps = [PlaybookStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            playbook_id=data["playbook_id"],
            recovery_item_id=data["recovery_item_id"],
            failure_category=data["failure_category"],
            strategy_name=data["strategy_name"],
            steps=steps,
            current_step_index=data.get("current_step_index", 0),
            budget_minor=data.get("budget_minor", 150000),
            budget_used_minor=data.get("budget_used_minor", 0),
            budget_remaining_minor=data.get("budget_remaining_minor", 150000),
            expected_remaining_recovery_minor=data.get("expected_remaining_recovery_minor", 0),
            stop_conditions=data.get("stop_conditions", []),
            status=data.get("status", "ACTIVE"),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


class RecoveryPlaybookEngine:
    """Generates and dynamically steps through bounded category playbooks."""

    DEFAULT_STOP_CONDITIONS = [
        "Hard bank decline",
        "Fraud risk flag active",
        "Customer opt-out request",
        "Retry budget exhausted (max 3)",
        "Negative EV ($EV_{net} < 0$)",
    ]

    def generate_playbook(self, item: RecoveryItem, context: RecoveryContext) -> RecoveryPlaybook:
        import uuid
        cat = (context.failure_category.value if hasattr(context.failure_category, "value") else str(context.failure_category)).lower()
        root = (item.root_cause or cat).lower()

        playbook_id = f"pb_{item.id}_{uuid.uuid4().hex[:6]}"
        expected_ev = item.expected_recovery_value or int(item.amount_minor * 0.85)

        if "auth" in root or "auth" in cat:
            strategy = "Authentication Requirement Pivot Playbook"
            steps = [
                PlaybookStep(1, "Diagnose root cause", "diagnose", "COMPLETED", result_summary="Diagnosed: authentication_required"),
                PlaybookStep(2, "Wait 30 min for bank session reset", "wait", "COMPLETED", wait_duration_minutes=30, result_summary="Failed: authentication_required"),
                PlaybookStep(3, "Send payment link", "send_payment_link", "CURRENT", estimated_cost_minor=2500),
                PlaybookStep(4, "Wait for customer response", "wait", "PENDING", wait_duration_minutes=60),
                PlaybookStep(5, "Send payment reminder", "send_reminder", "PENDING", estimated_cost_minor=500),
                PlaybookStep(6, "Escalate if unresolved", "escalate_human", "PENDING", estimated_cost_minor=5000),
            ]
            current_idx = 2
        elif "hard" in root or "expired" in root:
            strategy = "Expired Card / Hard Decline Playbook"
            steps = [
                PlaybookStep(1, "Diagnose root cause", "diagnose", "COMPLETED", result_summary="Diagnosed: hard_decline"),
                PlaybookStep(2, "Request payment method update", "send_payment_link", "CURRENT", estimated_cost_minor=2500),
                PlaybookStep(3, "Wait for update", "wait", "PENDING", wait_duration_minutes=1440),
                PlaybookStep(4, "Retry updated payment", "retry_payment", "PENDING", estimated_cost_minor=500),
                PlaybookStep(5, "Stop recovery", "stop_recovery", "PENDING", estimated_cost_minor=0),
            ]
            current_idx = 1
        elif "overdue" in root or "receivable" in root or "b2b" in root:
            strategy = "B2B Overdue Invoice Playbook"
            steps = [
                PlaybookStep(1, "Diagnose root cause", "diagnose", "COMPLETED", result_summary="Diagnosed: overdue_receivable"),
                PlaybookStep(2, "Send email notice", "send_reminder", "COMPLETED", result_summary="Notice delivered"),
                PlaybookStep(3, "Send payment link", "send_payment_link", "CURRENT", estimated_cost_minor=2500),
                PlaybookStep(4, "Record Promise-to-Pay", "promise_to_pay", "PENDING", estimated_cost_minor=500),
                PlaybookStep(5, "Send reminder on promised date", "send_reminder", "PENDING", estimated_cost_minor=500),
                PlaybookStep(6, "Escalate if broken", "escalate_human", "PENDING", estimated_cost_minor=5000),
            ]
            current_idx = 2
        elif "fraud" in root:
            strategy = "Fraud Risk Containment Playbook"
            steps = [
                PlaybookStep(1, "Diagnose root cause", "diagnose", "COMPLETED", result_summary="Diagnosed: fraud_detected"),
                PlaybookStep(2, "Policy Stop", "stop_recovery", "CURRENT", result_summary="Stopped by fraud guardrail"),
            ]
            current_idx = 1
        else:
            strategy = "Soft Failure Smart Retry Playbook"
            steps = [
                PlaybookStep(1, "Diagnose root cause", "diagnose", "COMPLETED", result_summary="Diagnosed: soft_decline"),
                PlaybookStep(2, "Wait for optimal payment window", "wait", "COMPLETED", wait_duration_minutes=120),
                PlaybookStep(3, "Smart retry payment", "retry_payment", "CURRENT", estimated_cost_minor=500),
                PlaybookStep(4, "Send payment link if retry fails", "send_payment_link", "PENDING", estimated_cost_minor=2500),
                PlaybookStep(5, "Alternate payment channel", "alternate_channel", "PENDING", estimated_cost_minor=2500),
                PlaybookStep(6, "Stop recovery", "stop_recovery", "PENDING", estimated_cost_minor=0),
            ]
            current_idx = 2

        used = sum(s.estimated_cost_minor for s in steps[:current_idx] if s.status == "COMPLETED")
        rem_budget = max(0, 150000 - used)

        return RecoveryPlaybook(
            playbook_id=playbook_id,
            recovery_item_id=item.id,
            failure_category=cat,
            strategy_name=strategy,
            steps=steps,
            current_step_index=current_idx,
            budget_minor=150000,
            budget_used_minor=used,
            budget_remaining_minor=rem_budget,
            expected_remaining_recovery_minor=expected_ev,
            stop_conditions=self.DEFAULT_STOP_CONDITIONS,
            status="ACTIVE",
        )

    def advance_playbook(
        self,
        playbook: RecoveryPlaybook,
        observation: dict[str, Any],
        item: RecoveryItem,
        policy_engine: PolicyEngine | None = None,
    ) -> RecoveryPlaybook:
        """Observe result and dynamically re-evaluate next step."""
        obs_success = observation.get("success", False) or observation.get("outcome") in ("success", "recovered")
        obs_action = observation.get("action")
        obs_reason = observation.get("reason") or observation.get("failure_reason")

        current = playbook.current_step
        if current:
            if obs_success:
                current.status = "COMPLETED"
                current.result_summary = f"Success: {obs_action or current.action} recovered payment"
                playbook.status = "COMPLETED_RECOVERED"
                playbook.expected_remaining_recovery_minor = 0
                return playbook

            current.status = "FAILED"
            current.result_summary = f"Failed: {obs_reason or 'Intervention unsuccessful'}"

        # Re-evaluate Policy Gate for remaining steps
        playbook.current_step_index += 1
        while playbook.current_step_index < len(playbook.steps):
            next_step = playbook.steps[playbook.current_step_index]
            if policy_engine:
                policy_dec = policy_engine.evaluate(item, next_step.action)
                if not policy_dec.allowed:
                    next_step.status = "SKIPPED"
                    next_step.result_summary = f"Skipped by policy: {policy_dec.policy_rule}"
                    playbook.current_step_index += 1
                    continue

            next_step.status = "CURRENT"
            break

        if playbook.current_step_index >= len(playbook.steps):
            playbook.status = "STOPPED_POLICY"

        playbook.budget_used_minor += (current.estimated_cost_minor if current else 500)
        playbook.budget_remaining_minor = max(0, playbook.budget_minor - playbook.budget_used_minor)
        playbook.updated_at = datetime.now(timezone.utc).isoformat()
        return playbook
