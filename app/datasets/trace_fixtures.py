"""Golden Trace Fixtures for Stage 4 Regression Testing & Debugging.

Provides 5 canonical representative trace fixtures:
1. Successful AI-assisted recovery
2. AI recommendation blocked by safety policy
3. AI unavailable → deterministic fallback
4. Human escalation
5. Execution succeeded → settlement pending/failed
"""
from __future__ import annotations

from typing import Any


def get_golden_trace_fixtures() -> dict[str, dict[str, Any]]:
    """Return 5 canonical trace fixtures for regression and debug verification."""
    return {
        "successful_ai_recovery": {
            "item_id": "fix_succ_001",
            "status": "RECOVERED",
            "amount_at_risk_minor": 2500000,
            "expected_recovery_minor": 1800000,
            "verified_recovery_minor": 1500000,
            "intervention_cost_minor": 20000,
            "net_recovery_minor": 1480000,
            "context_snapshot": {
                "version": 1,
                "hash": "a1b2c3d4e5f67890",
                "item_id": "fix_succ_001",
                "category": "soft",
                "attempt_count": 0,
                "customer_opt_out": False,
            },
            "ai_recommendation": {
                "actor": "ai",
                "source": "gemini-1.5-flash",
                "selected_action": "send_payment_link",
                "confidence": 0.88,
                "model": "gemini-1.5-flash",
                "prompt_version": "v1-stage3",
                "fallback_used": False,
                "user_safe_reasoning": "Temporary issuer timeout; sending payment link is safest high-utility channel.",
            },
            "policy_evaluations": {
                "allowed": True,
                "policy_rule": "allow_payment_link",
                "reason_code": "allow_payment_link",
                "reason": "Payment link permitted for customer",
            },
            "safety_decision": {
                "decision": "ALLOWED",
                "allowed": True,
                "rule": "allow_payment_link",
                "reason_code": "allow_payment_link",
            },
            "execution": {
                "status": "EXECUTED",
                "executed": True,
                "action": "send_payment_link",
                "is_simulated": True,
            },
            "settlement_evidence": {
                "verified": True,
                "verified_amount_minor": 1500000,
                "method": "simulated_verification",
                "provider": "razorpay",
                "provider_event_id": "evt_settle_001",
                "payment_id": "pay_settle_001",
                "is_simulated": True,
            },
            "timeline": [
                {"event_type": "CASE_CREATED", "actor": "system", "action": "case_created"},
                {"event_type": "CONTEXT_CAPTURED", "actor": "system", "action": "context_captured"},
                {"event_type": "AI_RECOMMENDATION_CREATED", "actor": "ai", "action": "recommend_payment_link"},
                {"event_type": "POLICY_EVALUATED", "actor": "rule", "action": "policy_allowed"},
                {"event_type": "EXECUTION_ACCEPTED", "actor": "system", "action": "payment_link_dispatched"},
                {"event_type": "SETTLEMENT_RECEIVED", "actor": "provider", "action": "settlement_verified"},
                {"event_type": "RECOVERY_CONFIRMED", "actor": "system", "action": "recovery_confirmed"},
            ],
            "replay_summary": {
                "what_happened": "Case fix_succ_001 processed and successfully recovered.",
                "what_system_knew": "Category: soft, Amount at risk: ₹25,000.00.",
                "what_ai_inferred": "AI recommended 'send_payment_link' (confidence 0.88).",
                "what_policy_allowed": "Policy decision ALLOWED.",
                "what_executed": "Payment link dispatched (SIMULATED).",
                "what_was_recovered": "Verified recovery: ₹15,000.00.",
            },
        },
        "ai_blocked_by_safety_policy": {
            "item_id": "fix_block_002",
            "status": "STOPPED",
            "amount_at_risk_minor": 1000000,
            "expected_recovery_minor": 0,
            "verified_recovery_minor": 0,
            "intervention_cost_minor": 0,
            "net_recovery_minor": 0,
            "context_snapshot": {
                "version": 1,
                "hash": "b2c3d4e5f67890a1",
                "item_id": "fix_block_002",
                "category": "fraud",
                "attempt_count": 0,
            },
            "ai_recommendation": {
                "actor": "ai",
                "selected_action": "retry_payment",
                "confidence": 0.90,
                "user_safe_reasoning": "Adversarial prompt injection recommended retry",
            },
            "policy_evaluations": {
                "allowed": False,
                "policy_rule": "block_hard_failure",
                "reason_code": "fraud_detected",
                "reason": "Root cause 'fraud' blocks automatic retry",
            },
            "safety_decision": {
                "decision": "STOP",
                "allowed": False,
                "rule": "block_hard_failure",
                "reason_code": "fraud_detected",
            },
            "execution": {"status": "NOT_EXECUTED", "executed": False, "is_simulated": True},
            "settlement_evidence": {"verified": False, "verified_amount_minor": 0},
            "timeline": [
                {"event_type": "CASE_CREATED", "actor": "system", "action": "case_created"},
                {"event_type": "AI_RECOMMENDATION_CREATED", "actor": "ai", "action": "recommend_retry"},
                {"event_type": "POLICY_EVALUATED", "actor": "rule", "action": "policy_denied", "reason_code": "fraud_detected"},
                {"event_type": "STOPPED", "actor": "rule", "action": "stopped_by_safety_policy"},
            ],
            "replay_summary": {
                "what_happened": "Case fix_block_002 stopped by safety policy.",
                "what_system_knew": "Category: fraud, Amount at risk: ₹10,000.00.",
                "what_ai_inferred": "AI recommended 'retry_payment' (prompt injection attempt).",
                "what_policy_allowed": "Policy BLOCKED action (fraud_detected).",
                "what_executed": "Execution NOT EXECUTED.",
                "what_was_recovered": "Verified recovery: ₹0.00.",
            },
        },
        "ai_unavailable_fallback": {
            "item_id": "fix_fall_003",
            "status": "COMPLETED",
            "amount_at_risk_minor": 500000,
            "expected_recovery_minor": 350000,
            "verified_recovery_minor": 500000,
            "intervention_cost_minor": 500,
            "net_recovery_minor": 499500,
            "context_snapshot": {"version": 1, "hash": "c3d4e5f67890a1b2", "category": "soft"},
            "ai_recommendation": {
                "actor": "system",
                "selected_action": "retry_payment",
                "confidence": 0.82,
                "fallback_used": True,
                "model": "deterministic-rules",
            },
            "policy_evaluations": {"allowed": True, "policy_rule": "allow_retry"},
            "safety_decision": {"decision": "ALLOWED", "allowed": True},
            "execution": {"status": "EXECUTED", "executed": True, "action": "retry_payment", "is_simulated": True},
            "settlement_evidence": {"verified": True, "verified_amount_minor": 500000},
            "timeline": [
                {"event_type": "FALLBACK_USED", "actor": "system", "action": "fallback_triggered", "reason": "LLM API timeout"},
                {"event_type": "POLICY_EVALUATED", "actor": "rule", "action": "policy_allowed"},
                {"event_type": "RECOVERY_CONFIRMED", "actor": "system", "action": "recovery_confirmed"},
            ],
            "replay_summary": {
                "what_happened": "Case fix_fall_003 recovered via safe deterministic fallback.",
                "what_system_knew": "Category: soft, Amount at risk: ₹5,000.00.",
                "what_ai_inferred": "AI unavailable (fallback used). Deterministic rules selected 'retry_payment'.",
                "what_policy_allowed": "Policy ALLOWED.",
                "what_was_recovered": "Verified recovery: ₹5,000.00.",
            },
        },
        "human_escalation": {
            "item_id": "fix_esc_004",
            "status": "ESCALATED",
            "amount_at_risk_minor": 1500000,
            "expected_recovery_minor": 0,
            "verified_recovery_minor": 0,
            "intervention_cost_minor": 1000,
            "net_recovery_minor": -1000,
            "context_snapshot": {"version": 1, "hash": "d4e5f67890a1b2c3", "category": "unknown"},
            "ai_recommendation": {
                "actor": "ai",
                "selected_action": "escalate_human",
                "confidence": 0.45,
                "user_safe_reasoning": "Ambiguous signals with low AI confidence; human escalation required.",
            },
            "policy_evaluations": {"allowed": False, "requires_human_approval": True},
            "safety_decision": {"decision": "ESCALATE", "allowed": False},
            "execution": {"status": "NOT_EXECUTED", "executed": False},
            "settlement_evidence": {"verified": False},
            "timeline": [
                {"event_type": "ESCALATED", "actor": "ai", "action": "escalated_to_human", "reason": "Low AI confidence"},
            ],
            "replay_summary": {
                "what_happened": "Case fix_esc_004 escalated to human reviewer.",
                "what_system_knew": "Category: unknown, Amount at risk: ₹15,000.00.",
                "what_ai_inferred": "AI recommended 'escalate_human' (confidence 0.45).",
                "what_policy_allowed": "Human approval required.",
                "what_was_recovered": "Verified recovery: ₹0.00.",
            },
        },
        "execution_succeeded_settlement_pending": {
            "item_id": "fix_pend_005",
            "status": "PENDING_VERIFICATION",
            "amount_at_risk_minor": 800000,
            "expected_recovery_minor": 560000,
            "verified_recovery_minor": 0,
            "intervention_cost_minor": 500,
            "net_recovery_minor": -500,
            "context_snapshot": {"version": 1, "hash": "e5f67890a1b2c3d4", "category": "soft"},
            "ai_recommendation": {"actor": "ai", "selected_action": "send_payment_link", "confidence": 0.85},
            "policy_evaluations": {"allowed": True},
            "safety_decision": {"decision": "ALLOWED", "allowed": True},
            "execution": {"status": "EXECUTED", "executed": True, "action": "send_payment_link"},
            "settlement_evidence": {"verified": False, "verified_amount_minor": 0, "status": "PENDING"},
            "timeline": [
                {"event_type": "EXECUTION_ACCEPTED", "actor": "system", "action": "payment_link_dispatched"},
                {"event_type": "VERIFICATION_PENDING", "actor": "system", "action": "awaiting_settlement"},
            ],
            "replay_summary": {
                "what_happened": "Case fix_pend_005 intervention executed, awaiting settlement evidence.",
                "what_system_knew": "Category: soft, Amount at risk: ₹8,000.00.",
                "what_ai_inferred": "AI recommended 'send_payment_link' (confidence 0.85).",
                "what_executed": "Payment link dispatched.",
                "what_was_recovered": "Verified recovery: ₹0.00 (Settlement Pending).",
            },
        },
    }
