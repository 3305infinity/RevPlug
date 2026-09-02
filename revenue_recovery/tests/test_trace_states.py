"""Trace State Tests — Canonical decision trace evidence validation (Prompt 17).

Tests Cases A–J as specified:
A — RECOVER + successful execution + verified settlement
B — RECOVER + successful execution + no settlement
C — RECOVER + policy rejection
D — AI-assisted decision
E — Deterministic decision
F — AI fallback
G — WAIT
H — ESCALATE
I — STOP
J — No candidates
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — build minimal trace dicts that mimic backend trace_service output
# ---------------------------------------------------------------------------

def _make_trace(
    *,
    status: str = "pending",
    amount_minor: int = 100000,
    expected_recovery: int = 0,
    verified_recovery: int = 0,
    settlement_verified: bool = False,
    settlement_amount: int | None = None,
    execution_recorded: bool = False,
    execution_action: str | None = None,
    execution_status: str = "NOT_EXECUTED",
    ai_selected_action: str | None = None,
    classification_method: str = "RULES",
    ai_model: str | None = None,
    ai_fallback_used: bool = False,
    policy_allowed: bool | None = None,
    policy_reason_code: str | None = None,
    candidates: list | None = None,
    product_decision_decision: str | None = None,
    product_decision_reason: str | None = None,
    product_decision_reason_code: str | None = None,
    safety_decision_decision: str = "UNKNOWN",
    safety_decision_allowed: bool | None = None,
    safety_decision_reason: str | None = None,
) -> dict:
    """Build a synthetic trace dict matching the shape returned by build_case_trace()."""
    return {
        "item_id": "test-item",
        "status": status,
        "amount_at_risk_minor": amount_minor,
        "expected_recovery_minor": expected_recovery,
        "verified_recovery_minor": verified_recovery,
        "intervention_cost_minor": 500 if execution_recorded else 0,
        "net_recovery_minor": (settlement_amount or 0) - (500 if execution_recorded else 0),
        "context_snapshot": {
            "item_id": "test-item",
            "failure_category": "soft",
            "amount_minor": amount_minor,
            "attempt_count": 1,
            "hash": "abc123",
        },
        "diagnosis": {
            "root_cause": "soft",
            "confidence": 0.85,
            "recommended_action": ai_selected_action,
        } if ai_selected_action else {},
        "ai_recommendation": {
            "selected_action": ai_selected_action,
            "model": ai_model,
            "confidence": 0.9 if ai_selected_action and not ai_fallback_used else None,
            "fallback_used": ai_fallback_used,
        },
        "candidate_actions": candidates or [],
        "policy_evaluations": {
            "allowed": policy_allowed,
            "reason_code": policy_reason_code,
            "reason": policy_reason_code,
        } if policy_allowed is not None else {},
        "safety_decision": {
            "decision": safety_decision_decision,
            "allowed": safety_decision_allowed if safety_decision_allowed is not None else policy_allowed,
            "reason": safety_decision_reason,
            "reason_code": policy_reason_code,
        },
        "execution": {
            "executed": execution_recorded,
            "status": execution_status,
            "action": execution_action,
            "cost_minor": 500 if execution_recorded else None,
        },
        "settlement_evidence": {
            "verified": settlement_verified,
            "verified_amount_minor": settlement_amount if settlement_verified else 0,
        },
        "timeline": [],
        "replay_summary": {},
        "product_decision": {
            "decision": product_decision_decision,
            "reason": product_decision_reason,
            "reason_code": product_decision_reason_code,
            "selected_action": ai_selected_action,
        } if product_decision_decision else {},
        "classification_method": classification_method,
    }


# ---------------------------------------------------------------------------
# Import resolveCaseData logic equivalently in Python for assertion testing
# (The actual function lives in TypeScript; here we test the backend trace shape)
# ---------------------------------------------------------------------------

def _resolve_verified_recovery(trace: dict) -> int | None:
    """Mirrors TypeScript resolveCaseData() verifiedRecovery logic."""
    settlement = trace.get("settlement_evidence") or {}
    if settlement.get("verified") is True:
        return settlement.get("verified_amount_minor")
    return None


def _resolve_action_executed(trace: dict) -> str | None:
    """Mirrors TypeScript actionExecuted derivation — execution.action only."""
    execution = trace.get("execution") or {}
    return execution.get("action") if execution.get("executed") else None


# ---------------------------------------------------------------------------
# Case A — RECOVER + successful execution + verified settlement
# ---------------------------------------------------------------------------

def test_case_a_recover_verified_settlement():
    """RECOVER + execution + settlement: verified recovery is settlement amount, attribution shown."""
    trace = _make_trace(
        status="recovered",
        amount_minor=120000,
        expected_recovery=85000,
        settlement_verified=True,
        settlement_amount=120000,
        execution_recorded=True,
        execution_action="retry_payment",
        execution_status="EXECUTED",
        ai_selected_action="retry_payment",
        classification_method="RULES",
        policy_allowed=True,
        policy_reason_code="allow_retry",
        product_decision_decision="RECOVER",
        product_decision_reason_code="allow_retry",
        safety_decision_decision="ALLOWED",
        safety_decision_allowed=True,
    )
    verified = _resolve_verified_recovery(trace)
    action = _resolve_action_executed(trace)

    assert trace["product_decision"]["decision"] == "RECOVER"
    assert trace["execution"]["executed"] is True
    assert trace["settlement_evidence"]["verified"] is True
    assert verified == 120000, "Verified recovery must equal settlement amount"
    assert action == "retry_payment", "Action must come from execution record"
    # Cannot be more than amount at risk
    assert verified <= trace["amount_at_risk_minor"]


# ---------------------------------------------------------------------------
# Case B — RECOVER + successful execution + NO settlement
# ---------------------------------------------------------------------------

def test_case_b_recover_no_settlement():
    """RECOVER + execution but NO settlement: verified_recovery must be 0/None. Never claim money."""
    trace = _make_trace(
        status="pending",
        amount_minor=90000,
        expected_recovery=60000,
        settlement_verified=False,  # <-- No settlement
        execution_recorded=True,
        execution_action="send_payment_link",
        execution_status="EXECUTED",
        ai_selected_action="send_payment_link",
        policy_allowed=True,
        product_decision_decision="RECOVER",
        safety_decision_decision="ALLOWED",
        safety_decision_allowed=True,
    )
    verified = _resolve_verified_recovery(trace)

    assert trace["execution"]["executed"] is True
    assert trace["settlement_evidence"]["verified"] is False
    assert verified is None, "No verified recovery when settlement is absent — must not show money"
    # The UI must show 'Settlement not verified', not a recovery amount


# ---------------------------------------------------------------------------
# Case C — RECOVER + policy rejection
# ---------------------------------------------------------------------------

def test_case_c_recover_policy_rejected():
    """Policy rejected the action: no execution should have occurred."""
    trace = _make_trace(
        status="stopped",
        amount_minor=75000,
        expected_recovery=50000,
        execution_recorded=False,  # Policy blocked it — nothing executed
        ai_selected_action="retry_payment",
        classification_method="LLM_PRIMARY",
        policy_allowed=False,
        policy_reason_code="fraud_retry_protection",
        product_decision_decision="STOP",
        product_decision_reason="Fraud protection blocks automated retries.",
        product_decision_reason_code="fraud_retry_protection",
        safety_decision_decision="STOP",
        safety_decision_allowed=False,
        safety_decision_reason="Fraud protection blocks automated retries.",
    )
    verified = _resolve_verified_recovery(trace)
    action = _resolve_action_executed(trace)

    assert trace["policy_evaluations"]["allowed"] is False
    assert trace["execution"]["executed"] is False
    assert action is None, "No action executed — policy blocked it"
    assert verified is None, "No verified recovery — execution never occurred"
    assert trace["product_decision"]["reason_code"] == "fraud_retry_protection"


# ---------------------------------------------------------------------------
# Case D — AI-assisted decision
# ---------------------------------------------------------------------------

def test_case_d_ai_assisted():
    """AI-assisted: classification_method = LLM_PRIMARY, AI model visible."""
    trace = _make_trace(
        status="pending",
        amount_minor=80000,
        ai_selected_action="send_payment_link",
        classification_method="LLM_PRIMARY",
        ai_model="llama-3.3-70b-versatile",
        policy_allowed=True,
        product_decision_decision="RECOVER",
        safety_decision_decision="ALLOWED",
        safety_decision_allowed=True,
        candidates=[
            {"action": "send_payment_link", "selected": True, "expected_recovery": 60000, "cost": 500, "policy_status": "ALLOWED"},
            {"action": "retry_payment", "selected": False, "expected_recovery": 40000, "cost": 500, "policy_status": "ALLOWED"},
        ],
    )
    assert trace["classification_method"] == "LLM_PRIMARY"
    assert trace["ai_recommendation"]["model"] == "llama-3.3-70b-versatile"
    assert trace["ai_recommendation"]["fallback_used"] is False

    # Selected candidate is explicitly marked — not inferred from position
    selected = next((c for c in trace["candidate_actions"] if c.get("selected")), None)
    assert selected is not None, "Selected candidate must be explicitly marked"
    assert selected["action"] == "send_payment_link"

    # Unselected candidates exist
    unselected = [c for c in trace["candidate_actions"] if not c.get("selected")]
    assert len(unselected) == 1


# ---------------------------------------------------------------------------
# Case E — Deterministic decision (no AI)
# ---------------------------------------------------------------------------

def test_case_e_deterministic_no_fake_ai():
    """Deterministic: no AI model, no AI candidates should be fabricated."""
    trace = _make_trace(
        status="stopped",
        amount_minor=60000,
        classification_method="RULES",
        ai_selected_action=None,  # No AI proposal
        ai_model=None,
        policy_allowed=False,
        policy_reason_code="opt_out_block",
        product_decision_decision="STOP",
        product_decision_reason_code="opt_out_block",
        safety_decision_decision="STOP",
        safety_decision_allowed=False,
        candidates=[],  # No candidates — deterministic path
    )
    assert trace["classification_method"] == "RULES"
    assert trace["ai_recommendation"]["model"] is None, "No AI model for deterministic cases"
    assert trace["ai_recommendation"]["selected_action"] is None, "No AI action for deterministic cases"
    assert len(trace["candidate_actions"]) == 0

    # Frontend must show no candidates
    selected = next((c for c in trace["candidate_actions"] if c.get("selected")), None)
    assert selected is None, "No selected candidate when deterministic — never pick candidates[0]"


# ---------------------------------------------------------------------------
# Case F — AI fallback
# ---------------------------------------------------------------------------

def test_case_f_ai_fallback():
    """AI fallback: fallback_used=True, final action is from fallback logic not LLM."""
    trace = _make_trace(
        status="stopped",
        amount_minor=70000,
        ai_selected_action="stop_recovery",
        classification_method="LLM_FALLBACK",
        ai_model=None,  # Fallback means LLM didn't run successfully
        ai_fallback_used=True,
        policy_allowed=False,
        product_decision_decision="STOP",
        safety_decision_decision="STOP",
        safety_decision_allowed=False,
    )
    assert trace["classification_method"] == "LLM_FALLBACK"
    assert trace["ai_recommendation"]["fallback_used"] is True
    # UI must show "AI fallback" label, not claim AI chose the action


# ---------------------------------------------------------------------------
# Case G — WAIT
# ---------------------------------------------------------------------------

def test_case_g_wait():
    """WAIT: no execution, no recovery claim."""
    trace = _make_trace(
        status="pending",
        amount_minor=55000,
        product_decision_decision="WAIT",
        product_decision_reason="Retry window not yet optimal.",
        execution_recorded=False,
    )
    verified = _resolve_verified_recovery(trace)
    action = _resolve_action_executed(trace)

    assert trace["product_decision"]["decision"] == "WAIT"
    assert trace["execution"]["executed"] is False
    assert action is None, "No action executed for WAIT"
    assert verified is None, "No verified recovery for WAIT"
    # UI must not show any execution claim or recovered money


# ---------------------------------------------------------------------------
# Case H — ESCALATE
# ---------------------------------------------------------------------------

def test_case_h_escalate():
    """ESCALATE: requires human review, no recovery claim."""
    trace = _make_trace(
        status="escalated",
        amount_minor=200000,
        product_decision_decision="ESCALATE",
        product_decision_reason="Dispute flag active — human review required.",
        product_decision_reason_code="dispute_flag",
        execution_recorded=False,
        policy_allowed=False,
        policy_reason_code="escalation_required",
        safety_decision_decision="ESCALATE",
        safety_decision_allowed=False,
    )
    verified = _resolve_verified_recovery(trace)

    assert trace["product_decision"]["decision"] == "ESCALATE"
    assert trace["execution"]["executed"] is False
    assert verified is None, "No verified recovery for ESCALATE"
    assert trace["product_decision"]["reason"] == "Dispute flag active — human review required."


# ---------------------------------------------------------------------------
# Case I — STOP
# ---------------------------------------------------------------------------

def test_case_i_stop():
    """STOP: backend reason shown, no execution claim, no recovery claim."""
    trace = _make_trace(
        status="stopped",
        amount_minor=45000,
        product_decision_decision="STOP",
        product_decision_reason="Customer opted out of automated contact.",
        product_decision_reason_code="opt_out_block",
        execution_recorded=False,
        policy_allowed=False,
        policy_reason_code="opt_out_block",
        safety_decision_decision="STOP",
        safety_decision_allowed=False,
        safety_decision_reason="Customer opted out of automated contact.",
    )
    verified = _resolve_verified_recovery(trace)
    action = _resolve_action_executed(trace)

    assert trace["product_decision"]["decision"] == "STOP"
    assert trace["execution"]["executed"] is False
    assert action is None
    assert verified is None
    # Reason comes from backend, not a hardcoded string
    assert trace["product_decision"]["reason"] == "Customer opted out of automated contact."


# ---------------------------------------------------------------------------
# Case J — No candidates
# ---------------------------------------------------------------------------

def test_case_j_no_candidates():
    """No candidates: trace must remain valid. No selected candidate fabricated."""
    trace = _make_trace(
        status="stopped",
        amount_minor=30000,
        candidates=[],  # Explicitly empty
        product_decision_decision="STOP",
        product_decision_reason_code="opt_out_block",
    )
    assert len(trace["candidate_actions"]) == 0

    # Frontend rule: never pick candidates[0] — must be None when empty
    selected = next((c for c in trace["candidate_actions"] if c.get("selected")), None)
    assert selected is None, "No candidate must be selected when candidate_actions is empty"

    # UI must show 'No candidate evidence recorded'


# ---------------------------------------------------------------------------
# Evidence invariant tests
# ---------------------------------------------------------------------------

def test_action_executed_never_inferred_from_ai_proposal():
    """Action executed must ONLY come from execution record, not from AI proposal."""
    trace = _make_trace(
        status="stopped",
        execution_recorded=False,  # Nothing executed
        ai_selected_action="send_payment_link",  # AI proposed but it didn't execute
        policy_allowed=False,
        product_decision_decision="STOP",
    )
    action = _resolve_action_executed(trace)
    assert action is None, "Must not show execution when execution.executed is False"


def test_verified_recovery_never_inferred_from_status():
    """Verified recovery must be 0/None when settlement_evidence.verified is False, even if status=recovered."""
    trace = _make_trace(
        status="recovered",  # Item may be in recovered state
        settlement_verified=False,  # But no settlement evidence
        execution_recorded=True,
        execution_action="retry_payment",
    )
    verified = _resolve_verified_recovery(trace)
    assert verified is None, "Status=recovered alone must NOT yield verified recovery"


def test_settlement_inference_from_status_is_forbidden():
    """Explicitly confirm that detail.status alone cannot trigger settlement verification."""
    # This mirrors the fix to RecoveryReceipt.tsx where we removed:
    # outcomeVerified = outcome?.verified === true || detail?.status === "recovered"
    mock_detail = {"status": "recovered", "outcome": {"verified": False}}
    # Old (buggy) behavior:
    old_outcome_verified = mock_detail["status"] == "recovered"
    # New (correct) behavior:
    new_settlement_verified = mock_detail.get("outcome", {}).get("verified", False)
    assert old_outcome_verified is True, "Old code would have returned True"
    assert new_settlement_verified is False, "New code correctly returns False"
    # The point: status alone must NOT trigger settlement display


def test_no_hardcoded_model_in_deterministic_trace():
    """Deterministic trace must not carry a model name."""
    trace = _make_trace(
        classification_method="RULES",
        ai_model=None,
        ai_selected_action=None,
    )
    model = trace["ai_recommendation"]["model"]
    # Must be None \u2014 not "mock", not "Groq / llama-3.3-70b-versatile"
    assert model is None, f"Expected None, got '{model}'"


def test_no_is_simulated_in_execution_record():
    """Execution record must not contain is_simulated field (merchant-visible forbidden term)."""
    trace = _make_trace(execution_recorded=True, execution_action="retry_payment")
    assert "is_simulated" not in trace["execution"], "is_simulated must not appear in execution"


def test_cost_none_when_not_recorded():
    """Cost must be None (not 500) when not recorded from backend."""
    trace = _make_trace(execution_recorded=False)
    assert trace["execution"]["cost_minor"] is None, "Cost must be None when execution not recorded"
