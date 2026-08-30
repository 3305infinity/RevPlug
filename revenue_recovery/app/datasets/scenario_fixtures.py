"""Golden End-to-End Scenarios Fixtures for Stage 5 Bounded Autonomous Recovery.

Provides 8 canonical deterministic test scenarios (Scenarios A through H):
1. Scenario A — Successful recovery
2. Scenario B — Retry then alternative
3. Scenario C — Correct stop
4. Scenario D — Opt-out
5. Scenario E — Independent payment
6. Scenario F — Provider timeout & reconciliation
7. Scenario G — AI failure & fallback
8. Scenario H — Human approval required
"""
from __future__ import annotations

from typing import Any


def get_golden_end_to_end_scenarios() -> dict[str, dict[str, Any]]:
    """Return 8 canonical closed-loop end-to-end scenarios."""
    return {
        "scenario_a_successful_recovery": {
            "name": "Scenario A — Successful Recovery",
            "item_id": "scen_a_001",
            "category": "soft",
            "amount_minor": 2500000,
            "steps": [
                {"step": "DETECT", "status": "DETECTED"},
                {"step": "DIAGNOSE", "category": "soft"},
                {"step": "PLAN", "action": "send_payment_link"},
                {"step": "POLICY_CHECK", "allowed": True},
                {"step": "SAFETY_CHECK", "allowed": True},
                {"step": "ECONOMIC_CHECK", "ev_positive": True},
                {"step": "ACT", "action": "send_payment_link", "executed": True},
                {"step": "WAIT", "status": "PENDING_VERIFICATION"},
                {"step": "VERIFY", "settled": True, "provider_event_id": "evt_scen_a"},
                {"step": "TERMINAL", "status": "RECOVERED", "verified_amount": 2500000},
            ],
        },
        "scenario_b_retry_then_alternative": {
            "name": "Scenario B — Retry then Alternative",
            "item_id": "scen_b_002",
            "category": "soft",
            "amount_minor": 1500000,
            "steps": [
                {"step": "PLAN", "actions": ["retry_payment", "send_payment_link"]},
                {"step": "ACT_1", "action": "retry_payment", "result": "FAILED"},
                {"step": "RE_EVALUATE", "next_action": "send_payment_link"},
                {"step": "ACT_2", "action": "send_payment_link", "result": "EXECUTED"},
                {"step": "VERIFY", "settled": True},
                {"step": "TERMINAL", "status": "RECOVERED"},
            ],
        },
        "scenario_c_correct_stop": {
            "name": "Scenario C — Correct Stop (Do Nothing / Hard Decline)",
            "item_id": "scen_c_003",
            "category": "hard",
            "amount_minor": 500000,
            "steps": [
                {"step": "DIAGNOSE", "category": "hard"},
                {"step": "POLICY_CHECK", "retry_allowed": False},
                {"step": "SAFETY_CHECK", "stop": True, "reason": "block_hard_failure"},
                {"step": "ACT", "action": "stop_recovery", "executed": True},
                {"step": "TERMINAL", "status": "STOPPED"},
            ],
        },
        "scenario_d_opt_out": {
            "name": "Scenario D — Customer Opt-Out Mid-Workflow",
            "item_id": "scen_d_004",
            "category": "soft",
            "amount_minor": 800000,
            "steps": [
                {"step": "PLAN", "action": "send_customer_message"},
                {"step": "OPT_OUT_RECEIVED", "customer_opt_out": True},
                {"step": "RE_EVALUATE", "blocked": True, "reason": "customer_opted_out"},
                {"step": "TERMINAL", "status": "STOPPED"},
            ],
        },
        "scenario_e_independent_payment": {
            "name": "Scenario E — Independent Customer Payment",
            "item_id": "scen_e_005",
            "category": "soft",
            "amount_minor": 1200000,
            "steps": [
                {"step": "WAITING_VERIFICATION", "status": "PENDING_VERIFICATION"},
                {"step": "WEBHOOK_RECEIVED", "provider_event": "payment.captured"},
                {"step": "TERMINAL", "status": "RECOVERED"},
                {"step": "QUEUED_ACTION", "cancelled": True},
            ],
        },
        "scenario_f_provider_timeout": {
            "name": "Scenario F — Provider Timeout & Reconciliation",
            "item_id": "scen_f_006",
            "category": "soft",
            "amount_minor": 2000000,
            "steps": [
                {"step": "ACT", "action": "send_payment_link", "timeout": True},
                {"step": "STATUS", "outcome": "UNKNOWN"},
                {"step": "RECONCILE", "query_provider": True, "outcome": "ACCEPTED"},
                {"step": "DUPLICATE_PREVENTED", "re_execution": False},
            ],
        },
        "scenario_g_ai_failure": {
            "name": "Scenario G — AI Failure & Deterministic Fallback",
            "item_id": "scen_g_007",
            "category": "soft",
            "amount_minor": 900000,
            "steps": [
                {"step": "AI_REQUEST", "timeout": True},
                {"step": "FALLBACK_TRIGGERED", "used": True, "source": "deterministic-rules"},
                {"step": "PLAN", "action": "retry_payment"},
                {"step": "TERMINAL", "status": "RECOVERED"},
            ],
        },
        "scenario_h_human_approval": {
            "name": "Scenario H — Human Approval Required",
            "item_id": "scen_h_008",
            "category": "soft",
            "amount_minor": 5000000,
            "high_value": True,
            "steps": [
                {"step": "PLAN", "action": "custom_discount_offer"},
                {"step": "POLICY_CHECK", "approval_required": True},
                {"step": "STATUS", "status": "ESCALATED"},
                {"step": "HUMAN_APPROVAL", "granted": True},
                {"step": "ACT", "action": "custom_discount_offer", "executed": True},
                {"step": "TERMINAL", "status": "RECOVERED"},
            ],
        },
    }
