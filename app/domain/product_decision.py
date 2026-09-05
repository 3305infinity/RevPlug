"""Canonical product decision model for RevPlug.

Maps every internal state/action/reason to one of four product-level decisions:

    RECOVER  — take a recovery action now
    WAIT     — do not act yet; a later time/condition has better expected value
    ESCALATE — human judgment is required
    STOP     — further recovery is unsafe, uneconomic, prohibited, or terminal

The mapping preserves the original internal reason_code and reason separately
so that downstream surfaces can always distinguish WHY a decision was made.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Canonical product-level decisions
DECISION_RECOVER = "RECOVER"
DECISION_WAIT = "WAIT"
DECISION_ESCALATE = "ESCALATE"
DECISION_STOP = "STOP"

ALL_DECISIONS = frozenset({DECISION_RECOVER, DECISION_WAIT, DECISION_ESCALATE, DECISION_STOP})


# ---------------------------------------------------------------------------
# Action -> Decision mapping
# ---------------------------------------------------------------------------
# Actions that RevPlug can execute autonomously -> RECOVER
_RECOVER_ACTIONS = frozenset({
    "send_payment_link",
    "retry_payment",
    "send_reminder",
    "send_customer_message",
    "alternate_channel",
    "promise_to_pay",
    "send_discount",
    "execute",
    "act",
})

# Actions that defer to a later time -> WAIT
_WAIT_ACTIONS = frozenset({
    "wait",
    "wait_systemic",
    "defer",
    "scheduled",
    "no_action",  # when paired with NEGATIVE_NET_EV or systemic
})

# Actions that require human judgment -> ESCALATE
_ESCALATE_ACTIONS = frozenset({
    "escalate_human",
    "review_required",
})

# Actions that halt recovery -> STOP
_STOP_ACTIONS = frozenset({
    "stop_recovery",
    "suppress",
})


# ---------------------------------------------------------------------------
# Policy state -> Decision mapping
# ---------------------------------------------------------------------------
_POLICY_STATE_TO_DECISION: dict[str, str] = {
    "ACTIONABLE": DECISION_RECOVER,
    "NEGATIVE_NET_EV": DECISION_STOP,
    "BLOCKED_FRAUD": DECISION_STOP,
    "BLOCKED_CONSENT": DECISION_STOP,
    "HUMAN_REVIEW_DISPUTE": DECISION_ESCALATE,
    "SUPPRESSED_SYSTEMIC": DECISION_WAIT,
}


# ---------------------------------------------------------------------------
# RecoveryStatus -> Decision mapping (for terminal/active states)
# ---------------------------------------------------------------------------
_STATUS_TO_DECISION: dict[str, str] = {
    "recovered": DECISION_RECOVER,
    "escalated": DECISION_ESCALATE,
    "stopped": DECISION_STOP,
    "failed": DECISION_STOP,
}


# ---------------------------------------------------------------------------
# Policy decision_type -> Decision mapping
# ---------------------------------------------------------------------------
_POLICY_DECISION_TYPE_TO_DECISION: dict[str, str] = {
    "ALLOWED": DECISION_RECOVER,
    "DENY": DECISION_STOP,
    "ESCALATE": DECISION_ESCALATE,
    "WAIT": DECISION_WAIT,
}


# ---------------------------------------------------------------------------
# Canonical decision summary
# ---------------------------------------------------------------------------
@dataclass
class ProductDecision:
    """Normalized product-level decision for a recovery opportunity."""
    decision: str  # RECOVER | WAIT | ESCALATE | STOP
    reason_code: str
    reason: str
    selected_action: str | None
    policy_status: str
    requires_human_review: bool = False
    terminal: bool = False
    scheduled_for: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "selected_action": self.selected_action,
            "policy_status": self.policy_status,
            "requires_human_review": self.requires_human_review,
            "terminal": self.terminal,
            "scheduled_for": self.scheduled_for,
        }


def resolve_decision(
    *,
    action: str | None = None,
    policy_state: str | None = None,
    status: str | None = None,
    policy_decision_type: str | None = None,
    reason_code: str = "",
    reason: str = "",
    requires_human_review: bool = False,
    terminal: bool = False,
    scheduled_for: str | None = None,
) -> ProductDecision:
    """Resolve the canonical product decision from any combination of inputs.

    Priority:
    1. Explicit action mapping
    2. Policy state mapping
    3. Policy decision_type mapping
    4. RecoveryStatus mapping
    5. Fallback: STOP (fail-closed)
    """
    decision = None
    selected_action = action

    # 1. Action-based mapping
    if action:
        act = action.lower()
        if act in _RECOVER_ACTIONS:
            decision = DECISION_RECOVER
        elif act in _WAIT_ACTIONS:
            decision = DECISION_WAIT
        elif act in _ESCALATE_ACTIONS:
            decision = DECISION_ESCALATE
        elif act in _STOP_ACTIONS:
            decision = DECISION_STOP

    # 2. Policy state mapping (overrides action if more specific)
    if policy_state and policy_state in _POLICY_STATE_TO_DECISION:
        decision = _POLICY_STATE_TO_DECISION[policy_state]
        if not selected_action:
            selected_action = _policy_state_to_action(policy_state)

    # 3. Policy decision_type mapping
    if policy_decision_type and policy_decision_type in _POLICY_DECISION_TYPE_TO_DECISION:
        pt_decision = _POLICY_DECISION_TYPE_TO_DECISION[policy_decision_type]
        # ESCALATE from policy takes precedence over RECOVER from action
        if pt_decision == DECISION_ESCALATE:
            decision = DECISION_ESCALATE
            requires_human_review = True
        elif pt_decision == DECISION_STOP and decision == DECISION_RECOVER:
            decision = DECISION_STOP
        elif decision is None:
            decision = pt_decision

    # 4. Status-based mapping
    if status and status.lower() in _STATUS_TO_DECISION:
        st_decision = _STATUS_TO_DECISION[status.lower()]
        if st_decision in (DECISION_ESCALATE, DECISION_STOP):
            decision = st_decision
        elif decision is None:
            decision = st_decision

    # 5. Fail-closed fallback
    if decision is None:
        decision = DECISION_STOP
        if not reason:
            reason = "Unable to determine decision from available state"

    # Determine policy_status string
    if decision == DECISION_RECOVER and not requires_human_review:
        policy_status = "ALLOWED"
    elif decision == DECISION_ESCALATE:
        policy_status = "ESCALATE"
    elif decision == DECISION_WAIT:
        policy_status = "WAIT"
    else:
        policy_status = "BLOCKED"

    return ProductDecision(
        decision=decision,
        reason_code=reason_code,
        reason=reason,
        selected_action=selected_action,
        policy_status=policy_status,
        requires_human_review=requires_human_review,
        terminal=terminal,
        scheduled_for=scheduled_for,
    )


def _policy_state_to_action(policy_state: str) -> str | None:
    """Map a policy_state back to a representative action."""
    mapping = {
        "ACTIONABLE": "send_payment_link",
        "NEGATIVE_NET_EV": "no_action",
        "BLOCKED_FRAUD": "stop_recovery",
        "BLOCKED_CONSENT": "stop_recovery",
        "HUMAN_REVIEW_DISPUTE": "escalate_human",
        "SUPPRESSED_SYSTEMIC": "wait",
    }
    return mapping.get(policy_state)


def decision_from_opportunity_record(record: Any) -> ProductDecision:
    """Build a ProductDecision from an OpportunityRecord (opportunity-inbox)."""
    policy_state = getattr(record, "policy_state", None) or ""
    recommended_action = getattr(record, "recommended_action", None) or ""
    reason = getattr(record, "reason", "") or ""

    # Determine reason_code from policy_state
    reason_code = policy_state.lower() if policy_state else ""

    requires_human = policy_state in {"HUMAN_REVIEW_DISPUTE"}
    terminal = getattr(record, "current_status", "") in {"recovered", "stopped"}

    return resolve_decision(
        action=recommended_action,
        policy_state=policy_state or None,
        status=getattr(record, "current_status", None),
        reason_code=reason_code,
        reason=reason,
        requires_human_review=requires_human,
        terminal=terminal,
    )


def decision_from_item(item: Any, recommended_action: str | None = None) -> ProductDecision:
    """Build a ProductDecision from a RecoveryItem."""
    status = item.status.value if hasattr(item.status, "value") else str(item.status)
    meta = item.metadata if isinstance(item.metadata, dict) else {}

    policy_state = meta.get("policy_state", "")
    reason = meta.get("reason", "")
    reason_code = meta.get("reason_code", "") or policy_state.lower()

    # Check for terminal states
    terminal = status in {"recovered", "stopped"}

    # Check if human review is required
    requires_human = (
        status == "escalated"
        or policy_state in {"HUMAN_REVIEW_DISPUTE"}
        or meta.get("requires_human_review", False)
    )

    action = recommended_action or meta.get("recommended_action", "")

    return resolve_decision(
        action=action,
        policy_state=policy_state or None,
        status=status,
        reason_code=reason_code,
        reason=reason,
        requires_human_review=requires_human,
        terminal=terminal,
    )
